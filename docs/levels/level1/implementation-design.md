# Dossier de conception d’implémentation — niveau 1B

Statut : **brouillon — proposition d’implémentation soumise à validation**

Destinataire principal : **Claude Code**

Supervision : **Lionel ORCIL**

Responsabilité scientifique et conceptuelle : **ChatGPT**

Audit scientifique externe : **Claude Fable, exceptionnellement et uniquement sur demande explicite**

Ce document traduit les contrats scientifiques gelés du niveau 1B en lots d’implémentation. Il ne modifie aucune définition de :

- `docs/level1-specification.md` ;
- `docs/decisions.md`, notamment D012 et D013 ;
- `experiments/LEVEL1B-preregistered-manifest.md` ;
- `docs/level1-validation-plan.md` ;
- `schemas/level1-correlators-v1.schema.json`.

En cas de divergence, la hiérarchie définie dans `docs/documentation-governance.md` s’applique. Claude Code ne doit jamais résoudre une divergence scientifique par une décision locale dans le code.

---

## 1. Répartition des responsabilités

### 1.1 ChatGPT

ChatGPT fixe et contrôle :

- les définitions physiques ;
- les conventions d’orientation ;
- les observables ;
- les invariants ;
- les cas structurellement attendus ;
- les critères scientifiques d’acceptation ;
- l’interprétation des résultats.

ChatGPT ne prescrit pas inutilement les détails internes de programmation lorsque plusieurs solutions respectent exactement les contrats scientifiques.

### 1.2 Claude Code

Claude Code prend en charge :

- l’architecture logicielle détaillée ;
- les structures de données ;
- les signatures finales des API internes ;
- l’implémentation ;
- les tests ;
- le profilage ;
- les optimisations ;
- la documentation développeur ;
- les commits techniques.

Claude Code peut proposer une amélioration de conception, mais ne doit pas modifier silencieusement une convention scientifique gelée.

### 1.3 Supervision

Lionel ORCIL :

- valide le passage d’un lot au suivant ;
- arbitre les propositions ;
- autorise les commits, les push et les changements de périmètre ;
- décide d’un recours exceptionnel à Claude Fable.

---

## 2. Principes d’implémentation

### 2.1 Réutiliser le niveau 0

Le niveau 1B doit réutiliser les primitives validées du niveau 0 pour :

- la représentation des réseaux ;
- l’encodage des états ;
- la base physique ;
- les créations et annihilations fermioniques ;
- les opérateurs de lien ;
- l’indexation clé-vers-ligne ;
- les Hamiltoniens ;
- les groupes spectraux ;
- les générateurs de saveur ;
- les automorphismes validés.

Une primitive existante ne doit pas être recodée dans `level1` uniquement pour simplifier un appel.

### 2.2 Séparer noyau, diagnostics et campagne

Le code doit distinguer :

1. les objets mathématiques et opérateurs ;
2. les évaluations sur états ou sous-espaces ;
3. les agrégations et diagnostics ;
4. l’orchestration de campagne ;
5. la sérialisation.

Le noyau d’opérateurs ne doit dépendre ni du manifeste de campagne, ni du format JSON.

### 2.3 Résultats individuels avant agrégation

Toute agrégation doit conserver les valeurs sources :

- paire ordonnée ;
- chemin individuel ;
- saveurs ;
- groupe spectral ;
- valeur de S ;
- normalisation.

Aucune moyenne d’orbite ou de chemins ne peut remplacer les résultats élémentaires.

### 2.4 Fermeture stricte

Toute transition non nulle produite par un opérateur invariant de jauge doit conduire à une clé présente dans la base physique ciblée.

Une image non nulle absente de la base est une violation d’invariant et doit lever une exception explicite. Elle ne doit jamais être ignorée.

### 2.5 Déterminisme

À paramètres identiques, doivent être déterministes :

- l’ordre des nœuds, liens et chemins ;
- l’ordre des paires ;
- l’ordre des groupes spectraux ;
- l’ordre des observables ;
- l’ordre de sérialisation ;
- les empreintes ;
- les résultats hors opérations numériquement dégénérées explicitement contrôlées.

---

## 3. Arborescence conceptuelle proposée

Claude Code reste libre d’ajuster les noms ou de regrouper certains modules, sous réserve de conserver les frontières de responsabilité.

