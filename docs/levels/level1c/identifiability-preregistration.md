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

## 15. Contrat `STRUCTURALLY_ELIGIBLE` v1 et statut de `J0` (1C-5a/1C-5b, gelé)

**[GELÉ]** Pré-enregistrement documentaire issu de l'audit 1C-5a (accepté définitivement), **avant** toute conception de campagne `J0×S`. Aucune valeur de `J0`, aucune fenêtre, aucun seuil numérique de succès, aucun algorithme n'est fixé ici — voir §15.10 (« ce que ce document ne définit pas »).

### 15.1 Contrat `STRUCTURALLY_ELIGIBLE` — Level 1C, v1

```text
STRUCTURALLY_ELIGIBLE_CONTRACT_VERSION = 1
```

Un groupe spectral est `STRUCTURALLY_ELIGIBLE` si et seulement si :

```text
1. status == complete_multiplet ;
2. lower_bound_only == False ;
3. l'identification du groupe (sélection par rang d'énergie ou par
   twice_T) n'utilise aucune information géométrique destinée ensuite
   à servir de cible d'inférence ;
4. C_TT_conn complet est disponible : N diagonales + N(N-1)
   hors-diagonales ordonnées ;
5. l'application de l'ENSEMBLE GELÉ v1 de contraintes analytiques
   Level 1C (§15.2) ne démontre PAS N_independent_geometry_DOF = 0
   pour ce groupe ;
6. si une revendication inter-S est faite pour ce groupe, un matching
   inter-S admissible (`matching.match_spectral_group`, déjà accepté)
   doit être disponible.
```

**Distinction impérative, jamais confondue** :

```text
STRUCTURALLY_ELIGIBLE  !=  INFORMATION_GEOMETRICALLY_DEMONSTRATED
DOF_max > 0             !=  DOF_exact > 0
```

`STRUCTURALLY_ELIGIBLE` signifie exactement : « l'ensemble gelé v1 des contraintes analytiques Level 1C ne ferme pas ce secteur à `DOF=0` » — jamais : « une information géométrique est démontrée disponible ». `DOF_exact` reste `UNKNOWN` tant qu'il n'a pas été démontré par un protocole séparé (§15.9, §15.18).

### 15.2 Ensemble analytique gelé v1 (liste fermée, aucune identité nouvelle)

```text
v1.1  C_ij = C_ji
      (commutation d'opérateur exacte -- fondations corrigées issues de
      l'audit 1C-2a, retenues telles que subsumées par 1C-2b/1C-2c)

v1.2  symétrie spatiale résiduelle applicable au cas considéré
      (ex. {identité, réflexion fixant le site 0} sous j_break --
      fondations corrigées issues de l'audit 1C-2a, retenues telles que
      subsumées par 1C-2b/1C-2c)

v1.3  fermeture globale V23 :
      sum_i C_ii + sum_{i!=j} C_ij = T(T+1)
      (1C-3b, une seule relation scalaire globale par groupe, jamais
      davantage)

v1.4  théorème analytique du secteur de saveur maximale, lorsqu'il
      s'applique (T=N/2) :
      -> n_i=1 (opérateur, exact)
      -> C_ii=3/4 exactement
      -> C_ij=1/4 exactement pour tout i!=j
      -> rho_QQ structurellement null
      -> G_ij^{alpha,beta}[P]=0 pour tout i!=j
      -> DOF géométrique C_TT = 0
      (1C-4b/1C-4c)
```

Aucune identité au-delà de `v1.1`-`v1.4` n'est incluse dans l'ensemble gelé v1.

### 15.3 Gouvernance et versionnement du contrat

```text
Une identité analytique découverte APRÈS le gel d'une version (v1,
puis une éventuelle v2, v3, ...) :
  1. ne modifie JAMAIS silencieusement la version en vigueur ;
  2. doit être auditée séparément (un lot dédié, comme 1C-4b l'a été
     pour le théorème T_max) ;
  3. doit produire une nouvelle version explicite du contrat (v2, v3,
     ...), jamais une réécriture silencieuse de v1 ;
  4. doit être gelée AVANT toute campagne utilisant cette nouvelle
     version -- jamais appliquée rétroactivement à une campagne déjà
     lancée ou déjà interprétée sous une version antérieure.

Le versionnement protège UNIQUEMENT contre la sélection post-hoc de
cibles après observation de résultats numériques -- il n'autorise
JAMAIS à ignorer une contradiction scientifique réelle : si une
identité nouvellement découverte invalide une interprétation
antérieure, cela doit être rapporté explicitement et sans délai,
indépendamment de toute question de version.
```

### 15.4 Application du contrat v1 (état actuel)

```text
triangle :
  fundamental    -> STRUCTURALLY_ELIGIBLE
  first_excited  -> STRUCTURALLY_ELIGIBLE
  T_max          -> CALIBRATION_ONLY / non éligible (v1.4 ferme DOF=0)

ring5 :
  fundamental    -> STRUCTURALLY_ELIGIBLE
  first_excited  -> STRUCTURALLY_ELIGIBLE
  T_3_2          -> STRUCTURALLY_ELIGIBLE
  T_max          -> CALIBRATION_ONLY / non éligible (v1.4 ferme DOF=0)
```

Ces groupes constituent des **canaux observationnels distincts, non dupliqués** (`distinct observational channels`, `non-duplicate spectral groups`) — cette formulation n'affirme et ne présuppose **aucune indépendance informationnelle déjà démontrée** entre eux (voir §15.7).

### 15.5 Comptage des DOF de la matrice complète `C_TT` sous `j_break`

**Triangle (`N=3`)** :

```text
N_serialized_values = 9   (3 diagonales + 6 hors-diagonales ordonnées)

N_diagonal_orbits = 2       {D0} , {D1,D2}
N_offdiagonal_pair_orbits = 2   {(0,1),(0,2)} , {(1,2)}
N_symmetry_orbits_total = 4

DOF_max_before_global_closure = 4
DOF_max_after_global_closure  = 3   (V23 ferme exactement UNE relation
                                      scalaire globale, jamais davantage)
DOF_exact = UNKNOWN
```

**Ring5 (`N=5`)** :

```text
N_serialized_values = 25   (5 diagonales + 20 hors-diagonales ordonnées)

N_diagonal_orbits = 3       {D0} , {D1,D4} , {D2,D3}
N_offdiagonal_pair_orbits = 6
N_symmetry_orbits_total = 9

DOF_max_before_global_closure = 9
DOF_max_after_global_closure  = 8
DOF_exact = UNKNOWN
```

**`3` et `8` sont des plafonds, jamais des rangs réellement démontrés indépendants.** `DOF_exact = UNKNOWN` dans les deux cas.

**Quantité historique distincte, conditionnelle, jamais confondue avec le plafond de la matrice complète** : en traitant les diagonales comme des entrées déjà connues plutôt que comme faisant partie du pool de DOF, la fermeture ne porte plus que sur les orbites hors-diagonale seules :

```text
offdiagonal_DOF_max conditional on measured diagonals :
  triangle : 2 -> 1
  ring5    : 6 -> 5
```

Cette quantité **n'est pas** le DOF de la matrice complète (`3`/`8` ci-dessus) — une convention différente, gardée séparée.

### 15.6 Politique de cibles : `ELIGIBILITY_BASED`

```text
TARGET_POLICY = ELIGIBILITY_BASED
```

```text
Aucune liste future de target_id choisie opportunistement après
observation de résultats numériques. Les groupes alimentant
l'inférence Level 1C sont exactement ceux satisfaisant
STRUCTURALLY_ELIGIBLE v1 (§15.1), jamais une sélection manuelle ad hoc.
```

**Non gelé par cette politique** : aucune métrique multi-état, aucune concaténation arbitraire des matrices de groupes éligibles distincts — le simple fait qu'un groupe soit éligible ne l'oblige jamais à être combiné avec un autre dans une structure unique.

### 15.7 Hypothèse de cohérence inter-secteurs (multi-état)

```text
MULTISTATE_COMMON_GEOMETRY_HYPOTHESIS = DEFENSIBLE (comme critère, pas
                                                      comme fait établi)
```

