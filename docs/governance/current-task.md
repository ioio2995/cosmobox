# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md). Le contrat scientifique actif Level 3 est désormais [`../levels/level3/s5-second-extension-preregistration.md`](../levels/level3/s5-second-extension-preregistration.md).

## État Git

```text
ACTIVE_BRANCH = research/level2-energy-regime

LEVEL3_A_SPIN_ENCODING_IMPLEMENTATION = c7e43771fdf3ed23720bfb245c8c8d3bb320a257
LEVEL3_B_GENERIC_EXECUTION_IMPLEMENTATION = ce2c7a16387490bb13ba1156249ea1129ec3bbc9
LEVEL3_E_FULL_SPECTRUM_POLICY_IMPLEMENTATION = d8281b48b836a3ce14bb05cd739ea6b22f4a7ea4
LEVEL3_F_S4_SCIENTIFIC_PREREGISTRATION = 1c1d71f07dd6a7399b3965b2bb0acfa5c665991e
LEVEL3_H_FROZEN_LEVEL2_REFERENCE_ARTIFACTS = d1515a8118e415e78e0b8f9fc98ce93b63ec26f2
LEVEL3_I_S4_CAMPAIGN_INFRASTRUCTURE = c215f5d9470daa01005dd93054f9dac991d849c7
LEVEL3_J_EXECUTION_PREFLIGHT_GOVERNANCE = f43529b624cb12339156efaa76f30e0e7e186078
LEVEL3_K_S4_NORMATIVE_CAMPAIGN_GOVERNANCE = ffb49da84111f778e45aa95b6d9e80b45d68f34c
LEVEL3_L_FROZEN_S4_REFERENCE_ARTIFACTS = 9b946b36cd302b595f16ed734c62121afbad62ff
LEVEL3_M_S5_SCIENTIFIC_PREREGISTRATION = 496ba9484a6d7df9beb738607a5ffe23a75219ad
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S5_PREREGISTERED_CAPABILITY_PREFLIGHT

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-I-S4-CAMPAIGN-INFRASTRUCTURE
LAST_ACCEPTED_EXECUTION_PREFLIGHT = L3-J-S4-CAMPAIGN-EXECUTION-PREFLIGHT
LAST_COMPLETED_NORMATIVE_CAMPAIGN = L3-K-S4-NORMATIVE-CAMPAIGN
LAST_FROZEN_REFERENCE_LOT = L3-L-FREEZE-S4-REFERENCE-ARTIFACTS
LAST_FROZEN_SCIENTIFIC_JALON = L3-M-S5-SCIENTIFIC-PREREGISTRATION

LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
UNIFORM_TRUNCATION_STABILIZATION = NOT_OBSERVED_THROUGH_S4
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED_THROUGH_S4
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Références scientifiques gelées

### S=2 / S=3

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
CAMPAIGN_STATUS = COMPLETE
REFERENCE_PATH = results/level2/level2-energy-regime-v1/
LEVEL2_RECOMPUTATION = FORBIDDEN
```

### S=4

```text
CAMPAIGN_ID = level3-s4-truncation-extension-v1
MANIFEST_FINGERPRINT = 3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba
REPOSITORY_COMMIT = ffb49da84111f778e45aa95b6d9e80b45d68f34c
CAMPAIGN_STATUS = COMPLETE
REFERENCE_PATH = results/level3/level3-s4-truncation-extension-v1/
S4_REFERENCE_VERSIONED = YES
S4_REFERENCE_SHA256_VERIFIED = YES
S4_RECOMPUTATION = FORBIDDEN
```

## Résultat S=4 accepté

```text
TRIANGLE_M_TT = S4_DIRECTION_REVERSES
TRIANGLE_R_EFF = S4_DIRECTION_REVERSES
RING4_M_TT = S4_DIRECTION_REVERSES
RING4_R_EFF = S4_DIRECTION_PERSISTS
RING5_M_TT = S4_DIRECTION_PERSISTS
RING5_R_EFF = S4_DIRECTION_PERSISTS

UNIFORM_TRUNCATION_STABILIZATION = NOT_OBSERVED
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

## Contrat scientifique S=5 gelé

Source normative :

```text
docs/levels/level3/s5-second-extension-preregistration.md
```

Contrat principal :

```text
LEVEL3_SECOND_NEW_SPIN = 5
LEVEL3_NEW_CASES = triangle:S5, ring4:S5, ring5:S5
PRIMARY_PAIR = S4_TO_S5

PHYSICAL_PARAMETERS = IDENTICAL_TO_LEVEL2_AND_S4
FULL_SPECTRUM = REQUIRED
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

S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

## Lot courant — L3-N

```text
LOT = L3-N-S5-CAPABILITY-PREFLIGHT
STATUS = OPEN
TYPE = READ_ONLY_CAPABILITY_AUDIT

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO

S5_BASIS_CAPABILITY_INSPECTION_AUTHORIZED = YES
S5_ENCODING_CAPABILITY_INSPECTION_AUTHORIZED = YES
SYNTHETIC_DENSE_SOLVER_BENCHMARK_AUTHORIZED = YES

REAL_S5_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S5_DIAGONALIZATION_AUTHORIZED = NO
S5_OBSERVABLES_AUTHORIZED = NO
LEVEL3_S5_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : établir si les trois cas S=5 pré-enregistrés sont exécutables dans le contrat full-spectrum actuel, sans produire aucune donnée physique S=5.

Le préflight doit établir exactement :

```text
- dimensions Hilbert S5 pour triangle/ring4/ring5 ;
- capacité d'encodage S5 et bits requis ;
- comparaison avec LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008 ;
- taille mémoire brute d'une matrice complexe dense pour chaque dimension ;
- capacité machine actuelle ;
- benchmark synthétique full eigensystem à la plus grande dimension S5 si celle-ci dépasse 2008 ;
- verdict sur l'extension éventuelle de la limite opérationnelle dense.
```

Aucune construction d'Hamiltonien physique S5, diagonalisation physique S5 ou observable S5 n'est autorisée.

## Invariants L3-N

```text
LEVEL2 = CLOSED
LEVEL2_ARTIFACTS = FROZEN_REFERENCE
LEVEL2_RECOMPUTATION = FORBIDDEN

S4_REFERENCE = FROZEN_AND_VERSIONED
S4_RECOMPUTATION = FORBIDDEN

S5_PREREGISTRATION = FROZEN
S5_EXECUTION = FORBIDDEN
S6_EXECUTION = FORBIDDEN

FULL_SPECTRUM = REQUIRED
SPARSE_FALLBACK = FORBIDDEN
INTER_S_BRANCH_MATCHING = FORBIDDEN

PHYSICAL_MODEL_CHANGE = NO
NEW_OBSERVABLE = NO
NEW_PRIMARY_METRIC = NO
NEW_SCIENTIFIC_THRESHOLD = NO
COMPOSITE_SCORE = FORBIDDEN

S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Étape suivante

```text
NEXT_STEP = L3_N_S5_CAPABILITY_PREFLIGHT
S5_EXECUTION = FORBIDDEN
```

Après le rapport L3-N, ChatGPT audite la capacité réelle. Si le plus grand cas S5 dépasse la limite dense actuellement validée, une extension opérationnelle séparée de cette limite pourra être autorisée uniquement après benchmark synthétique concluant. Aucun PASS de préflight n'autorise automatiquement une campagne physique S5.

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation / interpretation / audit

Claude:
software implementation / repository operations / execution explicitly authorized by mandate

Lionel:
intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un PASS, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
