# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. Le contrat scientifique actif Level 3 est [`../levels/level3/s6-third-extension-preregistration.md`](../levels/level3/s6-third-extension-preregistration.md).

## État Git

```text
ACTIVE_BRANCH = research/level2-energy-regime

LEVEL3_S_FROZEN_S5_REFERENCE_ARTIFACTS = 7239efe1708535d09d779ee95eb024f9233d9242
LEVEL3_T_S6_SCIENTIFIC_PREREGISTRATION = 1c19a01e051c3df6f547afe0816a795989fdac3b
LEVEL3_U_S6_CAPABILITY_PREFLIGHT_GOVERNANCE = 2dd5765121964054de4a12395932600d69c17be6
LEVEL3_V_DENSE_CAPABILITY_3016 = 1bda37eac844cc9b603de25ccf595581428a061b
LEVEL3_W_S6_CAMPAIGN_INFRASTRUCTURE = d39c2547242619d424ae1f97b44636ecc737ffb3
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S6_EXECUTION_PREFLIGHT

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-W-S6-CAMPAIGN-INFRASTRUCTURE
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

```text
LEVEL3_THIRD_NEW_SPIN = 6
LEVEL3_NEW_CASES = triangle:S6, ring4:S6, ring5:S6
PRIMARY_PAIR = S5_TO_S6
FULL_SPECTRUM = REQUIRED
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
PRIMARY_CONTRAST = HIGH_MINUS_LOW
INTER_S_BRANCH_MATCHING = FORBIDDEN
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
FIVE_SPIN_DIRECTIONAL_DESCRIPTOR = REVERSAL_COUNT_23456
TWO_STEP_DIRECTIONAL_DESCRIPTOR = LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

## Capacité et infrastructure S=6 acceptées

```text
TRIANGLE_S6_DIMENSION = 248
RING4_S6_DIMENSION = 852
RING5_S6_DIMENSION = 3016
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 3016
S6_CAMPAIGN_ID = level3-s6-truncation-extension-v1
S6_MANIFEST_FINGERPRINT = 2e0f06b69139abeb0b225a3d2b715242d6a0c26d2d1067b789f26b4829f847ca
S6_MANIFEST_IMPLEMENTED = YES
S6_SCHEMAS_IMPLEMENTED = YES
S5_FROZEN_REFERENCE_LOADER_IMPLEMENTED = YES
S6_PLANNING_IMPLEMENTED = YES
S6_GATES_IMPLEMENTED = YES
S6_SERIALIZATION_IMPLEMENTED = YES
S6_RUNNER_IMPLEMENTED = YES
S6_NO_IMPLICIT_RESUME = YES
S6_SUMMARY_WRITTEN_LAST = YES
```

## Lot courant — L3-X

```text
LOT = L3-X-S6-CAMPAIGN-EXECUTION-PREFLIGHT
STATUS = OPEN
TYPE = READ_ONLY_EXECUTION_PREFLIGHT

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO

REAL_S6_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S6_DIAGONALIZATION_AUTHORIZED = NO
S6_OBSERVABLES_AUTHORIZED = NO
LEVEL3_S6_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
S7_EXECUTION_AUTHORIZED = NO
```

Objectif : réaliser le dernier préflight d'exécution de la campagne S=6 avant toute donnée physique S=6. Le lot doit vérifier le manifeste/fingerprint S6, les références gelées Level2/S4/S5, le plan exact des trois cas, la capacité dense 3016, l'environnement numérique, l'absence de répertoire normatif S6 préexistant et un dry-run complet du vrai runner avec `run_case` strictement monkeypatché.

Le dry-run doit démontrer :

```text
- exactement 3 cas simulés : triangle:S6, ring4:S6, ring5:S6 ;
- aucune comparaison S5→S6 avant 3/3 cas persistés ;
- exactement 3 comparaisons après complétude 3/3 ;
- campaign-summary.json écrit en dernier ;
- NO_IMPLICIT_RESUME ;
- en cas d'échec synthétique du deuxième cas : aucun summary, aucune comparaison, troisième cas non exécuté ;
- aucune primitive physique S6 réelle atteinte.
```

## Invariants L3-X

```text
LEVEL2 = CLOSED
LEVEL2_REFERENCE = FROZEN
LEVEL2_RECOMPUTATION = FORBIDDEN
S4_REFERENCE = FROZEN_AND_VERSIONED
S4_RECOMPUTATION = FORBIDDEN
S5_REFERENCE = FROZEN_AND_VERSIONED
S5_RECOMPUTATION = FORBIDDEN
S6_PREREGISTRATION = FROZEN
S6_CAMPAIGN_INFRASTRUCTURE = ACCEPTED
S6_EXECUTION = FORBIDDEN
S7_EXECUTION = FORBIDDEN
S6_MANIFEST_FINGERPRINT = 2e0f06b69139abeb0b225a3d2b715242d6a0c26d2d1067b789f26b4829f847ca
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
```

## Étape suivante

```text
NEXT_STEP = L3_X_S6_CAMPAIGN_EXECUTION_PREFLIGHT
S6_EXECUTION = FORBIDDEN
```

Après livraison L3-X, ChatGPT audite le rapport. Seul un PASS suivi d'une autorisation explicite de Lionel pourra ouvrir la campagne normative physique S=6.

## Rôles de collaboration

```text
ChatGPT: scientific lead / conceptual design / scientific documentation / interpretation / audit
Claude: software implementation / repository operations / execution explicitement autorisée
Lionel: intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un PASS, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
