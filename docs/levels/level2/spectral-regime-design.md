# Design scientifique — Level 2B : régimes spectraux

Statut : **design scientifique, non normatif**

Branche : `research/level2-energy-regime`

Ce document fait suite à `conceptual-framing.md` et à l'audit `spectral-capability-audit.md`.

## 1. Point de départ expérimental

Le préflight `L2-A1 FULL-SPECTRUM RESOURCE PREFLIGHT` a confirmé que les six cas centraux proposés pour Level 2 sont entièrement diagonalisationnables avec le chemin dense existant :

```text
triangle S=2 : 88 / 88 eigenpairs, 22 groupes complets
triangle S=3 : 128 / 128 eigenpairs, 32 groupes complets
ring4    S=2 : 292 / 292 eigenpairs, 106 groupes complets
ring4    S=3 : 432 / 432 eigenpairs, 158 groupes complets
ring5    S=2 : 1000 / 1000 eigenpairs, 226 groupes complets
ring5    S=3 : 1504 / 1504 eigenpairs, 342 groupes complets
```

Dans les six cas :

```text
solver_method = dense
window_truncated = false
partial_subspaces = 0
full_spectrum_available = yes
```

Aucune approximation spectrale nouvelle n'est donc nécessaire pour le premier test de Level 2.

## 2. Décision scientifique centrale

Level 2B abandonne comme unité principale :

```text
une branche spectrale ciblée
```

et adopte :

```text
chaque multiplet spectral complet du spectre complet
```

comme unité élémentaire de description.

Cette décision est motivée par deux faits :

1. le spectre complet est accessible pour tous les cas centraux ;
2. Level 1C a montré qu'un suivi de branche inter-Hamiltonien pouvait devenir non identifiable avant même le calcul d'une réponse physique.

Level 2 ne suit aucun état entre deux Hamiltoniens différents. Le Hamiltonien reste fixe et les observables sont étudiées comme fonctions de la position dans son spectre.

## 3. Périmètre du premier test

Le premier test Level 2 conserve :

```text
Hamiltonien : reference uniquement
J_i         : 1
h           : 0
t           : 1
g_E         : 1
K           : 1
n_flavors   : 2
charges ext : 0

geometries  : triangle, ring4, ring5
spin        : S=2, S=3
spectre     : complet
```

`S=1` n'est pas retenu comme contrôle principal : Level 1 a déjà montré qu'il constitue une troncature nettement plus forte. Il pourra rester disponible comme diagnostic secondaire ultérieur, mais il ne doit pas définir les conclusions du premier test Level 2.

## 4. Coordonnées spectrales

Deux coordonnées descriptives complémentaires sont retenues.

### 4.1 Coordonnée énergétique normalisée

Le spectre complet rendant `E_min` et `E_max` disponibles, chaque groupe spectral `g` reçoit :

\[
\epsilon_g = \frac{E_g-E_{\min}}{E_{\max}-E_{\min}}
\]

avec :

\[
0 \le \epsilon_g \le 1.
\]

`E_g` est l'énergie représentative du multiplet déjà définie par l'infrastructure spectrale existante.

Cette coordonnée décrit la position énergétique du groupe relativement à l'étendue spectrale du cas considéré.

Elle ne doit pas être interprétée comme une température.

### 4.2 Coordonnée cumulative d'états

Les multiplets ayant des multiplicités différentes, leur donner à tous le même poids déformerait la densité réelle des états du sous-espace physique.

Pour un groupe de multiplicité `d_g`, on définit donc sa position cumulative par le centre de sa masse d'états :

\[
q_g = \frac{N_{<g}+d_g/2}{D},
\]

où `N_<g` est le nombre d'états appartenant aux groupes d'énergie strictement inférieure et `D` la dimension physique totale.

Ainsi :

\[
0 < q_g < 1.
\]

`q` répond à une question différente de `epsilon` : il indique où se trouve un multiplet dans la population cumulative du spectre, indépendamment des irrégularités de l'espacement énergétique.

Les deux coordonnées doivent être conservées. Aucune ne remplace l'autre.

## 5. Unité statistique et pondération

La quantité physique est calculée sur le multiplet complet à l'aide de la moyenne canonique déjà validée :

\[
\rho_M = \Pi_M / d_M.
\]

Le groupe spectral reste donc l'unité de calcul des observables.

Pour les synthèses portant sur une fraction du spectre, le poids statistique du groupe est sa multiplicité `d_g`, car chaque valeur de groupe représente `d_g` états du sous-espace physique.

Cette pondération ne signifie pas que les états du multiplet sont physiquement distingués par l'observable ; elle évite simplement qu'un singulet et un multiplet de dimension huit comptent artificiellement comme deux observations de même poids lorsqu'on décrit la population spectrale totale.

## 6. Observable primaire

```text
PRIMARY_OBSERVABLE = C_TT_conn
```

Pour chaque multiplet complet, on conserve la matrice complète :

\[
C^{TT}_g(i,j).
\]

