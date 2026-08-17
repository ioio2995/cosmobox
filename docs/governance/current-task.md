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
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S4_EXECUTION_PREFLIGHT

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-I-S4-CAMPAIGN-INFRASTRUCTURE
LAST_FROZEN_SCIENTIFIC_JALON = L3-F-S4-SCIENTIFIC-PREREGISTRATION
LAST_ACCEPTED_AUDIT = L3-G-S4-CAMPAIGN-INFRASTRUCTURE-AUDIT

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
LEVEL2_ARTIFACT_BYTES_CHANGED = NO
LEVEL2_RECOMPUTATION_PERFORMED = NO
LEVEL2_REFERENCE_SHA256_VERIFIED = YES
```

Les artefacts gelés sont versionnés sous :

```text
results/level2/level2-energy-regime-v1/
```

avec `SHA256SUMS`. Ils constituent la référence normative reproductible S=2/S=3 pour Level3. Level2 reste immuable et clos.

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

## Capacités et infrastructure Level 3 établies

```text
LEVEL0_SPIN_ENCODING_GENERIC = YES
LEVEL3_CASESPEC_GENERIC = YES
LEVEL3_RUN_CASE_IMPLEMENTED = YES
LEVEL3_SPIN_PAIR_COMPARISON = YES
LEVEL3_FULL_SPECTRUM_POLICY = IMPLEMENTED
LEVEL3_SPARSE_FALLBACK_POSSIBLE = NO

TRIANGLE_S4_DIMENSION = 168
RING4_S4_DIMENSION = 572
RING5_S4_DIMENSION = 2008
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008

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
```

Aucun Hamiltonien physique S=4 n'a encore été construit ou diagonalisé. Aucune observable S=4 n'a été inspectée.

## Lot courant — L3-J

```text
LOT = L3-J-S4-CAMPAIGN-EXECUTION-PREFLIGHT
STATUS = OPEN
TYPE = EXECUTION_PREFLIGHT_ONLY

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO

DRY_RUN_MONKEYPATCHED_AUTHORIZED = YES
RESOURCE_INSPECTION_AUTHORIZED = YES
MANIFEST_FINGERPRINT_VERIFICATION_AUTHORIZED = YES
LEVEL2_REFERENCE_INTEGRITY_VERIFICATION_AUTHORIZED = YES
OUTPUT_PATH_PREFLIGHT_AUTHORIZED = YES

REAL_S4_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S4_DIAGONALIZATION_AUTHORIZED = NO
S4_OBSERVABLES_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : effectuer le dernier préflight d'exécution avant toute donnée physique S=4. Le lot doit vérifier l'environnement réel dans lequel la future campagne serait lancée, sans atteindre une vraie exécution `run_case(..., spin=4)` :

```text
- HEAD / branche / worktree ;
- manifeste Level3 et fingerprint canonique ;
- identité de pré-enregistrement ;
- SHA256SUMS et provenance de la référence Level2 ;
- planning exact des trois cas S4 ;
- dimensions attendues et garde dense ;
- chemins de sortie et politique NO_IMPLICIT_RESUME ;
- espace disque, RAM visible, CPU et environnement numérique ;
- dry-run complet du runner avec run_case strictement monkeypatché ;
- ordre 3/3 avant comparaison ;
- écriture campaign-summary en dernier ;
- absence de résultat normatif dans le dépôt après le dry-run.
```

Le dry-run doit utiliser un répertoire temporaire hors du dépôt et des `CaseExecutionResult` synthétiques conformes. Il doit échouer si le vrai `cosmobox.level3.execution.run_case` est atteint.

## Invariants L3-J

```text
LEVEL2 = CLOSED
LEVEL2_ARTIFACTS = FROZEN_REFERENCE
LEVEL2_RECOMPUTATION = FORBIDDEN
LEVEL3_S4_PREREGISTRATION = FROZEN
LEVEL3_CAMPAIGN_INFRASTRUCTURE = ACCEPTED
REAL_S4_EXECUTION = FORBIDDEN
S5_EXECUTION = FORBIDDEN
FULL_SPECTRUM = REQUIRED
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
NEXT_STEP = L3_J_S4_CAMPAIGN_EXECUTION_PREFLIGHT
REAL_S4_EXECUTION = FORBIDDEN
```

Après le rapport L3-J, ChatGPT audite le préflight. Lionel décide ensuite explicitement si la campagne normative réelle S=4 peut être autorisée. Aucun PASS de préflight ne lance automatiquement cette campagne.

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation / audit

Claude:
software implementation / repository operations / execution

Lionel:
intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un `PASS`, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
