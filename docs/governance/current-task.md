# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet de gouvernance jusqu'à la clôture de Level 1 est archivé par snapshot Git dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime
CURRENT_ACCEPTED_HEAD = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
LEVEL2_FRAMING_CANDIDATE = 39a7f3ca5a28850ed96e436251c9c094b4f16a76
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = L2_A_CONCEPTUAL_FRAMING

LAST_CLOSED_LEVEL = LEVEL1

LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
PHASE_G_OPENED           = NO

LEVEL2_PRIMARY_AXIS = ENERGY_SPECTRAL_REGIME
LEVEL2_IMPLEMENTATION = NOT_STARTED
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

## Document scientifique actif

- `docs/levels/level2/conceptual-framing.md`

Objet : déterminer si l'organisation des observables relationnelles invariantes de jauge dépend du régime énergétique/spectral, avant toute nouvelle tentative de reconstruction géométrique.

Le document ouvre uniquement `L2-A`. Il n'autorise aucun manifeste, aucune grille numérique, aucun seuil, aucune campagne et aucune implémentation.

## Prochaine question scientifique

```text
Quelle portion du spectre est réellement accessible,
avec quelles informations par état ou par multiplet,
sur les systèmes actuels ?
```

Après acceptation du cadrage, la prochaine action est un audit scientifique read-only des capacités spectrales actuelles. Le design expérimental Level 2 sera dérivé de cet audit et non présupposé.

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
- L'unité de progrès est l'expérience scientifique, pas le lot logiciel.
- Aucun code Level 2 avant conception scientifique acceptée.
- Aucun résultat de Level 1C ne doit être réparé post-hoc : Level 1 est clos.
- Un défaut logiciel ne bloque que s'il peut altérer le résultat physique,
  sa provenance ou son interprétation.
- Une métrique Level 2 ne sera gelée que si sa signification physique ou
  structurelle est explicite et si son comportement nul est interprétable.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence de la clôture Level 1 est le commit :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
