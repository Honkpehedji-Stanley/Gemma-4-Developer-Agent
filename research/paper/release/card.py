import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig = plt.figure(figsize=(11.2, 5.6), dpi=100)  # 1120x560 = 2x (560x280)
fig.patch.set_facecolor('white')
fig.text(0.5, 0.90, 'Summarized Before It Edits', ha='center', va='center', fontsize=34, weight='bold', color='#1a1a2e')
fig.text(0.5, 0.79, 'Context compaction and the success of a local Gemma 4 coding agent', ha='center', fontsize=15, color='#444')
ax = fig.add_axes([0.30, 0.15, 0.40, 0.54])  # centred, so a square thumbnail crop keeps it
vals = [63.4, 41.0, 11.6]; cols = ['#3b6ea8', '#9cc3e6', '#d64545']
labels = ['No\ncompaction', 'Compacted\nafter 1st edit', 'Compacted\nbefore 1st edit']
ax.bar(range(3), vals, color=cols, width=0.7)
for i, v in enumerate(vals):
    ax.text(i, v + 2, f'{v:.0f}%', ha='center', fontsize=20, weight='bold', color='#3b6ea8' if i < 2 else '#d64545')
ax.set_xticks(range(3)); ax.set_xticklabels(labels, fontsize=12)
ax.set_ylim(0, 75); ax.set_yticks([])
for s in ('top', 'right', 'left'):
    ax.spines[s].set_visible(False)
fig.text(0.5, 0.025, 'Resolve rate, 909 trajectories  ·  paired by task: 30% → 14%, p = 0.0013', ha='center', fontsize=13, color='#555')
fig.savefig('../card.png', dpi=100)
