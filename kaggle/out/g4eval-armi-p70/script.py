# Évaluation Gemma 4 Developer Agent sur Kaggle, dans les conditions de la notation.
# Généré par kaggle/build_kernel.py : ne pas éditer la copie générée, éditer ce modèle.
#
# Reprend le montage du notebook officiel (ryanholbrook/getting-started-gemma-4-developer-agent) :
# roues du wheelhouse, bac à sable `subprocess`, vLLM gemma4 en mode agent.
# Modes : gold (correctif de référence), empty (aucun correctif), agent (soumission embarquée).

import asyncio
import base64
import glob
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

CONFIG = json.loads(r'''{"mode": "agent", "teacher": false, "task_ids": ["fastapi_11194", "fastapi_13537", "fastapi_13920", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14372", "fastapi_14419", "fastapi_14448", "fastapi_14458", "fastapi_14463", "fastapi_14479", "fastapi_14487", "fastapi_14492", "fastapi_14616", "fastapi_14786", "fastapi_14794", "fastapi_14873", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_15661", "fastapi_15800", "fastapi_5077", "fastapi_5624", "fastapi_9425", "fastapi_9555", "fastapi_9753", "rich_2725", "rich_2943", "rich_3006", "rich_3043", "rich_3052", "rich_3061", "rich_3063", "rich_3067", "rich_3105", "rich_3180", "rich_3278", "rich_3454", "rich_3468", "rich_3470", "rich_3471", "rich_3472", "rich_3480", "rich_3506", "rich_3518", "rich_3521", "rich_3535", "rich_3675", "rich_3676", "rich_3718", "rich_3772", "rich_3777", "rich_3882", "rich_3894", "rich_3905", "rich_3930", "rich_3934", "rich_3935", "rich_3938", "rich_3942", "rich_3944", "rich_3953", "rich_4006", "rich_4075", "rich_4076", "rich_4077", "rich_4079"], "concurrency": 1, "submission": "submissions/armI"}''')
SUBMISSION_ZIP_B64 = '''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'''

os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
os.environ['VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS'] = '1'
os.environ['VLLM_ENGINE_READY_TIMEOUT_S'] = '1200'
os.environ['VLLM_NO_USAGE_STATS'] = '1'
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

T0 = time.time()
WORKING_DIR = Path('/kaggle/working')
RESULTS_DIR = WORKING_DIR / 'results'


def find_dir(candidates, marker):
    # `marker` est un motif glob : les versions des roues changent quand Kaggle met le harnais à jour.
    for c in candidates:
        if any(Path(c).glob(marker)):
            return Path(c)
    for p in Path('/kaggle/input').rglob(marker):
        return p.parent
    raise FileNotFoundError(marker)


DATA_DIR = find_dir(['/kaggle/input/competitions/gemma-4-developer-agent',
                     '/kaggle/input/gemma-4-developer-agent'], 'tasks.jsonl')
WHEELHOUSE_DIR = find_dir(['/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse',
                           '/kaggle/input/gemma-4-developer-agent-wheelhouse'], 'swegemma-*.whl')
print('data:', DATA_DIR, '| wheelhouse:', WHEELHOUSE_DIR, flush=True)

# --- 1. Roues du harnais (identique au notebook officiel) -------------------------------------
for pth in glob.glob('/usr/local/lib/python*/dist-packages/*cutlass*.pth') + glob.glob(
        '/usr/local/lib/python*/site-packages/*cutlass*.pth'):
    try:
        os.unlink(pth)
    except OSError:
        pass
tmp_whl = Path('/tmp/wheelhouse')
tmp_whl.mkdir(parents=True, exist_ok=True)
for w in WHEELHOUSE_DIR.glob('*.whl'):
    if 'cutlass' in w.name.lower():
        continue
    if CONFIG['mode'] != 'agent' and any(k in w.name.lower() for k in ('vllm', 'torch', 'flashinfer', 'xformers', 'triton')):
        continue  # inutile sans GPU
    name = w.name.replace('cu128', '+cu128') if ('cu128' in w.name and '+' not in w.name) else w.name
    if not (tmp_whl / name).exists():
        os.symlink(w, tmp_whl / name)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '--force-reinstall',
                *sorted(str(w) for w in tmp_whl.glob('*.whl'))], check=True)
importlib.invalidate_caches()
print(f'roues installées ({time.time() - T0:.0f}s)', flush=True)

# --- 2. Soumission ------------------------------------------------------------------------------
AGENT_DIR = WORKING_DIR / 'submission'
shutil.rmtree(AGENT_DIR, ignore_errors=True)
if SUBMISSION_ZIP_B64.strip():
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(SUBMISSION_ZIP_B64))) as zf:
        zf.extractall(AGENT_DIR)
