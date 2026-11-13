#!/usr/bin/env python3
"""Convertit les traces ATIF réussies du harnais en exemples d'entraînement (messages OpenAI + outils).

Chaque exemple = une trajectoire qui a résolu sa tâche : system, user, puis alternance assistant (texte + appels
d'outil) / tool (observations). Le gabarit de conversation de Gemma 4 (build/gemma4_tok/chat_template.jinja) sait
rendre ce format ; l'entraînement apprend donc aussi la syntaxe correcte des appels d'outil.

Usage : tools/trace_to_sft.py --runs kaggle/runs/pub024-p70 results/teacher/run1 --out build/sft/train.jsonl
        [--exclude-tasks kaggle/panel_holdout.txt] [--max-per-task 4]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = json.loads((ROOT / 'build' / 'tool_schemas.json').read_text())


def observation_text(obs) -> str:
    if isinstance(obs, dict):
        c = obs.get('content', '')
        return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
    return str(obs)


def trace_to_messages(trace: dict) -> list[dict] | None:
    msgs: list[dict] = []
    n_call = 0
    for s in trace['steps']:
        src = s.get('source')
        if src == 'system':
            msgs.append({'role': 'system', 'content': s.get('message') or ''})
        elif src == 'user':
            msgs.append({'role': 'user', 'content': s.get('message') or ''})
        elif src == 'agent':
            calls = s.get('tool_calls') or []
            m = {'role': 'assistant', 'content': s.get('message') or ''}
            if calls:
                m['tool_calls'] = []
                for c in calls:
                    n_call += 1
                    m['tool_calls'].append({'id': c.get('tool_call_id') or f'call_{n_call}', 'type': 'function',
                                            'function': {'name': c['function_name'],
                                                         'arguments': c.get('arguments') or {}}})
            msgs.append(m)
            if calls:
                # Une observation par étape dans ATIF ; elle répond au premier appel de l'étape.
                msgs.append({'role': 'tool', 'tool_call_id': m['tool_calls'][0]['id'],
                             'name': calls[0]['function_name'],
                             'content': observation_text(s.get('observation'))})
    if not msgs or msgs[0]['role'] != 'system' or not any(m.get('tool_calls') for m in msgs):
        return None
    # Seulement les six outils de base : l'agent entraîné n'aura que ceux-là (pas de graphe, d'analyseur, de skill).
    allowed = {t['function']['name'] for t in TOOLS}
    if any(c['function']['name'] not in allowed for m in msgs for c in m.get('tool_calls') or []):
        return None
    return msgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', nargs='+', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--exclude-tasks', type=Path, help='tâches gardées hors entraînement (une par ligne)')
    ap.add_argument('--max-per-task', type=int, default=4)
    args = ap.parse_args()

    excluded = set(args.exclude_tasks.read_text().split()) if args.exclude_tasks else set()
    per_task: dict[str, list] = defaultdict(list)
    for run in args.runs:
        res = run / 'results' if (run / 'results').exists() else run
        for line in open(res / 'task_results.jsonl'):
            r = json.loads(line)
            iid = r['instance_id']
            if not r['resolved'] or iid in excluded:
                continue
            tp = res / 'traces' / f'trace_{iid}.json'
            if not tp.exists():
                continue
            msgs = trace_to_messages(json.loads(tp.read_text()))
            if msgs:
                per_task[iid].append({'instance_id': iid, 'run': run.name, 'tool_calls': r.get('tool_calls'),
                                      'messages': msgs, 'tools': TOOLS})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(args.out, 'w') as f:
        for iid, exs in sorted(per_task.items()):
            # Les trajectoires les plus courtes d'abord : moins d'errance à imiter.
            for ex in sorted(exs, key=lambda e: e['tool_calls'] or 0)[:args.max_per_task]:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')
                n += 1
    print(f'{n} exemples, {len(per_task)} tâches -> {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