> Chaque groupe spectral fournit un canal observationnel distinct du même support microscopique. Une future structure géométrique candidate serait renforcée si une même reconstruction pouvait expliquer plusieurs groupes sans paramètres géométriques indépendants ajustés groupe par groupe.

**Ceci reste une hypothèse à tester, jamais présupposée** — aucune géométrie commune n'est présupposée par ce document ; cette formulation ne fait que fixer un CRITÈRE d'évaluationméthodologique pour un futur candidat, cohérent avec §12 (hypothèse de cohérence inter-secteurs, déjà enregistrée en 1C-1).

### 15.8 Statut scientifique de `J0`

```text
J0_STATUS = LOCAL_RESPONSE_PROBE

J0 IS NOT GEOMETRY
J0 IS NOT CURVATURE
J0 IS NOT METRIC
J0 IS NOT A GRAVITATIONAL SOURCE
```

`J_0` est le coefficient d'un terme de Hamiltonien **local, sur site** (couplage densité-densité type Hubbard-U entre les deux saveurs au même site), établi par lecture directe du code (1C-2a/1C-2b) — sans dimension spatiale, sans relation démontrée à une distance, une courbure, ou une métrique. `J_0 - 1` est une perturbation locale contrôlée, utilisée uniquement pour sonder la réponse des observables relationnelles déjà gauge-invariantes/SU(2)-invariantes — jamais pour être renommée en un concept géométrique ou gravitationnel non démontré.

### 15.9 Rôle de `J0=1`

```text
J0_EQ_1_ROLE = CALIBRATION_BASELINE
```

```text
J0=1  -> point symétrique de référence / calibration (groupe diédral
         complet, riche en contrôles déjà établis)
J0!=1 -> brisure locale contrôlée et connue
comparaison -> réponse relationnelle à cette perturbation connue
```

`J0=1` ne devient jamais automatiquement une donnée principale d'inférence — rôle strictement auxiliaire/soustractif, jamais fusionné avec le rôle d'inférence (même séparation de principe que pour `T_max`, §6).

### 15.10 `Delta C_TT` — outil d'analyse, pas un nouvel observable

```text
DELTA_CTT_USEFULNESS = PROMISING

Delta C_ij(J0) = C_ij(J0) - C_ij(J0=1)
```

Uniquement comme outil potentiel d'analyse future (quantité dérivée de valeurs déjà sérialisées, comme le ratio `r_X` de 1C-2c). **Ce document ne crée aucun nouvel observable normatif, ne modifie aucun schéma, ne gèle aucun seuil, aucune normalisation, et n'impose `Delta_C` comme donnée obligatoire nulle part.**

### 15.11 Réponse permise versus réponse démontrée

```text
absence de fermeture analytique (STRUCTURALLY_ELIGIBLE)
!=
réponse effective démontrée

DOF structurellement permis (DOF_max > 0)
n'implique PAS
dC/dJ0 != 0
```

La variation effective reste, dans tous les cas, une propriété à mesurer par un protocole futur — jamais présupposée par l'éligibilité structurelle.

### 15.12 `BLIND_DEFECT_LOCALIZATION`

```text
BLIND_DEFECT_LOCALIZATION = CONDITIONAL
```

```text
Le reconstructeur ne reçoit PAS l'identité du site perturbé --
uniquement la structure relationnelle admissible (matrice C_TT,
diagonale incluse). Une localisation ne serait réussie que si un
profil relationnel unique permet d'identifier de façon covariante le
site exceptionnel.
```

La symétrie résiduelle garantit certaines égalités entre sites d'une même orbite (ex. `D1=D2` sous `{id, réflexion}`), mais **ne garantit pas** l'unicité de `D0` ni de son profil complet par rapport aux autres orbites — une coïncidence accidentelle reste possible en principe. Le succès de cette piste **doit être testé empiriquement** dans un futur lot ; il n'est jamais annoncé comme déjà acquis ici.

### 15.13 Exigence d'invariance par relabellage

```text
RELABEL_INVARIANCE_REQUIREMENT = REQUIRED
```

Déjà un critère minimal gelé (`geometry-liberation.md §6`), confirmé et précisé ici :

```text
Interdit pour toute procédure future :
  - hardcoder "site 0" comme information d'entrée scientifique ;
  - supposer une correspondance fixe des indices entre deux runs
    distincts ;
  - utiliser la numérotation des sites comme coordonnée.

Le site effectivement perturbé peut être connu dans la PROVENANCE
expérimentale (métadonnée de calibration), mais ne doit jamais être
fourni au reconstructeur lors d'un test blind (§15.12).
```

### 15.14 Triangle versus ring5 — différence structurelle

```text
triangle : 4 orbites totales C_TT sous j_break, DOF_max_after_V23 = 3
           -- structure relationnelle très limitée.
ring5    : 9 orbites totales C_TT sous j_break, DOF_max_after_V23 = 8
           -- structure potentiellement plus riche (organisation par
           distance combinatoire au défaut : orbites touchant le site 0
           à distance 1/2, et orbites ne touchant pas le site 0 du tout).
```

`ring5` n'est **pas** défini par cela comme automatiquement géométrique, et aucune distance radiale n'est définie ici comme vérité-cible d'une future reconstruction — seule la richesse structurelle comparative (nombre d'orbites, présence de paires ne touchant pas le défaut) est enregistrée comme un fait déjà établi.

### 15.15 Rôle de `S` en Level 1C

```text
INTER_S_LEVEL1C_ROLE = ROBUSTNESS_ONLY
```

`S` reste un paramètre de **troncature du quantum link model** (représentation de spin du champ de jauge) — jamais une coordonnée spatiale, une dimension géométrique, ou un paramètre métrique. Une comparaison inter-S sert exclusivement à vérifier que la structure relationnelle interprétée n'est pas un artefact d'une troncature particulière, avant toute interprétation géométrique — exactement le rôle déjà validé pour Level 1B.

### 15.16 Questions empiriques non résolues (1C-5a/1C-5b)

**[DÉCISION OUVERTE — aucune présentée comme résolue]**

```text
- DOF_exact réel des groupes STRUCTURALLY_ELIGIBLE (au-delà des
  plafonds DOF_max de §15.5) ;
- réponse effective de C_TT à une variation de J0 (dC/dJ0, §15.11) ;
- redondance ou information commune réelle entre groupes spectraux
  distincts (§15.4/§15.7) ;
- existence effective d'un profil de défaut relationnel unique
  (§15.12) ;
- succès ou échec réel de BLIND_DEFECT_LOCALIZATION ;
- structure de propagation de la réponse vers les paires ne touchant
  pas directement le site perturbé ;
- stabilité de cette structure sous variation de S ;
- possibilité future d'une reconstruction géométrique commune à
  plusieurs groupes (§15.7) ;
- forme éventuelle d'une future transformation corrélateur -> distance
  (aucune n'est adoptée ni même esquissée ici).
```

### 15.17 Statut de préparation d'une campagne `J0×S`

```text
J0_CAMPAIGN_READY = NO
```

Ce document ne définit PAS :

```text
- valeurs de J0, nombre de points J0, symétrie d'une grille autour de 1 ;
- amplitudes de perturbation ;
- ordre des runs ;
- fenêtres spectrales (aucune fenêtre nouvelle, exploratoire ou
  normative, n'est choisie ici) ;
- critères de succès numériques ou seuils Delta_C ;
- algorithme de blind localization.
```

Tout ce qui précède appartient à un futur lot distinct, séparé, non ouvert par ce document.

## 16. Design de la campagne de réponse locale `J0` (1C-6a/1C-6b, gelé)

**[GELÉ]** Pré-enregistrement documentaire des décisions scientifiques acceptées définitivement lors des audits en lecture seule **1C-6a** (design de la campagne) et **1C-6b** (stratégie de baseline `J0=1` et audit `BRANCH_C2`). **Ce document ne fixe encore AUCUNE valeur numérique de `δ`, AUCUNE fenêtre spectrale, AUCUN seuil, AUCUN algorithme** — voir §16.25 pour la liste exhaustive de ce qui reste ouvert.

### 16.1 Question expérimentale (1C-6a)

