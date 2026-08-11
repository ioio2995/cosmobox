# Pré-enregistrement scientifique — Level 2C : comparaison des profils spectraux

Statut : **pré-enregistrement scientifique, avant implémentation et avant inspection des observables plein spectre**

Branche : `research/level2-energy-regime`

Ce document complète `conceptual-framing.md`, `spectral-capability-audit.md` et `spectral-regime-design.md`.

Il fixe la manière de comparer les profils spectraux entre `S=2` et `S=3` sans appariement multiplet-par-multiplet et sans introduire un seuil physique arbitraire.

## 1. Problème à résoudre

Level 2 doit déterminer si l'organisation relationnelle dépend de la position dans le spectre et si cette dépendance est compatible entre les deux troncatures principales `S=2` et `S=3`.

Le problème méthodologique est le suivant :

```text
une compatibilité inter-S ne doit pas dépendre
- d'un matching multiplet-par-multiplet ;
- d'une tolérance physique choisie arbitrairement ;
- d'un score binaire fabriqué après observation ;
- d'un ajustement de courbe ou d'un lissage adaptatif.
```

Level 2C adopte donc une stratégie différente : **la robustesse inter-S est décrite par des observables continues de concordance de profils et par des signes de contrastes pré-enregistrés ; elle n'est pas réduite à un seuil scalaire PASS/FAIL.**

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

Les définitions de ces quantités sont celles de `spectral-regime-design.md` et ne sont pas modifiées ici.

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

Cette représentation porte naturellement le poids de multiplicité et permet de comparer `S=2` à `S=3` sur le même domaine abstrait :

\[
q\in[0,1].
\]

Aucun multiplet `S=2` n'est associé à un multiplet `S=3`.

## 4. Résumés LOW / MID / HIGH

Les trois régimes secondaires restent :

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

## 6. Concordance de direction inter-S

Pour une géométrie donnée et une métrique donnée, le premier contrôle inter-S est le signe du contraste principal :

```text
sign(Delta_X_HL at S=2)
sign(Delta_X_HL at S=3)
```

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

Un contraste compatible avec zéro au niveau du contrôle numérique n'est jamais déclaré physiquement nul : il reçoit `NUMERICALLY_UNRESOLVED`.

## 7. Rôle exclusif de la tolérance numérique

La tolérance utilisée pour décider si une quantité est numériquement distinguable de zéro doit provenir exclusivement d'un contrôle de reproductibilité/erreur numérique établi avant campagne.

Elle ne constitue jamais :

```text
- un seuil de réponse physique ;
- une taille minimale d'effet ;
- un seuil de significance ;
- un critère de succès scientifique.
```

La logique est :

```text
|Delta| <= numerical_guard
    -> NUMERICALLY_UNRESOLVED

|Delta| > numerical_guard
    -> signe descriptif disponible
```

Le `numerical_guard` devra être dérivé ou justifié dans un lot technique séparé avant l'exécution normative. Il ne peut pas être choisi après observation des profils.

## 8. Concordance de forme continue

Le signe de `Delta_HL` ne suffit pas à décrire la forme du profil. Level 2C fixe donc deux diagnostics continus supplémentaires, sans seuil de décision.

### 8.1 Corrélation fonctionnelle centrée

Pour une métrique `X` évaluable sur tout `[0,1]`, on définit :

\[
\mu_S = \int_0^1 X_S(q)\,dq,
\]

puis :

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

Interprétation :

```text
C proche de +1 : formes centrées similaires
C proche de 0  : faible concordance linéaire de forme
C proche de -1 : formes centrées inversées
```

Aucune frontière numérique entre ces descriptions n'est normative.

### 8.2 Distance de profil normalisée

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

`D_X^{23}` est un descripteur continu de différence entre profils. Il n'existe aucun `D_max` normatif.

## 9. Tendance monotone intra-S

Le coefficient de Spearman préfiguré en Level 2B est conservé :

\[
\rho_S(q,X).
\]

Il est calculé sur les groupes spectraux avec poids de multiplicité pris en compte par la représentation cumulative ; l'implémentation exacte doit être définie sans réplication massive des états, mais être mathématiquement équivalente à un classement pondéré par `d_g`.

Le coefficient est descriptif :

```text
pas de p-value
pas de seuil de significance
pas de classification automatique
```

La concordance de signe de `rho_S` entre S=2 et S=3 est publiée comme information secondaire, jamais comme verdict unique.

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

Pour `A_QQ` et `M_QQ`, les analyses inter-S de forme restent secondaires jusqu'à vérification de leur couverture réelle.

## 11. Hiérarchie des conclusions autorisées

Level 2C n'utilise pas de score composite.

Pour une géométrie et une métrique primaire données, les conclusions descriptives autorisées sont structurées ainsi :

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

`C` ne signifie pas convergence `S -> infinity`. Il signifie seulement que la direction du contraste spectral est reproduite entre les deux troncatures testées.

## 12. Niveau de généralité entre géométries

Chaque géométrie reçoit d'abord son propre résultat.

Les formulations autorisées sont :

```text
GEOMETRY_SPECIFIC:
la dépendance spectrale est observée dans telle géométrie.

CROSS_GEOMETRY_RECURRENT:
la même direction de contraste est observée dans plusieurs géométries.

CROSS_GEOMETRY_COMMON:
la même direction de contraste est observée dans les trois géométries.
```

Aucun seuil `2 sur 3 = succès` n'est introduit.

Une récurrence sur deux géométries est décrite comme telle ; elle n'est pas automatiquement promue en propriété générique.

## 13. Critère scientifique principal du premier test

Le premier test Level 2 répond à la question :

> Existe-t-il une dépendance spectrale résolue de la structure relationnelle primaire (`C_TT_conn`) dont la direction se reproduit entre `S=2` et `S=3` pour au moins une réalisation microscopique ?

Cette question est évaluée séparément pour :

```text
M_TT
R_eff
```

Un résultat positif minimal est donc l'existence d'au moins une géométrie pour laquelle `M_TT` ou `R_eff` possède un contraste `HIGH-LOW` numériquement résolu et de même signe entre S=2 et S=3.

Cette condition n'est pas une preuve de géométrie émergente ; elle établit seulement une dépendance spectrale reproduite sous le contrôle de troncature disponible.

## 14. Résultats négatifs et inconclusifs

Résultat négatif autorisé :

> Aucun contraste spectral primaire résolu ne présente la même direction entre S=2 et S=3 dans les géométries testées.

Résultat inconclusif autorisé :

> Les gardes numériques, la couverture des métriques ou les invariants de calcul empêchent d'évaluer la concordance inter-S.

Un résultat négatif ou inconclusif ne déclenche aucune nouvelle métrique post-hoc dans la même campagne.

## 15. Contrôle `rho_QQ`

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

## 17. Ce que ce document gèle

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
```

## 18. Ce qui reste à résoudre avant implémentation

Un seul point méthodologique reste ouvert :

```text
NUMERICAL_GUARD_FOR_ZERO_CONTRAST
```

Il doit être établi par un contrôle strictement numérique, indépendant des amplitudes physiques de la campagne, avant toute exécution normative.

Ce guard n'aura qu'un rôle de résolution numérique autour de zéro ; il ne deviendra jamais un seuil de taille d'effet physique.

## 19. Étape suivante

La prochaine action autorisée est un audit technique/read-only visant à répondre :

> Quelle garde numérique peut être justifiée pour les contrastes agrégés Level 2 à partir de la reproductibilité du pipeline plein spectre, sans utiliser les amplitudes physiques de la future campagne ?

Aucune implémentation de campagne normative n'est encore autorisée par ce document.
