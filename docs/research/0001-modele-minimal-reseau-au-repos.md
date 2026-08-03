# 0001 — Modèle minimal du réseau au repos

## Statut

Proposition de travail.

Ce document définit le plus petit modèle exploitable pour reprendre les expériences de CosmoBox. Il ne décrit ni une particule, ni une masse, ni la gravitation. Son seul objet est le comportement du milieu discret en l'absence de structure localisée persistante.

## 1. Objectif

Établir un fond dynamique suffisamment simple pour répondre à cinq questions préalables :

1. une perturbation locale se propage-t-elle ;
2. l'énergie injectée est-elle conservée ou dissipée de manière contrôlée ;
3. la propagation dépend-elle de l'orientation dans le réseau ;
4. le signal se disperse-t-il ;
5. les résultats dépendent-ils fortement des frontières ou de la taille du domaine.

Tant que ces propriétés ne sont pas caractérisées, les notions de particule, masse et gravitation restent prématurées.

## 2. Périmètre

### Inclus

- réseau diamant tridimensionnel ;
- nœuds matériels ou géométriques ;
- liaisons entre voisins ;
- longueur de repos commune `c` ;
- déplacement et vitesse des nœuds ;
- énergie cinétique des nœuds ;
- énergie élastique des liaisons ;
- intégration temporelle ;
- conditions aux limites explicitement choisies ;
- mesures de propagation, d'énergie, d'anisotropie et de dispersion.

### Exclus

- particules nommées ;
- chiralité imposée ;
- cycles tétraédriques persistants ;
- masse assimilée à une contraction ;
- gravitation ;
- flux signé indépendant de la mécanique ;
- facteur de déformation piloté artificiellement pendant toute la simulation ;
- interprétations cosmologiques.

## 3. Géométrie de fond

### 3.1 Topologie

Le fond est représenté par un réseau diamant, construit comme deux sous-réseaux cubiques à faces centrées interpénétrés.

Pour tout nœud intérieur :

- le degré topologique vaut exactement 4 ;
- les quatre voisins sont disposés selon des directions tétraédriques ;
- chaque liaison relie des voisins immédiats ;
- toutes les liaisons ont la même longueur de repos `c`.

La topologie est fixe pendant une expérience : aucune liaison n'est créée ou supprimée.

### 3.2 Positions de référence

Chaque nœud `i` possède une position de référence :

`X_i`.

Chaque liaison `(i,j)` vérifie au repos :

`|X_j - X_i| = c`.

La position courante du nœud est :

`x_i(t) = X_i + u_i(t)`,

où `u_i(t)` est son déplacement.

### 3.3 Domaine

Le domaine initial recommandé est une découpe sphérique du réseau afin de limiter le biais visuel et géométrique d'un domaine cubique.

Ce choix ne garantit pas l'isotropie. Il réduit seulement l'introduction de directions privilégiées par la forme de la frontière.

## 4. Degrés de liberté

Chaque nœud porte uniquement :

- un déplacement tridimensionnel `u_i(t)` ;
- une vitesse tridimensionnelle `v_i(t)` ;
- une masse inertielle numérique commune `m`.

Les liaisons ne portent pas, dans ce modèle minimal, de variable dynamique indépendante. Leur allongement résulte uniquement de la position des nœuds.

Pour une liaison `(i,j)` :

- longueur courante : `L_ij(t) = |x_j(t) - x_i(t)|` ;
- allongement : `Delta L_ij(t) = L_ij(t) - c`.

## 5. Loi mécanique minimale

### 5.1 Énergie élastique

Chaque liaison est modélisée comme un ressort central linéaire de raideur commune `k` :

`E_ij = 1/2 k (L_ij - c)^2`.

Cette loi est un choix expérimental minimal, pas une propriété supposée fondamentale du modèle final.

### 5.2 Force

La force exercée par la liaison `(i,j)` est dirigée suivant l'axe courant de la liaison et dérive de l'énergie élastique.

Aucune force tangentielle, torsionnelle ou volumique n'est incluse dans la première expérience.

### 5.3 Énergie cinétique

Pour chaque nœud :

`K_i = 1/2 m |v_i|^2`.

L'énergie mécanique totale mesurée est :

`E_total = somme_i K_i + somme_(i,j) E_ij`.

### 5.4 Amortissement

La configuration de référence de l'expérience doit utiliser un amortissement nul.

Un amortissement numérique ou physique ne pourra être activé que dans une variante explicitement identifiée. Il ne doit pas être confondu avec une perte d'énergie due à l'intégrateur.

## 6. Évolution temporelle

Le moteur doit intégrer les équations du mouvement à partir des forces dérivées de l'énergie élastique.

L'intégrateur doit être choisi et documenté. Pour l'expérience de référence, un schéma symplectique ou Verlet est préférable à Euler explicite, car le critère principal inclut la conservation de l'énergie sur une durée longue.

Le pas de temps `dt` doit faire l'objet d'une étude de convergence. Une simulation ne peut pas être interprétée avant d'avoir vérifié que ses résultats restent stables lorsque `dt` est diminué.

## 7. État de repos

L'état de repos est défini par :

