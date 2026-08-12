# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet de gouvernance jusqu'à la clôture de Level 1 est archivé par snapshot Git dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime
LEVEL2_FROZEN_PREREGISTRATION = 2d4c859db7939da51ee7d919889a18f4c7e229ed
LEVEL2_D1_IMPLEMENTATION = 27807985f18d1f97b0eb065b7fb436d6253ab3cd
LEVEL2_D1_CORRECTIVE_COMMIT = ef8495f9539fef7e4c614d96907ba1224809b0d4
LEVEL2_D2_ADAPTER_IMPLEMENTATION = 2fad3951290489ad0ddb4b8bb99f858651485f82
LEVEL2_D2_CORRECTIVE_COMMIT = 25f09735caed2a2ddfa1833e69165c81f7740183
LEVEL2_D3_ORCHESTRATION_IMPLEMENTATION = 118c323aa8b2193a14f6edf19f5ac3167ebadf72
LEVEL2_D4_EXECUTION_IMPLEMENTATION = 9f14a8a9367cad80f013d68ff79af2f3dd039fcf
LEVEL2_D4_CORRECTIVE_COMMIT = 50df74b284cebcdc4e910e64965c3ceeab51cab5
LEVEL2_D4_REAL_PREFLIGHT = 1d55f490b1bf8cf4738964e773516292b39e7767
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = L2_D4_REAL_PREFLIGHT_ACCEPTED

LAST_CLOSED_LEVEL = LEVEL1
LAST_ACCEPTED_LOT = L2-D4-REAL-PREFLIGHT

LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
PHASE_G_OPENED           = NO

LEVEL2_PRIMARY_AXIS = ENERGY_SPECTRAL_REGIME
LEVEL2_C_PREREGISTRATION = FROZEN
LEVEL2_D1_PRIMITIVES = ACCEPTED
LEVEL2_D2_ADAPTER = ACCEPTED
LEVEL2_D3_ORCHESTRATION = ACCEPTED
LEVEL2_D4_EXECUTION = ACCEPTED
LEVEL2_D4_REAL_PREFLIGHT = ACCEPTED
LEVEL2_IMPLEMENTATION = IN_MEMORY_CHAIN_COMPLETE
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

## Documents scientifiques actifs

- `docs/levels/level2/conceptual-framing.md`
- `docs/levels/level2/spectral-capability-audit.md`
- `docs/levels/level2/spectral-regime-design.md`
- `docs/levels/level2/profile-comparison-preregistration.md`
- `docs/levels/level2/numerical-guard-protocol.md`

## Contrat scientifique Level 2 gelé

```text
UNIT = complete spectral multiplet over the full spectrum
COORDINATES = epsilon, q
PRIMARY = C_TT_conn
CONTROL = rho_QQ
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
REGIMES = LOW/MID/HIGH equal thirds of cumulative state population
PRIMARY_CONTRAST = HIGH_MINUS_LOW
INTER_S_BRANCH_MATCHING = FORBIDDEN
INTER_S_SHAPE_DESCRIPTORS = C_X_23, D_X_23
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
```

## Résultat L2-C1 — calibration numérique

```text
NUMERICAL_GUARD_M_TT  = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
L2_C1_GUARD_SCOPE = DELTA_HL_ONLY
```

Les gardes ont un rôle exclusivement numérique de résolution du signe autour de zéro. Elles ne sont pas des seuils physiques et ne peuvent pas être élargies post-hoc pendant la campagne.

## Résultat L2-D1 — primitives Level2

```text
STATUS = ACCEPTED
PRIMARY_METRICS = IMPLEMENTED_AND_TESTED
CONTROL_METRICS = IMPLEMENTED_AND_TESTED
REGIME_AGGREGATION = IMPLEMENTED_AND_TESTED
CONTRASTS = IMPLEMENTED_AND_TESTED
INTER_S_PROFILE_DESCRIPTORS = IMPLEMENTED_AND_TESTED
INTER_S_TAXONOMY = IMPLEMENTED_AND_TESTED
```

## Résultat L2-D2 — adaptateur spectral Level2

```text
STATUS = ACCEPTED
COMPLETE_MULTIPLET_EXTRACTION = IMPLEMENTED_AND_TESTED
PARTIAL_SUBSPACE_CASE_REJECTION = IMPLEMENTED_AND_TESTED
C_TT_CONN_ASSEMBLY = IMPLEMENTED_AND_TESTED
RHO_QQ_ASSEMBLY = IMPLEMENTED_AND_TESTED
PER_MULTIPLET_PROFILE_ADAPTER = IMPLEMENTED_AND_TESTED
PARTIAL_SUBSPACE_SILENT_EXCLUSION = NO
EXPLORATORY_PARTIAL_SUBSPACE_MEAN_USED = NO
```

## Arbitrage L2-D3 — métriques de contrôle