```text
Pour les groupes spectraux STRUCTURALLY_ELIGIBLE v1, une perturbation
locale contrôlée J0 != 1 produit-elle une variation de la matrice
C_TT_conn complète qui :

1. n'est pas restreinte aux seules entrées incidentes au site perturbé ;
2. respecte la covariance imposée par les symétries résiduelles exactes ;
3. n'est pas un artefact de la troncature S dans le domaine effectivement
   testé ?
```

Le mot « reproductible » n'est jamais employé au sens expérimental/statistique : le calcul est une diagonalisation déterministe (D021), sans dérive instrumentale — il n'y a rien à « reproduire », seulement à structurer/qualifier.

### 16.2 Hiérarchie d'hypothèses

```text
H0 -- absence de réponse informative
H1 -- réponse locale triviale / incidente au défaut
H2 -- réponse relationnelle sur des paires non incidentes au défaut
H3 -- organisation commune compatible entre groupes spectraux distincts
H4 -- NON PAS un palier séquentiel : robustesse inter-S, axe transversal
      applicable à toute conclusion H1/H2/H3 retenue, à n'importe quel
      niveau de la hiérarchie
```

Aucune des hypothèses H1–H4 n'est démontrée à ce jour par une campagne `J0` — aucune campagne `J0` n'a encore été exécutée.

### 16.3 Variable `J0`

```text
J0_STATUS    = LOCAL_RESPONSE_PROBE
J0_EQ_1_ROLE = CALIBRATION_BASELINE
```

`delta_J = J0 - 1` : variable conceptuelle de conception de grille **uniquement**. `delta_J` n'est jamais : un observable ; une normalisation ; une distance ; une métrique ; une courbure ; une source gravitationnelle.

### 16.4 Forme de grille `J0`

```text
J0_GRID_SYMMETRY               = SYMMETRIC_AROUND_1
J0_POINT_COUNT_RECOMMENDATION  = 5
AMPLITUDE_POLICY                = PARAMETRIC_DELTA
J0_1P5_STATUS                   = USEFUL_ANCHOR
```

Forme conceptuelle : `{1-2δ, 1-δ, 1, 1+δ, 1+2δ}`, avec la contrainte gelée : tout `J0` retenu doit satisfaire `J0 > 0` strictement (`J0=0` supprime qualitativement le terme sur site ; `J0<0` inverse la configuration d'occupation locale favorisée — un régime différent, jamais une simple perturbation plus forte du même régime).

**[HISTORIQUE — statut au moment de 1C-6a/1C-6b/1C-6c]** `δ = OPEN` à ce stade : aucune valeur numérique de `δ` n'était fixée (ni `0.25`, ni `0.5`) et aucune des valeurs `J0 ∈ {0.5, 0.75, 1.25, 1.5}` n'était gelée comme grille — `J0=1.5` restait exclusivement `USEFUL_ANCHOR` (seul point historiquement calculé, jamais démontré optimal).

**[ÉTAT COURANT — gelé par 1C-6d/1C-6e, voir §17]** `δ` est désormais fixé à `0.25` et la grille `J0_GRID = {0.5, 0.75, 1.0, 1.25, 1.5}` est `FROZEN`.

### 16.5 Ensemble `S`

```text
S_SET_RECOMMENDATION  = {2,3}
BASELINE_S_SET         = {2,3}
INTER_S_LEVEL1C_ROLE   = ROBUSTNESS_ONLY
```

`S=1` n'est pas inclus par inertie historique (aucune justification scientifique spécifique ne l'exige). Aucune convergence `S -> infini` n'est revendiquée.

### 16.6 Ensembles de cibles

```text
PRIMARY_ANALYSIS_SET   = triangle{fundamental,first_excited} ∪
                          ring5{fundamental,first_excited}
SECONDARY_ANALYSIS_SET = ring5{T_3_2}
CALIBRATION_SET         = T_max si naturellement disponible
```

```text
TARGET_POLICY                          = ELIGIBILITY_BASED
STRUCTURALLY_ELIGIBLE_CONTRACT_VERSION = 1
```

PRIMARY/SECONDARY sont des **rôles analytiques pré-enregistrés maintenant**, jamais une sélection post-hoc sur résultats — ils ne modifient en rien le contrat `STRUCTURALLY_ELIGIBLE` v1 (§15.1), qui reste l'unique critère d'éligibilité. `T_max` reste `CALIBRATION_ONLY` (§15.1 v1.4) ; aucune fenêtre plus profonde ne peut être demandée uniquement pour l'obtenir.

### 16.7 Unité d'analyse

```text
unité = une matrice C_TT_conn complète (diagonale + hors-diagonale)
        pour un groupe spectral admissible, à (geometry, J0, S) fixé

intra-S / inter-J0            -> réponse locale
inter-S / même J0              -> robustesse uniquement
multi-group / même geometry,J0,S -> cohérence inter-secteurs
```

Aucune métrique multi-groupe n'est définie.

### 16.8 Baseline Level 1C à `J0=1`

```text
LEVEL1B_REFERENCE_REUSE   = PARTIAL_ONLY
LEVEL1C_BASELINE_STRATEGY = RECOMPUTE_COMPLETE_BASELINE
```

Raison : les artefacts Level 1B historiques (`reference`, `J0=1`) ne contiennent pas `C_TT_conn(i,i)` (production ajoutée seulement en 1C-3a, après la clôture de Level 1B) — ils ne satisfont donc pas le critère 4 de `STRUCTURALLY_ELIGIBLE` v1 (matrice complète). La nouvelle baseline `J0=1` :

```text
- doit être produite avec le pipeline Level 1C courant ;
- contient la matrice C_TT_conn complète (diagonale + hors-diagonale) ;
- appartient techniquement au corpus de production de la future
  campagne J0 (un point sur l'axe J0 parmi d'autres, du point de vue de
  l'ingénierie) ;
- reste scientifiquement CALIBRATION_BASELINE (§16.3) -- jamais
  PRIMARY_INFERENCE_POINT -- ces deux affirmations ne se contredisent
  pas : elles portent sur des axes différents (catégorie de cible vs
  rôle de la valeur J0 elle-même sur l'axe de perturbation) ;
- ne fusionne jamais des valeurs historiques Level 1B avec les
  nouvelles valeurs Level 1C (cross-check uniquement, §16.9).
```

### 16.9 Non-régression Level 1B

```text
BASELINE_NON_REGRESSION_CHECK = REQUIRED
```

Pour les quantités communes entre la nouvelle baseline Level 1C et l'ancienne référence Level 1B (hors-diagonale), les valeurs historiques servent uniquement de `NON_REGRESSION_CHECK`, dans les tolérances numériques déjà gelées.

```text
NON_REGRESSION_CHECK != scientific J0 response test
```

Le premier valide la continuité du pipeline, jamais une propriété physique nouvelle.

### 16.10 Provenance baseline (exigences conceptuelles minimales)

```text
geometry ; S ; J0=1 ; identifiant de campagne/provenance Level 1C
distinct de level1b-reference-v1 ; repository commit ; version de
code/schéma ; fenêtre spectrale ; identité de groupe ; complete_multiplet ;
lower_bound_only=False ; twice_T ; multiplicité ; labels de symétrie ;
matrice C_TT_conn complète ; validation V23
```

Aucun identifiant concret n'est créé, aucun schéma n'est modifié par ce document.

### 16.11 Préflight baseline

```text
BASELINE_PREFLIGHT_REQUIRED   = YES
SPECTRAL_PREFLIGHT_REQUIRED   = YES
```

Le futur préflight doit inclure la baseline Level 1C elle-même (2 géométries × 2 `S`), pas seulement les points `J0!=1`. Aucune fenêtre numérique n'est choisie ici.

### 16.12 Tracking inter-`J0`

```text
J0_GROUP_TRACKING_RECOMMENDATION = HYBRID_ARCHITECTURE
```

Architecture conceptuelle : (1) ancre de sélection par catégorie de cible (`target_selection.py`, inchangé) ; (2) labels du sous-groupe commun (`matching.py`, primitives inchangées) ; (3) décomposition du parent sous le sous-groupe résiduel (`BRANCH_C1`, §16.13) ; (4) état `AMBIGUOUS` explicite. `matching.py` n'est jamais modifié.

```text
matching.py = appariement inter-S à Hamiltonien fixé
             != tracking inter-J0
```

