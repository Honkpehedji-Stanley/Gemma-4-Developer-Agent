## Abstract

Local coding agents run with small context windows, so their frameworks compact the history: once a token threshold is crossed, older turns are replaced by a model-written summary. We study this mechanism in the official evaluation harness of the Gemma 4 Developer Agent competition (Google ADK 1.36.1, `gemma-4-31b-it-qat-w4a16-ct` on 4×L4, 32k context, compaction at 14,336 tokens). Reading the ADK source shows that the summarizer keeps only text parts: every tool call and every tool output (the code the agent has read) is discarded, and the issue statement survives only as a paraphrase. Across 25 evaluation runs (909 trajectories, 70 tasks from FastAPI and Rich), two thirds of trajectories are compacted. Trajectories that are compacted *before their first edit* resolve 12% of tasks, against 41% when the first edit came earlier and 63% without compaction. Pairing runs of the same task removes the difficulty confound: on the 47 tasks observed both ways, compaction before the first edit lowers the per-task success rate from 30.0% to 14.0% (worse on 19 tasks, better on 4; sign test p = 0.0013). A token audit shows that, before compaction, the context is filled by file reads (45%) and the agent's own prose (39%), while hidden reasoning is negligible. Pinning the exact issue in the system instruction, the obvious fix, has no measurable effect (30/70 vs 29/70). A token-budget prompt (narrow reads, terse prose, earlier edits) reduces compaction (paired McNemar p = 0.049) and time per task by 14%, with a non-significant gain in resolved tasks (32 vs 29), but does not reduce compaction before the first edit, which points to harness-side fixes. We release a compaction detector, the paired analysis and the annotated trajectories.

## 1. Introduction

The promise of a local coding agent is that a developer can fix real issues with an open model on hardware they own. The price is context: a 31B model quantized to 4 bits fits on four 24 GB L4 GPUs with a 32,768-token window, while a single debugging session reads several files, runs commands and writes code. Agent frameworks handle the overflow with *context compaction*: when the prompt crosses a threshold, older events are summarized by the model itself and the summary replaces them. OpenHands calls this a condenser and Google ADK calls it events compaction, and similar mechanisms exist in commercial coding assistants.

Compaction is usually treated as plumbing. This paper argues that it is a first-order determinant of agent success, and that its cost depends sharply on *when* it happens. Our contributions:

1. **Mechanism.** A source-level description of what ADK's compaction keeps and drops (Section 3). The summary is built from text parts only, so tool calls and tool outputs vanish.
2. **Measurement.** A simple trace-level detector for compaction events and the observation that two thirds of trajectories in the official setup are compacted (Section 4).
3. **Causal evidence.** A within-task paired analysis over 25 runs showing that compaction before the first edit halves the success rate of the same task (Section 5).
4. **Token budget.** An audit of what fills the window before compaction, which rules out the commonly tuned knob (the thinking budget) and points to file reads and agent prose instead (Section 6).
5. **Interventions.** One negative result (pinning the issue) and one budget-based intervention evaluated on the same 70 tasks (Section 7).
6. **Evaluation noise.** Four scorings of an unchanged agent spread over three tasks on a 58-task leaderboard, and a variant that gained on a local panel lost on the leaderboard; we argue for mechanistic endpoints alongside resolve rate (Section 8).

## 2. Setup

**Model and serving.** `gemma-4-31b-it-qat-w4a16-ct`, served by vLLM 0.19.1 with the competition's chat template, Gemma 4 tool and reasoning parsers, `max_model_len` 32,768, tensor parallel over 4×NVIDIA L4 (Kaggle). Sampling: temperature 0.2, top-p 0.95, 8,192 output tokens, thinking enabled (budget 4,096).

**Harness.** `swegemma` 0.2.11 on Google ADK 1.36.1, configured as in the official scorer: tool set `run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch`; the baseline allows 28 tool calls and 8 minutes per task (variants range from 3.5 to 10 minutes and 28 to 60 calls); `EventsCompactionConfig` with `token_threshold` 14,336 and `event_retention_size` 5; prefix caching. Tasks run sequentially (concurrency 1), as in scoring.

**Tasks.** The 129 public development tasks (FastAPI 67, Rich 48, Requests 13, HTTPX 1), each a real GitHub issue with hidden tests. We use two fixed panels: 30 tasks, and 70 *discriminative* tasks (resolved in some but not all of our early runs).

**Runs.** 25 complete evaluation runs of prompt and budget variants of a public baseline agent (including the two interventions of Section 7), 909 trajectories over 70 distinct tasks, 367 resolved. All runs share model, harness and compaction settings, which is what makes pooling across variants meaningful for the questions below. Every run stores ATIF traces with per-step token usage.

## 3. What compaction keeps

ADK's token-threshold compaction triggers after an invocation when the latest prompt exceeds `token_threshold`. All events except the last `event_retention_size` are passed to `LlmEventSummarizer`, which formats them as `author: text` lines and asks the agent's own model to "summarize the conversation, focusing on key information and decisions made". The formatter iterates over `event.content.parts` and keeps only `part.text` (`google/adk/apps/llm_event_summarizer.py`). Function calls and function responses have no text part, so they are not shown to the summarizer at all.

