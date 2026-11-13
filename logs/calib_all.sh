#!/bin/bash
# Calibration complète de l'instrument : environnements par tâche, puis gold (attendu ~100 %) et empty (attendu ~0 %).
cd ~/Téléchargements/gemma4-agent
.venv/bin/python tools/task_envs.py > logs/task_envs.log 2>&1
echo "ENVS DONE"
rm -rf results/calib_gold results/calib_empty
.venv/bin/python tools/eval_local.py --mode gold  --results-dir results/calib_gold  --concurrency 3 > logs/calib_gold.log 2>&1
echo "GOLD DONE"
.venv/bin/python tools/eval_local.py --mode empty --results-dir results/calib_empty --concurrency 3 > logs/calib_empty.log 2>&1
echo "EMPTY DONE"
