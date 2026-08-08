# Level 1C — Pré-enregistrement conceptuel de la stratégie d'identifiabilité géométrique (1C-1)

Statut : **pré-enregistrement conceptuel — non normatif, aucune implémentation scientifique autorisée**

Branche : `research/level1-correlators`

Ce document est le livrable du lot 1C-1. Il ne calcule rien, ne lance aucune campagne, ne définit aucune transformation corrélateur→distance, n'ajuste aucun modèle et ne choisit aucune géométrie candidate. Il fige des choix méthodologiques et conceptuels sur la base de l'audit scientifique en lecture seule des degrés de liberté relationnels (accepté comme base conceptuelle) et du cadrage 1C-0 (`docs/levels/level1c/conceptual-framing.md`, accepté). Chaque affirmation reste étiquetée **[ÉTABLI]**, **[GELÉ]**, **[HYPOTHÈSE]**, **[OPTION MÉTHODOLOGIQUE]** ou **[DÉCISION OUVERTE]**.

## 1. Motivation issue de l'audit DOF

**[ÉTABLI]** L'audit scientifique en lecture seule (accepté) a établi qu'au point de référence `J_i` uniforme :

```text
triangle : 1 orbite de paires
ring4    : 2 orbites de paires
ring5    : 2 orbites de paires
```

et qu'après symétries et contraintes exactes (commutation `i<->j`, orbites spatiales, règle de somme de charge `Q_tot=0`, règle de somme de saveur `T(T+1)` au secteur de saveur maximale) :

```text
C_TT_conn : 1 à 2 DOF relationnels libres par groupe en général,
            0 dans le secteur de saveur maximale analysé.

rho_QQ    : 0 à 1 DOF relationnel libre par groupe,
            null structurel dans le secteur de saveur maximale.
```

**Conclusion méthodologique acceptée** : le point de référence maximalement symétrique est un excellent jeu de calibration analytique, mais il est trop pauvre en degrés de liberté pour constituer, à lui seul et groupe par groupe, une base fortement falsifiable de reconstruction géométrique générique.

**Reformulation de la question centrale de 1C** (`conceptual-framing.md` §2 reste la question scientifique de fond ; ce document en précise la condition opérationnelle) :

```text
Non plus seulement : quelle observable utiliser ?

Mais : dans quelles conditions mesurer les relations pour obtenir
suffisamment de degrés de liberté indépendants afin qu'une hypothèse
géométrique puisse réellement être falsifiée ?
```

**[GELÉ — distinction méthodologique centrale de 1C-1]** Ce document distingue explicitement et ne fusionne jamais :

```text
choix de la sonde            (quelle observable porte le signal)
            vs
identifiabilité du problème  (le signal porté a-t-il assez de DOF
                               pour rejeter une hypothèse géométrique)
```

Une observable physiquement pertinente n'est pas suffisante si les symétries et contraintes réduisent ses données à 0-2 DOF par groupe, comme l'audit l'a montré pour les deux observables actuellement disponibles.

## 2. Sonde primaire

**[GELÉ]** `C_TT_conn` → sonde relationnelle primaire de Level 1C.

Justification documentaire, reprise de l'audit accepté et de l'inventaire 1C-0 (§5.3) :

```text
- scalaire réel ;
- gauge-invariant ;
- aucun chemin P (pas de dépendance à la sélection minimal_paths) ;
- aucun transporteur U_e explicite dans l'opérateur ;
- couverture complète dans la campagne Level 1B (0/96 null, cf. audit §J) ;
- davantage de DOF relationnels que rho_QQ dans l'audit accepté
  (1-2 contre 0-1 par groupe) ;
- règle de somme globale T(T+1) moins directement contraignante sur les
  seuls termes hors diagonale actuellement sérialisés (la diagonale
  T_i^a n'étant pas serialisée hors secteur de saveur maximale, la
  règle ne réduit pas artificiellement le compte de DOF disponible).
```

**Formulation prudente obligatoire, à respecter dans tout document ultérieur de la chaîne 1C** :

