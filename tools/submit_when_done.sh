#!/bin/bash
# submit_when_done.sh <version> <message> : attend la fin du kernel g4-submit puis soumet cette version.
cd "$(dirname "$0")/.."
K() { uvx --with six kaggle "$@" 2>&1; }
for i in $(seq 1 400); do
  st=$(K kernels status stanleyhonkpehedji/g4-submit)
  if echo "$st" | grep -q COMPLETE; then
    K competitions submit gemma-4-developer-agent -k stanleyhonkpehedji/g4-submit -v "$1" -f submission.zip -m "$2" | tail -2
    exit 0
  fi
  echo "$st" | grep -qE 'ERROR|CANCEL' && { echo "kernel en échec : $st"; exit 1; }
  sleep 60
done
echo "délai dépassé"; exit 1
