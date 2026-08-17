# Contrat de continuité — état courant

## État Git

```text
ACTIVE_BRANCH = research/level2-energy-regime
LEVEL3_Y_S6_NORMATIVE_CAMPAIGN_GOVERNANCE = 55ea89be3a744953ff677754ff2ca22dbf116428
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S6_CAMPAIGN_COMPLETE_PENDING_ARCHIVAL_FREEZE

LAST_COMPLETED_NORMATIVE_CAMPAIGN = L3-Y-S6-NORMATIVE-CAMPAIGN
LAST_FROZEN_REFERENCE_LOT = L3-S-FREEZE-S5-REFERENCE-ARTIFACTS

S5_TO_S6_DIRECTIONAL_CONTINUITY = OBSERVED_4_OF_6
S5_TO_S6_DELTA_STEP_REDUCTION = OBSERVED_2_OF_6
UNIFORM_LATE_STABILIZATION = NOT_SUPPORTED
DETAILED_PROFILE_STABILIZATION = NOT_OBSERVED_THROUGH_S6
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

## Références gelées

```text
S2_S3_REFERENCE = results/level2/level2-energy-regime-v1/
S4_REFERENCE = results/level3/level3-s4-truncation-extension-v1/
S5_REFERENCE = results/level3/level3-s5-truncation-extension-v1/
S2_S3_S4_S5_RECOMPUTATION = FORBIDDEN
```

## Campagne S=6 complète

```text
CAMPAIGN_ID = level3-s6-truncation-extension-v1
MANIFEST_FINGERPRINT = 2e0f06b69139abeb0b225a3d2b715242d6a0c26d2d1067b789f26b4829f847ca
REPOSITORY_COMMIT = 55ea89be3a744953ff677754ff2ca22dbf116428
TRIANGLE_S6_DIMENSION = 248
RING4_S6_DIMENSION = 852
RING5_S6_DIMENSION = 3016
CAMPAIGN_STATUS = COMPLETE
```

Résultat primaire S5→S6 :

```text
TRIANGLE_M_TT = S6_DIRECTION_REVERSES
TRIANGLE_R_EFF = S6_DIRECTION_REVERSES
RING4_M_TT = S6_DIRECTION_PERSISTS
RING4_R_EFF = S6_DIRECTION_PERSISTS
RING5_M_TT = S6_DIRECTION_PERSISTS
RING5_R_EFF = S6_DIRECTION_PERSISTS
```

## Lot courant — L3-Z

```text
LOT = L3-Z-FREEZE-S6-REFERENCE-ARTIFACTS
STATUS = OPEN
TYPE = ARCHIVAL_IMPLEMENTATION

CODE_CHANGE_AUTHORIZED = YES
COMMIT_AUTHORIZED = YES
PUSH_AUTHORIZED = YES

S6_RECOMPUTATION_AUTHORIZED = NO
S6_ARTIFACT_CONTENT_MUTATION_AUTHORIZED = NO
S7_PREREGISTRATION_AUTHORIZED = NO
S7_EXECUTION_AUTHORIZED = NO
```

Objectif : versionner octet pour octet les artefacts existants de la campagne S=6 complète et ajouter `SHA256SUMS`, sans aucune recomputation, régénération, reformatage ni modification scientifique.

Périmètre attendu :

```text
.gitignore
results/level3/level3-s6-truncation-extension-v1/manifest.json
results/level3/level3-s6-truncation-extension-v1/campaign-summary.json
results/level3/level3-s6-truncation-extension-v1/cases/triangle-S6.json
results/level3/level3-s6-truncation-extension-v1/cases/ring4-S6.json
results/level3/level3-s6-truncation-extension-v1/cases/ring5-S6.json
results/level3/level3-s6-truncation-extension-v1/SHA256SUMS
```

## Invariants

```text
LEVEL2_REFERENCE = FROZEN
S4_REFERENCE = FROZEN_AND_VERSIONED
S5_REFERENCE = FROZEN_AND_VERSIONED
S6_CAMPAIGN = COMPLETE
S6_RECOMPUTATION = FORBIDDEN
S6_ARTIFACT_REGENERATION = FORBIDDEN
S6_ARTIFACT_CONTENT_CHANGE = FORBIDDEN
S7_PREREGISTRATION = NOT_YET_FROZEN
S7_EXECUTION = FORBIDDEN
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

## Étape suivante

```text
NEXT_STEP = L3_Z_FREEZE_S6_REFERENCE_ARTIFACTS
S7_EXECUTION = FORBIDDEN
```

Après livraison L3-Z, ChatGPT audite le commit distant et les hashes avant toute décision sur S=7.