```text
src/cosmobox/level1/
  paths.py             # chemins orientés et chemins minimaux
  transporters.py      # application de W_P
  matter.py            # opérateurs habillés c† W c
  local_observables.py # Q_i, T_i^a et produits locaux
  restricted.py        # O_rest = Psi† O Psi et état mixte
  flavor.py            # invariants de saveur
  orbits.py            # covariance et statistiques d’orbite
  matching.py          # appariement inter-S des groupes spectraux
  robustness.py        # verdicts fermés inter-S
  records.py           # modèles de résultats internes
  serialization.py     # adaptation vers le schéma v1

scripts/
  level1b_campaign/     # orchestration, reprise et manifeste

tests/level1/
  test_paths.py
  test_transporters.py
  test_matter.py
  test_local_observables.py
  test_restricted.py
  test_flavor.py
  test_orbits.py
  test_matching.py
  test_robustness.py
  test_serialization.py
```

Cette arborescence est une proposition, pas une norme. Claude Code doit expliquer toute variation importante dans son compte rendu de conception.

---

## 4. Lot 1B-1 — chemins, transporteurs et opérateur habillé

### 4.1 Objectif

Construire et valider les fondations permettant d’appliquer :

```text
O_ij^{alpha,beta}[P] = c†_{i,alpha} W_P c_{j,beta}
```

sur une clé de la base physique exacte du niveau 0.

Ce lot ne diagonalise aucun Hamiltonien et ne lance aucune campagne scientifique.

### 4.2 Modèle conceptuel d’un pas orienté

Un pas doit identifier sans ambiguïté :

- le lien du réseau ;
- son nœud de départ effectif ;
- son nœud d’arrivée effectif ;
- le sens de parcours relativement à l’orientation stockée.

Convention gelée :

```text
sens stocké   -> U_e
sens inverse  -> U_e†
```

Un pas incohérent avec les extrémités du lien doit être rejeté à la construction.

### 4.3 Modèle conceptuel d’un chemin

Un chemin orienté doit contenir :

- le nœud source ;
- le nœud destination ;
- une suite immuable de pas ;
- sa longueur combinatoire ;
- un identifiant canonique déterministe.

Invariants :

- les pas sont contigus ;
- le premier pas part de la source ;
- le dernier arrive à la destination ;
- un chemin vide n’est valide que si source = destination ;
- l’inversion renverse l’ordre des pas et leur orientation ;
- `inverse(inverse(P)) == P`.

### 4.4 Chemins minimaux

L’algorithme doit énumérer tous les chemins minimaux simples entre deux nœuds.

Exigences :

- aucune dépendance à l’ordre d’itération non déterministe d’un dictionnaire ou ensemble ;
- tri canonique final ;
- aucune sélection arbitraire d’un chemin lorsqu’il en existe plusieurs ;
- la distance combinatoire ne sert qu’à la sélection ;
- les chemins non minimaux sont hors périmètre.

Cas obligatoires :

- `i == j` : un unique chemin vide ;
- paire adjacente : un unique chemin de longueur 1 ;
- antipodes de `ring4` : deux chemins minimaux distincts de longueur 2.

Claude Code choisit librement BFS, pré-calcul ou autre stratégie exacte adaptée aux petits graphes finis.

### 4.5 Application du transporteur

Le transporteur agit sur les flux uniquement.

Pour chaque pas, l’application utilise strictement les primitives validées de lien du niveau 0 :

```text
pas direct  -> U_e
pas inverse -> U_e†
```

Le produit doit respecter l’ordre opératoire imposé par l’action sur un ket. Claude Code doit documenter explicitement l’ordre d’application choisi et démontrer qu’il correspond à la définition mathématique de `W_P`.

Résultat attendu d’une primitive d’application :

```text
None
```

si l’amplitude est exactement nulle à cause de la troncature, sinon :

```text
(new_key, complex_amplitude)
```

Aucune renormalisation supplémentaire n’est permise :

```text
nu_S = 1
```

### 4.6 Application de l’opérateur habillé

Pour `O_ij^{alpha,beta}[P]`, l’ordre conceptuel sur un ket est :

1. annihiler la saveur `beta` au nœud `j` ;
2. appliquer le transporteur `W_P` ;
3. créer la saveur `alpha` au nœud `i`.

