#!/usr/bin/env python3
"""Génère un kernel Kaggle d'évaluation prêt à pousser (kaggle kernels push -p <dossier>).

  gold / empty : CPU, sans modèle, ne consomme pas de quota GPU.
  agent        : machine NvidiaL4 + modèle QAT, la soumission (--submission-dir) est embarquée.

Exemples :
  python kaggle/build_kernel.py --mode gold
  python kaggle/build_kernel.py --mode agent --submission-dir submissions/sample_nolora --task-ids fastapi_14258
  uvx kaggle kernels push -p kaggle/out/g4eval-gold
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = 'stanleyhonkpehedji'
OFFICIAL_GPU_IMAGE = ('gcr.io/kaggle-private-byod/python@sha256:'
                      '37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461')


def zip_submission(d: Path, skip_weights: bool = False) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(d.rglob('*')):
            if p.is_file() and not (skip_weights and p.suffix == '.safetensors'):
                zf.write(p, p.relative_to(d).as_posix())
    return base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['gold', 'empty', 'agent'], required=True)
    ap.add_argument('--submission-dir', type=Path)
    ap.add_argument('--task-ids', nargs='+')
    ap.add_argument('--concurrency', type=int, default=2)
    ap.add_argument('--machine', default='NvidiaL4',
                    help="mode agent : NvidiaL4 (conditions de notation) ou NvidiaTeslaT4 (2×T4, file plus courte, plus lent)")
    ap.add_argument('--teacher', action='store_true',
                    help="mode agent : servir gpt-oss-120b (Apache 2.0) au lieu de Gemma, pour générer des trajectoires")
    ap.add_argument('--adapter-kernel', help="kernel d'entraînement dont la sortie fournit les poids LoRA (g4train-...)")
    ap.add_argument('--slug', help='nom du kernel (défaut : g4eval-<mode>)')
    args = ap.parse_args()

    slug = args.slug or f'g4eval-{args.mode}'
    cfg = {'mode': args.mode, 'teacher': args.teacher, 'task_ids': args.task_ids, 'concurrency': args.concurrency,
           'submission': str(args.submission_dir) if args.submission_dir else 'sample_submission'}
    sub_b64 = zip_submission(args.submission_dir, bool(args.adapter_kernel)) if args.submission_dir else ''

    src = (ROOT / 'kaggle' / 'eval_kernel_template.py').read_text()
    src = src.replace('__CONFIG__', json.dumps(cfg)).replace('__SUBMISSION_ZIP_B64__', sub_b64)

    out = ROOT / 'kaggle' / 'out' / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / 'script.py').write_text(src)
    gpu = args.mode == 'agent'
    meta = {
        'id': f'{USER}/{slug}',
        'title': slug,
        'code_file': 'script.py',
        'language': 'python',
        'kernel_type': 'script',
        'is_private': True,
        'enable_gpu': gpu,
        'enable_tpu': False,
        'enable_internet': False,
        'dataset_sources': ['metric/gemma-4-developer-agent-wheelhouse'],
        'competition_sources': ['gemma-4-developer-agent'],
        'kernel_sources': [],
        'model_sources': ['google/gemma-4/Other/gemma-4-31b-it-qat-w4a16-ct/2'] if gpu else [],
    }
    if args.adapter_kernel:
        meta['kernel_sources'] = [f'{USER}/{args.adapter_kernel}']
    if args.teacher:
        # Kaggle refuse internet sur GPU : l'encodage o200k d'openai_harmony vient d'un dataset.
        meta['model_sources'] = ['danielhanchen/gpt-oss-120b/transformers/default/1']
        meta['dataset_sources'].append(f'{USER}/tiktoken-encodings')
    if gpu:
        meta['machine_shape'] = args.machine
        # Image du notebook officiel (Python 3.12) : les roues du wheelhouse sont en cp312,
        # l'image GPU par défaut est en 3.13 et l'installation échoue.
        meta['docker_image'] = OFFICIAL_GPU_IMAGE
    (out / 'kernel-metadata.json').write_text(json.dumps(meta, indent=2))
    print(out)


if __name__ == '__main__':
    main()
