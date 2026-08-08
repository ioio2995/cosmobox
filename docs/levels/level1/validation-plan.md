# Plan de validation — niveau 1B

Ce document est normatif pour l’acceptation de l’implémentation décrite dans `docs/level1-specification.md`.

| ID | Exigence | Cas minimal | Type | Tolérance |
|---|---|---|---|---:|
| V01 | Commutation avec Gauss | triangle, chemin direct | analytique + matrice | 1e-10 |
| V02 | Arête parcourue en sens inverse | chemin contenant U† | exact | 1e-10 |
| V03 | Relation d’adjoint | P et P⁻¹ | exact | 1e-10 |
| V04 | Chemin nul | i=j | exact | 1e-10 |
| V05 | Fermeture de base | transition non nulle | invariant | exact |
| V06 | Covariance d’automorphisme | point J_i=1 | matrice | 1e-10 |
| V07 | Réduction du groupe de symétrie | `j_break`, triangle et ring5, S=2 | logique + matrice | 1e-10 |
| V08 | Invariance de base du multiplet | rotations unitaires aléatoires | numérique | 1e-8 |
| V09 | État mixte canonique | rho=Pi/d | analytique + numérique | 1e-10 |
| V10 | Groupe tronqué | `lower_bound_only=true` | contrat | exact |
| V11 | Saveur maximale | triangle T=3/2 | analytique | 1e-10 |
| V12 | Parité de T | ring4 | logique | exact |
| V13 | Normalisation du lien | S=1,2,3 | analytique | 1e-15 |
| V14 | Chemins multiples | antipodes de ring4 | structurel | exact |
| V15 | Normalisation nulle | variance de charge nulle | sérialisation | exact |
| V16 | Invariance de saveur | singlet et valeurs singulières | numérique | 1e-10 |
| V17 | Déterminisme | chemins, manifeste, empreintes | reproductibilité | exact |
| V18 | Reprise | sortie partielle atomique | intégration | exact |
| V19 | Agrégation d’orbite | moyenne, dispersion maximale et défaut de covariance | numérique | 1e-10 |
| V20 | Diagnostics non hermitiens | absence de Schur et de spectre complexe | contrat | exact |
| V21 | Corrélateurs de charge/saveur multiplet (D020) | triangle S=1, multiplet fondamental dégénéré | analytique + numérique | 1e-10 |
| V22 | Identité exacte des groupes spectraux (D022) | triangle S=2 `j_break`, groupes 0/1 collisionnant | contrat + numérique | exact |
| V23 | Somme totale de saveur (T(T+1)), self-corrélateur diagonal (1C-3a/1C-3b) | triangle/ring4 référence, triangle `j_break`, tous groupes `complete_multiplet` | analytique + numérique | 1e-8 |

## Règles

- les tolérances sont gelées avant exécution ;
- les tests analytiques ne sont pas remplacés par des tests numériques ;
- la dispersion intra-orbite au point symétrique est un défaut numérique ;
- `rho_QQ=null` avec `zero_local_charge_variance` est le résultat attendu dans le secteur de saveur maximale à demi-remplissage ;
- aucun test ne doit promouvoir un groupe tronqué en multiplet complet ;
- les fenêtres du contrôle `j_break` restent 16 pour triangle et 24 pour ring5 ;
- `gamma_O = |O_high - O_low| / max(|O_high|, |O_low|)`, `null` avec `normalization_denominator_below_floor` si le dénominateur est sous `NORMALIZATION_FLOOR` (D018) ; verdict `robuste` si `|O_high - O_low| <= max(0.05, 0.15 * max(|O_high|, |O_low|))`, frontière incluse ;
- un appariement ambigu ou un groupe `partial_subspace` ne produit jamais de verdict `robuste`/`non_robuste` (`null_reason = "truncated_spectral_group"` pour un groupe tronqué, `"ambiguous_cross_truncation_match"` pour l’appariement — jamais fusionnés) ;
- l’appariement inter-S exige un Hamiltonien identique à l’exception de S (référence avec référence, un `j_break` avec exactement le même `j_break`, jamais l’un avec l’autre) ;
- pour un `SpectralGroupState` (D020), `C_QQ_raw/conn` et `C_TT_raw/conn` de groupe utilisent exclusivement la moyenne canonique (`complete_multiplet`) ou exploratoire (`partial_subspace`) déjà gelée pour tout opérateur ; le terme connecté de saveur soustrait composante par composante, jamais après sommation globale ; un groupe `partial_subspace` ne reçoit jamais de statut promu ni de verdict normatif ; `rho_QQ` de groupe réutilise `normalized_charge_correlator` sans modification ni epsilon artificiel ;
- deux groupes spectraux d'un même cas ne sont considérés comme la même identité que si tous les champs de `SpectralGroupIdentity` coïncident exactement, y compris `spectral_window_group_index` (D022) ; `representative_energy` est une métadonnée exacte, jamais arrondie et jamais elle-même le discriminant ; ni l'un ni l'autre champ n'intervient dans l'appariement inter-S ;
- `sum_i C_TT_conn(i,i) + sum_{i!=j} C_TT_conn(i,j) = T(T+1)` (V23) n'est vérifiée que pour un groupe `complete_multiplet` dont `twice_T` est résolu — jamais pour `partial_subspace` (T n'y est pas un nombre quantique exact), jamais en divisant la somme hors-diagonale par deux (les deux ordres `(i,j)`/`(j,i)` sont sommés tels que sérialisés) ; la tolérance `1e-8` réutilise verbatim `matching.FLAVOR_LABEL_TOLERANCE`, déjà gelée pour la même comparaison à `T(T+1)` (résolution de `twice_T` depuis un Casimir) ; cette vérification est absente des artefacts Level 1B historiques (qui ne sérialisent pas la diagonale de `C_TT_conn`) sans que cela invalide rétroactivement ces artefacts.
