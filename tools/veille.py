#!/usr/bin/env python3
"""Veille publique : tous les notebooks de la compétition → configuration exacte + scores annoncés → research/VEILLE.md.

Pour chaque notebook nouveau ou relancé depuis le dernier passage :
  - `kernels pull` (code + texte) et `kernels output` (le submission.zip réellement produit) dans research/veille/<auteur>__<slug>/
  - lecture STATIQUE seulement (contenu non fiable : rien n'est exécuté) du zip : agent.yaml, sampling, eval_config,
    adaptateurs LoRA, hash du prompt ; scores « LB 0.xx » cités dans le texte.
Écrit research/VEILLE.md (trié par meilleur score annoncé, ★ = nouveau ou changé) et research/veille/index.json.
Usage : python3 tools/veille.py [--max 300]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'research' / 'veille'
COMP = 'gemma-4-developer-agent'
BASE_PROMPT = (ROOT / 'submissions/pub024/prompts/system.md')


def kaggle(*a, timeout=600):
    r = subprocess.run(['uvx', '--with', 'six', 'kaggle', *a], capture_output=True, text=True, timeout=timeout)
    return r.stdout + r.stderr


def lister(maxn):
    rows, page = [], 1
    while len(rows) < maxn:
        txt = kaggle('kernels', 'list', '--competition', COMP, '--page-size', '100', '-p', str(page), '--csv')
        lines = [l for l in txt.splitlines() if l.count(',') >= 3]
        got = list(csv.DictReader(io.StringIO('\n'.join(lines))))
        if not got:
            break
        rows += got
        page += 1
    return rows[:maxn]


def num(pat, s):
    m = re.search(pat, s)
    return m.group(1) if m else ''


def lire_zip(zp: Path):
    info = {}
    try:
        z = zipfile.ZipFile(zp)
    except Exception as e:  # zip absent ou corrompu
        return {'zip': f'illisible ({type(e).__name__})'}
    names = z.namelist()
    txt = {n: z.read(n).decode('utf-8', 'replace') for n in names
           if n.endswith(('.yaml', '.yml', '.md', '.json', '.txt')) and z.getinfo(n).file_size < 2_000_000}
    tout = '\n'.join(txt.values())
    info['thinking'] = num(r'thinking_budget:\s*(\d+)', tout)
    info['temp'] = num(r'temperature:\s*([\d.]+)', tout)
    info['calls'] = num(r'max_tool_calls:\s*(\d+)', tout)
    info['min'] = num(r'max_time_minutes:\s*([\d.]+)', tout)
    info['out_tok'] = num(r'max_output_tokens:\s*(\d+)', tout)
    agent = txt.get('agent.yaml', '') or txt.get('root_agent.yaml', '')
    info['tools'] = ' '.join(re.findall(r'^\s*-\s*([a-z_]+)\s*$', agent.split('generate_content_config')[0], re.M))
    info['sub_agents'] = 'oui' if 'sub_agents' in tout else ''
    info['lora'] = ', '.join(sorted({n.split('/')[1] for n in names if n.startswith('adapters/') and n.count('/') >= 2}))
    if info['lora']:
        cfgs = [json.loads(txt[n]) for n in txt if n.endswith('adapter_config.json')]
        info['lora'] += ' r=' + ','.join(str(c.get('r')) for c in cfgs)
    prompts = [n for n in names if n.startswith('prompts/') or n.endswith('system.md')]
    ph = hashlib.md5(''.join(txt.get(n, '') for n in sorted(prompts)).encode()).hexdigest()[:8] if prompts else ''
    base = hashlib.md5(BASE_PROMPT.read_text().encode()).hexdigest()[:8] if BASE_PROMPT.exists() else ''
    info['prompt'] = ph + (' (=pub024)' if ph and ph == base else '')
    info['nfiles'] = str(len(names))
    return info


def scores_annonces(d: Path):
    s = ''
    for p in list(d.glob('*.ipynb')) + list(d.glob('*.py')):
        try:
            nb = json.loads(p.read_text()) if p.suffix == '.ipynb' else {'cells': [{'source': p.read_text()}]}
            s += '\n'.join(''.join(c.get('source', '')) for c in nb.get('cells', []))
        except Exception:
            pass
    vals = re.findall(r'(?i)(?:\bLB\b|public(?: leaderboard)?(?: score)?|leaderboard|scored?)\D{0,25}?\b(0\.\d{2,3})\b', s)
    return sorted({v for v in vals if 0.05 <= float(v) <= 0.6}, key=float, reverse=True)[:5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max', type=int, default=300)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = OUT / 'index.json'
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {}
    rows = lister(a.max)
    nouveaux = []
    for r in rows:
        ref, run = r.get('ref', ''), r.get('lastRunTime', '')
        if '/' not in ref:
            continue
        key = ref.replace('/', '__')
        old = idx.get(ref, {})
        d = OUT / key
        if old.get('lastRunTime') != run or not d.exists():
            d.mkdir(exist_ok=True)
            kaggle('kernels', 'pull', ref, '-p', str(d), '-m')
            od = d / 'output'
            od.mkdir(exist_ok=True)
            kaggle('kernels', 'output', ref, '-p', str(od), '--file-pattern', r'.*\.zip$', timeout=900)
            zips = sorted(od.rglob('*.zip'), key=lambda p: (p.name != 'submission.zip', p.stat().st_size))
            info = lire_zip(zips[0]) if zips else {'zip': 'aucun'}
            info.update(scores=scores_annonces(d), title=r.get('title', ''), votes=r.get('totalVotes', ''),
                        lastRunTime=run, vu=datetime.now(timezone.utc).strftime('%F'), nouveau=True)
            idx[ref] = info
            nouveaux.append(ref)
        else:
            idx[ref]['nouveau'] = False
    idx_p.write_text(json.dumps(idx, indent=1, ensure_ascii=False))

    def best(v):
        return max(map(float, v.get('scores') or ['0']))
    cols = ['score annoncé', 'votes', 'min', 'appels', 'réflexion', 'temp', 'outils', 'LoRA', 'sous-agents', 'prompt', 'notebook']
    L = [f"# Veille publique ({datetime.now(timezone.utc):%F %H:%M} UTC) : {len(idx)} notebooks, {len(nouveaux)} nouveaux ou relancés (★)",
         '', 'Base pub024 : 8 min, 28 appels, réflexion 4096, temp 0.2. Les écarts à cette base sont les pistes à vérifier.', '',
         '| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for ref, v in sorted(idx.items(), key=lambda kv: (-best(kv[1]), kv[0])):
        L.append('| ' + ' | '.join([
            ('★ ' if v.get('nouveau') else '') + ' / '.join(v.get('scores') or []), v.get('votes', ''), v.get('min', ''),
            v.get('calls', ''), v.get('thinking', ''), v.get('temp', ''), v.get('tools', '')[:60], v.get('lora', ''),
            v.get('sub_agents', ''), v.get('prompt', '') or v.get('zip', ''), f"[{ref}](https://www.kaggle.com/code/{ref})"]) + ' |')
    lora = [r for r, v in idx.items() if v.get('lora')]
    L += ['', f"**Notebooks publics avec LoRA : {len(lora)}** " + ', '.join(lora)]
    (ROOT / 'research' / 'VEILLE.md').write_text('\n'.join(L) + '\n')
    print(f'{len(idx)} notebooks, {len(nouveaux)} nouveaux ; LoRA : {len(lora)}')


if __name__ == '__main__':
    main()
