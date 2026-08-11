# Pré-enregistrement scientifique — Level 2C : comparaison des profils spectraux

Statut : **pré-enregistrement scientifique gelé avant implémentation et avant inspection des observables plein spectre**

Branche : `research/level2-energy-regime`

Ce document complète `conceptual-framing.md`, `spectral-capability-audit.md`, `spectral-regime-design.md` et `numerical-guard-protocol.md`.

Il fixe la manière de comparer les profils spectraux entre `S=2` et `S=3` sans appariement multiplet-par-multiplet et sans introduire un seuil physique arbitraire.

## 1. Problème à résoudre

Level 2 doit déterminer si l'organisation relationnelle dépend de la position dans le spectre et si cette dépendance est compatible entre les deux troncatures principales `S=2` et `S=3`.

La compatibilité inter-S ne doit pas dépendre :

```text
- d'un matching multiplet-par-multiplet ;
- d'une tolérance physique choisie arbitrairement ;
- d'un score binaire fabriqué après observation ;
- d'un ajustement de courbe ou d'un lissage adaptatif.
```

La robustesse inter-S est donc décrite par des observables continues de concordance de profils et par des signes de contrastes pré-enregistrés ; elle n'est pas réduite à un seuil scalaire PASS/FAIL.

## 2. Données d'entrée gelées

Pour chaque géométrie `G in {triangle, ring4, ring5}` et chaque spin `S in {2,3}`, le spectre complet est utilisé.

Chaque multiplet complet `g` fournit :

```text
q_g
epsilon_g
multiplicity d_g
M_TT(g)
R_eff(g)
A_QQ(g)
M_QQ(g) lorsque disponible
```

Les définitions de ces quantités sont celles de `spectral-regime-design.md`.

Aucune autre métrique primaire ne peut être ajoutée après inspection de la campagne normative.

## 3. Représentation sans matching : fonction en q

Chaque multiplet `g` occupe un intervalle exact de population cumulative :

\[
I_g = [N_{<g}/D,\,(N_{<g}+d_g)/D].
\]

Pour une métrique scalaire `X_g`, on définit la fonction spectrale en escalier :

\[
X_S(q)=X_g \quad \text{pour } q\in I_g.
\]

Cette représentation porte naturellement le poids de multiplicité et permet de comparer `S=2` à `S=3` sur le même domaine abstrait `q in [0,1]`.

Aucun multiplet `S=2` n'est associé à un multiplet `S=3`.

## 4. Résumés LOW / MID / HIGH

```text
LOW  = q in [0, 1/3)
MID  = q in [1/3, 2/3)
HIGH = q in [2/3, 1]
```

Pour une métrique `X`, les moyennes de régime sont les intégrales exactes de la fonction en escalier :

\[
\bar X_R = \frac{1}{|R|}\int_R X_S(q)\,dq.
\]

Cette écriture est équivalente à la pondération par le nombre exact d'états du multiplet intersectant le régime.

## 5. Contrastes pré-enregistrés

Pour chaque métrique et chaque couple `(geometry,S)`, trois contrastes sont publiés :

\[
\Delta^{HL}_X = \bar X_{HIGH}-\bar X_{LOW},
\]

\[
\Delta^{ML}_X = \bar X_{MID}-\bar X_{LOW},
\]

\[
\Delta^{HM}_X = \bar X_{HIGH}-\bar X_{MID}.
\]

Le contraste principal est :

```text
PRIMARY_REGIME_CONTRAST = HIGH_MINUS_LOW
```

Les deux autres sont descriptifs et servent à distinguer une évolution monotone d'une structure intermédiaire.

Aucun contraste n'est transformé en taille d'effet binaire.

## 6. Gardes numériques gelées

Le lot `L2-C1-NUMERICAL-ZERO-GUARD-CALIBRATION` a exécuté le protocole de `numerical-guard-protocol.md` sans exposer de valeur physique absolue.

Résultat :

