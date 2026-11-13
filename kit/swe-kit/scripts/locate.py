"""Rank the source files and functions of /workspace most relevant to an issue.

Usage: locate.py "<words, identifiers, error messages from the issue>"
Prints the best files, the best functions/classes with line ranges, and exact matches
of the most specific terms. Standard library only; runs in well under a second on
repositories of a few thousand files.
"""

from __future__ import annotations

import ast
import math
import os
import re
import sys
from collections import Counter


def _find_root() -> str:
    """Le dépôt de la tâche. ADK exécute les scripts de skill depuis un dossier temporaire (os.chdir),
    donc le répertoire courant n'est PAS le dépôt : /workspace en Docker ; dans le bac à sable `subprocess`
    de Kaggle, `PWD` (posé par le shell, inchangé par chdir) ou le dossier `workspace` voisin du `tmp`."""
    env = os.environ.get('SWE_KIT_ROOT')
    if env:
        return env
    cands = [os.environ.get('PWD', ''), '/workspace', os.getcwd()]
    here = os.path.abspath(os.getcwd())
    while here != '/':
        cands.append(os.path.join(here, 'workspace'))
        cands.append(here)
        here = os.path.dirname(here)
    for cand in cands:
        if cand and os.path.isdir(os.path.join(cand, '.git')):
            return cand
    return os.environ.get('PWD') or os.getcwd()


ROOT = _find_root()
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'build', 'dist', '.venv', 'venv', 'site-packages',
             '.tox', '.mypy_cache', '.pytest_cache', 'docs', 'docs_src', 'tests', 'test', 'testing',
             'benchmarks', 'examples', 'scripts'}
STOP = set('''a an and are as at be been but by can could did do does for from has have how if in into is
it its make may more must new no not of on or our out should so some such than that the their them then
there these they this to too up use used using via was we were what when where which while who why will
with would you your issue bug fix fixes fixed error errors add adds added support allow allows when
feature should wrong instead does doesn work works working case cases value values return returns
returned get set default option options able also like just only one two need needs want same
https http github com www pull request'''.split())
MAX_FILES = 6000
MAX_BYTES = 400_000


def split_ident(tok: str) -> list[str]:
    parts = re.findall(r'[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+', tok)
    return [p.lower() for p in parts if len(p) > 1]


def tokens(text: str) -> list[str]:
    out = []
    for tok in re.findall(r'[A-Za-z_][A-Za-z0-9_]*', text):
        low = tok.lower()
        if len(low) > 2 and low not in STOP:
            out.append(low)
        sub = split_ident(tok)
        if len(sub) > 1:
            out.extend(s for s in sub if len(s) > 2 and s not in STOP)
    return out


def source_files(root: str) -> list[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in filenames:
            if fn.endswith('.py') and not fn.startswith('test_') and not fn.endswith('_test.py') \
                    and fn not in ('conftest.py', 'setup.py', 'noxfile.py'):
                files.append(os.path.join(dirpath, fn))
                if len(files) >= MAX_FILES:
                    return files
    return files


def definitions(src: str):
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return []
    defs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(node, 'end_lineno', node.lineno)
            defs.append((node.name, node.lineno, end, type(node).__name__))
    return defs


def main() -> int:
    query = ' '.join(sys.argv[1:]).strip()
    if not query:
        print('usage: locate.py "<issue words, identifiers, error messages>"')
        return 2
    q_tokens = Counter(tokens(query))
    exact_terms = {t for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', query)
                   if ('_' in t or re.search(r'[a-z][A-Z]', t) or t.isupper()) and t.lower() not in STOP}
    exact_terms |= {m for m in re.findall(r'["`\']([^"`\'\n]{4,60})["`\']', query)}

    docs = {}
    for path in source_files(ROOT):
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            with open(path, encoding='utf-8', errors='ignore') as fh:
                docs[path] = fh.read()
        except OSError:
            continue
    if not docs:
        print('no python source files found under', ROOT)
        return 1

    tf = {p: Counter(tokens(t)) for p, t in docs.items()}
    df = Counter()
    for c in tf.values():
        df.update(c.keys())
    n = len(tf)
    avg_len = sum(sum(c.values()) for c in tf.values()) / n

    def bm25(counts: Counter, length: int) -> float:
        s = 0.0
        for term, qf in q_tokens.items():
            f = counts.get(term, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            s += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * length / avg_len)) * min(qf, 2)
        return s

    file_scores = {}
    for p, c in tf.items():
        s = bm25(c, sum(c.values()))
        rel = os.path.relpath(p, ROOT)
        path_toks = set(tokens(rel.replace('/', ' ').replace('.py', '')))
        s += 1.5 * sum(1 for t in q_tokens if t in path_toks)
        s += 3.0 * sum(1 for t in exact_terms if t in docs[p])
        file_scores[p] = s
    top_files = [p for p, s in sorted(file_scores.items(), key=lambda kv: -kv[1])[:8] if s > 0]

    print('## Most relevant source files')
    for p in top_files:
        print(f'{file_scores[p]:6.1f}  {os.path.relpath(p, ROOT)}')

    scored_defs = []
    for p in top_files[:6]:
        lines = docs[p].splitlines()
        for name, start, end, kind in definitions(docs[p]):
            body = '\n'.join(lines[start - 1:min(end, start + 120)])
            c = Counter(tokens(body))
            s = bm25(c, max(sum(c.values()), 1))
            name_toks = set(tokens(name))
            s += 2.5 * sum(1 for t in q_tokens if t in name_toks)
            s += 4.0 * sum(1 for t in exact_terms if t in body)
            if kind == 'ClassDef':
                s *= 0.6  # a class body contains all its methods; prefer the specific method
            scored_defs.append((s, os.path.relpath(p, ROOT), name, start, end, kind))
    scored_defs.sort(key=lambda d: -d[0])
    print('\n## Most relevant definitions (file:start-end)')
    for s, rel, name, start, end, kind in scored_defs[:12]:
        if s <= 0:
            break
        label = 'class' if kind == 'ClassDef' else 'def'
        print(f'{s:6.1f}  {rel}:{start}-{end}  {label} {name}')

    if exact_terms:
        print('\n## Exact matches of specific terms')
        shown = 0
        for p in sorted(docs, key=lambda q: -file_scores[q]):
            for i, line in enumerate(docs[p].splitlines(), 1):
                if any(t in line for t in exact_terms):
                    print(f'{os.path.relpath(p, ROOT)}:{i}: {line.strip()[:140]}')
                    shown += 1
                    if shown >= 15:
                        break
            if shown >= 15:
                break
        if not shown:
            print('(none in source files)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
