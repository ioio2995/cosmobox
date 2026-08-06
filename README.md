# Cosmobox

Cosmobox est le socle logiciel d’un modèle de jauge U(1) fini sur graphe, développé par niveaux scientifiques gelés avant implémentation.

L’ancien prototype de maillage déformable reste archivé sur `legacy/mesh-prototype` et ne constitue plus une fondation du code actuel.

## Documentation

L’index documentaire principal est :

```text
docs/README.md
```

Les règles transverses sont :

```text
docs/governance/documentation-governance.md
docs/governance/collaboration-governance.md
```

Organisation fonctionnelle :

```text
docs/
├── README.md
├── governance/
├── model/
├── decisions/
└── levels/
    ├── level0/
    └── level1/
```

Les manifestes expérimentaux et schémas de sérialisation sont également classés par niveau :

```text
experiments/level1/
schemas/level1/
```

## État d’avancement

- **Niveau 0 — clos.** Spécification : `docs/levels/level0/specification.md`. Plan de validation : `docs/levels/level0/validation-plan.md`.
- **Niveau 1B — spécification gelée, implémentation en cours par lots.** Le lot **1B-1** (chemins orientés, transporteurs et opérateurs de matière habillés) est accepté au commit `9a352b2e17fe989397996117b1b089174547db07`.
- Prochain lot non commencé : **1B-2**, observables locales de charge et de saveur.

Documents Level 1B :

```text
docs/levels/level1/specification.md
docs/levels/level1/validation-plan.md
docs/levels/level1/implementation-design.md
experiments/level1/preregistered-manifest.md
schemas/level1/correlators-v1.schema.json
```

## Code

```text
src/cosmobox/
├── level0/
└── level1/
    ├── paths.py
    ├── transporters.py
    └── matter.py

tests/
├── level0/
└── level1/
```

À la clôture du lot 1B-1, la suite complète comporte **665 tests passants**.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```
