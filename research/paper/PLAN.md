# Article Paper Track : plan (date limite 2026-11-12 23:59 UTC, 3 000 mots maximum)

## Titre provisoire
Summarized Before It Edits: How Context Compaction Silently Halves a Local Coding Agent's Success, and What a Token Budget Can Do About It

## Thèse
Les agents de code locaux tournent avec de petites fenêtres de contexte et donc avec une compaction (résumé) de l'historique.
Dans le harnais officiel (ADK EventsCompactionConfig, seuil de 14 336 jetons, 5 événements gardés, résumé texte seul), la compaction
efface tous les appels d'outils et leurs sorties, et paraphrase l'énoncé. Quand elle survient avant la première édition, la réussite
est divisée par deux à tâche égale (p = 0,0013). Effet général : tout agent à mémoire résumée (OpenHands, Claude Code, ADK) est concerné.

## Critères du jury → ce qui les sert
- Nouveauté : mesure appariée de l'effet compaction / première édition ; ce qui survit au résumé (lecture du code ADK).
- Qualité / généralité : le mécanisme est propre au résumé de contexte, pas à la compétition ; des règles de conception transposables.
- Pertinence : agents locaux = petite fenêtre = compaction fréquente (2/3 des tâches ici).
- Vérifiabilité : 24 passages, 839 trajectoires, scripts publiés (détecteur de compaction, comparaison appariée), jeu de traces.
- Clarté : une figure centrale, trois tableaux, des résultats négatifs déclarés.

## Sections
1. Abstract
2. Introduction : agents locaux, petite fenêtre, compaction
3. Setup : modèle, harnais, matériel (4×L4, vLLM 0.19.1), tâches (129, panels de 30 et 70 tâches), 24 passages
4. Le mécanisme : lecture du code d'ADK 1.36.1 (llm_event_summarizer : texte seul) ; détection dans les traces (chute de prompt > 25 %)
5. Résultat 1 : prévalence (2/3 des tâches) et réussite par état (74 / 41 / 12 %)
6. Résultat 2 : appariement par tâche (46 tâches, 14,5 % contre 30,5 %, 19 contre 4, test du signe p = 0,0013)
7. Résultat 3 : budget de jetons, d'où vient le contexte (45 % lectures de fichiers, 39 % texte du modèle ; la réflexion est négligeable)
8. Interventions :
   - armI (énoncé épinglé via {problem_description}) : nul (30 contre 29) ; l'énoncé survit mais la 1re édition n'arrive pas plus tôt
   - armJ (budget mémoire : lectures de 40 lignes, une phrase par tour, édition avant l'appel 8) : critère principal = part des tâches
     compactées avant la 1re édition ; critère secondaire = réussite
9. Résultat 4 : le bruit du classement (passages identiques : 0,20 / 0,18 / sub12 ; les notebooks publics donnent 0,05 à 0,24) ; ce qu'il implique pour l'évaluation des agents
10. Résultats négatifs (budgets temps et appels, réflexion 1024, professeur gpt-oss 5/94, LoRA OOM) : brièvement
11. Related work : SWE-bench, SWE-agent, Agentless, OpenHands (condenser), MemGPT, lost-in-the-middle, ADK
12. Conclusion et recommandations aux concepteurs de harnais et d'agents

## Ressources à publier
- Notebook public : détecteur de compaction + analyses appariées sur les traces
- Dataset : traces anonymisées (839 trajectoires) avec annotations (compaction, 1re édition, résolu)
