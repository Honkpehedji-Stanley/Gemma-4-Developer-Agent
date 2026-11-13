# Ce que Kaggriculture nous a appris (à appliquer ici dès le jour 1)

Résultat là-bas : 1 822e sur 10 193. Ce fichier existe pour que les mêmes
erreurs ne se répètent pas.

## Les cinq erreurs qui nous ont coûté le plus

1. **Avoir caractérisé le terrain trop tard.** Nous n'avons su qu'au 19e jour
   que le sommet était tenu par une classe d'agents à laquelle la nôtre ne
   pouvait pas accéder (plafond mesuré à 2 965 contre 3 030 pour le top 10).
   → **Ici : le jour 1, établir qui domine, avec quelle approche, et quel est
   le plafond de chaque approche.** Avant d'écrire une ligne.

2. **Avoir validé sur un panel non représentatif.** Nos agents faisaient
   100 % contre les 8 agents publics que nous détenions, et 44 % sur le ladder.
   → **Ici : le jeu de tâches de validation doit ressembler au jeu
   d'évaluation** (même distribution de dépôts, même difficulté). Mesurer
   l'écart dev/test explicitement, dès le début.

3. **Avoir fait confiance à un instrument biaisé.** Le banc de rejeu nous
   donnait 13 victoires sur 14 contre des équipes qui nous dominaient de
   600 points. Je m'en suis servi trois jours avant de le déclarer invalide.
   → **Ici : tout instrument doit être calibré contre une vérité connue
   avant usage**, et re-testé quand ses conclusions contredisent le classement.

4. **Avoir couru après le méta.** Adopter chaque jour l'agent public le plus
   fort donne un score éphémère : il se périme en 24-48 h parce que tout le
   monde fait pareil. Sept soumissions, sept déclins, aucune exception.
   → **Ici : construire notre propre approche, et n'emprunter au public que
   des briques vérifiées, pas la stratégie entière.**

5. **Avoir confondu marqueur et cause.** Dix fois, une métrique qui distinguait
   les forts s'est révélée être une conséquence de leur architecture, pas une
   recette transférable (tours inactifs, prix capté, taille du troupeau,
   ouverture du sommet...).
   → **Ici : avant de copier un comportement observé chez un concurrent,
   tester s'il se transpose sur NOTRE agent, toutes choses égales.**

## Les pratiques qui ont marché, à reprendre

- **Comparaison appariée** : même tâche, même graine, une seule chose qui
  change. Rapporter le nombre de cas basculés (+a / -b) et un test des signes,
  jamais une moyenne.
- **Refuser sans preuve** : sur ~90 constantes balayées, 3 gains réels. La
  valeur de l'outillage a été de **refuser** 11 fausses pistes.
- **Tout garder dans le dépôt, jamais dans /tmp** : le dossier temporaire a
  été effacé 4 fois, emportant scripts et résultats.
- **Détacher les tâches longues** (`setsid nohup`), et vérifier qu'elles ont
  survécu : plusieurs mesures ont été perdues à la fermeture de session.
- **Vérifier l'empreinte de tout code public** : trois fois, un carnet au titre
  spectaculaire était un fichier déjà connu, republié sous un autre nom.
- **Lire les règles en entier, tôt.** Deux pièges découverts tard :
  seules les 2 DERNIÈRES soumissions par date comptent (donc soumettre le
  meilleur en dernier), et le classement final est un tournoi Bradley-Terry
  rejoué après la clôture.

## Ce qu'il faut faire ici que nous n'avons pas fait là-bas

- **Un journal de décisions daté** : chaque changement, sa mesure, et la
  décision prise. Nous avons reconstruit trois fois le même raisonnement.
- **Un budget de soumissions explicite** (5/jour) et une règle d'usage.
- **Une estimation honnête du plafond de notre approche**, révisée chaque
  semaine, et l'abandon rapide d'une voie plafonnée.
