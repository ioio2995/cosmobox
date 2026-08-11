# Protocole numérique — Level 2C : garde de résolution autour de zéro

Statut : **calibration numérique exécutée et valeurs gelées**

Branche : `research/level2-energy-regime`

Ce document complète `profile-comparison-preregistration.md`. Il ne modifie aucune définition physique de Level 2.

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

La calibration peut exécuter les mêmes primitives numériques que la future campagne, mais les valeurs physiques absolues de `C_TT_conn`, `M_TT`, `R_eff`, `rho_QQ`, `A_QQ`, `M_QQ` et des contrastes spectraux ne doivent jamais être exposées par l'artefact public de calibration.

Seules les différences entre deux représentations mathématiquement équivalentes du même calcul peuvent être publiées.

## 3. Transformation de calibration

Pour chaque multiplet complet `g` de dimension `d_g`, si la matrice des vecteurs propres est

\[
\Psi_g,
\]

la calibration construit

\[
\Psi'_g=\Psi_g U_g,
\]

où `U_g` est une matrice unitaire déterministe de dimension `d_g`.

Cette transformation ne change ni le sous-espace spectral, ni le projecteur `Pi_M`, ni la physique du multiplet. Elle change uniquement sa base interne.

Pour un singulet (`d_g=1`), une phase complexe unitaire déterministe non triviale est utilisée.

## 4. Deux chemins mathématiquement équivalents

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

## 5. Cas et graines de calibration

Les six cas gelés du premier test Level 2 ont été utilisés :

```text
triangle S=2
triangle S=3
ring4 S=2
ring4 S=3
ring5 S=2
ring5 S=3
```

avec :

```text
CALIBRATION_ROTATION_SEEDS = [0, 1, 2, 3]
```

Chaque rotation interne a été produite de manière déterministe à partir de `(seed, case_index, group_index)`.

## 6. Grandeurs de calibration

Pour chaque métrique primaire `X in {M_TT, R_eff}` :

\[
e_X = |\Delta_{X,A}^{HL}-\Delta_{X,B}^{HL}|,
\]

puis :

\[
E_X=\max_{case,seed} e_X.
\]

Pour `rho_QQ`, l'identité exacte des statuts numériques/nulls et des `null_reason` est un invariant catégoriel : toute divergence aurait constitué un échec de calibration.

## 7. Résultat de L2-C1

Exécution :

```text
LOT = L2-C1-NUMERICAL-ZERO-GUARD-CALIBRATION
REPOSITORY_HEAD = 9d369589a7b7f05bf231dbcbe05be8a6e857aa78
CODE_CHANGED = NO
NORMATIVE_CAMPAIGN_EXECUTED = NO
PHYSICAL_VALUES_EXPOSED = NO
CALIBRATION_CASE_COUNT = 6
ROTATION_SEEDS = 0,1,2,3
```

Contrôles :

```text
UNITARITY_CHECK = PASS
PROJECTOR_INVARIANCE = PASS
RHO_NULL_SEMANTICS = PASS
M_TT_AVAILABILITY_INVARIANT = PASS
R_EFF_AVAILABILITY_INVARIANT = PASS
```

Les six cas ont reproduit leur structure plein spectre avec uniquement des multiplets complets.

Les défauts maximaux observés sont restés au niveau de l'arithmétique flottante : défaut d'unitarité entre `8.9e-16` et `1.2e-15`, défaut de projecteur entre `3.3e-16` et `6.7e-16`.

Les écarts agrégés maximaux sont :

```text
E_M_TT   = 4.163336342344337e-17
E_R_EFF  = 4.440892098500626e-16
```

## 8. Dérivation et gel des gardes

Pour `E_X > 0`, la règle pré-enregistrée est :

\[
G_X=10^{\lceil\log_{10}E_X\rceil}.
\]

Elle donne :

```text
NUMERICAL_GUARD_M_TT  = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
```

avec, dans les deux cas :

```text
G_X >= E_X
```

Ces deux valeurs sont désormais gelées pour la première campagne normative Level 2.

## 9. Utilisation normative

```text
abs(Delta_HL_M_TT) <= 1e-16
    -> NUMERICALLY_UNRESOLVED

abs(Delta_HL_M_TT) > 1e-16
    -> sign(Delta_HL_M_TT) is numerically resolved
```

et :

```text
abs(Delta_HL_R_EFF) <= 1e-15
    -> NUMERICALLY_UNRESOLVED

abs(Delta_HL_R_EFF) > 1e-15
    -> sign(Delta_HL_R_EFF) is numerically resolved
```

`NUMERICALLY_UNRESOLVED` signifie exclusivement que le signe du contraste n'est pas résolu au-delà de la garde de reproductibilité du pipeline.

Il ne signifie jamais :

```text
physical effect absent
physically negligible
statistically insignificant
H0 accepted
```

## 10. Portée méthodologique

La calibration teste l'invariance numérique de la chaîne Level 2 sous changement de base interne des multiplets complets. Elle ne constitue pas une estimation générale de toute erreur théorique ou de toute variation inter-environnement.

Son rôle normatif est volontairement plus étroit : empêcher qu'un signe de contraste au niveau du bruit de représentation interne du pipeline soit interprété comme une direction spectrale résolue.

Aucun élargissement post-hoc de ces gardes n'est autorisé pendant la campagne normative.

## 11. Statut après calibration

```text
NUMERICAL_GUARD_PROTOCOL = CLOSED
NUMERICAL_GUARD_CALIBRATION = PASS
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15

LEVEL2_C_METHODOLOGY = COMPLETE
LEVEL2_IMPLEMENTATION = NOT_STARTED
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

Le verrou `NUMERICAL_GUARD_FOR_ZERO_CONTRAST` est levé. L'étape suivante autorisée est l'implémentation minimale du contrat scientifique Level 2, sans exécution normative avant audit du code.