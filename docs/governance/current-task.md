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
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S4_PREREGISTERED

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-H-FREEZE-LEVEL2-REFERENCE-ARTIFACTS
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

avec `SHA256SUMS`. Ils constituent désormais la référence normative reproductible S=2/S=3 pour Level3. Level2 reste immuable et clos.

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

## Capacités Level 3 établies

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
```

Aucun Hamiltonien physique S=4 n'a encore été construit ou diagonalisé. Aucune observable S=4 n'a été inspectée.

## Lot courant — L3-I

```text
LOT = L3-I-S4-CAMPAIGN-INFRASTRUCTURE
STATUS = OPEN
TYPE = SOFTWARE_IMPLEMENTATION

CODE_CHANGE_AUTHORIZED = YES
COMMIT_AUTHORIZED = YES
PUSH_AUTHORIZED = YES

REAL_S4_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S4_DIAGONALIZATION_AUTHORIZED = NO
S4_OBSERVABLES_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : implémenter l'infrastructure Level3 nécessaire à la future campagne S=4 sans exécuter de cas physique S=4 : manifeste pré-enregistré, schémas, sérialisation, adaptateur de référence Level2 gelée, provenance, planning, gates, sorties atomiques, runner et tests logiciels.

Décisions d'architecture gelées pour ce lot :

```text
- Les artefacts versionnés Level2 sont la seule référence normative S2/S3.
- Aucune recomputation normative S2/S3.
- Le runner Level3 est distinct du runner Level2.
- Les utilitaires de campagne Level3 peuvent être localement dupliqués pour préserver l'isolation de campagne.
- Les primitives mathématiques génériques Level2 (profiles/orchestration/metrics/adapter) peuvent être réutilisées en lecture/import sans modifier leur contrat.
- Le style de clés JSON Level3 est snake_case.
- La reconstruction S3 depuis artefact gelé doit porter les scalaires/profils nécessaires ; aucune reconstruction de matrice brute supplémentaire n'est requise par le pré-enregistrement.
- Aucun résultat partiel de campagne ne vaut COMPLETE ; le résumé de campagne écrit en dernier est le marqueur de complétude.
```

## Invariants L3-I

```text
LEVEL2 = CLOSED
LEVEL2_ARTIFACTS = FROZEN_REFERENCE
LEVEL2_RECOMPUTATION = FORBIDDEN
LEVEL3_S4_PREREGISTRATION = FROZEN
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
NEXT_STEP = L3_I_S4_CAMPAIGN_INFRASTRUCTURE_IMPLEMENTATION
REAL_S4_EXECUTION = FORBIDDEN
```

Après livraison L3-I, ChatGPT audite le commit distant. Lionel accepte ou non le lot. Une autorisation séparée sera nécessaire avant tout préflight d'exécution ou toute campagne physique S=4.

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
