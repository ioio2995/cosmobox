# Level 2 — synthèse scientifique et clôture

Statut : **campagne normative exécutée, résultat scientifique figé**

Branche : `research/level2-energy-regime`

Ce document clôt le premier test normatif Level 2 défini par :

- `conceptual-framing.md` ;
- `spectral-capability-audit.md` ;
- `spectral-regime-design.md` ;
- `profile-comparison-preregistration.md` ;
- `numerical-guard-protocol.md`.

Il ne redéfinit aucune métrique ni aucun seuil. Il synthétise uniquement les résultats de la campagne préenregistrée `level2-energy-regime-v1`.

## 1. Provenance de la campagne

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY = ioio2995/cosmobox
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
BRANCH = research/level2-energy-regime
FROZEN_PREREGISTRATION_COMMIT = 2d4c859db7939da51ee7d919889a18f4c7e229ed
```

La campagne contient les six cas gelés et les trois comparaisons inter-S attendues.

```text
triangle S=2 : D=88,   groupes=22
triangle S=3 : D=128,  groupes=32
ring4    S=2 : D=292,  groupes=106
ring4    S=3 : D=432,  groupes=158
ring5    S=2 : D=1000, groupes=226
ring5    S=3 : D=1504, groupes=342
```

Pour les six cas : spectre complet, solveur dense, `window_truncated=false`, `partial_subspace_count=0`, somme des multiplicités égale à la dimension.

## 2. Question scientifique préenregistrée

Le critère principal du premier test était :

> Existe-t-il une dépendance spectrale résolue de la structure relationnelle primaire `C_TT_conn` dont la direction se reproduit entre `S=2` et `S=3` pour au moins une réalisation microscopique ?

Cette question est évaluée séparément pour `M_TT` et `R_eff` à partir du contraste principal :

```text
Delta_HL = HIGH - LOW
```

Un résultat positif minimal est l'existence d'au moins une géométrie où `M_TT` ou `R_eff` possède un `Delta_HL` numériquement résolu et de même signe pour `S=2` et `S=3`.

## 3. Résultats primaires par géométrie

### triangle

```text
M_TT:
  Delta_HL S=2 = -0.004126671615421296
  Delta_HL S=3 = -0.019478063957488134
  taxonomy = SAME_INTER_S_DIRECTION
  C_X_23 = 0.03810261500220246
  D_X_23 = 1.3878668932597007

R_eff:
  Delta_HL S=2 = 0.0019610736818521657
  Delta_HL S=3 = 0.008366750093282582
  taxonomy = SAME_INTER_S_DIRECTION
  C_X_23 = 0.06720497447792737
  D_X_23 = 1.3676673156151988
```

### ring4

```text
M_TT:
  Delta_HL S=2 = -0.007742838926974305
  Delta_HL S=3 = -0.005857982377896448
  taxonomy = SAME_INTER_S_DIRECTION
  C_X_23 = -0.04090283144144193
  D_X_23 = 1.4429225743845608

R_eff:
  Delta_HL S=2 = -0.0020882959675153634
  Delta_HL S=3 = -0.0021358495740230188
  taxonomy = SAME_INTER_S_DIRECTION
  C_X_23 = 0.11613297956586083
  D_X_23 = 1.329579810321566
```

### ring5

```text
M_TT:
  Delta_HL S=2 = -0.005818691260019174
  Delta_HL S=3 = 0.004351133007983621
  taxonomy = OPPOSITE_INTER_S_DIRECTION
  C_X_23 = 0.012987171802246213
  D_X_23 = 1.4052852928874415

R_eff:
  Delta_HL S=2 = 0.002277479585917397
  Delta_HL S=3 = -0.009134320925960226
  taxonomy = OPPOSITE_INTER_S_DIRECTION
  C_X_23 = 0.01952155882157506
  D_X_23 = 1.402480260102137
```

## 4. Verdict scientifique principal

```text
LEVEL2_PRIMARY_TEST = POSITIVE
```

Le critère positif préenregistré est satisfait : triangle et ring4 présentent une direction de contraste spectral reproduite entre `S=2` et `S=3` pour les deux métriques primaires.

La géométrie ring5 ne reproduit pas cette direction : les deux métriques primaires y changent de signe entre `S=2` et `S=3`.

Le niveau de généralité approprié est donc :

```text
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
```

Cette formulation ne constitue pas une règle post-hoc de type « 2 sur 3 = succès ». Elle indique seulement que le motif primaire positif apparaît dans plusieurs réalisations microscopiques mais pas dans toutes.

## 5. Concordance de forme inter-S

Les valeurs de `C_X_23` restent proches de zéro pour les six comparaisons primaires, tandis que `D_X_23` est compris approximativement entre `1.33` et `1.44`.

Aucun seuil de décision n'étant préenregistré pour ces descripteurs, aucune classification binaire supplémentaire n'est introduite.

Le constat descriptif autorisé est : la concordance observée pour triangle et ring4 porte sur la **direction globale du contraste LOW→HIGH**, tandis que la forme détaillée des profils spectraux reste sensible à la troncature `S`.

En particulier :

```text
SAME_INTER_S_DIRECTION != convergence S -> infinity
```

## 6. Contrôle `rho_QQ`

Les métriques de contrôle `A_QQ` et `M_QQ` restent descriptives et ne portent aucune taxonomie primaire.

Le cas triangle illustre un découplage partiel entre canal primaire et contrôle :

```text
M_QQ S=2 : Delta_HL = 0
M_QQ S=3 : Delta_HL = 0
```

alors que `M_TT` et `R_eff` présentent tous deux des contrastes primaires résolus.

Le canal charge n'est cependant pas totalement inerte : `A_QQ` varie avec le régime spectral dans plusieurs cas.

Conformément au pré-enregistrement, `rho_QQ` qualifie donc l'interprétation mais ne peut ni créer ni sauver le verdict primaire.

## 7. Interprétation autorisée

La première campagne normative Level 2 établit :

> une dépendance spectrale résolue de la structure relationnelle primaire, reproduite sous le contrôle de troncature `S=2` / `S=3` pour triangle et ring4, mais non universelle entre géométries et sans stabilité démontrée de la forme détaillée du profil spectral.

Elle n'établit pas :

```text
- une universalité inter-géométrie ;
- une convergence S -> infinity ;
- une géométrie émergente ;
- une dimension effective ;
- une courbure ;
- une dynamique gravitationnelle.
```

## 8. Statut des phases

```text
LEVEL2_NORMATIVE_CAMPAIGN = COMPLETE
LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED

PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## 9. Clôture Level 2

Le premier test scientifique Level 2 est clos sur un résultat positif mais limité : une organisation spectrale primaire récurrente est observée, avec une dépendance persistante à la géométrie microscopique et à la troncature.

Aucune nouvelle métrique, aucun nouveau seuil et aucune relance de la campagne `level2-energy-regime-v1` ne sont autorisés pour renforcer ce résultat.

Toute étape ultérieure doit être ouverte comme une nouvelle question scientifique, avec son propre cadrage et ses propres critères préenregistrés avant inspection de nouvelles données.
