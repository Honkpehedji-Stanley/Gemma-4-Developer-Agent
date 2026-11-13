#!/usr/bin/env python3
"""Environnements de test par tâche, pour reproduire localement le cache privé de Kaggle.

Problème : les roues publiques contiennent jusqu'à 60 versions d'un même paquet (starlette...),
dépaquetées en vrac par le harnais ; il manque aussi des dépendances de test (inline_snapshot,
dirty_equals, python-multipart...). Résultat : les correctifs de référence échouent.

Solution : pour chaque tâche, on construit sur l'hôte (qui a Internet) un site-packages Python 3.13
à partir des fichiers de dépendances du dépôt au base_commit :
  - uv.lock     → `uv export --frozen` (versions exactes, groupe `tests`) ;
  - poetry.lock → toutes les versions verrouillées ;
  - sinon       → pyproject/requirements*/setup.py résolus avec --exclude-newer = date de la tâche.
L'environnement est archivé dans build/envs/<clé>.tar, où la clé est l'empreinte des fichiers de
dépendances : le conteneur la recalcule lui-même (voir KEY_SCRIPT), sans connaître la tâche.

Usage : .venv/bin/python tools/task_envs.py [--task-ids ...] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
ENVS = ROOT / 'build' / 'envs'

KEY_FILES = (
    'pyproject.toml', 'uv.lock', 'poetry.lock', 'setup.py', 'setup.cfg',
    'requirements.txt', 'requirements-dev.txt', 'requirements-tests.txt',
)
PY = '3.13'
PLATFORM = 'x86_64-manylinux_2_28'

# Même calcul d'empreinte, exécuté dans le conteneur (python3 -S, sans dépendances).
KEY_SCRIPT = (
    "import hashlib,pathlib;h=hashlib.sha256()\n"
    f"for n in {KEY_FILES!r}:\n"
    " p=pathlib.Path('/workspace')/n;h.update(n.encode()+b'\\0'+(p.read_bytes() if p.is_file() else b'<absent>')+b'\\0')\n"
    "print(h.hexdigest()[:16])"
)


def env_key(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for n in KEY_FILES:
        h.update(n.encode() + b'\0' + files.get(n, b'<absent>') + b'\0')
    return h.hexdigest()[:16]


def read_dep_files(snapshot: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with tarfile.open(snapshot, 'r:gz') as tf:
        for m in tf:
            name = m.name[2:] if m.name.startswith('./') else m.name
            if name in KEY_FILES and m.isfile():
                out[name] = tf.extractfile(m).read()
    return out


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


COMPILED_RECENT = ('markupsafe', 'pyyaml', 'cffi', 'coverage', 'brotli', 'brotlicffi', 'gevent',
                   'greenlet', 'cryptography', 'pyzmq', 'zope-interface', 'charset-normalizer',
                   'rpds-py', 'pydantic-core', 'lxml', 'psutil', 'ujson', 'orjson', 'msgpack', 'pillow',
                   'numpy', 'regex', 'multidict', 'yarl', 'frozenlist', 'aiohttp', 'uvloop', 'httptools',
                   'watchfiles', 'websockets', 'simplejson', 'mypy', 'setproctitle', 'wrapt')


# Contraintes ajoutées par dépôt, justifiées par la calibration gold.
REPO_CONSTRAINTS = {
    # httpbin 0.10 importe werkzeug.http.parse_authorization_header, supprimé dans werkzeug 3 ;
    # les roues publiques de la compétition fournissent werkzeug 2.3.8.
    'psf/requests': ['werkzeug<3'],
}


def uv_install(target: Path, reqs: list[str], *, no_deps: bool, exclude_newer: str | None,
               recent_packages: tuple[str, ...] = ()) -> tuple[bool, str]:
    req_file = target.parent / f'{target.name}.reqs.txt'
    req_file.write_text('\n'.join(reqs) + '\n')
    cmd = ['uv', 'pip', 'install', '--quiet', '--target', str(target), '--python-version', PY,
           '--python-platform', PLATFORM, '-r', str(req_file)]
    if no_deps:
        cmd.append('--no-deps')
    if exclude_newer:
        cmd += ['--exclude-newer', exclude_newer]
        for pkg in recent_packages:
            cmd += ['--exclude-newer-package', f'{pkg}=2100-01-01T00:00:00Z']
    r = run(cmd)
    return r.returncode == 0, (r.stderr or '')[-2000:]


def install_pinned(target: Path, pins: list[str], exclude_newer: str) -> list[str]:
    """Installe des versions exactes ; un paquet qui échoue (pas de roue 3.13...) est remplacé
    par la version la plus récente disponible à la date de la tâche. Renvoie les remplacements."""
    ok, _ = uv_install(target, pins, no_deps=True, exclude_newer=None)
    if ok:
        return []
    replaced = []
    for pin in pins:
        ok, _ = uv_install(target, [pin], no_deps=True, exclude_newer=None)
        if not ok:
            name = re.split(r'[=<>!~ ;\[]', pin, 1)[0]
            if uv_install(target, [name], no_deps=True, exclude_newer=exclude_newer)[0]:
                replaced.append(f'{pin} -> {name} (date)')
            elif uv_install(target, [name], no_deps=True, exclude_newer=None)[0]:
                replaced.append(f'{pin} -> {name} (récente)')
            else:
                replaced.append(f'{pin} -> ABSENT')
    return replaced


def pins_from_uv_lock(work: Path) -> list[str]:
    for extra in (['--no-default-groups', '--group', 'tests'], ['--no-default-groups'], []):
        r = run(['uv', 'export', '--frozen', '--no-emit-project', '--no-hashes', '--no-header',
                 '--no-annotate', '--all-extras', *extra], cwd=work)
        if r.returncode == 0:
            return [l.strip() for l in r.stdout.splitlines()
                    if l.strip() and not l.startswith(('#', '-e', '.'))]
    raise RuntimeError(f'uv export a échoué : {r.stderr[-500:]}')


def pins_from_poetry_lock(data: bytes) -> list[str]:
    lock = tomllib.loads(data.decode())
    return [f"{p['name']}=={p['version']}" for p in lock.get('package', [])]


def loose_requirements(files: dict[str, bytes]) -> list[str]:
    reqs: list[str] = []
    if 'pyproject.toml' in files:
        py = tomllib.loads(files['pyproject.toml'].decode())
        proj = py.get('project', {})
        reqs += proj.get('dependencies', [])
        for group in proj.get('optional-dependencies', {}).values():
            reqs += group
        for group in py.get('dependency-groups', {}).values():
            reqs += [g for g in group if isinstance(g, str)]
    for name in ('requirements.txt', 'requirements-dev.txt', 'requirements-tests.txt'):
        for line in files.get(name, b'').decode().splitlines():
            line = line.split('#', 1)[0].strip()
            if line and not line.startswith('-'):
                reqs.append(line)
    if 'setup.py' in files:
        src = files['setup.py'].decode(errors='ignore')
        for block in re.findall(r'(?:requires|install_requires)\s*=\s*\[(.*?)\]', src, re.S):
            reqs += re.findall(r'["\']([^"\']+)["\']', block)
    # Le dépôt lui-même est installé en editable par le harnais.
    return sorted({r for r in reqs if not r.lower().startswith(('requests[', 'rich[', 'httpx[', 'fastapi['))})


def build_env(task: dict, files: dict[str, bytes], key: str) -> dict:
    exclude_newer = task['created_at']
    target = ENVS / key
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    info: dict = {'key': key, 'instance_id': task['instance_id'], 'source': None, 'replaced': []}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for n, b in files.items():
            (work / n).write_bytes(b)
        if 'uv.lock' in files:
            info['source'] = 'uv.lock'
            info['replaced'] = install_pinned(target, pins_from_uv_lock(work), exclude_newer)
        elif 'poetry.lock' in files:
            info['source'] = 'poetry.lock'
            info['replaced'] = install_pinned(target, pins_from_poetry_lock(files['poetry.lock']), exclude_newer)
        else:
            info['source'] = 'résolution datée'
            reqs = loose_requirements(files) + REPO_CONSTRAINTS.get(task['repo'], [])
            ok, err = uv_install(target, reqs, no_deps=False, exclude_newer=exclude_newer)
            if not ok:
                # Paquets compilés sans roue 3.13 à la date de la tâche (markupsafe 2.1.x...) :
                # on les laisse récents, le reste reste daté.
                info['source'] = 'résolution datée, compilés récents'
                shutil.rmtree(target, ignore_errors=True)
                target.mkdir(parents=True)
                ok, err = uv_install(target, reqs, no_deps=False, exclude_newer=exclude_newer,
                                     recent_packages=COMPILED_RECENT)
            if not ok:
                info['source'] = 'résolution récente (datée impossible)'
                shutil.rmtree(target, ignore_errors=True)
                target.mkdir(parents=True)
                ok, err = uv_install(target, reqs, no_deps=False, exclude_newer=None)
            if not ok:
                raise RuntimeError(f'résolution impossible : {err}')
    # pytest et ses greffons de l'image restent ceux du harnais : on n'écrase que ce que le dépôt fixe.
    for junk in ('bin', '__pycache__'):
        shutil.rmtree(target / junk, ignore_errors=True)
    dists = sorted(re.sub(r'-[^-]+\.dist-info$', '', p.name) for p in target.glob('*.dist-info'))
    info['dists'] = dists
    with tarfile.open(ENVS / f'{key}.tar', 'w') as tf:
        tf.add(target, arcname='.')
    (ENVS / f'{key}.json').write_text(json.dumps(info, indent=1))
    shutil.rmtree(target)
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--task-ids', nargs='+')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    ENVS.mkdir(parents=True, exist_ok=True)
    tasks = [json.loads(l) for l in open(DATA / 'tasks.jsonl')]
    if args.task_ids:
        tasks = [t for t in tasks if t['instance_id'] in set(args.task_ids)]
    index_path = ENVS / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for t in tasks:
        iid = t['instance_id']
        snap = DATA / 'snapshots' / f'{iid}.tgz'
        if not snap.exists():
            print(f'{iid}: snapshot absent', flush=True)
            continue
        files = read_dep_files(snap)
        key = env_key(files)
        index[iid] = key
        if (ENVS / f'{key}.tar').exists() and not args.force:
            print(f'{iid}: {key} déjà construit', flush=True)
            continue
        try:
            info = build_env(t, files, key)
            print(f"{iid}: {key} {info['source']} {len(info['dists'])} paquets, remplacés={info['replaced']}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f'{iid}: ÉCHEC {e}', flush=True)
        index_path.write_text(json.dumps(index, indent=1, sort_keys=True))
    index_path.write_text(json.dumps(index, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
