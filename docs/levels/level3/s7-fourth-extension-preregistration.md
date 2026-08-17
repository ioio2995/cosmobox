# Level 3 — Pré-enregistrement de la quatrième extension de troncature S=7

## 1. Statut

Ce document est le contrat scientifique normatif de la quatrième extension de troncature du Level 3.

Il est gelé **avant toute construction d’un Hamiltonien physique S=7, toute diagonalisation S=7 et toute inspection d’observable S=7**.

```text
LEVEL3_FOURTH_NEW_SPIN = 7
LEVEL3_NEW_CASES = triangle:S7, ring4:S7, ring5:S7
PRIMARY_PAIR = S6_TO_S7
PRIMARY_SCIENTIFIC_OBJECTIVE = TEST_TRUNCATION_STRUCTURE
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Les références normatives antérieures sont gelées et versionnées :

```text
S2/S3 = results/level2/level2-energy-regime-v1/
S4    = results/level3/level3-s4-truncation-extension-v1/
S5    = results/level3/level3-s5-truncation-extension-v1/
S6    = results/level3/level3-s6-truncation-extension-v1/
```

Aucune recomputation normative de S=2, S=3, S=4, S=5 ou S=6 n’est autorisée.

## 2. Contexte scientifique gelé avant S=7

La campagne S=6 a établi :

```text
S5_TO_S6_DIRECTIONAL_CONTINUITY = OBSERVED_4_OF_6
S5_TO_S6_DIRECTIONAL_REVERSAL = OBSERVED_2_OF_6
S5_TO_S6_DELTA_STEP_REDUCTION = OBSERVED_2_OF_6
UNIFORM_LATE_STABILIZATION = NOT_SUPPORTED
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED_THROUGH_S6
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Les deux inversions S5→S6 concernent les deux métriques primaires du triangle.

Séquences directionnelles primaires gelées :

```text
triangle / M_TT  = NEGATIVE, NEGATIVE, POSITIVE, POSITIVE, NEGATIVE
triangle / R_eff = POSITIVE, POSITIVE, NEGATIVE, NEGATIVE, POSITIVE

ring4 / M_TT     = NEGATIVE, NEGATIVE, POSITIVE, POSITIVE, POSITIVE
ring4 / R_eff    = NEGATIVE, NEGATIVE, NEGATIVE, NEGATIVE, NEGATIVE

ring5 / M_TT     = NEGATIVE, POSITIVE, POSITIVE, POSITIVE, POSITIVE
ring5 / R_eff    = POSITIVE, NEGATIVE, NEGATIVE, NEGATIVE, NEGATIVE
```

Les corrections adjacentes ont évolué de manière non uniforme :

```text
T_56 < T_45 = OBSERVED_2_OF_6
T_56 > T_45 = OBSERVED_4_OF_6
```

Les deux cas où `T_56 < T_45` sont les deux métriques primaires de ring5.

Ce contexte est gelé avant S=7 et ne peut pas être redéfini post-hoc.

## 3. Question scientifique primaire

La campagne S=7 ne cherche pas à démontrer directement une convergence vers `S→∞`.

La question primaire est :

> Lorsque la troncature de jauge est augmentée de S=6 à S=7, la structure géométriquement différenciée observée jusqu’à S=6 persiste-t-elle, se réorganise-t-elle, ou révèle-t-elle un motif directionnel supplémentaire ?

Pour chaque géométrie et chacune des deux métriques primaires, on testera d’abord si le signe du contraste S=6 :

- persiste à S=7 ;
- s’inverse à S=7 ;
- devient numériquement non résolu.

La transition primaire reste exclusivement :

```text
PRIMARY_PAIR = S6_TO_S7
```

Aucune conclusion de convergence ne peut être produite à partir de la seule persistance S6→S7.

## 4. Hypothèses descriptives ciblées pré-enregistrées

### 4.1 Triangle — motif par blocs de deux troncatures

Les deux métriques primaires du triangle présentent avant S=7 :

```text
S2,S3 = même direction
S4,S5 = même direction opposée à S2,S3
S6     = retour à la direction de S2,S3
```

S=7 permet de tester, sans le supposer, si le motif descriptif suivant apparaît :

```text
A,A | B,B | A,A
```

Ce motif sera testé par un descripteur générique défini à la section 13 :

```text
PAIRWISE_BLOCK_RECURRENCE_23_45_67
```

Il ne constitue ni une périodicité démontrée, ni une loi de parité, ni une preuve de convergence.

### 4.2 Ring4 — direction et amplitude séparées

