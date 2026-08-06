# Dossier de conception d’implémentation — niveau 1B

Statut : **brouillon — proposition d’implémentation soumise à validation**

Destinataire principal : **Claude Code**

Supervision : **Lionel ORCIL**

Responsabilité scientifique et conceptuelle : **ChatGPT**

Audit scientifique externe : **Claude Fable, exceptionnellement et uniquement sur demande explicite**

Ce document traduit les contrats scientifiques gelés du niveau 1B en lots d’implémentation. Il ne modifie aucune définition de :

- `docs/level1-specification.md` ;
- `docs/decisions.md`, notamment D012 et D013 ;
- `experiments/LEVEL1B-preregistered-manifest.md` ;
- `docs/level1-validation-plan.md` ;
- `schemas/level1-correlators-v1.schema.json`.

En cas de divergence, la hiérarchie définie dans `docs/documentation-governance.md` s’applique. Claude Code ne doit jamais résoudre une divergence scientifique par une décision locale dans le code.

---

## 1. Répartition des responsabilités

### 1.1 ChatGPT

ChatGPT fixe et contrôle :

- les définitions physiques ;
- les conventions d’orientation ;
- les observables ;
- les invariants ;
- les cas structurellement attendus ;
- les critères scientifiques d’acceptation ;
- l’interprétation des résultats.

ChatGPT ne prescrit pas inutilement les détails internes de programmation lorsque plusieurs solutions respectent exactement les contrats scientifiques.

### 1.2 Claude Code

Claude Code prend en charge :

- l’architecture logicielle détaillée ;
- les structures de données ;
- les signatures finales des API internes ;
- l’implémentation ;
- les tests ;
- le profilage ;
- les optimisations ;
- la documentation développeur ;
- les commits techniques.

Claude Code peut proposer une amélioration de conception, mais ne doit pas modifier silencieusement une convention scientifique gelée.

### 1.3 Supervision

Lionel ORCIL :

- valide le passage d’un lot au suivant ;
- arbitre les propositions ;
- autorise les commits, les push et les changements de périmètre ;
- décide d’un recours exceptionnel à Claude Fable.

---

## 2. Principes d’implémentation

### 2.1 Réutiliser le niveau 0

Le niveau 1B doit réutiliser les primitives validées du niveau 0 pour :

- la représentation des réseaux ;
- l’encodage des états ;
- la base physique ;
- les créations et annihilations fermioniques ;
- les opérateurs de lien ;
- l’indexation clé-vers-ligne ;
- les Hamiltoniens ;
- les groupes spectraux ;
- les générateurs de saveur ;
- les automorphismes validés.

Une primitive existante ne doit pas être recodée dans `level1` uniquement pour simplifier un appel.

### 2.2 Séparer noyau, diagnostics et campagne

Le code doit distinguer :

1. les objets mathématiques et opérateurs ;
2. les évaluations sur états ou sous-espaces ;
3. les agrégations et diagnostics ;
4. l’orchestration de campagne ;
5. la sérialisation.

Le noyau d’opérateurs ne doit dépendre ni du manifeste de campagne, ni du format JSON.

### 2.3 Résultats individuels avant agrégation

Toute agrégation doit conserver les valeurs sources :

- paire ordonnée ;
- chemin individuel ;
- saveurs ;
- groupe spectral ;
- valeur de S ;
- normalisation.

Aucune moyenne d’orbite ou de chemins ne peut remplacer les résultats élémentaires.

### 2.4 Fermeture stricte

Toute transition non nulle produite par un opérateur invariant de jauge doit conduire à une clé présente dans la base physique ciblée.

Une image non nulle absente de la base est une violation d’invariant et doit lever une exception explicite. Elle ne doit jamais être ignorée.

### 2.5 Déterminisme

À paramètres identiques, doivent être déterministes :

- l’ordre des nœuds, liens et chemins ;
- l’ordre des paires ;
- l’ordre des groupes spectraux ;
- l’ordre des observables ;
- l’ordre de sérialisation ;
- les empreintes ;
- les résultats hors opérations numériquement dégénérées explicitement contrôlées.

---

## 3. Arborescence conceptuelle proposée

Claude Code reste libre d’ajuster les noms ou de regrouper certains modules, sous réserve de conserver les frontières de responsabilité.