Level 2B ne réduit pas cette matrice à une seule amplitude avant persistance. Les diagnostics scalaires sont dérivés ensuite d'une matrice complète identifiable et conservée.

### 6.1 Force relationnelle hors diagonale

Premier diagnostic de magnitude :

\[
M_{TT}(g)=
\sqrt{\frac{1}{N(N-1)}\sum_{i\neq j} |C^{TT}_g(i,j)|^2}.
\]

Interprétation : amplitude RMS typique des corrélations connectées entre sites distincts.

Propriétés :

```text
- continue ;
- permutation-invariante ;
- aucune distance du graphe ;
- aucun seuil physique ;
- valeur nulle interprétable : absence de corrélation connectée hors diagonale.
```

Cette grandeur mesure une **force de corrélation**, pas à elle seule une organisation géométrique.

### 6.2 Concentration modale de la matrice

Une variation d'amplitude ne suffit pas pour conclure à une réorganisation. Un second diagnostic doit donc décrire la structure de la matrice indépendamment de son échelle globale.

Soient `s_k >= 0` les valeurs singulières de la matrice complète `C_TT_conn`. Si :

\[
\sum_k s_k > 0,
\]

on définit :

\[
p_k = \frac{s_k}{\sum_j s_j}
\]

et le rang effectif entropique :

\[
r_{eff}(g)=\exp\left(-\sum_k p_k\ln p_k\right).
\]

Pour comparer des géométries de tailles différentes :

\[
R_{eff}(g)=\frac{r_{eff}(g)}{N}.
\]

avec :

\[
1/N \le R_{eff} \le 1.
\]

Si la matrice est exactement nulle, `R_eff` est **NOT_AVAILABLE** avec une raison explicite (`ZERO_CTT_MATRIX`) ; aucune valeur conventionnelle n'est inventée.

Interprétation :

```text
R_eff faible  -> poids concentré dans peu de modes singuliers
R_eff élevé   -> structure répartie sur davantage de modes
```

Cette quantité est une mesure de complexité/concentration algébrique de la matrice, pas une dimension spatiale.

## 7. Observable de contrôle

```text
CONTROL_OBSERVABLE = rho_QQ
```

`rho_QQ` conserve sa sémantique de Level 1 : une paire peut être numérique ou nulle pour une raison structurelle explicite, notamment variance locale de charge nulle.

Aucune valeur nulle sémantiquement (`null`) ne doit être remplacée par zéro.

Deux diagnostics descriptifs sont retenus :

### 7.1 Fraction de paires numériques

\[
A_{QQ}(g)=\frac{N_{numeric}}{N(N-1)}.
\]

Cette quantité mesure la disponibilité structurelle de `rho_QQ` dans le multiplet.

### 7.2 Amplitude RMS conditionnelle

Si au moins une paire est numérique :

\[
M_{QQ}(g)=
\sqrt{\frac{1}{N_{numeric}}\sum_{(i,j)\;numeric}|\rho_{QQ,g}(i,j)|^2}.
\]

Sinon :

```text
M_QQ = NOT_AVAILABLE
reason = NO_NUMERIC_RHO_QQ_PAIR
```

`M_QQ` n'est jamais calculé après imputation des nulls.

## 8. Description continue avant découpage en régimes

Le résultat primaire de Level 2 doit rester un **profil spectral continu** :

```text
(q_g, epsilon_g, M_TT, R_eff, A_QQ, M_QQ)
```

pour chaque multiplet complet.

Les courbes/scatters en fonction de `q` et de `epsilon` sont descriptifs. Aucun lissage adaptatif, aucun bandwidth choisi après observation et aucune segmentation optimisée sur les données n'est autorisé pour le premier test.

Le découpage LOW/MID/HIGH ne constitue donc pas la donnée primaire.

## 9. Régimes LOW / MID / HIGH

Pour disposer d'une synthèse compacte pré-enregistrable, trois régimes sont définis uniquement à partir de la population cumulative d'états :

```text
LOW  : q in [0, 1/3)
MID  : q in [1/3, 2/3)
HIGH : q in [2/3, 1]
```

La frontière d'un multiplet peut traverser un tiers de la population. Dans ce cas, sa contribution à chaque régime est pondérée par le **nombre exact d'états du multiplet appartenant à l'intervalle de rang correspondant**. Il ne faut ni déplacer arbitrairement tout le multiplet dans un seul régime, ni scinder sa moyenne physique en nouveaux pseudo-états : seule sa pondération statistique est fractionnée.

Ces tiers sont un outil de synthèse symétrique et fixé a priori ; ils ne sont pas présentés comme des phases physiques naturelles.

## 10. Résumés par régime

Pour chaque métrique scalaire `X_g`, le résumé principal d'un régime est la moyenne pondérée par le nombre d'états représentés :

\[
\bar X_R=\frac{\sum_g w_{g,R}X_g}{\sum_g w_{g,R}},
\]

où `w_{g,R}` est le nombre d'états du multiplet `g` appartenant au régime `R` dans la comptabilité cumulative.

Pour les métriques `NOT_AVAILABLE`, aucune imputation n'est autorisée ; la fraction de poids spectral évaluable doit être publiée avec la moyenne correspondante.

