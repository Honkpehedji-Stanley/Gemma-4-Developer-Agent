# Entraînement d'un LoRA pour Gemma 4 31B sur des trajectoires d'agent réussies (QLoRA 4 bits, 4×L4).
#
# Entrée : un .jsonl d'exemples {messages, tools} (tools/trace_to_sft.py) ; base = poids QAT non compressés
# (google/gemma-4/transformers/gemma-4-31b-it-qat-q4_0-unquantized/2), identiques au modèle de notation avant
# compression w4a16. Sortie : adapters/<nom>/adapter_config.json + adapter_model.safetensors, prêts pour vLLM.
#
# La perte ne porte que sur ce que le modèle écrit (texte et appels d'outil du tour « model »), jamais sur le
# système, l'énoncé ni les réponses d'outil. Elle est calculée seulement aux positions entraînées, par morceaux :
# les logits complets (séquence × 262 144) ne tiendraient pas en mémoire.
#
# Utilisable en local sur un modèle minuscule aléatoire (--tiny) pour vérifier la chaîne sans GPU.

import argparse
import json
import math
import os
import random
import re
import time
from pathlib import Path

import torch
import torch.nn.functional as F

TRAIN_TAGS = [('<|tool_call>', '<tool_call|>')]  # appels d'outil : toujours entraînés
RESP_OPEN, RESP_CLOSE = '<|tool_response>', '<tool_response|>'
TURN_MODEL, TURN_END, TURN_USER = '<|turn>model\n', '<turn|>', '<|turn>user'


def trained_char_spans(text: str) -> list[tuple[int, int]]:
    """Intervalles écrits par le modèle : du « <|turn>model » au tour utilisateur suivant, moins les réponses d'outil
    et les marqueurs <turn|>. Le gabarit Kaggle (celui de la notation) garde un seul tour « model » ouvert sur toute
    la trajectoire et y insère des <turn|> : <turn|> étant un jeton de fin, l'apprendre couperait les appels d'outil."""
    excluded = []
    for o, c in ((RESP_OPEN, RESP_CLOSE), (TURN_END, None)):
        pos = 0
        while (r := text.find(o, pos)) >= 0:
            e = r + len(o) if c is None else text.find(c, r)
            e = len(text) if e < 0 else (e if c is None else e + len(c))
            excluded.append((r, e))
            pos = e
    spans = []
    pos = 0
    while (a := text.find(TURN_MODEL, pos)) >= 0:
        a += len(TURN_MODEL)
        b = text.find(TURN_USER, a)
        b = len(text) if b < 0 else b
        cur = a
        for x, y in sorted(excluded):
            if y <= cur or x >= b:
                continue
            spans.append((cur, x))
            cur = max(cur, y)
        spans.append((cur, b))
        pos = b
    return [(x, y) for x, y in spans if y > x]


def encode(tok, template: str, ex: dict, max_len: int):
    text = tok.apply_chat_template(ex['messages'], tools=ex['tools'], chat_template=template, tokenize=False)
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False)
    ids, offs = enc['input_ids'], enc['offset_mapping']
    spans = trained_char_spans(text)
    labels = [-100] * len(ids)
    j = 0
    for i, (s, e) in enumerate(offs):
        while j < len(spans) and spans[j][1] <= s:
            j += 1
        if j < len(spans) and s >= spans[j][0] and e <= spans[j][1] and e > s:
            labels[i] = ids[i]
    if len(ids) > max_len:  # on garde le début : la localisation et la première édition comptent le plus
        ids, labels = ids[:max_len], labels[:max_len]
    return ids, labels


