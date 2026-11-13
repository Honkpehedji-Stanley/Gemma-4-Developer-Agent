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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["fastapi_14258", "fastapi_14458", "fastapi_14794", "fastapi_15280", "rich_2725", "rich_2943", "rich_3180", "rich_3675", "rich_3935", "rich_4077"], "concurrency": 4, "submission": "submissions/sample_nolora"}''')
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