> `C_TT_conn` est retenu comme meilleure sonde primaire disponible parmi les observables Level 1B actuelles ; ceci ne signifie pas qu'il fournisse à lui seul suffisamment d'information pour reconstruire une géométrie.

**Interdictions de formulation, gelées** : ne jamais écrire dans un document de la chaîne 1C, sous aucune forme équivalente :

```text
"C_TT_conn démontre la géométrie"
"C_TT_conn est une distance"
"C_TT_conn suffit à reconstruire une métrique"
```

## 3. Contrôle de concordance

**[GELÉ]** `rho_QQ` → contrôle relationnel indépendant charge/jauge (jamais une sonde primaire).

**Base analytique documentée** (reprise de l'audit accepté) :

```text
Q_tot = sum_i Q_i = 0   (identité d'opérateur, loi de Gauss sommée,
                          docs/model/physical-model.md)
```

Conséquence exacte au point de référence homogène (variance locale identique sur tous les sites, orbite de sites unique) :

```text
sum_{j != i} rho_QQ(i,j) = -1
```

**Conséquences numériques acceptées** :

```text
triangle :
  rho_QQ = -0.5 imposé sur l'orbite unique de paires
  -> 0 DOF géométrique libre

ring4 / ring5 :
  1 DOF libre après application de la règle de somme
  (2x(d=1) + k*x(d=2) = -1, k=1 pour ring4, k=2 pour ring5)
```

Donc `rho_QQ` est un contrôle de concordance, jamais une sonde primaire — son rôle est de vérifier qu'un futur pipeline respecte une contrainte exacte connue, pas de porter le signal géométrique principal.

**[GELÉ — avertissement de portée]** Sous une brisure spatiale telle que `j_break`, ne jamais supposer que `sum_{j!=i} rho_QQ(i,j) = -1` survit sous cette forme normalisée : cette forme précise dépend de l'homogénéité de la variance locale sur une orbite de sites unique, qui n'est plus garantie sous brisure de symétrie spatiale. La conservation brute `sum_j C_QQ_conn(i,j) = 0` (loi de Gauss, opérateur) reste exacte dans tous les cas, mais les variances locales `C_QQ_conn(i,i)` peuvent devenir inhomogènes d'un site à l'autre, ce qui invaliderait la simplification `rho_QQ(i,j)=C_QQ_conn(i,j)/var` à variance constante. Toute exploitation de `rho_QQ` comme contrôle sous `j_break` devra re-dériver la forme correcte de la règle de somme avant utilisation.

## 4. Observables différées

**[GELÉ]** `G_ij^{alpha,beta}[P]` → non utilisé comme sonde primaire de reconstruction métrique initiale.

Motif documenté : les artefacts Level 1B ont sélectionné les chemins via `paths.minimal_paths` (distance combinatoire non orientée du graphe), donc la distance combinatoire imposée intervient déjà dans la sélection des valeurs disponibles pour `G[P]`. Ce risque de circularité (déjà signalé, risque **ÉLEVÉ**, `conceptual-framing.md` §5.1/§5.6/§6) interdit son utilisation comme preuve indépendante d'une métrique émergente dans la phase actuelle.

`G[P]` n'est pas abandonné : `G[P]` → réservé à un futur volet transport / phase / holonomie / dépendance au chemin, hors périmètre de la première stratégie de reconstruction géométrique.

**[GELÉ]** `gamma_O` reste uniquement un diagnostic de robustesse inter-`S` (D018, déjà frozen). `gamma_O` ne doit jamais être présenté, dans aucun document de la chaîne 1C, comme une distance ou comme une sonde spatiale primaire.

## 5. Point de référence comme calibration

**[GELÉ — nouvelle interprétation méthodologique]**

```text
J_i = 1 uniforme  ->  jeu de calibration analytique
                  ->  PAS le jeu principal d'inférence géométrique
```

Les valeurs et règles forcées observées au point de référence doivent devenir des tests de contrôle pour tout futur pipeline 1C, jamais une preuve géométrique en tant que telle (puisqu'une valeur forcée par symétrie/conservation ne peut, par construction, discriminer entre hypothèses géométriques — voir §6).

Exemples de tests de calibration gelés, tous déjà vérifiés par l'audit accepté :

```text
rho_QQ(triangle, secteur non maximal) = -0.5 exactement.
C_TT_conn(triangle, secteur de saveur maximale) = 0.25 exactement.
rho_QQ(secteur de saveur maximale) = null / zero_local_charge_variance.
```

Un futur pipeline de reconstruction qui ne reproduit pas exactement ces contraintes est invalide avant même toute interprétation géométrique — ce sont des tests de correction du pipeline, pas des résultats scientifiques à interpréter.

### Tests d'ordre au point de référence (test de localité relationnelle)

**[OPTION MÉTHODOLOGIQUE]** Autorisé uniquement comme futur test de calibration, jamais comme reconstruction géométrique : la comparaison des valeurs entre orbites `d=1` et `d=2` sur `ring4`/`ring5`. Exemple de question admissible pour un futur lot : `|C_TT_conn(d=1)| > |C_TT_conn(d=2)| ?`. Cette inégalité particulière n'est **pas gelée** comme critère scientifique par ce document — son orientation physique n'a pas été vérifiée séparément ici.

**[GELÉ — nom et portée de ce type de test]** Ce type de test est nommé **test de localité relationnelle par rapport au support combinatoire microscopique**. Précision obligatoire à toute utilisation future : réussir ce test ne démontre aucune géométrie émergente, puisque les classes `d=1`/`d=2` proviennent elles-mêmes du graphe imposé (même risque de circularité que celui déjà signalé pour la distance combinatoire, `conceptual-framing.md` §6.1) — c'est un test de cohérence interne du pipeline, pas une preuve géométrique indépendante.

## 6. Secteurs inéligibles à l'inférence

**[GELÉ]** Deux usages distincts des secteurs de saveur maximale, jamais confondus :

**Calibration analytique** : les secteurs de saveur maximale sont conservés et utiles précisément parce que certaines valeurs y sont imposées exactement (§5) — ils servent de test de correction, pas de source de signal.

**Inférence géométrique** : un secteur est déclaré **INÉLIGIBLE** à l'inférence géométrique dès que l'audit établit `N_independent_DOF = 0` pour ce secteur et cette observable (c'est le cas de `triangle[T=3/2]` pour `C_TT_conn` et `rho_QQ`, et plus généralement de tout secteur de saveur maximale sur une géométrie à orbite de paires unique). Motif : une valeur forcée analytiquement (par symétrie + conservation) ne peut par construction porter aucune information géométrique indépendante — n'importe quelle hypothèse géométrique candidate reproduirait cette valeur automatiquement, donc l'accord ne teste rien.

**[GELÉ — distinction à ne jamais confondre]**

```text
secteur physiquement intéressant   !=   secteur informatif pour
                                          reconstruction géométrique
```

Un secteur peut être l'un sans être l'autre : le secteur de saveur maximale reste physiquement intéressant (théorème V11, structure exacte du modèle) tout en étant inéligible à toute tentative de reconstruction géométrique par manque de DOF.

### Statut du secteur de saveur maximale `T_max` (1C-4b, gelé)

**[GELÉ]** Pour Level 1C, le secteur de saveur maximale `T_max` (`T=N/2`, `twice_T=N`, pour une géométrie à `N` sites) est classé :

```text
CALIBRATION_ONLY
```

**Justification, démontrée (audit 1C-4b) sous les hypothèses `M=2`, `Q_tot=0` (demi-remplissage global), SU(2) de saveur exacte, `T=N/2` :**

```text
T=N/2  ->  n_d=0 (aucune double occupation, théorème déjà gelé,
           specification.md §"Théorème du secteur de saveur maximale")
       ->  à demi-remplissage (Q_tot=0) : n_i=1 sur CHAQUE site,
           exactement, opérateur (pas seulement en espérance)
       ->  C_TT_conn(i,i) = <T_i²> = 3/4 exactement (Casimir local d'un
           spin-1/2 exact, scalaire sur toute représentation irréductible)
       ->  C_TT_conn(i,j) = 1/4 exactement pour tout i != j (règle de
           somme T_tot² + symétrie de permutation S_N du secteur de spin
           maximal d'un produit de N spins-1/2, multiplicité 1 dans la
           décomposition de Clebsch-Gordan -- une symétrie ABSTRAITE du
           secteur de saveur, indépendante de la géométrie du graphe et
           du groupe d'automorphismes spatial)
       ->  rho_QQ structurellement null (zero_local_charge_variance) :
           Q_i=n_i-1=0 exactement, Var(Q_i)=0 exactement, pour toute paire
       ->  G_ij^{alpha,beta}[P] = 0 pour tout i != j, par orthogonalité
           exacte des secteurs d'occupation (c†_{i,alpha} W_P c_{j,beta}
           transforme (n_i,n_j)=(1,1) en (2,0) ou s'annule par exclusion
           de Pauli ; le résultat non nul porte n_d>=1, donc T<N/2,
           orthogonal à T_max -- W_P n'agit que sur les degrés de liberté
           de jauge, jamais sur l'occupation matière) ; conséquence :
           flavor_singlet=0, flavor_frobenius_squared=0,
           flavor_singular_values=(0,0) (valeurs exactes, PAS "null"),
           flavor_singular_value_ratio=null/normalization_denominator_
           below_floor (contrat déjà gelé D018/1B-7, jamais une valeur
           fabriquée)
       ->  aucune liberté relationnelle primaire disponible pour
           l'inférence géométrique actuelle.
```

**`G[P]` n'est pas réintroduit comme sonde géométrique primaire par cette annulation** : il reste différé pour un futur volet transport/phase/holonomie, en raison du risque de circularité déjà signalé (§4, dépendance à `paths.minimal_paths`) — cette annulation dans `T_max` est une conséquence du secteur de saveur, pas un changement de statut de `G[P]` lui-même.

**Distinction des trois quantités, jamais confondues :**

```text
N_records                     : nombre d'enregistrements C_TT_conn
                                 sérialisés (N diagonales + N(N-1) paires
                                 ordonnées hors-diagonale).
N_pair_orbits                 : nombre d'orbites de paires sous le
                                 sous-groupe de symétrie SPATIAL effectif
                                 (2 pour triangle, 6 pour ring5 sous
                                 j_break -- audit 1C-2a).
N_independent_geometry_DOF     : nombre de valeurs RÉELLEMENT libres pour
                                 l'inférence géométrique -- 0 dans T_max,
                                 quelle que soit la géométrie, quel que
                                 soit j_break, parce que la symétrie
                                 pertinente (S_N, secteur de saveur) est
                                 strictement plus grande que le groupe
                                 d'automorphismes spatial et force TOUTES
                                 les paires à la même valeur, pas
                                 seulement celles d'une même orbite
                                 spatiale.
```

**Le fait qu'une brisure spatiale (`j_break`) augmente `N_pair_orbits` ne change JAMAIS `N_independent_geometry_DOF` dans `T_max`** :

```text
TMAX_GEOMETRY_INFORMATION_DOF_CTT = 0
```

**Rôle de calibration légitime (liste fermée, audit 1C-4b)** : occupation `n_i=1` ; self-corrélateur `C_TT_conn(i,i)=3/4` ; hors-diagonale `C_TT_conn(i,j)=1/4` ; fermeture de la règle de somme `T(T+1)` (V23) ; `rho_QQ` structurellement null ; `G=0` et ses invariants dérivés forcés ; cohérence SU(2) (exactitude de la symétrie de saveur) ; sérialisation/normalisation (contrats de plancher/null déjà gelés). **Une cible peut être excellente comme contrôle et non informative pour l'inférence** — ce n'est pas une contradiction, ce sont deux rôles distincts, jamais fusionnés (§8 de l'audit 1C-4b).

**Règle de campagne future (universelle, gelée)** :

```text
Une campagne géométrique Level 1C ne doit PAS être déclarée invalide
uniquement parce que T_max n'est pas résolu dans la fenêtre spectrale
choisie pour d'autres raisons.

Aucune profondeur spectrale supplémentaire ne doit être choisie
uniquement pour atteindre T_max.

Si T_max est naturellement présent dans la fenêtre retenue pour
d'autres cibles, il est exploité comme contrôle de calibration, mais
jamais compté dans les degrés de liberté d'inférence géométrique.
```

Cette règle s'applique **universellement** — toute géométrie (présente ou future), toute valeur future de `J_0`, toute valeur future de `S` — tant que les hypothèses du théorème restent vraies (`M=2`, `Q_tot=0`/demi-remplissage global, SU(2) de saveur exacte, `T=N/2`). Elle ne décide **aucune autre cible requise** pour une future campagne — ce choix reste ouvert, séparé.

**Contrôle du biais post-hoc (audit 1C-4b §12, confirmé)** : cette politique est acceptable malgré la découverte préalable du coût spectral de `ring5 T_max` (`1C-4a`) parce que (1) sa justification est analytique, indépendante du coût observé — la même preuve, avec la même force, s'applique à `triangle`, où aucun problème de coût n'existe ; (2) la règle est appliquée universellement à `triangle` et `ring5` (et à toute géométrie future), jamais ciblée sur `ring5` seul ; (3) la même conclusion aurait été tirée même si `T_max` avait été gratuit à résoudre ; (4) la décision est gelée ici, avant toute conception de campagne normative `J0×S` ; (5) aucun résultat Level 1B n'est supprimé ni invalidé ; (6) le manifeste Level 1B historique reste inchangé. L'ordre chronologique réel (coût découvert avant la décision) n'est pas dissimulé — il est documenté explicitement ici et dans `docs/governance/current-task.md`.

**Statut historique Level 1B, inchangé** : `T_max` reste une cible historique valide de Level 1B (`experiments/level1/preregistered-manifest-v1.json`, cible `T_max`/`selection_kind="flavor_label"`) — aucun manifeste Level 1B n'est modifié par cette décision. La politique `CALIBRATION_ONLY` concerne exclusivement la **future** inférence géométrique Level 1C.

## 7. Principe d'identifiabilité

**[GELÉ — exigence de conception, pas encore quantifiée]**

> Avant toute reconstruction géométrique normative, le jeu de données retenu doit posséder suffisamment de degrés de liberté relationnels indépendants pour que les classes géométriques comparées disposent d'une possibilité réelle d'être rejetées.

Ce document ne fixe **pas** de seuil numérique arbitraire du type `DOF >= X` (**[DÉCISION OUVERTE]**, non tranchée ici). La comparaison à opérer dans un futur lot devra mettre en regard :

```text
nombre de DOF relationnels indépendants (établi par un audit du même
type que celui déjà accepté, refait pour toute nouvelle condition
de mesure)
                    vs
nombre effectif de paramètres libres du candidat géométrique après
quotient par ses jauges (translations, rotations, échelle, etc.)
```

Aucune formule de ce rapport n'est gelée ici ; ce document enregistre seulement l'existence et la nécessité du principe.

## 8. j_break comme candidat de campagne informative

**[ÉTABLI — enregistré, pas autorisé]** `j_break` est enregistré comme **candidat principal actuellement identifié pour augmenter l'identifiabilité relationnelle**, mais n'est **pas** encore une campagne autorisée par ce document.

Le modèle actuel définit `J_0 = 1.5`, `J_{i != 0} = 1` — ce choix réduit la symétrie spatiale du Hamiltonien (déjà établi par 1B-4 : seule la réflexion fixant le site perturbé survit, la translation ne commute plus exactement avec `H`).

**Constat conceptuel enregistré** : moins de symétrie → éclatement des orbites de paires → potentiel de DOF relationnels supplémentaires.

Pour les géométries actuelles, le comptage théorique du nombre d'orbites sous une réflexion résiduelle seule (au lieu du groupe diédral complet) suggère notamment :

```text
triangle : 1 -> 2 orbites de paires
ring5    : 2 -> 6 orbites de paires
```

**[GELÉ — avertissement obligatoire, ne jamais omettre]** Ne pas écrire, dans aucun document futur de la chaîne 1C :

```text
"2 orbites = 2 DOF indépendants"
"6 orbites = 6 DOF indépendants"
```

Un nombre d'orbites plus élevé est une **borne supérieure potentielle**, pas un compte final de DOF indépendants : les conservations exactes (charge, saveur) et d'autres dépendances linéaires exactes non encore identifiées sous `j_break` peuvent encore réduire ce rang, exactement comme elles l'ont fait au point de référence (§1). Avant toute campagne normative `j_break` à but d'inférence géométrique, un futur lot devra pré-enregistrer et vérifier, par le même type d'audit que celui déjà accepté :

```text
N_orbits
N_exact_constraints
N_expected_independent_DOF
```

## 9. Données supplémentaires nécessaires

**[ÉTABLI — besoin documenté, aucune implémentation autorisée par ce lot]** Pour fermer exactement la règle de somme de saveur `sum_{i,j} C_TT_conn(i,j) = T(T+1)` dans **tous** les secteurs spectraux complets (pas uniquement le secteur de saveur maximale, où elle est déjà fermée analytiquement), il manque un self-correlator de saveur non actuellement sérialisé :

```text
<T_i^2>   (ou, de façon équivalente si retenu scientifiquement plus
           tard : C_TT_conn(i,i))
```

Ceci est enregistré comme un besoin de données futures, **pas** implémenté par ce lot.

**[GELÉ]** Aucune nouvelle observable normalisée `rho_TT` n'est définie par ce document. Une éventuelle définition future de `rho_TT` nécessiterait une décision scientifique et un contrat de normalisation séparés (par analogie avec la manière dont `rho_QQ` a été gelé), jamais une extrapolation mécanique de la forme de `rho_QQ`.

### Trou de test de commutation

**[ÉTABLI — trou de couverture documenté par l'audit accepté]** Pour `i != j`, il manque un test unitaire dédié de la propriété exacte réellement utilisée par `C_TT_conn` (commutation `[T_i^a, T_j^b] = 0` pour des sites distincts, ou toute propriété équivalente suffisante) — contrairement à la charge, qui dispose déjà de `test_local_charge_product_distinct_nodes`. Ce trou est enregistré ici comme besoin futur ; **aucun numéro de validation (`V19` ou autre) n'est attribué par ce document** sans audit préalable de la numérotation existante du plan de validation (`docs/levels/level1/validation-plan.md`), et **aucun test n'est ajouté par 1C-1** — ce lot est documentaire uniquement.

## 10. Information mutuelle

**[ÉTABLI — reconduit depuis l'audit accepté]** `I(i:j)` → upgrade relationnel futur séparé.

Statut : **non calculable depuis les artefacts Level 1B actuels**, pour trois raisons cumulatives déjà établies par l'audit :

```text
- rho_i / rho_ij (matrices densité réduites) non sérialisées ;
- vecteurs propres (Psi) non sérialisés, par principe architectural
  gelé (eigenvectors never serialized) ;
- l'ensemble actuel de corrélateurs (canaux Q, T uniquement) est
  incomplet pour une tomographie locale complète.
```

Une future campagne d'information mutuelle nécessitera donc une nouvelle spécification scientifique (nouvelles observables et/ou nouveau protocole de calcul), à traiter séparément. Elle ne fait **pas** partie de la première campagne géométrique envisagée par la présente chaîne 1C.

## 11. Statut de disk7

**[GELÉ]** `disk7` n'est **pas** admis dans Level 1C par ce lot. Il est enregistré uniquement comme candidat futur à auditer.

Un futur audit devra établir, avant toute admission, au minimum :

```text
- définition exacte du graphe ;
- nombre de nœuds et liens ;
- groupe d'automorphismes ;
- orbites de paires ;
- nombre potentiel de DOF relationnels (même type d'audit que celui
  déjà accepté pour triangle/ring4/ring5) ;
- coût Hilbert / ressources ;
- valeurs de S réalisables ;
- garde-fous runtime/mémoire (cohérents avec max_dense_dimension /
  max_sparse_dimension déjà gelés) ;
- rôle scientifique distinct de ring5/j_break (pourquoi disk7 apporterait
  quelque chose que ring5 et ring5-j_break n'apportent pas déjà).
```

Aucune campagne `disk7` n'est autorisée par ce document.

## 12. Hypothèse de cohérence inter-secteurs

**[HYPOTHÈSE À TESTER — pas présupposée]** Ce document ne présuppose **pas** qu'un seul plongement géométrique doive être identique pour tous les groupes spectraux. La question est enregistrée comme hypothèse à tester par une future campagne, pas comme un fait acquis :

> Les différents secteurs spectraux compatibles avec un même support microscopique produisent-ils une organisation géométrique compatible ?

C'est potentiellement un résultat physique en soi (une confirmation positive serait un résultat non trivial ; une confirmation négative — incompatibilité entre secteurs — le serait tout autant).

**[GELÉ — usage interdit de cette hypothèse]** Cette hypothèse ne doit **pas** être utilisée comme moyen post-hoc de multiplier artificiellement les degrés de liberté disponibles (par exemple en additionnant naïvement les DOF de plusieurs groupes spectraux pour atteindre un seuil d'identifiabilité) avant qu'elle soit elle-même pré-enregistrée et testée séparément comme hypothèse scientifique à part entière. L'audit accepté (§I) a déjà signalé que combiner les 7 groupes de référence suppose implicitement cette cohérence inter-secteurs sans la démontrer — ce document formalise cette réserve en règle de conception permanente pour la suite de la chaîne 1C.

## 13. Décisions encore ouvertes

**[DÉCISION OUVERTE — liste, aucune tranchée par ce document]**

```text
- seuil quantitatif (ou absence de seuil) du principe d'identifiabilité
  (§7) : comment comparer précisément N_DOF et N_parametres_de_jauge
  pour juger une classe géométrique "réellement falsifiable" ;
- transformation corrélateur -> dissimilarité/distance à choisir pour
  C_TT_conn (toutes les options déjà inventoriées par 1C-0 §8 restent
  ouvertes, aucune adoptée) ;
- protocole exact d'une future campagne j_break à but d'identifiabilité
  (valeurs de S, garde-fous, audit préalable des DOF sous j_break) ;
- décision scientifique séparée pour une éventuelle définition de
  rho_TT (§9) ;
- calendrier et portée d'un audit disk7 (§11) ;
- protocole de test de la cohérence inter-secteurs (§12) ;
- orientation physique de l'inégalité de localité relationnelle d=1
  vs d=2 (§5), non vérifiée par ce document ;
- numérotation d'un futur critère de validation pour la commutation
  T_i^a/T_j^b (§9), à faire après audit de docs/levels/level1/
  validation-plan.md, pas par attribution arbitraire.
```

## 14. Ce que 1C-1 n'autorise pas

**[ÉTABLI — limite explicite de ce lot]**

```text
- aucune nouvelle campagne (y compris j_break, disk7, ou toute
  extension de la campagne normative Level 1B) ;
- aucun calcul scientifique, aucune diagonalisation, aucun nouveau run ;
- aucun fitting, aucun embedding, aucune reconstruction géométrique ;
- aucune transformation corrélateur -> distance/dissimilarité définie
  ou adoptée ;
- aucune nouvelle observable (notamment aucun rho_TT) ;
- aucun calcul d'information mutuelle ;
- aucun choix de géométrie candidate (R1/R2/S1/S2) comme hypothèse
  favorite ;
- aucune modification de src/*, scripts/*, tests/*, experiments/*,
  schemas/*, .github/workflows/* ;
- aucun test ajouté (y compris pour le trou de commutation §9) ;
- aucun numéro de validation attribué sans audit préalable de la
  numérotation existante.
```

Ce document fige uniquement une stratégie conceptuelle et des garde-fous de formulation ; il n'ouvre, n'autorise, ni n'engage aucun sous-lot d'exécution.
