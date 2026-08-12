# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet de gouvernance jusqu'à la clôture de Level 1 est archivé par snapshot Git dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime
LEVEL2_L2B_DESIGN_CANDIDATE = bb16f57838cdddfb4eca94b8a78cce5a7ccebe1b
LEVEL2_L2C_PREREGISTRATION_CANDIDATE = 3169671bdfe1daaafdeb985aa175f35c49950576
LEVEL2_NUMERICAL_GUARD_PROTOCOL_CANDIDATE = f2a08b73e7109aa8ae8c8d3c30365b64f91f21d6
LEVEL2_NUMERICAL_GUARD_RESULT_CANDIDATE = bb52e968d4a5d465a3db0b194aadc53e9295a442
LEVEL2_FROZEN_PREREGISTRATION = 2d4c859db7939da51ee7d919889a18f4c7e229ed
LEVEL2_D1_IMPLEMENTATION = 27807985f18d1f97b0eb065b7fb436d6253ab3cd
LEVEL2_D1_CORRECTIVE_COMMIT = ef8495f9539fef7e4c614d96907ba1224809b0d4
LEVEL2_D2_ADAPTER_IMPLEMENTATION = 2fad3951290489ad0ddb4b8bb99f858651485f82
LEVEL2_D2_CORRECTIVE_COMMIT = 25f09735caed2a2ddfa1833e69165c81f7740183
LEVEL2_D3_ORCHESTRATION_IMPLEMENTATION = 118c323aa8b2193a14f6edf19f5ac3167ebadf72
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = L2_D3_ACCEPTED

LAST_CLOSED_LEVEL = LEVEL1
LAST_ACCEPTED_LOT = L2-D3-ANALYTIC-ORCHESTRATION

LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
PHASE_G_OPENED           = NO

LEVEL2_PRIMARY_AXIS = ENERGY_SPECTRAL_REGIME
LEVEL2_C_PREREGISTRATION = FROZEN
LEVEL2_D1_PRIMITIVES = ACCEPTED
LEVEL2_D2_ADAPTER = ACCEPTED
LEVEL2_D3_ORCHESTRATION = ACCEPTED
LEVEL2_IMPLEMENTATION = IN_PROGRESS
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

## Documents scientifiques actifs

- `docs/levels/level2/conceptual-framing.md`
- `docs/levels/level2/spectral-capability-audit.md`
- `docs/levels/level2/spectral-regime-design.md`
- `docs/levels/level2/profile-comparison-preregistration.md`
- `docs/levels/level2/numerical-guard-protocol.md`

## Résultat L2-A1 — préflight plein spectre

```text
triangle S=2 : 88/88 eigenpairs, 22 groupes complets
triangle S=3 : 128/128 eigenpairs, 32 groupes complets
ring4    S=2 : 292/292 eigenpairs, 106 groupes complets
ring4    S=3 : 432/432 eigenpairs, 158 groupes complets
ring5    S=2 : 1000/1000 eigenpairs, 226 groupes complets
ring5    S=3 : 1504/1504 eigenpairs, 342 groupes complets

ALL_6_CASES_FULL_SPECTRUM_AVAILABLE = YES
PARTIAL_SUBSPACES = 0
NEW_SPECTRAL_APPROXIMATION_REQUIRED = NO
```

Aucune observable physique Level 2 n'a été inspectée pendant ce préflight.

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
CALIBRATION_STATUS = PASS
UNITARITY_CHECK = PASS
PROJECTOR_INVARIANCE = PASS
RHO_NULL_SEMANTICS = PASS
M_TT_AVAILABILITY_INVARIANT = PASS
R_EFF_AVAILABILITY_INVARIANT = PASS

E_M_TT  = 4.163336342344337e-17
E_R_EFF = 4.440892098500626e-16

NUMERICAL_GUARD_M_TT  = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
```

Les gardes ont un rôle exclusivement numérique de résolution du signe autour de zéro. Elles ne sont pas des seuils physiques et ne peuvent pas être élargies post-hoc pendant la campagne.

## Résultat L2-D1 — primitives Level2

```text
LOT = L2-D1-METRICS-AND-PROFILE-PRIMITIVES
STATUS = ACCEPTED
IMPLEMENTATION_COMMIT = 27807985f18d1f97b0eb065b7fb436d6253ab3cd
CORRECTIVE_COMMIT = ef8495f9539fef7e4c614d96907ba1224809b0d4