```text
NUMERICAL_GUARD_M_TT  = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15

NUMERICAL_GUARD_ROLE = REPRODUCIBILITY_ONLY
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
SIGNIFICANCE_THRESHOLD = NOT_APPLICABLE
```

Ces valeurs ne peuvent pas être modifiées après observation de la campagne normative.

## 7. Concordance de direction inter-S

Pour une géométrie et une métrique données, le premier contrôle inter-S est le signe du contraste principal.

Pour `M_TT` :

```text
abs(Delta_HL) <= 1e-16
    -> NUMERICALLY_UNRESOLVED
```

Pour `R_eff` :

```text
abs(Delta_HL) <= 1e-15
    -> NUMERICALLY_UNRESOLVED
```

Au-delà de la garde correspondante, le signe mathématique du contraste est disponible.

Les catégories descriptives autorisées sont :

```text
SAME_POSITIVE_DIRECTION
SAME_NEGATIVE_DIRECTION
OPPOSITE_DIRECTION
NUMERICALLY_UNRESOLVED
NOT_EVALUABLE
```

`SAME_*_DIRECTION` exige seulement que les deux contrastes soient numériquement résolus et aient le même signe mathématique.

Aucune magnitude minimale physique n'est imposée.

## 8. Concordance de forme continue

Pour une métrique `X` évaluable sur tout `[0,1]`, on définit :

\[
\mu_S = \int_0^1 X_S(q)\,dq,
\]

puis la corrélation fonctionnelle centrée :

\[
C_X^{23} =
\frac{
\int_0^1 (X_2(q)-\mu_2)(X_3(q)-\mu_3)\,dq
}{
\sqrt{\int_0^1 (X_2(q)-\mu_2)^2 dq}
\sqrt{\int_0^1 (X_3(q)-\mu_3)^2 dq}
}.
\]

Si l'une des deux fonctions est constante au niveau numérique, `C_X^{23}` est `NOT_AVAILABLE` avec une raison explicite.

On définit également :

\[
D_X^{23}=
\frac{
\sqrt{\int_0^1 (X_2(q)-X_3(q))^2 dq}
}{
\sqrt{\frac12\left[
\int_0^1 (X_2(q)-\mu_2)^2 dq+
\int_0^1 (X_3(q)-\mu_3)^2 dq
\right]}
}.
\]

Si le dénominateur est nul au niveau numérique, `D_X^{23}` est `NOT_AVAILABLE`.

`C_X^{23}` et `D_X^{23}` sont des descripteurs continus ; aucun seuil de décision n'est associé à leurs valeurs.

## 9. Tendance monotone intra-S

Le coefficient de Spearman descriptif :

\[
\rho_S(q,X)
\]

est conservé.

Il doit être calculé avec pondération de multiplicité mathématiquement équivalente à la population cumulative, sans nécessité de réplication massive explicite des états.

```text
pas de p-value
pas de seuil de significance
pas de classification automatique
```

La concordance de signe de `rho_S` entre `S=2` et `S=3` est secondaire et n'est jamais un verdict unique.

## 10. Métriques partiellement disponibles

`M_TT` est attendu évaluable pour tous les groupes complets.

`R_eff` peut être `NOT_AVAILABLE` pour une matrice `C_TT_conn` numériquement nulle.

`M_QQ` peut être `NOT_AVAILABLE` lorsqu'aucune paire `rho_QQ` n'est numérique.

Pour toute métrique partielle :

```text
- aucune imputation ;
- publication de la fraction de poids spectral évaluable ;
- contrastes calculés seulement si chaque régime possède une couverture évaluable ;
- C_X^23 et D_X^23 calculés seulement sur une règle de domaine commun pré-enregistrée.
```

Pour le premier test, `C_X^23` et `D_X^23` sont normatifs uniquement pour `M_TT` et, si disponible partout, `R_eff`.

Pour `A_QQ` et `M_QQ`, les analyses inter-S de forme restent secondaires.

## 11. Hiérarchie des conclusions autorisées

Pour une géométrie et une métrique primaire données :

