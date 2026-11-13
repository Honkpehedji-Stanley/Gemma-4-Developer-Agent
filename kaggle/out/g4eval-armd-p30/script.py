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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_11194", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14419", "fastapi_14458", "fastapi_14463", "fastapi_14794", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_5077", "rich_2725", "rich_2943", "rich_3061", "rich_3063", "rich_3180", "rich_3506", "rich_3675", "rich_3676", "rich_3718", "rich_3882", "rich_3894", "rich_3934", "rich_3935", "rich_3953", "rich_4006", "rich_4076", "rich_4077"], "concurrency": 1, "submission": "submissions/armD"}''')
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
