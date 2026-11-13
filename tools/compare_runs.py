#!/usr/bin/env python3
"""Compare deux passages Kaggle tâche par tâche (sur les tâches communes) + effet de la compaction.
Usage : python3 tools/compare_runs.py kaggle/runs/pub024-p70 kaggle/runs/armi-p70"""
import glob, json, os, sys

def charge(run):
    res = {}
    for l in open(f'{run}/results/task_results.jsonl'):
        r = json.loads(l); res[r['instance_id']] = r
    for f in glob.glob(f'{run}/results/traces/*.json'):
        tid = os.path.basename(f)[6:-5]
        pt = [s['metrics'].get('prompt_tokens') for s in json.load(open(f))['steps'] if s.get('metrics')]
        pt = [p for p in pt if p]
        if tid in res: res[tid]['compacte'] = any(b < 0.75 * a for a, b in zip(pt, pt[1:]))
    return res

a, b = charge(sys.argv[1]), charge(sys.argv[2])
com = sorted(set(a) & set(b))
ra = sum(bool(a[t]['resolved']) for t in com); rb = sum(bool(b[t]['resolved']) for t in com)
g = [t for t in com if b[t]['resolved'] and not a[t]['resolved']]; p = [t for t in com if a[t]['resolved'] and not b[t]['resolved']]
print(f'{len(com)} tâches communes : A {ra}  B {rb}  (B gagne {len(g)}, perd {len(p)})')
print('gagnées :', ' '.join(g)); print('perdues :', ' '.join(p))
for n, r in (('A', a), ('B', b)):
    c = [t for t in com if r[t].get('compacte')]
    print(f"{n} : compactées {len(c)} (résolues {sum(bool(r[t]['resolved']) for t in c)}), "
          f"durée moy {sum(r[t]['duration_seconds'] or 0 for t in com)/len(com)/60:.1f} min")