```text
A. NO_RESOLVED_SPECTRAL_CONTRAST
   Delta_HL numériquement non résolu pour S=2 et/ou S=3.

B. OPPOSITE_INTER_S_DIRECTION
   Delta_HL résolu mais de signes opposés entre S=2 et S=3.

C. SAME_INTER_S_DIRECTION
   Delta_HL résolu et de même signe entre S=2 et S=3.
   C_X^23 et D_X^23 sont alors publiés pour qualifier la forme,
   sans seuil supplémentaire.

D. NOT_EVALUABLE
   couverture ou invariant numérique insuffisant.
```

`SAME_INTER_S_DIRECTION` ne signifie pas convergence `S -> infinity`. Il signifie seulement que la direction du contraste spectral est reproduite entre les deux troncatures testées.

## 12. Niveau de généralité entre géométries

Chaque géométrie reçoit d'abord son propre résultat.

Les formulations autorisées sont :

```text
GEOMETRY_SPECIFIC
CROSS_GEOMETRY_RECURRENT
CROSS_GEOMETRY_COMMON
```

Aucun seuil `2 sur 3 = succès` n'est introduit.

## 13. Critère scientifique principal du premier test

Question :

> Existe-t-il une dépendance spectrale résolue de la structure relationnelle primaire (`C_TT_conn`) dont la direction se reproduit entre `S=2` et `S=3` pour au moins une réalisation microscopique ?

Cette question est évaluée séparément pour :

```text
M_TT
R_eff
```

Un résultat positif minimal est l'existence d'au moins une géométrie pour laquelle `M_TT` ou `R_eff` possède un contraste `HIGH-LOW` numériquement résolu et de même signe entre `S=2` et `S=3`.

Cette condition n'est pas une preuve de géométrie émergente ; elle établit seulement une dépendance spectrale reproduite sous le contrôle de troncature disponible.

## 14. Résultats négatifs et inconclusifs

Résultat négatif autorisé :

> Aucun contraste spectral primaire résolu ne présente la même direction entre S=2 et S=3 dans les géométries testées.

Résultat inconclusif autorisé :

> Les gardes numériques, la couverture des métriques ou les invariants de calcul empêchent d'évaluer la concordance inter-S.

Un résultat négatif ou inconclusif ne déclenche aucune nouvelle métrique post-hoc dans la même campagne.

## 15. Contrôle rho_QQ

`rho_QQ` ne peut pas sauver un résultat primaire négatif.

Son rôle est uniquement de qualifier l'interprétation :

```text
- évolution conjointe du canal charge et du canal saveur ;
- évolution principalement visible dans C_TT_conn ;
- disponibilité structurelle de rho_QQ elle-même dépendante du spectre.
```

Aucune conclusion Level 2 ne repose exclusivement sur `rho_QQ`.

## 16. Géométrie et gravité restent fermées

Même si `M_TT` ou `R_eff` présentent une dépendance spectrale reproduite entre S=2 et S=3 :

```text
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

Aucun fit métrique, aucune dimension effective et aucune courbure ne sont ouverts dans la première campagne Level 2.

## 17. Contrat scientifique gelé

```text
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
PRIMARY_CONTRAST = HIGH_MINUS_LOW
REGIMES = equal thirds of cumulative state population
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
INTER_S_BRANCH_MATCHING = FORBIDDEN
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
INTER_S_SHAPE_DESCRIPTORS = C_X_23, D_X_23
PRIMARY_POSITIVE_PATTERN = SAME_INTER_S_DIRECTION on M_TT and/or R_eff
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
```

## 18. Statut

```text
L2_C_PREREGISTRATION = FROZEN
NUMERICAL_GUARD_CALIBRATION = PASS
OPEN_METHODOLOGICAL_ITEM = NONE
LEVEL2_IMPLEMENTATION = NOT_STARTED
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

L'étape suivante autorisée est l'implémentation minimale du contrat gelé. L'exécution normative reste interdite jusqu'à audit et acceptation explicite de cette implémentation.