# Contrat de continuité — lot actif (anti-compactage)

Ce document est un contrat de reprise, pas une documentation scientifique. Il doit être relu intégralement (avec les documents qu'il référence) avant toute action de code, commit ou push si le contexte conversationnel a été compacté ou paraît incomplet.

## Dernier commit accepté

```text
63d3db6018cb5f2d1ccd5b4a34a5bf3d6ebd9a42
```

D022 accepté à ce commit, sur `research/level1-correlators`.

## Lot actif

1B-8 — runner mono-cas.

Du code non commité préexiste dans `scripts/level1b_campaign/` (écrit avant la suspension du lot pour D022). **Ce code n'est pas présumé conforme** : il doit être audité ligne par ligne contre le présent mandat, et toute décision non explicitement autorisée ici doit être supprimée ou corrigée avant d'être conservée.

## Objectif

Livrer l'exécution complète d'un seul `CampaignCaseSpec`, depuis la diagonalisation jusqu'à l'assemblage déterministe des documents v2 en mémoire. Ce lot ne livre pas encore : la boucle sur toute la campagne, la reprise depuis des fichiers, `run.json`, l'écriture JSONL atomique, ni les comparaisons inter-S.

## Identité spectrale (D022)

Chaque identité de groupe doit être construite exclusivement via :

```python
build_spectral_group_identity(
    group, group_state,
    spectral_window_group_index=group_index,
    twice_T=twice_T,
)
```

`group_index` provient de l'énumération de la séquence **complète et non filtrée** des groupes spectraux du cas :

```python
for group_index, group in enumerate(degeneracy_report.groups):
```

Cette énumération a lieu **avant** toute sélection des cibles, tout filtrage complet/partiel, tout filtrage par saveur, et toute suppression de groupes absents des productions. L'indice n'est jamais reconstruit depuis `target_id`, l'ordre des cibles, une liste filtrée, ou un rang après sélection. Deux cibles qui résolvent vers le même groupe physique réutilisent la même `SpectralGroupIdentity` (même objet de contenu), jamais deux identités artificiellement différentes.

## Périmètre autorisé (fichiers)

- `docs/governance/current-task.md` (ce fichier).
- Documents Level 1 directement nécessaires au runner (mise à jour minimale, sans formule scientifique nouvelle).
- `scripts/level1b_campaign/__init__.py`, `runner.py`.
- Tests du runner (`tests/scripts/level1b_campaign/`).
- Un module d'orchestration sous `experiments/level1/` uniquement si strictement nécessaire et déjà prévu par D021 (à justifier explicitement si utilisé).

## Hors périmètre strict

Ne pas modifier : `results.py`, `serialization.py`, `assembly.py`, les schémas (`schemas/level1/*`), le manifeste JSON (`experiments/level1/preregistered-manifest-v1.json`), `target_selection.py`, `local_observables.py`, `matching.py`, le niveau 0, D020, D021, D022. Toute nouvelle lacune découverte dans ces composants **bloque le runner** (signalement explicite) plutôt que d'être contournée localement.

Le runner mono-cas ne doit jamais produire : `gamma_O`, `G_occ`, `path_phase_coherence`, un `MatchOutcome` inter-S, un verdict `robuste`/`non_robuste`, une comparaison entre deux valeurs de `S`, ou une conclusion scientifique globale.

## Pipeline d'exécution (13 étapes)

1. Recevoir un `Manifest` déjà validé et un `CampaignCaseSpec` issu du plan.
2. Vérifier que le cas appartient bien à ce manifeste.
3. Construire la géométrie et le Hamiltonien du cas.
4. Exécuter le rapport Level0 avec eigenvectors et les `SpectrumOptions` du cas.
5. Construire la séquence complète des groupes spectraux (`DegeneracyReport.groups`).
6. Extraire un `SpectralGroupState` pour chaque groupe (dans le même ordre, avant tout filtrage).
7. Calculer les labels nécessaires à la sélection (`twice_T` via le Casimir de saveur).
8. Sélectionner les groupes cibles via `target_selection.py` (inchangé).
9. Produire les résultats mono-cas autorisés (voir liste ci-dessous) pour chaque groupe sélectionné.
10. Sérialiser chaque `ResultRecord` en v2.
11. Valider chaque document.
12. Appeler `assemble_execution`.
13. Retourner un résultat typé en mémoire (documents assemblés + rapport d'assemblage).

## Cibles

- `selected` et `meets_normative_requirements=True` : produire les résultats normatifs.
- `selected` mais `partial_subspace` : produire uniquement les résultats exploratoires, statut partiel propagé sans promotion.
- `not_in_window` : conserver un statut d'exécution explicite, jamais substituer un autre groupe.
- `ambiguous` : conserver un statut explicite, jamais choisir arbitrairement.
- `structurally_not_applicable` : ne produire aucune observable physique pour cette cible.

## Productions mono-cas obligatoires

Pour chaque groupe sélectionné et chaque paire ordonnée distincte (`pair_selection = all_ordered_distinct_pairs`) : `C_QQ_raw`, `rho_QQ`, `C_TT_raw`, `C_TT_conn` (D020, `*_group`), `raw_G`, `flavor_singlet`, `flavor_frobenius_squared`, `flavor_singular_values`, `flavor_singular_value_ratio`.

`rho_QQ` : `connected`/`variance_i`/`variance_j` calculés avec le **même** `group_state`, statuts des trois vérifiés identiques, puis `normalized_charge_correlator(connected.value, variance_i.value, variance_j.value)` — aucun epsilon artificiel.

Pour chaque paire ordonnée, `path_selection = all_minimal_paths` : énumérer tous les chemins minimaux, conserver un résultat individuel par chemin (jamais un chemin choisi arbitrairement), produire `O_ij_raw` et les dérivés de saveur, ne calculer aucune statistique agrégée de chemin non gelée.

Labels/diagnostics lorsque les primitives et l'applicabilité le permettent : `twice_T`, caractère de translation, caractère de réflexion (états `numeric`/`not_applicable`/`unavailable` respectés exactement, jamais un `None` nu), diagnostic restreint hermitien, diagnostic restreint non hermitien.

Orbites : uniquement via `ValidatedOrbit` (jamais une moyenne non validée) ; `orbit_mean`, `orbit_max_pairwise_spread`, `orbit_covariance_defect` ; jamais de moyenne entre orbites distinctes, chemins de longueurs différentes, groupes différents, ou définitions d'observables différentes.

## Provenance

Chaque document porte exactement : le commit du dépôt réellement utilisé, `manifest_fingerprint`, `campaign_id`, `scientific_seed` du cas, `solver_seed` réellement utilisé, `validation_rotation_seed = null` sauf validation aléatoire réellement rejouée, le statut spectral réel, le type/module producteurs réels. `target_id` n'entre jamais dans `SpectralGroupIdentity`.

## Régression obligatoire

Triangle S=2 `j_break` : groupes 0 et 1 présents, multiplicité 2 pour les deux, `twice_T=1` pour les deux, identités spectrales d'indices 0 et 1 distinctes, caractères réellement distincts lorsqu'applicables, assemblage réussi sans `AssemblyContradiction`. Les énergies décimales exactes ne sont jamais figées — seuls leur ordre et leur finitude sont vérifiés.

## Règle « un mandat = un commit »

Toute la portée de ce mandat est livrée en un seul commit. `results/` (sortie Level0 antérieure, non produite par ce lot) est explicitement exclu de tout commit.

## Procédure en cas de compactage

Si le contexte conversationnel a été compacté ou paraît incomplet :

1. ne rien coder ;
2. ne rien commiter ;
3. ne rien pousser ;
4. relire ce fichier et les documents normatifs qu'il référence (`docs/decisions/decisions.md`, `docs/levels/level1/specification.md`, `docs/levels/level1/implementation-design.md`, `docs/levels/level1/validation-plan.md`, `docs/governance/collaboration-governance.md`) ;
5. produire une synthèse de reprise explicite (dernier commit accepté, lot actif, périmètre autorisé, ce qui reste à faire) ;
6. ne poursuivre que si toutes les contraintes ci-dessus sont retrouvées sans ambiguïté — sinon, signaler le blocage plutôt que d'inventer.