Three consequences follow for a coding agent:

- **The code it has read is gone.** File contents arrive as tool responses. After compaction the agent keeps only what it wrote about them in prose.
- **The specification is paraphrased.** The issue arrives as the first user message and is summarized like everything else. Exact names, error strings and status codes, which hidden tests check character for character, may not survive.
- **Edits to unseen lines become guesses.** `edit_file` requires `old_string` to match the file exactly; after compaction, the agent must re-read or reconstruct it.

## 4. Detecting compaction in traces

The traces do not log compaction events, but the effect is visible in the per-step prompt size. Without compaction, prompt tokens only grow (in the baseline run, a median of 458 tokens per model call). We flag a compaction when the prompt shrinks by more than 25% between consecutive model calls. The flag agrees with threshold crossings: in the baseline run, 48 of 70 trajectories exceed 14,336 prompt tokens and 47 are flagged.

**Prevalence.** In the baseline run, 47 of 70 trajectories are compacted at least once. Over all 25 runs, 619 of 909 (68%) are.

## 5. Compaction before the first edit

We classify each trajectory by whether compaction happened, and if so whether the agent had already called `edit_file` or `write_file` before the first compaction.

**Table 1.** Resolve rate by compaction state (25 runs, 909 trajectories).

| State | Trajectories | Resolved |
|---|---|---|
| No compaction | 290 | 63.4% |
| Compacted after the first edit | 378 | 41.0% |
| **Compacted before the first edit** | **241** | **11.6%** |

[ICI : insérer l image figure1.png]

*Figure 1. (A) Resolve rate by compaction state over all trajectories. (B) Each line is one task observed in both conditions across runs; red lines are tasks whose success rate drops when compaction precedes the first edit.*

The obvious objection is difficulty: hard tasks need more exploration, so they cross the threshold earlier *and* fail more often. We control for it by pairing within tasks. Because the 25 runs repeat the same tasks under slightly different agents and sampling noise, many tasks are observed both with and without early compaction.

**Paired analysis.** 47 tasks were observed in both conditions. Weighting every task equally, the success rate is 30.0% when compaction did not precede the first edit and 14.0% when it did. For 19 tasks the rate is higher without early compaction, for 4 it is lower, and for the rest it is equal; a one-sided sign test gives p = 0.0013 (two-sided p = 0.0026). Pooled over trajectories of these 47 tasks, the rates are 35.9% (165/460) and 12.2% (28/229).

Early compaction is therefore not just a marker of hard tasks: the same task, attempted by comparable agents, is about half as likely to be solved when the agent is summarized before it commits to an edit. Variants are not randomized, so residual confounding by agent variant is possible; Section 7 tests interventions directly.

## 6. What fills the window

To know which lever moves the threshold, we decompose context growth in the 241 trajectories compacted before the first edit, up to their first compaction (median 14 tool calls).

**Table 2.** Share of context growth before the first compaction.

| Source | Share |
|---|---|
| `read_file` outputs | 45% |
| Agent's visible text | 39% |
| `grep` outputs | 10% |
| Other tool outputs and tool arguments | 6% |

Two facts stand out. First, file reads dominate: the agent averages about seven reads before an edit. Second, the agent's own prose costs almost as much as the files. Hidden reasoning, by contrast, is negligible: in the baseline run, per turn the model generates 302 completion tokens on average, of which 279 are visible text and tool arguments. Lowering the thinking budget from 4,096 to 1,024, a common tuning move, scored within leaderboard noise of the baseline (0.15, against 0.17 to 0.20 for four scorings of the baseline).

## 7. Interventions

**Pinning the issue (negative).** ADK interpolates session state into the instruction, and the harness stores the issue as `problem_description`. Our variant armI appends the exact issue to the system instruction, which compaction never touches, plus a rule to re-read lines before editing them. On the 70-task panel it resolves 30 tasks against 29 for the baseline (+4/−3). The share of trajectories compacted before the first edit did not fall (19 vs 13), and the first edit came no earlier (median call 10). Keeping the specification is not enough: what is lost is the *working state* (the code read so far), and what matters is reaching an edit before losing it.

**Budgeting tokens (armJ).** The variant changes only three things in the baseline prompt: reads limited to 40 lines around a grep hit and never repeated, at most one sentence of prose per tool call, and a first edit by the 8th call instead of the 12th, with a one-paragraph explanation of the memory limit. On the same 70 tasks:

**Table 3.** Baseline vs interventions (70-task panel, one run each).

| | Baseline | armI (pinned issue) | armJ (token budget) |
|---|---|---|---|
| Resolved | 29 | 30 | 32 |
| Compacted at least once | 47 | 49 | 38 |
| Compacted before first edit | 13 | 19 | 12 |
| Prompt above 14,336 tokens at least once | 48 | 50 | 43 |
| Median prompt growth per model call (tokens) | 458 | 474 | 444 |
| Median tool call of first edit | 11 | 10 | 11 |
| Mean time per task (min) | 4.9 | 4.9 | 4.2 |

