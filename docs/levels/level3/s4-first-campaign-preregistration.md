# Pré-enregistrement scientifique — Level 3 : première extension `S=4`

Statut : **gelé avant toute construction d’Hamiltonien, diagonalisation ou inspection d’observable physique `S=4`**

Branche : `research/level2-energy-regime`

Ce document ouvre la première campagne scientifique Level 3 à partir de la clôture gelée de Level 2 et des préflights de capacité L3-C/L3-D ainsi que de la politique d’exécution L3-E.

Il ne modifie aucune définition physique. Il fixe à l’avance la question posée à la nouvelle troncature `S=4`, les données autorisées, les comparaisons normatives, les conclusions permises et les conclusions interdites.

## 1. Contexte scientifique

Level 2 a établi une dépendance spectrale primaire récurrente entre `S=2` et `S=3` pour `triangle` et `ring4`, tandis que `ring5` change de direction entre ces deux troncatures pour les deux métriques primaires.

Level 2 a également montré que les profils détaillés restent fortement sensibles à la troncature et a explicitement conclu :

```text
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

La nouvelle donnée scientifique de cette campagne est exclusivement `S=4`.

Les résultats `S=2` et `S=3` sont des références historiques gelées ; ils ne peuvent pas être retouchés, remplacés ou sélectionnés post-hoc pour améliorer la comparaison avec `S=4`.

## 2. Question scientifique primaire

Pour chaque géométrie et chaque métrique primaire :

> Le contraste spectral principal observé à `S=3` conserve-t-il sa direction lorsque la troncature du champ de jauge est relâchée une étape supplémentaire jusqu’à `S=4` ?

Cette question est évaluée séparément pour :

```text
M_TT
R_eff
```

Elle constitue un test de **continuité directionnelle supplémentaire sous changement de troncature**.

Elle ne constitue pas un test de convergence `S -> infinity`.

## 3. Cas normatifs

Les seules nouvelles exécutions physiques autorisées par la future campagne normative sont :

```text
triangle, S=4
ring4,    S=4
ring5,    S=4
```

Paramètres physiques gelés :

```text
n_flavors = 2
J_i = 1
h = 0
t = 1
g_E = 1
K = 1
external_charges = 0
```

Le spectre complet est obligatoire.

Aucune autre géométrie, aucun autre spin et aucune variante de paramètre ne peuvent être ajoutés à la campagne après inspection d’un résultat `S=4`.

## 4. Références historiques

Les références `S=2` et `S=3` sont celles de la campagne Level 2 gelée :

```text
CAMPAIGN_ID = level2-energy-regime-v1
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
FROZEN_PREREGISTRATION_COMMIT = 2d4c859db7939da51ee7d919889a18f4c7e229ed
```

Dimensions historiques :

```text
triangle: S2=88,   S3=128
ring4:    S2=292,  S3=432
ring5:    S2=1000, S3=1504
```

Dimensions `S=4` établies par le préflight L3-C, sans observable :

```text
triangle: 168
ring4:    572
ring5:    2008
```

Les artefacts Level 2 gelés doivent être réutilisés comme source normative des données `S=2/S=3` chaque fois qu’ils contiennent l’information nécessaire. Une recomputation de `S=2/S=3` peut servir à la non-régression logicielle, mais ne remplace pas la provenance scientifique gelée de Level 2.

## 5. Observables et métriques

Aucune nouvelle observable physique n’est introduite.

Canal primaire :

```text
C_TT_conn
```

Contrôle :

```text
rho_QQ
```

Métriques primaires :

```text
M_TT
R_eff
```

Métriques de contrôle :

```text
A_QQ
M_QQ
```

Le contrôle `rho_QQ` ne peut ni créer ni sauver un résultat primaire.

## 6. Représentation spectrale

La représentation Level 2 est conservée sans modification :

```text
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
REGIMES = equal thirds of cumulative state population
PRIMARY_CONTRAST = HIGH_MINUS_LOW
```

Pour chaque métrique `X` et chaque spin `S` :

```text
Delta_HL_X(S) = mean_HIGH(X,S) - mean_LOW(X,S)
```

Aucun matching multiplet-par-multiplet inter-S n’est autorisé.

## 7. Gardes numériques

Les gardes Level 2 restent les seules gardes numériques utilisées pour décider si le signe du contraste primaire est résolu :

```text
NUMERICAL_GUARD_M_TT  = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15

