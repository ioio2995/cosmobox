# Level 1C — Cadrage conceptuel (1C-0)

Statut : **cadrage conceptuel — non normatif, aucune implémentation scientifique autorisée**

Branche : `research/level1-correlators`

Ce document est le livrable du lot 1C-0. Il ne calcule rien, ne lance aucune campagne, ne transforme aucun corrélateur en distance, n'ajuste aucun modèle et ne sélectionne aucune géométrie candidate favorite. Il inventorie, cadre, et signale les décisions scientifiques encore ouvertes — il ne les tranche pas. Chaque affirmation est étiquetée **[ÉTABLI]**, **[HYPOTHÈSE]**, **[OPTION MÉTHODOLOGIQUE]** ou **[DÉCISION OUVERTE]**.

## 1. État hérité de Level 1B

**[ÉTABLI]** Level 1B est clos (`docs/levels/level1/level1b-conclusion.md`, lots 1B-9b à 1B-9g). Sur la campagne normative pré-enregistrée (`campaign_id=level1b-reference-v1`), 7 groupes spectraux appariés exactement entre `S=3` et `S=2`, 684/684 comparaisons évaluables robustes selon le critère gelé (D018), 0 `non_robust`, 0 `indeterminate`. Les structures relationnelles gauge-invariantes testées (corrélateur habillé, `rho_QQ`, `C_TT_conn`, invariants de saveur) ne sont pas un artefact fragile de la troncature en spin de lien `S` testée dans le domaine pré-enregistré.

**[ÉTABLI]** Level 1B ne définit aucune distance effective ni aucune métrique (`docs/levels/level1/level1b-conclusion.md` §15). `docs/levels/level1/geometry-liberation.md` reste, pour Level 1B, une orientation conceptuelle non normative.

**[ÉTABLI]** Level 1B ne compare que `S=2` et `S=3` — aucune comparaison à `S=1`, aucune limite `S → infini` établie, aucune convergence démontrée au-delà de ces deux points.

## 2. Question scientifique de Level 1C

> Les données relationnelles invariantes de jauge validées et robustes de Level 1B contiennent-elles suffisamment de structure pour permettre la reconstruction d'une organisation géométrique effective sans imposer a priori sa dimension, sa topologie ou son plongement ?

Level 1C ne part **pas** de l'hypothèse qu'une géométrie existe. La question porte sur l'existence même d'une structure reconstructible, pas sur la nature de cette structure.

## 3. Hypothèse nulle