Les signes fermioniques proviennent exclusivement des primitives Jordan–Wigner du niveau 0.

L’opérateur doit :

- multiplier exactement toutes les amplitudes intermédiaires ;
- retourner `None` dès qu’une primitive produit une amplitude nulle ;
- ne pas modifier une clé en place ;
- vérifier la fermeture dans la base lorsqu’un index de base est fourni ;
- lever une erreur d’invariant si une image non nulle est absente.

### 4.7 Cas local `i == j`

Pour un chemin vide :

```text
W_P = I
```

L’opérateur devient :

```text
c†_{i,alpha} c_{i,beta}
```

Ce cas doit être traité par le même contrat public, sans branche physique alternative ni convention spéciale cachée.

### 4.8 Relation d’adjoint

L’adjoint doit satisfaire :

```text
(O_ij^{alpha,beta}[P])†
=
O_ji^{beta,alpha}[P^{-1}]
```

La validation doit comparer les matrices assemblées ou l’action exhaustive sur la base, et pas uniquement les métadonnées du chemin.

### 4.9 API conceptuelle minimale

Les noms sont indicatifs. Les capacités suivantes doivent exister :

```text
make_oriented_path(...)
invert_path(path)
minimal_paths(lattice, source, destination)
apply_transporter(key, path, ...)
apply_dressed_matter(key, path, alpha, beta, ...)
build_dressed_matter_matrix(basis, path, alpha, beta, ...)
```

Claude Code peut proposer une API plus cohérente avec le niveau 0. Elle doit rester explicite, typée et testable sans lancer une campagne.

### 4.10 Tests d’acceptation du lot 1B-1

Le lot est accepté uniquement après validation de :

- **V01** — commutation avec la loi de Gauss ;
- **V02** — arête parcourue en sens inverse ;
- **V03** — relation d’adjoint ;
- **V04** — chemin nul ;
- **V05** — fermeture de base.

Tests supplémentaires obligatoires :

- chemin discontinu rejeté ;
- extrémités incohérentes rejetées ;
- double inversion identique ;
- déterminisme de l’énumération ;
- deux chemins minimaux pour les antipodes de `ring4` ;
- saturation haute ou basse d’un lien donnant `None` ;
- aucune double normalisation du lien ;
- égalité entre action élémentaire et matrice sur toutes les colonnes d’un petit cas.

### 4.11 Livrables du lot 1B-1

Claude Code doit fournir :

1. les modules nécessaires ;
2. les tests unitaires ;
3. un bref document de choix d’architecture ;
4. la correspondance tests ↔ V01–V05 ;
5. la sortie complète de `pytest` ;
6. le diff exact ;
7. la liste des points ouverts, sans les résoudre par hypothèse implicite.

---

## 5. Lot 1B-2 — observables locales de charge et de saveur

### 5.1 Objectif

Implémenter :

```text
Q_i
T_i^x, T_i^y, T_i^z
Q_i Q_j
T_i^a T_j^a
```

puis les briques nécessaires à :

```text
C_QQ
rho_QQ
C_TT_raw
C_TT_conn
```

### 5.2 Contraintes

- aucune redéfinition des générateurs SU(2) du niveau 0 ;
- réutilisation des générateurs existants lorsqu’ils sont localement exploitables ;
- distinction explicite entre moment brut et connecté ;
- `rho_QQ = null` si le dénominateur est sous le plancher ;
- `null_reason = zero_local_charge_variance` dans le secteur maximal prévu ;
- aucune valeur artificielle égale à zéro à la place d’un `null` normatif.

### 5.3 Verrou d’acceptation

V11, V12 et V15 doivent être démontrés au minimum sur les cas prescrits par le plan de validation.

### 5.4 Généralisation multiplet (D020, lot 1B-8a)

