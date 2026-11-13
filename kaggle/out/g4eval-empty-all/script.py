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

CONFIG = json.loads(r'''{"mode": "empty", "task_ids": null, "concurrency": 2, "submission": "sample_submission"}''')
SUBMISSION_ZIP_B64 = ''''''

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
    server = VllmServer(VllmConfig(
        model=str(model_path), port=8000, host='127.0.0.1',
        tool_call_parser='gemma4', reasoning_parser='gemma4', max_model_len=32768,
        dtype='bfloat16' if torch.cuda.is_bf16_supported() else 'auto',
        gpu_memory_utilization=0.90, enable_auto_tool_choice=True,
        enable_lora=True, max_loras=8, max_lora_rank=128,
        tensor_parallel_size=4 if n_gpu >= 4 else (2 if n_gpu >= 2 else 1),
        startup_timeout=60 * 20,
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
