# Protocole numérique — Level 2C : garde de résolution autour de zéro

Statut : **protocole de calibration numérique, avant implémentation normative**

Branche : `research/level2-energy-regime`

Ce document complète `profile-comparison-preregistration.md`. Il ne modifie aucune définition physique de Level 2 et ne fixe encore aucune valeur numérique de garde.

## 1. Objet

Le pré-enregistrement Level 2C utilise le signe du contraste principal

\[
\Delta_X^{HL}=\bar X_{HIGH}-\bar X_{LOW}
\]

pour comparer la direction d'une dépendance spectrale entre `S=2` et `S=3`.

Une quantité calculée en arithmétique flottante ne doit cependant pas être déclarée positive ou négative si son signe peut être produit uniquement par l'erreur numérique du pipeline.

Le seul objet de ce protocole est donc de déterminer une **garde numérique de résolution autour de zéro**.

```text
NUMERICAL_GUARD_ROLE = REPRODUCIBILITY_ONLY
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
SIGNIFICANCE_THRESHOLD = NOT_APPLICABLE
```

La garde ne mesure aucune importance physique et ne transforme jamais une petite amplitude physique en « absence d'effet ».

## 2. Principe de non-contamination scientifique

La calibration peut exécuter les mêmes primitives numériques que la future campagne, mais les **valeurs physiques absolues** de `C_TT_conn`, `M_TT`, `R_eff`, `rho_QQ`, `A_QQ`, `M_QQ` et des contrastes spectraux ne doivent jamais être exposées par l'artefact public de calibration.

Seules les **différences entre deux représentations mathématiquement équivalentes du même calcul** peuvent être publiées.

```text
PUBLIC_CALIBRATION_ARTIFACT:
- numerical discrepancies only
- no raw physical observable
- no regime mean
- no physical contrast value
- no spectral profile value
```

Ainsi, la conception scientifique reste aveugle aux amplitudes de la future campagne.

## 3. Pourquoi une simple répétition identique ne suffit pas

Le solveur dense peut être déterministe sur une machine donnée. Deux appels identiques peuvent donc reproduire exactement les mêmes bits sans tester la sensibilité la plus pertinente : dans un sous-espace spectral dégénéré, les vecteurs propres individuels ne constituent pas une base physique unique.

Level 2 utilise des multiplets complets et la moyenne canonique

\[
\rho_M=\Pi_M/d_M,
\]

qui doit être invariante sous changement de base interne du multiplet.

La calibration doit donc tester explicitement cette invariance numérique.

## 4. Transformation de calibration

Pour chaque multiplet complet `g` de dimension `d_g`, si la matrice des vecteurs propres est

\[
\Psi_g,
\]

construire une seconde représentation

\[
\Psi'_g=\Psi_g U_g,
\]

où `U_g` est une matrice unitaire déterministe de dimension `d_g`, dérivée d'une graine de calibration fixée avant exécution.

Cette transformation :

```text
- ne change pas le sous-espace spectral ;
- ne change pas le projecteur Pi_M ;
- ne change pas la physique du multiplet ;
- change uniquement sa base interne.
```

Pour un singulet (`d_g=1`), appliquer une phase complexe unitaire déterministe non triviale afin de tester également l'invariance de phase.

Aucun bruit n'est ajouté au Hamiltonien et aucune énergie n'est déplacée.

## 5. Deux chemins mathématiquement équivalents

Pour chaque cas de calibration :

```text
PATH_A:
full spectrum
-> original complete-multiplet eigenvectors
-> Level 2 candidate observables/metrics
-> regime summaries
-> Delta_HL

PATH_B:
exact same full spectrum
-> deterministic unitary rotation inside every complete multiplet
-> same Level 2 candidate observables/metrics
-> same regime summaries
-> Delta_HL
```

Toutes les règles physiques et statistiques sont identiques entre `A` et `B`.

La seule différence autorisée est la représentation numérique de la base interne des multiplets.

## 6. Quantités de calibration

Pour chaque métrique primaire `X in {M_TT, R_eff}` et chaque cas, calculer uniquement :

\[
e_X = |\Delta_{X,A}^{HL}-\Delta_{X,B}^{HL}|.
\]

L'artefact public peut également conserver, pour diagnostic purement numérique :

```text
max_abs_group_metric_difference
max_abs_matrix_entry_difference for C_TT_conn
```

mais jamais les valeurs de référence elles-mêmes.

Pour le contrôle `rho_QQ`, vérifier en plus l'identité exacte des statuts `numeric/null_reason` entre les deux chemins. Toute divergence de nullité est un **échec de calibration**, pas une erreur à convertir en nombre.

## 7. Cas de calibration

La calibration doit utiliser les six cas déjà gelés du premier test Level 2 :

```text
triangle S=2
triangle S=3
ring4 S=2
ring4 S=3
ring5 S=2
ring5 S=3
```

