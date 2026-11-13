#!/usr/bin/env python3
"""Génère un kernel Kaggle d'entraînement LoRA (kaggle/train_lora.py + données embarquées), prêt à pousser.

Le kernel installe les roues du wheelhouse (transformers, peft, bitsandbytes, accelerate), entraîne sur les poids
QAT non compressés et écrit l'adaptateur dans /kaggle/working/adapters/<nom>/.

Exemple :
  python kaggle/build_train_kernel.py --data build/sft/train.jsonl --name swe_lora --slug g4train-v1 --max-steps 2
  uvx --with six kaggle kernels push -p kaggle/out/g4train-v1
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
from pathlib import Path

from build_kernel import OFFICIAL_GPU_IMAGE, ROOT, USER

BASE_MODEL = 'google/gemma-4/Transformers/gemma-4-31b-it-qat-q4_0-unquantized/2'

KERNEL = r'''# Entraînement LoRA Gemma 4 31B — généré par kaggle/build_train_kernel.py, ne pas éditer.
import base64, glob, gzip, os, subprocess, sys, time
from pathlib import Path
T0 = time.time()
ARGS = __ARGS__
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
gpus = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True).stdout
print(gpus, flush=True)
if gpus.count('L4') < 4:  # Kaggle bascule sur 2×T4 quand la machine L4 est prise : inutile, on s'arrête tout de suite
    sys.exit('pas de 4×L4')
wh = [p for p in glob.glob('/kaggle/input/**/gemma-4-developer-agent-wheelhouse/*.whl', recursive=True)]
need = ('transformers-', 'peft-', 'bitsandbytes-', 'accelerate-', 'compressed_tensors-', 'safetensors-', 'tokenizers-',
        'huggingface_hub-')
sel = [w for w in wh if os.path.basename(w).startswith(need)]
print('roues :', [os.path.basename(w) for w in sel], flush=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', *sel], check=True)
model = next(Path(p).parent for p in glob.glob('/kaggle/input/models/**/gemma-4-31b-it-qat-q4_0-unquantized/**/config.json', recursive=True))
print('modèle :', model, flush=True)
Path('/kaggle/working/train_lora.py').write_bytes(gzip.decompress(base64.b64decode("""__SCRIPT__""")))
Path('/kaggle/working/train.jsonl').write_bytes(gzip.decompress(base64.b64decode("""__DATA__""")))
r = subprocess.run([sys.executable, '/kaggle/working/train_lora.py', '--data', '/kaggle/working/train.jsonl',
                    '--model', str(model), '--out', '/kaggle/working/adapters/' + ARGS['name'], *ARGS['extra']])
subprocess.run(['nvidia-smi'])
print(f'fin ({(time.time() - T0) / 60:.0f} min), code {r.returncode}', flush=True)
'''


def b64gz(p: Path) -> str:
    return base64.b64encode(gzip.compress(p.read_bytes(), 9)).decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--name', default='swe_lora', help="nom de l'adaptateur (dossier adapters/<nom>)")
    ap.add_argument('--slug', required=True)
    ap.add_argument('extra', nargs=argparse.REMAINDER, help='arguments passés à train_lora.py (après --)')
    args = ap.parse_args()
    extra = [a for a in args.extra if a != '--']

    src = KERNEL.replace('__ARGS__', repr({'name': args.name, 'extra': extra}))
    src = src.replace('__SCRIPT__', b64gz(ROOT / 'kaggle' / 'train_lora.py')).replace('__DATA__', b64gz(args.data))
    out = ROOT / 'kaggle' / 'out' / args.slug
    out.mkdir(parents=True, exist_ok=True)
    (out / 'script.py').write_text(src)
    meta = {
        'id': f'{USER}/{args.slug}', 'title': args.slug, 'code_file': 'script.py', 'language': 'python',
        'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_tpu': False,
        'enable_internet': False, 'dataset_sources': ['metric/gemma-4-developer-agent-wheelhouse'],
        # Sans la source concours, Kaggle donne 2×T4 au lieu de 4×L4.
        'competition_sources': ['gemma-4-developer-agent'], 'kernel_sources': [], 'model_sources': [BASE_MODEL],
        'machine_shape': 'NvidiaL4', 'docker_image': OFFICIAL_GPU_IMAGE,
    }
    (out / 'kernel-metadata.json').write_text(json.dumps(meta, indent=2))
    print(out, f'{(out / "script.py").stat().st_size / 1e6:.1f} Mo')


if __name__ == '__main__':
    main()