À S=6, ring4 conserve les directions S=5 pour les deux métriques primaires, mais :

```text
T_56 > T_45
```

pour les deux métriques.

S=7 permettra de distinguer descriptivement :

- la continuité de direction S6→S7 ;
- l’évolution indépendante de la taille de correction `T_67`.

Aucune stabilité de signe ne sera assimilée à une stabilisation d’amplitude.

### 4.3 Ring5 — poursuite éventuelle de la réduction locale

Ring5 est la seule géométrie pour laquelle, à S=6, les deux métriques primaires satisfont simultanément :

```text
S5_TO_S6_DIRECTION = PERSISTS
T_56 < T_45
```

S=7 testera descriptivement si :

```text
T_67 < T_56
```

pour l’une ou les deux métriques primaires.

Même si cette relation est observée, elle ne constitue pas une preuve de convergence.

## 5. Modèle physique gelé

Les paramètres physiques restent exactement ceux des campagnes précédentes :

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

## 6. Géométries et cas

Exactement trois cas physiques sont pré-enregistrés :

```text
triangle:S7
ring4:S7
ring5:S7
```

Sont interdits dans cette campagne :

```text
S8
nouvelle géométrie
nouveau paramètre physique
nouvelle métrique primaire
nouveau contrôle
nouveau seuil scientifique
```

S8 n’est pas autorisé implicitement par un résultat S7, quel qu’il soit.

## 7. Contrat spectral

Le contrat reste identique aux campagnes précédentes :

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

## 8. Métriques

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

Les contrôles restent strictement descriptifs et ne peuvent ni créer, ni sauver, ni invalider un résultat primaire.

## 9. Gardes numériques

Les gardes numériques restent inchangées :

```text
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
NUMERICAL_GUARD_SCOPE = DELTA_HL_ONLY
```

Elles servent uniquement à distinguer un signe numériquement résolu d’un contraste non résolu.

```text
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
```

## 10. Taxonomie primaire S6→S7

Pour chaque géométrie et chaque métrique primaire X :

```text
S7_DIRECTION_PERSISTS
S7_DIRECTION_REVERSES
S7_CONTRAST_UNRESOLVED
NOT_EVALUABLE
```

Définitions :

- `S7_DIRECTION_PERSISTS` : Δ_HL(S6) et Δ_HL(S7) sont tous deux numériquement résolus et de même signe ;
- `S7_DIRECTION_REVERSES` : Δ_HL(S6) et Δ_HL(S7) sont tous deux numériquement résolus et de signes opposés ;
- `S7_CONTRAST_UNRESOLVED` : au moins le contraste S7 n’a pas de signe numériquement résolu selon la garde pré-enregistrée ;
- `NOT_EVALUABLE` : les données nécessaires ne permettent pas l’évaluation.

Aucune règle de majorité inter-géométries ou inter-métriques n’est définie.

## 11. Séquence directionnelle S2…S7

La séquence complète des six signes est enregistrée :

```text
S2_DIRECTION
S3_DIRECTION
S4_DIRECTION
S5_DIRECTION
S6_DIRECTION
S7_DIRECTION
```

Le nombre total d’inversions successives est :

```text
REVERSAL_COUNT_234567 = 0 | 1 | 2 | 3 | 4 | 5 | NOT_EVALUABLE
```

avec :

```text
REVERSAL_COUNT_234567 =
  I[sign(S2) != sign(S3)]
+ I[sign(S3) != sign(S4)]
+ I[sign(S4) != sign(S5)]
+ I[sign(S5) != sign(S6)]
+ I[sign(S6) != sign(S7)]
```

uniquement lorsque les six directions sont résolues.

Ce descripteur reste strictement descriptif.

## 12. Continuité sur les deux dernières transitions

Pour chaque géométrie et métrique primaire :

```text
LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS_567 = YES | NO | NOT_EVALUABLE
```

avec :

```text
YES
si sign(S5) = sign(S6) = sign(S7)

NO
si les trois signes sont résolus et au moins une des transitions S5→S6 ou S6→S7 change de signe

NOT_EVALUABLE
si l’un des trois signes n’est pas résolu
```

Ce descripteur n’est pas un critère de convergence.

## 13. Descripteur de récurrence par blocs 23|45|67

Pour chaque géométrie et métrique primaire :

```text
PAIRWISE_BLOCK_RECURRENCE_23_45_67 = YES | NO | NOT_EVALUABLE
```

`YES` si et seulement si les six signes sont résolus et :

