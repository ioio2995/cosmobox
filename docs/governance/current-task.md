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
LEVEL2_E_CAMPAIGN_INFRASTRUCTURE = 41bf85e3ee22e7ba28fde294c072157fd8eef21e
LEVEL2_E1_RAW_OBSERVABLE_RETENTION = 59dc708e481cd0b7bfb8117d3f69c6cefb1e2924
LEVEL2_E1_IMMUTABILITY_CORRECTIVE = 7258dda1571e85f7cdfe42d86fa21dc6315e2be6
LEVEL2_E2_END_TO_END_RUNNER = d2374128fa0562efbb257845d6d4d134ba132af9
LEVEL2_E2_PROVENANCE_CORRECTIVE = d058b81eb583200956e282fb934a974dbf18e27f
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = NORMATIVE_CAMPAIGN_AUTHORIZED

LAST_CLOSED_LEVEL = LEVEL1
LAST_ACCEPTED_LOT = L2-FINAL-REAL-PREFLIGHT

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
LEVEL2_E_CAMPAIGN_AND_PROVENANCE_AUDIT = ACCEPTED
LEVEL2_E_CAMPAIGN_INFRASTRUCTURE = ACCEPTED
LEVEL2_E1_RAW_OBSERVABLE_RETENTION = ACCEPTED
LEVEL2_E2_CASE_RESULT_AND_END_TO_END_RUNNER = ACCEPTED
LEVEL2_FINAL_REAL_PREFLIGHT = ACCEPTED
LEVEL2_IMPLEMENTATION = CAMPAIGN_LAYER_COMPLETE
LEVEL2_NORMATIVE_CAMPAIGN = AUTHORIZED_NOT_STARTED
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

## Résultats D1 → D4

```text
L2-D1 = ACCEPTED
L2-D2 = ACCEPTED
L2-D3 = ACCEPTED
L2-D4-EXECUTION = ACCEPTED
L2-D4-REAL-PREFLIGHT = ACCEPTED
```

Le préflight réel reproduit exactement les invariants L2-A1 :

```text
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

## Décision L2-E — campagne et provenance

```text
SEEDS_REQUIRED = NO
MANIFEST_FINGERPRINT = SHA256_CANONICAL_JSON
REPOSITORY_IDENTITY = ioio2995/cosmobox
REPOSITORY_COMMIT_CAPTURE = ONCE_AT_CAMPAIGN_START_AFTER_CLEAN_WORKTREE_CHECK
ALL_6_CASES_REQUIRED = YES
ALL_3_GEOMETRY_COMPARISONS_REQUIRED = YES
MIXED_COMMIT = FORBIDDEN
MIXED_MANIFEST_FINGERPRINT = FORBIDDEN
PARTIAL_CAMPAIGN_COMPLETE_STATUS = FORBIDDEN
NO_IMPLICIT_RESUME = YES
ARTIFACT_OVERWRITE = FORBIDDEN
```

Trois schémas Level2 sont gelés :

```text
schemas/level2/campaign-manifest-v1.schema.json
schemas/level2/case-result-v1.schema.json
schemas/level2/campaign-summary-v1.schema.json
```

Les artefacts de run doivent vivre sous `results/level2/<campaign-id>/`, jamais sous `experiments/level2/`.

### Persistance des observables sources

```text
C_TT_CONN_PERSISTENCE = REQUIRED
C_TT_CONN_FORMAT = FULL_NxN_MATRIX_WITH_DIAGONAL

RHO_QQ_PERSISTENCE = REQUIRED
RHO_QQ_FORMAT = ALL_ORDERED_I_NE_J_PAIRS
RHO_QQ_VALUE_PRESERVATION = EXACT
RHO_QQ_NULL_REASON_PRESERVATION = EXACT
RHO_QQ_IMPUTATION = FORBIDDEN
```

## Résultat L2-E — couche de campagne complète

```text
LOT = L2-E-CAMPAIGN-LAYER
STATUS = ACCEPTED

INFRASTRUCTURE_COMMIT = 41bf85e3ee22e7ba28fde294c072157fd8eef21e
RAW_OBSERVABLE_RETENTION_COMMIT = 59dc708e481cd0b7bfb8117d3f69c6cefb1e2924
RAW_OBSERVABLE_IMMUTABILITY_CORRECTIVE = 7258dda1571e85f7cdfe42d86fa21dc6315e2be6
END_TO_END_RUNNER_COMMIT = d2374128fa0562efbb257845d6d4d134ba132af9
PROVENANCE_NO_OVERWRITE_CORRECTIVE = d058b81eb583200956e282fb934a974dbf18e27f