```text
PRIMARY_INTER_S_SHAPE_DESCRIPTORS:
  M_TT  -> C_X_23, D_X_23
  R_eff -> C_X_23, D_X_23 si le profil est évaluable partout

CONTROL_INTER_S_SHAPE_DESCRIPTORS:
  A_QQ -> NOT_COMPUTED
  M_QQ -> NOT_COMPUTED

CONTROL_ANALYSIS:
  LOW/MID/HIGH = COMPUTED
  DELTA_HL/DELTA_ML/DELTA_HM = COMPUTED_DESCRIPTIVELY
  PRIMARY_TAXONOMY = NOT_APPLICABLE
  L2_C1_GUARDS = NOT_APPLICABLE
```

## Résultat L2-D3 — orchestration analytique

```text
STATUS = ACCEPTED
CASE_METRIC_ANALYSIS = IMPLEMENTED_AND_TESTED
LOW_MID_HIGH = IMPLEMENTED_AND_TESTED
DELTA_HL_ML_HM = IMPLEMENTED_AND_TESTED
PRIMARY_INTER_S_SHAPE = IMPLEMENTED_AND_TESTED
PRIMARY_INTER_S_TAXONOMY = IMPLEMENTED_AND_TESTED
CONTROL_ANALYSIS_DESCRIPTIVE_ONLY = ENFORCED_STRUCTURALLY
INCOMPLETE_PROFILE_COVERAGE = EXPLICIT_NOT_AVAILABLE
```

## Résultat L2-D4 — exécution en mémoire

```text
STATUS = ACCEPTED
CASE_SPEC_PHYSICAL_LOCK = PASS
FULL_SPECTRUM_ENFORCEMENT = PASS
EXECUTION_PIPELINE = IMPLEMENTED_AND_TESTED
INTER_S_STRUCTURE = IMPLEMENTED_AND_TESTED
PHYSICAL_DEGREES_OF_FREEDOM_EXPOSED = NO
MANIFEST_CREATED = NO
SCHEMA_CREATED = NO
RUNNER_CREATED = NO
RESULT_SERIALIZATION = NO
```

## Résultat L2-D4 — préflight réel

```text
LOT = L2-D4-REAL-PREFLIGHT
STATUS = ACCEPTED
COMMIT = 1d55f490b1bf8cf4738964e773516292b39e7767

triangle S=2 : D=88,   eigenpairs=88,   groupes=22
triangle S=3 : D=128,  eigenpairs=128,  groupes=32
ring4    S=2 : D=292,  eigenpairs=292,  groupes=106
ring4    S=3 : D=432,  eigenpairs=432,  groupes=158
ring5    S=2 : D=1000, eigenpairs=1000, groupes=226
ring5    S=3 : D=1504, eigenpairs=1504, groupes=342

ALL_6_CASES_PASS = YES
SOLVER_METHOD = dense
WINDOW_TRUNCATED = false
PARTIAL_SUBSPACES = 0
MULTIPLICITY_COVERAGE = COMPLETE

REAL_LEVEL2_DIAGONALIZATION = YES
REAL_LEVEL2_OBSERVABLE_COMPUTATION = NO
PHYSICAL_RESULT_INSPECTED = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
```

Le préflight réel reproduit exactement les invariants L2-A1 et n'a inspecté aucune observable Level2.

## Taxonomie de conclusion primaire

Pour chaque géométrie et chaque métrique primaire :

```text
NO_RESOLVED_SPECTRAL_CONTRAST
OPPOSITE_INTER_S_DIRECTION
SAME_INTER_S_DIRECTION
NOT_EVALUABLE
```

`SAME_INTER_S_DIRECTION` ne constitue pas une preuve de convergence `S -> infinity`.

## Étape suivante

```text
NEXT_STEP = L2_E_CAMPAIGN_AND_PROVENANCE_AUDIT
OPEN_METHODOLOGICAL_ITEM = NONE
```

La chaîne scientifique D1→D4 et le préflight spectral réel sont acceptés. Avant toute première exécution normative des observables Level2, la couche de campagne doit être auditée puis figée : manifeste et fingerprint, schémas versionnés, provenance Git/pré-enregistrement/gardes numériques, runner, règles de persistance et atomicité de campagne.

Aucune observable Level2 réelle n'est autorisée tant que cette couche n'est pas implémentée, revue et acceptée explicitement.

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation / audit

Claude:
software implementation / repository operations / execution

Lionel:
intuition / direction / final decision
```

## Règles de progression

```text
- L'unité de progrès est l'expérience scientifique, pas le lot logiciel.
- Aucun résultat de Level 1C ne doit être réparé post-hoc : Level 1 est clos.
- Un défaut logiciel ne bloque que s'il peut altérer le résultat physique, sa provenance ou son interprétation.
- Aucun seuil binaire de réponse physique ne doit être réintroduit.
- Aucune nouvelle métrique ne sera ajoutée après ouverture de la campagne pour améliorer le résultat.
- Aucun matching multiplet-par-multiplet S=2 vers S=3 n'est autorisé dans Level 2.
- Aucun élargissement post-hoc des gardes numériques n'est autorisé.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence de la clôture Level 1 est :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
