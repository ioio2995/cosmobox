# Level 3 — Pré-enregistrement de la seconde extension de troncature S=5

## 1. Statut

Ce document est le contrat scientifique normatif de la seconde extension de troncature du Level 3.

Il est gelé **avant toute construction d’un Hamiltonien physique S=5, toute diagonalisation S=5 et toute inspection d’observable S=5**.

```text
LEVEL3_SECOND_NEW_SPIN = 5
LEVEL3_NEW_CASES = triangle:S5, ring4:S5, ring5:S5
PRIMARY_PAIR = S4_TO_S5
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

La campagne S=4 précédente est complète et gelée sous :

```text
results/level3/level3-s4-truncation-extension-v1/
```

Elle constitue la référence normative S=4 de la présente extension. Les données S=2/S=3 restent celles de la campagne Level2 gelée.

## 2. Question scientifique primaire

Pour chaque géométrie et chacune des deux métriques primaires :

> Lorsque la troncature de jauge est augmentée de S=4 à S=5, la direction du contraste spectral primaire observée à S=4 persiste-t-elle, ou observe-t-on une nouvelle inversion ?

La campagne S=5 vise donc à distinguer :

- un début éventuel de stabilisation directionnelle après S=4 ;
- d’une sensibilité à la troncature qui continuerait à produire des inversions de direction.

Une persistance S4→S5 ne constitue pas, à elle seule, une preuve de convergence S→∞.

## 3. Modèle physique gelé

Les paramètres physiques restent exactement ceux des campagnes Level2 et S=4 :

```text
n_flavors = 2
J_i = 1
h = 0
t = 1
g_E = 1
K = 1
external_charges = 0
```

Aucun nouveau paramètre, observable ou terme d’Hamiltonien n’est introduit.

## 4. Géométries et cas

Exactement trois cas physiques sont pré-enregistrés :

```text
triangle:S5
ring4:S5
ring5:S5
```

Sont interdits dans cette campagne :

```text
S6
nouvelle géométrie
nouveau paramètre physique
nouvelle métrique primaire
nouveau seuil scientifique
```

## 5. Contrat spectral

Le contrat reste identique à celui de S=4 :

```text
FULL_SPECTRUM = REQUIRED
SPECTRAL_UNIT = COMPLETE_MULTIPLET
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
REGIMES = equal thirds cumulative state population
PRIMARY_CONTRAST = HIGH_MINUS_LOW
INTER_S_BRANCH_MATCHING = FORBIDDEN
```

Aucun sous-spectre, fenêtrage énergétique, matching multiplet-par-multiplet ou branche ad hoc n’est autorisé.

## 6. Métriques

Métriques primaires :

```text
M_TT
R_eff
```

Métriques de contrôle :

```text
A_QQ
M_QQ
```

Les contrôles restent descriptifs et ne peuvent ni créer, ni sauver, ni invalider un résultat primaire.

## 7. Gardes numériques

Les gardes numériques restent inchangées :

```text
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
NUMERICAL_GUARD_SCOPE = DELTA_HL_ONLY
```

Elles servent uniquement à distinguer un signe numériquement résolu d’un contraste non résolu.

Elles ne constituent pas des seuils d’effet physique.

```text
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
```

## 8. Taxonomie primaire S4→S5

Pour chaque géométrie et chaque métrique primaire X :

```text
S5_DIRECTION_PERSISTS
S5_DIRECTION_REVERSES
S5_CONTRAST_UNRESOLVED
NOT_EVALUABLE
```

Définitions :

- `S5_DIRECTION_PERSISTS` : Δ_HL(S4) et Δ_HL(S5) sont tous deux numériquement résolus et de même signe ;
- `S5_DIRECTION_REVERSES` : Δ_HL(S4) et Δ_HL(S5) sont tous deux numériquement résolus et de signes opposés ;
- `S5_CONTRAST_UNRESOLVED` : au moins le contraste S5 n’a pas de signe numériquement résolu selon la garde pré-enregistrée ;
- `NOT_EVALUABLE` : les données nécessaires ne permettent pas l’évaluation.

Aucune règle de majorité entre géométries ou entre métriques n’est définie.

## 9. Séquence directionnelle S2,S3,S4,S5

La séquence complète des quatre signes est enregistrée comme donnée descriptive primaire.

Elle sera rapportée littéralement sous la forme :

```text
S2_DIRECTION
S3_DIRECTION
S4_DIRECTION
S5_DIRECTION
```

et classée selon la transition finale S4→S5 ainsi que le nombre total d’inversions observées entre transitions successives :

```text
REVERSAL_COUNT_2345 = 0 | 1 | 2 | 3 | NOT_EVALUABLE
```

avec :

```text
REVERSAL_COUNT_2345 =
  I[sign(S2) != sign(S3)]