`local_observables.py` ci-dessus ne définit `C_QQ`/`rho_QQ`/`C_TT_raw`/`C_TT_conn` que sur un état pur ; les fonctions correspondantes restent inchangées. Le lot 1B-8a ajoute, dans le même fichier, `charge_correlator_raw_group`, `charge_correlator_connected_group`, `flavor_correlator_raw_group`, `flavor_correlator_connected_group` et le type `GroupMoment` (`value`, `status`), qui appliquent la même prescription à un `SpectralGroupState` dégénéré : moyenne canonique (`restricted.canonical_multiplet_expectation`) pour `complete_multiplet`, moyenne exploratoire (`restricted.exploratory_partial_subspace_mean`) pour `partial_subspace`, dispatch via un helper privé `_group_expectation` sur `group_state.is_complete`. Le corrélateur connecté de saveur soustrait composante par composante, jamais après sommation globale. `rho_QQ` réutilise `normalized_charge_correlator` sans modification, alimentée par les moments de groupe. Aucun verdict, aucune raison de nullité nouvelle, aucun appariement inter-S dans cette couche.

---

## 6. Lot 1B-3 — états, multiplets et opérateurs restreints

### 6.1 Objectif

Fournir une interface uniforme pour évaluer une observable sur :

- un état propre non dégénéré ;
- un multiplet complet ;
- un sous-espace partiel explicitement non conclusif.

### 6.2 Prescription obligatoire

Pour un multiplet complet :

```text
rho = Pi / d
expectation(O) = Tr(Psi† O Psi) / d
```

Pour les corrélations connectées, tous les termes utilisent le même `rho`.

Pour `lower_bound_only=true` :

- aucun `multiplet_average` ;
- sortie éventuelle nommée `partial_subspace` ;
- aucun verdict scientifique.

### 6.3 Diagnostics

Hermitien :

- trace normalisée ;
- valeurs propres ;
- min, max et étendue.

Non hermitien :

- trace normalisée ;
- valeurs singulières ;
- norme de Frobenius.

Sont interdits :

- Schur ;
- spectre complexe d’une matrice non normale ;
- vecteurs propres non hermitiens.

### 6.4 Verrou d’acceptation

V08, V09 et V10 doivent passer avant le lot suivant.

---

## 7. Lot 1B-4 — invariants de saveur, chemins multiples et orbites

### 7.1 Invariants de saveur

À partir de la matrice complète `G` en saveur :

```text
flavor_singlet
flavor_frobenius_squared
flavor_singular_values
flavor_singular_value_ratio
```

La matrice 2x2 brute reste disponible.

### 7.2 Chemins multiples

Pour chaque chemin minimal, conserver la valeur individuelle avant tout diagnostic transversal.

Les statistiques de chemins autorisées sont celles de la spécification. Aucun moyennage entre longueurs ou couples différents.

### 7.3 Orbites

Le groupe utilisé est celui du Hamiltonien effectif avec ses paramètres, non celui du graphe nu.

Produire seulement après validation de covariance :

```text
orbit_mean
orbit_max_pairwise_spread
orbit_covariance_defect
```

Le contrôle `j_break` doit démontrer la réduction attendue du groupe.

### 7.4 Verrou d’acceptation

V06, V07, V14 et V16 doivent passer.

---

## 8. Lot 1B-5 — appariement inter-S, robustesse et sérialisation

### 8.1 Appariement

Ne jamais apparier les groupes par rang énergétique seul.

L’identité utilise les étiquettes gelées : géométrie, paramètres (Hamiltonien identique à l’exception de S), complétude, T, translation, réflexion et multiplicité. Le rang énergétique sert uniquement à rechercher les candidats et détecter une fenêtre incomplète, jamais à prouver une identité physique.

Labels de symétrie (D018) : `twice_T` (demi-entier exact, via `Tr(rho T²) ≈ T(T+1)`, résidu <= 1e-8) ; caractère restreint `chi_A = Tr(Psi† U_A Psi)` pour translation/réflexion, accepté seulement pour un générateur appartenant réellement au sous-groupe de symétrie du Hamiltonien (validé par stabilité du sous-espace + unitarité de l’opérateur restreint, tolérance 1e-8), sinon marqué `not_applicable` (jamais une valeur numérique arbitraire) ; un calcul invalide malgré un générateur applicable est marqué `unavailable`. Deux caractères correspondent si `|chi_A^(1) - chi_A^(2)| <= 1e-8 * max(1, |chi_A^(1)|, |chi_A^(2)|)`.

Statuts explicites obligatoires :

```text
exact_label_match
ambiguous_cross_truncation_match
target_group_not_in_window
structurally_not_applicable
```

Une multiplicité différente interdit toujours `exact_label_match`. Un groupe `partial_subspace` ne produit jamais d’`exact_label_match` normatif.

