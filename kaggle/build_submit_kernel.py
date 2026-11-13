#!/usr/bin/env python3
"""Génère le kernel g4-submit qui écrit /kaggle/working/submission.zip.

Les poids LoRA (centaines de Mo) ne passent pas dans le script : avec --adapter-kernel, ils sont repris de la sortie
du kernel d'entraînement (kernel_sources) et ajoutés au zip sous adapters/<nom>/.
Usage : python kaggle/build_submit_kernel.py --submission-dir submissions/lora1 [--adapter-kernel g4train-self1]
        uvx --with six kaggle kernels push -p kaggle/out/g4-submit
"""

from __future__ import annotations

import argparse
import json

from build_kernel import ROOT, USER, zip_submission

SCRIPT = r'''# Écrit submission.zip (agent déclaratif) dans /kaggle/working pour la soumission.
import base64, io, zipfile
from pathlib import Path
data = base64.b64decode("__ZIP__")
zin = zipfile.ZipFile(io.BytesIO(data))
with zipfile.ZipFile('/kaggle/working/submission.zip', 'w', zipfile.ZIP_DEFLATED) as zout:
    for n in zin.namelist():
        zout.writestr(n, zin.read(n))
        if n.startswith('adapters/') and n.endswith('/adapter_config.json'):
            name = n.split('/')[1]
            w = next(p for p in Path('/kaggle/input').rglob('adapter_model.safetensors') if p.parent.name == name)
            zout.write(w, f'adapters/{name}/adapter_model.safetensors')
            print('adaptateur', name, '<-', w, w.stat().st_size)
z = zipfile.ZipFile('/kaggle/working/submission.zip')
print([(i.filename, i.file_size) for i in z.infolist()])
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--submission-dir', required=True)
    ap.add_argument('--adapter-kernel')
    args = ap.parse_args()
    out = ROOT / 'kaggle' / 'out' / 'g4-submit'
    out.mkdir(parents=True, exist_ok=True)
    zip_b64 = zip_submission(ROOT / args.submission_dir, skip_weights=bool(args.adapter_kernel))
    (out / 'script.py').write_text(SCRIPT.replace('__ZIP__', zip_b64))
    meta = {
        'id': f'{USER}/g4-submit', 'title': 'g4-submit', 'code_file': 'script.py', 'language': 'python',
        'kernel_type': 'script', 'is_private': True, 'enable_gpu': False, 'enable_tpu': False,
        'enable_internet': False, 'dataset_sources': [], 'competition_sources': ['gemma-4-developer-agent'],
        'kernel_sources': [f'{USER}/{args.adapter_kernel}'] if args.adapter_kernel else [], 'model_sources': [],
    }
    (out / 'kernel-metadata.json').write_text(json.dumps(meta, indent=2))
    print(out)


if __name__ == '__main__':
    main()
