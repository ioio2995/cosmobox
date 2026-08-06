# Contrat de continuité — lot actif (anti-compactage)

Ce document est un contrat de reprise, pas une documentation scientifique. Il doit être relu intégralement (avec les documents qu'il référence) avant toute action de code, commit ou push si le contexte conversationnel a été compacté ou paraît incomplet.

## Dernier commit accepté

```text
dcea01cbd9a741b1fdff0799c53de67101e543c0
```

D021 accepté à ce commit, sur `research/level1-correlators`.

## Lot actif

1B-8b — identité exacte des groupes spectraux mono-cas (D022).

Ce sous-lot corrige une collision d'identité découverte en construisant le runner mono-cas du lot 1B-8 (toujours suspendu, voir ci-dessous) : `SpectralGroupIdentity` (status/multiplicity/twice_T seuls, gelée au lot 1B-7) ne discrimine pas exhaustivement deux groupes spectraux distincts d'un même cas — collision réelle observée sur triangle S=2 `j_break`.

## Objectif

Étendre `SpectralGroupIdentity` avec `spectral_window_group_index` (discriminant exact, position dans la séquence complète et non filtrée des groupes spectraux du cas) et `representative_energy` (métadonnée descriptive exacte, jamais le discriminant). Propager ces deux champs dans le schéma v2, la sérialisation, et l'ordre d'assemblage — sans affaiblir `AssemblyContradiction`, sans toucher à l'appariement inter-S.

## Périmètre autorisé

- `SpectralGroupIdentity` (nouveaux champs + validations) et `build_spectral_group_identity` (constructeur dérivé, contrôles croisés `SpectralLevelGroup`/`SpectralGroupState`) dans `src/cosmobox/level1/results.py`.
- `src/cosmobox/level1/serialization.py` : les deux champs dans le payload v2 de `spectral_group`.
- `schemas/level1/correlators-v2.schema.json` : les deux champs rendus obligatoires dans `$defs/spectralGroupIdentity`. `correlators-v1.schema.json` non modifié.
- `src/cosmobox/level1/assembly.py` : `_sort_key` seulement, pour un ordre spectral explicite `(spectral_window_group_index, status, multiplicity, twice_T, representative_energy)`. `_identity_key`/`AssemblyContradiction` non affaiblis (les deux nouveaux champs y entrent déjà automatiquement, sans modification de code, car la clé hash déjà le dictionnaire `spectral_group` entier).
- `src/cosmobox/level1/__init__.py` : export de `build_spectral_group_identity`.
- Tests directement concernés : `tests/level1/test_results.py`, `test_serialization.py`, `test_assembly.py`, `test_matching.py` (uniquement un test contractuel démontrant que `matching.py` n'utilise jamais les nouveaux champs — `matching.py` lui-même non modifié).
- `docs/decisions/decisions.md` (D022), `docs/levels/level1/implementation-design.md`, `docs/levels/level1/validation-plan.md`.
- `docs/governance/current-task.md` (ce fichier).

## Hors périmètre

- Le runner de campagne (`scripts/level1b_campaign/`, présent dans l'arbre de travail mais **non commité par ce lot** — reste suspendu jusqu'à nouvelle autorisation explicite).
- Le manifeste de campagne, la sélection des cibles (`experiments/level1/*`).
- D020/D021 sauf référence croisée minimale dans D022.
- Toute formule scientifique, tout verdict de robustesse.
- Le niveau 0.
- `matching.py` (sauf le test contractuel ci-dessus).
- `G_occ`, `path_phase_coherence`.

## Décisions scientifiques/architecturales obligatoires (déjà gelées, jamais réinventées)

D013, D018, D019, D020, D021, et désormais **D022** (identité mono-cas des groupes spectraux — ce lot).

## Règle « un mandat = un commit »

Toute la portée de ce mandat (extension de `SpectralGroupIdentity`, constructeur dérivé, sérialisation, schéma v2, ordre d'assemblage, tests, D022, ce fichier) est livrée en un seul commit. Le répertoire `scripts/level1b_campaign/` reste présent mais non suivi/non commité par ce lot.

## Procédure en cas de compactage

Si le contexte conversationnel a été compacté ou paraît incomplet :

1. ne rien coder ;
2. ne rien commiter ;
3. ne rien pousser ;
4. relire ce fichier et les documents normatifs qu'il référence (`docs/decisions/decisions.md`, `docs/levels/level1/specification.md`, `docs/levels/level1/implementation-design.md`, `docs/levels/level1/validation-plan.md`, `docs/governance/collaboration-governance.md`) ;
5. produire une synthèse de reprise explicite (dernier commit accepté, lot actif, périmètre autorisé, ce qui reste à faire) ;
6. ne poursuivre que si toutes les contraintes ci-dessus sont retrouvées sans ambiguïté — sinon, signaler le blocage plutôt que d'inventer.

## Suite (une fois 1B-8b accepté)

Le runner mono-cas du lot 1B-8 (diagonalisation, sélection des cibles, productions mono-cas D020/raw_G/diagnostics/labels/O_ij_raw/orbites, `ResultRecord`, sérialisation, assemblage) peut reprendre, désormais en s'appuyant sur `build_spectral_group_identity` pour construire une identité spectrale sans collision. Il devra utiliser `spectral_window_group_index=enumerate(groups)` (avant tout filtrage) pour chaque groupe qu'il traite.