NUMERICAL_GUARD_ROLE = REPRODUCIBILITY_ONLY
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
SIGNIFICANCE_THRESHOLD = NOT_APPLICABLE
```

Aucun seuil physique nouveau n’est introduit pour `S=4`.

## 8. Test primaire `S=3 <-> S=4`

Pour chaque géométrie `G` et chaque métrique primaire `X`, on compare uniquement le signe résolu de :

```text
Delta_HL_X(S=3)
Delta_HL_X(S=4)
```

Taxonomie normative :

```text
S4_DIRECTION_PERSISTS
    Delta_HL(S3) et Delta_HL(S4) sont numériquement résolus
    et ont le même signe mathématique.

S4_DIRECTION_REVERSES
    Delta_HL(S3) et Delta_HL(S4) sont numériquement résolus
    et ont des signes opposés.

S4_CONTRAST_UNRESOLVED
    Delta_HL(S4) n’est pas résolu par la garde numérique applicable.

NOT_EVALUABLE
    invariant numérique, couverture ou disponibilité insuffisante.
```

Aucune magnitude minimale physique n’est exigée.

## 9. Lecture de la séquence `S=2,3,4`

Une fois le résultat primaire `S=3 <-> S=4` établi, la séquence historique complète est décrite sans créer de nouveau score.

Catégories autorisées :

```text
THREE_SPIN_SAME_DIRECTION
    S2, S3 et S4 sont tous résolus avec le même signe.

S3_S4_PERSIST_AFTER_S2_S3_REVERSAL
    S2 et S3 avaient des signes opposés,
    puis S3 et S4 possèdent le même signe.

SECOND_DIRECTION_REVERSAL_AT_S4
    S3 et S4 ont des signes opposés.

THREE_SPIN_DIRECTION_NOT_EVALUABLE
    au moins une étape requise n’est pas évaluable.
```

Ces catégories décrivent une séquence finie de troncatures. Aucune ne signifie convergence `S -> infinity`.

## 10. Descripteurs continus de stabilisation

La campagne publie également, pour `M_TT` et `R_eff`, des descripteurs continus pré-enregistrés destinés à mesurer l’évolution de la sensibilité à la troncature sans seuil de décision supplémentaire.

### 10.1 Variation du contraste principal

On définit :

```text
T_X_23 = abs(Delta_HL_X(S3) - Delta_HL_X(S2))
T_X_34 = abs(Delta_HL_X(S4) - Delta_HL_X(S3))
```

et, si `T_X_23 > 0` :

```text
R_DELTA_X = T_X_34 / T_X_23
```

`R_DELTA_X` est un descripteur continu.

La référence mathématique `R_DELTA_X = 1` peut être rapportée descriptivement, mais aucun voisinage de 1, aucune tolérance physique et aucune classe PASS/FAIL ne sont définis.

### 10.2 Concordance de forme

La définition mathématique des descripteurs Level 2 est conservée, mais généralisée à la paire explicite `S=3 <-> S=4` :

```text
C_X_34 = cross-profile centered correlation
D_X_34 = normalized cross-profile distance
```

avec exactement les mêmes intégrales sur les fonctions en escalier `X_S(q)` que pour `C_X_23` et `D_X_23`.

Les valeurs historiques `C_X_23` et `D_X_23` restent gelées.

Si `D_X_23` et `D_X_34` sont tous deux disponibles et `D_X_23 > 0`, publier également :

```text
R_D_X = D_X_34 / D_X_23
```

`C_X_34`, `D_X_34`, `R_DELTA_X` et `R_D_X` sont descriptifs continus.

Aucun seuil de décision n’est associé à ces valeurs dans la première campagne `S=4`.

## 11. Pourquoi aucun verdict de convergence n’est défini à `S=4`

Avec trois troncatures finies `S=2,3,4`, une diminution d’un écart entre deux étapes successives peut être compatible avec une stabilisation locale, mais ne démontre pas une limite `S -> infinity`.

La première campagne Level 3 doit donc distinguer :

```text
DIRECTIONAL_CONTINUITY = testable at S4
TRUNCATION_SENSITIVITY_EVOLUTION = descriptively measurable at S4
S_TO_INFINITY_CONVERGENCE = NOT TESTABLE FROM S2,S3,S4 ALONE
```

Aucun critère de convergence asymptotique n’est fabriqué à partir du résultat `S=4`.

## 12. Résultat primaire autorisé par géométrie et métrique

Pour chaque couple `(geometry, primary_metric)`, le résultat normatif principal est exactement l’une des catégories :

```text
S4_DIRECTION_PERSISTS
S4_DIRECTION_REVERSES
S4_CONTRAST_UNRESOLVED
NOT_EVALUABLE
```

La séquence `S=2,3,4` et les descripteurs continus sont ensuite publiés comme qualification.

Il n’existe pas de score composite.

## 13. Conclusion globale Level 3 après la première campagne

Aucun seuil du type :

```text
1 geometry out of 3
2 geometries out of 3
majority vote
```

n’est défini.

La synthèse doit décrire explicitement les trois géométries et les deux métriques primaires.

Formulations autorisées :

```text
- direction persistante jusqu’à S=4 pour telle géométrie / telle métrique ;
- nouvelle inversion à S=4 pour telle géométrie / telle métrique ;
- séquence de trois spins de même direction ;
- persistance S3->S4 après inversion S2->S3 ;
- évolution descriptive de la distance de profil et de l’amplitude du contraste entre étapes de troncature.
```

Formulation interdite après cette seule campagne :

```text
S_TO_INFINITY_CONVERGENCE = ESTABLISHED
```

Le statut reste :

```text
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

