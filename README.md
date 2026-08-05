# Cosmobox

Cosmobox est le socle logiciel d'un modèle de jauge U(1) fini sur graphe
(recherche sur un substrat quantique relationnel, piste A). Le projet avance
par niveaux, chacun défini par une spécification normative avant toute
implémentation scientifique.

L'ancien prototype de maillage diamant/blende déformable est archivé sur la
branche `legacy/mesh-prototype` (tag `legacy/mesh-prototype-v1`) et n'est
plus une fondation du code actuel.

## Gouvernance documentaire

La charte normative du dépôt est :

```text
docs/documentation-governance.md
```

Elle définit la hiérarchie des sources, le rôle des répertoires, les statuts
documentaires, les règles de migration des features et les contrôles
obligatoires avant tout gel ou push documentaire.

Répartition des sources :

- `docs/physical-model.md` : modèle physique général ;
- `docs/levelN-specification.md` : spécification normative d'un niveau ;
- `docs/decisions.md` : décisions gelées et historique des arbitrages ;
- `docs/levelN-validation-plan.md` : contrat de validation ;
- `experiments/` : manifestes et protocoles de campagne ;
- `schemas/` : contrats de sérialisation versionnés ;
- `features/` : propositions temporaires non gelées uniquement ;
- `src/`, `scripts/` et `tests/` : implémentation et validation.

Le code doit implémenter les documents normatifs, jamais introduire
silencieusement une nouvelle hypothèse physique.

## État d'avancement

- **Niveau 0 — clos.** Modèle de jauge U(1) fini exact : géométries,
  encodage canonique, base physique (loi de Gauss exacte), Hamiltonien
  creux complet, diagnostics spectraux avec dégénérescence, générateurs de
  symétrie (saveur SU(2), translation, réflexion) et diagnostics restreints
  par sous-espace. Spécification : `docs/level0-specification.md`.
  Synthèse : `experiments/LEVEL0-synthesis-and-closure.md`.
  Campagnes de référence exécutées : `results/level0-reference-v1/`,
  `results/level0-symmetry-v1/` (non suivies par git).

- **Niveau 1B — spécification scientifique gelée, implémentation non encore
  commencée.** Corrélateurs matière–matière invariants de jauge habillés par
  lignes de Wilson, corrélateurs de charge et de saveur, prescriptions de
  multiplets, robustesse inter-troncatures et agrégation par orbites.
  Spécification : `docs/level1-specification.md`.
  Validation : `docs/level1-validation-plan.md`.
  Manifeste : `experiments/LEVEL1B-preregistered-manifest.md`.
  Schéma : `schemas/level1-correlators-v1.schema.json`.

## Arborescence du moteur niveau 0

```text
src/cosmobox/level0/
├── lattice.py       # géométries finies déterministes
├── encoding.py      # encodage canonique uint64
├── charges.py       # normalisation des charges externes
├── basis.py         # base physique exacte
├── gauge.py         # loi de Gauss
├── operators.py     # primitives fermioniques et de lien
├── params.py        # paramètres du Hamiltonien
├── hamiltonian.py   # H_dot + H_hop + H_E + H_B
├── degeneracy.py    # regroupement spectral
├── reports.py       # diagnostics numériques
├── symmetries.py    # saveur et automorphismes
└── experiments.py   # exécution et export JSON

scripts/
├── level0_reference_campaign/
└── level0_symmetry_campaign/

tests/level0/
tests/
```

609 tests (`pytest -q`), tous passants sur `research/level0-gauge` fusionnée
dans `main`.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest -q
```

## Lancer une campagne niveau 0

```bash
python -m scripts.run_level0_reference_campaign --output-dir <répertoire>
python -m scripts.run_level0_symmetry_campaign --output-dir <répertoire>
```

Ces campagnes sont reprenables, utilisent des écritures atomiques et
n'écrivent rien par défaut dans un répertoire suivi par git.
