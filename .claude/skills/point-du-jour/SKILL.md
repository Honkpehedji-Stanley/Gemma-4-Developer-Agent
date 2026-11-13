---
name: point-du-jour
description: Routine quotidienne de la compétition Gemma 4 Developer Agent — état GPU/boucle, notes, veille publique, décision de soumission fondée sur une preuve. À lancer au début de chaque session et dès que l'utilisateur demande « où en est-on ».
---

# Point du jour (répondre en français)

1. **Boucle et file GPU** : `ps -eo pid,args | grep "[w]hile true; do tools/cron_tick"` (relancer si absente :
   `setsid nohup bash -c 'while true; do tools/cron_tick.sh; sleep 900; done' >/dev/null 2>&1 &`) ;
   `tail -5 logs/cron_tick.log ; ls logs/etat/`. Jamais `pkill -f`/`pgrep -f`.
2. **Notes** : `uvx --with six kaggle competitions submissions gemma-4-developer-agent | head -5`. Mettre à jour
   le tableau des notes dans notes/JOURNAL.md.
3. **Veille publique** : lire `research/VEILLE.md` (rafraîchi chaque jour par la boucle ; sinon `python3 tools/veille.py`).
   Pour chaque ligne ★ (nouvelle) : qu'est-ce qui diffère de pub024 ? un score annoncé répété ? un LoRA ?
   Lire le notebook dans `research/veille/<auteur>__<slug>/` si un écart est accompagné d'un score ≥ 0,20.
   Les discussions ne sont pas lisibles automatiquement : demander à l'utilisateur de coller les sujets importants.
4. **Résultats locaux** : comparer toute éval terminée (kaggle/runs/*) à la base sur les MÊMES tâches
   (pub024-p70 pour holdout35 et panel70), tâche par tâche avec `python3 tools/compare_runs.py <base> <variante>` (gains/pertes, compaction), pas seulement le total.
   Attention : armF faisait +5 sur panel70 et a fait 0,15 au LB, donc un gain inférieur à ~7 tâches sur 70 reste fragile.
5. **Décision de soumission** (une par jour, jamais de jour sans) :
   - une variante n'est soumise que si une preuve est écrite AVANT dans JOURNAL.md (mesure locale ≥ base sur
     les mêmes tâches, ou résultat public répété) ;
   - sinon resoumettre pub024 (`submissions/pub024`) ;
   - ne jamais toucher au budget temps/appels (8 min / 28 appels est l'optimum, la limite totale de 12 h est atteinte) ;
   - soumission : `python3 kaggle/build_submit_kernel.py --submission-dir submissions/X [--adapter-kernel g4train-…]`,
     push `kaggle/out/g4-submit`, attendre COMPLETE, vérifier le zip, puis
     `kaggle competitions submit gemma-4-developer-agent -k stanleyhonkpehedji/g4-submit -v N -f submission.zip -m "..."`.
6. **Prochaine étape GPU** : la file doit toujours suivre le chemin le plus court vers le levier principal (LoRA).
   Si une étape a échoué, le corriger tout de suite, sans attendre le tick suivant.
7. Écrire au journal ce qui a été appris ; répondre à l'utilisateur franchement : faits, chiffres, ce qui est fait, ce qui suit.

Sécurité : identifiants uniquement dans ~/.config/gemma4-agent/ ; ne jamais les afficher ni les mettre dans le dépôt, une soumission ou un notebook.
