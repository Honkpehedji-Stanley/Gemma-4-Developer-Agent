#!/bin/bash
# Fait avancer la file GPU d'une étape ; à relancer toutes les 15 min (boucle ou cron). Reprend après un redémarrage.
# Étapes (fichiers témoins dans logs/etat/) : professeur teach94, puis entraînement self1.
# Une seule session L4 à la fois : on ne pousse l'étape suivante qu'après la fin (et le rapatriement) de la précédente.
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p logs/etat
exec 9> logs/etat/.verrou
flock -n 9 || exit 0
K() { uvx --with six kaggle "$@" 2>&1; }

# Veille publique quotidienne (notebooks de la compétition → research/VEILLE.md), en arrière-plan, sans le verrou GPU.
j=$(date -u +%F)
if [ ! -f logs/etat/veille.$j ]; then
  date -u > logs/etat/veille.$j
  ( timeout 3000 python3 tools/veille.py >> logs/veille.log 2>&1 ) 9>&- &
fi

# Filet : si aucune soumission du jour à 18:00 UTC, soumettre pub024 (règle : jamais de jour sans soumission).
filet() {
  [ "$(date -u +%H)" -lt 18 ] && return 0
  local j; j=$(date -u +%F)
  [ -f logs/etat/filet.$j.fait ] && return 0
  if K competitions submissions gemma-4-developer-agent | grep -q "$j"; then date -u > logs/etat/filet.$j.fait; return 0; fi
  if [ ! -f logs/etat/filet.$j.pousse ]; then
    python3 kaggle/build_submit_kernel.py --submission-dir submissions/pub024 >> logs/cron_tick.log 2>&1 || return 0
    K kernels push -p kaggle/out/g4-submit | grep -o 'version [0-9]*' | grep -o '[0-9]*' > logs/etat/filet.$j.v
    [ -s logs/etat/filet.$j.v ] && cp logs/etat/filet.$j.v logs/etat/filet.$j.pousse
    return 0
  fi
  if K kernels status stanleyhonkpehedji/g4-submit | grep -q COMPLETE; then
    K competitions submit gemma-4-developer-agent -k stanleyhonkpehedji/g4-submit -v "$(cat logs/etat/filet.$j.pousse)" \
      -f submission.zip -m "filet auto $j : pub024 tel quel (aucune variante prouvée)" >> logs/cron_tick.log
    echo "$(date -u +%FT%T) filet : soumission pub024 envoyée" >> logs/cron_tick.log
  fi
}
filet

etape() {  # etape <nom> <dossier_kernel> <slug> <dossier_sortie>
  local n=$1 dir=$2 slug=$3 outd=$4
  [ -f logs/etat/$n.fini ] && return 0
  if [ ! -f logs/etat/$n.pousse ]; then
    if K kernels push -p "$dir" | tee -a logs/cron_tick.log | grep -q 'successfully pushed'; then
      date -u > logs/etat/$n.pousse
    fi
    return 1
  fi
  local st; st=$(K kernels status "stanleyhonkpehedji/$slug")
  echo "$(date -u +%FT%T) $n $st" >> logs/cron_tick.log
  if echo "$st" | grep -qE 'Status\.(COMPLETE|ERROR|CANCEL)'; then
    mkdir -p "$outd" && timeout 1500 uvx --with six kaggle kernels output "stanleyhonkpehedji/$slug" -p "$outd" >/dev/null 2>&1 \
      && date -u > logs/etat/$n.fini
  fi
  return 1
}

# Ordre : LoRA sur les succès de Gemma (valide toute la chaîne), son éval holdout35, puis le professeur.
# Mesure armI (énoncé répété contre la compaction) sur panel70, comparée à pub024-p70 tâche par tâche.
etape armip70 kaggle/out/g4eval-armi-p70 g4eval-armi-p70 kaggle/runs/armi-p70 || exit 0
etape self1 kaggle/out/g4train-self1 g4train-self1 kaggle/runs/self1 || exit 0
if [ ! -d kaggle/out/g4eval-lora1-h35 ] && [ ! -f logs/etat/lora1h35.fini ]; then
  a=$(dirname "$(find kaggle/runs/self1 -name adapter_model.safetensors | head -1)")
  { uv run --no-project --with safetensors --with numpy python tools/make_lora_submission.py --base submissions/pub024 --adapter "$a" --out submissions/lora1 \
    && python3 kaggle/build_kernel.py --mode agent --submission-dir submissions/lora1 --adapter-kernel g4train-self1 \
         --concurrency 1 --slug g4eval-lora1-h35 --task-ids $(cat kaggle/panel_holdout35.txt); } >> logs/cron_tick.log 2>&1 \
    || { echo "$(date -u +%FT%T) ECHEC préparation lora1, on passe au professeur" >> logs/cron_tick.log; date -u > logs/etat/lora1h35.fini; }
fi
etape lora1h35 kaggle/out/g4eval-lora1-h35 g4eval-lora1-h35 kaggle/runs/lora1-h35 || exit 0
etape teach94 kaggle/out/g4eval-teach94 g4eval-teach94 kaggle/runs/teach94 || exit 0
etape armjp70 kaggle/out/g4eval-armj-p70 g4eval-armj-p70 kaggle/runs/armj-p70 || exit 0