```text
src/cosmobox/level1/
  paths.py             # chemins orientés et chemins minimaux
  transporters.py      # application de W_P
  matter.py            # opérateurs habillés c† W c
  local_observables.py # Q_i, T_i^a et produits locaux
  restricted.py        # O_rest = Psi† O Psi et état mixte
  flavor.py            # invariants de saveur
  orbits.py            # covariance et statistiques d’orbite
  matching.py          # appariement inter-S des groupes spectraux
  robustness.py        # verdicts fermés inter-S
  records.py           # modèles de résultats internes
  serialization.py     # adaptation vers le schéma v1

scripts/
  level1b_campaign/     # orchestration, reprise et manifeste

tests/level1/
  test_paths.py
  test_transporters.py
  test_matter.py
  test_local_observables.py
  test_restricted.py
  test_flavor.py
  test_orbits.py
  test_matching.py
  test_robustness.py
  test_serialization.py
```

Cette arborescence est une proposition, pas une norme. Claude Code doit expliquer toute variation importante dans son compte rendu de conception.

---

## 4. Lot 1B-1 — chemins, transporteurs et opérateur habillé

### 4.1 Objectif

Construire et valider les fondations permettant d’appliquer :

```text
O_ij^{alpha,beta}[P] = c†_{i,alpha} W_P c_{j,beta}
```

sur une clé de la base physique exacte du niveau 0.

Ce lot ne diagonalise aucun Hamiltonien et ne lance aucune campagne scientifique.

### 4.2 Modèle conceptuel d’un pas orienté

Un pas doit identifier sans ambiguïté :

- le lien du réseau ;
- son nœud de départ effectif ;
- son nœud d’arrivée effectif ;
- le sens de parcours relativement à l’orientation stockée.

Convention gelée :

```text
sens stocké   -> U_e
sens inverse  -> U_e†
```

Un pas incohérent avec les extrémités du lien doit être rejeté à la construction.

### 4.3 Modèle conceptuel d’un chemin

Un chemin orienté doit contenir :

- le nœud source ;
- le nœud destination ;
- une suite immuable de pas ;
- sa longueur combinatoire ;
- un identifiant canonique déterministe.

Invariants :

- les pas sont contigus ;
- le premier pas part de la source ;
- le dernier arrive à la destination ;
- un chemin vide n’est valide que si source = destination ;
- l’inversion renverse l’ordre des pas et leur orientation ;
- `inverse(inverse(P)) == P`.

### 4.4 Chemins minimaux

L’algorithme doit énumérer tous les chemins minimaux simples entre deux nœuds.

Exigences :

- aucune dépendance à l’ordre d’itération non déterministe d’un dictionnaire ou ensemble ;
- tri canonique final ;
- aucune sélection arbitraire d’un chemin lorsqu’il en existe plusieurs ;
- la distance combinatoire ne sert qu’à la sélection ;
- les chemins non minimaux sont hors périmètre.

Cas obligatoires :

- `i == j` : un unique chemin vide ;
- paire adjacente : un unique chemin de longueur 1 ;
- antipodes de `ring4` : deux chemins minimaux distincts de longueur 2.

Claude Code choisit librement BFS, pré-calcul ou autre stratégie exacte adaptée aux petits graphes finis.

### 4.5 Application du transporteur

Le transporteur agit sur les flux uniquement.

Pour chaque pas, l’application utilise strictement les primitives validées de lien du niveau 0 :

```text
pas direct  -> U_e
pas inverse -> U_e†
```

Le produit doit respecter l’ordre opératoire imposé par l’action sur un ket. Claude Code doit documenter explicitement l’ordre d’application choisi et démontrer qu’il correspond à la définition mathématique de `W_P`.

Résultat attendu d’une primitive d’application :

```text
None
```

si l’amplitude est exactement nulle à cause de la troncature, sinon :

```text
(new_key, complex_amplitude)
```

Aucune renormalisation supplémentaire n’est permise :

```text
nu_S = 1
```

### 4.6 Application de l’opérateur habillé

Pour `O_ij^{alpha,beta}[P]`, l’ordre conceptuel sur un ket est :

1. annihiler la saveur `beta` au nœud `j` ;
2. appliquer le transporteur `W_P` ;
3. créer la saveur `alpha` au nœud `i`.

Les signes fermioniques proviennent exclusivement des primitives Jordan–Wigner du niveau 0.

L’opérateur doit :

- multiplier exactement toutes les amplitudes intermédiaires ;
- retourner `None` dès qu’une primitive produit une amplitude nulle ;
- ne pas modifier une clé en place ;
- vérifier la fermeture dans la base lorsqu’un index de base est fourni ;
- lever une erreur d’invariant si une image non nulle est absente.

### 4.7 Cas local `i == j`

Pour un chemin vide :

