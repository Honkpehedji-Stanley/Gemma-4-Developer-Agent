#!/bin/bash
# Envoie une soumission dès que plus aucune n'est en attente (une seule autorisée à la fois).
# Usage : tools/submit_when_free.sh <version du kernel g4-submit> "<message>"
cd "$(dirname "$0")/.."
while uvx --with six kaggle competitions submissions gemma-4-developer-agent 2>/dev/null | grep -q 'PENDING'; do sleep 900; done
date -u
uvx --with six kaggle competitions submissions gemma-4-developer-agent 2>&1 | sed -n 3,4p
uvx --with six kaggle competitions submit gemma-4-developer-agent -k stanleyhonkpehedji/g4-submit -v "$1" -f submission.zip -m "$2" 2>&1 | tail -2