**Sous-groupe commun** : lorsqu'une comparaison franchit la frontière `J0=1 ↔ J0!=1`, la translation est **exclue de l'identité de tracking** (transition `numeric -> not_applicable` structurellement attendue, jamais une discontinuité physique à elle seule) ; la réflexion reste un label spatial commun utilisable. Pour deux points `J0!=1` distincts, les règles usuelles de labels `not_applicable` (`matching.py`, inchangées) s'appliquent normalement.

**Taxonomie conceptuelle** (non codée, aucun schéma créé) :

```text
TRACKED_ONE_TO_ONE   -- multiplicité inchangée, labels du sous-groupe
                        commun cohérents
TRACKED_SPLIT_BRANCH -- multiplicité strictement réduite, cohérente
                        avec une sous-pièce du parent
AMBIGUOUS            -- collision de branches sous tous les labels
                        communs disponibles
DISCONTINUOUS        -- twice_T incompatible (jamais un simple
                        changement de multiplicité, jamais la
                        transition attendue translation numeric ->
                        not_applicable)
NOT_AVAILABLE        -- cible non sélectionnée à ce point J0
```

### 16.13 `BRANCH_C1` — décomposition du parent

```text
BRANCH_C1 = PARENT_SUBGROUP_DECOMPOSITION
statut    = DEFINED
```

Rôle : classification structurelle du multiplet parent sous le sous-groupe spatial résiduel commun, avec les primitives déjà existantes (`build_restricted_operator`, `compute_restricted_symmetry_label`) — aucune nouvelle diagonalisation du Hamiltonien complet. **BRANCH_C1 fournit des `candidate parent branch classes`, jamais automatiquement une `unique daughter identity`** — l'ambiguïté peut subsister (taxonomie `AMBIGUOUS` ci-dessus).

Projecteurs (objets conceptuels, aucune densité gelée) :

```text
P_parent   = projecteur sur le multiplet spectral parent à J0=1
P_r_global = projecteur de l'irrep/classe résiduelle r dans l'espace de
             Hilbert complet
Q_parent,r = projecteur sur V_parent ∩ V_r
           = P_parent P_r_global = P_r_global P_parent
             (lorsque [P_parent, P_r_global] = 0, ce qui est établi
             lorsque le générateur résiduel commute avec le
             Hamiltonien de référence)
```

### 16.14 SU(2) et réflexion

```text
[R, T^x] = 0
[R, T^y] = 0
[R, T^z] = 0
```

résultat structurel accepté : la réflexion agit spatialement (relabellage de site/lien) et laisse les indices de saveur strictement invariants (`specification.md` §11, covariance `U_A O_ij[P] U_A† = O_{A(i)A(j)}[A(P)]`, jamais de transformation des indices `alpha,beta`, y compris tout signe de Jordan-Wigner déjà absorbé par cette identité déjà validée V06/V07). Par conséquent, sous les conditions déjà établies :

```text
[P_r_global, T^a] = 0
[Q_parent,r, T^a] = 0
```

### 16.15 `AVERAGE_CASIMIR_RESOLVED` vs `FIXED_T_SUBSPACE`

Distinction critique, jamais confondue :

```text
AVERAGE_CASIMIR_RESOLVED = Tr(Psi† T² Psi)/d ≈ T(T+1)   -- disponible,
                                                            via compute_twice_T
FIXED_T_SUBSPACE          = Psi† T² Psi ≈ T(T+1) I_d      -- NON démontré
                                                            par le pipeline
                                                            courant
```

`compute_twice_T` ne vérifie que la trace normalisée (le premier), jamais la matrice complète (le second). Le premier n'implique jamais automatiquement le second.

### 16.16 Conséquence sur V23 sous projection spatiale

```text
SUBPROJECTED_V23_STATUS = PRESERVED_IF_FIXED_T
```

(jamais `PRESERVED_BY_SU2` sans condition). Démontré sans `FIXED_T_SUBSPACE` : si une densité uniforme hypothétique est construite sur `Q_parent,r`, elle est SU(2)-invariante, donc `<T_i^a>=0` pour tout site/composante, donc `sum_i C_ii + sum_{i!=j} C_ij = <T²>_sub`. Nécessite `FIXED_T_SUBSPACE` : la dernière égalité `<T²>_sub = T(T+1)` — sans elle, une projection spatiale commutant avec SU(2) peut repondérer différemment, selon la classe `r`, plusieurs secteurs `T` déjà mélangés dans le parent (le lemme de Schur interdit un mélange ENTRE secteurs `T` distincts, mais pas une repondération différente de chacun selon `r`).

### 16.17 Multiplicité des branches

La dimension brute du sous-espace de réflexion n'est jamais utilisée comme multiplicité spatiale. Si (et seulement si) `FIXED_T_SUBSPACE` est démontré pour le parent considéré :

```text
V_parent ≅ M_parent ⊗ V_T,   dim(V_T) = 2T+1
m_r_spatial = dim(Q_parent,r) / (2T+1)
```

L'ambiguïté pertinente concerne exclusivement plusieurs copies indiscernables dans l'espace de multiplicité `M_parent` sous l'ensemble complet des labels communs — jamais `dim(Q_parent,r) > 1` à elle seule.

```text
REPEATED_IRREP_POLICY = MORE_STRUCTURE_REQUIRED
```

par défaut, tant que `FIXED_T_SUBSPACE`/copie unique n'est pas démontré empiriquement (jamais présumé).

### 16.18 `BRANCH_C2`

```text
BRANCH_C2                      = SUBPROJECTED_PARENT_EXPECTATION
BRANCH_C2_CONTRACT              = NOT_DEFINED
SUBPROJECTED_CANONICAL_DENSITY = NEW_ASSUMPTION
```

Aucune formule normative, aucune primitive, aucun observable n'est créé par ce document.

### 16.19 Politique des branches scindées — première campagne

```text
SPLIT_BRANCH_RESPONSE_POLICY = STRUCTURAL_ONLY
DELTA_CTT_SPLIT_BRANCH        = BLOCKED
```

```text
TRACKED_ONE_TO_ONE   -> Delta_C_TT utilisable comme quantité dérivée
TRACKED_SPLIT_BRANCH -> suivi/classification structurelle uniquement,
                        aucun Delta_C_TT quantitatif
```

tant que `BRANCH_C2` n'est pas conçu, audité et gelé séparément.

### 16.20 `Delta C_TT`

```text
Delta C_ij(J0,S) = C_ij(J0,S) - C_ij(J0=1,S)
```

conservée comme quantité dérivée potentielle, uniquement lorsque la correspondance physique est admissible (`TRACKED_ONE_TO_ONE`, §16.19) — aucune nouvelle observable normative, aucun seuil défini.

### 16.21 Test incident / non-incident

```text
NONLOCAL_RESPONSE_TEST = ADMISSIBLE
```

uniquement avec la partition binaire `incident_to_defect` / `non_incident_to_defect` — aucune subdivision graduée par distance combinatoire comme vérité géométrique. Ce test ne démontre qu'une propagation relationnelle au-delà des entrées directement incidentes au défaut, jamais une géométrie.

### 16.22 Protocole blind et invariance de relabellage

```text
BLIND_PROTOCOL              = DEFINED
BLIND_DEFECT_LOCALIZATION   = CONDITIONAL
RELABEL_TEST_POLICY          = EXHAUSTIVE
```

Entrée aveugle : matrice relationnelle admissible, sans identité du site perturbé. Sortie conceptuelle : site/orbite candidat ou `NO_UNIQUE_DEFECT`. Scoring futur (non codé) : `UNIQUE_CORRECT`/`UNIQUE_INCORRECT`/`AMBIGUOUS`/`NO_SIGNAL`. Énumération exhaustive des permutations pour les géométries actuelles (`triangle`: `3!`, `ring5`: `5!`) — les labels de sites ne deviennent jamais des coordonnées physiques.

### 16.23 Seuils

```text
PHYSICAL_RESPONSE_THRESHOLD = OPEN
```

```text
NUMERICAL_EQUALITY_TOLERANCE != PHYSICAL_RESPONSE_THRESHOLD
```

Les tolérances `1e-8` déjà gelées peuvent servir à des validations numériques déjà établies (V23, matching), jamais à déclarer automatiquement une réponse physiquement significative.