PRIMARY_METRICS = IMPLEMENTED_AND_TESTED
CONTROL_METRICS = IMPLEMENTED_AND_TESTED
REGIME_AGGREGATION = IMPLEMENTED_AND_TESTED
CONTRASTS = IMPLEMENTED_AND_TESTED
INTER_S_PROFILE_DESCRIPTORS = IMPLEMENTED_AND_TESTED
INTER_S_TAXONOMY = IMPLEMENTED_AND_TESTED

L2_C1_GUARD_SCOPE = DELTA_HL_ONLY
NEW_NUMERICAL_TOLERANCE = NO
REAL_LEVEL2_DIAGONALIZATION = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
WEIGHTED_SPEARMAN_IMPLEMENTED = NO
```

## Résultat L2-D2 — adaptateur spectral Level2

```text
LOT = L2-D2-LEVEL2-ADAPTER
STATUS = ACCEPTED
IMPLEMENTATION_COMMIT = 2fad3951290489ad0ddb4b8bb99f858651485f82
CORRECTIVE_COMMIT = 25f09735caed2a2ddfa1833e69165c81f7740183

COMPLETE_MULTIPLET_EXTRACTION = IMPLEMENTED_AND_TESTED
PARTIAL_SUBSPACE_CASE_REJECTION = IMPLEMENTED_AND_TESTED
C_TT_CONN_ASSEMBLY = IMPLEMENTED_AND_TESTED
RHO_QQ_ASSEMBLY = IMPLEMENTED_AND_TESTED
PER_MULTIPLET_PROFILE_ADAPTER = IMPLEMENTED_AND_TESTED
SYNTHETIC_TESTS_ONLY = YES

PARTIAL_SUBSPACE_SILENT_EXCLUSION = NO
EXPLORATORY_PARTIAL_SUBSPACE_MEAN_USED = NO
REAL_LEVEL2_DIAGONALIZATION = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
NEW_SCIENTIFIC_METRIC = NO
NEW_NUMERICAL_TOLERANCE = NO
```

## Arbitrage L2-D3 — métriques de contrôle

L'audit L2-D3 a identifié une ambiguïté de périmètre concernant les descripteurs inter-S de forme pour les métriques de contrôle. Pour le premier test normatif, l'interprétation conservatrice suivante est gelée :

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

`A_QQ` et `M_QQ` restent donc des contrôles descriptifs. Aucun `C_X_23`, `D_X_23`, classement inter-S primaire ou garde numérique n'est introduit pour ces métriques dans ce premier test. Cette décision ne modifie pas les définitions pré-enregistrées ; elle borne leur usage normatif au périmètre explicitement prévu pour les métriques primaires.

## Résultat L2-D3 — orchestration analytique

```text
LOT = L2-D3-ANALYTIC-ORCHESTRATION
STATUS = ACCEPTED
IMPLEMENTATION_COMMIT = 118c323aa8b2193a14f6edf19f5ac3167ebadf72

CASE_METRIC_ANALYSIS = IMPLEMENTED_AND_TESTED
LOW_MID_HIGH = IMPLEMENTED_AND_TESTED
DELTA_HL_ML_HM = IMPLEMENTED_AND_TESTED
PRIMARY_INTER_S_SHAPE = IMPLEMENTED_AND_TESTED
PRIMARY_INTER_S_TAXONOMY = IMPLEMENTED_AND_TESTED
CONTROL_ANALYSIS_DESCRIPTIVE_ONLY = ENFORCED_STRUCTURALLY
INCOMPLETE_PROFILE_COVERAGE = EXPLICIT_NOT_AVAILABLE
SYNTHETIC_TESTS_ONLY = YES

L2_C1_GUARD_SCOPE = DELTA_HL_ONLY
REAL_LEVEL2_DATA_USED = NO
REAL_LEVEL2_DIAGONALIZATION = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
NEW_SCIENTIFIC_METRIC = NO
NEW_NUMERICAL_TOLERANCE = NO
```

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
NEXT_STEP = L2_D4_EXECUTION_AND_PROVENANCE_AUDIT
OPEN_METHODOLOGICAL_ITEM = NONE
```

L2-D1, L2-D2 et L2-D3 sont clos. La chaîne scientifique en mémoire est implémentée et testée sur données synthétiques. L'étape suivante doit auditer la couche minimale d'exécution et de provenance nécessaire pour relier les six cas Level2 gelés à cette chaîne et produire des résultats persistables, sans encore exécuter la campagne normative réelle.

Aucune exécution normative réelle n'est autorisée avant audit, implémentation, revue et acceptation explicite de cette dernière couche de campagne.

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
- Un défaut logiciel ne bloque que s'il peut altérer le résultat physique,
  sa provenance ou son interprétation.
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