```text
W_P = I
```

L’opérateur devient :

```text
c†_{i,alpha} c_{i,beta}
```

Ce cas doit être traité par le même contrat public, sans branche physique alternative ni convention spéciale cachée.

### 4.8 Relation d’adjoint

L’adjoint doit satisfaire :

```text
(O_ij^{alpha,beta}[P])†
=
O_ji^{beta,alpha}[P^{-1}]
```

La validation doit comparer les matrices assemblées ou l’action exhaustive sur la base, et pas uniquement les métadonnées du chemin.

### 4.9 API conceptuelle minimale

Les noms sont indicatifs. Les capacités suivantes doivent exister :

```text
make_oriented_path(...)
invert_path(path)
minimal_paths(lattice, source, destination)
apply_transporter(key, path, ...)
apply_dressed_matter(key, path, alpha, beta, ...)
build_dressed_matter_matrix(basis, path, alpha, beta, ...)
```

Claude Code peut proposer une API plus cohérente avec le niveau 0. Elle doit rester explicite, typée et testable sans lancer une campagne.

### 4.10 Tests d’acceptation du lot 1B-1

Le lot est accepté uniquement après validation de :

- **V01** — commutation avec la loi de Gauss ;
- **V02** — arête parcourue en sens inverse ;
- **V03** — relation d’adjoint ;
- **V04** — chemin nul ;
- **V05** — fermeture de base.

Tests supplémentaires obligatoires :

- chemin discontinu rejeté ;
- extrémités incohérentes rejetées ;
- double inversion identique ;
- déterminisme de l’énumération ;
- deux chemins minimaux pour les antipodes de `ring4` ;
- saturation haute ou basse d’un lien donnant `None` ;
- aucune double normalisation du lien ;
- égalité entre action élémentaire et matrice sur toutes les colonnes d’un petit cas.

### 4.11 Livrables du lot 1B-1

Claude Code doit fournir :

1. les modules nécessaires ;
2. les tests unitaires ;
3. un bref document de choix d’architecture ;
4. la correspondance tests ↔ V01–V05 ;
5. la sortie complète de `pytest` ;
6. le diff exact ;
7. la liste des points ouverts, sans les résoudre par hypothèse implicite.

---

## 5. Lot 1B-2 — observables locales de charge et de saveur

### 5.1 Objectif

Implémenter :

```text
Q_i
T_i^x, T_i^y, T_i^z
Q_i Q_j
T_i^a T_j^a
```

puis les briques nécessaires à :

```text
C_QQ
rho_QQ
C_TT_raw
C_TT_conn
```

### 5.2 Contraintes

- aucune redéfinition des générateurs SU(2) du niveau 0 ;
- réutilisation des générateurs existants lorsqu’ils sont localement exploitables ;
- distinction explicite entre moment brut et connecté ;
- `rho_QQ = null` si le dénominateur est sous le plancher ;
- `null_reason = zero_local_charge_variance` dans le secteur maximal prévu ;
- aucune valeur artificielle égale à zéro à la place d’un `null` normatif.

### 5.3 Verrou d’acceptation

V11, V12 et V15 doivent être démontrés au minimum sur les cas prescrits par le plan de validation.

---

## 6. Lot 1B-3 — états, multiplets et opérateurs restreints

### 6.1 Objectif

Fournir une interface uniforme pour évaluer une observable sur :

- un état propre non dégénéré ;
- un multiplet complet ;
- un sous-espace partiel explicitement non conclusif.

### 6.2 Prescription obligatoire

Pour un multiplet complet :

```text
rho = Pi / d
expectation(O) = Tr(Psi† O Psi) / d
```

Pour les corrélations connectées, tous les termes utilisent le même `rho`.

Pour `lower_bound_only=true` :

- aucun `multiplet_average` ;
- sortie éventuelle nommée `partial_subspace` ;
- aucun verdict scientifique.

### 6.3 Diagnostics

Hermitien :

- trace normalisée ;
- valeurs propres ;
- min, max et étendue.

Non hermitien :

- trace normalisée ;
- valeurs singulières ;
- norme de Frobenius.

Sont interdits :

- Schur ;
- spectre complexe d’une matrice non normale ;
- vecteurs propres non hermitiens.

### 6.4 Verrou d’acceptation

V08, V09 et V10 doivent passer avant le lot suivant.

---

## 7. Lot 1B-4 — invariants de saveur, chemins multiples et orbites

### 7.1 Invariants de saveur

À partir de la matrice complète `G` en saveur :