Cette utilisation est autorisée parce que l'artefact public est firewallé : les amplitudes physiques, profils et contrastes ne sont jamais restitués.

Le but n'est pas d'utiliser un petit holdout moins représentatif, mais de calibrer la stabilité numérique **sur exactement les dimensions, multiplicités et géométries que la campagne utilisera**, tout en maintenant l'aveuglement scientifique sur leur contenu physique.

## 8. Graines de rotation

Utiliser plusieurs rotations déterministes afin de ne pas calibrer la garde sur une seule base interne arbitraire.

```text
CALIBRATION_ROTATION_SEEDS = [0, 1, 2, 3]
```

Le chemin `A` reste la base produite par le solveur. Chaque seed produit un chemin `B_seed` indépendant.

Pour chaque métrique `X`, définir :

\[
E_X=\max_{case,seed}|\Delta_{X,A}^{HL}-\Delta_{X,B_{seed}}^{HL}|.
\]

Aucune moyenne des erreurs n'est utilisée : la calibration retient le maximum observé dans le domaine exact de la campagne.

## 9. Dérivation de la garde

La garde est spécifique à chaque métrique primaire :

```text
NUMERICAL_GUARD_M_TT
NUMERICAL_GUARD_R_EFF
```

Règle :

- si `E_X > 0`, utiliser le **plus petit multiple décimal de puissance de dix supérieur ou égal à `E_X`**, suivant la même politique de plafond de décennie déjà utilisée historiquement pour séparer reproductibilité numérique et effet physique ;
- si `E_X == 0`, utiliser `nextafter(0,+inf)` n'est pas une garde utile à l'échelle des opérations flottantes. Dans ce cas, la calibration doit retourner `ZERO_EMPIRICAL_DISCREPANCY` et la valeur finale de garde reste **PENDING** jusqu'à un audit analytique du plancher flottant des opérations concernées ; aucune valeur arbitraire n'est inventée.

Formellement, pour `E_X>0` :

\[
G_X=10^{\lceil\log_{10}E_X\rceil}.
\]

avec vérification obligatoire :

\[
G_X\ge E_X.
\]

Cette règle est un arrondi conservateur de représentation numérique, pas une taille minimale d'effet physique.

## 10. Utilisation normative future

Après calibration acceptée :

```text
abs(Delta_X_HL) <= G_X
    -> NUMERICALLY_UNRESOLVED

abs(Delta_X_HL) > G_X
    -> sign(Delta_X_HL) is numerically resolved
```

`NUMERICALLY_UNRESOLVED` signifie exclusivement :

> le signe du contraste n'est pas résolu au-delà de la garde de reproductibilité du pipeline.

Il ne signifie jamais :

```text
physical effect absent
physically negligible
statistically insignificant
H0 accepted
```

## 11. Conditions d'échec de calibration

La calibration échoue et bloque l'implémentation normative si l'un des cas suivants apparaît :

```text
- un cas plein spectre ne se reproduit plus structurellement ;
- un multiplet devient partial_subspace ;
- les rotations ne sont pas unitaires dans la tolérance numérique ;
- le sous-espace tourné ne reproduit pas le projecteur initial dans la tolérance numérique ;
- un statut/null_reason de rho_QQ change sous rotation ;
- une métrique devient non finie ;
- une métrique change de disponibilité sous rotation ;
- les artefacts publics contiennent une amplitude physique absolue.
```

Aucun de ces défauts ne peut être réparé en augmentant post-hoc la garde.

## 12. Ce qui est interdit pendant la calibration

```text
FORBIDDEN:
- modifier H ;
- modifier une tolérance de solveur ;
- perturber les énergies ;
- changer la définition des multiplets ;
- regarder les profils physiques ;
- publier M_TT, R_eff, A_QQ, M_QQ ;
- publier Delta_HL lui-même ;
- choisir une garde à partir de la taille de l'effet physique ;
- utiliser la future garde pour filtrer les données de calibration.
```

## 13. Artefact public minimal

L'artefact public doit contenir uniquement :

```text
repository_commit
python/numpy/scipy environment fingerprint
BLAS/LAPACK fingerprint
case identities
rotation seeds
per-case structural status
per-metric discrepancy e_X
aggregate E_X
calibration status
candidate numerical guards, if E_X > 0
```

Il ne doit contenir aucune énergie autre que l'identité structurelle déjà gelée du cas, ni aucune valeur d'observable ou de contraste physique.

## 14. Statut après ce document

```text
NUMERICAL_GUARD_PROTOCOL = FROZEN
NUMERICAL_GUARD_VALUE = PENDING_CALIBRATION
LEVEL2_IMPLEMENTATION = NOT_STARTED
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

La prochaine action autorisée est l'exécution technique de cette calibration numérique, sans modification du code scientifique de production si un script isolé suffit.
