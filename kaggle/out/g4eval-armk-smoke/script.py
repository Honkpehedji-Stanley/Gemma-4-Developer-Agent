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

CONFIG = json.loads(r'''{"mode": "agent", "task_ids": ["rich_3675", "fastapi_14258"], "concurrency": 1, "submission": "submissions/armK"}''')
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
