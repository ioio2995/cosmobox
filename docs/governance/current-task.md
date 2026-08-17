# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. Le contrat scientifique actif Level 3 est désormais [`../levels/level3/s6-third-extension-preregistration.md`](../levels/level3/s6-third-extension-preregistration.md).

## État Git

```text
ACTIVE_BRANCH = research/level2-energy-regime

LEVEL3_L_FROZEN_S4_REFERENCE_ARTIFACTS = 9b946b36cd302b595f16ed734c62121afbad62ff
LEVEL3_M_S5_SCIENTIFIC_PREREGISTRATION = 496ba9484a6d7df9beb738607a5ffe23a75219ad
LEVEL3_N_S5_CAPABILITY_PREFLIGHT_GOVERNANCE = 7793bfcef52924561b3d4947a39fdb857b23c614
LEVEL3_O_DENSE_CAPABILITY_2512 = 8f9c6e6a3d1b841ce862f81741cf8031693dc26f
LEVEL3_P_S5_CAMPAIGN_INFRASTRUCTURE = 9b9cf69ad84b5655c80be3085c4c1f1bcd15982b
LEVEL3_Q_S5_EXECUTION_PREFLIGHT_GOVERNANCE = 263663c0ac208dd0521901bd88f0f2b5696c6270
LEVEL3_R_S5_NORMATIVE_CAMPAIGN_GOVERNANCE = 782f29eb9dcbc21ca2168e109997b0f59a12402f
LEVEL3_S_FROZEN_S5_REFERENCE_ARTIFACTS = 7239efe1708535d09d779ee95eb024f9233d9242
LEVEL3_T_S6_SCIENTIFIC_PREREGISTRATION = 1c19a01e051c3df6f547afe0816a795989fdac3b
LEVEL3_U_S6_CAPABILITY_PREFLIGHT_GOVERNANCE = 2dd5765121964054de4a12395932600d69c17be6
LEVEL3_V_DENSE_CAPABILITY_3016 = 1bda37eac844cc9b603de25ccf595581428a061b
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S6_CAMPAIGN_INFRASTRUCTURE

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-V-EXTEND-DENSE-CAPABILITY-TO-3016
LAST_ACCEPTED_EXECUTION_PREFLIGHT = L3-Q-S5-CAMPAIGN-EXECUTION-PREFLIGHT
LAST_COMPLETED_NORMATIVE_CAMPAIGN = L3-R-S5-NORMATIVE-CAMPAIGN
LAST_FROZEN_REFERENCE_LOT = L3-S-FREEZE-S5-REFERENCE-ARTIFACTS
LAST_FROZEN_SCIENTIFIC_JALON = L3-T-S6-SCIENTIFIC-PREREGISTRATION
LAST_ACCEPTED_CAPABILITY_PREFLIGHT = L3-U-S6-CAPABILITY-PREFLIGHT

S4_TO_S5_DIRECTIONAL_CONTINUITY = OBSERVED_6_OF_6
S4_TO_S5_DELTA_STEP_REDUCTION = OBSERVED_6_OF_6
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED_THROUGH_S5
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Références scientifiques gelées

```text
S2_S3_REFERENCE = results/level2/level2-energy-regime-v1/
S4_REFERENCE = results/level3/level3-s4-truncation-extension-v1/
S5_REFERENCE = results/level3/level3-s5-truncation-extension-v1/

S2_S3_S4_S5_RECOMPUTATION = FORBIDDEN
```

## Contrat scientifique S=6 gelé

Source normative :

```text
docs/levels/level3/s6-third-extension-preregistration.md
```

```text
LEVEL3_THIRD_NEW_SPIN = 6
LEVEL3_NEW_CASES = triangle:S6, ring4:S6, ring5:S6
PRIMARY_PAIR = S5_TO_S6
PHYSICAL_PARAMETERS = IDENTICAL_TO_LEVEL2_S4_S5
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
FIVE_SPIN_DIRECTIONAL_DESCRIPTOR = REVERSAL_COUNT_23456
TWO_STEP_DIRECTIONAL_DESCRIPTOR = LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS
CONTINUOUS_DESCRIPTORS = T_X_45,T_X_56,R_DELTA_X_56_45,C_X_45,D_X_45,C_X_56,D_X_56,R_D_X_56_45
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