else:
    shutil.copytree(DATA_DIR / 'sample_submission', AGENT_DIR)
# Poids LoRA trop lourds pour le script : ils viennent de la sortie du kernel d'entraînement (kernel_sources).
for cfg_file in AGENT_DIR.glob('adapters/*/adapter_config.json'):
    w = cfg_file.parent / 'adapter_model.safetensors'
    if not w.exists():
        src = next(p for p in Path('/kaggle/input').rglob('adapter_model.safetensors')
                   if p.parent.name == cfg_file.parent.name)
        shutil.copy(src, w)
        print('adaptateur', cfg_file.parent.name, '<-', src, w.stat().st_size, flush=True)

import litellm  # noqa: E402
import yaml  # noqa: E402
from google.adk.agents.context_cache_config import ContextCacheConfig  # noqa: E402
from google.adk.apps._configs import EventsCompactionConfig  # noqa: E402
from swegemma.config import EvalConfig, build_submission_limits  # noqa: E402
from swegemma.evaluate import Evaluator  # noqa: E402

litellm.drop_params = True

# --- 3. Modèle (mode agent seulement) ----------------------------------------------------------
adapters = None
server = None
if CONFIG['mode'] == 'agent':
    import torch
    from adk_submission import VllmConfig, VllmServer, discover_adapters
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS
    # swegemma >= 0.2.11 : validate_single_declared_model a disparu ; la découverte est dans adk_submission.
    from adk_submission.discovery import discover_declared_models

    teacher = bool(CONFIG.get('teacher'))  # professeur gpt-oss-120b (génération de trajectoires d'entraînement)
    if teacher:
        # Sans internet (refusé sur GPU) : openai_harmony lit les encodages depuis le dataset tiktoken-encodings.
        os.environ['TIKTOKEN_ENCODINGS_BASE'] = str(next(Path('/kaggle/input').rglob('o200k_base.tiktoken')).parent)
        model_path = next(p.parent for p in Path('/kaggle/input/models').rglob('config.json') if 'gpt-oss-120b' in str(p))
    else:
        model_path = find_dir(['/kaggle/input/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct/2'], 'config.json')
    declared_models = sorted({m.strip().split('/')[-1] for m in discover_declared_models(AGENT_DIR)})
    assert declared_models == ['gemma-4-31b-it-qat-w4a16-ct'], declared_models
    declared = declared_models[0]
    adapters = discover_adapters(str(AGENT_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    n_gpu = torch.cuda.device_count()
    turing = torch.cuda.get_device_capability()[0] < 8  # T4 : test seulement, pas les conditions de notation
    if teacher:
        if n_gpu < 4 or turing:
            sys.exit('professeur : 4×L4 requis (61 Go de poids)')
        server = VllmServer(VllmConfig(
            model=str(model_path), port=8000, host='127.0.0.1',
            tool_call_parser='openai', reasoning_parser='openai_gptoss', max_model_len=65536,
            # Poids MXFP4 : 17,2 Gio par L4 ; à 0,90 + graphes CUDA il ne reste rien pour le cache KV.
            dtype='bfloat16', gpu_memory_utilization=0.96, enable_auto_tool_choice=True,
            extra_args=['--max-num-seqs', '8', '--max-num-batched-tokens', '4096'],
            tensor_parallel_size=4, startup_timeout=60 * 30,
        ), adapter_manifest=None)
    else:
        server = VllmServer(VllmConfig(
            model=str(model_path), port=8000, host='127.0.0.1',
            tool_call_parser='gemma4', reasoning_parser='gemma4', max_model_len=32768,
            # Paramètres de notation (HARNESS_README §3.1) : 0.80 et enable_thinking=True.
            default_chat_template_kwargs={'enable_thinking': True},
            # T4 : pas de bfloat16 matériel (vLLM refuse), all-reduce maison en panne, 15 Go par carte.
            dtype='float16' if turing else 'bfloat16',
            gpu_memory_utilization=0.92 if turing else 0.80,
            extra_args=['--disable-custom-all-reduce'] if turing else [],
            enable_auto_tool_choice=True,
            enable_lora=True, max_loras=8, max_lora_rank=128,
            tensor_parallel_size=4 if n_gpu >= 4 else (2 if n_gpu >= 2 else 1),
            startup_timeout=60 * 30,
        ), adapter_manifest=adapters)
    server.start()
    if teacher:
        # Le harnais impose thinking_budget=4096 (vLLM : thinking_token_budget), que gpt-oss refuse, et l'agent tourne
        # dans un sous-processus : un relais local sur 8001 retire ces champs avant vLLM (8000).
        import threading
        import urllib.request
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        class _Relais(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _relayer(self, body, un_seul_appel=False):
                req = urllib.request.Request('http://127.0.0.1:8000' + self.path, data=body, method=self.command,
                                             headers={'Content-Type': 'application/json'})
                try:
                    with urllib.request.urlopen(req, timeout=1800) as r:
                        code, out = r.status, r.read()
                except urllib.error.HTTPError as e:
                    code, out = e.code, e.read()
                if un_seul_appel and code == 200:
                    # gpt-oss émet jusqu'à 40 appels parallèles et le harnais leur renvoie à tous la même observation :
                    # on ne garde que le premier (une action par étape, comme Gemma).
                    try:
                        rep = json.loads(out)
                        for ch in rep.get('choices') or []:
                            tc = (ch.get('message') or {}).get('tool_calls')
                            if tc and len(tc) > 1:
                                ch['message']['tool_calls'] = tc[:1]
                        out = json.dumps(rep).encode()
                    except Exception:
                        pass
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def do_GET(self):
                self._relayer(None)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                for k in [k for k in body if 'thinking' in k]:
                    body.pop(k)
                ctk = body.get('chat_template_kwargs')
                if isinstance(ctk, dict):
                    for k in [k for k in ctk if 'thinking' in k]:
                        ctk.pop(k)
                body['parallel_tool_calls'] = False
                self._relayer(json.dumps(body).encode(), un_seul_appel=True)

        threading.Thread(target=ThreadingHTTPServer(('127.0.0.1', 8001), _Relais).serve_forever, daemon=True).start()
        type(server).base_url = property(lambda self: 'http://127.0.0.1:8001/v1')
    models = server.create_model_registry(aliases=[declared, 'gemma-4-31b-it-qat-w4a16-ct'],
                                          model_prefix='openai/', api_key='EMPTY')
    print(f'vLLM prêt sur {n_gpu} GPU ({time.time() - T0:.0f}s)', flush=True)
else:
    from adk_submission import ModelRegistry
    models = ModelRegistry()  # gold / empty : aucun modèle n'est appelé

# --- 4. Évaluation ------------------------------------------------------------------------------
ev = (yaml.safe_load((AGENT_DIR / 'eval_config.yaml').read_text()) or {}) if (AGENT_DIR / 'eval_config.yaml').exists() else {}
ev = ev.get('evaluation', ev) or {}
turns = ev.get('max_turns', ev.get('max_llm_calls'))
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl',
    snapshots_dir=DATA_DIR / 'snapshots',
    results_dir=RESULTS_DIR,
    submission_dir=AGENT_DIR,
    models=models,
    sandbox='subprocess',
    timeout_seconds=int(ev.get('timeout_seconds', 300)),
    max_time_minutes=float(ev.get('max_time_minutes', 60.0)),
    max_tool_calls=int(ev.get('max_tool_calls', 100)),
    max_turns=int(turns) if turns is not None else None,
    limits=limits,
    generation_constraints=gen_constraints,
    adapter_manifest=adapters,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2,
                                                    token_threshold=14336, event_retention_size=5),
    graph_dir=str(DATA_DIR / 'graphs'),
    embeddings_dir=str(DATA_DIR / 'embeddings'),
    wheels_dir=DATA_DIR / 'wheels',
    task_ids=CONFIG.get('task_ids') or None,
    skip_agent_patch=(CONFIG['mode'] == 'empty'),
    concurrency=int(CONFIG.get('concurrency', 1)),
    display_mode='quiet',
    verbose=False,
)
evaluator = Evaluator(config)

if CONFIG['mode'] == 'gold':
    from adk_eval_core.tracing import SessionTrace

    async def _gold(task, *a, **kw):
        return task.patch or '', None, SessionTrace()

    evaluator._run_agent_sandbox = _gold

result = asyncio.run(evaluator.run())
meta = {'config': CONFIG, 'resolved': result.resolved, 'total': result.total,
        'resolution_rate': result.resolution_rate, 'seconds': round(time.time() - T0),
        'python': sys.version}
(RESULTS_DIR / 'run_meta.json').write_text(json.dumps(meta, indent=2))
print(json.dumps(meta), flush=True)

# Instantané des paquets de l'environnement, pour comparer avec l'éval locale.
(RESULTS_DIR / 'pip_freeze.txt').write_text(
    subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True).stdout)
if server is not None:
    server.stop()
