# Compaction traces of a local Gemma 4 coding agent

Data and scripts for the writeup *Summarized Before It Edits* (Gemma 4 Developer Agent, Paper Track).

- `trajectories.csv`: 909 trajectories (25 evaluation runs, 70 tasks) of a Gemma 4 agent in the official ADK harness. One row per (run, task). Columns: run, task, repo, resolved, state (no_compaction / compacted_after_first_edit / compacted_before_first_edit), n_compactions, first_compaction_call, first_edit_call, prompt_at_first_edit, max_prompt, median_growth (median prompt increase per model call before the first compaction), tool_calls, duration_s, error.
- `token_shares.csv`: content-free character counts. `kind=trajectory` rows give the size of each context category before the first compaction (241 trajectories compacted before their first edit). `kind=turn` rows give completion tokens and visible characters per model turn (baseline run).
- `annotate_traces.py`: raw ADK traces → `trajectories.csv`. A compaction is a drop of more than 25 % in prompt tokens between two consecutive model calls.
- `analyze.py trajectories.csv`: Tables 1 and 3, the paired sign test and the McNemar test.
- `token_audit.py token_shares.csv`: Table 2. On raw traces: `token_audit.py RUN_DIR ... --export token_shares.csv`.
- `figure.py trajectories.csv figure1.png`: Figure 1.

Metrics only: no task text, code or model output is included. Licence: Apache 2.0.
