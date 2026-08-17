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
LEVEL3_C_GOVERNANCE_OPENING = 8cbefa7b712915b15a07e68686e92480062634e6
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = SOLVER_CAPABILITY

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_LOT = L3-C-S4-CAPABILITY-PREFLIGHT

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

### L3-C — préflight de capacité S=4

```text
STATUS = ACCEPTED
TYPE = CAPABILITY_EXECUTION
CODE_CHANGE_PERFORMED = NO

TRIANGLE_S4_DIMENSION = 168
RING4_S4_DIMENSION = 572
RING5_S4_DIMENSION = 2008

S4_BASIS_CONSTRUCTION = COMPLETE
S4_HAMILTONIAN_BUILT = NO
S4_DIAGONALIZATION = NO
S4_OBSERVABLES_COMPUTED = NO
NEW_PHYSICAL_RESULT_INSPECTED = NO
```

La croissance descriptive de dimension est :

```text
triangle: D4/D3 = 1.3125
ring4:    D4/D3 ~= 1.3241
ring5:    D4/D3 ~= 1.3351
```

La capacité d'encodage uint64 reste suffisante pour les trois cas S=4.

Point bloquant identifié avant toute campagne physique :

```text
SpectrumOptions.max_dense_dimension = 2000
RING5_S4_DIMENSION = 2008
```

Le dispatcher spectral Level0 sélectionne le chemin dense uniquement pour `dimension <= max_dense_dimension`. Au-delà, le chemin sparse `eigsh` ne peut fournir au maximum que `dimension - 1` valeurs propres, alors que Level3 exige le spectre complet.

Donc :

```text
TRIANGLE_S4_CURRENT_FULL_SPECTRUM_PATH = AVAILABLE
RING4_S4_CURRENT_FULL_SPECTRUM_PATH = AVAILABLE
RING5_S4_CURRENT_FULL_SPECTRUM_PATH = BLOCKED_BY_DENSE_POLICY_THRESHOLD
```

Ce blocage est numérique / logiciel, pas physique.

## Lot courant — L3-D

```text
LOT = L3-D-FULL-SPECTRUM-SOLVER-CAPABILITY
STATUS = OPEN
TYPE = NUMERICAL_CAPABILITY_ONLY

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO

SYNTHETIC_DENSE_BENCHMARK_AUTHORIZED = YES
REAL_S4_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S4_DIAGONALIZATION_AUTHORIZED = NO
S4_OBSERVABLES_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : déterminer si une diagonalisation dense complète de dimension comparable à `D=2008` est techniquement raisonnable sur l'environnement d'exécution courant, sans utiliser le Hamiltonien physique S=4 et sans produire aucune donnée physique S=4.

Le lot peut utiliser des matrices Hermitiennes synthétiques et contrôlées de dimensions autour de 2008 pour mesurer :

```text
wall time
peak memory if safely measurable
full eigenvalue/eigenvector completion
numerical residual / reconstruction checks appropriate to the synthetic matrix
```

Le benchmark ne doit pas modifier `max_dense_dimension` ni aucun code. Il ne doit pas construire ou diagonaliser un Hamiltonien Cosmobox S=4.

## Invariants Level 3

```text
- Level 2 reste immuable et clos.
- Aucune définition physique ne change.
- Aucun nouvel observable n'est créé.
- Aucun seuil de convergence scientifique n'est défini.
- Aucun matching multiplet-par-multiplet inter-S.
- Toute nouvelle donnée physique S>3 exige un cadrage scientifique séparé.
- Une limite de calcul est un résultat de capacité, pas une justification pour changer silencieusement de solveur ou de protocole.
- PHASE_GEOMETRY reste CLOSED.
- PHASE_GRAVITY reste CLOSED.
```

## Étape suivante

```text
NEXT_STEP = L3_D_FULL_SPECTRUM_SOLVER_CAPABILITY
OPEN_METHODOLOGICAL_ITEM = DEFINE_LEVEL3_CONVERGENCE_PROTOCOL_AFTER_SOLVER_CAPABILITY
```

Après le rapport L3-D, ChatGPT audite le benchmark. Lionel décide ensuite si une politique dense Level3 peut être cadrée explicitement avant tout résultat physique S=4.

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
