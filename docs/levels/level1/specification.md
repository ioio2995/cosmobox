# Spécification scientifique et d’implémentation — niveau 1B

Statut : **gelée — conception conceptuelle et implémentation autorisées par lots**

Branche : `research/level1-correlators`

Documents normatifs associés :

- `docs/physical-model.md` — modèle physique général ;
- `docs/decisions.md` — D012 et D013 ;
- `experiments/LEVEL1B-preregistered-manifest.md` — campagne pré-enregistrée ;
- `schemas/level1-correlators-v1.schema.json` — contrat de sérialisation ;
- `docs/level1-validation-plan.md` — critères d’acceptation.

En cas de divergence, D013 et le manifeste fixent les valeurs gelées de campagne. La présente spécification fixe les définitions scientifiques et techniques.

---

## 1. Question scientifique

Le niveau 1B mesure des corrélations relationnelles invariantes de jauge entre degrés de liberté de matière sur l’espace de Hilbert physique exact du niveau 0.

Question principale :

> Les corrélations invariantes de jauge de matière, de charge et de saveur présentent-elles une organisation reproductible entre états, orbites du groupe de symétrie du Hamiltonien et troncatures finies des liens ?

Le niveau 1B ne définit ni distance effective, ni métrique, ni courbure, ni structure causale. Toute transformation de corrélations en distance relève d’une spécification future distincte.

## 2. Périmètre

Sont inclus :

- corrélateurs de matière à deux points habillés par une ligne de Wilson ;
- observables locales de densité, charge et saveur ;
- états propres non dégénérés et multiplets complets ;
- chemins minimaux orientés ;
- covariance sous symétries du Hamiltonien ;
- comparaison entre troncatures S ;
- production de données brutes et normalisées.

Sont exclus :

- secteur de jauge pur, notamment <E>, <E²> et <W_p> ;
- corrélations mixtes matière–jauge ;
- chemins arbitraires non minimaux ;
- construction d’une distance ;
- extrapolation thermodynamique ou continue ;
- revendication de géométrie ou de gravité émergente.

## 3. Conventions héritées du niveau 0

Le niveau 1B réutilise sans modification :

- la base physique exacte et la loi de Gauss ;
- l’ordre de Jordan–Wigner ;
- l’orientation des liens ;
- les opérateurs de création et d’annihilation ;
- les conventions de charge externe ;
- le groupement spectral et le statut `lower_bound_only` ;
- les générateurs de saveur SU(2) et le Casimir T² ;
- les opérateurs validés de translation et de réflexion.

Le transporteur est déjà normalisé au niveau 0 :

U_e = S_e^+ / sqrt(S(S+1)).

La convention du niveau 1B est donc :

```text
mathcal_U_e = U_e
nu_S = 1
```

Aucune normalisation supplémentaire du lien n’est autorisée.

## 4. États et multiplets

Pour un état propre normalisé |psi> :

< O > = <psi|O|psi>.

Pour un groupe spectral complet M de dimension d, la prescription canonique est :

rho_M = Pi_M / d,

avec Pi_M = Psi Psi†.

Les corrélations connectées sont calculées à partir du même état mixte rho_M. Cette prescription est la seule prescription canonique pour un multiplet complet et doit être invariante sous toute rotation unitaire interne Psi -> Psi V.

Pour un groupe `lower_bound_only=true` :

- aucune moyenne de multiplet n’est définie ;
- une compression exploratoire peut être sérialisée comme `partial_subspace` ;
- aucun verdict scientifique définitif n’est autorisé.

## 5. Observables locales

Avec deux saveurs :

```text
n_i = sum_alpha c†_{i,alpha} c_{i,alpha}
Q_i = n_i - 1
```

Le corrélateur connecté de charge est :

C_QQ(i,j) = <Q_i Q_j> - <Q_i><Q_j>.

Le coefficient normalisé est :

rho_QQ(i,j) = C_QQ(i,j) / sqrt(C_QQ(i,i) C_QQ(j,j)).

Il est défini uniquement si le dénominateur dépasse `normalization_floor`.

Les générateurs locaux de saveur sont :

T_i^a = 1/2 sum_{alpha,beta} c†_{i,alpha} sigma^a_{alpha,beta} c_{i,beta}.

Les deux corrélateurs suivants sont obligatoires :

```text
C_TT_raw(i,j)  = sum_a <T_i^a T_j^a>
C_TT_conn(i,j) = sum_a [<T_i^a T_j^a> - <T_i^a><T_j^a>]
```

