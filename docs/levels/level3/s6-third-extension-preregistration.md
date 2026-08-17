# Level 3 — Pré-enregistrement de la troisième extension de troncature S=6

## 1. Statut

Ce document est le contrat scientifique normatif de la troisième extension de troncature du Level 3.

Il est gelé **avant toute construction d’un Hamiltonien physique S=6, toute diagonalisation S=6 et toute inspection d’observable S=6**.

```text
LEVEL3_THIRD_NEW_SPIN = 6
LEVEL3_NEW_CASES = triangle:S6, ring4:S6, ring5:S6
PRIMARY_PAIR = S5_TO_S6
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Les références normatives antérieures sont déjà gelées et versionnées :

```text
S2/S3 = results/level2/level2-energy-regime-v1/
S4    = results/level3/level3-s4-truncation-extension-v1/
S5    = results/level3/level3-s5-truncation-extension-v1/
```

Aucune recomputation normative de S=2, S=3, S=4 ou S=5 n’est autorisée pour la présente campagne.

## 2. Contexte scientifique gelé avant S=6

La campagne S=5 a établi, pour les six combinaisons géométrie × métrique primaire :

```text
S4_TO_S5_DIRECTIONAL_CONTINUITY = OBSERVED_6_OF_6
S4_TO_S5_DELTA_STEP_REDUCTION = OBSERVED_6_OF_6
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Autrement dit :

- les six contrastes primaires ont conservé à S=5 le signe observé à S=4 ;
- pour les six contrastes primaires, la correction |Δ_HL(S5)-Δ_HL(S4)| est inférieure à la correction |Δ_HL(S4)-Δ_HL(S3)| ;
- les profils spectraux détaillés S4/S5 restent fortement sensibles à la troncature et ne montrent pas de stabilisation systématique.

Ce contexte constitue le point de départ scientifique du présent pré-enregistrement. Il ne doit pas être réinterprété post-hoc après observation de S=6.

## 3. Question scientifique primaire

Pour chaque géométrie et chacune des deux métriques primaires :

> Lorsque la troncature de jauge est augmentée de S=5 à S=6, la direction du contraste spectral primaire observée à S=5 persiste-t-elle, ou observe-t-on une nouvelle inversion ?

La campagne S=6 teste donc si la continuité uniforme apparue sur la transition S4→S5 :

- se prolonge sur une seconde transition successive S5→S6 ;
- ou se révèle transitoire par une nouvelle inversion de direction.

Une persistance S5→S6, même observée pour les six combinaisons géométrie × métrique, ne constitue pas à elle seule une preuve de convergence S→∞.

## 4. Question quantitative secondaire pré-enregistrée

Pour chaque métrique primaire X, on testera descriptivement si la taille de la correction du contraste continue à diminuer :

```text
T_X_45 = |Δ_HL_X(S5) - Δ_HL_X(S4)|
T_X_56 = |Δ_HL_X(S6) - Δ_HL_X(S5)|
R_DELTA_X_56_45 = T_X_56 / T_X_45    si T_X_45 > 0
```

La relation algébrique :

```text
T_X_56 < T_X_45
```

peut être décrite comme une correction adjacente plus faible que lors de l’étape précédente.

Elle n’est **pas** un seuil de convergence, ni un PASS scientifique autonome.

## 5. Modèle physique gelé