## Capacité S=6 acceptée

```text
TRIANGLE_S6_DIMENSION = 248
RING4_S6_DIMENSION = 852
RING5_S6_DIMENSION = 3016
S6_ENCODING_SUPPORTED = YES
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 3016
D3016_ACCEPTED_BY_GUARD = YES
D3017_REJECTED_BY_GUARD = YES
FULL_SPECTRUM_POLICY_UNCHANGED = YES
SPARSE_FALLBACK_POSSIBLE = NO
```

## Lot courant — L3-W

```text
LOT = L3-W-S6-CAMPAIGN-INFRASTRUCTURE
STATUS = OPEN
TYPE = SOFTWARE_IMPLEMENTATION

CODE_CHANGE_AUTHORIZED = YES
COMMIT_AUTHORIZED = YES
PUSH_AUTHORIZED = YES

REAL_S6_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S6_DIAGONALIZATION_AUTHORIZED = NO
S6_OBSERVABLES_AUTHORIZED = NO
LEVEL3_S6_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
S7_EXECUTION_AUTHORIZED = NO
```

Objectif : implémenter l'infrastructure logicielle complète de la campagne normative S=6 conformément au pré-enregistrement gelé, sans produire aucune donnée physique S=6.

La future campagne doit exécuter exactement :

```text
triangle:S6
ring4:S6
ring5:S6
```

et utiliser exclusivement les références gelées antérieures :

```text
S2/S3 depuis Level2
S4 depuis la campagne Level3 S4 gelée
S5 depuis la campagne Level3 S5 gelée
```

Aucune recomputation normative S2/S3/S4/S5 n'est autorisée.

L'infrastructure doit permettre après une future exécution S6 complète :

```text
- comparaison primaire S5→S6 ;
- direction_s2 ... direction_s6 ;
- taxonomie S6 pré-enregistrée ;
- REVERSAL_COUNT_23456 ;
- LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS ;
- T_X_45, T_X_56, R_DELTA_X_56_45 ;
- C_X_45, D_X_45, C_X_56, D_X_56, R_D_X_56_45 ;
- complétude 3/3 avant toute comparaison normative ;
- campaign-summary.json écrit en dernier ;
- NO_IMPLICIT_RESUME.
```

Toute implémentation ou test S=6 dans ce lot doit être synthétique ou monkeypatché avant toute primitive physique réelle.

## Invariants L3-W

```text
LEVEL2 = CLOSED
LEVEL2_REFERENCE = FROZEN
LEVEL2_RECOMPUTATION = FORBIDDEN

S4_REFERENCE = FROZEN_AND_VERSIONED
S4_RECOMPUTATION = FORBIDDEN

S5_REFERENCE = FROZEN_AND_VERSIONED
S5_RECOMPUTATION = FORBIDDEN

S6_PREREGISTRATION = FROZEN
REAL_S6_EXECUTION = FORBIDDEN
S7_EXECUTION = FORBIDDEN

LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 3016
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
NEXT_STEP = L3_W_S6_CAMPAIGN_INFRASTRUCTURE_IMPLEMENTATION
S6_EXECUTION = FORBIDDEN
```

Après livraison L3-W, ChatGPT audite le commit distant. Un préflight d'exécution S6 distinct sera ensuite nécessaire. Aucun PASS logiciel n'autorise automatiquement une campagne physique S6.

## Rôles de collaboration

```text
ChatGPT: scientific lead / conceptual design / scientific documentation / interpretation / audit
Claude: software implementation / repository operations / execution explicitement autorisée
Lionel: intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un PASS, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
