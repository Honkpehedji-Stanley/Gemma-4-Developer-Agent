#!/bin/bash
# Télécharge les gros fichiers de la compétition dans data/, reprend là où il s'est arrêté.
cd ~/Téléchargements/gemma4-agent/data
while read f; do
  [ -s "$f" ] && continue
  d=$(dirname "$f"); mkdir -p "$d"
  for try in 1 2 3; do
    uvx kaggle competitions download gemma-4-developer-agent -f "$f" -p "$d" -q >/dev/null 2>&1
    z="$d/$(basename "$f").zip"
    if [ -s "$z" ]; then (cd "$d" && unzip -oq "$(basename "$z")" && rm "$(basename "$z")"); fi
    [ -s "$f" ] && break
  done
  [ -s "$f" ] && echo "OK $f" || echo "FAIL $f"
done < ../logs/download_list_wheels.txt
echo DONE
