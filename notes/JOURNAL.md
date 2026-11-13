# Journal de décisions — Gemma 4 Developer Agent

## 2026-09-30 — Mise en place de l'évaluation locale

**Récupéré**
- Données de la compétition dans `data/` (tasks.jsonl, 129 snapshots ≈ 21,5 Go, graphes,
  embeddings, 124 roues publiques, docker/, sandbox/setup.py, sample_submission/).
  Script de téléchargement reprenable : `logs/download_data.sh`.
- Le harnais officiel n'est ni dans les données ni sur PyPI : il est dans le dataset Kaggle
  `metric/gemma-4-developer-agent-wheelhouse` → `vendor/wheels/` (swegemma 0.2.7,
  adk_submission 0.2.11, adk_eval_core 0.1.0, google_adk 1.36.1). Installé dans `.venv`
  (torch CPU).
- Image `swebench-sandbox:latest` construite depuis `data/docker/Dockerfile.public`
  (`docker build --network=host`, le DNS du réseau bridge ne résout pas sur cette machine).

**Outil** : `tools/eval_local.py`, modes `gold` / `empty` / `agent` / `replay`.
Budgets lus dans `eval_config.yaml` de la soumission, compaction de contexte du README §7.2.

**Biais d'instrument détectés (calibration gold)**
1. `typing_inspection` absent des roues publiques (pydantic 2.13 en dépend) → le correctif
   de référence de fastapi_14258 échouait. Le cache privé de Kaggle le fournit.
   Correctif : `vendor/extra_wheels/` + `tools/build_wheels_dir.sh` → `build/wheels`.
2. Le harnais met en cache les roues dépaquetées dans `/tmp/swegemma_sp_cache_v8` par nom :
   toute modification des roues exige de vider ce cache (fait par `build_wheels_dir.sh`).

