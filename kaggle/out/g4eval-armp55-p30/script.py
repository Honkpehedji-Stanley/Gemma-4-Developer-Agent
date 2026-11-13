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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_11194", "fastapi_14258", "fastapi_14301", "fastapi_14306", "fastapi_14419", "fastapi_14458", "fastapi_14463", "fastapi_14794", "fastapi_14986", "fastapi_15280", "fastapi_15588", "fastapi_15589", "fastapi_5077", "rich_2725", "rich_2943", "rich_3061", "rich_3063", "rich_3180", "rich_3506", "rich_3675", "rich_3676", "rich_3718", "rich_3882", "rich_3894", "rich_3934", "rich_3935", "rich_3953", "rich_4006", "rich_4076", "rich_4077"], "concurrency": 1, "submission": "submissions/armP55"}''')
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
