# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique jusqu'à la clôture de Level 1 est archivé dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md). La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime

LEVEL2_FROZEN_PREREGISTRATION = 2d4c859db7939da51ee7d919889a18f4c7e229ed
LEVEL2_NORMATIVE_AUTHORIZATION = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
LEVEL2_SYNTHESIS = 10b8da8756112b9055c52b58e169707818cf6429
LEVEL2_CLOSURE_GOVERNANCE = bf3dd8c7399181d527ea4956ed06379480246809

LEVEL3_A_GOVERNANCE_OPENING = 6ccc360267593a63219812cc81cf30eac002cca4
LEVEL3_A_SPIN_ENCODING_IMPLEMENTATION = c7e43771fdf3ed23720bfb245c8c8d3bb320a257
LEVEL3_B_GOVERNANCE_OPENING = 6e87bc6d5f1140abff6d95f3c17a253bbac7f42b
LEVEL3_B_GENERIC_EXECUTION_IMPLEMENTATION = ce2c7a16387490bb13ba1156249ea1129ec3bbc9
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = CAPABILITY_PREFLIGHT

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_LOT = L3-B-GENERIC-EXECUTION-LAYER

LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Référence Level 2

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
CAMPAIGN_STATUS = COMPLETE
```

Résultat primaire figé :

```text
triangle:
  M_TT  = SAME_INTER_S_DIRECTION
  R_eff = SAME_INTER_S_DIRECTION

ring4:
  M_TT  = SAME_INTER_S_DIRECTION
  R_eff = SAME_INTER_S_DIRECTION

ring5:
  M_TT  = OPPOSITE_INTER_S_DIRECTION
  R_eff = OPPOSITE_INTER_S_DIRECTION
```

Limites figées :

```text
NO_UNIVERSALITY_CLAIM
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
LEVEL2_RESULT_RETRY = FORBIDDEN
LEVEL2_POST_HOC_METRIC = FORBIDDEN
```

## Question scientifique Level 3

> Les observables relationnelles admettent-elles une stabilisation lorsque la troncature du champ de jauge est progressivement relâchée, c'est-à-dire lorsque `S` augmente au-delà de 3 ?

```text
LEVEL3_WORKING_NAME = TRUNCATION_CONVERGENCE
S_ROLE = GAUGE_FIELD_TRUNCATION_PARAMETER
S_IS_NEW_PHYSICAL_FIELD = NO
S_IS_SPACETIME_DIMENSION = NO
PHYSICAL_MODEL_CHANGE = NO
```

## Lots Level 3 acceptés

### L3-A — généralisation de l'encodage spin

```text
STATUS = ACCEPTED
IMPLEMENTATION_COMMIT = c7e43771fdf3ed23720bfb245c8c8d3bb320a257
LEVEL0_SPIN_ENCODING_GENERIC = YES
```

Politique d'encodage :

```text
flux_bits_per_edge(spin) = max(3, (2*spin).bit_length())
```

L'encodage historique `S=1,2,3` reste bit-à-bit inchangé.

### L3-B — couche d'exécution générique

```text
STATUS = ACCEPTED
IMPLEMENTATION_COMMIT = ce2c7a16387490bb13ba1156249ea1129ec3bbc9
LEVEL3_CASESPEC_GENERIC = YES
LEVEL3_RUN_CASE_IMPLEMENTED = YES
LEVEL3_SPIN_PAIR_COMPARISON = YES
LEVEL2_FILES_MODIFIED = NO
REAL_S4_EXECUTION = NO
NEW_PHYSICAL_RESULT_INSPECTED = NO
```

La couche `src/cosmobox/level3/` permet désormais de représenter un spin générique et des comparaisons `S_a <-> S_b` sans modifier les contrats Level2.

## Lot courant — L3-C

```text
LOT = L3-C-S4-CAPABILITY-PREFLIGHT
STATUS = OPEN
TYPE = CAPABILITY_EXECUTION

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO

S4_BASIS_CONSTRUCTION_AUTHORIZED = YES
S4_HILBERT_DIMENSION_INSPECTION_AUTHORIZED = YES
S4_MEMORY_COST_ESTIMATION_AUTHORIZED = YES
S4_HAMILTONIAN_BUILD_AUTHORIZED = NO
S4_DIAGONALIZATION_AUTHORIZED = NO
S4_OBSERVABLES_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : déterminer, avant toute donnée physique Level3, si les trois réalisations microscopiques de référence `triangle`, `ring4`, `ring5` restent accessibles en spectre complet à `S=4`.

Le préflight peut construire les bases physiques `S=4` avec les paramètres gelés :

```text
n_flavors = 2
external_charges = 0
geometry in {triangle, ring4, ring5}
spin = 4
```

Il peut inspecter :

```text
physical_basis_dimension
encoding_required_bits
estimated_dense_matrix_elements = D^2
estimated_dense_real_bytes = 8 * D^2
estimated_dense_complex_bytes = 16 * D^2
```

Ces estimations sont des métriques de capacité numérique, pas des observables physiques.

Interdit pendant L3-C :

```text
build_hamiltonian_terms for a real S=4 case
build_level0_report_with_eigenvectors for S=4
any eigensolver / diagonalization at S=4
adapter.build_case_multiplet_profile at S=4
C_TT_conn at S=4
rho_QQ at S=4
M_TT / R_eff / A_QQ / M_QQ at S=4
any inter-S scientific classification using S=4
```

Le lot doit s'arrêter après le rapport de capacité. Aucun protocole de convergence, seuil, campagne ou interprétation scientifique ne peut être défini à partir de ce préflight.

## Invariants Level 3

```text
- Level 2 reste immuable et clos.
- Aucune définition physique ne change.
- Aucun nouvel observable n'est créé.
- Aucun seuil de convergence n'est défini avant pré-enregistrement dédié.
- Aucun matching multiplet-par-multiplet inter-S.
- Toute nouvelle donnée physique S>3 exige un cadrage scientifique séparé.
- Une limite de calcul est un résultat de capacité, pas une justification pour changer silencieusement de solveur ou de protocole.
- PHASE_GEOMETRY reste CLOSED.
- PHASE_GRAVITY reste CLOSED.
```

## Étape suivante

```text
NEXT_STEP = L3_C_S4_CAPABILITY_PREFLIGHT
OPEN_METHODOLOGICAL_ITEM = DEFINE_LEVEL3_CONVERGENCE_PROTOCOL_AFTER_CAPABILITY_PREFLIGHT
```

Après le rapport L3-C, ChatGPT audite les dimensions et estimations. Lionel décide ensuite si un cadrage scientifique `S=4` peut être ouvert.

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
