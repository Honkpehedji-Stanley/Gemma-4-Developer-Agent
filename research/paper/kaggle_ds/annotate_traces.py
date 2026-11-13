#!/usr/bin/env python3
"""Annotate swegemma/ADK ATIF traces with compaction events and first-edit timing.

Usage: python annotate_traces.py RUN_DIR [RUN_DIR ...] > trajectories.csv
RUN_DIR must contain results/task_results.jsonl and results/traces/trace_<task>.json.
A compaction is flagged when the prompt size drops by more than 25% between consecutive model calls
(prompt tokens only grow otherwise). Licence: Apache 2.0.
"""
import csv, glob, json, os, statistics, sys

DROP = 0.75
EDIT_TOOLS = {'edit_file', 'write_file'}

def annotate(run_dir):
    res = {}
    for line in open(os.path.join(run_dir, 'results', 'task_results.jsonl')):
        r = json.loads(line); res[r['instance_id']] = r
    for path in sorted(glob.glob(os.path.join(run_dir, 'results', 'traces', 'trace_*.json'))):
        task = os.path.basename(path)[len('trace_'):-len('.json')]
        if task not in res:
            continue
        prompts, n_calls, first_edit_call, first_edit_prompt, first_comp_call, n_comp, growth = [], 0, None, None, None, 0, []
        for step in json.load(open(path))['steps']:
            p = (step.get('metrics') or {}).get('prompt_tokens')
            if p:
                if prompts and p < DROP * prompts[-1]:
                    n_comp += 1
                    if first_comp_call is None:
                        first_comp_call = n_calls
                elif prompts and p > prompts[-1] and n_comp == 0:
                    growth.append(p - prompts[-1])  # prompt growth per model call, before any compaction
                prompts.append(p)
            for tc in step.get('tool_calls') or []:
                n_calls += 1
                if tc['function_name'] in EDIT_TOOLS and first_edit_call is None:
                    first_edit_call, first_edit_prompt = n_calls, (prompts[-1] if prompts else 0)
        r = res[task]
        if first_comp_call is None:
            state = 'no_compaction'
        elif first_edit_call is not None and first_edit_call <= first_comp_call:
            state = 'compacted_after_first_edit'
        else:
            state = 'compacted_before_first_edit'
        yield dict(run=os.path.basename(os.path.normpath(run_dir)), task=task, repo=r.get('repo'),
                   resolved=int(bool(r['resolved'])), state=state, n_compactions=n_comp,
                   first_compaction_call=first_comp_call, first_edit_call=first_edit_call,
                   prompt_at_first_edit=first_edit_prompt, max_prompt=max(prompts) if prompts else 0,
                   median_growth=statistics.median(growth) if growth else '', tool_calls=n_calls, duration_s=r.get('duration_seconds'), error=r.get('error') or '')

if __name__ == '__main__':
    rows = [row for d in sys.argv[1:] for row in annotate(d)]
    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