- `x_i(0) = X_i` ;
- `v_i(0) = 0` ;
- `L_ij(0) = c` pour toutes les liaisons ;
- `E_total(0) = 0` avant injection de la perturbation.

Le moteur doit vérifier que cet état reste stationnaire en l'absence de perturbation, à la précision numérique près.

Cette vérification constitue un prérequis et non un résultat secondaire.

## 8. Perturbation élémentaire

La première perturbation ne doit pas être appelée particule.

Elle consiste en une condition initiale localisée, appliquée une seule fois à `t = 0`, puis laissée évoluer librement.

Deux formes seront étudiées séparément :

1. **impulsion cinétique** : une vitesse initiale est affectée à un nœud central ;
2. **déplacement initial** : un nœud central est déplacé puis relâché avec une vitesse nulle.

La première expérience de référence utilise l'impulsion cinétique, car elle injecte une quantité d'énergie calculable sans modifier artificiellement une longueur de repos.

Après `t = 0`, aucune source externe ne doit continuer à alimenter le réseau.

## 9. Conditions aux limites

Les frontières peuvent dominer le résultat. Elles doivent donc être traitées comme un paramètre expérimental.

Trois variantes sont distinguées :

- **libre** : les nœuds de bord évoluent avec les mêmes lois que les autres ;
- **fixe** : les nœuds de bord sont immobiles ;
- **absorbante approximative** : une couche périphérique amortit progressivement le signal.

Aucune variante ne doit être considérée comme physiquement correcte par défaut.

La première exécution utilisera une frontière libre, puis sera comparée à une frontière absorbante afin d'identifier le temps à partir duquel les réflexions contaminent les mesures.

## 10. Invariants et contrôles obligatoires

### 10.1 Invariants géométriques initiaux

- tous les nœuds intérieurs ont quatre voisins ;
- toutes les longueurs de repos valent `c` à la tolérance numérique près ;
- les quatre directions locales d'un nœud intérieur forment la géométrie tétraédrique attendue ;
- le centre géométrique du domaine est connu et reproductible.

### 10.2 Contrôles dynamiques

- le repos reste stable sans perturbation ;
- l'énergie injectée est connue ;
- aucune énergie n'est injectée après l'initialisation ;
- la dérive relative de l'énergie est mesurée ;
- la quantité de mouvement totale est mesurée ;
- la translation globale du réseau n'est pas supprimée artificiellement sans être comptabilisée ;
- toute correction numérique appliquée au centre de masse doit être désactivée dans l'expérience de référence ou explicitement enregistrée comme une force externe.

## 11. Grandeurs à mesurer

### 11.1 Énergie

- énergie cinétique totale ;
- énergie élastique totale ;
- énergie mécanique totale ;
- erreur relative d'énergie par rapport à l'énergie injectée.

### 11.2 Propagation

- temps d'arrivée du front à différentes distances ;
- vitesse apparente du front ;
- position du maximum d'énergie en fonction du temps ;
- largeur radiale du paquet d'énergie ;
- amplitude maximale en fonction de la distance.

### 11.3 Anisotropie

Les mesures doivent être répétées dans plusieurs directions cristallographiques et dans des directions non alignées avec les liaisons.

L'anisotropie est quantifiée par la variation relative de la vitesse d'arrivée et de l'amplitude selon la direction.

Une représentation visuelle sphérique peut compléter les mesures, mais elle ne constitue pas à elle seule une preuve d'isotropie.

### 11.4 Dispersion

La dispersion est évaluée par l'évolution de la largeur du paquet et par la dépendance de la vitesse apparente au contenu fréquentiel de la perturbation.

### 11.5 Effets de frontière

- temps de première réflexion détectable ;
- différence entre domaines de tailles différentes ;
- différence entre frontières libre, fixe et absorbante.

## 12. Critères minimaux d'acceptation

Le modèle de fond sera considéré comme suffisamment caractérisé pour passer à l'étude de structures localisées si :

1. l'état de repos est numériquement stable ;
2. la dérive d'énergie est bornée et diminue avec `dt` ;
3. une vitesse de propagation peut être mesurée de manière reproductible ;
4. l'anisotropie est quantifiée, même si elle n'est pas nulle ;
5. les réflexions de frontière sont identifiées et séparées du régime utile ;
6. les résultats sont reproduits sur au moins deux tailles de domaine ;
7. la configuration, le commit et les sorties sont versionnés.

## 13. Ce que cette étape ne permettra pas de conclure

Même si une onde stable se propage, cela ne démontrera pas :

- que le réseau représente l'espace physique ;
- que la vitesse mesurée correspond à `c` au sens de la vitesse de la lumière ;
- qu'une particule peut émerger ;
- que la masse est une contraction ;
- que la gravitation est un gradient de déformation ;
- que le modèle reproduit une loi physique connue.

L'expérience caractérisera uniquement la dynamique du modèle numérique choisi.

## 14. Décision proposée

Utiliser ce modèle comme référence zéro de CosmoBox.

Toute nouvelle loi ou structure devra être comparée à cette référence et justifier explicitement :

- la variable ajoutée ;
- le problème qu'elle résout ;
- l'énergie qu'elle introduit ou transforme ;
- les nouveaux paramètres ;
- les nouveaux invariants ;
- le test susceptible de l'invalider.