**Modèle** : pas de GPU local. Gemma 4 31B-it disponible via le routeur Hugging Face
(fournisseur deepinfra, 0,13 $/M entrée, 0,38 $/M sortie, appels d'outils OK).
Écarts connus avec la notation : bf16 au lieu de QAT W4A16, contexte 262k au lieu de 32k,
pas de LoRA, analyseur d'appels d'outils du fournisseur au lieu de `gemma4` de vLLM.
→ À calibrer contre un passage sur Kaggle (machine NvidiaL4) avant de s'y fier.

**Calibration de l'instrument (terminée le 2026-09-30)**
- Roues publiques brutes : gold = 14/74. Cause : jusqu'à 60 versions d'un même paquet dépaquetées en vrac
  (starlette 1.x → `on_startup` refusé), dépendances de test absentes (inline_snapshot, dirty_equals...).
- Correctif : `tools/task_envs.py` construit un site-packages 3.13 par tâche (uv.lock / poetry.lock /
  résolution datée `--exclude-newer`), injecté par `eval_local.py --deps task-env` (défaut).
- Résultat : **gold 115/129, empty 2/129**. Fichier de référence : `results/calibration.json`.
  - 113 tâches discriminantes, 2 gratuites (fastapi_14851, fastapi_14077 passent sans correctif).
  - 14 impossibles même avec la référence, causes propres au harnais officiel / Python 3.13 :
    8 requests (tests de délai vers 10.255.255.1, réseau coupé), 3 fastapi (`-p no:anyio` du harnais),
    rich_3486 (test sauté ≥ 3.11), rich_3472 (message d'erreur 3.13), fastapi_14186 (test sauté, à creuser).
  → **Plafond local : 115/129 = 89,1 %.** Un score agent se lit contre ce plafond.
  Hypothèse non vérifiée : Kaggle a les mêmes impossibles (même harnais, même Python, réseau coupé).
- Incident : concurrence 3 → charge 40 sur 8 cœurs, swap plein, VS Code planté. Défaut passé à 1, `nice 10`.

**Bloquant pour mesurer un agent** : crédits HF gratuits épuisés (erreur 402 après 21 appels d'outils sur le
test fumée, qui a par ailleurs montré que la boucle agent fonctionne de bout en bout).

## 2026-10-02 — Calibration sur Kaggle (conditions officielles)

Outil : `kaggle/build_kernel.py` → kernel privé (modèle `kaggle/eval_kernel_template.py`), bac à sable
`subprocess` comme le notebook officiel. gold/empty en CPU (aucun quota GPU), ~12-14 min pour 129 tâches.

- **Kaggle : Python 3.12** et paquets de l'image Kaggle (starlette 0.52.1, pydantic 2.12.3, pytest 8.4.2) ;
  en mode subprocess le harnais n'injecte AUCUNE dépendance de test.
- **gold 73/129, empty 3/129** → 70 discriminantes, 3 gratuites, 56 impossibles.
  Fichier : `results/calibration_kaggle.json`.
- Impossibles : 36 fastapi (inline_snapshot / dirty_equals absents de l'image, async sans anyio),
  12 requests (délais réseau → expiration 124), 7 rich, 1 httpx.
- Désaccord avec l'éval Docker locale sur 44 tâches (43 « discriminantes » en local, impossibles sur Kaggle).
  → **L'éval Docker locale n'est pas fidèle. L'instrument de référence est Kaggle.**
- Hypothèse non vérifiée : l'environnement de notation = celui des notebooks. Si oui, le plafond réel est
  ~57 % (73/129) et non 89 %.
- Classement au 2026-10-02 : 1er 0,24 ; ensuite un paquet à 0,15-0,17 ; beaucoup à 0,13.
  Les paliers (0,13 / 0,15 / 0,17 / 0,24) collent à k/46 ou k/54 tâches évaluées.

## 2026-10-03 — Premier passage agent sur GPU Kaggle

- Panel de 10 tâches discriminantes (6 rich, 4 fastapi, graine 20261003) : `kaggle/panel_smoke10.txt`.
- L4 (NvidiaL4) : en file d'attente > 4 h sans démarrer (cause inconnue : saturation ou accès).
- Repli 2×T4 : **impasse matérielle**, 4 essais (~1 h de quota) :
  v1 image GPU par défaut en Python 3.13 (roues cp312) → `docker_image` du notebook officiel épinglé ;
  v2 pas de bfloat16 sur T4 → float16 ; v3 `custom_all_reduce` en panne → `--disable-custom-all-reduce` ;
  v4 noyau Triton qui exige 96 Ko de mémoire partagée, le T4 n'en a que 64 Ko → non contournable.
- Gabarit aligné sur la notation (README §3.1) : `gpu_memory_utilization=0.80`, `enable_thinking=True`
  (le notebook officiel met 0.90 et n'active pas enable_thinking).
- Version L4 corrigée renvoyée (v2), en file d'attente.

**Résultat L4 (v2, terminé le 2026-10-03 13:42) — agent d'exemple sans LoRA, panel smoke10**
- **3/10 résolues** (fastapi_14794, fastapi_14458, rich_2725). Durée totale 29 min : 8 min de démarrage
  (roues 1 min + chargement vLLM 7 min), puis ~20 min pour 10 tâches à concurrence 4 (≈ 3 à 11 min par tâche).
- Échecs : 4 correctifs faux, **3 plantages par dépassement du contexte de 32 768 jetons**
  (fastapi_15280, rich_3935, rich_3180), 1 budget de 100 tours épuisé (rich_2943).
- Cause des dépassements : `max_output_tokens: 16384` réserve la moitié du contexte à la réponse ;
  dès que l'historique dépasse 16 384 jetons, vLLM refuse la requête et la tâche meurt **sans correctif**.
  → Piste n°1 à tester en apparié : baisser `max_output_tokens` (ex. 8192) et/ou compacter plus tôt.

## 2026-10-06 — Correction importante et première soumission

**Correction (source : forum, cité par zhukovoleksiy/gemma-4-walkthrough-first-submission)**
- Kaggle (Ryan Holbrook) confirme que **les tâches cachées passent toutes avec leur correctif de référence**.
  L'environnement de notation a donc les dépendances absentes des notebooks.
  → La conclusion « plafond réel ~57 % » du 2026-10-02 est **fausse**. Les 56 « impossibles » ne le sont que
  dans l'environnement des notebooks, qui reste notre instrument de mesure (mesurer sur les 70 discriminantes).
- **Tâches cachées = dépôts privés**, ~120 tâches (58 publiques d'après les paliers du classement).
  Nos 129 tâches ne sont qu'un substitut de distribution (leçon n°2).
- **Notation en série, 12 h pour tout, démarrage du modèle compris** → ~5 min max par tâche. Au-delà :
  « Notebook Exceeded Allowed Compute ». Mes mesures à 30 min/tâche et concurrence 4 ne sont pas
  représentatives du budget : désormais mesurer avec le budget de la soumission.

**Soumission n°1 (2026-10-06 09:26, réf. 56876951)** — `submissions/sub01` :
agent d'exemple sans LoRA, `max_output_tokens: 8192`, 3,5 min / 80 tours / 60 appels / 120 s par commande.
Envoi via le kernel `stanleyhonkpehedji/g4-submit` (écrit submission.zip). Score : en attente.

## 2026-10-07

- **sub01 : score public 0,10** (≈ 6 tâches sur 58).
- **Comparaison appariée A (16384) / B (8192)**, panel smoke10, budget 30 min (non représentatif) :
  A 3/10, B 4/10, basculements +1 / −0 (rich_2943). Plantages de contexte : 3 → 0. Gain mécanique confirmé,
  écart de score non significatif sur 10 tâches.
- Plantages machine des 06/10 (10:48 et 16:46) : aucun processus de mesure à moi pendant la session
  plantée de 16:46 ; sysstat juste avant : mémoire 63 %, charge ~3, swap quasi vide, aucun OOM.
  Dernière ligne avant le gel de 10:48 : erreur JS de l'extension GNOME CoverflowAltTab (Alt-Tab).

## 2026-10-07 (soir) — Référence panel30

- Panel30 (`kaggle/panel30.txt`) : 17 rich + 13 fastapi parmi les 70 discriminantes (smoke10 inclus, graine 20261007).
- **sub01 sur panel30 : 9/30**, concurrence 1, budget réel. 107 min au total (≈ 3,6 min par tâche, chargement compris)
  → 120 tâches ≈ 7,2 h : marge d'environ 4,8 h sous les 12 h.
- **17 des 21 échecs = délai de 3,5 min dépassé** ; 4 d'entre eux sans aucun correctif. Souvent 10-12 appels seulement.
  → Le temps est le facteur limitant. Bras lancés en parallèle (apparié contre sub01) :
  armT = réflexion désactivée (`include_thoughts: false`), 3,5 min ; armM = réflexion active, 4,5 min.
- Écart panel (30 %) / classement (0,10) : notre panel est plus facile que les tâches cachées, ou l'environnement diffère.

## 2026-10-08 — Bras T et M, soumission n°2

Apparié contre sub01 (9/30) sur panel30, budget réel, concurrence 1 :
- **armT (réflexion désactivée) : 6/30, +0 / −3. REJETÉ.** Sans réflexion le modèle boucle : rich_3180 répète
  la même commande plus de 20 fois puis soumet un correctif vide. 11 tâches sans correctif.
- **armM (4,5 min) : 11/30, +2 / −0** (fastapi_5077, rich_3676). 129 min pour 30 tâches → 4,3 min/tâche,
  120 tâches ≈ 8,6 h. ADOPTÉ.
- **Soumission n°2 (2026-10-08 08:13, réf. 56943942)** = armM (`submissions/sub02`). Score : en attente.
- Bras suivants lancés, appariés contre sub02 : armO (`max_output_tokens: 4096`, borne la réflexion
  puisque `thinking_budget` n'est jamais transmis à vLLM) ; armA (sans sous-agent analyseur).
- **armO (`max_output_tokens: 4096`) : 7/30, +0 / −4. REJETÉ.**
- **armA (sans analyseur) : 9/30, +2 / −4. REJETÉ.**
- rich_3676 gagné par M puis perdu par O et A : le bruit d'un passage à l'autre est réel et non mesuré.
  → Lancés : réplique exacte de sub02 (mesure du bruit) et armP (prompt système réécrit : grep d'abord,
  lire les tests voisins pour les conventions, jamais deux fois la même commande, gestion du temps, `| tail`).

**Mesure du bruit (2026-10-08 après-midi)** — sub02 relancé à l'identique sur panel30 :
- passage 1 : 11/30, passage 2 : 8/30 → **3 tâches basculent par pur hasard** (fastapi_14794, fastapi_5077,
  rich_3676). 8 tâches stables, 11 résolues au moins une fois.
  → Le +2/−0 de M contre sub01 est **dans le bruit**. Tout écart ≤ 3 tâches sur un seul passage est inconclusif.
  → Règle : comparer sur 2 passages par bras (60 essais), ou panel plus grand.
- **armP (prompt réécrit) : 12/30.** Contre sub02 : +2/−1 (passage 1), +5/−1 (passage 2) ; moyenne sub02 = 9,5.
  Indice favorable (≈ +2,5 tâches), pas encore une preuve. 122 min / 30 tâches (4,1 min/tâche).
- **Quota GPU hebdomadaire Kaggle de 30 h atteint le 2026-10-08 vers 14 h** : réplique de P et P à 5,5 min refusées.
  Consommation : ~1 h d'essais T4 + ~10 passages L4 (2 h chacun). Un passage panel30 coûte ~2 h → ~14 par semaine max.
  Les soumissions ne consomment PAS ce quota (la notation tourne côté Kaggle).

**Analyse des trajectoires (2026-10-08, 120 tâches jouées, sans GPU)**
- **Premier levier identifié : ~40 % des tâches finissent sans AUCUNE modification du code du projet.**
  Échecs sans modification : 12 / 11 / 13 / 11 (sub01, sub02 ×2, armP) contre 7 à 9 correctifs faux.
  L'agent écrit des scripts de reproduction (repro.py, reproduce_issue.py...), et le délai tombe avant l'édition.
  1re édition médiane : 93 à 127 s sur ~270 s disponibles.
- Fichiers parasites dans les correctifs : 24 % de réussite avec contre 58 % sans, mais ils ne figurent dans
  aucune sortie de test en échec → **marqueur, pas cause** (leçon n°5). Non traité en soi.
- Hypothèse à tester dès le retour du quota : bras P2 = armP + « éditer le code source dans les ~90 premières
  secondes, aucun script de reproduction avant la première édition ».

## 2026-10-09

- sub02 : « Notebook Running » depuis plus de 30 h ; Kaggle n'accepte **qu'une soumission en attente à la fois**
  (« Your team already has 1 pending submissions ») → sub03 (= armP, prête) refusée tant que sub02 tourne.
- Quota GPU : 0 h sur 30 h. Quota « AI » : 10 $/jour, 100 $/mois inutilisés.
- **Kaggle Model Proxy** (`kaggle benchmarks auth`, identifiants dans `~/.config/gemma4-agent/`, hors dépôt,
  valables 2 h) : **ne sert aucun Gemma** (claude-sonnet-5, gemini-3-flash, gpt-oss-120b, qwen3-next,
  deepseek-r1, granite, gpt-5.4-nano). Impasse pour mesurer notre agent. Usage possible plus tard :
  produire des trajectoires de référence (distillation vers un adaptateur LoRA), à évaluer.

**Caractérisation du sommet (2026-10-09, en retard : leçon n°1 appliquée au 16e jour, pas au 1er)**
Notebook public honghanhhh/gemma-4-baseline-lb-0-24 (dérivé de verracodeguacas « Budget-Fit Single Agent », 0,18) :
agent unique, sans outils de graphe ni analyseur, 8 min / 28 appels / `timeout_seconds: 240`, réflexion active,
8192 jetons, « édition du code source avant l'appel n°12 » (sinon ~87 % d'échec d'après leurs mesures),
soumettre dès que l'édition existe, brouillons dans /tmp. L'auteur du 0,18 dit qu'une notation à 8 min
a tenu dans les 12 h, car la plupart des tâches s'arrêtent tôt.
- **Vérifié dans le code du harnais** (verification.py:502) : le pytest de notation utilise
  `timeout=command_timeout_seconds`, donc notre `timeout_seconds: 120` (sub01, sub02, sub03 prête) peut faire
  échouer un correctif juste dont les tests durent plus de 120 s. À corriger avant toute nouvelle soumission.
- Notre constat (≈ 40 % de tâches sans édition) rejoint indépendamment leur règle « édition avant l'appel 12 ».
- Le budget de 8 min n'est PAS transposable tel quel : notre agent utilise presque toujours tout son temps
  (4,3 min en moyenne pour un plafond de 4,5). À 8 min il dépasserait les 12 h si son comportement ne change pas.

## 2026-10-10

- **sub02 : 0,13** (≈ 7-8 tâches / 58), contre 0,10 pour sub01 (≈ 6). Écart d'environ 1 tâche : dans le bruit
  du classement (≈ 2 tâches entre deux soumissions identiques). Durée de notation ≈ 47 h, file d'attente comprise.
- **Soumission n°3 (2026-10-10 07:12, réf. 57034676)** = `submissions/sub03` : prompt P + « édition avant
  l'appel n°12 » + brouillons dans /tmp + `timeout_seconds: 240`, 4,5 min/tâche.
  Ajouts au prompt NON mesurés sur panel (quota GPU à 0) ; correction du délai vérifiée dans le code.

## 2026-10-12

- **sub03 : 0,15** (≈ 9 tâches / 58). Suite 0,10 → 0,13 → 0,15. Sommet : 0,24 (2 équipes), puis 0,22 (3 équipes).
- Quota GPU revenu. Lancés sur panel30 : sub03 (mesure de la soumission) et sub03_t65 (même agent, 6,5 min/tâche)
  pour mesurer gain et durée réelle par tâche avec la règle « édition avant l'appel 12 ».
- **Harnais mis à jour par Kaggle le 2026-10-09** : swegemma 0.2.7 → 0.2.11, adk_submission 0.2.11 → 0.2.13.
  Changements utiles : `submit_patch` retire désormais du correctif les fichiers de test et de configuration
  protégés ; `validate_single_declared_model` et `setup_gemma_model_registry` disparaissent
  (→ `adk_submission.discovery.discover_declared_models`, `ModelRegistry`). Gabarit Kaggle adapté.
  Les 2 passages GPU lancés plus tôt avaient échoué au démarrage (nom de roue figé) : relancés.
- Recalibration gold sous 0.2.11 : **73/129, mêmes tâches** qu'avant → le panel30 reste valide.
- **sub03 sur panel30 : 13/30** (vs armP 12 : +3/−2). Tâches sans modification : 10 ; durée moyenne 3,6 min.
- **sub03_t65 (6,5 min) : 16/30, +4/−1 contre sub03** (au-dessus du seuil de bruit de 3). Sans modification : 6.
  162 min pour 30 tâches → 5,1 min/tâche → 120 tâches ≈ 10,4 h (marge ≈ 1,6 h, à surveiller).
- **Soumission n°4 (2026-10-12 13:49, réf. 57109081)** = `submissions/sub04` (sub03 à 6,5 min/tâche).
  Risque : dépassement des 12 h si les tâches cachées sont plus lentes que le panel.

**Analyse des 14 échecs de sub04 (panel30)** : 6 sans modification (toutes rich, énoncés de 71 à 1189 car.),
7 bon fichier mais mauvais comportement, 1 mauvais fichier. Sur rich_3953, l'agent identifie la cause à 184 s
mais une seule réflexion dure 115 s (10 766 caractères), puis une autre 80 s → délai atteint avant l'édition.
→ Bras armS = sub04 + consigne « réflexions courtes ; éditer dès que la cause est trouvée ». Lancé avec la
réplique de sub04.
- **Réplique de sub04 : 13/30** (1er passage 16) → sub04 ≈ 14,5/30 en moyenne ; le +4/−1 contre sub03 était en
  partie de la chance (sub03 n'a qu'un passage à 13).
- **armS (réflexions courtes) : 13/30**, +1/−1 contre la réplique : **aucun gain mesurable**, un peu plus rapide
  (4,5 contre 4,9 min/tâche). Non retenu.
- Constat : les retouches de prompt donnent maintenant des écarts ≤ 3 tâches, indiscernables du bruit sur 30 tâches.
  → Pour trancher, passer au panel des 70 discriminantes (~5,5 h GPU par passage), ou chercher des leviers plus gros.

## 2026-10-14 — sub04 notée, boîte à outils swe-kit

- **sub04 : 0,17** (≈ 10 tâches / 58), notation terminée dans les 12 h à 6,5 min/tâche. Suite 0,10 → 0,13 → 0,15 → 0,17.
- **Nouveau levier : les « skills » ADK.** Depuis swegemma 0.2.11, `run_skill_script` exécute nos scripts .py
  DANS le bac à sable de l'agent (`AdkSandboxCodeExecutor`, adk_eval_core/sandbox/base.py). On peut donc livrer
  nos propres outils. Nom de skill obligatoirement en kebab-case → `swe-kit`.
- `kit/swe-kit/` : locate.py (BM25 fichiers + définitions + correspondances exactes), show.py (source d'une
  fonction par nom), tests_for.py (tests existants qui utilisent un nom + commande pytest). Bibliothèque standard.
- **Mesure hors GPU de locate.py** (`kit/eval_locate.py`, 126 tâches, énoncé seul) : bon fichier dans le top 3
  pour 69 %, top 8 pour 86 % ; bonne fonction dans le top 5 pour 69 % ; ≤ 0,42 s, sortie ≤ 3 000 car.
- armK = sub04 + skill swe-kit + prompt « commencer par locate, puis show, puis tests_for ». Compilation validée
  avec le nouveau harnais (`.venv-new`). Essai GPU sur 2 tâches en cours avant le panel complet.
- Essais GPU de armK sur 2 tâches : (1) scripts muets « no python source files » car ADK exécute les scripts de
  skill depuis un dossier temporaire (`os.chdir(td)`, google/adk/tools/skill_toolset.py) → racine du dépôt
  retrouvée via `PWD`, `/workspace` ou le dossier `workspace` voisin du `tmp` du bac à sable. (2) Prompt :
  donner à locate le titre + les identifiants (10-30 mots), pas un mot isolé. (3) Essai 3 : les scripts
  répondent, l'agent enchaîne sur le bon fichier. Lancés : armK ×2 sur panel30.
- **armK (swe-kit) ×2 : 12 et 13/30 = 25/60, contre sub04 ×2 = 29/60.** Aucune tâche meilleure, 3 moins bonnes.
  **REJETÉ.** Interprétation : la localisation n'était pas le goulot (l'agent trouvait déjà le fichier par grep) ;
  les échecs sont des comportements faux au bon endroit et des réflexions trop longues.
- Caractérisation du sommet (leçon n°1) : l'agent public « 0,24 » (honghanhhh, empreinte du prompt
  sha256 7163e664…) extrait tel quel dans `submissions/pub024` (8 min, 28 appels, sans graphe ni analyseur)
  et mesuré ×2 sur panel30. Sert aussi à calibrer panel ↔ classement.
- Mesure de pub024 NON lancée : **quota GPU de 30 h épuisé à nouveau** (2026-10-14). Consommation de la semaine :
  ~10 passages panel30 (≈ 2,5 h chacun) + essais. Le quota était revenu entre le 08/10 14 h et le 12/10 matin.

## 2026-10-27 — Reprise après 13 jours d'arrêt

- Aucune action du 14/10 au 27/10 (abonnement de l'utilisateur interrompu) : ~13 soumissions perdues. 36 jours restants.
- Classement : **5 équipes à 0,24** (2 le 14/10) → plafond commun probablement atteint par des copies du notebook
  public : son 0,24 est reproductible, pas de la chance. Notre meilleur : 0,17 (sub04).
- Analyse des échecs « bon fichier » (50 cas, 6 passages) : 17 correctifs beaucoup plus petits que la référence,
  17 fichiers manquants, 16 de taille comparable → **2/3 des échecs = correctifs incomplets**.
- Lancés : pub024 sur panel30 ; armC = sub04 + « implémentation complète » (remplace « plus petit changement »,
  étape « compléter : chercher les autres endroits qui traitent la même notion »).

### 2026-10-27 (soir) — résultats panel30 et sub05
- pub024a-p30 (agent public 0,24) : 15/30, 5,0 min/tâche, 3 timeouts, 4 patchs vides.
- armc-p30 (sub04 + « implémentation complète ») : 13/30, 12 timeouts → **rejeté** (aucun gain).
- Référence sub04 : 16 et 13/30, 10–13 timeouts.
- Sur le panel, l'agent public n'est pas meilleur que le nôtre, pourtant le LB dit 0,24 contre 0,17. Soit le
  panel ne représente pas le jeu caché, soit l'écart vient des timeouts (3 contre 10–13 : nos sessions
  coupées à 6,5 min perdent leur travail).
- **sub05 = pub024 tel quel** (ref 57706307), pour calibrer : si on obtient ~0,24, le panel ne voit pas l'écart
  et il faut chercher la cause (timeouts, budget de 28 appels, absence d'analyseur ou d'outils de graphe).

### 2026-10-28 — armD (prompt sub04 + réglages pub024 : 28 appels, 8 min, sans analyseur ni graphe)
- armd-p30 : 13/30, 4,8 min/tâche, 2 timeouts, 7 patchs vides.
- Les timeouts disparaissent (2 contre 10–13), mais le score ne bouge pas. Les 5 passages tombent tous entre 13 et 16/30 :
  le panel30 ne distingue plus nos variantes (bruit ±3). sub05 (pub024) toujours en attente de note.
- Si sub05 ≈ 0,24 : le panel ne voit pas un écart de 4 tâches sur 58 → passer au panel des 70 discriminantes (~6 h GPU par passage).
- 15h30 UTC : sub05 toujours en attente (~23 h). Lancé pub024-p70 et sub04-p70 (panel des 70 discriminantes,
  `kaggle/panel70.txt`, ~6 h GPU chacun), pour voir si un panel plus grand reproduit l'écart du classement.

### 2026-10-29 — sub05 noté, panel70
- **sub05 (agent public tel quel) : 0,20 au LB**, pas 0,24. Le 0,24 des équipes en tête est en partie de la chance.
- Panel70 (concurrence 1) : pub024 29/70 (11 timeouts, 11 vides), sub04 29/70 (29 timeouts, 18 vides).
  5 tâches gagnées de chaque côté. **Égalité parfaite** : aucune recette cachée dans l'agent public.
- Union des deux : 34/70. Le plafond pratique de ce modèle avec ces approches est vers 40–45 % des discriminantes.
- sub06 = pub024 identique à sub05, pour mesurer le bruit du LB sur un même agent.
- Suite : chercher des leviers plus gros que des retouches de consigne (patchs vides, sessions coupées sans patch).
- **Défaut trouvé : appels d'outil tronqués.** Le modèle ferme parfois une chaîne d'argument par un backtick au lieu
  du délimiteur ; le parseur gemma4 de vLLM découpe alors mal les arguments → « mandatory input parameters are not present ».
  Le modèle renvoie ensuite le même appel en boucle (73 fois sur rich_3454). Touche 6 tâches/70 (sub04) et 13/70 (pub024),
  surtout edit_file (new_string avant old_string), parfois write_file.
- armE = pub024 + section « If a tool call is rejected » (ne jamais renvoyer, réduire old/new à 1-3 lignes, ordre
  filepath/old/new, puis éditions d'une ligne). Panel ciblé `kaggle/panel_toolfail.txt` (17 tâches touchées).
- Push refusé : **quota GPU hebdomadaire épuisé** (30 h). armE candidat pour sub07 dès que sub06 est noté.
- Causes des 82 échecs (sub04-p70 + pub024-p70, 140 tâches) : 45 modif faite mais fausse (55 %), 20 aucune modif
  (exploration jusqu'au timeout, surtout sub04 : la règle « éditer avant l'appel 12 » est ignorée), 7 appels rejetés en boucle,
  7 même appel répété ≥4 fois, 3 old_string introuvable. Les boucles (14) se corrigent par consigne → armE.
- sub07 = armE, envoi automatique dès que sub06 est noté (kernel g4-submit v7).
- Plan au retour du quota : armE sur le panel ciblé (17 tâches, ~1,5 h) puis sur panel70 (~6 h), comparé à pub024-p70.
  Ensuite s'attaquer aux « modif fausse » (55 %), le gros morceau.

### 2026-10-30
- Le script d'envoi de sub07 est mort avec la session → réécrit en `tools/submit_when_free.sh`, lancé détaché
  (setsid nohup, journal dans logs/submit_sub07.log). sub06 toujours en attente après 25 h. Quota GPU toujours épuisé.
- Tâches « mauvais fichier » : énoncés quasi vides (« fix fonts », « Fix #3104 », « preserve newlines ») ou correctif
  attendu à un autre endroit que celui que l'énoncé suggère. Pas de règle de localisation exploitable → levier faible.

### 2026-10-31
- **sub06 (pub024 identique à sub05) : 0,18** contre 0,20 → bruit du LB ≈ ±0,02 pour un même agent. sub04 (0,17),
  pub024 (0,18–0,20) : indiscernables. sub07 (armE) envoyé automatiquement le 30/10 à 09h58, en attente.
- Quota GPU revenu : arme-tf lancé (17 tâches à appels rejetés), rapatriement détaché via tools/fetch_when_done.sh.

### 2026-11-01 — armE rejeté
- arme-tf : 8/17 sur les tâches à boucles (pub024 7, sub04 8). arme-p70 : 28/70 (pub024 29). **sub07 : 0,15 au LB.**
- La règle raccourcit les boucles (max 57 → 13 rejets, 13 → 9 tâches touchées) mais ne gagne aucune tâche : les tâches
  à boucles sont aussi des tâches difficiles. **armE rejeté.**
- Bilan : toutes nos variantes de consigne plafonnent à ~29/70 (41 %). Les retouches de consigne sont épuisées.
  Prochain levier : LoRA (seul différenciateur face aux copies du notebook public). Étape 1 : vérifier les règles
  (données externes, modèles tiers) et la faisabilité mémoire sur 4×L4.
- Panne : `uvx kaggle` ne trouve plus `six` → `uvx --with six kaggle` partout.
- **Erreur reconnue** : ne pas soumettre faute de « meilleure version » (reproche de l'utilisateur, leçon Kaggriculture).
  → sub08 = armF (pub024 + 36 appels au lieu de 28 : 15/70 tâches butaient sur 28, dont 6 patchs vides ; marge ~2 h
  sur 12 h). Ref 57874036. Mesure armf-p70 lancée en parallèle.
- **Règles lues** (§2.6) : données et modèles externes autorisés s'ils sont accessibles à tous à coût minime ;
  licence gagnant Apache 2.0 ; code d'entraînement à fournir. gpt-oss-120b (Apache 2.0, via proxy Kaggle) = OK.
- Chantier professeur : proxy Kaggle gpt-oss-120b OK avec appels d'outils (1,5 s, ~0,04 $/tâche estimé,
  10 $/jour). `tools/eval_local.py` lit la clé dans EVAL_API_KEY. Test sur 3 tâches en cours (results/teacher/smoke).
- Pipeline professeur : `tools/proxy_relay.py` (relais local 127.0.0.1:8765 → proxy Kaggle, réessaie les réponses
  `message: null`, clé lue dans l'environnement) ; piège : le harnais retire le préfixe `openai/` du nom de modèle.
  `tools/trace_to_sft.py` (traces ATIF réussies → messages OpenAI + schémas d'outils `build/tool_schemas.json`),
  rendu vérifié avec le gabarit Gemma 4 (`build/gemma4_tok/`). Hors entraînement : `kaggle/panel_holdout35.txt`
  (35 des 70 discriminantes, graine 20261101) — jamais dans les données d'entraînement.
- Entraînement LoRA : l'environnement Kaggle a transformers 5.13.1, peft 0.19.1, bitsandbytes 0.46.1,
  torch 2.10, compressed-tensors 0.15. Base d'entraînement : `google/gemma-4/transformers/gemma-4-31b-it-qat-q4_0-unquantized/2`
  (62,6 Go, mêmes poids QAT que le modèle de notation, non compressés) → QLoRA 4 bits sur 4×L4.
- Relais : renouvelle seul la clé (401 → `kaggle benchmarks auth`), 25 essais. Proxy : qwen3-next (404) et
  deepseek-r1 (erreur) en panne malgré la liste ; gpt-oss ~50-76 % de réponses vides → lent (~1 appel/min).
  Smoke 3 tâches dures : 0/3. Test sur 8 tâches moyennes en cours (results/teacher/t8).
- `kaggle/train_lora.py` validé en local sur Gemma 4 minuscule (masque vérifié : seuls texte et appels du tour
  model sont entraînés). Données Gemma seules (hors holdout, 6 outils de base) : 65 exemples, 22 tâches — trop peu.
- `kaggle/build_train_kernel.py` ; sonde g4train-probe (3 pas, 12k tokens) poussée : chargement, mémoire, durée d'un pas.

## 2026-11-01 (soir) — professeur via proxy abandonné, professeur auto-hébergé, masque corrigé
- **Professeur gpt-oss via Kaggle Model Proxy : 0/8**, les 8 tâches dépassent 25 min. 494 requêtes au proxy,
  42 réponses non vides (8,5 %). Impasse : abandonné.
- **Sonde d'entraînement g4train-probe : OOM**. Kaggle a donné **2×T4** au lieu de 4×L4 (la machine L4 était prise
  par armf-p70 : une seule session L4 à la fois, bascule silencieuse). Chargement nf4 : ~9,5 min.
  Garde-fous ajoutés : le kernel d'entraînement et le professeur s'arrêtent tout de suite sans 4×L4.
- **Gabarit de conversation** : w4a16 (notation) = q4_0-unquantized (md5 identique), mais ≠ gabarit HF.
  Le gabarit Kaggle garde un seul tour « model » ouvert et y insère des `<turn|>` : l'ancien masque n'entraînait que
  10 k tokens sur 738 k. Nouveau masque (`trained_char_spans`) : tout le tour modèle sauf réponses d'outil et `<turn|>`
  (jeton de fin : l'apprendre couperait les appels) → 208 k tokens entraînés. On entraîne avec le gabarit de la notation.
- **Professeur auto-hébergé** : `danielhanchen/gpt-oss-120b` (Apache 2.0, MXFP4 61 Go) servi par vLLM 0.19.1 sur 4×L4
  (parseurs `openai` / `openai_gptoss`, openai-harmony présent dans le wheelhouse). `build_kernel.py --teacher`.
  Kernel `g4eval-teach94` : 94 tâches hors holdout (`kaggle/panel_train94.txt`), concurrence 4, 15 min/tâche, 36 appels.
- File GPU (`tools/push_after.sh`) : armf-p70 → teach94 → g4train-self1 (LoRA sur 65 succès de Gemma, 2 époques).

## 2026-11-02
- **armF (36 appels) panel70 : 34/70** vs pub024 29/70 (+7 −2). Les 7 gains ont tous > 28 appels.
  Reste : 13 timeouts à 8 min, 9 plafonds d'appels ; durée moyenne 4,9 min/tâche (marge sur 12 h).
- **sub09 = armG** : armF + 40 appels / 10 min (prompt aligné). Envoyée via submit_when_free (sub08 encore PENDING).
- Push teach94 refusé (400) : Kaggle refuse internet sur GPU. Encodages tiktoken → dataset
  `stanleyhonkpehedji/tiktoken-encodings`, `TIKTOKEN_ENCODINGS_BASE`. File : g4train-self1 (lancé) → teach94.
- 11:30 UTC : self1 a de nouveau reçu 2×T4 (garde-fou → arrêt immédiat, pas de quota perdu) alors qu'aucune session L4
  ne tournait : l'attribution L4 n'est pas garantie. teach94 v1 a eu 4×L4 : gpt-oss MXFP4 charge (Marlin, 17,2 Gio/carte)
  mais « No available memory for the cache blocks » à 0,90. v2 : 0,96 + max-num-seqs 8 + batched-tokens 4096. File : teach94 v2 → self1.
- sub08 toujours PENDING après 21 h ; sub09 attend derrière.
- 12:00 UTC : teach94 v2 → vLLM gpt-oss **démarre** (mémoire OK), mais 94/94 requêtes refusées :
  `thinking_token_budget` (thinking_config du sampling Gemma) non supporté → retiré pour le professeur. v3 lancé.
- **Vraie cause des 2×T4** : le kernel d'entraînement n'avait pas `competition_sources` ; les 4×L4 ne sont données
  qu'aux kernels attachés au concours (les kernels d'éval l'ont). Corrigé ; self1 enchaîné après teach94.
- 16:30 UTC : teach94 v3 encore 94 refus : le budget thinking vient des défauts du harnais (`build_submission_limits` :
  thinking_budget 4096), et l'agent tourne en sous-processus → relais HTTP local 8001→8000 dans le kernel professeur
  qui retire les champs `*thinking*` (testé en local).
- self1 v3 : **4×L4 obtenues**, 31B nf4 chargé, LoRA 122 M params, 208 660 tokens entraînés ; crash au 1er pas
  (tête de sortie cuda:0 / étiquettes cuda:3) → corrigé. File : self1 v4 → teach94 v4.
- Classement : 1er 0,29 (Yurnero), puis plusieurs à 0,24. Nos 0,20/0,18.

## 2026-11-03
- **sub08 (armF) : 0,15** au LB malgré 34/70 au panel (pub024 : 0,20 / 0,18 ; armE 0,15). Écart ~1,3 σ
  (≈ 12 tâches basculent entre deux passages identiques sur 120). Le panel et le LB divergent.
- La machine a redémarré : tous les processus détachés tués, sub09 jamais envoyée hier (jour perdu).
  **sub09 = armG envoyée ce matin** (ref 57942563) : test direct du sens « plus de budget ».
- teach94 v4 : le professeur tourne (14 appels/tâche) mais 1/94 : gpt-oss émet jusqu'à 40 appels parallèles et le
  harnais leur renvoie la même observation → modèle perdu (`echo hello`). Relais : `parallel_tool_calls=false` + on ne
  garde que le premier appel.
- self1 v4 : OOM GPU 0 dans la perte (logits fp32 de tous les morceaux gardés pour la rétropropagation) → morceaux de
  512 recalculés (checkpoint) + max_memory GPU 0 = 12 Gio.
- **Quota GPU hebdo épuisé** (armf-p70 6 h + teach94 v4 4 h + essais). Retour samedi 07/11 00:00 UTC.
  `tools/push_when_quota.sh` réessaie le professeur toutes les 30 min.
- **Compatibilité LoRA vérifiée sans GPU** : vLLM 0.19.1 PyPI → `Gemma4ForConditionalGeneration` sans SupportsLoRA
  (le serveur planterait), mais la roue du wheelhouse Kaggle (sha 73c69baf…, différente) est patchée : SupportsLoRA +
  hf_to_vllm_mapper `model.language_model.` → `language_model.model.`, q/k/v et gate/up empaquetés. Nos noms PEFT
  (`base_model.model.model.language_model.layers.*`) = ceux de l'exemple officiel. Rang 16 dans les rangs vLLM admis.
- Harnais Kaggle = adk_submission 0.2.13 / swegemma 0.2.11 (copiés dans vendor/wheels).
- Outils prêts pour samedi : `tools/make_lora_submission.py` (contrôles rang/noms/taille), poids LoRA via
  `kernel_sources` (sortie du kernel d'entraînement) dans l'éval (`build_kernel.py --adapter-kernel`) et dans
  `kaggle/build_submit_kernel.py` (testé localement sur l'adaptateur d'exemple).
- Chaîne samedi (`tools/chain_samedi.sh`, détachée) : teach94 v5 → self1 v5. Test --tiny de la nouvelle perte OK (12,49).

## 2026-11-05
- Machine redémarrée le 03/11 à 12:07 : chaîne du samedi morte, **pas de soumission le 04/11** (jour perdu).
- **sub09 (armG, 40 appels / 10 min) : COMPLETE sans note** → très probablement dépassement des 12 h de notation.
  Avec armF (36 appels) 0,15 et pub024 (28 / 8 min) 0,18–0,20 : **la limite totale de 12 h est déjà presque atteinte
  sur les tâches cachées** ; ajouter du budget coupe la fin de la série. Le panel (concurrence 2, tâches publiques) ne
  le voit pas. Sens inverse à tester : moins de temps par tâche.
- **sub10 = armH : pub024 à 7 min/tâche** (ref 58029941).
- File GPU désormais pilotée par `tools/cron_tick.sh` (étapes avec témoins dans logs/etat/, reprend après redémarrage),
  lancé en boucle détachée ; l'ajout d'une crontab a été refusé par le mode auto.
- Conséquence pour le LoRA : il doit aussi rendre l'agent plus rapide (moins d'appels), pas seulement plus juste.
- **Veille publique (enfin)** : 12 notebooks tirés dans research/. Faits clés (dmitriigluzdov, dariushafshar) :
  LB public = 58 tâches, mêmes fichiers → 4 à 13 tâches selon le passage ; budget-fit 8 min projeté à 11,6 h sur
  120 tâches (limite 12 h). Presque tous les publics = même base (8 min, 28 appels, thinking 4096, T 0,2).
  Exception : navyadevadiga thinking_budget 256, 25 appels, T 0,3 (0,15–0,24). À lire : serving-and-lora-verification-kit.

### 2026-11-06
- sub10 (armH, pub024 à 7 min) : **0,13**. Comme sub09 et armF : réduire ou augmenter le budget temps et appels ne mène nulle part, c'est du bruit au mieux.
- sub11 = armR1k = pub024 avec thinking_budget 1024 au lieu de 4096 (un seul changement). On teste la vitesse à budget égal ;
  le T8 de Navya (réflexion 256, 8 min) a obtenu 0,20 puis 0,15. Le quota GPU revient le 11-07 à 00:00 UTC, et cron_tick poussera alors teach94 puis self1.
- File GPU réordonnée : self1 (LoRA, 65 succès Gemma) → éval lora1 sur holdout35 (base : pub024-p70 sur les mêmes tâches) → teach94. Règle : aucune variante sans preuve écrite.
- **Veille publique** (`tools/veille.py`, quotidienne via cron_tick → research/VEILLE.md) : 300 notebooks. 8 contiennent un LoRA
  (r=4 ou 8, aucun score annoncé au-dessus de 0,08). Skill de routine : `.claude/skills/point-du-jour`.
- **Compaction (hibbamd/gpuuuu V39-40, vérifié dans ADK 1.36.1)** : au-delà de 14 336 jetons, ADK résume tout sauf les 5 derniers
  événements, et le résumé ne garde QUE le texte (appels d'outils et résultats perdus, énoncé paraphrasé par Gemma).
  Nos traces : pub024-p70, 47/70 tâches compactées, résolues 13/47 contre 16/23 non compactées (même tendance sur armF et sub04).
- **armI** = pub024 + énoncé exact répété dans l'instruction via `{problem_description}` (prévu par la doc, injection testée avec
  ADK 1.36.1) + règle « relire les lignes avant d'éditer ». Mesure g4eval-armi-p70 en tête de file samedi, à comparer avec
  `tools/compare_runs.py`. Soumission seulement si armI ≥ pub024 sur les mêmes tâches.
- Analyse post-compaction (pub024-p70) : 13 tâches compactées AVANT la première édition → 0/13 résolues ; les 13 compactées résolues
  avaient toutes édité avant. Croissance du contexte ≈ 640 jetons/tour : ~45 % texte et arguments du modèle, ~40 % observations ;
  la réflexion pèse presque rien (complétion 302 ≈ visible 279) → le budget de réflexion n'est pas un levier (sub11 = probablement du bruit).
  Piste suivante si armI confirme : première édition avant le seuil (lectures ciblées, messages courts), en variante séparée.

### 2026-11-08
- Redémarrage le 11-07 à 20:57 : boucle morte, **aucune soumission le 11-07**. Erreurs API Kaggle (JSON vide, SSL) de 15:15 à 19:37 sur
  le push de self1. Boucle relancée ; self1 v5 RUNNING depuis 09:10 UTC. Filet ajouté à cron_tick : si rien n'est soumis à 18:00 UTC, pub024 part seul.
- sub11 (réflexion 1024) : **0,15**, conforme à l'analyse (la réflexion pèse peu).
- **armI panel70 : 30/70 contre 29 pour pub024** (+4 −3), du bruit. Compactées avant édition : 19 (2 résolues) contre 13 (0) ; la 1re édition
  n'arrive pas plus tôt (appel 10, contexte 9,2k). Garder l'énoncé ne suffit pas : l'agent n'édite pas assez tôt.
- sub12 = pub024 tel quel (ref 58122132), 3e mesure de la base.
- **Paper Track** (gemma-4-developer-agent-paper) : 35 000 $, 667 équipes, date limite 2026-11-12. Classement principal : 5 088 équipes, nous 301e.
  Décision : l'effort principal va à l'article ; le classement principal passe en pilote automatique (filet + file GPU), le LoRA décide ce soir.
- Résultat central (24 passages, 839 trajectoires) : compaction avant la 1re édition → 12 % résolues ; compaction après édition → 41 % ;
  pas de compaction → 74 %. Apparié par tâche (46 tâches vues dans les deux conditions) : 14,5 % contre 30,5 %, mieux pour 19 tâches et pire pour 4,
  test du signe p = 0,0013. L'effet n'est donc pas seulement celui de la difficulté.
- 2026-11-08 soir : self1 a manqué de mémoire GPU au 1er backward (GPU 3, longueur max 12 288) ; professeur teach94 = 5/94 résolues
  → voie LoRA abandonnée. armJ (budget mémoire) lancé sur panel70. Crontab installée par l'utilisateur et vérifiée (22:15 UTC).
  Brouillon de l'article : research/paper/writeup.md (~2 200 mots), plan : research/paper/PLAN.md. Restent : résultat armJ, figure, notebook public et dataset de traces.

### 2026-11-09
- sub12 (pub024 tel quel) : **0,18** (la base a donc fait 0,20, 0,18 et 0,18).
- **armJ panel70 : 32/70 contre 29 pour pub024** (+5 −2 ; non significatif seul). Critère mécanique : tâches compactées 38 contre 47
  (apparié : 13 contre 4, McNemar exact p = 0,049) ; croissance par tour 390 contre 445 jetons ; durée moyenne 4,2 contre 4,9 min
  (projection sur 120 tâches : 8,4 h contre 9,7 h). La compaction avant la 1re édition ne baisse PAS (12 contre 13) et la 1re édition
  n'arrive pas plus tôt (appel 11).
- Preuve pour sub13 = armJ : ≥ base sur les mêmes tâches, compaction réduite (p = 0,049) et 14 % plus rapide.
- sub13 = armJ soumis (ref 58171079) après un kernel de soumission resté 1 h 30 en file (v13) ; v14 a fini en 2 min.

## 2026-11-10
- sub13 armJ = 0,13 (base 0,20 / 0,18 / 0,18) : le gain du panel70 ne se transfère pas. Ce soir : filet pub024.
- Paper : token_audit.py exporte token_shares.csv (sans contenu) ; tableaux 1-3 reproduits à l'identique. Dataset privé stanleyhonkpehedji/gemma4-agent-compaction-traces + notebook privé gemma4-compaction-repro (v1 erreur de chemin, v2 corrigée). À rendre publics le 11-12 avec l'article. Liens insérés dans writeup.md, sub13 ajouté à la section 8.

## 2026-11-11
- Filet du 11-10 : pub024 = 0,17 (4e mesure de la base : 0,20 / 0,18 / 0,18 / 0,17).
- Test côté harnais (seuil de compaction 20 480, kernel g4eval-thr20k-p70 construit) impossible : quota GPU hebdo Kaggle épuisé, pas de GPU local, crédits HF épuisés. Étape retirée de la file.
- Relecture jury de l'article : croissance du prompt rendue reproductible (colonne median_growth) ; l'ancien « −12 % » (médiane groupée, non reproductible depuis le CSV) remplacé par 458 vs 444 et 48 vs 43 franchissements ; p bilatéral ; citations de notebooks non sourcées retirées ; section Limitations. Dataset v2. Ancienne version : research/paper/writeup.v1.md.
- Paper : dataset et notebook publics, Writeup soumis par l'utilisateur (11-11).
- 2026-11-12 : classement principal abandonné par l'utilisateur ; filet maintenu. Writeup soumis.