### Théorème du secteur de saveur maximale

Pour n fermions et n_d doubles occupations :

T <= (n - 2 n_d) / 2.

Donc T = n/2 implique n_d = 0. À demi-remplissage, cela implique aussi l’absence de trous, donc n_i = 1 et Q_i = 0 pour tout site.

Dans tout multiplet complet à demi-remplissage de saveur maximale :

```text
C_QQ(i,j) = 0
rho_QQ = null
null_reason = zero_local_charge_variance
```

La parité de n contraint T : n pair implique T entier ; n impair implique T demi-entier. En particulier, T=3/2 est structurellement impossible pour `ring4`.

## 6. Chemins et transporteurs

Un chemin orienté est une suite déterministe d’arêtes parcourues dans leur sens stocké ou en sens inverse.

Pour une arête stockée :

```text
sens direct  -> U_e
sens inverse -> U_e†
```

Le chemin nul i=j est autorisé et son transporteur vaut l’identité.

Les chemins minimaux sont déterminés exclusivement par la distance combinatoire du graphe. Cette distance sert à sélectionner les chemins ; elle n’est pas une observable émergente.

Dans la campagne principale, les seuls couples possédant plusieurs chemins minimaux sont les paires antipodales de `ring4`.

## 7. Opérateur de matière habillé

Pour un chemin P allant de i vers j :

O_ij^{alpha,beta}[P] = c†_{i,alpha} W_P c_{j,beta}.

Le produit W_P est le produit ordonné des transporteurs élémentaires du chemin.

### Invariance de jauge

Le transporteur le long du chemin produit, par télescopage, une variation de divergence +1 au départ, -1 à l’arrivée et 0 aux nœuds intermédiaires. Les variations de charge introduites par c†_i et c_j compensent exactement ces variations de flux.

Ainsi :

```text
[G_k, O_ij^{alpha,beta}[P]] = 0
```

pour tout nœud k. Cette identité est indépendante des saveurs alpha et beta.

Le corrélateur habillé est :

G_ij^{alpha,beta}[P] = Tr(rho O_ij^{alpha,beta}[P]).

La matrice 2x2 complète en saveur est toujours conservée.

## 8. Invariants de saveur

Les invariants sérialisés sont :

```text
flavor_singlet = Tr_f(G)
flavor_frobenius_squared = Tr_f(G†G)
flavor_singular_values = [sigma_1, sigma_2], sigma_1 >= sigma_2 >= 0
```

Le rapport `flavor_singular_value_ratio = sigma_2 / sigma_1` est défini uniquement si sigma_1 dépasse le plancher de normalisation.

## 9. Normalisations

Trois niveaux sont conservés séparément :

```text
raw_G      : corrélateur complexe brut
G_occ      : normalisation par les occupations locales
gamma_O    : normalisation par l’amplitude de l’opérateur
```

`gamma_O` est l’observable primaire du verdict inter-S. `G_occ` est secondaire.

`gamma_O` élimine une renormalisation multiplicative globale, mais ne supprime pas nécessairement les effets de saturation m=±S ni les dépendances à l’état de flux.

Formule exacte (D018), pour une observable scalaire réelle ou complexe `O` évaluée aux deux plus grandes valeurs disponibles de S :

```text
difference = |O_high - O_low|
amplitude  = max(|O_high|, |O_low|)

si amplitude <= NORMALIZATION_FLOOR (1e-12) :
    gamma_O = null, null_reason = "normalization_denominator_below_floor"
sinon :
    gamma_O = difference / amplitude
```

Le plancher décide que la normalisation n’est pas physiquement interprétable ; il ne remplace jamais le dénominateur pour fabriquer une valeur artificielle. `gamma_O` est symétrique entre les deux valeurs de S, sans dimension, invariant sous une renormalisation multiplicative commune non nulle, borné par 2 hors plancher.

La construction physique de `G_occ` reste hors périmètre du niveau 1B-6 : une valeur `G_occ` déjà calculée reçoit la même formule `gamma_O`/verdict que tout autre scalaire de la liste fermée, sans que son propre calcul soit spécifié ici.

Aucune transformation logarithmique en distance n’est autorisée.

## 10. Diagnostics dans un sous-espace spectral

Pour O_rest = Psi† O Psi :

Opérateur hermitien :

- trace normalisée ;
- valeurs propres ;
- minimum, maximum et étendue.

Opérateur non hermitien :

- trace normalisée ;
- valeurs singulières ;
- norme de Frobenius.

