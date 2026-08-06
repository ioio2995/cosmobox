# Documentation Cosmobox

Ce fichier est le point d’entrée documentaire du dépôt.

## Gouvernance

- [`governance/documentation-governance.md`](governance/documentation-governance.md) — architecture documentaire, sources de vérité, statuts et règles de migration.
- [`governance/collaboration-governance.md`](governance/collaboration-governance.md) — rôles, cycle des lots, format des échanges et règles de livraison Git.

## Modèle physique

- [`model/physical-model.md`](model/physical-model.md) — modèle physique général et conventions communes.

## Décisions

- [`decisions/decisions.md`](decisions/decisions.md) — journal historique D001 à D016.
- [`decisions/D017-functional-documentation-layout.md`](decisions/D017-functional-documentation-layout.md) — migration vers l’arborescence fonctionnelle.

## Niveau 0

- [`levels/level0/specification.md`](levels/level0/specification.md)
- [`levels/level0/validation-plan.md`](levels/level0/validation-plan.md)

Statut : **clos**.

## Niveau 1B

- [`levels/level1/specification.md`](levels/level1/specification.md)
- [`levels/level1/validation-plan.md`](levels/level1/validation-plan.md)
- [`levels/level1/implementation-design.md`](levels/level1/implementation-design.md)
- [`../experiments/level1/preregistered-manifest.md`](../experiments/level1/preregistered-manifest.md)
- [`../schemas/level1/correlators-v1.schema.json`](../schemas/level1/correlators-v1.schema.json)

Statut : **spécification gelée, implémentation en cours**.

Jalon courant : **lot 1B-1 accepté** au commit `9a352b2e17fe989397996117b1b089174547db07`.

## Compatibilité des anciens chemins

Les anciens fichiers placés directement sous `docs/`, ainsi que les anciens chemins du manifeste et du schéma Level 1B, sont conservés temporairement sous forme de fichiers de redirection textuels. Ils ne sont plus des sources de vérité.

Tout nouveau document ou nouveau renvoi doit utiliser les chemins fonctionnels définis ci-dessus.
