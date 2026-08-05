# Cosmobox

Cosmobox est le socle logiciel d'un modèle de jauge U(1) fini sur graphe
(recherche sur un substrat quantique relationnel, piste A). Le projet avance
par niveaux, chacun défini par un document de spécification physique
(rédigé côté physique) avant tout code (rédigé côté ingénierie).

L'ancien prototype de maillage diamant/blende déformable est archivé sur la
branche `legacy/mesh-prototype` (tag `legacy/mesh-prototype-v1`) et n'est
plus une fondation du code actuel.

## Répartition des rôles

- **Physique / spécification** : `docs/*.md` (conventions gelées du niveau 0),
  `features/*.md` (définition d'un niveau à venir), `experiments/*.md`
  (synthèses de clôture). Ces documents sont la source de vérité ; le code
  doit implémenter ce qu'ils décrivent, jamais l'inverse.
- **Ingénierie** : `src/cosmobox/level0/` (moteur), `scripts/` (outillage de
  campagnes, hors moteur), `tests/`. N'introduit aucune hypothèse physique
  non validée par les documents ci-dessus.

## État d'avancement

- **Niveau 0 — clos.** Modèle de jauge U(1) fini exact : géométries,
  encodage canonique, base physique (loi de Gauss exacte), Hamiltonien
  creux complet, diagnostics spectraux avec dégénérescence, générateurs de
  symétrie (saveur SU(2), translation, réflexion) et diagnostics restreints
  par sous-espace. Synthèse : `experiments/LEVEL0-synthesis-and-closure.md`.
  Campagnes de référence exécutées : `results/level0-reference-v1/`,
  `results/level0-symmetry-v1/` (non suivies par git).
- **Niveau 1 — définition, pas encore implémenté.** Corrélateurs
  matière–matière invariants de jauge habillés par lignes de Wilson.
  Spécification : `features/LEVEL1-gauge-invariant-correlators.md`
  (branche `research/level1-correlators`). Aucun code n'a été écrit tant
  que les décisions ouvertes listées en fin de document n'ont pas été
  tranchées.

## Arborescence (niveau 0, moteur)

```text
src/cosmobox/level0/
├── lattice.py       # géométries finies déterministes (nœuds, liens, arbre, plaquettes)
├── encoding.py      # encodage canonique uint64 (occupations + flux)
├── charges.py       # normalisation des charges externes
├── basis.py         # base physique exacte (résolution de la loi de Gauss par l'arbre)
├── gauge.py         # loi de Gauss, vérification indépendante de la physicité
├── operators.py     # primitives fermioniques/de lien (create, annihilate, transport, ...)
├── params.py        # HamiltonianParameters (J, h, t, g_E, K)
├── hamiltonian.py   # assemblage creux H_dot + H_hop + H_E + H_B
├── degeneracy.py    # regroupement spectral ancré sur tolérance relative
├── reports.py       # diagnostics numériques (spectre, hermiticité, ...)
├── symmetries.py    # générateurs de saveur, automorphismes de graphe, diagnostics restreints
└── experiments.py   # exécution d'une expérience + export JSON canonique

scripts/
├── level0_reference_campaign/    # campagne 5B (grille 72 configs, S=1 référence)
└── level0_symmetry_campaign/     # campagne 6C (grille 8 configs, S=2, diagnostics T^2/T/R)

tests/level0/   # un fichier de test par module du moteur
tests/          # tests des deux campagnes (test_reference_campaign.py, test_symmetry_campaign.py)
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

## Lancer une campagne (outillage, pas une exécution scientifique en soi)

```bash
python -m scripts.run_level0_reference_campaign --output-dir <répertoire>
python -m scripts.run_level0_symmetry_campaign --output-dir <répertoire>
```

Les deux sont reprenables (écritures atomiques, validation de l'existant) et
n'écrivent rien par défaut dans un répertoire suivi par git.
