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
LEVEL2_NORMATIVE_AUTHORIZATION = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
LEVEL2_SYNTHESIS = 10b8da8756112b9055c52b58e169707818cf6429
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = CLOSED

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_LOT = L2-FIRST-NORMATIVE-CAMPAIGN

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
LEVEL2_E_CAMPAIGN_LAYER = ACCEPTED
LEVEL2_FINAL_REAL_PREFLIGHT = ACCEPTED
LEVEL2_NORMATIVE_CAMPAIGN = COMPLETE
LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Documents scientifiques Level 2

- `docs/levels/level2/conceptual-framing.md`
- `docs/levels/level2/spectral-capability-audit.md`
- `docs/levels/level2/spectral-regime-design.md`
- `docs/levels/level2/profile-comparison-preregistration.md`
- `docs/levels/level2/numerical-guard-protocol.md`
- `docs/levels/level2/synthesis-and-closure.md`

La synthèse scientifique de référence est désormais :

```text
docs/levels/level2/synthesis-and-closure.md
```

## Campagne normative Level 2

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY = ioio2995/cosmobox
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
BRANCH = research/level2-energy-regime
FROZEN_PREREGISTRATION_COMMIT = 2d4c859db7939da51ee7d919889a18f4c7e229ed

CASE_COUNT = 6
GEOMETRY_COMPARISON_COUNT = 3
CAMPAIGN_STATUS = COMPLETE
```

Les six cas gelés ont été exécutés en spectre complet :

```text
triangle S=2 : D=88,   groupes=22
triangle S=3 : D=128,  groupes=32
ring4    S=2 : D=292,  groupes=106
ring4    S=3 : D=432,  groupes=158
ring5    S=2 : D=1000, groupes=226
ring5    S=3 : D=1504, groupes=342
```

Pour les six cas :

```text
solver_method = dense
window_truncated = false
partial_subspace_count = 0
multiplicity_coverage = complete
C_TT_conn persisted = yes
rho_QQ persisted = yes
```

## Résultat primaire Level 2

Le critère scientifique préenregistré était positif si au moins une géométrie reproduisait entre `S=2` et `S=3` la direction d'un contraste spectral primaire `HIGH-LOW` pour `M_TT` ou `R_eff`.

Résultat :

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

Donc :

```text
LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
```

La récurrence est observée dans plusieurs réalisations microscopiques mais n'est pas commune aux trois géométries.

## Limites physiques figées

Les descripteurs continus de forme `C_X_23` restent proches de zéro, sans qu'aucun seuil post-hoc ne soit introduit. La direction globale LOW→HIGH peut donc être reproduite alors que la forme détaillée du profil reste sensible à la troncature.

Les conclusions interdites restent :

```text
SAME_INTER_S_DIRECTION != convergence S -> infinity
NO_UNIVERSALITY_CLAIM
NO_EMERGENT_GEOMETRY_CLAIM
NO_EFFECTIVE_DIMENSION_CLAIM
NO_CURVATURE_CLAIM
NO_GRAVITY_CLAIM
```

Les métriques de contrôle `A_QQ` et `M_QQ` restent descriptives et ne portent aucune taxonomie primaire.

## Clôture Level 2

```text
LEVEL2 = CLOSED
NORMATIVE_CAMPAIGN = COMPLETE
NEW_METRIC_AFTER_CAMPAIGN = FORBIDDEN
NEW_THRESHOLD_AFTER_CAMPAIGN = FORBIDDEN
RESULT_BASED_RETRY = FORBIDDEN
POST_HOC_RECLASSIFICATION = FORBIDDEN
```

La campagne `level2-energy-regime-v1` ne doit pas être relancée, modifiée ou filtrée pour renforcer son résultat.

Toute suite doit constituer une nouvelle question scientifique avec cadrage et pré-enregistrement propres avant inspection de nouvelles données.

## Étape suivante

```text
NEXT_STEP = DEFINE_POST_LEVEL2_SCIENTIFIC_QUESTION
OPEN_METHODOLOGICAL_ITEM = NONE
```

Aucune phase « géométrie » ou « gravité » n'est ouverte automatiquement par la clôture positive de Level 2.

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
- Level 1 et Level 2 sont clos et ne doivent pas être réparés post-hoc.
- Aucun résultat physique ne doit être filtré, corrigé ou reclassifié pour obtenir une conclusion préférée.
- Aucun matching multiplet-par-multiplet S=2 vers S=3 ne peut être réintroduit dans l'interprétation de Level 2.
- Aucun élargissement post-hoc des gardes numériques n'est autorisé.
- Toute nouvelle étape scientifique doit être définie avant inspection de nouvelles données.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence de la clôture Level 1 est :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
