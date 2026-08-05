# Cosmobox

Cosmobox est le socle logiciel d'un modèle de jauge U(1) fini sur graphe
(recherche sur un substrat quantique relationnel, piste A, niveau 0). Voir
`docs/project-context.md`, `docs/physical-model.md` et
`docs/level0-specification.md` pour le contexte et la spécification
complète.

L'ancien prototype de maillage diamant/blende déformable est archivé sur la
branche `legacy/mesh-prototype` (tag `legacy/mesh-prototype-v1`) et n'est
plus une fondation du code actuel.

## Arborescence

```text
src/cosmobox/level0/
├── lattice.py    # géométries finies déterministes (nœuds, liens, arbre, plaquettes)
└── encoding.py   # encodage canonique uint64 (occupations + flux)

tests/level0/
├── test_lattice.py
└── test_encoding.py
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest tests/ -v
```