Les paramètres physiques restent exactement ceux des campagnes Level2, S=4 et S=5 :

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
triangle:S6
ring4:S6
ring5:S6
```

Sont interdits dans cette campagne :

```text
S7
nouvelle géométrie
nouveau paramètre physique
nouvelle métrique primaire
nouveau seuil scientifique
```

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

Les contrôles restent descriptifs et ne peuvent ni créer, ni sauver, ni invalider un résultat primaire.

## 9. Gardes numériques

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

## 10. Taxonomie primaire S5→S6

Pour chaque géométrie et chaque métrique primaire X :

```text
S6_DIRECTION_PERSISTS
S6_DIRECTION_REVERSES
S6_CONTRAST_UNRESOLVED
NOT_EVALUABLE
```

Définitions :

- `S6_DIRECTION_PERSISTS` : Δ_HL(S5) et Δ_HL(S6) sont tous deux numériquement résolus et de même signe ;
- `S6_DIRECTION_REVERSES` : Δ_HL(S5) et Δ_HL(S6) sont tous deux numériquement résolus et de signes opposés ;
- `S6_CONTRAST_UNRESOLVED` : au moins le contraste S6 n’a pas de signe numériquement résolu selon la garde pré-enregistrée ;
- `NOT_EVALUABLE` : les données nécessaires ne permettent pas l’évaluation.

Aucune règle de majorité entre géométries ou entre métriques n’est définie.

## 11. Séquence directionnelle S2,S3,S4,S5,S6

La séquence complète des cinq signes est enregistrée comme donnée descriptive primaire :

```text
S2_DIRECTION
S3_DIRECTION
S4_DIRECTION
S5_DIRECTION
S6_DIRECTION
```

Le nombre total d’inversions entre transitions successives est :

```text
REVERSAL_COUNT_23456 = 0 | 1 | 2 | 3 | 4 | NOT_EVALUABLE
```

avec :

```text
REVERSAL_COUNT_23456 =
  I[sign(S2) != sign(S3)]
+ I[sign(S3) != sign(S4)]
+ I[sign(S4) != sign(S5)]
+ I[sign(S5) != sign(S6)]
```

uniquement lorsque les cinq directions sont résolues.

Cette quantité est descriptive. Aucun nombre d’inversions n’est défini comme critère de convergence ou de non-convergence.

## 12. Continuité sur les deux dernières transitions

Afin de tester explicitement le caractère durable ou transitoire du signal observé à S=5, on enregistrera pour chaque géométrie et métrique primaire :

```text
LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS = YES | NO | NOT_EVALUABLE
```

avec :

```text
YES
si sign(S4) = sign(S5) = sign(S6)

NO
si les trois signes sont résolus et au moins une des transitions S4→S5 ou S5→S6 change de signe

