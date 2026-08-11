# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet de gouvernance jusqu'à la clôture de Level 1 est archivé par snapshot Git dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md).

## État Git accepté

```text
CURRENT_ACCEPTED_HEAD = f2c63722e69f552a85212db5c4dd787d0c10c7cf
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = NOT_STARTED

LAST_CLOSED_LEVEL = LEVEL1

LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
PHASE_G_OPENED           = NO

NEXT_SCIENTIFIC_AXIS = ENERGY_SPECTRAL_REGIME
```

## Références scientifiques de clôture

- `docs/levels/level1/level1-synthesis-and-closure.md`
- `docs/levels/level1c/level1c-conclusion.md`
- `docs/levels/level1/level1b-conclusion.md`
- `experiments/LEVEL0-synthesis-and-closure.md`

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation

Claude:
software implementation / repository operations / execution

Lionel:
intuition / direction / final decision
```

La documentation scientifique de Level 2 est placée sous la responsabilité de ChatGPT. Aucune implémentation Level 2 ne démarre avant acceptation explicite du cadrage scientifique correspondant.

## Règles de progression

```text
- Level 2 n'est pas encore ouvert.
- Aucune implémentation Level 2 sans cadrage scientifique accepté.
- L'unité de progrès est l'expérience scientifique, pas le lot logiciel.
- Un défaut logiciel ne bloque que s'il peut altérer le résultat physique,
  sa provenance ou son interprétation.
- Aucun résultat de Level 1C ne doit être « réparé » post-hoc : Level 1 est clos.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence est le commit :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
