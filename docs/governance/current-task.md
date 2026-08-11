# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet de gouvernance jusqu'à la clôture de Level 1 est archivé par snapshot Git dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime
CURRENT_ACCEPTED_HEAD = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
LEVEL2_FRAMING_CANDIDATE = 39a7f3ca5a28850ed96e436251c9c094b4f16a76
LEVEL2_SPECTRAL_AUDIT_CANDIDATE = 372bfe5884e67c0f31ca9387601b3378605b30bf
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = L2_A_SPECTRAL_CAPABILITY_AUDIT

LAST_CLOSED_LEVEL = LEVEL1

LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
PHASE_G_OPENED           = NO

LEVEL2_PRIMARY_AXIS = ENERGY_SPECTRAL_REGIME
LEVEL2_IMPLEMENTATION = NOT_STARTED
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

## Documents scientifiques actifs

- `docs/levels/level2/conceptual-framing.md`
- `docs/levels/level2/spectral-capability-audit.md`

Objet : déterminer si l'organisation des observables relationnelles invariantes de jauge dépend du régime énergétique/spectral, avant toute nouvelle tentative de reconstruction géométrique.

## Résultat L2-A de l'audit spectral

L'audit read-only du solveur et du manifeste Level 1B établit, pour `triangle`, `ring4`, `ring5` et `S in {1,2,3}` :

```text
MAX_PHYSICAL_DIMENSION = 1504
DENSE_SOLVER_THRESHOLD = 2000
FULL_SPECTRUM_FOR_LEVEL2_CORE_CASES = AVAILABLE
NEW_SPECTRAL_APPROXIMATION_REQUIRED = NO
E_MAX_EXACTLY_AVAILABLE = YES
```

Le chemin dense actuel exécute déjà une eigendecomposition complète via `numpy.linalg.eigh` puis tronque seulement la restitution à `n_eigenvalues`. Pour les cas centraux proposés de Level 2, conserver tout le spectre ne nécessite donc pas un nouveau solveur ni une approximation du milieu/haut du spectre.

L'infrastructure Level 1 sait déjà calculer `C_TT_conn` et `rho_QQ` sur un `SpectralGroupState`, mais le runner Level 1B ne les produit que pour des groupes sélectionnés par `target_groups`. Level 2 devra utiliser comme unité scientifique les multiplets complets du spectre complet, sans branche cible et sans tracking inter-Hamiltonien.

## Périmètre scientifique proposé pour la première campagne

```text
Hamiltonien : reference uniquement
n_flavors   : 2
charges ext : 0
geometries  : triangle, ring4, ring5
spin        : S=2, S=3
spectre     : complet

PRIMARY = C_TT_conn
CONTROL = rho_QQ
BRANCH_TRACKING_REQUIRED = NO
PHASE_G = OUT_OF_SCOPE
```

Les métriques structurelles proposées dans l'audit restent candidates et ne sont pas encore gelées.

## Prochaine étape

```text
NEXT_STEP = FULL_SPECTRUM_RESOURCE_PREFLIGHT
```

Le préflight doit rester non interprétatif et ne produire aucun verdict physique. Il doit mesurer uniquement, pour les six cas principaux proposés : dimension, méthode solveur, coût de calcul, nombre d'eigenpaires, nombre de groupes spectraux, statut complet/partiel, distribution des multiplicités, `E_min` et `E_max`.

Aucune valeur de `C_TT_conn` ou `rho_QQ` ne doit être analysée physiquement pendant ce préflight.

Après ce préflight, ChatGPT rédigera L2-B et décidera si les métriques candidates et le découpage spectral peuvent être gelés.

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

La documentation scientifique de Level 2 est placée sous la responsabilité de ChatGPT. Aucune campagne normative Level 2 ne démarre avant acceptation explicite de son pré-enregistrement scientifique.

## Règles de progression

```text
- L'unité de progrès est l'expérience scientifique, pas le lot logiciel.
- Aucun résultat de Level 1C ne doit être réparé post-hoc : Level 1 est clos.
- Un défaut logiciel ne bloque que s'il peut altérer le résultat physique,
  sa provenance ou son interprétation.
- Une métrique Level 2 ne sera gelée que si sa signification physique ou
  structurelle est explicite et si son comportement nul est interprétable.
- Aucun seuil binaire de réponse physique ne doit être réintroduit.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence de la clôture Level 1 est le commit :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
