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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_11194", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14419", "fastapi_14458", "fastapi_14463", "fastapi_14794", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_5077", "rich_2725", "rich_2943", "rich_3061", "rich_3063", "rich_3180", "rich_3506", "rich_3675", "rich_3676", "rich_3718", "rich_3882", "rich_3894", "rich_3934", "rich_3935", "rich_3953", "rich_4006", "rich_4076", "rich_4077"], "concurrency": 1, "submission": "submissions/sub03_t65"}''')
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

    model_path = find_dir(['/kaggle/input/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct/2'], 'config.json')
    declared_models = sorted({m.strip().split('/')[-1] for m in discover_declared_models(AGENT_DIR)})
    assert declared_models == ['gemma-4-31b-it-qat-w4a16-ct'], declared_models
    declared = declared_models[0]
    adapters = discover_adapters(str(AGENT_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    n_gpu = torch.cuda.device_count()
    turing = torch.cuda.get_device_capability()[0] < 8  # T4 : test seulement, pas les conditions de notation
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
