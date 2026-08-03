# Architecture logicielle

## Statut
Brouillon (Claude / logiciel)

## Principe fondamental

Le moteur de simulation ne contient jamais directement d'hypothèse physique.
Il expose uniquement des briques génériques (réseau spatial, nœuds, arêtes,
cellules, contraintes, solveur mécanique, moteur de propagation,
visualisation, mesures) et des interfaces d'injection que les modèles
physiques utilisent, par exemple :

```python
space.inject_edge_constraint(...)
space.inject_node_impulse(...)
space.inject_energy(...)
```

Les lois physiques doivent pouvoir être remplacées sans modifier le cœur du
moteur.

## État actuel du code

```
cosmobox/
├── core/
│   ├── config.py
│   ├── matrix.py
│   ├── mechanics.py
│   └── simulation.py
├── physics/
│   ├── particle.py
│   └── metrics.py
├── visualization/
│   └── animation.py
└── cli.py
```

## Architecture cible

```
cosmobox/
├── core/
│   ├── node.py
│   ├── edge.py
│   ├── tetrahedron.py
│   └── lattice.py
├── physics/
│   ├── elasticity.py
│   ├── propagation.py
│   ├── mechanics.py
│   └── constraints.py
├── particles/
│   ├── particle.py
│   ├── photon.py
│   ├── mass.py
│   └── composite.py
├── simulation/
│   ├── engine.py
│   └── scheduler.py
├── renderer/
│   ├── animation.py
│   └── renderer3d.py
├── io/
│   ├── yaml_loader.py
│   └── csv_export.py
├── docs/
├── experiments/
└── tests/
```

Chaque module a une responsabilité unique et les dépendances restent limitées
(`particles` dépend de `core`/`physics` via les interfaces d'injection, jamais
l'inverse).

## Statut de la migration

Pas encore commencée. La structure actuelle (`core/`, `physics/`,
`visualization/`, `cli.py` plat) doit migrer vers le layout ci-dessus. Cette
migration fera l'objet d'un ADR dédié dans `05_decisions/` avant exécution.

## Reproductibilité

- Toute configuration d'expérience (`examples/*.yaml`) doit rester versionnée.
- Les sorties (`output/`) ne sont pas versionnées (voir `.gitignore`) ; ce qui
  doit être reproductible, c'est la configuration + le code, pas le résultat
  lui-même.
