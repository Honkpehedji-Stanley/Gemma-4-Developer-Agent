#!/usr/bin/env python3
"""Figure 1 from trajectories.csv. Usage: python figure.py trajectories.csv figure1.png. Licence: Apache 2.0."""
import csv, collections, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rows = list(csv.DictReader(open(sys.argv[1])))
states = [('no_compaction', 'No compaction'), ('compacted_after_first_edit', 'Compacted\nafter first edit'),
          ('compacted_before_first_edit', 'Compacted\nbefore first edit')]
by = collections.defaultdict(list)
for r in rows:
    by[r['state']].append(int(r['resolved']))
t = collections.defaultdict(lambda: {'B': [], 'N': []})
for r in rows:
    t[r['task']]['B' if r['state'] == 'compacted_before_first_edit' else 'N'].append(int(r['resolved']))
both = [k for k in t if t[k]['B'] and t[k]['N']]
rate = lambda v: sum(v) / len(v)
pairs = sorted(((rate(t[k]['N']), rate(t[k]['B'])) for k in both), key=lambda x: x[0] - x[1])

fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={'width_ratios': [1, 1.2]})
cols = ['#4c78a8', '#9ecae9', '#e45756']
vals = [100 * rate(by[s]) for s, _ in states]
bars = a.bar([l for _, l in states], vals, color=cols)
for bar, (s, _), v in zip(bars, states, vals):
    a.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f'{v:.0f}%\n(n={len(by[s])})', ha='center', fontsize=9)
a.set_ylabel('Resolved (%)'); a.set_ylim(0, 80); a.set_title('A. All 909 trajectories (25 runs)', fontsize=10)
a.spines[['top', 'right']].set_visible(False)

for i, (n, bb) in enumerate(pairs):
    b.plot([0, 1], [100 * n, 100 * bb], color='#e45756' if n > bb else ('#4c78a8' if n < bb else '#bbbbbb'), alpha=.6, lw=1.2)
mn = 100 * sum(p[0] for p in pairs) / len(pairs); mb = 100 * sum(p[1] for p in pairs) / len(pairs)
b.plot([0, 1], [mn, mb], color='black', lw=3, marker='o', label=f'mean {mn:.0f}% → {mb:.0f}%')
b.set_xticks([0, 1], ['Not compacted\nbefore first edit', 'Compacted\nbefore first edit'])
b.set_xlim(-.3, 1.3); b.set_ylabel('Per-task success rate (%)')
b.set_title(f'B. Same task, both conditions ({len(both)} tasks; 19 lower, 4 higher)', fontsize=10)
b.legend(frameon=False, fontsize=9, loc='upper right'); b.spines[['top', 'right']].set_visible(False)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=160)