NOT_EVALUABLE
si l’un des trois signes n’est pas résolu
```

Ce descripteur est strictement descriptif. Il ne constitue pas un critère de convergence S→∞.

## 13. Descripteurs continus de stabilisation

Pour chaque métrique primaire X :

```text
T_X_45 = |Δ_HL_X(S5) - Δ_HL_X(S4)|
T_X_56 = |Δ_HL_X(S6) - Δ_HL_X(S5)|
R_DELTA_X_56_45 = T_X_56 / T_X_45    si T_X_45 > 0
```

Les descripteurs de profil sont :

```text
C_X_56
D_X_56
```

avec exactement les mêmes définitions mathématiques que `C_X_45` et `D_X_45`, appliquées au couple S5/S6.

Le rapport de distance est :

```text
R_D_X_56_45 = D_X_56 / D_X_45
```

si `D_X_45 > 0` et si les deux valeurs sont disponibles.

Ces ratios sont **strictement descriptifs**.

La valeur `1` reste uniquement une référence algébrique naturelle :

- ratio < 1 : correction/distance plus petite que lors de l’étape précédente ;
- ratio > 1 : correction/distance plus grande que lors de l’étape précédente.

Aucun voisinage, tolérance, seuil ou classe de convergence n’est défini autour de 1.

## 14. Références normatives antérieures

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

Les cinq hashes SHA-256 normatifs S=5 sont :

```text
manifest.json          = 1754ca2758807d2dbc0464668c298e7a3f22fc81d6143a2304b0167ffb291e39
campaign-summary.json  = a50b159d54c5b49fc0ac385ed2a90839ef1f758ff003b0ee3bec4eb5734792f9
cases/triangle-S5.json = e453764e62f982032b701f035923de9a60ade924c5f9d1026449e84375f29400
cases/ring4-S5.json    = c75bad9fda8f7c32e7f4a3b7d42b192d264c515e42cfbffa8eae30d0ffec1389
cases/ring5-S5.json    = 3ab452a0bc41e57d2c4482ae6431506fbb7bbd6a723442aadb40d9b3ece2abdb
```

Aucune recomputation normative de S=2, S=3, S=4 ou S=5 n’est autorisée.

## 15. Validité d’un cas S=6

Un cas S=6 n’est valide que si :

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

## 16. Capacité numérique S=6

Le pré-enregistrement scientifique n’autorise pas encore l’exécution physique.

La capacité dense actuellement validée est :

```text
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2512
```

Avant toute campagne S=6, un préflight distinct doit :

1. établir exactement les dimensions S=6 des trois géométries par construction de base uniquement ;
2. vérifier la capacité d’encodage et les bits requis ;
3. comparer les dimensions S=6 à la limite dense validée 2512 ;
4. si la plus grande dimension dépasse 2512, exécuter un benchmark dense synthétique à cette dimension ;
5. étendre la limite opérationnelle uniquement dans un lot logiciel distinct après benchmark concluant ;
6. ne produire aucune observable physique S=6.

Aucune dimension S=6 ne doit être déduite normativement par simple extrapolation des dimensions S=2…S=5.

## 17. Interprétation autorisée après une future campagne S=6 complète

Après une future campagne S=6 complète :

```text
DIRECTIONAL_CONTINUITY_S5_TO_S6 = TESTABLE
TWO_STEP_DIRECTIONAL_CONTINUITY_S4_TO_S6 = DESCRIPTIVELY_TESTABLE
FIVE_SPIN_REVERSAL_PATTERN = DESCRIPTIVELY_TESTABLE
DELTA_STEP_EVOLUTION = DESCRIPTIVELY_TESTABLE
TRUNCATION_PROFILE_SENSITIVITY_EVOLUTION = DESCRIPTIVELY_TESTABLE
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED_BY_S2_S3_S4_S5_S6_ALONE
```

Si les six directions persistent encore de S=5 à S=6 et si les corrections T_X_56 sont toutes ou majoritairement inférieures à T_X_45, la formulation autorisée est au plus :

> le signal de stabilisation tardive des contrastes spectraux agrégés observé à S=5 est renforcé sur une seconde transition successive.

Cette formulation ne constitue toujours pas une démonstration de convergence vers S→∞.

Si une ou plusieurs directions s’inversent à S=6, le résultat doit être rapporté tel quel comme persistance de la sensibilité à la troncature, sans redéfinir post-hoc un sous-ensemble favorable.

## 18. Règles anti post-hoc

Après la première construction d’un Hamiltonien physique S=6, il est interdit de modifier pour cette campagne :

- les géométries ;
- les paramètres physiques ;
- les métriques primaires ou de contrôle ;
- les régimes LOW/MID/HIGH ;
- le domaine q ;
- le contraste HIGH_MINUS_LOW ;
- les gardes numériques ;
- les taxonomies ;
- les définitions de T, R_DELTA, C, D ou R_D ;
- la définition de REVERSAL_COUNT_23456 ;
- la définition de LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS ;
- le contrat full-spectrum ;
- la provenance S2/S3/S4/S5 ;
- les règles d’interprétation ;
- l’ajout de S7 dans cette campagne.

## 19. Résumé normatif

```text
LEVEL3_THIRD_NEW_SPIN = 6
LEVEL3_NEW_CASES = triangle:S6, ring4:S6, ring5:S6
PRIMARY_PAIR = S5_TO_S6

PHYSICAL_PARAMETERS = IDENTICAL_TO_LEVEL2_S4_S5
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
  S6_DIRECTION_PERSISTS |
  S6_DIRECTION_REVERSES |
  S6_CONTRAST_UNRESOLVED |
  NOT_EVALUABLE

CONTINUOUS_DESCRIPTORS =
  T_X_45,
  T_X_56,
  R_DELTA_X_56_45,
  C_X_45,
  D_X_45,
  C_X_56,
  D_X_56,
  R_D_X_56_45

FIVE_SPIN_DIRECTIONAL_DESCRIPTOR = REVERSAL_COUNT_23456
TWO_STEP_DIRECTIONAL_DESCRIPTOR = LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS

S2_S3_REFERENCE = FROZEN_LEVEL2_ARTIFACTS
S4_REFERENCE = FROZEN_LEVEL3_S4_ARTIFACTS
S5_REFERENCE = FROZEN_LEVEL3_S5_ARTIFACTS
S2_S3_S4_S5_RECOMPUTATION = FORBIDDEN

S6_EXECUTION = NOT_AUTHORIZED_BY_THIS_PREREGISTRATION
S7_EXECUTION = FORBIDDEN

S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```
