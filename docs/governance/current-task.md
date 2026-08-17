# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md). Le contrat scientifique actif Level 3 est [`../levels/level3/s4-first-campaign-preregistration.md`](../levels/level3/s4-first-campaign-preregistration.md).

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
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S4_NORMATIVE_CAMPAIGN_AUTHORIZED

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-I-S4-CAMPAIGN-INFRASTRUCTURE
LAST_ACCEPTED_EXECUTION_PREFLIGHT = L3-J-S4-CAMPAIGN-EXECUTION-PREFLIGHT
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

Les artefacts gelés sont versionnés sous :

```text
results/level2/level2-energy-regime-v1/
```

Ils constituent la seule référence normative S=2/S=3 pour Level3.

## Contrat scientifique Level 3 gelé

Source normative :

```text
docs/levels/level3/s4-first-campaign-preregistration.md
```

Contrat principal :

```text
LEVEL3_FIRST_NEW_SPIN = 4
LEVEL3_NEW_CASES = triangle:S4, ring4:S4, ring5:S4
FULL_SPECTRUM = REQUIRED
PRIMARY_PAIR = S3_TO_S4
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
PRIMARY_CONTRAST = HIGH_MINUS_LOW
INTER_S_BRANCH_MATCHING = FORBIDDEN
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Taxonomie primaire :

```text
S4_DIRECTION_PERSISTS
S4_DIRECTION_REVERSES
S4_CONTRAST_UNRESOLVED
NOT_EVALUABLE
```

La séquence S=2,3,4 et les descripteurs continus `T_X_23`, `T_X_34`, `R_DELTA_X`, `C_X_23`, `D_X_23`, `C_X_34`, `D_X_34`, `R_D_X` sont pré-enregistrés sans seuil de convergence.

## Infrastructure et préflight acceptés

```text
LEVEL3_FULL_SPECTRUM_POLICY = IMPLEMENTED
LEVEL3_SPARSE_FALLBACK_POSSIBLE = NO
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008

TRIANGLE_S4_DIMENSION = 168
RING4_S4_DIMENSION = 572
RING5_S4_DIMENSION = 2008

LEVEL3_MANIFEST_IMPLEMENTED = YES
LEVEL3_SCHEMAS_IMPLEMENTED = YES
LEVEL3_FROZEN_REFERENCE_LOADER_IMPLEMENTED = YES
LEVEL3_SERIALIZATION_IMPLEMENTED = YES
LEVEL3_PLANNING_IMPLEMENTED = YES
LEVEL3_GATES_IMPLEMENTED = YES
LEVEL3_ATOMIC_OUTPUTS_IMPLEMENTED = YES
LEVEL3_RUNNER_IMPLEMENTED = YES
LEVEL3_NO_IMPLICIT_RESUME = YES
LEVEL3_CAMPAIGN_COMPLETE_REQUIRES_SUMMARY = YES

L3_J_S4_CAMPAIGN_EXECUTION_PREFLIGHT = PASS
LEVEL3_MANIFEST_FINGERPRINT = 3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba
LEVEL2_FROZEN_REFERENCE_VERIFICATION = PASS
LEVEL3_CAMPAIGN_PLAN = triangle:S4,ring4:S4,ring5:S4
LEVEL3_DENSE_CAPABILITY_COVERS_ALL_S4_CASES = YES
LEVEL3_RESOURCE_PREFLIGHT = PASS
LEVEL3_DRY_RUN = PASS
REAL_RUN_CASE_REACHED = NO
```

Aucune donnée physique S=4 n'a encore été inspectée avant l'ouverture du lot courant.

## Lot courant — L3-K

```text
LOT = L3-K-S4-NORMATIVE-CAMPAIGN
STATUS = OPEN
TYPE = NORMATIVE_PHYSICAL_EXECUTION

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO

REAL_S4_HAMILTONIAN_BUILD_AUTHORIZED = YES
REAL_S4_DIAGONALIZATION_AUTHORIZED = YES
S4_OBSERVABLES_AUTHORIZED = YES
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = YES

AUTHORIZED_CASES = triangle:S4, ring4:S4, ring5:S4
S5_EXECUTION_AUTHORIZED = NO
```

Objectif : exécuter exactement une fois la campagne normative Level3 pré-enregistrée via `scripts.level3_campaign.runner.run_campaign`, avec le manifeste gelé et le fingerprint validé. Les trois cas doivent être exécutés sans inspection/interprétation intermédiaire. Le runner produit les case-results puis `campaign-summary.json` en dernier.

Le répertoire de sortie normatif attendu est :

```text
results/level3/level3-s4-truncation-extension-v1/
```

Ce répertoire reste un résultat généré et n'est pas autorisé à être ajouté à Git pendant L3-K. L'intégration/archivage éventuel des résultats sera décidée après revue scientifique.

## Invariants L3-K

```text
LEVEL2 = CLOSED
LEVEL2_ARTIFACTS = FROZEN_REFERENCE
LEVEL2_RECOMPUTATION = FORBIDDEN
LEVEL3_S4_PREREGISTRATION = FROZEN
LEVEL3_MANIFEST_FINGERPRINT = 3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba
FULL_SPECTRUM = REQUIRED
SPARSE_FALLBACK = FORBIDDEN
AUTHORIZED_SPIN = 4
AUTHORIZED_GEOMETRIES = triangle, ring4, ring5
S5_EXECUTION = FORBIDDEN
INTER_S_BRANCH_MATCHING = FORBIDDEN
NEW_OBSERVABLE = NO
NEW_PRIMARY_METRIC = NO
NEW_SCIENTIFIC_THRESHOLD = NO
COMPOSITE_SCORE = FORBIDDEN
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
NO_POST_HOC_PROTOCOL_CHANGE = YES
```

Aucune modification de code, manifeste, schéma, seuil, convention ou pré-enregistrement n'est autorisée pendant l'exécution. En cas d'échec technique, la campagne s'arrête ; aucun correctif ni relance implicite n'est autorisé dans ce lot.

## Étape suivante

```text
NEXT_STEP = L3_K_S4_NORMATIVE_CAMPAIGN
S4_NORMATIVE_EXECUTION = AUTHORIZED
S5_EXECUTION = FORBIDDEN
```

Après le rapport L3-K, ChatGPT audite les artefacts produits et réalise l'interprétation scientifique conformément au pré-enregistrement. Aucun lot suivant n'est ouvert automatiquement.

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation / interpretation / audit

Claude:
software execution / repository operations explicitly authorized by mandate

Lionel:
intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un `PASS`, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
