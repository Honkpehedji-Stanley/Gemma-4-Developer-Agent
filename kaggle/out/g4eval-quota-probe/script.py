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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["rich_3882"], "concurrency": 1, "submission": "submissions/armP"}''')
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