```text
sign(S2) = sign(S3)
sign(S4) = sign(S5)
sign(S6) = sign(S7)
sign(S2) != sign(S4)
sign(S2) = sign(S6)
```

Autrement dit, la séquence directionnelle est de la forme :

```text
A,A | B,B | A,A
```

`NO` si les six signes sont résolus mais qu’au moins une de ces égalités/inégalités n’est pas satisfaite.

`NOT_EVALUABLE` si au moins un signe n’est pas résolu.

Ce descripteur est pré-enregistré pour tester une structure finie observée comme possibilité après S6. Il ne démontre ni périodicité asymptotique, ni effet de parité, ni convergence.

## 14. Descripteurs continus S6→S7

Pour chaque métrique primaire X :

```text
T_X_56 = |Δ_HL_X(S6) - Δ_HL_X(S5)|
T_X_67 = |Δ_HL_X(S7) - Δ_HL_X(S6)|
R_DELTA_X_67_56 = T_X_67 / T_X_56    si T_X_56 > 0
```

Les descripteurs de profil sont :

```text
C_X_56
D_X_56
C_X_67
D_X_67
```

avec les mêmes définitions mathématiques historiques appliquées respectivement aux couples S5/S6 et S6/S7.

Le rapport de distance est :

```text
R_D_X_67_56 = D_X_67 / D_X_56
```

si `D_X_56 > 0` et si les deux valeurs sont disponibles.

Tous ces descripteurs sont strictement descriptifs.

La valeur `1` est uniquement une référence algébrique naturelle : aucun seuil, voisinage ou classe de convergence n’est défini autour de 1.

## 15. Références normatives antérieures

Les valeurs S=2 et S=3 doivent provenir exclusivement de :

```text
results/level2/level2-energy-regime-v1/
```

Les valeurs S=4 doivent provenir exclusivement de :

```text
results/level3/level3-s4-truncation-extension-v1/
```

Les valeurs S=5 doivent provenir exclusivement de :

```text
results/level3/level3-s5-truncation-extension-v1/
```

Les valeurs S=6 doivent provenir exclusivement de :

```text
results/level3/level3-s6-truncation-extension-v1/
```

Hashes SHA-256 normatifs S=6 :

```text
manifest.json          = 45c01569c67b7386dc6c63be957a4f759158d5042ffc06c351f3e1982fc6599d
campaign-summary.json  = 34fe0487006ece2a903fc4c4c9e733762aba0129d893849e30f7a53c2087810f
cases/triangle-S6.json = 7b4f5aa82ddd1b84e8e1cf868d9b1a74027126f192b78facfd728ef72e686763
cases/ring4-S6.json    = 79a38a3e9523cd119d7096ee3ac6003f4c48dc4978bdb25a3d2a5c3ea432eea1
cases/ring5-S6.json    = 660797b62c3081cfa65320827101e9c27e1d42b73569bb49e8068b6db693fb5f
```

S6 frozen-reference commit :

```text
689a74dc9768f27843a4b9e8599947aa11c364b8
```

Aucune recomputation normative S2…S6 n’est autorisée.

## 16. Validité d’un cas S=7

Un cas S=7 n’est valide que si :

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

## 17. Capacité numérique S=7

Le présent pré-enregistrement **n’autorise aucune exécution physique S=7**.

La capacité dense Level3 actuellement validée est :

```text
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 3016
```

Avant toute campagne S=7, un préflight distinct doit :

1. construire réellement les bases S=7 pour triangle/ring4/ring5, sans Hamiltonien physique ;
2. établir les dimensions exactes ;
3. vérifier `validate_spin(7)` et `flux_bits_per_edge(7)` ;
4. vérifier les bits requis et `MAX_KEY_BITS` ;
5. calculer les tailles brutes `D*D*16` ;
6. comparer les dimensions à la limite dense validée 3016 ;
7. si la plus grande dimension dépasse 3016, effectuer un benchmark Hermitien dense synthétique exactement à cette dimension ;
8. déterminer si une extension de capacité Level3 séparée est nécessaire et faisable ;
9. ne construire aucun Hamiltonien physique S=7 ;
10. ne diagonaliser aucun cas physique S=7 ;
11. ne calculer aucune observable S=7.

Aucune dimension S=7 ne doit être déduite normativement par extrapolation de la suite S2…S6.

## 18. Interprétation autorisée après une future campagne S=7 complète

Après une future campagne complète :