### 16.24 Robustesse inter-S, ordre de campagne, gestion des échecs

```text
INTER_S_RESPONSE_ROBUSTNESS = PARTIALLY_DEFINED
```

Admissible dès maintenant : comparaison élément-par-élément de `C_TT_conn` (réutilise `robustness.py` inchangé) ; signe de `Delta_C_TT` lorsqu'il est admissible (§16.19/§16.20). Restent futurs : robustesse d'un ranking global, robustesse blind, robustesse d'une reconstruction géométrique/d'un embedding — aucun nouveau seuil.

```text
RUN_ORDER_POLICY = IRRELEVANT_BUT_FIXED
```

Calcul déterministe, aucune dérive instrumentale — mais la grille doit être gelée avant toute lecture de résultat, aucune adaptation silencieuse après résultat partiel.

Gestion conceptuelle des échecs (aucun schéma créé) :

```text
cible absente/incomplète                     -> GROUP_UNEVALUABLE
tracking inter-J0 ambigu/discontinu            -> comparaison inter-J0
                                                   concernée UNEVALUABLE
matching inter-S absent/ambigu                 -> ROBUSTNESS_UNEVALUABLE
échec V23/intégrité                            -> CASE_INVALID
échec ressource                                -> CASE_INVALID
échec isolé != CAMPAIGN_INVALID automatiquement
```

Aucun rerun adaptatif silencieux.

### 16.25 Rôles géométriques et gate de reconstruction

```text
triangle -> contrôle relationnel minimal
ring5     -> support principal plus riche pour tester une réponse
             relationnelle structurée
```

`ring5` n'est jamais qualifié de « géométrie émergente démontrée ».

```text
GEOMETRY_RECONSTRUCTION_GATE = CONDITIONAL
```

Conditions nécessaires (non suffisantes) avant tout futur lot corrélateur→distance : réponse effective dans au moins un groupe éligible ; réponse sur au moins une paire non incidente au défaut ; tracking non ambigu pour la revendication concernée ; covariance de relabellage exhaustive ; robustesse inter-S minimale ; absence de fermeture analytique `DOF=0` ; idéalement cohérence multi-groupe. Aucune transformation corrélateur→distance n'est définie par ce document.

### 16.26 Statuts de préparation et points ouverts après 1C-6c

```text
1C6A_READ_ONLY_DESIGN                = ACCEPTÉ DÉFINITIVEMENT
1C6B_READ_ONLY_AUDIT                 = ACCEPTÉ DÉFINITIVEMENT
1C6B_READY_FOR_PREREGISTRATION       = YES
J0_DESIGN_READY_FOR_PREREGISTRATION  = CONDITIONAL
J0_CAMPAIGN_READY                    = NO
```

Points explicitement encore ouverts après 1C-6c :

```text
- valeur numérique de δ ;
- préflight spectral/ressources (y compris pour la baseline J0=1) ;
- fenêtres spectrales futures ;
- PHYSICAL_RESPONSE_THRESHOLD ;
- contrôle FIXED_T_SUBSPACE, si un jour nécessaire à BRANCH_C2 ;
- BRANCH_C2 lui-même, volontairement différé.
```

`BRANCH_C2` n'est pas un blocage pour la première campagne : `SPLIT_BRANCH_RESPONSE_POLICY = STRUCTURAL_ONLY` (§16.19) permet de procéder sans lui pour tout groupe `TRACKED_ONE_TO_ONE`.

## 17. Gel de `δ`, de la grille `J0` et contrat de préflight (1C-6d/1C-6e, gelé)

**[GELÉ]** Pré-enregistrement documentaire des décisions acceptées définitivement lors de l'audit en lecture seule **1C-6d** (choix scientifique de `δ`, design du préflight spectral/resources, contrat d'aveuglement, politique de gel avant préflight). **Ce document ne fixe encore AUCUNE fenêtre spectrale numérique, AUCUN outil, AUCUNE exécution** — voir §17.16 pour la liste exhaustive de ce qui reste ouvert.

### 17.1 Gel numérique de `δ`

```text
DELTA_SELECTION_POLICY = FIX_BEFORE_PREFLIGHT
DELTA_RECOMMENDATION   = 0.25
J0_GRID_READY_TO_FREEZE = YES

DELTA_J0        = 0.25
J0_GRID         = {0.5, 0.75, 1.0, 1.25, 1.5}
J0_GRID_STATUS  = FROZEN
```

`δ = OPEN` décrit uniquement l'état antérieur à ce lot (§16.4) — pour la campagne en cours de conception, `δ` n'est plus ouvert.

### 17.2 Justification du gel

```text
PRIMARY   : grille symétrique autour de J0=1 ; deux amplitudes contrôlées
            |delta_J| = 0.25 et 0.50 ; tous les J0 de la grille restent
            strictement positifs ; aucun point ne supprime ni n'inverse
            le signe du terme local ; amplitude suffisamment distincte
            entre points internes et externes ; choix fait AVANT toute
            nouvelle donnée scientifique
SECONDARY : J0=1.5 coïncide avec l'ancre historique externe USEFUL_ANCHOR
```

**Aucune ancienne valeur `C_TT_conn`/`Delta_C_TT` n'a été utilisée pour choisir `δ`.** Le terme « perturbatif » n'est jamais employé pour qualifier `±25%`/`±50%` (aucune preuve d'un régime perturbatif au sens formel n'est établie ni requise pour ce choix).

### 17.3 Ordre méthodologique gelé

```text
1. choisir δ ;
2. faire accepter la décision (gouvernance) ;
3. geler/pré-enregistrer la grille (ce document) ;
4. exécuter le préflight spectral/resources de CETTE grille figée ;
5. décider si la grille est structurellement exécutable ;
6. lancer une campagne seulement si le préflight passe pour tous les cas requis.
```

Le préflight **teste** une grille déjà gelée — il ne peut jamais **choisir**, **confirmer**, **optimiser**, ni **réviser silencieusement** `δ`.

### 17.4 Statuts distincts

```text
GRID_READY_TO_FREEZE   = YES        -- δ scientifiquement motivé, prêt à
                                        geler, indépendant du préflight
J0_GRID_STATUS          = FROZEN     -- la grille est désormais une
                                        décision gelée
GRID_PREFLIGHT_PASSED   = NOT_EVALUATED -- statut futur distinct, obtenu
                                        uniquement après exécution du
                                        préflight sur la grille déjà
                                        gelée ; jamais confondu avec les
                                        deux précédents
```

### 17.5 Politique en cas d'échec du préflight

```text
préflight échoue sur au moins un cas REQUIRED
  -> J0_CAMPAIGN_READY = NO
  -> aucun lancement de campagne
  -> aucun ajustement silencieux de δ, de fenêtre, ou de cible
  -> ouverture éventuelle d'un NOUVEAU lot de redesign, distinct
  -> toute nouvelle valeur de δ dans ce futur lot doit être rejustifiée
     sur les mêmes critères (jamais sur le résultat du préflight
     échoué), re-pré-enregistrée, et gelée avant tout nouveau préflight
```

Un échec du préflight n'annule jamais rétroactivement la validité du gel initial de `δ=0.25` — il clôture seulement cette tentative de campagne.

### 17.6 Ensemble complet de cas

```text
PREFLIGHT_CASE_SET = FULL_20_CASE_GRID

geometry ∈ {triangle, ring5}
S ∈ {2,3}
J0 ∈ {0.5,0.75,1.0,1.25,1.5}

2 × 2 × 5 = 20 cas, J0=1 (baseline) inclus sans exemption
```

### 17.7 Cibles requises

```text
triangle : REQUIRED {fundamental, first_excited} ; OPTIONAL/CALIBRATION {T_max}
ring5    : REQUIRED {fundamental, first_excited, T_3_2} ; OPTIONAL/CALIBRATION {T_max}
```

`T_max` reste `CALIBRATION_ONLY` — aucune fenêtre plus profonde n'est jamais demandée uniquement pour l'obtenir.

### 17.8 Complétude d'une cible et marge spectrale

