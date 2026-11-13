#!/bin/bash
# build/wheels = roues publiques de la compétition + compléments locaux (vendor/extra_wheels).
# Les compléments comblent les dépendances que le cache privé de Kaggle fournit mais pas les roues publiques
# (détectées par la calibration gold). Liens symboliques : data/ reste intact.
cd "$(dirname "$0")/.."
rm -rf build/wheels && mkdir -p build/wheels
for w in data/wheels/*.whl vendor/extra_wheels/*.whl; do ln -s "$(realpath "$w")" build/wheels/; done
# Le harnais met en cache les roues dépaquetées par nom, pas par contenu : à vider à chaque changement.
rm -rf "${TMPDIR:-/tmp}"/swegemma_sp_cache_v*
ls build/wheels | wc -l