MANIFEST = PASS
FINGERPRINT = PASS
PROVENANCE = PASS
REPOSITORY_IDENTITY = PASS
SCHEMAS = PASS
CASE_RESULT_SERIALIZATION = PASS
CAMPAIGN_SUMMARY_SERIALIZATION = PASS
C_TT_CONN_RETENTION_AND_PERSISTENCE = PASS
RHO_QQ_RETENTION_AND_PERSISTENCE = PASS
CASE_ARTIFACT_ATOMIC_WRITE = PASS
CASE_ARTIFACT_RELOAD_VALIDATION = PASS
END_TO_END_RUNNER = PASS
CAMPAIGN_COMPLETENESS_GATE = PASS
CAMPAIGN_FINALIZATION = PASS
MANIFEST_NO_OVERWRITE = PASS
CASE_NO_OVERWRITE = PASS
SUMMARY_NO_OVERWRITE = PASS

REAL_LEVEL2_DIAGONALIZATION_DURING_IMPLEMENTATION = NO
REAL_LEVEL2_OBSERVABLE_COMPUTATION_DURING_IMPLEMENTATION = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
NEW_SCIENTIFIC_METRIC = NO
NEW_NUMERICAL_TOLERANCE = NO
```

## Résultat du préflight réel final

Le préflight final a été rejoué sur le HEAD de gouvernance `ed28c4163b751bbd91ffed2fef3770d6af800c95`, avec worktree propre, sans modification du dépôt et sans calcul d'observable Level2.

```text
triangle S=2 : D=88,   eigenpairs=88,   groupes=22,  PASS
triangle S=3 : D=128,  eigenpairs=128,  groupes=32,  PASS
ring4    S=2 : D=292,  eigenpairs=292,  groupes=106, PASS
ring4    S=3 : D=432,  eigenpairs=432,  groupes=158, PASS
ring5    S=2 : D=1000, eigenpairs=1000, groupes=226, PASS
ring5    S=3 : D=1504, eigenpairs=1504, groupes=342, PASS

ALL_6_CASES_PASS = YES
L2_FINAL_REAL_PREFLIGHT = PASS
REAL_LEVEL2_DIAGONALIZATION = YES
REAL_LEVEL2_OBSERVABLE_COMPUTATION = NO
PHYSICAL_RESULT_INSPECTED = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
```

Ce résultat est accepté comme dernière barrière technique avant la première campagne normative Level2.

### Validation normative

La finalisation de campagne porte uniquement sur le protocole et la structure :

```text
6/6 cases present
3/3 geometry comparisons present
same repository
same repository_commit
same manifest_fingerprint
same campaign_id
full spectrum for all cases
partial_subspaces = 0
schema-valid artifacts
L2-A1 dimension/group_count references matched
q coverage valid
primary/control separation intact
```

Aucune gate ne peut dépendre de la valeur physique obtenue :

```text
NO_EFFECT_THRESHOLD
NO_EXPECTED_DELTA_DIRECTION
NO_MINIMUM_C_X_23
NO_RESULT_BASED_RETRY
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

## Autorisation de la première campagne normative Level2

La première campagne normative Level2 est explicitement autorisée à partir du présent HEAD de gouvernance.

Elle doit utiliser exclusivement :

```text
experiments/level2/preregistered-manifest-v1.json
scripts/level2_campaign/runner.run_campaign
```

Aucun paramètre, seuil, métrique, garde, cas, branche inter-S ou règle de classification ne peut être modifié avant ou pendant l'exécution.

La campagne doit produire les artefacts normatifs sous :

```text
results/level2/level2-energy-regime-v1/
```

Le résultat physique doit être rapporté tel quel. Toute défaillance technique arrête la campagne ; aucune correction post-hoc ou reprise implicite n'est autorisée.

## Étape suivante

```text
NEXT_STEP = L2_FIRST_NORMATIVE_CAMPAIGN
OPEN_METHODOLOGICAL_ITEM = NONE
NORMATIVE_CAMPAIGN_AUTHORIZED = YES
```

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
- Aucun résultat physique Level2 ne doit être filtré, corrigé ou réinterprété pour obtenir une conclusion préférée.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence de la clôture Level 1 est :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
