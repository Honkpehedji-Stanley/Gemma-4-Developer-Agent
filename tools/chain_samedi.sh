#!/bin/bash
# Samedi (retour du quota) : professeur gpt-oss, puis entraînement self1. Une seule session L4 à la fois.
cd "$(dirname "$0")/.."
tools/push_when_quota.sh kaggle/out/g4eval-teach94
sleep 120
tools/fetch_when_done.sh teach94
tools/push_when_quota.sh kaggle/out/g4train-self1
sleep 120
PREFIX=g4train- tools/fetch_when_done.sh self1