def chunked_loss(model, hidden, labels, chunk=512):
    """Entropie croisée sur les seules positions entraînées (décalage d'une position). Chaque morceau est recalculé à
    la rétropropagation (checkpoint) : sinon ses logits fp32 (512 × 262 144) restent tous en mémoire sur le GPU 0."""
    from torch.utils.checkpoint import checkpoint
    h = hidden[:, :-1, :]
    y = labels[:, 1:]
    keep = y != -100
    h, y = h[keep], y[keep]
    if y.numel() == 0:
        return hidden.sum() * 0.0, 0
    lm_head = model.get_output_embeddings()
    # device_map='auto' : la tête de sortie (liée aux embeddings) est sur le premier GPU, la dernière couche ailleurs.
    h, y = h.to(lm_head.weight.device), y.to(lm_head.weight.device)
    cap = getattr(model.config.get_text_config(), 'final_logit_softcapping', None)

    def piece(hc, yc):
        logits = lm_head(hc).float()
        if cap:
            logits = torch.tanh(logits / cap) * cap
        return F.cross_entropy(logits, yc, reduction='sum')

    total = 0.0
    for i in range(0, y.numel(), chunk):
        total = total + checkpoint(piece, h[i:i + chunk], y[i:i + chunk], use_reentrant=False)
    return total / y.numel(), y.numel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--model', default='')
    ap.add_argument('--tokenizer', default='', help='dossier du tokenizer (défaut : celui du modèle)')
    ap.add_argument('--template', default='', help='gabarit de conversation (défaut : celui du tokenizer)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-len', type=int, default=12288)
    ap.add_argument('--epochs', type=float, default=2.0)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--rank', type=int, default=16)
    ap.add_argument('--alpha', type=int, default=32)
    ap.add_argument('--grad-accum', type=int, default=8)
    ap.add_argument('--max-steps', type=int, default=0)
    ap.add_argument('--time-budget-h', type=float, default=10.0)
    ap.add_argument('--tiny', action='store_true', help='modèle minuscule aléatoire (test de la chaîne)')
    args = ap.parse_args()

    from peft import LoraConfig, get_peft_model
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.tokenizer or args.model)
    template = Path(args.template or Path(args.tokenizer or args.model, 'chat_template.jinja')).read_text()
    rows = [json.loads(l) for l in open(args.data)]
    data = [encode(tok, template, r, args.max_len) for r in rows]
    n_tr = sum(sum(1 for x in lab if x != -100) for _, lab in data)
    print(f'{len(data)} exemples, {sum(len(i) for i, _ in data)} tokens, {n_tr} entraînés', flush=True)

    if args.tiny:
        cfg = AutoConfig.from_pretrained(args.tokenizer)
        tc = cfg.text_config
        tc.num_hidden_layers, tc.hidden_size, tc.intermediate_size = 2, 64, 128
        tc.num_attention_heads, tc.num_key_value_heads, tc.head_dim = 2, 1, 32
        if hasattr(tc, 'global_head_dim'):
            tc.global_head_dim = 32
        if hasattr(tc, 'layer_types'):
            tc.layer_types = tc.layer_types[:2]
        model = AutoModelForCausalLM.from_config(tc)
    else:
        from transformers import BitsAndBytesConfig
        bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True,
                                 bnb_4bit_compute_dtype=torch.bfloat16)
        # GPU 0 porte aussi les embeddings (262 144 × 5 376) et la perte : on lui laisse de la marge.
        n = torch.cuda.device_count()
        mem = {i: ('12GiB' if i == 0 else '19GiB') for i in range(n)}
        model = AutoModelForCausalLM.from_pretrained(args.model, quantization_config=bnb, device_map='auto',
                                                     max_memory=mem, dtype=torch.bfloat16)
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False
    # Modules du seul modèle de langage (pas la tour vision) : mêmes noms dans le checkpoint w4a16 servi par vLLM.
    targets = r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$'
    if args.tiny:
        targets = r'.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$'
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.0,
                                             target_modules=targets, task_type='CAUSAL_LM'))
    model.print_trainable_parameters()
    if not args.tiny:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    total = args.max_steps or math.ceil(len(data) * args.epochs / args.grad_accum)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / 5) * 0.5 * (1 + math.cos(math.pi * min(s, total) / total)))
    dev = next(model.parameters()).device
    base = model.get_base_model()
    body = base.model if hasattr(base, 'model') else base
    t0, step, micro, seen = time.time(), 0, 0, 0.0
    order = []
    random.seed(0)
    while len(order) < total * args.grad_accum:
        idx = list(range(len(data)))
        random.shuffle(idx)
        order += idx
    model.train()
    for k in order[:total * args.grad_accum]:
        ids, lab = data[k]
        x = torch.tensor([ids], device=dev)
        y = torch.tensor([lab], device=dev)
        out = body(input_ids=x, use_cache=False)
        hidden = out.last_hidden_state if hasattr(out, 'last_hidden_state') else out[0]
        loss, n = chunked_loss(base, hidden, y.to(hidden.device))
        (loss / args.grad_accum).backward()
        seen += loss.item()
        micro += 1
        if micro % args.grad_accum == 0:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1
            el = time.time() - t0
            print(f'pas {step}/{total} perte {seen / args.grad_accum:.4f} lr {sched.get_last_lr()[0]:.2e} '
                  f'{el / 60:.1f} min', flush=True)
            seen = 0.0
            if el > args.time_budget_h * 3600:
                print('budget de temps atteint, arrêt', flush=True)
                break
    out_dir = Path(args.out)
    model.save_pretrained(out_dir, safe_serialization=True)
    for f in out_dir.iterdir():
        print(f.name, f.stat().st_size)


if __name__ == '__main__':
    main()