Sont explicitement exclus au niveau 1B :

```text
Schur decomposition
complex spectrum of non-normal matrices
non-Hermitian eigenvectors
```

Ces objets ne sont pas sérialisés.

## 11. Covariance et agrégation par orbite

Pour une symétrie A du Hamiltonien :

U_A O_ij[P] U_A† = O_{A(i)A(j)}[A(P)].

Les résultats primaires restent les valeurs par paire ordonnée et par chemin individuel.

Pour une orbite O d’éléments comparables x, on sérialise :

```text
orbit_mean = (1/|O|) sum_{x in O} x
orbit_max_pairwise_spread = max_{x,y in O} |x-y|
orbit_covariance_defect = max_{x in O} |x-orbit_mean|
```

L’agrégat n’est produit qu’après validation de covariance.

Sont interdites les moyennes entre :

- orbites distinctes ;
- chemins de longueurs différentes ;
- groupes spectraux différents ;
- définitions ou normalisations d’observables différentes.

Au point symétrique et pour un état invariant, les dispersions intra-orbite sont des défauts numériques, non des fluctuations physiques ni des barres d’erreur.

Les orbites sont calculées avec le groupe de symétrie du Hamiltonien, pas seulement celui du graphe nu.

## 12. Appariement entre valeurs de S

Les groupes spectraux ne sont jamais appariés par le seul rang énergétique.

L’appariement utilise :

- géométrie et paramètres (Hamiltonien identique à l’exception de S) ;
- groupe complet ;
- T ;
- translation ;
- réflexion lorsqu’elle est définie ;
- multiplicité.

Le qualificatif « lorsqu’elle est définie » (D018) s’applique à chaque générateur individuellement, translation et réflexion également : un générateur qui n’appartient pas au sous-groupe de symétrie du Hamiltonien effectif à ce point (par exemple la translation sous `j_break`, cf. V07) est marqué `not_applicable`, jamais remplacé par une valeur numérique arbitraire. Trois états sont distingués pour chaque label de symétrie — `numeric`, `not_applicable`, `unavailable` (calcul invalide) — jamais confondus dans un simple `None`.

**Label T** (D018) : `c_T = Tr(rho · T²)` ; T résout `T(T+1) ≈ c_T`, stocké sous forme exacte `twice_T` (`T = twice_T / 2`), normatif seulement si `|c_T - T(T+1)| <= 1e-8`.

**Labels de translation/réflexion** (D018) : caractère restreint `chi_A = Tr(Psi† U_A Psi)` sur le multiplet complet, pour chaque générateur A appartenant réellement au sous-groupe de symétrie du Hamiltonien (jamais supposé depuis le seul graphe nu). Accepté comme label normatif seulement après validation de la stabilité du sous-espace sous U_A et de l’unitarité de l’opérateur restreint (tolérance 1e-8 chacune). `chi_A` est invariant sous Psi -> Psi V. Deux caractères correspondent si `|chi_A^(1) - chi_A^(2)| <= 1e-8 * max(1, |chi_A^(1)|, |chi_A^(2)|)`.

L’appariement inter-S exige un Hamiltonien identique à l’exception de S : le point de référence J_i=1 s’apparie uniquement avec lui-même, un cas `j_break` uniquement avec exactement le même cas `j_break`. Comparer la référence à `j_break`, ou deux perturbations différentes, est interdit. Une multiplicité différente interdit toujours `exact_label_match`, même si T ou un caractère coïncident par ailleurs.

Les statuts autorisés sont notamment :

```text
exact_label_match
ambiguous_cross_truncation_match
target_group_not_in_window
structurally_not_applicable
```

Aucun verdict n’est produit pour un appariement ambigu ou un groupe tronqué. Un groupe `partial_subspace` ne produit jamais d’`exact_label_match` normatif.

## 13. Robustesse sous troncature

La liste des observables recevant un verdict binaire est fermée.

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

`C_TT_conn` est inclus car il ne dépend pas du transporteur de lien.

Ne reçoivent aucun verdict automatique :

```text
raw_G
C_QQ
C_TT_raw
path_spread
path_mean
path_mean_abs
path_rms
flavor_frobenius_squared
individual_singular_values
```

Pour une observable approuvée x, on compare les deux plus grandes valeurs de S disponibles (même formule que `gamma_O`, D018) :

```text
D_S = |x_high - x_low|
robuste si D_S <= max(0.05, 0.15 * max(|x_high|, |x_low|))
non_robuste sinon
```

