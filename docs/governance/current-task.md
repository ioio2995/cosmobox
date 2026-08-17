# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet jusqu'à la clôture de Level 1 est archivé dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md). La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime
LEVEL2_FROZEN_PREREGISTRATION = 2d4c859db7939da51ee7d919889a18f4c7e229ed
LEVEL2_NORMATIVE_AUTHORIZATION = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
LEVEL2_SYNTHESIS = 10b8da8756112b9055c52b58e169707818cf6429
LEVEL2_CLOSURE_GOVERNANCE = bf3dd8c7399181d527ea4956ed06379480246809
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = DEFINITION_IN_PROGRESS

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_LOT = L2-FIRST-NORMATIVE-CAMPAIGN

LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Référence Level 2

Campagne normative close :

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
CAMPAIGN_STATUS = COMPLETE
```

Résultat primaire :

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

## Question scientifique post-Level2

Level 2 montre une dépendance spectrale primaire récurrente mais une forte sensibilité de la forme détaillée des profils à la troncature `S`, avec inversion de direction sur `ring5` entre `S=2` et `S=3`.

La nouvelle question scientifique est :

> Les observables relationnelles admettent-elles une stabilisation lorsque la troncature du champ de jauge est progressivement relâchée, c'est-à-dire lorsque `S` augmente au-delà de 3 ?

Le but n'est pas de choisir une valeur particulière de `S` comme nouvelle physique, mais de rendre `S` configurable puis d'étudier successivement `S=4,5,6,...` tant que le calcul exact reste accessible et que chaque nouvelle valeur apporte une information scientifique utile.

## Principe Level 3

```text
LEVEL3_WORKING_NAME = TRUNCATION_CONVERGENCE
S_ROLE = GAUGE_FIELD_TRUNCATION_PARAMETER
S_IS_NEW_PHYSICAL_FIELD = NO
S_IS_SPACETIME_DIMENSION = NO
S_CONFIGURABLE_IN_CODE = TARGET
PHYSICAL_MODEL_CHANGE = NO
NEW_OBSERVABLE_AT_THIS_STAGE = NO
```

La généralisation logicielle ne doit modifier ni :

```text
Hamiltonian definitions
Gauss constraint
matter content
lattice geometries
C_TT_conn definition
rho_QQ definition
M_TT / R_eff / A_QQ / M_QQ definitions
Level2 archived results
```

## Lot courant — L3-A

```text
LOT = L3-A-SPIN-GENERALIZATION-AUDIT
STATUS = OPEN
TYPE = SOFTWARE_AUDIT_ONLY
CODE_CHANGE_AUTHORIZED = NO
REAL_S4_EXECUTION_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : cartographier tous les endroits où `S` est artificiellement limité à `{2,3}` ou où les comparaisons sont structurellement codées `S=2 ↔ S=3`, puis proposer la généralisation minimale permettant :

```text
CaseSpec(geometry, spin) with configurable valid spin
run_case unchanged as far as possible
pairwise comparison S_a ↔ S_b without hard-coded 2/3 roles
campaign/planning capable of explicit spin sets
strict S=2/S=3 regression preservation
```

Le cœur Level0 doit être audité séparément pour confirmer qu'il accepte déjà des spins supérieurs sans hypothèse cachée `S in {2,3}`.

## Contraintes de conception Level 3

```text
- Level 2 reste immuable et clos.
- Aucun artefact de la campagne Level 2 ne doit être réécrit.
- La généralisation de S est une généralisation d'interface/exécution, pas une modification de la physique.
- Aucun calcul réel S=4 n'est autorisé pendant l'audit L3-A.
- Aucun seuil de convergence n'est défini pendant L3-A.
- Aucun résultat S=4 ne doit être inspecté avant pré-enregistrement scientifique dédié.
- Les comparaisons futures doivent pouvoir porter sur des paires explicites de spins sans supposer S=2 et S=3.
- Les résultats S=2 et S=3 existants doivent rester des références de non-régression.
```

## Étape suivante

```text
NEXT_STEP = L3_A_SPIN_GENERALIZATION_AUDIT
OPEN_METHODOLOGICAL_ITEM = DEFINE_CONVERGENCE_PROTOCOL_AFTER_SOFTWARE_GENERALIZATION
```

Après audit Claude, ChatGPT arbitre l'architecture. Lionel autorise ensuite explicitement l'implémentation. Aucune implémentation n'est autorisée implicitement par l'ouverture de l'audit.

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
- L'unité de progrès reste l'expérience scientifique, pas le lot logiciel.
- Level 1 et Level 2 sont clos et ne doivent pas être réparés post-hoc.
- Toute nouvelle donnée S>3 doit être obtenue uniquement après cadrage et pré-enregistrement adaptés.
- Une limite de calcul est un résultat de capacité, jamais une justification pour changer silencieusement de solveur ou de protocole.
- Aucune géométrie ni gravité ne sont ouvertes par la seule généralisation de S.
```
