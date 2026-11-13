"""Print the source of a function, method or class by name, with line numbers.

Usage: show.py <name> [<name> ...]   e.g. show.py cell_len   or   show.py Console.is_terminal
Searches source files under /workspace (tests excluded unless the name starts with test_).
Shows at most 3 matches per name and 120 lines per match.
"""

from __future__ import annotations

import ast
import os
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
MAX_LINES = 120


def iter_py(include_tests: bool):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')
                       and (include_tests or d not in ('tests', 'test', 'testing'))]
        for fn in filenames:
            if fn.endswith('.py'):
                yield os.path.join(dirpath, fn)


def find(name: str):
    parts = name.split('.')
    target, owner = parts[-1], (parts[-2] if len(parts) > 1 else None)
    hits = []
    for path in iter_py(include_tests=target.startswith('test_')):
        try:
            src = open(path, encoding='utf-8', errors='ignore').read()
            tree = ast.parse(src)
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and owner and node.name == owner:
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and sub.name == target:
                        hits.append((path, sub, src))
            elif not owner and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and node.name == target:
                hits.append((path, node, src))
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: show.py <name> [<name> ...]')
        return 2
    for name in sys.argv[1:]:
        hits = find(name)
        if not hits:
            print(f'## {name}: not found (try a shorter name, or Class.method)')
            continue
        for path, node, src in hits[:3]:
            lines = src.splitlines()
            start = min([d.lineno for d in getattr(node, 'decorator_list', [])] + [node.lineno])
            end = getattr(node, 'end_lineno', node.lineno)
            stop = min(end, start + MAX_LINES - 1)
            print(f'## {os.path.relpath(path, ROOT)}:{start}-{end}')
            for i in range(start, stop + 1):
                print(f'{i:5d}  {lines[i - 1]}')
            if stop < end:
                print(f'      ... {end - stop} more lines: use read_file with start_line={stop + 1}')
        if len(hits) > 3:
            print(f'({len(hits) - 3} more matches not shown)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