The budget works on the mechanism it targets: fewer trajectories cross the threshold (43 vs 48), and paired by task, 13 tasks are compacted under the baseline but not under armJ, against 4 the other way (exact McNemar p = 0.049). Typical growth per call barely changes (median 458 vs 444 tokens), so the effect comes from the trajectories that would have crossed the threshold, not from a uniform shrinking of every turn. Tasks are also 14% faster, which matters under the competition's 12-hour total limit (projected 8.4 h instead of 9.7 h for 120 tasks). The resolve gain (+5/−2) is in the expected direction but not significant on its own. The instruction did not move the first edit earlier, however, and compaction *before* the first edit is unchanged (12 vs 13). Prompting reduces how often the window overflows, but not the failure mode that matters most: the trajectories that explore longest before committing still cross the threshold first. This points to harness-side fixes (Section 10) rather than further prompting.

## 8. A note on evaluation noise

The leaderboard of the main competition scores 58 hidden tasks. The same baseline, submitted four times without any change, received 0.20, 0.18, 0.18 and 0.17. One task is worth 0.017, so differences below about four tasks are not evidence. Our 70-task panel has the same problem: armJ, which gained three tasks net on the panel and significantly reduced compaction, scored 0.13 on the leaderboard, below all four scorings of the baseline. Whether that gap is noise or a real regression on harder hidden tasks cannot be decided from one score. This is why we measure interventions first on a *mechanistic* endpoint (the share of trajectories compacted before the first edit), which is what the intervention is designed to change, and only then on resolve rate, which also depends on everything else the agent does.

## 9. Related work

SWE-bench (Jimenez et al., 2024) established issue resolution with hidden tests as the benchmark for coding agents; SWE-agent (Yang et al., 2024) showed that the agent–computer interface, including how file contents are shown, strongly affects success; Agentless (Xia et al., 2024) argued for fixed localize-then-repair pipelines with small budgets; OpenHands (Wang et al., 2025) provides history condensers for long sessions. MemGPT (Packer et al., 2023) treats context as managed memory, and Lost in the Middle (Liu et al., 2024) showed that long contexts are used unevenly. Our work is complementary: we measure the cost of a specific, widely deployed memory policy, summarization of tool history, on a local model under a fixed budget, and show that its cost depends on the agent's progress when it fires.

## 10. Recommendations and conclusion

For harness designers: do not drop tool outputs silently; keep the most recent version of every file region the agent has read, or at least the issue and the current diff, outside the summarized history; log compaction events. For agent designers: treat the compaction threshold, not the context limit, as the real budget; spend it on narrow reads and reach a first edit before it; measure interventions on mechanistic endpoints before resolve rate. For evaluators: report repeated runs, since single 58-task scores cannot rank agents that differ by a few tasks.

**Limitations.** One model and one harness; 70 tasks from mostly two repositories (FastAPI and Rich); the pooled variants are not randomized, so the paired analysis controls for task difficulty but not fully for agent variant; the token audit uses characters as a proxy for tokens; each intervention is a single run. The harness-side fix we recommend (a higher threshold, or keeping recent file regions out of the summary) is untested here: our weekly GPU quota was exhausted before the deadline. A threshold sweep with the same agent is the natural next experiment, and the released detector makes it cheap to analyse.

Compaction makes small-window agents possible, but it is not free. In our setting it is the most common failure path we could measure, and a cheap trace statistic is enough to see it.

## Reproducibility

Code: https://www.kaggle.com/code/stanleyhonkpehedji/gemma4-compaction-repro. Data: https://www.kaggle.com/datasets/stanleyhonkpehedji/gemma4-agent-compaction-traces with 909 annotated trajectories (task, variant, compaction flag, first-edit call, prompt sizes, resolved). Model, harness versions and all agent configurations are listed in Section 2 and the notebook. `annotate_traces.py` turns raw traces into `trajectories.csv`; `analyze.py` reproduces Tables 1 and 3, the counts in Section 4 and every test in Sections 5 and 7; `token_audit.py` reproduces Table 2 (character shares, a proxy for tokens) from raw traces or from the content-free `token_shares.csv`. Only metrics are published, no task content.

## References

- Jimenez, C. E. et al. SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR 2024.
- Yang, J. et al. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. NeurIPS 2024.
- Xia, C. S. et al. Agentless: Demystifying LLM-based Software Engineering Agents. arXiv:2407.01489, 2024.
- Wang, X. et al. OpenHands: An Open Platform for AI Software Developers as Generalist Agents. ICLR 2025.
- Packer, C. et al. MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560, 2023.
- Liu, N. F. et al. Lost in the Middle: How Language Models Use Long Contexts. TACL 2024.
- Google. Agent Development Kit (ADK), version 1.36.1, `google/adk/apps/llm_event_summarizer.py`.
