#!/usr/bin/env python3
"""Mesure la précision de locate.py sur les 129 tâches publiques (sans GPU).

Pour chaque tâche : extraction des seuls .py du snapshot dans un dossier temporaire, lancement de
locate.py sur l'énoncé (+ indices), puis rang des fichiers source du correctif de référence parmi
les fichiers et définitions proposés. Écrit results/locate_eval.jsonl et affiche hit@1 / hit@3 / hit@8.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCATE = ROOT / 'kit' / 'swe-kit' / 'scripts' / 'locate.py'
OUT = ROOT / 'results' / 'locate_eval.jsonl'


def gold_sources(patch: str) -> list[str]:
    files = re.findall(r'^\+\+\+ b/(\S+)', patch, re.M)
    return [f for f in files if f.endswith('.py') and not re.search(r'(^|/)(tests?|docs_src)/|(^|/)test_', f)]


def main() -> int:
    tasks = [json.loads(l) for l in open(ROOT / 'data' / 'tasks.jsonl')]
    if len(sys.argv) > 1:
        tasks = [t for t in tasks if t['instance_id'] in set(sys.argv[1:])]
    OUT.parent.mkdir(exist_ok=True)
    done = {json.loads(l)['instance_id'] for l in open(OUT)} if OUT.exists() else set()
    with open(OUT, 'a') as out:
        for t in tasks:
            if t['instance_id'] in done:
                continue
            gold = gold_sources(t['patch'])
            if not gold:
                continue
            tmp = Path(tempfile.mkdtemp(prefix='loc_', dir=ROOT / 'build'))
            try:
                with tarfile.open(ROOT / 'data' / 'snapshots' / f"{t['instance_id']}.tgz", 'r:gz') as tf:
                    members = [m for m in tf if m.isfile() and m.name.endswith('.py')]
                    tf.extractall(tmp, members=members, filter='data')
                query = t['problem_statement'] + '\n' + (t.get('hints_text') or '')
                t0 = time.time()
                r = subprocess.run([sys.executable, str(LOCATE), query], capture_output=True, text=True,
                                   timeout=120, env={'SWE_KIT_ROOT': str(tmp), 'PATH': '/usr/bin:/bin'})
                dt = time.time() - t0
                files = re.findall(r'^\s*[\d.]+\s{2}(\S+\.py)$', r.stdout, re.M)
                defs = re.findall(r'^\s*[\d.]+\s{2}(\S+\.py):\d+-\d+', r.stdout, re.M)
                rank = min((files.index(g) + 1 for g in gold if g in files), default=None)
                def_rank = min((defs.index(g) + 1 for g in gold if g in defs), default=None)
                rec = {'instance_id': t['instance_id'], 'repo': t['repo'], 'gold': gold, 'file_rank': rank,
                       'def_rank': def_rank, 'seconds': round(dt, 2), 'out_chars': len(r.stdout),
                       'stmt_chars': len(t['problem_statement'])}
                out.write(json.dumps(rec) + '\n')
                out.flush()
                print(t['instance_id'], rank, def_rank, f'{dt:.2f}s', flush=True)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    recs = [json.loads(l) for l in open(OUT)]
    n = len(recs)
    for k in (1, 3, 8):
        hit = sum(1 for r in recs if r['file_rank'] and r['file_rank'] <= k)
        print(f'hit@{k} fichier : {hit}/{n} = {hit / n:.0%}')
    print('temps max', max(r['seconds'] for r in recs), 's ; sortie max', max(r['out_chars'] for r in recs), 'car.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
