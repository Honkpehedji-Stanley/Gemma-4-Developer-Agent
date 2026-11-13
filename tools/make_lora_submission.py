#!/usr/bin/env python3
"""Crée une soumission avec adaptateur LoRA : copie d'une soumission de base + adapters/<nom>/ + `adapter: <nom>`.

Vérifie ce que la notation exige : adapter_config.json + .safetensors, rang ≤ 128, total < 3 Gio, noms de poids sous
`base_model.model.model.language_model.` (format de l'exemple officiel, que vLLM Kaggle renomme).
Usage : tools/make_lora_submission.py --base submissions/pub024 --adapter kaggle/runs/self1/adapters/swe_lora --out submissions/lora1
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from safetensors import safe_open


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--adapter', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--name', default='swe_lora')
    args = ap.parse_args()

    cfg = json.loads((args.adapter / 'adapter_config.json').read_text())
    assert cfg['r'] <= 128, cfg['r']
    with safe_open(str(args.adapter / 'adapter_model.safetensors'), 'np') as f:
        keys = list(f.keys())
    bad = [k for k in keys if not k.startswith('base_model.model.model.language_model.layers.')]
    assert not bad, bad[:3]

    shutil.rmtree(args.out, ignore_errors=True)
    shutil.copytree(args.base, args.out)
    dst = args.out / 'adapters' / args.name
    dst.mkdir(parents=True)
    for n in ('adapter_config.json', 'adapter_model.safetensors'):
        shutil.copy(args.adapter / n, dst / n)
    agent = args.out / 'agent.yaml'
    txt = agent.read_text()
    txt = re.sub(r'(?m)^adapter:.*\n', '', txt)
    txt = re.sub(r'(?m)^(model:.*\n)', rf'\1adapter: {args.name}\n', txt, count=1)
    agent.write_text(txt)
    size = sum(p.stat().st_size for p in args.out.rglob('*') if p.is_file())
    assert size < 3 * 2**30, size
    print(f'{args.out} : rang {cfg["r"]}, {len(keys)} tenseurs, {size / 2**20:.0f} Mio')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
