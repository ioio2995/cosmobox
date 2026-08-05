# Manifeste pré-enregistré — campagne Level 1B

Statut : **gelé avant exécution scientifique**

## Identité

```text
campaign_id = level1b-reference-v1
schema_version = level1-correlators-v1
branch = research/level1-correlators
n_flavors = 2
external_charges = 0
```

Le commit exact et l’empreinte du manifeste sont injectés au moment de l’exécution.

## Hamiltonien de référence

```text
J_i = 1
h = 0
t = 1
g_E = 1
K = 1
```

Contrôle de brisure :

```text
control_id = j_break
J_0 = 1.5
J_i = 1 pour i != 0
```

Le désordre gaussien est hors périmètre.

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
- groupe complet de saveur maximale \(T=n/2\) ;
- pour les géométries impaires, plus bas groupe complet \(T=3/2\) lorsqu’il est distinct ;
- `ring4`: \(T=3/2\) est `structurally_not_applicable`.

## Observables obligatoires

- \(C^{QQ}\) et \(\rho^{QQ}\) ;
- \(C^{TT,\mathrm{raw}}\) et \(C^{TT,\mathrm{conn}}\) ;
- matrice habillée complète de saveur ;
- singlet de saveur ;
- norme de Frobenius au carré ;
- valeurs singulières ;
- \(G\) brut ;
- \(G^{\mathrm{occ}}\) ;
- \(\gamma_O\) ;
- statistiques de chemins minimaux.

## Verdicts de robustesse

Primaire :

```text
gamma_O
```

Secondaires :

```text
G_occ
rho_QQ
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

## Orbites

Les orbites sont calculées à partir du groupe de symétrie du Hamiltonien. Leur dispersion au point symétrique est un défaut numérique, pas une dispersion physique.

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