```text
flavor_singlet
flavor_frobenius_squared
flavor_singular_values
flavor_singular_value_ratio
```

La matrice 2x2 brute reste disponible.

### 7.2 Chemins multiples

Pour chaque chemin minimal, conserver la valeur individuelle avant tout diagnostic transversal.

Les statistiques de chemins autorisées sont celles de la spécification. Aucun moyennage entre longueurs ou couples différents.

### 7.3 Orbites

Le groupe utilisé est celui du Hamiltonien effectif avec ses paramètres, non celui du graphe nu.

Produire seulement après validation de covariance :

```text
orbit_mean
orbit_max_pairwise_spread
orbit_covariance_defect
```

Le contrôle `j_break` doit démontrer la réduction attendue du groupe.

### 7.4 Verrou d’acceptation

V06, V07, V14 et V16 doivent passer.

---

## 8. Lot 1B-5 — appariement inter-S, robustesse et sérialisation

### 8.1 Appariement

Ne jamais apparier les groupes par rang énergétique seul.

L’identité utilise les étiquettes gelées : géométrie, paramètres, complétude, T, translation, réflexion et multiplicité.

Statuts explicites obligatoires :

```text
exact_label_match
ambiguous_cross_truncation_match
target_group_not_in_window
structurally_not_applicable
```

### 8.2 Verdicts fermés

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

Aucune autre observable ne reçoit de verdict automatique.

### 8.3 Sérialisation

Le modèle interne peut être plus strict que le JSON, mais toute sortie doit valider le schéma v1.

Une raison explicite accompagne toute valeur normative `null`.

### 8.4 Verrou d’acceptation

V13 et les tests contractuels du schéma doivent passer avant l’orchestration de campagne.

---

## 9. Lot 1B-6 — campagne pré-enregistrée

### 9.1 Objectif

Exécuter exactement le manifeste :

```text
experiments/LEVEL1B-preregistered-manifest.md
```

Aucune extension adaptative après lecture des corrélateurs.

### 9.2 Exigences d’exploitation

- reprise sûre ;
- écritures atomiques ;
- validation d’un résultat existant avant saut ;
- empreinte du manifeste ;
- commit du dépôt ;
- journal des erreurs ;
- garde-fous de ressources ;
- absence d’écriture par défaut dans un répertoire suivi par Git.

### 9.3 Verrou d’acceptation

V17 et V18 doivent passer avant toute exécution scientifique officielle.

---

## 10. Règles de revue entre lots

À la fin de chaque lot, Claude Code transmet :

```text
1. Résumé fonctionnel
2. Choix d’architecture
3. Fichiers modifiés
4. Tests ajoutés
5. Correspondance avec les validations Vxx
6. Résultat pytest
7. Écarts éventuels avec ce dossier
8. Questions scientifiques bloquantes
9. SHA du commit local ou distant, selon autorisation
```

ChatGPT vérifie :

- la conformité scientifique ;
- l’absence de convention implicite ;
- l’alignement avec les documents normatifs ;
- la suffisance des tests conceptuels.

Lionel valide le passage au lot suivant.

Claude Fable n’est sollicité que pour :

- une contradiction scientifique non résolue ;
- une modification d’une décision gelée ;
- un nouveau gel de campagne ;
- une conclusion scientifique majeure nécessitant un audit indépendant.

---

## 11. Interdictions générales pour Claude Code

Claude Code ne doit pas :

- modifier les seuils ou fenêtres ;
- ajouter une normalisation du transporteur ;
- convertir une corrélation en distance ;
- promouvoir un groupe tronqué en multiplet ;
- apparier des groupes par rang seul ;
- ajouter un verdict à une observable non listée ;
- remplacer une valeur `null` par zéro ;
- moyenner des catégories non comparables ;
- ignorer une transition hors base ;
- adapter une campagne après observation ;
- modifier un document gelé sans proposition explicite et validation de Lionel.

---

## 12. Première mission transmise à Claude Code

Claude Code doit commencer uniquement par le **lot 1B-1**.

Il doit d’abord :

1. auditer les API existantes du niveau 0 ;
2. proposer l’arborescence et les signatures finales ;
3. identifier précisément les primitives réutilisées ;
4. signaler tout conflit ou manque ;
5. implémenter les chemins, transporteurs et opérateurs habillés ;
6. livrer V01 à V05 et les tests complémentaires ;
7. ne pas commencer le lot 1B-2 sans validation explicite.

La première réponse attendue de Claude Code est un court compte rendu d’audit et un plan de fichiers. Il ne doit pas inventer de physique pour combler une ambiguïté.