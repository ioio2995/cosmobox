# Manifeste pré-enregistré — campagne Level 1B

Statut : **gelé avant exécution scientifique**

Ce document est **explicatif**. La transcription machine-readable **normative** est `experiments/level1/preregistered-manifest-v1.json`, validée contre `schemas/level1/preregistered-manifest-v1.schema.json` (Draft 2020-12). Toute divergence entre les deux bloque l'exécution ; en cas de divergence constatée, ce document doit être corrigé pour redevenir cohérent avec le JSON (jamais l'inverse).

## Identité

```text
campaign_id = level1b-reference-v1
schema_version = level1-correlators-v2
branch = research/level1-correlators
n_flavors = 2
external_charges = 0
scientific_seed = 0
```

`schemas/level1/correlators-v1.schema.json` est conservé comme contrat historique uniquement ; la campagne utilise exclusivement `level1-correlators-v2`.

Le commit exact et l’empreinte du manifeste sont injectés au moment de l’exécution. `scientific_seed` fait partie du document fingerprinté (D021) : toute variation de sa valeur change l'empreinte. Les seeds par cas (`scientific`, `solver`) sont dérivés de `scientific_seed`, du `case_id` canonique du cas, et du rôle, par SHA-256 — jamais par `hash()` Python.

## Hamiltonien de référence

```text
J_i = 1
h = 0
t = 1
g_E = 1
K = 1
```

Le désordre gaussien est hors périmètre de la campagne Level 1B.

## Contrôle de brisure `j_break`

Le contrôle est épinglé aux points suivants :

| Géométrie | S | Fenêtre |
|---|---:|---:|
| triangle | 2 | 16 |
| ring5 | 2 | 24 |

Paramètres :

```text
control_id = j_break
J_0 = 1.5
J_i = 1 pour i != 0
h = 0
t = 1
g_E = 1
K = 1
```

Les orbites sont recalculées avec le sous-groupe de symétrie du Hamiltonien brisé.

## Géométries, troncatures et fenêtres

| Géométrie | S | Dimension physique | Fenêtre spectrale |
|---|---:|---:|---:|
| triangle | 1 | 48 | 16 |
| triangle | 2 | 88 | 16 |
| triangle | 3 | 128 | 16 |
| ring4 | 1 | 152 | 20 |
| ring4 | 2 | 292 | 20 |
| ring4 | 3 | 432 | 20 |
| ring5 | 1 | 496 | 24 |
| ring5 | 2 | 1000 | 24 |
| ring5 | 3 | 1504 | 24 |

## Groupes spectraux ciblés

- groupe fondamental complet ;
- premier groupe excité complet avec `exact_label_match` ;
- groupe complet de saveur maximale T=n/2 ;
- pour les géométries impaires, plus bas groupe complet T=3/2 lorsqu’il est distinct ;
- `ring4` : T=3/2 est `structurally_not_applicable`.

## Paires

```text
pair_selection = all_ordered_distinct_pairs
```

La campagne produit une identité pour chaque paire ordonnée `(i,j)`, `i != j` — `(i,j)` et `(j,i)` sont deux éléments distincts, jamais fusionnés (une observable prouvée symétrique peut être optimisée en interne côté exécution, sans que cela retire l'identité ordonnée du plan de résultats).

## Observables mono-cas obligatoires

Calculables à partir d'un seul cas diagonalisé (`SpectralGroupState`, complet ou partiel — D020) :

- C_QQ_raw et rho_QQ ;
- C_TT_raw et C_TT_conn ;
- matrice habillée complète de saveur (G brut) ;
- singlet de saveur ;
- norme de Frobenius au carré ;
- valeurs singulières ;
- diagnostics restreints hermitien et non hermitien de l'opérateur habillé (voir « Diagnostics non hermitiens »).

## Chemins

```text
path_selection = all_minimal_paths
```

Tous les chemins minimaux de chaque paire ordonnée sont énumérés ; la valeur individuelle de chaque observable sur chaque chemin est conservée. Aucune statistique agrégée de chemin (comptage, moyenne, dispersion) n'est produite tant qu'une formule n'est pas gelée.

## Observables inter-S

`gamma_O` et les verdicts de robustesse comparent deux cas diagonalisés à des `S` différents — ce ne sont jamais des grandeurs mono-cas. `G_occ` reste hors périmètre de calcul (voir « Verdicts de robustesse »). Les statistiques d'orbite (`orbit_mean`, `orbit_max_pairwise_spread`, `orbit_covariance_defect`, voir « Orbites » ci-dessous) sont, elles, mono-cas : elles agrègent sur les images d'un automorphisme au sein d'un même cas, jamais entre deux valeurs de `S`.

## Verdicts de robustesse

Primaire :

```text
gamma_O
```

Secondaires :

```text
G_occ
rho_QQ
C_TT_conn
flavor_singular_value_ratio
path_phase_coherence
```

Seuils :

```text
absolute_tolerance = 0.05
relative_tolerance = 0.15
normalization_floor = 1e-12
```

Aucune autre observable ne reçoit un verdict binaire automatique.

`G_occ` et `path_phase_coherence` restent pré-enregistrés comme secondaires ci-dessus, mais n'ont actuellement aucun producteur physique implémenté : leur pré-enregistrement et leur calculabilité actuelle sont deux faits indépendants. Aucune valeur fictive n'est produite pour l'un ou l'autre en leur absence.

## Diagnostics non hermitiens

Sont sérialisés uniquement :

```text
normalized_trace
singular_values
frobenius_norm
```

Sont exclus :

```text
schur_decomposition
complex_eigenvalues
nonhermitian_eigenvectors
```

## Orbites

Pour chaque orbite comparable, les valeurs individuelles restent primaires et les statistiques stockées sont :

```text
orbit_mean
orbit_max_pairwise_spread
orbit_covariance_defect
```

Aucune moyenne n’est autorisée entre orbites distinctes, chemins de longueurs différentes, groupes spectraux différents ou définitions d’observables différentes.

Au point symétrique, la dispersion intra-orbite est un défaut numérique, pas une dispersion physique.

## Garde-fous de ressources

Toute extension doit pré-enregistrer :

```text
maximum_physical_basis_dimension
maximum_estimated_peak_memory_bytes
maximum_expected_runtime_seconds
```

`disk7` est exclu de la campagne principale et ne peut être admis qu’après comptage et décision explicite.

## Interdictions

- aucun ajustement post-hoc des seuils ;
- aucune augmentation adaptative de fenêtre après lecture des corrélateurs ;
- aucun verdict sur un groupe tronqué ou apparié de manière ambiguë ;
- aucune transformation en distance ;
- aucune revendication de métrique, causalité ou gravité émergente.