```text
DIRECTIONAL_CONTINUITY_S6_TO_S7 = TESTABLE
SIX_SPIN_REVERSAL_PATTERN = DESCRIPTIVELY_TESTABLE
PAIRWISE_BLOCK_RECURRENCE_23_45_67 = DESCRIPTIVELY_TESTABLE
DELTA_STEP_EVOLUTION_56_TO_67 = DESCRIPTIVELY_TESTABLE
TRUNCATION_PROFILE_SENSITIVITY_67 = DESCRIPTIVELY_TESTABLE
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED_BY_S2_TO_S7_ALONE
```

Interprétations pré-enregistrées :

1. **Triangle** : si `PAIRWISE_BLOCK_RECURRENCE_23_45_67 = YES` pour une ou les deux métriques, on peut rapporter qu’une récurrence directionnelle finie par blocs `AA|BB|AA` est observée jusqu’à S=7. Il est interdit de la qualifier de périodicité asymptotique sans données supplémentaires.

2. **Ring4** : une persistance S6→S7 accompagnée de `T_67 >= T_56` doit être décrite comme continuité de direction sans réduction de correction. Une persistance avec `T_67 < T_56` peut être décrite comme réduction locale de correction, sans convergence.

3. **Ring5** : si la direction persiste et `T_67 < T_56`, on peut rapporter une troisième étape compatible avec une réduction locale successive des corrections agrégées depuis S4. Cela reste insuffisant pour établir S→∞.

4. Si une ou plusieurs directions s’inversent à S=7, elles doivent être rapportées sans redéfinir post-hoc un sous-ensemble favorable.

5. Les profils `C_67`, `D_67` et `R_D_67_56` restent indépendants des contrastes agrégés et ne peuvent être fusionnés dans un score composite.

6. **Aucun résultat S7 n’autorise automatiquement S8.** Après S7, une revue scientifique explicite doit décider s’il est pertinent de poursuivre en S ou de changer d’approche analytique.

## 19. Règles anti post-hoc

Après la première construction d’un Hamiltonien physique S=7, il est interdit de modifier pour cette campagne :

- les géométries ;
- les paramètres physiques ;
- les métriques primaires ou de contrôle ;
- les régimes LOW/MID/HIGH ;
- le domaine q ;
- le contraste HIGH_MINUS_LOW ;
- les gardes numériques ;
- la taxonomie S6→S7 ;
- `REVERSAL_COUNT_234567` ;
- `LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS_567` ;
- `PAIRWISE_BLOCK_RECURRENCE_23_45_67` ;
- les définitions de T, R_DELTA, C, D et R_D ;
- le contrat full-spectrum ;
- la provenance S2…S6 ;
- les règles d’interprétation ;
- l’ajout de S8.

## 20. Résumé normatif

```text
LEVEL3_FOURTH_NEW_SPIN = 7
LEVEL3_NEW_CASES = triangle:S7, ring4:S7, ring5:S7
PRIMARY_PAIR = S6_TO_S7
PRIMARY_SCIENTIFIC_OBJECTIVE = TEST_TRUNCATION_STRUCTURE

PHYSICAL_PARAMETERS = IDENTICAL_TO_LEVEL2_S4_S5_S6
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
  S7_DIRECTION_PERSISTS |
  S7_DIRECTION_REVERSES |
  S7_CONTRAST_UNRESOLVED |
  NOT_EVALUABLE

SIX_SPIN_DIRECTIONAL_DESCRIPTOR = REVERSAL_COUNT_234567
LAST_TWO_TRANSITIONS_DESCRIPTOR = LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS_567
PAIRWISE_BLOCK_DESCRIPTOR = PAIRWISE_BLOCK_RECURRENCE_23_45_67

CONTINUOUS_DESCRIPTORS =
  T_X_56,
  T_X_67,
  R_DELTA_X_67_56,
  C_X_56,
  D_X_56,
  C_X_67,
  D_X_67,
  R_D_X_67_56

S2_S3_REFERENCE = FROZEN_LEVEL2_ARTIFACTS
S4_REFERENCE = FROZEN_LEVEL3_S4_ARTIFACTS
S5_REFERENCE = FROZEN_LEVEL3_S5_ARTIFACTS
S6_REFERENCE = FROZEN_LEVEL3_S6_ARTIFACTS
S2_TO_S6_RECOMPUTATION = FORBIDDEN

LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 3016
S7_EXECUTION = NOT_AUTHORIZED_BY_THIS_PREREGISTRATION
S8_EXECUTION = FORBIDDEN

S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED_BY_S2_TO_S7_ALONE

POST_S7_SCIENTIFIC_REVIEW_REQUIRED = YES
AUTO_S8 = FORBIDDEN
```
