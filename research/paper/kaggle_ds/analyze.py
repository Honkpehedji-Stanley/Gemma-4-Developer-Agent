#!/usr/bin/env python3
"""Reproduce the paper's tables from trajectories.csv. Usage: python analyze.py trajectories.csv. Licence: Apache 2.0."""
import csv, sys, collections, statistics
from math import comb

rows = list(csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else 'trajectories.csv')))
print(f"{len(rows)} trajectories, {len({r['run'] for r in rows})} runs, {len({r['task'] for r in rows})} tasks")

print('\nTable 1: resolve rate by compaction state')
by = collections.defaultdict(list)
for r in rows:
    by[r['state']].append(int(r['resolved']))
for s in ('no_compaction', 'compacted_after_first_edit', 'compacted_before_first_edit'):
    v = by[s]; print(f'  {s:30s} {sum(v):4d}/{len(v):4d} = {sum(v)/len(v):.1%}')
comp = sum(len(by[s]) for s in by if s != 'no_compaction'); print(f'  compacted at least once: {comp}/{len(rows)} = {comp/len(rows):.0%}')

print('\nPaired within-task analysis: compacted before first edit (B) vs not (N)')
t = collections.defaultdict(lambda: {'B': [], 'N': []})
for r in rows:
    t[r['task']]['B' if r['state'] == 'compacted_before_first_edit' else 'N'].append(int(r['resolved']))
both = [k for k in t if t[k]['B'] and t[k]['N']]
rate = lambda v: sum(v) / len(v)
mb = sum(rate(t[k]['B']) for k in both) / len(both); mn = sum(rate(t[k]['N']) for k in both) / len(both)
better = sum(rate(t[k]['N']) > rate(t[k]['B']) for k in both); worse = sum(rate(t[k]['N']) < rate(t[k]['B']) for k in both)
n = better + worse; p = sum(comb(n, i) for i in range(better, n + 1)) / 2 ** n
pb = sum(sum(t[k]['B']) for k in both), sum(len(t[k]['B']) for k in both)
pn = sum(sum(t[k]['N']) for k in both), sum(len(t[k]['N']) for k in both)
print(f'  tasks observed both ways: {len(both)}')
print(f'  per-task mean success: N {mn:.1%}  B {mb:.1%}')
print(f'  pooled: N {pn[0]}/{pn[1]} = {pn[0]/pn[1]:.1%}  B {pb[0]}/{pb[1]} = {pb[0]/pb[1]:.1%}')
print(f'  tasks better without early compaction: {better}, worse: {worse}, one-sided sign test p = {p:.2g}')

def run_stats(run):
    rr = [r for r in rows if r['run'] == run]
    fe = sorted(int(r['first_edit_call']) for r in rr if r['first_edit_call'])
    return dict(resolved=sum(int(r['resolved']) for r in rr), compacted=sum(r['state'] != 'no_compaction' for r in rr),
                before=sum(r['state'] == 'compacted_before_first_edit' for r in rr),
                median_first_edit=fe[len(fe) // 2] if fe else None,
                median_growth=statistics.median(float(r['median_growth']) for r in rr if r['median_growth']),
                above_threshold=sum(int(r['max_prompt']) > 14336 for r in rr),
                mean_min=round(sum(float(r['duration_s'] or 0) for r in rr) / len(rr) / 60, 1))
print('\nTable 3: interventions on the 70-task panel')
for run in ('pub024-p70', 'armi-p70', 'armj-p70'):
    print(' ', run, run_stats(run))
a = {r['task']: r['state'] != 'no_compaction' for r in rows if r['run'] == 'pub024-p70'}
b = {r['task']: r['state'] != 'no_compaction' for r in rows if r['run'] == 'armj-p70'}
x = sum(a[k] and not b[k] for k in a if k in b); y = sum(b[k] and not a[k] for k in a if k in b)
n = x + y; p = min(1, 2 * sum(comb(n, i) for i in range(max(x, y), n + 1)) / 2 ** n)
print(f'  compaction, paired baseline vs armJ: {x} only baseline, {y} only armJ, exact McNemar p = {p:.3f}')
