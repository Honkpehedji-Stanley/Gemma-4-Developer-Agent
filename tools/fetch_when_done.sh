#!/bin/bash
# Attend la fin d'un kernel d'évaluation et rapatrie ses résultats dans kaggle/runs/<nom>.
# Usage : tools/fetch_when_done.sh <slug sans le préfixe g4eval-> 
cd "$(dirname "$0")/.."
K=stanleyhonkpehedji/${PREFIX:-g4eval-}$1
sleep 120
while ! uvx --with six kaggle kernels status $K 2>&1 | grep -qE 'Status\.(COMPLETE|ERROR|CANCEL)'; do sleep 300; done
rm -rf kaggle/runs/$1; mkdir -p kaggle/runs/$1
for i in 1 2 3; do timeout 1200 uvx --with six kaggle kernels output $K -p kaggle/runs/$1 >/dev/null 2>&1 && break; done
echo "$1 $(uvx --with six kaggle kernels status $K 2>&1 | tail -1) $(date -u)"
