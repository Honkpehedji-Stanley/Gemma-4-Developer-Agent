"""List existing tests that exercise a name, to learn the expected conventions.

Usage: tests_for.py <name> [<name> ...]   e.g. tests_for.py cell_len   or   tests_for.py include_router
Prints the test files and test functions that mention the name, with the matching lines,
and the command to run them. Shows at most 8 files and 25 lines in total.
"""

from __future__ import annotations

import os
import re
import sys


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
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'build', 'dist', '.venv', 'venv', 'site-packages'}


def test_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in filenames:
            if fn.endswith('.py') and (fn.startswith('test_') or fn.endswith('_test.py')):
                yield os.path.join(dirpath, fn)


def main() -> int:
    names = [n.split('.')[-1] for n in sys.argv[1:] if n.strip()]
    if not names:
        print('usage: tests_for.py <name> [<name> ...]')
        return 2
    pat = re.compile(r'\b(' + '|'.join(map(re.escape, names)) + r')\b')
    results = []
    for path in test_files():
        try:
            lines = open(path, encoding='utf-8', errors='ignore').read().splitlines()
        except OSError:
            continue
        current, hits = None, []
        for i, line in enumerate(lines, 1):
            m = re.match(r'\s*(?:async\s+)?def\s+(test_\w+)', line)
            if m:
                current = m.group(1)
            if pat.search(line):
                hits.append((i, current, line.strip()))
        if hits:
            results.append((len(hits), os.path.relpath(path, ROOT), hits))
    if not results:
        print('no existing test mentions', ', '.join(names))
        return 0
    results.sort(key=lambda r: -r[0])
    shown = 0
    for count, rel, hits in results[:8]:
        funcs = sorted({h[1] for h in hits if h[1]})
        print(f'## {rel}  ({count} lines; tests: {", ".join(funcs[:6])}{" ..." if len(funcs) > 6 else ""})')
        for i, func, text in hits[:5]:
            if shown >= 25:
                break
            print(f'{i:5d}  {text[:150]}')
            shown += 1
    best = results[0]
    funcs = sorted({h[1] for h in best[2] if h[1]})
    k = ' or '.join(funcs[:3])
    print(f'\nrun: python -m pytest {best[1]}' + (f' -k "{k}"' if k else '') + ' -x -q 2>&1 | tail -15')
    return 0


if __name__ == '__main__':
    sys.exit(main())