+ I[sign(S3) != sign(S4)]
+ I[sign(S4) != sign(S5)]
```

uniquement lorsque les quatre directions sont résolues.

Cette quantité est descriptive. Aucun nombre d’inversions n’est défini comme critère de convergence ou de non-convergence.

## 10. Descripteurs continus de stabilisation

Pour chaque métrique primaire X :

```text
T_X_34 = |Δ_HL_X(S4) - Δ_HL_X(S3)|
T_X_45 = |Δ_HL_X(S5) - Δ_HL_X(S4)|
R_DELTA_X_45_34 = T_X_45 / T_X_34    si T_X_34 > 0
```

Les descripteurs de profil sont :

```text
C_X_45
D_X_45
```

avec exactement les mêmes définitions mathématiques que `C_X_34` et `D_X_34` de la campagne S=4, appliquées au couple S4/S5.

Le rapport de distance est :

```text
R_D_X_45_34 = D_X_45 / D_X_34
```

si `D_X_34 > 0` et si les deux valeurs sont disponibles.

Ces ratios sont **strictement descriptifs**.

La valeur `1` peut être mentionnée comme référence algébrique naturelle :

- ratio < 1 : correction/distance plus petite que lors de l’étape précédente ;
- ratio > 1 : correction/distance plus grande que lors de l’étape précédente.

Mais aucun voisinage, tolérance, seuil ou classe de convergence n’est pré-enregistré autour de 1.

## 11. Références normatives antérieures

Les valeurs S=2 et S=3 doivent provenir exclusivement de la campagne Level2 gelée :

```text
results/level2/level2-energy-regime-v1/
```

Les valeurs S=4 doivent provenir exclusivement de la campagne S=4 gelée :

```text
results/level3/level3-s4-truncation-extension-v1/
```

Aucune recomputation normative de S=2, S=3 ou S=4 n’est autorisée.

Une recomputation éventuelle à des fins de non-régression logicielle ne pourrait en aucun cas remplacer ces références scientifiques gelées.

## 12. Validité d’un cas S=5

Un cas S=5 n’est valide que si :

```text
full_spectrum = true
computed_eigenvalue_count = Hilbert_dimension
full_eigenvector_matrix_available_during_observable_calculation = true
window_truncated = false
partial_subspace_count = 0
sum(multiplet_multiplicities) = Hilbert_dimension
q_coverage = [0,1]
```

et si les invariants Level0/Level1 applicables passent.

Un résultat partiel ne doit jamais être utilisé dans une comparaison normative.

## 13. Capacité numérique S=5

Le pré-enregistrement scientifique n’autorise pas encore l’exécution physique.

La capacité dense actuellement validée est :

```text
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008
```

Avant toute campagne S=5, un préflight distinct doit :

1. établir exactement les dimensions S=5 des trois géométries sans diagonalisation physique ;
2. vérifier la capacité d’encodage ;
3. vérifier que le solveur full-spectrum peut traiter la plus grande dimension ;
4. si nécessaire, étendre la limite opérationnelle dense uniquement après benchmark synthétique explicite et validation séparée ;
5. ne produire aucune observable physique S=5.

Aucune augmentation de capacité ne peut être déduite implicitement du présent document.

## 14. Interprétation autorisée

Après une future campagne S=5 complète :

```text
DIRECTIONAL_CONTINUITY_S4_TO_S5 = TESTABLE
FOUR_SPIN_REVERSAL_PATTERN = DESCRIPTIVELY_TESTABLE
TRUNCATION_SENSITIVITY_EVOLUTION = DESCRIPTIVELY_TESTABLE
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED_BY_S2_S3_S4_S5_ALONE
```

Même si S=5 conserve les directions de S=4 pour toutes les géométries et métriques, la formulation autorisée est au plus :

> début ou indice de stabilisation directionnelle sur la dernière étape observée.

Il reste interdit d’en conclure une convergence démontrée vers S→∞.

## 15. Règles anti post-hoc

Après la première construction d’un Hamiltonien physique S=5, il est interdit de modifier pour cette campagne :

- les géométries ;
- les paramètres physiques ;
- les métriques primaires ou de contrôle ;
- les régimes LOW/MID/HIGH ;
- le domaine q ;
- le contraste HIGH_MINUS_LOW ;
- les gardes numériques ;
- les taxonomies ;
- les définitions de T, R_DELTA, C, D ou R_D ;
- le contrat full-spectrum ;
- la provenance S2/S3/S4 ;
- les règles d’interprétation ;
- l’ajout de S6 dans cette campagne.

## 16. Résumé normatif

```text
LEVEL3_SECOND_NEW_SPIN = 5
LEVEL3_NEW_CASES = triangle:S5, ring4:S5, ring5:S5
PRIMARY_PAIR = S4_TO_S5

PHYSICAL_PARAMETERS = IDENTICAL_TO_LEVEL2_AND_S4
FULL_SPECTRUM = REQUIRED
PROFILE_DOMAIN = q in [0,1]
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
PRIMARY_CONTRAST = HIGH_MINUS_LOW
INTER_S_BRANCH_MATCHING = FORBIDDEN

NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN

PRIMARY_TAXONOMY =
  S5_DIRECTION_PERSISTS |
  S5_DIRECTION_REVERSES |
  S5_CONTRAST_UNRESOLVED |
  NOT_EVALUABLE

CONTINUOUS_DESCRIPTORS =
  T_X_34,
  T_X_45,
  R_DELTA_X_45_34,
  C_X_34,
  D_X_34,
  C_X_45,
  D_X_45,
  R_D_X_45_34

FOUR_SPIN_DIRECTIONAL_DESCRIPTOR = REVERSAL_COUNT_2345

S2_S3_REFERENCE = FROZEN_LEVEL2_ARTIFACTS
S4_REFERENCE = FROZEN_LEVEL3_S4_ARTIFACTS
S2_S3_S4_RECOMPUTATION = FORBIDDEN

S5_EXECUTION = NOT_AUTHORIZED_BY_THIS_PREREGISTRATION
S6_EXECUTION = FORBIDDEN

S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```
