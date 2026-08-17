# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. Le contrat scientifique actif Level 3 reste [`../levels/level3/s5-second-extension-preregistration.md`](../levels/level3/s5-second-extension-preregistration.md).

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
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S5_CAMPAIGN_COMPLETE_PENDING_ARCHIVAL_FREEZE

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-P-S5-CAMPAIGN-INFRASTRUCTURE
LAST_ACCEPTED_EXECUTION_PREFLIGHT = L3-Q-S5-CAMPAIGN-EXECUTION-PREFLIGHT
LAST_COMPLETED_NORMATIVE_CAMPAIGN = L3-R-S5-NORMATIVE-CAMPAIGN
LAST_FROZEN_REFERENCE_LOT = L3-L-FREEZE-S4-REFERENCE-ARTIFACTS
LAST_FROZEN_SCIENTIFIC_JALON = L3-M-S5-SCIENTIFIC-PREREGISTRATION
LAST_ACCEPTED_CAPABILITY_PREFLIGHT = L3-N-S5-CAPABILITY-PREFLIGHT

S4_TO_S5_DIRECTIONAL_CONTINUITY = OBSERVED_6_OF_6
S4_TO_S5_DELTA_STEP_REDUCTION = OBSERVED_6_OF_6
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Références scientifiques gelées

```text
S2_S3_REFERENCE = results/level2/level2-energy-regime-v1/
S2_S3_CAMPAIGN_ID = level2-energy-regime-v1
S2_S3_MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
S2_S3_REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0

S4_REFERENCE = results/level3/level3-s4-truncation-extension-v1/
S4_CAMPAIGN_ID = level3-s4-truncation-extension-v1
S4_MANIFEST_FINGERPRINT = 3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba
S4_REPOSITORY_COMMIT = ffb49da84111f778e45aa95b6d9e80b45d68f34c
S4_REFERENCE_VERSIONED = YES
S4_REFERENCE_SHA256_VERIFIED = YES

S2_S3_S4_RECOMPUTATION = FORBIDDEN
```

## Campagne normative S=5 — L3-R

```text
L3_R_S5_NORMATIVE_CAMPAIGN = COMPLETE
CAMPAIGN_ID = level3-s5-truncation-extension-v1
MANIFEST_FINGERPRINT = 3160a8e6e0f9ae4a21c027a865e4d56527303ad644e3f45137baa2120f0c5d04
REPOSITORY_COMMIT = 782f29eb9dcbc21ca2168e109997b0f59a12402f
CAMPAIGN_PLAN = triangle:S5,ring4:S5,ring5:S5

TRIANGLE_S5_DIMENSION = 208
RING4_S5_DIMENSION = 712
RING5_S5_DIMENSION = 2512

ALL_CASES_FULL_SPECTRUM = YES
ALL_CASES_DENSE = YES
ALL_CASES_WINDOW_TRUNCATED_FALSE = YES
ALL_CASES_PARTIAL_SUBSPACE_ZERO = YES
ALL_CASES_MULTIPLICITY_SUM_MATCH_DIMENSION = YES
CAMPAIGN_STATUS = COMPLETE
```

Résultat scientifique primaire accepté pour S4→S5 :

```text
TRIANGLE_M_TT = S5_DIRECTION_PERSISTS
TRIANGLE_R_EFF = S5_DIRECTION_PERSISTS
RING4_M_TT = S5_DIRECTION_PERSISTS
RING4_R_EFF = S5_DIRECTION_PERSISTS
RING5_M_TT = S5_DIRECTION_PERSISTS
RING5_R_EFF = S5_DIRECTION_PERSISTS

S4_TO_S5_DIRECTIONAL_CONTINUITY = OBSERVED_6_OF_6
S4_TO_S5_DELTA_STEP_REDUCTION = OBSERVED_6_OF_6
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Les artefacts S=5 existent localement sous :

```text
results/level3/level3-s5-truncation-extension-v1/
```

Ils ne sont pas encore versionnés. Ils doivent être gelés avant tout pré-enregistrement/exécution S=6.

## Lot courant — L3-S

```text
LOT = L3-S-FREEZE-S5-REFERENCE-ARTIFACTS
STATUS = OPEN
TYPE = ARCHIVAL_IMPLEMENTATION

CODE_CHANGE_AUTHORIZED = YES
COMMIT_AUTHORIZED = YES
PUSH_AUTHORIZED = YES

S5_RECOMPUTATION_AUTHORIZED = NO
S5_ARTIFACT_CONTENT_MUTATION_AUTHORIZED = NO
S6_PREREGISTRATION_AUTHORIZED = NO
S6_EXECUTION_AUTHORIZED = NO
```

Objectif : intégrer dans Git, octet pour octet, les artefacts existants de la campagne S=5 complète afin qu'ils deviennent la référence normative reproductible pour toute future extension S=6.

Périmètre attendu :

```text
.gitignore
results/level3/level3-s5-truncation-extension-v1/manifest.json
results/level3/level3-s5-truncation-extension-v1/campaign-summary.json
results/level3/level3-s5-truncation-extension-v1/cases/triangle-S5.json
results/level3/level3-s5-truncation-extension-v1/cases/ring4-S5.json
results/level3/level3-s5-truncation-extension-v1/cases/ring5-S5.json
results/level3/level3-s5-truncation-extension-v1/SHA256SUMS
```

`SHA256SUMS` peut être créé comme métadonnée archivistique après calcul des hashes des cinq artefacts existants. Aucun artefact scientifique ne doit être régénéré, reformatté ou réécrit.

## Invariants L3-S

```text
LEVEL2 = CLOSED
LEVEL2_ARTIFACTS = FROZEN_REFERENCE
LEVEL2_RECOMPUTATION = FORBIDDEN

S4_REFERENCE = FROZEN_AND_VERSIONED
S4_RECOMPUTATION = FORBIDDEN

L3_R_S5_NORMATIVE_CAMPAIGN = COMPLETE
S5_ARTIFACTS = FROZEN_PENDING_VERSIONING
S5_RECOMPUTATION = FORBIDDEN
S5_ARTIFACT_REGENERATION = FORBIDDEN
S5_ARTIFACT_CONTENT_CHANGE = FORBIDDEN

S6_PREREGISTRATION = NOT_YET_FROZEN
S6_EXECUTION = FORBIDDEN

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
NEXT_STEP = L3_S_FREEZE_S5_REFERENCE_ARTIFACTS
S6_EXECUTION = FORBIDDEN
```

Après livraison L3-S, ChatGPT audite le commit distant. Le pré-enregistrement S=6 sera un lot scientifique distinct et devra être gelé avant toute exécution physique S=6.

## Rôles de collaboration

```text
ChatGPT: scientific lead / conceptual design / scientific documentation / interpretation / audit
Claude: software implementation / repository operations / execution explicitement autorisée par mandat
Lionel: intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un PASS, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
