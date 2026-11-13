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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_11194", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14419", "fastapi_14458", "fastapi_14463", "fastapi_14794", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_5077", "rich_2725", "rich_2943", "rich_3061", "rich_3063", "rich_3180", "rich_3506", "rich_3675", "rich_3676", "rich_3718", "rich_3882", "rich_3894", "rich_3934", "rich_3935", "rich_3953", "rich_4006", "rich_4076", "rich_4077"], "concurrency": 1, "submission": "submissions/sub03"}''')
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