### 8.2 Verdicts fermés

Primaire :

```text
gamma_O
```

Formule (D018) : `difference = |O_high - O_low|`, `amplitude = max(|O_high|, |O_low|)` ; `null` avec `normalization_denominator_below_floor` si `amplitude <= NORMALIZATION_FLOOR` (1e-12), sinon `gamma_O = difference / amplitude`. Verdict secondaire : `robuste` si `difference <= max(0.05, 0.15 * amplitude)`, frontière incluse.

Pour un groupe `partial_subspace` : aucun verdict `robuste`/`non_robuste`, `verdict = indeterminate`, `null_reason = "truncated_spectral_group"` (distinct de `"ambiguous_cross_truncation_match"`, qui décrit l’appariement).

Secondaires :

```text
G_occ
rho_QQ
C_TT_conn
flavor_singular_value_ratio
path_phase_coherence
```

`G_occ` reçoit la même formule `gamma_O`/verdict une fois sa valeur fournie ; son propre calcul physique reste hors périmètre de ce lot.

Aucune autre observable ne reçoit de verdict automatique.

### 8.3 Sérialisation

Le modèle interne peut être plus strict que le JSON, mais toute sortie doit valider le schéma en vigueur.

Une raison explicite accompagne toute valeur normative `null`.

**D019 (lot 1B-7)** : `schemas/level1/correlators-v1.schema.json` est conservé comme contrat historique, non modifié ; `schemas/level1/correlators-v2.schema.json` (Draft 2020-12, strict, `additionalProperties: false` racine et objets imbriqués, `record_kind`/`observable_kind`/`payload` discriminés via `if`/`then`) est le schéma utilisé par la campagne 1B finale. Taxonomie fermée `record_kind` (8 valeurs) et `observable_kind` (16 valeurs, auditées contre le code réel des lots 1B-1 à 1B-6) — voir `src/cosmobox/level1/results.py`. Modules `results.py` (identité scientifique + modèle de résultat), `serialization.py` (conversion stricte + validation Draft 2020-12, `jsonschema>=4.18`), `assembly.py` (déduplication comptabilisée, détection de contradiction, ordre déterministe) — aucune logique scientifique nouvelle dans aucun des trois.

**D022 (lot 1B-8b)** : `(status, multiplicity, twice_T)` seul ne discrimine pas exhaustivement les groupes spectraux d'un même cas — collision réelle observée sur triangle S=2 `j_break` (deux multiplets complets distincts, même multiplicité, même `twice_T`, `AssemblyContradiction` levée à juste titre). `SpectralGroupIdentity` gagne `spectral_window_group_index` (position dans la séquence complète `DegeneracyReport.groups`, énumérée avant tout filtrage — discriminant mono-cas exact) et `representative_energy` (métadonnée descriptive exacte, jamais arrondie, jamais elle-même le discriminant). `build_spectral_group_identity(group, group_state, *, spectral_window_group_index, twice_T)` est le constructeur recommandé, avec contrôles croisés entre `SpectralLevelGroup` et `SpectralGroupState`. Ni l'un ni l'autre champ n'est un critère d'appariement inter-S (`matching.py` non modifié). `assembly._sort_key` ordonne désormais sa composante spectrale explicitement par `(spectral_window_group_index, status, multiplicity, twice_T, representative_energy)` plutôt que par l'ordre alphabétique JSON ; `assembly._identity_key` inclut les deux nouveaux champs sans modification de code (elle hashe déjà le dictionnaire `spectral_group` entier). Changement cassant assumé du schéma v2 (v1 inchangé).

### 8.4 Verrou d’acceptation

V13 et les tests contractuels du schéma doivent passer avant l’orchestration de campagne.

---

## 9. Lot 1B-6 — campagne pré-enregistrée

### 9.1 Objectif

Exécuter exactement le manifeste :

```text
experiments/level1/preregistered-manifest-v1.json
```

(`experiments/level1/preregistered-manifest.md` en est le document humain explicatif ; `experiments/LEVEL1B-preregistered-manifest.md` est un chemin supersédé, non normatif.)

Aucune extension adaptative après lecture des corrélateurs.

### 9.2 Exigences d’exploitation

