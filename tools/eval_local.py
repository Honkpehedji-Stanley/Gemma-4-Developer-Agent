#!/usr/bin/env python3
"""Évaluation locale sur les 129 tâches publiques, avec le harnais officiel swegemma.

Modes :
  gold   : le correctif de référence (task.patch) remplace l'agent. Doit donner ~100 %.
  empty  : correctif vide. Doit donner ~0 %. Avec `gold`, calibre l'instrument.
  agent  : l'agent de --submission-dir tourne contre un serveur OpenAI-compatible
           (--api-base / --api-key / --served-model), comme en notation Kaggle.
  replay : revérifie des correctifs déjà produits (--patches-dir/<instance_id>.patch).

Les budgets reprennent eval_config.yaml de la soumission (comme scripts/inference.py),
la compaction de contexte reprend les valeurs du README §7.2.

Exemples :
  .venv/bin/python tools/eval_local.py --mode gold --results-dir results/calib_gold
  .venv/bin/python tools/eval_local.py --mode agent --submission-dir submissions/baseline \
      --results-dir results/baseline_01 --api-base https://.../v1 --served-model gemma-4-31b-it
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def load_eval_section(submission_dir: Path) -> dict:
    cfg = submission_dir / 'eval_config.yaml'
    if not cfg.exists():
        return {}
    raw = yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}
    return raw.get('evaluation', raw) or {}


def install_task_env_injection() -> None:
    """Remplace l'injection des roues publiques (versions non épinglées) par l'environnement
    construit pour la tâche par tools/task_envs.py (voir ce fichier pour le pourquoi)."""
    import logging
    import shlex

    import swegemma.harness.container_setup as cs

    sys.path.insert(0, str(ROOT / 'tools'))
    from task_envs import ENVS, KEY_SCRIPT

    log = logging.getLogger('eval_local')
    original = cs._ensure_container_site_packages
    sp_dir = '/usr/local/lib/python3.13/site-packages'

    def inject(docker, container_id, repo, config=None):
        key = (docker.exec(container_id, f'python3 -S -c {shlex.quote(KEY_SCRIPT)}').stdout or '').strip()
        tar = ENVS / f'{key}.tar'
        if not key or not tar.exists():
            log.warning('pas d’environnement pour la clé %r (%s) : roues publiques', key, repo)
            return original(docker, container_id, repo, config)
        marker = f'{sp_dir}/.task_env_{key}'
        if docker.exec(container_id, f'test -f {marker}').exit_code == 0:
            return None
        dists = json.loads((ENVS / f'{key}.json').read_text())['dists']
        # Retire les versions de l'image qui entreraient en conflit (pytest 9, rich...).
        docker.exec(container_id, 'pip uninstall -y -q ' + ' '.join(map(shlex.quote, dists)) + ' 2>/dev/null || true')
        cs._extract_tar_into_site_packages(docker, container_id, tar)
        docker.exec(container_id, f'touch {marker}')
        return None

    cs._ensure_container_site_packages = inject


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['gold', 'empty', 'agent', 'replay'], required=True)
    ap.add_argument('--results-dir', type=Path, required=True)
    ap.add_argument('--submission-dir', type=Path, default=DATA / 'sample_submission')
    ap.add_argument('--tasks', type=Path, default=DATA / 'tasks.jsonl')
    ap.add_argument('--snapshots-dir', type=Path, default=DATA / 'snapshots')
    ap.add_argument('--patches-dir', type=Path, help='mode replay : dossier des .patch')
    ap.add_argument('--task-ids', nargs='+')
    ap.add_argument('--num-shards', type=int)
    ap.add_argument('--shard-index', type=int)
    ap.add_argument('--concurrency', type=int, default=1,
                    help='au-delà de 2, la machine (8 cœurs, 15 Go) sature : charge 40 et VS Code planté le 30/09')
    ap.add_argument('--image', default='swebench-sandbox:latest')
    ap.add_argument('--wheels-dir', type=Path, default=ROOT / 'build' / 'wheels')
    ap.add_argument('--deps', choices=['task-env', 'public-wheels'], default='task-env',
                    help='task-env : environnements de tools/task_envs.py ; public-wheels : comportement brut du harnais')
    ap.add_argument('--api-base', help='endpoint OpenAI-compatible (mode agent)')
    ap.add_argument('--api-key', default=os.environ.get('EVAL_API_KEY'), help='sinon variable EVAL_API_KEY (évite la clé dans ps)')
    ap.add_argument('--served-model', help='nom du modèle côté serveur (sinon alias Gemma)')
    # Surcharges de budget ; par défaut eval_config.yaml, puis valeurs de inference.py.
    ap.add_argument('--max-tool-calls', type=int)
    ap.add_argument('--max-time-minutes', type=float)
    ap.add_argument('--max-turns', type=int)
    ap.add_argument('--timeout-seconds', type=int)
    ap.add_argument('--display', default='quiet', choices=['auto', 'dashboard', 'single', 'quiet'])
    args = ap.parse_args()
    os.nice(10)  # la machine sert aussi au travail interactif

    import litellm
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from swegemma.evaluate import EvalConfig, Evaluator
    from swegemma.models import setup_gemma_model_registry

    litellm.drop_params = True

    ev = load_eval_section(args.submission_dir) if args.mode == 'agent' else {}
    pick = lambda cli, key, default: cli if cli is not None else ev.get(key, default)

    models = setup_gemma_model_registry(
        api_base=args.api_base, api_key=args.api_key, served_model=args.served_model
    )
    config = EvalConfig(
        tasks_path=args.tasks,
        snapshots_dir=args.snapshots_dir,
        results_dir=args.results_dir,
        submission_dir=args.submission_dir,
        models=models,
        image=args.image,
        sandbox='docker',
        wheels_dir=args.wheels_dir,
        graph_dir=str(DATA / 'graphs'),
        embeddings_dir=str(DATA / 'embeddings'),
        timeout_seconds=int(pick(args.timeout_seconds, 'timeout_seconds', 300)),
        max_tool_calls=int(pick(args.max_tool_calls, 'max_tool_calls', 100)),
        max_time_minutes=float(pick(args.max_time_minutes, 'max_time_minutes', 60.0)),
        max_turns=pick(args.max_turns, 'max_turns', None),
        task_ids=args.task_ids,
        skip_agent_patch=(args.mode == 'empty'),
        concurrency=args.concurrency,
        shard_index=args.shard_index,
        num_shards=args.num_shards,
        display_mode=args.display,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5, overlap_size=2, token_threshold=14336, event_retention_size=5
        ),
    )

    if args.deps == 'task-env':
        install_task_env_injection()

    evaluator = Evaluator(config)

    if args.mode in ('gold', 'replay'):
        from adk_eval_core.tracing import SessionTrace

        def fixed_patch(task) -> str:
            if args.mode == 'gold':
                return task.patch or ''
            p = args.patches_dir / f'{task.instance_id}.patch'
            return p.read_text(encoding='utf-8') if p.exists() else ''

        async def _fake_agent(task, *a, **kw):
            return fixed_patch(task), None, SessionTrace()

        evaluator._run_agent_sandbox = _fake_agent  # type: ignore[method-assign]

    result = asyncio.run(evaluator.run())
    summary = {
        'mode': args.mode,
        'submission_dir': str(args.submission_dir),
        'resolved': result.resolved,
        'total': result.total,
        'resolution_rate': result.resolution_rate,
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / 'run_meta.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == '__main__':
    sys.exit(main())