À la frontière exacte, le verdict est `robuste`. `gamma_O` (continu) et le verdict binaire ne sont pas redondants et sont tous deux conservés.

La différence réelle est toujours stockée. Aucun verdict n’est produit sur une phase isolée lorsque l’amplitude associée est sous le plancher numérique.

Pour un groupe `partial_subspace`, une différence ou un `gamma_O` exploratoire peut être calculé si les deux valeurs existent, mais aucun verdict `robuste`/`non_robuste` n’est produit : `verdict = indeterminate`, `null_reason = "truncated_spectral_group"` — raison distincte de `"ambiguous_cross_truncation_match"` (qui décrit l’échec de l’appariement lui-même), les deux ne sont jamais fusionnées.

## 14. Campagne gelée

Les fenêtres spectrales sont :

```text
triangle = 16
ring4 = 20
ring5 = 24
```

Les dimensions physiques de référence pour S=1,2,3 sont :

```text
triangle : 48 / 88 / 128
ring4    : 152 / 292 / 432
ring5    : 496 / 1000 / 1504
```

`ring5`, S=3, est admis.

Groupes ciblés :

1. groupe fondamental complet ;
2. premier groupe excité complet avec appariement exact ;
3. groupe complet de saveur maximale T=n/2 ;
4. sur les géométries impaires, plus bas groupe complet T=3/2 lorsqu’il est distinct du groupe maximal.

Pour `ring4`, T=3/2 est `structurally_not_applicable` et la cible maximale est T=2.

Le point de référence utilise J_i=1. Le contrôle `j_break` utilise J_0=1.5 et J_i=1 ailleurs, sur `triangle` et `ring5` à S=2, avec fenêtres respectives 16 et 24.

Le désordre gaussien reste autorisé par le modèle général mais est hors campagne Level 1B.

`disk7` est exclu de la campagne principale et ne peut être ajouté qu’après comptage et garde-fous pré-enregistrés.

## 15. Sorties et sérialisation

La campagne 1B finale sérialise chaque résultat contre `schemas/level1/correlators-v2.schema.json` (D019) : structure racine `identity`/`provenance`/`record_kind`/`observable_kind`/`payload`, stricte (`additionalProperties: false` partout, y compris les objets imbriqués), sans champ `value` polymorphe unique. `schemas/level1/correlators-v1.schema.json` est conservé comme contrat historique, non utilisé par la campagne finale.

Chaque résultat enregistre au minimum :

- commit du dépôt et empreinte du manifeste ;
- géométrie, S, nombre de saveurs et paramètres ;
- convention du transporteur et nu_S ;
- fenêtre spectrale ;
- pilote de diagonalisation et solveur ;
- graines scientifique, solveur et rotation de validation ;
- identité et statut du groupe spectral ;
- identité de la paire, du chemin et de l’orbite ;
- valeur brute, normalisations et raisons explicites de `null`.

Les nombres complexes sont sérialisés sous la forme :

```json
{"real": 0.0, "imag": 0.0}
```

## 16. Lots d’implémentation

Ordre autorisé :

1. modèle de chemin et transporteur ;
2. opérateurs de matière, charge et saveur ;
3. diagnostics spectraux ;
4. invariants de saveur et automorphismes ;
5. outillage de campagne et sérialisation ;
6. campagne scientifique pré-enregistrée.

Le seul choix encore ouvert concerne l’organisation logicielle des utilitaires de campagne, mutualisés ou locaux. Ce choix ne peut modifier aucune définition scientifique ni aucune valeur gelée.

## 17. Critères d’acceptation

L’implémentation est acceptée uniquement si :

- tous les tests de `docs/level1-validation-plan.md` passent ;
- les sorties respectent le schéma v1 ;
- les fenêtres et seuils du manifeste sont inchangés ;
- aucun groupe tronqué ne reçoit de conclusion définitive ;
- aucun ajustement post-hoc n’est effectué ;
- les résultats individuels restent disponibles derrière toute agrégation.

## 18. Conclusions autorisées et interdites

Sont autorisées des conclusions limitées sur :

- la présence ou l’absence de corrélations invariantes de jauge ;
- leur dépendance au chemin minimal ;
- leur covariance sous les symétries exactes ;
- leur robustesse sous troncature selon les seuils gelés ;
- les différences entre groupes spectraux complets.

Sont interdites les conclusions affirmant qu’une distance, une métrique, une courbure, une causalité ou une dynamique gravitationnelle a émergé.