- reprise sûre ;
- écritures atomiques ;
- validation d’un résultat existant avant saut ;
- empreinte du manifeste ;
- commit du dépôt ;
- journal des erreurs ;
- garde-fous de ressources ;
- absence d’écriture par défaut dans un répertoire suivi par Git.

### 9.3 Verrou d’acceptation

V17 et V18 doivent passer avant toute exécution scientifique officielle.

### 9.4 Infrastructure de planification (D021, lot 1B-8, correctif)

**Statut normatif** : `experiments/level1/preregistered-manifest-v1.json` (validé Draft 2020-12 contre `schemas/level1/preregistered-manifest-v1.schema.json`) est la transcription normative. Le Markdown est explicatif uniquement. Toute divergence bloque l'exécution.

**Empreinte** (`experiments/level1/manifest.py:compute_manifest_fingerprint`) : SHA-256 de `json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)` appliqué au document entier déjà validé — aucun champ exclu, y compris le nouveau `scientific_seed` racine (aucun champ purement opérationnel comme un répertoire de sortie ou une date n'existe dans le manifeste).

**Seed racine et dérivation** : `manifest.scientific_seed` (entier non-négatif, dans le manifeste, donc dans l'empreinte) est l'unique source du seed racine — `planning.build_campaign_plan(manifest)` ne reçoit plus de `root_seed` libre. Valeur gelée : `scientific_seed = 0`. `planning.derive_case_seed(root_seed, case_id, role)` dérive chaque seed par cas via SHA-256 (`hashlib.sha256`, jamais `hash()`).

**Modèle de cas** (`planning.CampaignCaseSpec`) : auto-vérifiant (`case_id` recalculé et comparé en `__post_init__`), porte désormais `ordered_pairs` (`planning.build_ordered_pairs(n_nodes)`, toutes les paires `(i,j)`, `i != j`, les deux ordres présents et distincts) en plus des paramètres du Hamiltonien, du secteur, des options de diagonalisation, des groupes cibles demandés et des trois seeds.

**Sélection des groupes cibles** (`target_selection.py`) : `fundamental`/`first_excited` par rang, `flavor_label` par `twice_T` (jamais par rang) avec mise en commun de tous les candidats complets ET partiels avant classement par énergie représentative — un partiel de plus basse énergie n'est jamais écarté au profit d'un complet de plus haute énergie. `TargetSelectionOutcome` porte `selected_group_status` et `meets_normative_requirements` (comparaison au `required_spectral_status` du `TargetGroupSpec` cible, jamais à une exigence d'appariement inter-S).

**Politique complet/partiel** : `complete_multiplet`/`partial_subspace` toujours propagés depuis le groupe réellement sélectionné, jamais promus. `required_spectral_status` (`complete_multiplet` pour toute catégorie sauf `structurally_not_applicable`) et `requires_inter_s_exact_match` (`true` uniquement pour `first_excited`) encodent la politique du manifeste humain sans jamais prétendre produire un `exact_label_match` — réservé à l'étape d'appariement inter-S, hors périmètre de ce module.

**Garde-fous dimensionnels** : uniquement `resource_guardrails.max_dense_dimension`/`max_sparse_dimension` (2000/200000), déjà gelés par le niveau 0 ; aucun seuil mémoire/temps inventé.

**Chemins** : `path_selection = "all_minimal_paths"` — tous les chemins minimaux de chaque paire ordonnée sont énumérés, valeur individuelle par chemin conservée ; `productions.path_statistics` reste vide (aucune statistique agrégée de chemin n'est gelée — `minimal_path_count` d'une version antérieure était une grandeur inventée, retirée). Distinct de `orbit_statistics` : les statistiques d'orbite agrègent sur les images d'un automorphisme au sein d'un même cas (mono-cas), jamais sur des chemins de longueurs différentes ni entre deux valeurs de S.

**Séparation mono-cas / inter-S** : `productions` (manifeste) distingue `single_case_observables`/`single_case_diagnostics`/`path_statistics`/`orbit_statistics` (un seul cas diagonalisé) de `inter_s_observables` (`gamma_O` primaire, verdicts de robustesse, `G_occ`/`path_phase_coherence` marqués `unproduced` faute de producteur physique) — `gamma_O` n'est jamais listé parmi les observables mono-cas. Le bloc `robustness` du manifeste porte la liste secondaire complète (`G_occ`, `rho_QQ`, `C_TT_conn`, `flavor_singular_value_ratio`, `path_phase_coherence`), exactement celle du manifeste humain.

### 9.5 Runner mono-cas (lot 1B-8)

`scripts/level1b_campaign/runner.py::run_single_case(manifest, case, *, repository_commit)` exécute un seul `CampaignCaseSpec` (diagonalisation Level0, séquence complète des groupes spectraux, sélection des cibles via `target_selection.py` inchangé, productions mono-cas D020/`raw_G`/diagnostics/labels/`O_ij_raw`/orbites, sérialisation v2, assemblage) et retourne un résultat en mémoire — aucune écriture disque, aucune boucle multi-cas, aucune comparaison inter-S. Vérifie explicitement que le cas appartient au manifeste fourni (seeds re-dérivés via `planning.derive_case_seed`, `target_groups` comparés). Chaque identité de groupe spectral est construite exclusivement via `results.build_spectral_group_identity(group, group_state, spectral_window_group_index=group_index, twice_T=twice_T)` (D022), `group_index` provenant de l'énumération de la séquence complète et non filtrée des groupes, jamais d'un rang de cible ou d'une liste filtrée. `gamma_O`, `G_occ`, `path_phase_coherence`, tout `MatchOutcome` et tout verdict de robustesse restent hors périmètre de ce runner.

### 9.6 Self-corrélateur de saveur diagonal (lot 1C-3a)

`run_single_case` produit désormais, en plus du `C_TT_conn(i,j)` hors diagonale déjà existant, un enregistrement `C_TT_conn(i,i)` par site et par groupe spectral traité — même observable binaire, cas `j=i`, jamais une nouvelle famille (`_self_flavor_correlator_record`, produit dans la même boucle `for node in lattice.nodes` que le diagnostic restreint de `C_QQ_raw`). Représentation : `observable_kind="C_TT_conn"`, `record_kind="raw_observable"`, `path=(i,i)` (jamais `(i,)`, qui reste réservé aux diagnostics à un seul site), `payload` un flottant nu identique en forme au cas hors diagonale. Réutilise exclusivement `local_observables.flavor_correlator_connected_group(generators_i, generators_i, group_state)`, déjà documentée comme acceptant `i==j` — aucune seconde formule, aucun nouveau dispatch : le statut `complete_multiplet`/`partial_subspace` du groupe est propagé par le mécanisme déjà existant, sans jamais simplifier en `<T_i^2>` pour un groupe partiel. Le contrat D021 (`all_ordered_distinct_pairs`, `case.ordered_pairs`) reste inchangé — la diagonale est une production séparée, jamais mêlée à la boucle des paires distinctes. Aucune modification de schéma (`path` accepte déjà toute longueur ≥1 sans contrainte d'unicité des éléments). Conception validée par les audits en lecture seule 1C-2a/1C-2b/1C-2c (`docs/governance/current-task.md`).

### 9.7 Validation de la somme totale de saveur (lot 1C-3b, V23)

`local_observables.validate_flavor_total_sum(status, twice_T, diagonal_values, off_diagonal_values, *, tolerance=FLAVOR_TOTAL_SUM_TOLERANCE)` consomme les valeurs `C_TT_conn` déjà produites pour un seul groupe spectral (diagonale du lot 1C-3a + hors-diagonale déjà existante, les deux ordres `(i,j)`/`(j,i)` sommés tels que sérialisés, jamais divisés par deux, jamais reconstruits depuis une moyenne d'orbite) et vérifie `sum_i C_TT_conn(i,i) + sum_{i!=j} C_TT_conn(i,j) = T(T+1)` avec `T=twice_T/2`. `FLAVOR_TOTAL_SUM_TOLERANCE` réutilise verbatim `matching.FLAVOR_LABEL_TOLERANCE` (`1e-8`, audité en 1C-3b comme la tolérance déjà gelée pour cette même comparaison à `T(T+1)`, via `compute_twice_T`) — jamais la tolérance analytique plus stricte `1e-10` (V11), qui n'a jamais été gelée pour une somme de plusieurs termes et risquerait un échec parasite. Retourne `FlavorTotalSumValidation` (`applicable`, `measured`, `expected`, `residual`, `is_valid`) — `applicable=False` (et tous les autres champs `None`) pour tout groupe `partial_subspace` ou `twice_T` non résolu, jamais un verdict approximatif ; aucune exception pour un échec scientifique normal (`is_valid=False`), les exceptions restant réservées aux incohérences structurelles de l'appel. Fonction pure, ne recalcule aucun corrélateur, n'accepte jamais `C_TT_raw`. Aucune campagne, aucun préflight, aucun nouveau `J_0`/`S` : validation post-production uniquement, exercée sur les fixtures déjà existantes (`triangle` référence/`j_break`, `ring4` référence) — aucune fixture `ring5-j_break` n'existe dans la suite de tests (coût de diagonalisation disproportionné pour un test unitaire), donc les égalités de symétrie locale `D1≈D4`/`D2≈D3` sur `ring5-j_break` restent non couvertes par un test automatisé à ce stade.

**Correctif structurel (1C-3b correctif)** : avant tout verdict applicable, la fonction exige que `diagonal_values` soit non vide (`sites = set(diagonal_values.keys())`) et que `off_diagonal_values` porte EXACTEMENT les `N(N-1)` paires ordonnées `{(i,j) : i,j ∈ sites, i≠j}` — ni plus, ni moins. Une direction manquante, une paire absente, une paire diagonale `(i,i)` glissée dans `off_diagonal_values`, ou un site étranger lèvent `ValueError` avant tout calcul de somme, empêchant qu'un corpus incomplet ne produise par coïncidence un verdict `is_valid=True`/`False`. `twice_T` est en outre validé comme un `int >= 0` réel (jamais un `bool`), et chaque valeur `C_TT_conn` fournie doit être un nombre fini (`NaN`/`Inf` rejetés). Ces incohérences sont toutes des erreurs structurelles de l'appel (`ValueError`), jamais un résultat scientifique — `is_valid=False` reste exclusivement réservé à un corpus structurellement complet dont la somme physique manque `T(T+1)` au-delà de la tolérance. Le statut `partial_subspace` continue de court-circuiter cette vérification entièrement (`applicable=False` retourné avant toute inspection de complétude).

---

## 10. Règles de revue entre lots

À la fin de chaque lot, Claude Code transmet :

```text
1. Résumé fonctionnel
2. Choix d’architecture
3. Fichiers modifiés
4. Tests ajoutés
5. Correspondance avec les validations Vxx
6. Résultat pytest
7. Écarts éventuels avec ce dossier
8. Questions scientifiques bloquantes
9. SHA du commit local ou distant, selon autorisation
```

ChatGPT vérifie :

- la conformité scientifique ;
- l’absence de convention implicite ;
- l’alignement avec les documents normatifs ;
- la suffisance des tests conceptuels.

Lionel valide le passage au lot suivant.

Claude Fable n’est sollicité que pour :

- une contradiction scientifique non résolue ;
- une modification d’une décision gelée ;
- un nouveau gel de campagne ;
- une conclusion scientifique majeure nécessitant un audit indépendant.

---

## 11. Interdictions générales pour Claude Code

Claude Code ne doit pas :

- modifier les seuils ou fenêtres ;
- ajouter une normalisation du transporteur ;
- convertir une corrélation en distance ;
- promouvoir un groupe tronqué en multiplet ;
- apparier des groupes par rang seul ;
- ajouter un verdict à une observable non listée ;
- remplacer une valeur `null` par zéro ;
- moyenner des catégories non comparables ;
- ignorer une transition hors base ;
- adapter une campagne après observation ;
- modifier un document gelé sans proposition explicite et validation de Lionel.

---

## 12. Première mission transmise à Claude Code

Claude Code doit commencer uniquement par le **lot 1B-1**.

Il doit d’abord :

1. auditer les API existantes du niveau 0 ;
2. proposer l’arborescence et les signatures finales ;
3. identifier précisément les primitives réutilisées ;
4. signaler tout conflit ou manque ;
5. implémenter les chemins, transporteurs et opérateurs habillés ;
6. livrer V01 à V05 et les tests complémentaires ;
7. ne pas commencer le lot 1B-2 sans validation explicite.

La première réponse attendue de Claude Code est un court compte rendu d’audit et un plan de fichiers. Il ne doit pas inventer de physique pour combler une ambiguïté.