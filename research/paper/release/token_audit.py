#!/usr/bin/env python3
"""Table 2: what fills the context before the first compaction, for trajectories compacted before their first edit.

Two modes (shares are in characters, a proxy for tokens). Licence: Apache 2.0.
  python token_audit.py RUN_DIR [RUN_DIR ...] [--export token_shares.csv]   # from raw traces
  python token_audit.py token_shares.csv                                    # from the published, content-free export
"""
import collections, csv, glob, json, os, statistics, sys

CATS = ['read_file outputs', 'agent visible text', 'grep outputs', 'other tool outputs', 'tool arguments']


def from_traces(dirs):
    from annotate_traces import annotate
    rows, turns = [], []
    for d in dirs:
        run = os.path.basename(os.path.normpath(d))
        states = {r['task']: r['state'] for r in annotate(d)}
        for path in sorted(glob.glob(os.path.join(d, 'results', 'traces', 'trace_*.json'))):
            steps = json.load(open(path))['steps']
            task = os.path.basename(path)[len('trace_'):-len('.json')]
            if run == 'pub024-p70':  # completion tokens vs visible text, all baseline trajectories
                for s in steps:
                    m = s.get('metrics') or {}
                    if m.get('completion_tokens'):
                        turns.append({'run': run, 'task': task, 'completion_tokens': m['completion_tokens'],
                                      'visible_chars': len(s.get('message') or '') + sum(len(json.dumps(tc.get('arguments'))) for tc in s.get('tool_calls') or [])})
            if states.get(task) != 'compacted_before_first_edit':
                continue
            share, prompts, last, n_reads, n = collections.Counter(), [], 'none', 0, 0
            for s in steps:
                p = (s.get('metrics') or {}).get('prompt_tokens')
                if p:
                    if prompts and p < 0.75 * prompts[-1]:
                        break
                    prompts.append(p)
                share['agent visible text'] += len(s.get('message') or '')
                for tc in s.get('tool_calls') or []:
                    n += 1; fn = tc['function_name']; share['tool arguments'] += len(json.dumps(tc.get('arguments')))
                    last = fn
                    if fn == 'run_command' and 'grep' in str(tc['arguments'].get('command', '')):
                        last = 'grep'
                    n_reads += fn == 'read_file'
                obs = s.get('observation')
                if obs:
                    share[{'read_file': 'read_file outputs', 'grep': 'grep outputs'}.get(last, 'other tool outputs')] += len(json.dumps(obs))
            rows.append({'run': run, 'task': task, 'tool_calls_before_compaction': n, 'read_file_calls': n_reads,
                         **{c: share[c] for c in CATS}})
    return rows, turns


def report(rows, turns):
    tot = {c: sum(int(r[c]) for r in rows) for c in CATS}; T = sum(tot.values())
    calls = [int(r['tool_calls_before_compaction']) for r in rows]; reads = [int(r['read_file_calls']) for r in rows]
    print(f'{len(rows)} trajectories; median tool calls before first compaction {statistics.median(calls)}; mean read_file calls {statistics.mean(reads):.1f}')
    for c in sorted(CATS, key=lambda c: -tot[c]):
        print(f'  {c:22s} {tot[c] / T:.0%}')
    if turns:
        print(f"baseline: mean completion tokens per turn {statistics.mean(int(t['completion_tokens']) for t in turns):.0f}, "
              f"visible text+arguments ~{statistics.mean(int(t['visible_chars']) for t in turns) / 3.5:.0f} tokens")


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) == 1 and a[0].endswith('.csv'):
        allr = list(csv.DictReader(open(a[0])))
        report([r for r in allr if r['kind'] == 'trajectory'], [r for r in allr if r['kind'] == 'turn'])
    else:
        out = a[a.index('--export') + 1] if '--export' in a else None
        dirs = [x for i, x in enumerate(a) if x != '--export' and (i == 0 or a[i - 1] != '--export')]
        rows, turns = from_traces(dirs)
        report(rows, turns)
        if out:
            fields = ['kind', 'run', 'task', 'tool_calls_before_compaction', 'read_file_calls', *CATS, 'completion_tokens', 'visible_chars']
            with open(out, 'w', newline='') as f:
                w = csv.DictWriter(f, fields, restval=''); w.writeheader()
                for r in rows: w.writerow({'kind': 'trajectory', **r})
                for t in turns: w.writerow({'kind': 'turn', **t})