**[HYPOTHÈSE — cadre de test]** L'hypothèse nulle de Level 1C est qu'aucune structure géométrique classique simple (au sens de `geometry-liberation.md` §6 : dimension et topologie fixes, résidu d'ajustement borné, stable sous relabellage et sous variation de `S`) n'est nécessaire pour rendre compte des données relationnelles de Level 1B au-delà de ce que le graphe combinatoire microscopique décrit déjà lui-même.

Cette hypothèse nulle doit rester réfutable : Level 1C doit être conçu de manière à pouvoir la rejeter (structure trouvée) ou à échouer à la rejeter (aucune structure trouvée), sans qu'aucune des deux issues ne soit favorisée par construction.

## 4. Résultats admissibles

**[ÉTABLI — contrainte de conception]** Doivent rester explicitement admissibles comme conclusions possibles d'une future campagne Level 1C, sans que l'une soit privilégiée dans le cadrage :

- aucune géométrie classique simple n'est compatible avec les données ;
- une géométrie compatible existe, mais seulement pour certains secteurs spectraux ou certaines géométries de graphe, pas universellement ;
- plusieurs candidats de plongement sont compatibles de façon quasi équivalente, sans qu'un critère actuel ne permette de trancher ;
- un candidat s'ajuste avec un bon résidu numérique sans que cela constitue une preuve de géométrie fondamentale (`geometry-liberation.md` §6, avant-dernier critère).

## 5. Inventaire des données relationnelles disponibles

Inventaire des objets réellement présents dans le code Level 1B (`src/cosmobox/level1/*.py`) et/ou les artefacts normatifs. Aucun jugement de sélection n'est porté ici au-delà des risques signalés.

### 5.1 `O_ij_raw` / `G_ij^{alpha,beta}[P]` (corrélateur habillé)

- scalaire/complexe/matrice : matrice complexe 2×2 en espace de saveur (`FlavorCorrelatorMatrix.matrix`, `flavor.py`) ;
- dépendance à (i,j) : oui, paire ordonnée de nœuds ;
- dépendance au chemin : oui — un chemin orienté `P` explicite (`OrientedPath`) est un paramètre de construction, pas une propriété dérivée de (i,j) seul ; plusieurs chemins minimaux distincts peuvent exister entre deux mêmes nœuds (`paths.minimal_paths`) ;
- dépendance à la saveur : la matrice entière porte l'indice de saveur (`alpha`, `beta`) ; les 4 composantes sont disponibles ;
- normalisation disponible : `raw_G` (non normalisé) ; sert de base à `gamma_O` (normalisé par l'amplitude, `NORMALIZATION_FLOOR=1e-12`) ;
- cas null/non défini : la valeur brute elle-même n'est jamais null ; c'est `gamma_O` (comparaison inter-S) qui devient non défini sous le plancher d'amplitude (252/416 cas dans la campagne 1B) ;
- invariance sous relabellage : covariante (non invariante) sous les automorphismes du graphe validés — `U_A O_ij[P] U_A^dagger = O_{A(i)A(j)}[A(P)]` (V06/V07, `orbits.py`), jamais testée invariante en valeur brute ;
- disponibilité dans les artefacts normatifs : oui (`record_kind` ∈ `raw_observable`/`orbit_statistic`/`restricted_diagnostic`) ;
- intérêt potentiel : candidat primaire naturel — c'est l'observable de matière gauge-invariante fondamentale du modèle ;
- risque de circularité : **faible sur le principe**, mais dépendance au choix du chemin `P` introduit un degré de liberté non canonique (voir §6).

### 5.2 `rho_QQ`

- scalaire réel (`NormalizedMoment.value`) ;
- dépendance à (i,j) : oui, mais sans transporteur de jauge (`Q_i` est un opérateur local, pas un opérateur habillé sur un chemin) ;
- dépendance au chemin : **aucune** ;
- dépendance à la saveur : aucune (`Q_i` est un singulet de saveur par construction) ;
- normalisation disponible : auto-normalisé (`C_QQ(i,j) / sqrt(C_QQ(i,i) C_QQ(j,j))`), sans paramètre de normalisation supplémentaire ;
- cas null/non défini : `zero_local_charge_variance` quand la variance locale d'un des deux sites est sous le plancher (structurel dans le secteur de saveur maximale, 6/96 dans la campagne 1B) ;
- invariance sous relabellage : covariante sous les automorphismes du graphe, comme `O_ij_raw` ;
- disponibilité : oui, `record_kind="normalized_observable"` ;
- intérêt potentiel : candidat attractif car **sans dépendance au chemin** — évite le degré de liberté « choix de `P` » de `O_ij_raw` ;
- risque de circularité : faible en tant que tel, mais réel-valué uniquement (perte d'information de phase par rapport à `O_ij_raw`) — une dissimilarité construite dessus ne pourrait pas encoder de phase relative.

### 5.3 `C_TT_conn`

- scalaire réel (`sum_a [<T_i^a T_j^a> - <T_i^a><T_j^a>]`, `local_observables.py`) ;
- dépendance à (i,j) : oui, sans transporteur (opérateurs locaux) ;
- dépendance au chemin : aucune ;
- dépendance à la saveur : déjà sommée sur les 3 composantes SU(2) — pas de décomposition par composante disponible en sortie de cette fonction précise ;
- normalisation disponible : aucune — valeur brute du moment connexe, non normalisée par une amplitude ;
- cas null/non défini : aucun observé dans la campagne 1B (0/96) ;
- invariance sous relabellage : covariante sous les automorphismes du graphe ;
- disponibilité : oui, `record_kind="raw_observable"`, payload `float` nu ;
- intérêt potentiel : candidat de « corrélation de spin/saveur » scalaire réel, jamais null ;
- risque de circularité : faible, mais échelle non normalisée — le `gamma_o` générique mesuré en 1B atteint jusqu'à ≈0.28 sur certaines amplitudes faibles, signe que la valeur brute varie sur plusieurs ordres de grandeur selon le secteur.

### 5.4 Invariants de saveur (`flavor_singlet`, `flavor_frobenius_squared`, `flavor_singular_values`, `flavor_singular_value_ratio`)

- scalaire/complexe : `flavor_singlet` complexe ; `flavor_frobenius_squared` réel ≥0 ; `flavor_singular_values` couple de réels ≥0 ordonnés ; `flavor_singular_value_ratio` réel ∈[0,1] ou non défini ;
- dépendance à (i,j) et au chemin : héritée de `G_ij^{alpha,beta}[P]` dont ils sont dérivés — mêmes dépendances que §5.1 ;
- dépendance à la saveur : par construction, ce sont des invariants SOUS rotation de saveur SU(2) (`Psi -> Psi V`) — ils éliminent la dépendance de saveur plutôt que de la porter ;
- normalisation disponible : `flavor_singular_value_ratio` est auto-normalisé (rapport de deux valeurs singulières de la même matrice) ; les trois autres sont bruts ;
- cas null/non défini : `flavor_singular_value_ratio` devient non défini si `sigma_1` est sous le plancher (22/104 dans la campagne 1B) ; les trois autres ne portent aucune `null_reason` documentée dans le pipeline actuel ;
- invariance sous relabellage : covariante sous les automorphismes du graphe, comme `O_ij_raw` ; en outre invariante sous SU(2) de saveur (propriété distincte, déjà établie normativement, V16) ;
- disponibilité : `flavor_singular_value_ratio` disponible dans la campagne 1B (104 comparaisons) ; `flavor_singlet`/`flavor_frobenius_squared`/`flavor_singular_values` existent dans `results.py` mais `flavor_singlet` est explicitement exclu de tout verdict de robustesse (hors de `ROBUSTNESS_OBSERVABLE_KINDS`) ;
- intérêt potentiel : candidats « débarrassés » de la redondance de saveur, potentiellement plus proches d'une quantité purement géométrique ;
- risque de circularité : faible sur le principe, mais **résultat observé en 1B** : au point de référence SU(2)-symétrique de la campagne, `flavor_singular_value_ratio` vaut ≈1 sur la totalité des 82 cas évaluables — quasi aucun pouvoir discriminant à ce point précis des paramètres, ce qui n'est pas un défaut de circularité mais une limite pratique à documenter.

### 5.5 Identité de chemin (`OrientedPath.nodes`/`.steps`)

- pas un scalaire/complexe/matrice : une identité structurelle (tuple de nœuds + pas orientés) ;
- dépendance : est elle-même le chemin, donc s'applique à un couple (i,j) et sélectionne une route particulière parmi celles disponibles ;
- disponibilité : oui, `identity.path` sur chaque `ResultRecord` concerné ;
- intérêt potentiel : métadonnée nécessaire pour interpréter correctement `O_ij_raw`/invariants de saveur, pas une donnée candidate en tant que cible de reconstruction ;
- **risque de circularité : ÉLEVÉ** si utilisée comme cible — le chemin retenu provient déjà de `paths.minimal_paths`, qui utilise la distance combinatoire non orientée du graphe (voir §5.6).

### 5.6 Chemins minimaux (`paths.minimal_paths`)

- ensemble déterministe de tous les plus courts chemins simples entre deux nœuds, au sens de la distance de graphe non orientée ;
- disponibilité : utilisée en interne pour sélectionner quels `O_ij_raw`/invariants de saveur sont effectivement calculés dans la campagne (`path_selection = all_minimal_paths`, manifeste 1B) — pas sérialisée comme observable indépendante ;
- intérêt potentiel pour reconstruction : **aucun en tant que cible** ;
- **risque de circularité : ÉLEVÉ, signalé explicitement par le mandat** — la distance combinatoire du graphe est disponible comme propriété du graphe, mais l'utiliser comme CIBLE de reconstruction serait circulaire : elle a déjà servi à choisir quelles données relationnelles existent.

### 5.7 Information d'orbite (`OrbitResultPayload`/`OrbitStatistics`/`OrbitComparabilityKey`)

- statistiques scalaires (moyenne, dispersion) agrégées sur une orbite d'automorphismes, seulement après validation de covariance (`validate_orbit_covariance`) ;
- dépendance à (i,j)/chemin/saveur : héritée de la `OrbitComparabilityKey` (longueur de chemin, groupe spectral, `observable_kind`, normalisation, composante de saveur — tous fixés identiques au sein d'une orbite) ;
- disponibilité : `record_kind="orbit_statistic"`, présent dans le pipeline `results.py`, utilisé notamment pour `O_ij_raw` (l'un des trois `record_kind` possibles pour cet `observable_kind`, cf. 1B-9d) ;
- intérêt potentiel : réduit la redondance d'information entre paires (i,j) reliées par une symétrie exacte du Hamiltonien ;
- **risque de circularité : MOYEN à ÉLEVÉ** — une orbite est définie par le groupe d'automorphismes du graphe lui-même : une donnée « orbite-agrégée » présuppose déjà la symétrie combinatoire testée, elle ne la découvre pas.

### 5.8 Identité de groupe spectral (`SpectralGroupIdentity`)

- pas une donnée relationnelle (i,j) : décrit à quel multiplet un enregistrement appartient (`status`, `multiplicity`, `twice_T`, `spectral_window_group_index`, `representative_energy`) ;
- disponibilité : oui, sur chaque `ResultRecord` ;
- intérêt potentiel : critère de sélection (ne retenir que les groupes `complete_multiplet`, per `geometry-liberation.md` §6), pas une entrée de reconstruction elle-même ;
- risque de circularité : aucun en tant que filtre, à condition de ne jamais être traitée comme une coordonnée.

### 5.9 Labels de translation/réflexion (`SymmetryLabel`)

- complexe ou état qualitatif (`numeric`/`not_applicable`/`unavailable`), un caractère restreint `chi_A = Tr(Psi^dagger U_A Psi)` par générateur de symétrie et par groupe spectral (pas par paire (i,j)) ;
- disponibilité : oui, utilisée pour le matching inter-S (1B-9c) ;
- intérêt potentiel : indique quelle représentation du sous-groupe de symétrie effectivement conservé par le Hamiltonien un groupe spectral porte — pourrait éventuellement informer un nombre quantique de type moment angulaire SANS présupposer de plongement spatial, puisque c'est un caractère exact d'automorphisme, pas une coordonnée ;
- **risque de circularité** : moyen — interpréter directement une valeur de caractère comme un vecteur d'onde spatial `k` importerait une hypothèse géométrique non démontrée (c'est précisément ce que `level1b-conclusion.md` §11 refuse de faire pour `ring5[1→1]` sans démonstration supplémentaire).

### 5.10 Spin de lien `S`

- paramètre global de troncature du degré de liberté de jauge, pas une donnée relationnelle entre nœuds ;
- disponibilité : oui, `identity.spin` sur chaque enregistrement ;
- intérêt potentiel : non comme cible de reconstruction, mais comme axe de robustesse pour valider un futur candidat géométrique (`geometry-liberation.md` §6 : « tester la robustesse sous variation de `S` »), par analogie avec ce que 1B a déjà fait pour les corrélateurs ;
- risque de circularité : aucun, à condition de ne jamais être traité comme une coordonnée spatiale.

### 5.11 Identité de géométrie de graphe (`triangle`/`ring4`/`ring5`, `Lattice`)

- structure combinatoire complète : nœuds, liens orientés, incidence, plaquettes, automorphismes (`geometry-liberation.md` §1) ;
- disponibilité : totale, Level 0 ;
- intérêt potentiel : contexte structurel de référence, jamais une donnée « à reconstruire » ;
- **risque de circularité : ÉLEVÉ si traité comme cible de validation** — ajuster une géométrie candidate pour reproduire l'adjacence du graphe redécouvrirait seulement l'entrée, sans rien démontrer sur la structure portée par les corrélateurs eux-mêmes.

## 6. Risques de circularité — synthèse

**[ÉTABLI — contrainte de conception, reprise de `geometry-liberation.md` §2/§6]**

1. La distance combinatoire du graphe (chemins minimaux, §5.6) a déjà servi à sélectionner quelles données relationnelles existent dans les artefacts 1B ; elle ne peut donc pas servir de cible de validation d'une géométrie reconstruite sans circularité.
2. Les statistiques d'orbite (§5.7) présupposent le groupe d'automorphismes du graphe ; les traiter comme une découverte géométrique indépendante serait trompeur.
3. Le graphe lui-même (§5.11) est le contexte, jamais la cible : un bon ajustement qui ne fait que reproduire l'adjacence déjà connue du graphe ne démontre rien.
4. Les caractères de translation/réflexion (§5.9) risquent une lecture géométrique prématurée (ex. interprétation en vecteur d'onde spatial) si elle n'est pas explicitement démontrée à partir des labels spectraux déjà acceptés.
5. Le choix du chemin `P` dans `O_ij_raw`/invariants de saveur (§5.1, §5.4) n'est pas canonique : plusieurs chemins minimaux peuvent exister entre deux nœuds ; le choix ou l'agrégation de `P` fait partie des décisions encore ouvertes (§8), pas un fait déjà réglé.

## 7. Candidats de représentation géométrique

**[OPTION MÉTHODOLOGIQUE — inventaire sans sélection]** Reprise stricte de `geometry-liberation.md` §5, aucun candidat n'est favorisé :

- absence de plongement classique simple (résultat admissible en soi, §4) ;
- `R1` — plongement euclidien de dimension 1 ;
- `R2` — plongement euclidien de dimension 2 ;
- `S1` — plongement circulaire, hypothèse naturelle de contrôle pour `ringN` (`geometry-liberation.md` §3) ;
- `S2` — plongement sphérique, nécessite une structure bidimensionnelle fermée que les géométries `ringN` actuelles ne fournissent pas seules (`geometry-liberation.md` §3).

**[DÉCISION OUVERTE]** D'autres classes devraient-elles être envisagées (ex. arbres/graphes métriques discrets sans plongement continu, tores de dimension supérieure, hyperboliques) ? Ce cadrage ne tranche pas cette liste — il signale seulement qu'elle n'est peut-être pas exhaustive, sans en proposer d'extension normative.

Aucune fonction de coût, aucun résidu, aucun ajustement n'est défini pour aucun de ces candidats à ce stade.

## 8. Décisions scientifiques encore nécessaires

**[DÉCISION OUVERTE — réservée à ChatGPT après audit de ce rapport]**

La décision centrale : **quelle donnée relationnelle primaire utiliser pour construire une dissimilarité ou une structure géométrique candidate ?** Ce document catalogue les options sans en choisir aucune :

- `O_ij_raw`/`G_ij^{alpha,beta}[P]` brut (§5.1) — riche mais dépendant du choix de `P` ;
- `rho_QQ` (§5.2) — sans dépendance au chemin, mais réel-valué uniquement ;
- `C_TT_conn` (§5.3) — sans dépendance au chemin, jamais null, mais non normalisé ;
- un invariant de saveur (§5.4) — débarrassé de la redondance SU(2), mais quasi non discriminant au point de référence testé en 1B ;
- une combinaison ou une agrégation de plusieurs de ces observables.

Familles de transformations dissimilarité/distance **inventoriées uniquement, aucune adoptée** (chacune avec un défaut connu à documenter avant tout pré-enregistrement) :

- une transformation logarithmique du type `d = -xi log(|C|/C0)` — explicitement interdite sans pré-enregistrement séparé (`geometry-liberation.md` §5) ; défaut connu : diverge si `|C| → 0`, ce qui est précisément le régime le plus fréquent des données 1B (`gamma_O` sous plancher dans 252/416 cas) ;
- une transformation inverse du type `d = 1/|C|` — même défaut de divergence près de zéro, sans justification physique établie du choix de puissance ;
- une transformation fonction de `rho_QQ` — hérite des nulls structurels du secteur de saveur maximale (§5.2) ;
- l'absence de transformation (utiliser directement une similarité, sans passer par une distance) — évite la divergence mais change la nature mathématique du problème de reconstruction (similarité vs. métrique).

Autres décisions ouvertes, non tranchées ici :

- quel(s) groupe(s) spectraux retenir (seuls les groupes `complete_multiplet` sont éligibles, per `geometry-liberation.md` §6, mais lequel/lesquels précisément) ;
- quelle valeur de `S` de référence (probablement `S=2`, robustesse déjà testée contre `S=3`, mais non encore décidé normativement pour 1C) ;
- comment traiter les cas null structurels (exclusion, traitement séparé, autre) ;
- comment traiter la multiplicité de chemins minimaux entre deux nœuds (choix canonique, moyenne, conservation de la variabilité comme donnée) ;
- quelle méthode d'estimation de dimension/topologie candidate ;
- quelle définition de résidu et quel critère de comparaison entre candidats ;
- quel protocole de test de robustesse sous relabellage et sous `S` pour un candidat donné.

## 9. Hypothèse directrice générale et statut de chaque proposition

**[NON NORMATIF — rappel de cadre, jamais un résultat acquis]**

Hypothèse de travail générale du scénario global : la matière correspond à des excitations locales du système ; le champ de jauge fournit la connexion permettant de comparer et transporter leurs phases ; une éventuelle gravité émergente serait une réponse géométrique collective du support aux excitations ; un éventuel graviton serait alors un quantum de cette réponse géométrique collective.

Statut de chacune de ces quatre propositions :

- **matière locale** : **[ÉTABLI]** structure microscopique du modèle (opérateurs `c†_{i,alpha}`, `Q_i`, `T_i^a`) ; **pas** une émergence démontrée — c'est une brique de construction du modèle, pas un résultat physique.
- **connexion de jauge** : **[ÉTABLI structurellement]** réalisée par `U_e`/le transport de Wilson (`transporters.py`) ; **[HYPOTHÈSE]** aucune identification démontrée avec l'électromagnétisme physique.
- **géométrie collective** : **[HYPOTHÈSE]** — c'est précisément ce que Level 1C commence seulement à tester ; aucun résultat actuel ne l'établit ni ne l'infirme.
- **réponse à l'énergie-impulsion** : **[NON TESTÉ]** — non testée par 1C-0, et probablement postérieure à une éventuelle reconstruction géométrique réussie (elle présuppose qu'une géométrie candidate existe déjà).
- **graviton** : **[CONJECTURE FUTURE]** — aucun test actuel, aucune donnée de ce cadrage n'y touche.

Cette hypothèse ne doit jamais être présentée comme un résultat acquis, à aucune étape de 1C-0.

## 10. Ce que Level 1C ne testera pas encore

**[ÉTABLI — limite explicite de 1C-0 et de tout sous-lot d'implémentation qui n'aurait pas encore été pré-enregistré]**

- aucun calcul scientifique, aucune diagonalisation, aucune campagne ;
- aucune transformation corrélateur → distance/dissimilarité ;
- aucun ajustement (fitting) d'un candidat géométrique ;
- aucun choix de dimension ou de topologie privilégiée ;
- aucune conclusion de métrique, de courbure, ou de causalité émergente ;
- aucun lien testé avec une gravité émergente ou un graviton ;
- aucune extension de la campagne normative Level 1B (`S=1`, `S>3`, autres perturbations du Hamiltonien).

## 11. Proposition de découpage des futurs sous-lots — conception uniquement

**[OPTION MÉTHODOLOGIQUE — proposition, aucun engagement, aucun sous-lot ouvert par ce document]**

Un enchaînement possible, à valider et pré-enregistrer explicitement avant toute implémentation, sous responsabilité conceptuelle de ChatGPT pour les choix scientifiques (§8) :

1. **1C-1** — pré-enregistrement de la donnée relationnelle primaire retenue (§8) et de sa transformation en dissimilarité, avec justification, domaine de définition et défauts connus documentés avant tout calcul.
2. **1C-2** — pré-enregistrement des critères de validation d'un candidat géométrique : invariance sous relabellage, définition du résidu, comparaison multi-candidats (§7), robustesse sous `S`, verdict « aucune géométrie classique simple » explicitement autorisé.
3. **1C-3** — conception (design document, sans exécution) du pipeline de reconstruction, en couche externe aux modules `level1` existants (`geometry-liberation.md` §7 : `paths`/`transporters`/`matter`/`local_observables`/`restricted`/`flavor`/`orbits`/`matching`/`robustness` restent non modifiés).
4. **1C-4** — première exécution exploratoire, non normative, sur un sous-ensemble limité de groupes spectraux complets, à des fins de vérification du pipeline uniquement.
5. **1C-5** — campagne normative de reconstruction, pré-enregistrée, sur l'ensemble des groupes spectraux complets éligibles.

Aucun de ces sous-lots n'est ouvert, autorisé, ou engagé par le présent document.
