#!/bin/bash
# Réessaie de pousser un kernel GPU toutes les 30 min jusqu'au retour du quota hebdomadaire (samedi 00:00 UTC).
# Usage : tools/push_when_quota.sh <dossier_a_pousser>
cd "$(dirname "$0")/.."
until uvx --with six kaggle kernels push -p "$1" 2>&1 | tee -a /dev/stderr | grep -q 'successfully pushed'; do sleep 1800; done
date -u