```text
required target valide si : SELECTED, complete_multiplet,
  lower_bound_only=False, end_index_exclusive < candidate_window

SPECTRAL_MARGIN_POLICY = REUSE_1C4A
  -- après le dernier groupe REQUIRED sélectionné, au moins un groupe
     complet supplémentaire avec start_index >= last_required.
     end_index_exclusive et lower_bound_only=False ; aucun seuil
     d'écart énergétique
```

Réutilisation explicite, sans modification, du contrat déjà accepté en 1C-4a.

### 17.9 Fenêtres — concepts uniquement

```text
candidate_window
exploratory_window
```

**Aucune valeur numérique de fenêtre n'est fixée par ce document.** Les anciennes valeurs 1C-4a (`triangle`: 16/32 ; `ring5`: 24/48) restent `HISTORICAL_REFERENCE_ONLY` — jamais une garantie pour les nouveaux points de la grille `J0`.

**[HISTORIQUE — statut au moment de 1C-6d/1C-6e]** `FULL_DENSE_EXPLORATORY_WINDOW = CANDIDATE_DESIGN` : option de conception à évaluer, non gelée à ce stade. Dans le chemin dense (`dimension <= 2000`, cf. §17.14), `np.linalg.eigh` calcule déjà le spectre complet avant toute rétention partielle — fixer `exploratory_window = dimension` distinguerait sans ambiguïté une cible réellement absente du spectre d'une cible seulement hors d'une fenêtre tronquée, sans coût de diagonalisation supplémentaire.

**[ÉTAT COURANT — gelé par 1C-6f/1C-6g, voir §18]** `FULL_DENSE_EXPLORATORY_WINDOW = FROZEN` : le spectre exploratoire du préflight est désormais le spectre dense complet pour tous les cas actuels, et `production_window` est dérivée mécaniquement (§18.5–18.6) plutôt que devinée à l'avance.

### 17.10 Contrat d'aveuglement du préflight

```text
PREFLIGHT_BLINDNESS_CONTRACT = DEFINED
```

```text
AUTORISÉ pendant le préflight : dimension de Hilbert ; ordre
  énergétique/index spectral ; multiplicité ; twice_T ; translation_label ;
  reflection_label ; complete_multiplet ; lower_bound_only ; V23
  applicable/is_valid en tant que BOOLÉEN uniquement ; dispatch
  dense/sparse ; statut d'échec ressource

INTERDIT pour modifier δ/grille/target-set/fenêtre : valeurs numériques
  C_TT_conn (diagonale ou hors-diagonale) ; Delta_C_TT ; réponse rho_QQ ;
  réponse G ; amplitude de réponse incident/non-incident ; résultat de
  localisation blind ; toute reconstruction géométrique/distance/
  embedding/fit/courbure
```

### 17.11 V23 pendant le préflight

```text
PREFLIGHT_V23_POLICY = VALIDATE_WITHOUT_EXPOSING_VALUES
```

Le préflight peut calculer ce qui est nécessaire pour obtenir `applicable`/`is_valid`, mais sa surface de rapport destinée au choix de fenêtre/faisabilité ne doit jamais exposer `measured`/`expected`/`residual`/les valeurs diagonales ou hors-diagonale de `C_TT_conn`. **Ceci implique une adaptation future de l'outil `jbreak_spectral_preflight.py` existant** (qui sérialise actuellement ces valeurs numériques dans `TargetReport.v23`) — aucune implémentation n'est faite dans ce lot.

### 17.12 Baseline `J0=1` et non-régression

```text
LEVEL1C_BASELINE_STRATEGY = RECOMPUTE_COMPLETE_BASELINE
J0_EQ_1_ROLE               = CALIBRATION_BASELINE
NON_REGRESSION_TIMING      = FINAL_PRODUCTION
```

Le préflight sur le cas `J0=1` reste exploratoire/structurel ; la baseline normative finale est produite séparément avec sa provenance complète (§16.8/§16.10). `BASELINE_NON_REGRESSION_CHECK = REQUIRED` (rappel, inchangé) ne s'applique qu'entre la baseline finale Level 1C et la référence historique Level 1B, jamais pour choisir `δ`/fenêtre.

### 17.13 `FIXED_T_SUBSPACE` et `BRANCH_C1` pendant le préflight

```text
FIXED_T_REQUIRED_FOR_FIRST_CAMPAIGN = NO
```

(`SPLIT_BRANCH_RESPONSE_POLICY=STRUCTURAL_ONLY`, `DELTA_CTT_SPLIT_BRANCH=BLOCKED`, `BRANCH_C2_CONTRACT=NOT_DEFINED`, tous inchangés — `FIXED_T_SUBSPACE` reste hors périmètre de la première campagne). Le préflight vérifie seulement la faisabilité structurelle de `BRANCH_C1` (réflexion restreinte stable et unitaire dans la tolérance déjà gelée) — jamais une analyse `BRANCH_C2`.

### 17.14 Ressources

```text
Hilbert dimension : triangle S=2/S=3 = 88/128 ; ring5 S=2/S=3 = 1000/1504
  (dépend uniquement de geometry+S, indépendante de J0)
eigensolver dispatch : dimension <= 2000 -> chemin dense (np.linalg.eigh)
  pour les 20 cas -- aucun chemin sparse déclenché
dimension² × 16 = estimation de stockage de la matrice complexe128,
  jamais confondue avec le pic mémoire réel (espace de travail LAPACK
  supplémentaire non quantifié)
```

Aucune estimation de temps.

### 17.15 Statuts de préflight, priorité, frontière avec l'analyse finale

```text
WINDOW_SUFFICIENT / WINDOW_INSUFFICIENT / WINDOW_INCONCLUSIVE
TARGET_NOT_IDENTIFIABLE
RESOURCE_FEASIBLE / RESOURCE_BLOCKING
TRACKING_STRUCTURALLY_AMBIGUOUS
```

```text
Priorité : 1. INSUFFICIENT/NOT_IDENTIFIABLE  2. INCONCLUSIVE/
STRUCTURALLY_AMBIGUOUS  3. SUFFICIENT -- aucune heuristique post-hoc
```

```text
PRÉFLIGHT      -> vérifie que le design permet une analyse structurée
FINAL ANALYSIS -> attribue TRACKED_ONE_TO_ONE / TRACKED_SPLIT_BRANCH /
                  AMBIGUOUS / DISCONTINUOUS / NOT_AVAILABLE
```

`TRACKING_STRUCTURALLY_AMBIGUOUS` est un signal de faisabilité au niveau préflight, jamais un verdict final de tracking scientifique.

**Politique d'élargissement** : aucun élargissement automatique après inspection de la physique. Fenêtre plus profonde uniquement pour la complétude d'une cible `REQUIRED` + la marge spectrale (§17.8) — jamais pour `T_max`, un `C_TT` plus intéressant, un `Delta_C_TT` plus grand, une branche plus intéressante, ou un meilleur score blind.

```text
PREFLIGHT_GLOBAL_POLICY = ALL_REQUIRED_CASES
```

Au moins un cas `REQUIRED` bloquant ⇒ préflight global `FAIL` ⇒ campagne non lancée. Aucune campagne partielle destinée à sauver une sous-partie jugée intéressante.

**Symétrie `±δ` indivisible** : `±0.25` et `±0.50` sont des paires de design indivisibles pour toute revendication symétrique autour de `J0=1`. Si un seul côté d'une paire échoue structurellement, la paire complète ne peut plus soutenir une revendication symétrique — jamais conservée post-hoc uniquement du côté utilisable.

**Ordre déterministe** (auditabilité uniquement, `RUN_ORDER_POLICY=IRRELEVANT_BUT_FIXED` inchangé) :

```text
triangle { S=2 { J0=0.5,0.75,1.0,1.25,1.5 } ; S=3 { J0=0.5,0.75,1.0,1.25,1.5 } }
ring5    { S=2 { J0=0.5,0.75,1.0,1.25,1.5 } ; S=3 { J0=0.5,0.75,1.0,1.25,1.5 } }
```

### 17.16 Statuts de préparation et points ouverts après 1C-6e

```text
1C6D_READ_ONLY_DESIGN   = ACCEPTÉ DÉFINITIVEMENT
J0_GRID_STATUS           = FROZEN
GRID_PREFLIGHT_PASSED    = NOT_EVALUATED
PREFLIGHT_DESIGN_READY   = CONDITIONAL
J0_CAMPAIGN_READY        = NO
```