Les médianes, quantiles ou barres de dispersion peuvent être produits comme diagnostics secondaires s'ils sont définis avant la campagne, mais ils ne remplacent pas ce résumé principal.

## 11. Descripteur monotone continu

Pour chaque cas et chaque métrique entièrement ou suffisamment évaluable, Level 2 pourra calculer le coefficient de rang de Spearman entre `q_g` et la métrique de groupe :

\[
\rho_S(q,X).
\]

Ce coefficient est **descriptif uniquement** :

```text
- pas de p-value ;
- pas de seuil de significance ;
- pas de conversion automatique en verdict positif/négatif ;
- pas de correction multiple.
```

Son rôle est de distinguer une tendance monotone globale d'une simple différence entre quelques fenêtres.

Le traitement exact des égalités et des métriques partiellement disponibles devra être gelé dans le pré-enregistrement avant implémentation.

## 12. Contrôle inter-S sans matching de branches

Level 2 ne réintroduit pas un appariement multiplet-par-multiplet entre `S=2` et `S=3`.

La robustesse inter-S porte sur des **profils spectraux agrégés**, notamment :

```text
- direction et forme générale du profil M_TT(q) ;
- direction et forme générale du profil R_eff(q) ;
- contraste LOW / MID / HIGH ;
- comportement du contrôle rho_QQ ;
- cohérence entre descriptions en q et en epsilon.
```

Aucun groupe `S=2` n'a besoin d'être déclaré identique à un groupe `S=3` pour effectuer cette comparaison.

Une définition numérique précise de la compatibilité inter-S sera fixée en Level 2C ; elle ne doit pas être inventée après observation des données.

## 13. Géométries

Les trois géométries `triangle`, `ring4` et `ring5` sont des **réalisations microscopiques distinctes** du laboratoire.

Le premier test ne cherche pas à les superposer par une transformation géométrique ni à identifier leurs sites.

On compare seulement la présence ou non d'une dépendance spectrale des diagnostics permutation-invariants.

Un comportement présent sur une seule géométrie reste un résultat valide mais ne pourra pas être qualifié de générique.

## 14. Ce qui constituerait une information nouvelle

Level 2 serait informatif si, après pré-enregistrement et exécution :

```text
A. M_TT varie avec la position spectrale ; et/ou
B. R_eff varie avec la position spectrale ;
C. cette organisation n'est pas immédiatement détruite entre S=2 et S=3 ;
D. le contrôle rho_QQ permet de distinguer une réorganisation générale
   d'un phénomène spécifique au canal de saveur.
```

Cela ne nécessite aucune transition nette.

Une variation continue est un résultat physique admissible.

## 15. Résultats nuls ou inconclusifs admissibles

Résultat nul valide :

> Les profils pré-enregistrés de `M_TT` et `R_eff` ne présentent pas de dépendance spectrale structurée reproductible dans les six cas étudiés.

Résultat inconclusif valide :

> La couverture évaluable des observables de contrôle, la robustesse inter-S ou un autre prérequis gelé avant campagne empêche une conclusion sur la dépendance spectrale.

Aucun résultat nul ne doit déclencher automatiquement l'ajout d'une nouvelle métrique post-hoc.

## 16. Non-claims spécifiques

Même une dépendance spectrale robuste ne démontre pas :

```text
- une géométrie émergente ;
- une dimension spatiale ;
- une transition de phase thermodynamique ;
- une température ;
- une flèche du temps ;
- une gravité ;
- une courbure ;
- une cosmologie ;
- une limite S -> infinity.
```

Elle établirait seulement que le même laboratoire quantique fini supporte des organisations relationnelles différentes selon la région de son spectre.

## 17. Décisions gelables à l'étape suivante

Le futur pré-enregistrement Level 2C pourra maintenant figer, sans regarder les observables physiques du spectre complet :

```text
- les 6 cas de campagne ;
- spectre complet obligatoire ;
- multiplets complets comme unité ;
- epsilon et q ;
- C_TT_conn primaire ;
- rho_QQ contrôle ;
- M_TT ;
- R_eff ;
- A_QQ ;
- M_QQ ;
- LOW/MID/HIGH par tiers de population ;
- moyenne pondérée par nombre d'états ;
- Spearman descriptif ;
- règle de comparaison inter-S des profils ;
- taxonomie exacte SUCCESS / NULL_RESULT / INCONCLUSIVE.
```

La seule partie encore scientifiquement ouverte avant ce gel est la **règle normative de comparaison inter-S et de décision globale**. Elle doit être conçue avant toute production des valeurs `C_TT_conn`/`rho_QQ` plein spectre.

## 18. Prochaine étape

```text
L2-B = SCIENTIFIC DESIGN COMPLETE
NEXT = L2-C PREREGISTRATION DESIGN
```

L2-C devra transformer les choix ci-dessus en contrat falsifiable, sans ajouter de métrique à moins qu'un défaut conceptuel bloquant soit identifié avant toute observation des données physiques plein spectre.
