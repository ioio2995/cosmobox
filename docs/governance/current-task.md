# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md). Le contrat scientifique actif Level 3 reste [`../levels/level3/s4-first-campaign-preregistration.md`](../levels/level3/s4-first-campaign-preregistration.md) jusqu'au gel d'un pré-enregistrement S=5 distinct.

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
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S4_CAMPAIGN_COMPLETE

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-I-S4-CAMPAIGN-INFRASTRUCTURE
LAST_ACCEPTED_EXECUTION_PREFLIGHT = L3-J-S4-CAMPAIGN-EXECUTION-PREFLIGHT
LAST_COMPLETED_NORMATIVE_CAMPAIGN = L3-K-S4-NORMATIVE-CAMPAIGN
LAST_FROZEN_SCIENTIFIC_JALON = L3-F-S4-SCIENTIFIC-PREREGISTRATION

LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Référence scientifique Level 2

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
CAMPAIGN_STATUS = COMPLETE
LEVEL2_ARTIFACTS_VERSIONED = YES
LEVEL2_REFERENCE_SHA256_VERIFIED = YES
LEVEL2_RECOMPUTATION = FORBIDDEN
```

Les artefacts gelés Level2 sont sous :

```text
results/level2/level2-energy-regime-v1/
```

Ils constituent la seule référence normative S=2/S=3.

## Campagne normative S=4 — L3-K

```text
L3_K_S4_NORMATIVE_CAMPAIGN = COMPLETE
CAMPAIGN_ID = level3-s4-truncation-extension-v1
MANIFEST_FINGERPRINT = 3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba
REPOSITORY_COMMIT = ffb49da84111f778e45aa95b6d9e80b45d68f34c
CAMPAIGN_PLAN = triangle:S4,ring4:S4,ring5:S4

TRIANGLE_S4_DIMENSION = 168
RING4_S4_DIMENSION = 572
RING5_S4_DIMENSION = 2008

ALL_CASES_FULL_SPECTRUM = YES
ALL_CASES_DENSE = YES
ALL_CASES_WINDOW_TRUNCATED_FALSE = YES
ALL_CASES_PARTIAL_SUBSPACE_ZERO = YES
ALL_CASES_MULTIPLICITY_SUM_MATCH_DIMENSION = YES
CAMPAIGN_STATUS = COMPLETE
```

Résultat scientifique primaire accepté pour S3→S4 :

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

Les artefacts S=4 existent localement sous :

```text
results/level3/level3-s4-truncation-extension-v1/
```

Ils ne sont pas encore versionnés. Ils doivent être gelés avant tout pré-enregistrement/exécution S=5.

## Lot courant — L3-L

```text
LOT = L3-L-FREEZE-S4-REFERENCE-ARTIFACTS
STATUS = OPEN
TYPE = ARCHIVAL_IMPLEMENTATION

CODE_CHANGE_AUTHORIZED = YES
COMMIT_AUTHORIZED = YES
PUSH_AUTHORIZED = YES

S4_RECOMPUTATION_AUTHORIZED = NO
S4_ARTIFACT_CONTENT_MUTATION_AUTHORIZED = NO
S5_PREREGISTRATION_AUTHORIZED = NO
S5_EXECUTION_AUTHORIZED = NO
```

Objectif : intégrer dans Git, octet pour octet, les artefacts existants de la campagne S=4 complète afin qu'ils deviennent la référence normative reproductible pour la future extension S=5.

Périmètre attendu :

```text
.gitignore
results/level3/level3-s4-truncation-extension-v1/manifest.json
results/level3/level3-s4-truncation-extension-v1/campaign-summary.json
results/level3/level3-s4-truncation-extension-v1/cases/triangle-S4.json
results/level3/level3-s4-truncation-extension-v1/cases/ring4-S4.json
results/level3/level3-s4-truncation-extension-v1/cases/ring5-S4.json
results/level3/level3-s4-truncation-extension-v1/SHA256SUMS
```

`SHA256SUMS` peut être créé comme métadonnée archivistique après calcul des hashes des cinq artefacts existants. Aucun artefact scientifique ne doit être régénéré, reformatté ou réécrit.

## Invariants L3-L

```text
LEVEL2 = CLOSED
LEVEL2_ARTIFACTS = FROZEN_REFERENCE
LEVEL2_RECOMPUTATION = FORBIDDEN

L3_K_S4_NORMATIVE_CAMPAIGN = COMPLETE
S4_ARTIFACTS = FROZEN_PENDING_VERSIONING
S4_RECOMPUTATION = FORBIDDEN
S4_ARTIFACT_REGENERATION = FORBIDDEN
S4_ARTIFACT_CONTENT_CHANGE = FORBIDDEN

S5_PREREGISTRATION = NOT_YET_FROZEN
S5_EXECUTION = FORBIDDEN

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
NEXT_STEP = L3_L_FREEZE_S4_REFERENCE_ARTIFACTS
S5_EXECUTION = FORBIDDEN
```

Après livraison L3-L, ChatGPT audite le commit distant. Lionel accepte ou non le lot. Le pré-enregistrement S=5 sera un lot scientifique distinct et devra être gelé avant toute exécution physique S=5.

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