Points explicitement encore ouverts après 1C-6e :

```text
- candidate_window numérique ;
- exploratory_window numérique ;
- choix éventuel de FULL_DENSE_EXPLORATORY_WINDOW (§17.9) ;
- adaptation de la sortie V23 de l'outil existant pour préserver
  l'aveuglement (§17.11) ;
- représentation exacte des statuts de préflight (§17.15) ;
- implémentation effective de l'outil de préflight J0×S ;
- exécution des 20 cas ;
- PHYSICAL_RESPONSE_THRESHOLD (toujours OPEN) ;
- la campagne normative finale elle-même.
```

## 18. Design final des fenêtres et firewall du préflight aveugle (1C-6f/1C-6g, gelé)

**[GELÉ]** Pré-enregistrement documentaire des décisions acceptées définitivement lors de l'audit en lecture seule **1C-6f** (design final des fenêtres et architecture du préflight aveugle), après un correctif portant sur un seul point : `PRODUCTION_WINDOW_RULE` (`B → A`), corrigé après audit du comportement réel de `lower_bound_only` dans `cosmobox.level0.degeneracy`. **Ce document ne fixe encore AUCUNE valeur numérique de fenêtre, AUCUN outil, AUCUNE exécution.**

### 18.1 Spectre exploratoire complet

```text
FULL_DENSE_EXPLORATORY_WINDOW = FROZEN
exploratory_window            = full_spectrum_dimension
```

pour tous les cas dont le dispatch est dense (`dimension <= max_dense_dimension=2000`, gelé Level0). Dimensions actuelles : `triangle S=2/S=3 = 88/128` ; `ring5 S=2/S=3 = 1000/1504` — les 20 cas de la grille `J0×S` sont tous dans ce chemin.

`np.linalg.eigh` calcule déjà la totalité du spectre en un seul appel avant toute troncature de rétention — **aucune seconde diagonalisation n'est nécessaire pour approfondir la fenêtre dans le préflight dense**. Ceci n'est cependant jamais qualifié de surcoût nul : la rétention complète des eigenpairs augmente le travail aval (`_eigenpair_diagnostic` par eigenpair, construction des `SpectralGroupState`, vérifications de faisabilité `BRANCH_C1`) — jamais benchmarké, jamais garanti quant au pic mémoire réel (distinct du plancher de stockage `dimension²×16`, déjà établi §17.14).

### 18.2 Distinction exploratoire / production

```text
exploratory_window != production_window
```

Le préflight inspecte structurellement le spectre complet ; la production normative ultérieure ne conserve que la fenêtre dérivée par l'algorithme gelé (§18.5–18.6). Le spectre exploratoire complet ne devient jamais, par lui-même, un corpus normatif (`PREFLIGHT_ARTIFACT_REUSE_FOR_NORMATIVE = NO`, §18.14).

### 18.3 Politique de sélection et de gel de fenêtre

```text
WINDOW_SELECTION_POLICY   = FULL_SPECTRUM_DERIVED_PRODUCTION_WINDOW
NUMERIC_WINDOW_FREEZE_POLICY = DERIVE_BY_PREREGISTERED_ALGORITHM
```

Aucune fenêtre numérique n'est devinée avant préflight. L'objet gelé avant exécution est l'**algorithme** de sélection de fenêtre, jamais un nombre fixe (`triangle=16`, `ring5=24`, etc.) — les anciennes fenêtres 1C-4a restent `HISTORICAL_REFERENCE_ONLY`, jamais une garantie pour la nouvelle grille.

### 18.4 Cibles requises et déduplication

Cibles inchangées (§16.6/§17.7) : `triangle` REQUIRED `{fundamental, first_excited}` ; `ring5` REQUIRED `{fundamental, first_excited, T_3_2}` ; `T_max` `CALIBRATION_ONLY` — n'entre jamais dans `last_required_end`, `production_window`, ni le verdict global du préflight.

```text
si plusieurs target IDs sélectionnent le même groupe spectral,
  ce groupe compte UNE SEULE FOIS

last_required_end = max(end_index_exclusive des groupes REQUIRED uniques)
```

### 18.5 Politique de marge

```text
SPECTRAL_MARGIN_POLICY = REUSE_1C4A
```

**Interprétation désormais explicite, jamais réinterprétée après coup** : la marge est un critère du **spectre exploratoire de préflight** — le préflight complet doit démontrer l'existence, après `last_required_end`, d'au moins un groupe complet supplémentaire (`start_index >= last_required_end`, `lower_bound_only=False`) — **jamais** une obligation de contenu de la production normative finale. Ce groupe de marge est uniquement un témoin structurel de complétude du dernier `REQUIRED` : il n'est ni une cible scientifique, ni un objet de matching, ni un objet d'analyse `C_TT_conn`. Rien n'exige qu'il reste lui-même intégralement conservé dans la production.

### 18.6 Règle finale de `production_window`

```text
PRODUCTION_WINDOW_RULE = A

production_window (cas général)                      = last_required_end + 1
production_window (si last_required_end == full_spectrum_dimension) = full_spectrum_dimension
```

Justification : un état spectral distinct après le dernier groupe `REQUIRED` suffit à établir, par construction séquentielle de `analyze_spectral_degeneracies` (chaque frontière décidée uniquement par comparaison à l'ancre du groupe courant, jamais par anticipation), que ce groupe n'est plus terminal, donc `lower_bound_only=False` dans la production tronquée à cette valeur. Le groupe de marge complet observé lors du préflight n'a pas besoin d'être intégralement conservé dans la production.

### 18.7 Portée des fenêtres

```text
PRODUCTION_WINDOW_SCOPE = PER_CASE
```

`production_window(geometry,S,J0)` est déterminée indépendamment pour chacun des 20 cas — aucune fenêtre commune imposée inter-`J0`, inter-`S`, ou inter-géométrie, sauf nécessité future explicitement démontrée. Le matching inter-S déjà gelé (`matching.py::SpectralGroupMatchKey`) ne porte aucun champ de fenêtre/dimension — aucune égalité de fenêtre n'est requise pour lui.

### 18.8 Symétrie `±δ` et inter-S

Des fenêtres numériques différentes entre `J0=1-x` et `J0=1+x`, ou entre `S=2` et `S=3`, ne rompent pas la symétrie scientifique de la grille si elles sont obtenues par exactement la même règle mécanique (§18.6). La politique gelée de paire indivisible (§17.15) porte sur la **faisabilité** de chaque côté de la paire, jamais sur l'égalité numérique de leurs fenêtres. `matching.py` n'est jamais modifié.

### 18.9 Cible absente / non identifiable

```text
TARGET_NOT_IDENTIFIABLE = la cible ne peut pas être identifiée de
  manière admissible par la règle de sélection sur le spectre complet
```

Jamais formulé comme « cible physiquement absente » sans preuve supplémentaire. Deux sous-causes conceptuelles distinctes (aucun schéma créé) :

```text
TARGET_ABSENT_IN_FULL_SPECTRUM -- aucun groupe à label résolu ne
                                   correspond
TARGET_SELECTION_AMBIGUOUS      -- ambiguïté de sélection, ou twice_T
                                   non résolu empêchant une conclusion
                                   unique
```

`fundamental` (rang 0) est toujours sélectionnable dès qu'au moins un groupe existe. `first_excited` (rang 1) échoue uniquement si moins de deux groupes existent dans le spectre complet — un fait structurel, jamais un artefact de fenêtre. `T_3_2` (`selection_kind=flavor_label`, `target_twice_T=3`, `selection_within_label=lowest_representative_energy`) et sa politique de désambiguïsation restent inchangés — une égalité non résolue dans la tolérance de dégénérescence reste `AMBIGUOUS`, jamais brisée par ordre d'itération ou par rang spectral.

### 18.10 Contrat d'aveuglement — architecture

```text
PREFLIGHT_INFORMATION_FIREWALL = DEFINED
```

Deux couches :

```text
INTERNAL_PREFLIGHT_COMPUTATION -- calcule tout ce qui est nécessaire
                                   (y compris C_TT_conn/V23)
PUBLIC_PREFLIGHT_REPORT         -- expose exclusivement la whitelist
                                   structurelle ci-dessous
```

**Whitelist publique** : `geometry`, `S`, `J0`, `full_spectrum_dimension`, indices/ordre spectral, `start_index`/`end_index_exclusive` de groupe, `multiplicity`, `twice_T`, `translation_label`, `reflection_label`, `reflection_restriction_valid`, `complete_multiplet`, `lower_bound_only`, statut de sélection de cible, rôle requis/non-requis, `V23 applicable`/`V23 is_valid` (booléens uniquement), `exploratory_window`, `production_window`, `last_required_end`, `margin_group_start`/`margin_group_end`, dispatch de l'eigensolver, statut de ressource, statut de préflight, `TRACKING_PREFLIGHT_STATUS`. Aucune donnée physique numérique interdite (§18.12) ne figure dans cette liste.

```text
ENERGY_PUBLIC_POLICY = INDICES_ONLY
```

Le rapport public n'expose jamais `eigenvalue`, `representative_energy`, `min_energy`/`max_energy`, ni aucun écart d'énergie numérique — ces valeurs peuvent être utilisées **en interne** par une primitive de sélection déjà gelée (ex. `lowest_representative_energy`) mais ne traversent jamais le firewall.

### 18.11 V23

```text
PREFLIGHT_V23_POLICY = VALIDATE_WITHOUT_EXPOSING_VALUES
```

Architecture : calcul `C_TT_conn` complet en mémoire → validation `V23` interne (`local_observables.validate_flavor_total_sum`, inchangé) → sortie publique limitée à `applicable`/`is_valid`. Interdiction explicite d'exposer `measured`/`expected`/`residual`/valeurs diagonales ou hors-diagonale de `C_TT_conn` — implique une adaptation future de l'outil `jbreak_spectral_preflight.py` existant (qui les sérialise actuellement), non implémentée dans ce lot.

### 18.12 Surfaces de fuite couvertes

Le firewall couvre **toute** surface consultable par l'opérateur, pas seulement le JSON final : `stdout`/`stderr`, journaux, exceptions (capturées/assainies — un message d'exception brut de `validate_flavor_total_sum` peut intégrer `measured`/`expected`/`residual`), `repr()`/`str()` par défaut d'un objet interne portant des valeurs physiques, fichiers temporaires de débogage. Données interdites, quelle que soit la surface : `C_TT_conn` numérique, `Delta_C_TT`, réponse `rho_QQ`/`G`, amplitude de réponse incident/non-incident, résultat de localisation blind, reconstruction géométrique/distance/embedding/fit/courbure, énergies numériques. Aucune de ces données ne peut jamais modifier `δ`, la grille `J0`, l'ensemble des cibles, ou l'algorithme de fenêtre.

