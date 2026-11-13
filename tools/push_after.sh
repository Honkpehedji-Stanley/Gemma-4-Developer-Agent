#!/bin/bash
# Attend la fin d'un kernel Kaggle (la machine L4 n'accepte qu'une session), puis pousse un dossier de kernel.
# Usage : tools/push_after.sh <kernel_attendu> <dossier_a_pousser>
cd "$(dirname "$0")/.."
while ! uvx --with six kaggle kernels status "stanleyhonkpehedji/$1" 2>&1 | grep -qE 'Status\.(COMPLETE|ERROR|CANCEL)'; do sleep 300; done
sleep 60
uvx --with six kaggle kernels push -p "$2"