quelle que soit l’issue de `S=4`.

## 14. Contrôle `rho_QQ`

`A_QQ` et `M_QQ` sont calculés selon le même protocole spectral et publiés comme contrôles descriptifs.

Ils ne participent pas à la taxonomie primaire `S4_DIRECTION_*` et ne peuvent pas modifier un résultat primaire portant sur `M_TT` ou `R_eff`.

## 15. Interdictions post-hoc

Après la première inspection d’une observable physique `S=4`, il est interdit dans cette campagne de :

```text
- changer les régimes LOW/MID/HIGH ;
- changer q ou son poids de multiplicité ;
- changer PRIMARY_CONTRAST ;
- changer les gardes numériques ;
- ajouter une métrique primaire ;
- ajouter une géométrie ;
- ajouter S=5 parce que S=4 est ambigu ;
- relancer un cas S=4 avec une convention différente ;
- choisir un sous-ensemble spectral ;
- apparier des multiplets entre spins ;
- définir un seuil de convergence après observation ;
- créer un score composite ;
- requalifier les résultats Level 2 gelés.
```

Toute extension à `S=5` constitue une nouvelle étape pré-enregistrée.

## 16. Conditions de validité d’un cas `S=4`

Un cas n’est scientifiquement exploitable que si :

```text
full spectrum = complete
computed eigenvalues = Hilbert-space dimension
full eigenvector matrix available
window_truncated = false
partial_subspace_count = 0
sum of multiplet multiplicities = Hilbert-space dimension
all required Level0/Level1 invariants pass
```

La politique Level3 L3-E doit refuser explicitement tout eigensystème incomplet avant calcul des observables.

## 17. Capacité numérique pré-validée

Les préflights ont établi :

```text
triangle S4 D = 168
ring4    S4 D = 572
ring5    S4 D = 2008
```

et une capacité dense complète synthétique jusqu’à :

```text
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008
```

Cette limite est opérationnelle, non physique.

Elle n’autorise aucune extrapolation à une dimension supérieure sans nouveau capability preflight.

## 18. Phases fermées

Quelle que soit l’issue de la campagne `S=4` :

```text
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

Aucun fit métrique, aucune dimension effective, aucune courbure et aucune dynamique gravitationnelle ne sont ouverts.

## 19. Contrat gelé

```text
LEVEL3_FIRST_NEW_SPIN = 4
LEVEL3_NEW_CASES = triangle:S4, ring4:S4, ring5:S4
S_ROLE = GAUGE_FIELD_TRUNCATION_PARAMETER
FULL_SPECTRUM = REQUIRED
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
PRIMARY_CONTRAST = HIGH_MINUS_LOW
REGIMES = equal thirds of cumulative state population
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
PRIMARY_PAIR = S3_TO_S4
INTER_S_BRANCH_MATCHING = FORBIDDEN
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
S4_PRIMARY_TAXONOMY = S4_DIRECTION_PERSISTS | S4_DIRECTION_REVERSES | S4_CONTRAST_UNRESOLVED | NOT_EVALUABLE
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## 20. Statut

```text
L3_S4_SCIENTIFIC_PREREGISTRATION = FROZEN
REAL_S4_HAMILTONIAN_BUILT = NO
REAL_S4_DIAGONALIZATION = NO
S4_OBSERVABLES_COMPUTED = NO
NEW_PHYSICAL_RESULT_INSPECTED = NO
LEVEL3_S4_NORMATIVE_CAMPAIGN = NOT_STARTED
```

L’étape suivante autorisée est l’audit d’ingénierie de l’infrastructure nécessaire pour matérialiser ce contrat dans un manifeste, un schéma, une sérialisation et un runner Level 3 dédiés. Cet audit n’autorise aucune exécution physique `S=4`.