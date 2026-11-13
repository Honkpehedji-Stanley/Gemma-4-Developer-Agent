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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_14258", "fastapi_14458", "fastapi_14794", "fastapi_15280", "rich_2725", "rich_2943", "rich_3180", "rich_3675", "rich_3935", "rich_4077"], "concurrency": 4, "submission": "submissions/v1_out8k"}''')
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
