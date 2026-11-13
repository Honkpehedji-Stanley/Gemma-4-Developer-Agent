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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_11194", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14419", "fastapi_14458", "fastapi_14463", "fastapi_14794", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_5077", "rich_2725", "rich_2943", "rich_3061", "rich_3063", "rich_3180", "rich_3506", "rich_3675", "rich_3676", "rich_3718", "rich_3882", "rich_3894", "rich_3934", "rich_3935", "rich_3953", "rich_4006", "rich_4076", "rich_4077"], "concurrency": 1, "submission": "submissions/armM"}''')
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
    for c in candidates:
        if (Path(c) / marker).exists():
            return Path(c)
    for p in Path('/kaggle/input').rglob(marker):
        return p.parent
    raise FileNotFoundError(marker)


DATA_DIR = find_dir(['/kaggle/input/competitions/gemma-4-developer-agent',
                     '/kaggle/input/gemma-4-developer-agent'], 'tasks.jsonl')
WHEELHOUSE_DIR = find_dir(['/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse',
                           '/kaggle/input/gemma-4-developer-agent-wheelhouse'], 'swegemma-0.2.7-py3-none-any.whl')
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
    from swegemma.models.discovery import validate_single_declared_model

    model_path = find_dir(['/kaggle/input/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct/2'], 'config.json')
    declared = validate_single_declared_model(AGENT_DIR)
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
    from swegemma.models import setup_gemma_model_registry
    models = setup_gemma_model_registry()

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
