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

CONFIG = json.loads(r'''{"mode": "agent", "teacher": false, "task_ids": ["fastapi_11194", "fastapi_13537", "fastapi_13920", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14372", "fastapi_14419", "fastapi_14448", "fastapi_14458", "fastapi_14463", "fastapi_14479", "fastapi_14487", "fastapi_14492", "fastapi_14616", "fastapi_14786", "fastapi_14794", "fastapi_14873", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_15661", "fastapi_15800", "fastapi_5077", "fastapi_5624", "fastapi_9425", "fastapi_9555", "fastapi_9753", "rich_2725", "rich_2943", "rich_3006", "rich_3043", "rich_3052", "rich_3061", "rich_3063", "rich_3067", "rich_3105", "rich_3180", "rich_3278", "rich_3454", "rich_3468", "rich_3470", "rich_3471", "rich_3472", "rich_3480", "rich_3506", "rich_3518", "rich_3521", "rich_3535", "rich_3675", "rich_3676", "rich_3718", "rich_3772", "rich_3777", "rich_3882", "rich_3894", "rich_3905", "rich_3930", "rich_3934", "rich_3935", "rich_3938", "rich_3942", "rich_3944", "rich_3953", "rich_4006", "rich_4075", "rich_4076", "rich_4077", "rich_4079"], "concurrency": 1, "submission": "submissions/armJ"}''')
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