### 18.13 `BRANCH_C1` — rôle minimal et exigence `R²=I`

Exposition minimale : `reflection_label` + `reflection_restriction_valid` (booléen : stabilité + unitarité déjà gelées) — jamais la décomposition détaillée en valeurs propres/parités (qui appartient à la classification finale, hors périmètre du préflight). `BRANCH_C2` n'est jamais exécuté.

**Exigence documentée pour le futur lot d'implémentation, non résolue ici** : la réflexion restreinte utilisée doit satisfaire `R²=I` dans une tolérance numérique **déjà gelée et réutilisée**, jamais une tolérance nouvellement inventée pour ce besoin — si aucune tolérance déjà gelée n'est directement applicable, un audit séparé devra être ouvert avant toute exploitation scientifique de la réflexion dans le nouveau préflight. Ceci n'est pas transformé en décision scientifique silencieuse par ce document.

### 18.14 Tracking préflight, politique globale, réutilisation normative

```text
TRACKING_PREFLIGHT_STATUS ∈ {FEASIBLE, STRUCTURALLY_AMBIGUOUS, NOT_EVALUATED}
```

Vocabulaire exclusif au préflight — jamais confondu avec `TRACKED_ONE_TO_ONE`/`TRACKED_SPLIT_BRANCH`/`AMBIGUOUS`/`DISCONTINUOUS`/`NOT_AVAILABLE` (analyse finale).

```text
PREFLIGHT_GLOBAL_POLICY = ALL_REQUIRED_CASES
```

Un seul cas `REQUIRED` bloquant ⇒ `GLOBAL_PREFLIGHT=FAIL` ⇒ `J0_CAMPAIGN_READY=NO` — aucune réduction post-hoc de la grille.

```text
PREFLIGHT_ARTIFACT_REUSE_FOR_NORMATIVE = NO
```

Provenance différente, rôle exploratoire/structurel, rapport aveuglé, `production_window` dérivée après le préflight — la campagne normative doit être réexécutée sous le contrat final gelé (cohérent avec la distinction préflight/baseline déjà établie, §16.8/§17.12).

`FULL_20_CASE_GRID` ⇒ 20 diagonalisations exploratoires conceptuelles, une par cas ; aucune re-diagonalisation nécessaire pour approfondir la fenêtre dans le chemin dense (§18.1). Aucune durée promise.

### 18.15 Architecture future et tests futurs (non implémentés)

```text
scripts/level1c_preflight/j0_grid_preflight.py
  -- orchestration des 20 cas ; spectre dense complet ; sélection de
     cible ; dérivation de production_window ; contrôle de marge ; V23
     interne ; firewall ; agrégation ALL_REQUIRED_CASES ; ordre
     déterministe ; rapport public structurel

src/cosmobox/level1/ -- aucune nouvelle primitive scientifique requise
  à ce stade ; réutilisation maximale de l'existant
```

Interdictions : ne jamais modifier `matching.py` ; ne jamais créer de nouvelle observable ; ne jamais modifier le manifeste Level 1B.

Tests minimaux requis avant toute exécution (futur lot, non exécutés ici) : grille `J0` gelée exacte ; exactement 20 cas ; ordre déterministe ; `exploratory_window=dimension` ; sélection des cibles `REQUIRED` ; déduplication des groupes ; `last_required_end` ; `production_window=last_required_end+1` avec repli `=dimension` ; présence du groupe de marge dans le spectre exploratoire ; `T_max` non bloquant ; portée `PER_CASE` ; fenêtres `±δ`/inter-S autorisées à différer ; `V23` bool-only public ; absence de fuite `C_TT`/énergie ; exceptions/logs assainis ; `reflection_restriction_valid` ; `R²=I` ; `TRACKING_PREFLIGHT_STATUS` ; priorité des statuts ; un cas `REQUIRED` bloquant → échec global ; aucun changement `matching.py` ; aucun lancement de campagne normative.

### 18.16 Statuts de préparation et points ouverts après 1C-6g

```text
1C6F_READ_ONLY_DESIGN                  = ACCEPTÉ DÉFINITIVEMENT
FULL_DENSE_EXPLORATORY_WINDOW          = FROZEN
WINDOW_SELECTION_POLICY                = FULL_SPECTRUM_DERIVED_PRODUCTION_WINDOW
PRODUCTION_WINDOW_RULE                 = A
PRODUCTION_WINDOW_SCOPE                = PER_CASE
NUMERIC_WINDOW_FREEZE_POLICY           = DERIVE_BY_PREREGISTERED_ALGORITHM
ENERGY_PUBLIC_POLICY                   = INDICES_ONLY
PREFLIGHT_INFORMATION_FIREWALL         = DEFINED
PREFLIGHT_ARTIFACT_REUSE_FOR_NORMATIVE = NO
PREFLIGHT_IMPLEMENTATION_READY         = CONDITIONAL
GRID_PREFLIGHT_PASSED                  = NOT_EVALUATED
J0_CAMPAIGN_READY                      = NO
```

Points explicitement encore ouverts après 1C-6g :

```text
- implémentation réelle du préflight ;
- représentation exacte du rapport public ;
- sanitization concrète des erreurs/logs ;
- vérification/test R²=I, et éventuel audit séparé de tolérance R²
  si aucune tolérance déjà gelée n'est directement applicable ;
- exécution des 20 cas ;
- production des valeurs numériques de production_window ;
- GRID_PREFLIGHT_PASSED ;
- PHYSICAL_RESPONSE_THRESHOLD (toujours OPEN) ;
- la campagne normative Level 1C elle-même.
```
