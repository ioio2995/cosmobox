# CosmoBox — État des lieux initial

**Document :** `docs/research/0000-etat-des-lieux.md`  
**Statut :** document de travail vivant  
**Objet :** synthèse des idées, essais, résultats, abandons et questions ouvertes antérieurs à la reprise formelle du projet  
**Date de création :** 2026-08-03

---

## 1. Objet et portée

Ce document reconstruit l’état actuel du projet CosmoBox à partir des échanges, intuitions, simulations et décisions déjà intervenus.

Il ne présente pas une théorie physique établie. Il ne cherche pas non plus à rendre les idées plus cohérentes qu’elles ne l’étaient au moment où elles ont été formulées. Sa fonction est de fournir un point de reprise commun avant toute nouvelle formalisation physique ou évolution logicielle.

Le contenu est classé selon les catégories suivantes :

- **Observation** : ce qui a été effectivement constaté dans une simulation ou dans une propriété géométrique vérifiable du modèle ;
- **Interprétation** : lecture proposée d’une observation ;
- **Hypothèse** : proposition physique ou conceptuelle à tester ;
- **Décision de travail** : choix retenu provisoirement pour poursuivre l’exploration ;
- **Piste abandonnée** : piste écartée dans le cadre courant, sans interdiction de la rouvrir si de nouveaux arguments apparaissent ;
- **Question ouverte** : point encore insuffisamment défini ou testé.

Une simulation interne à CosmoBox ne constitue jamais une validation par rapport à la physique réelle. Elle permet seulement de vérifier la cohérence et les conséquences du modèle simulé.

---

## 2. Situation générale du projet

CosmoBox est actuellement un programme de recherche spéculatif portant sur la possibilité de représenter l’espace comme un milieu discret, localement connecté et déformable.

L’idée centrale qui s’est progressivement dégagée est la suivante :

> Les objets que nous appelons particules pourraient être représentés non comme des corps ajoutés dans l’espace, mais comme des configurations dynamiques, localisées et éventuellement stables du milieu constituant l’espace lui-même.

Cette formulation n’était pas présente dès le départ. Elle résulte de plusieurs évolutions successives :

1. représentation de l’espace par un maillage ;
2. choix d’une organisation tétraédrique locale ;
3. tentative de représenter une particule par un tétraèdre ;
4. remplacement de l’objet statique par une circulation ;
5. remplacement de la circulation abstraite par un flux énergétique ;
6. introduction de la contraction des liaisons ;
7. déformation géométrique réelle du réseau ;
8. reformulation de la particule comme configuration dynamique du milieu.

À ce stade, la seule partie relativement stabilisée concerne la géométrie de travail : un réseau de type diamant, composé de deux sous-réseaux cubiques à faces centrées interpénétrés, dans lequel chaque nœud intérieur possède quatre voisins disposés suivant une géométrie tétraédrique.

Les interprétations physiques relatives à la particule, la masse, la gravitation, l’énergie cachée ou la matière noire restent spéculatives.

---

## 3. Motivation méthodologique initiale

### 3.1 Question générale

La question de départ peut être reconstruite ainsi :

> Est-il possible de définir un milieu discret très simple, gouverné uniquement par des interactions locales, puis d’observer si certaines structures ou propriétés ressemblant à des phénomènes physiques émergent de sa dynamique ?

### 3.2 Contraintes recherchées

Très tôt, plusieurs qualités ont été recherchées pour le milieu de fond :

- discrétion ;
- homogénéité ;
- localité des interactions ;
- absence de direction arbitrairement privilégiée à l’échelle locale ;
- longueur fondamentale commune ;
- possibilité de propagation ;
- possibilité de déformation ;
- reproductibilité numérique.

### 3.3 Position de travail

Le projet ne cherche pas, à ce stade, à dériver la physique connue ni à ajuster des constantes physiques réelles. Les variables utilisées sont normalisées et sans unité physique assignée.

La démarche suivie jusqu’ici a surtout consisté à :

1. proposer une représentation ;
2. la simuler ;
3. observer les défauts géométriques ou dynamiques ;
4. modifier ou abandonner la représentation.

---

## 4. Évolution du support spatial

## 4.1 Maillage régulier générique

### Hypothèse initiale

L’espace pourrait être représenté par un ensemble discret de nœuds reliés entre eux.

### Motivation

Une topologie locale permet d’étudier une propagation sans recourir immédiatement à un champ continu. Chaque nœud ne dépend que d’un nombre limité de voisins.

### Statut

**Décision de travail retenue.**

La notion de réseau discret reste le fondement du projet.

---

## 4.2 Grilles à directions privilégiées

Des représentations régulières simples, notamment de type cubique, ont été envisagées comme support de simulation.

### Avantages constatés

- génération simple ;
- voisinage déterministe ;
- visualisation facile ;
- calcul peu coûteux.

### Limites identifiées

- axes privilégiés évidents ;
- symétrie locale peu compatible avec l’objectif d’un milieu tridimensionnel aussi uniforme que possible ;
- comportement de propagation fortement dépendant des directions du maillage.

### Décision

**Piste abandonnée comme géométrie principale.**

La grille cubique peut rester utile comme cas de contrôle numérique, mais ne constitue plus le candidat principal pour le fond spatial.

---

## 4.3 Tétraèdre isolé ou assemblages tétraédriques

### Motivation

Le tétraèdre est le simplexe élémentaire de l’espace tridimensionnel. Il offre quatre directions depuis chaque sommet et une organisation locale non coplanaire.

### Première interprétation

Le tétraèdre a d’abord été envisagé comme candidat direct pour représenter une particule fondamentale.

### Difficultés

- confusion entre la structure du fond et l’objet supposé émerger du fond ;
- particule trop statique et trop directement codée dans la géométrie ;
- difficulté à définir un déplacement sans déplacer l’objet lui-même de nœud en nœud ;
- difficulté à distinguer l’énergie transportée de la cellule géométrique porteuse.

### Évolution

Le tétraèdre a progressivement cessé d’être considéré comme la particule. Il a été conservé comme structure locale susceptible de supporter une circulation ou un équilibre tridimensionnel.

### Statut

- **Tétraèdre comme particule rigide : abandonné.**
- **Organisation tétraédrique locale : retenue.**

---

## 4.4 Maillages Delaunay et géométries irrégulières

### Motivation

Une triangulation ou tétraédrisation de Delaunay pouvait fournir une connectivité tridimensionnelle naturelle sans imposer une grille orthogonale.

### Avantages espérés

- diversité des directions ;
- remplissage tridimensionnel ;
- construction géométrique standard.

### Limites observées ou anticipées

- longueurs de liaison variables ;
- degrés variables selon les nœuds ;
- dépendance au tirage ou à la distribution initiale des points ;
- anisotropie locale et désordre difficiles à séparer des effets de la dynamique ;
- reproductibilité plus difficile ;
- absence d’une longueur fondamentale unique ;
- comparaison des expériences compliquée par la géométrie elle-même.

### Décision

**Piste abandonnée pour le modèle de référence.**

Elle pourrait être réouverte ultérieurement pour tester la robustesse du modèle à un défaut ou à un désordre géométrique, mais pas avant stabilisation du cas homogène.

---

## 4.5 Facteur géométrique aléatoire par liaison

Une étape intermédiaire a consisté à considérer une longueur de liaison modulée par un facteur géométrique propre à chaque arête, parfois noté conceptuellement `g_ij`.

### Motivation

Représenter une hétérogénéité locale ou éviter une régularité jugée artificielle.

### Limite principale

Ce facteur mélangeait deux effets :

- la structure fondamentale du milieu ;
- sa déformation dynamique.

Il devenait impossible de déterminer si un comportement provenait de la dynamique testée ou du désordre initial.

### Décision

**Piste abandonnée dans le modèle de référence.**

La longueur de repos doit être homogène. Le désordre éventuel devra être introduit plus tard comme expérience distincte et contrôlée.

---

## 4.6 Réseau diamant / blende

### Motivation

Le réseau diamant offre une réponse simple à plusieurs contraintes :

- chaque nœud intérieur possède exactement quatre voisins ;
- les quatre directions locales correspondent aux sommets d’un tétraèdre régulier ;
- toutes les liaisons de premier voisinage ont la même longueur ;
- le réseau est périodique et homogène ;
- la topologie est déterministe ;
- il permet une extension tridimensionnelle sans recourir à une grille orthogonale à six voisins.

### Construction utilisée

Le réseau est construit à partir de deux sous-réseaux cubiques à faces centrées interpénétrés. Chaque nœud d’un sous-réseau est connecté à quatre nœuds de l’autre sous-réseau.

Les quatre directions locales utilisées dans les prototypes sont équivalentes, à une permutation et un signe près, à :

```text
(+1, +1, +1)
(+1, -1, -1)
(-1, +1, -1)
(-1, -1, +1)
```

La longueur commune des arêtes vaut alors, dans les coordonnées internes utilisées :

```text
c = sqrt(3)
```

Cette valeur n’est pas interprétée comme une constante physique réelle. Elle résulte uniquement du choix de coordonnées. Le symbole `c` désigne ici la longueur fondamentale de repos entre deux nœuds voisins.

### Observation géométrique

Dans le volume intérieur du réseau :

- degré nodal égal à quatre ;
- longueurs de repos identiques ;
- voisinage local tétraédrique ;
- connectivité homogène.

Les nœuds proches de la frontière d’un domaine tronqué ont un degré inférieur à quatre. Cette propriété est un artefact des conditions aux limites et non une propriété du réseau infini.

### Décision

**Réseau de référence retenu.**

Cette décision doit être formalisée ultérieurement dans un ADR scientifique.

### Niveau de confiance interne

**Élevé comme choix de plateforme expérimentale**, mais pas comme affirmation sur la structure réelle de l’espace.

---

## 5. Définition progressive de l’unité fondamentale

Plusieurs notions ont été confondues au cours des premières explorations : nœud, liaison, tétraèdre, maille et particule.

L’état actuel de la réflexion est le suivant.

## 5.1 Nœud

Un nœud est un point topologique et géométrique du réseau.

Il peut porter :

- une position de référence ;
- une position courante ;
- une vitesse ;
- éventuellement une masse numérique ou une mobilité dans le solveur ;
- des contraintes externes.

Aucune interprétation physique définitive du nœud n’est actuellement retenue.

## 5.2 Liaison

La liaison entre deux nœuds voisins est devenue l’élément dynamique minimal du modèle.

Elle peut porter :

- une longueur de repos `c` ;
- une longueur géométrique courante `L_ij` ;
- un facteur de déformation `f_ij` ;
- une raideur ;
- un amortissement ;
- une activité ;
- un flux signé.

La relation de travail utilisée est :

```text
L_ij^cible(t) = c * f_ij(t)
```

avec, dans les essais actuels :

```text
f_ij = 1          liaison au repos
f_ij < 1          contraction
f_ij > 1          extension éventuelle
```

### Décision de travail

La liaison est actuellement considérée comme le degré de liberté élémentaire le plus pertinent.

Le tétraèdre fournit l’organisation locale tridimensionnelle, mais la déformation est portée par les liaisons.

## 5.3 Tétraèdre local

Le tétraèdre est actuellement une structure implicite définie par le voisinage d’un nœud intérieur à quatre voisins.

Il peut être utilisé pour définir :

- un cycle ordonné sur quatre liaisons ;
- une chiralité ;
- une orientation ;
- une circulation locale ;
- un équilibre de déformation ;
- éventuellement un volume local.

### Question ouverte

Le tétraèdre doit-il devenir un objet explicite du modèle, avec son propre état, ou rester une vue calculée sur le graphe ?

Cette question relève à la fois de la physique et de l’architecture logicielle. Elle n’est pas tranchée.

---

## 6. Évolution du concept de particule

## 6.1 Particule comme objet géométrique

### Hypothèse

Une particule fondamentale pourrait correspondre à un tétraèdre particulier du réseau.

### Difficultés

- l’objet est codé explicitement au lieu d’émerger ;
- son déplacement implique une procédure artificielle de transfert d’un tétraèdre à un autre ;
- la distinction entre matière et espace devient incohérente si tous les tétraèdres du réseau ont la même nature ;
- aucune stabilité dynamique n’est démontrée.

### Décision

**Abandonnée.**

---

## 6.2 Particule comme cycle tétraédrique

### Hypothèse

La particule pourrait être représentée par une activation cyclique des quatre liaisons associées à un voisinage tétraédrique.

Une phase désigne la liaison active. À chaque pas, la phase avance dans un ordre donné. Le sens de parcours définit une chiralité positive ou négative.

### Apport

Cette représentation transforme la particule d’un objet statique en processus dynamique.

### Limites

- le cycle est imposé par le programme ;
- la propagation n’émerge pas de la mécanique du réseau ;
- l’énergie n’est pas nécessairement conservée ;
- la stabilité du cycle est programmée plutôt qu’obtenue ;
- la relation entre la circulation et la déformation reste arbitraire.

### Statut

**Retenu comme mécanisme expérimental**, pas comme définition finale de la particule.

---

## 6.3 Particule comme flux

### Hypothèse

La particule ne serait pas le cycle lui-même, mais le flux d’énergie ou d’activité transporté par ce cycle.

La chiralité donne un signe au flux. Une activité absolue permet de distinguer la quantité d’action présente de sa résultante signée.

### Grandeurs introduites

- flux signé sur une liaison ;
- activité absolue ;
- phase ;
- chiralité ;
- énergie attribuée au processus.

### Apport conceptuel

Cette étape sépare :

- le support géométrique ;
- l’état dynamique ;
- le sens de circulation ;
- la quantité d’activité.

### Limites

Le flux reste injecté par un objet logiciel représentant la particule. Il n’est pas encore calculé comme conséquence d’un gradient ou d’une loi fondamentale du milieu.

### Statut

**Hypothèse de travail.**

---

## 6.4 Particule comme déformation dynamique

### Évolution

Lorsque les facteurs `f_ij` ont commencé à modifier réellement les longueurs cibles des liaisons, la représentation mentale du modèle a changé.

La particule peut alors être comprise comme une zone de déformation qui évolue dans le réseau plutôt que comme une entité indépendante qui se déplace à travers lui.

### Formulation actuelle

> Une particule serait une configuration localisée, dynamique et potentiellement stable de déformation et de transfert d’énergie dans le réseau.

### Importance

Cette formulation est actuellement la plus cohérente avec l’idée selon laquelle le réseau constitue lui-même l’espace.

### Limites majeures

Aucune simulation réalisée à ce jour n’a démontré :

- l’apparition spontanée d’une telle structure ;
- sa stabilité sans pilotage externe ;
- sa propagation autonome ;
- sa conservation lors d’une collision ;
- l’existence d’états quantifiés ;
- une relation avec une particule physique connue.

### Statut

**Hypothèse principale à formaliser et à tester.**

Elle ne doit pas encore être inscrite comme résultat établi dans `02_model.md` sans mention explicite de son statut.

---

## 7. Déformation du réseau

## 7.1 Première représentation : facteur interne sans mouvement géométrique

Les premières simulations associaient à chaque liaison un facteur de contraction ou de déformation. Ce facteur était visible par la couleur ou l’épaisseur des arêtes.

### Observation

L’animation montrait une activité sur certaines arêtes, mais les positions des nœuds restaient inchangées.

### Problème

La visualisation donnait l’impression d’un réseau déformé alors qu’elle n’affichait qu’un état scalaire abstrait.

### Décision

Cette représentation a été jugée insuffisante.

La distinction suivante a alors été imposée :

- état interne de la liaison ;
- géométrie réelle du réseau.

---

## 7.2 Déformation géométrique réelle

Un solveur mécanique élémentaire a ensuite été introduit.

Pour chaque liaison :

```text
longueur cible = longueur de repos * facteur de déformation
```

La force de rappel est calculée à partir de l’écart entre la longueur courante et la longueur cible. Les forces sont accumulées sur les nœuds, puis les positions et vitesses sont intégrées avec amortissement.

### Observation

Dans un test sur réseau diamant :

- les liaisons activées se contractent ;
- les nœuds se déplacent réellement ;
- la déformation est transmise aux liaisons voisines par la mécanique ;
- une activité de flux opposé peut produire une géométrie localement déformée malgré une somme signée nulle.

Un test documenté a produit, pour un cas particulier :

```text
nodes                         = 293
edges                         = 500
active_nodes                  = 20
c                             = 1.7320508075688774
final_signed_flux_total       = 0.0
final_hidden_activity         = 20.0
final_factor_energy           = 0.042767593257575315
final_geometry_energy         = 0.009431417034096452
final_mean_f                  = 0.994776952611091
final_min_f                   = 0.9366622308764927
final_max_node_displacement   = 0.13606413578958498
```

### Ce que ce test montre réellement

- le solveur transforme une modification des longueurs cibles en déplacement géométrique ;
- la somme des flux signés peut être nulle ;
- l’activité absolue peut rester non nulle ;
- une énergie élastique numérique est stockée ;
- le réseau est effectivement déformé.

### Ce que ce test ne montre pas

- que cette activité correspond à une particule réelle ;
- que l’énergie est conservée au sens physique ;
- que la déformation est stable ;
- qu’elle se propage sans commande externe ;
- qu’elle produit une gravitation ;
- qu’elle représente de la matière noire.

### Décision

**Déformation géométrique réelle retenue comme exigence minimale des prochaines simulations.**

Une simple mise en couleur d’un facteur interne ne doit plus être décrite comme une déformation du réseau.

---

## 7.3 Amplification visuelle

La déformation réelle étant faible dans certains essais, une amplification visuelle a été introduite :

```text
position_affichée = position_référence
                    + amplification
                    * (position_physique - position_référence)
```

### Décision méthodologique

L’amplification visuelle doit être explicitement distinguée de la simulation physique.

Les métriques doivent toujours être calculées sur les positions non amplifiées.

---

## 8. Dynamique utilisée dans les prototypes

Les simulations les plus récentes contiennent trois mécanismes distincts qu’il ne faut pas confondre.

## 8.1 Injection d’activité

Une particule logicielle sélectionne périodiquement une liaison parmi quatre et y injecte un flux signé ou une activité.

Cette injection est externe au milieu.

## 8.2 Évolution du facteur de déformation

Un facteur de liaison évolue selon une règle comprenant typiquement :

- contraction liée à l’activité ;
- relaxation vers `f = 1` ;
- compatibilité avec les liaisons voisines ;
- bornage minimal et maximal.

Schématiquement :

```text
variation(f_ij)
    = - beta * activité_ij
      + compatibilité_locale
      + relaxation * (1 - f_ij)
```

### Statut

Cette loi est un dispositif expérimental. Elle n’est pas dérivée d’un principe physique.

## 8.3 Relaxation mécanique

Le réseau cherche ensuite à atteindre les longueurs cibles définies par les facteurs `f_ij` au moyen d’un modèle de ressorts amortis.

### Statut

Le solveur est utile pour matérialiser la déformation, mais il ne constitue pas encore une loi fondamentale du modèle.

---

## 9. Flux alignés et flux opposés

## 9.1 Cas aligné

Dans le cas aligné, plusieurs cycles utilisent la même chiralité.

### Intention

Observer une résultante collective non nulle ou une organisation commune des flux.

### État des résultats

Les simulations montrent l’addition des flux programmés, mais aucune conclusion physique robuste n’a encore été tirée.

### Statut

**Cas expérimental conservé comme référence comparative.**

---

## 9.2 Cas opposé

Dans le cas opposé, les cycles sont répartis entre deux chiralités de signes contraires.

### Observation

Avec un nombre équilibré de cycles :

```text
somme du flux signé = 0
activité absolue     > 0
```

Une résultante vectorielle construite à partir des directions de liaison peut également être nulle selon la configuration, alors que les liaisons restent activées et que le réseau stocke une déformation.

### Interprétation proposée

Une annulation macroscopique ou signée ne signifie pas nécessairement l’absence d’activité interne.

### Terme provisoire

L’expression « activité cachée » ou `hidden_activity` a été utilisée pour désigner numériquement cette différence.

### Mise en garde

Ce terme ne correspond pas à une grandeur standard de la physique. Il décrit uniquement une métrique interne au prototype.

### Piste spéculative évoquée

Une analogie avec une énergie non directement observable, voire avec la matière noire, a été mentionnée.

### Décision

- **Observation numérique conservée.**
- **Analogie avec la matière noire non retenue comme hypothèse active.**

Avant toute réouverture, il faudrait définir un effet mesurable du modèle qui ne se réduit pas à une simple annulation algébrique programmée.

---

## 10. Masse

## 10.1 Intuition principale

La masse a été associée à une contraction locale ou persistante du réseau.

Formulation intuitive :

> Une concentration d’énergie ou une circulation stable rapproche localement les nœuds et réduit certaines longueurs de liaison.

### Représentation possible

```text
L_ij = c * (1 - delta_ij)
```

avec `delta_ij > 0` dans une région associée à la masse.

### Apport conceptuel

La masse ne serait pas un objet ajouté au réseau. Elle correspondrait à un état déformé du milieu.

### État réel des travaux

Les prototypes ont démontré qu’une contraction imposée déforme le réseau. Ils n’ont pas démontré que :

- la contraction émerge d’une circulation autonome ;
- une quantité équivalente à la masse inertielle apparaît ;
- l’état est stable ;
- la contraction agit sur d’autres excitations de manière compatible avec une interaction gravitationnelle.

### Statut

**Hypothèse ouverte, non validée.**

---

## 10.2 Masse comme énergie de circulation

Une autre formulation a été évoquée : la masse serait liée non seulement à la contraction géométrique, mais à l’énergie maintenue dans une circulation locale.

Cette piste permettrait conceptuellement de relier :

- énergie interne ;
- déformation ;
- persistance ;
- inertie éventuelle.

### Difficulté

Aucune définition opérationnelle de l’inertie n’a encore été introduite.

### Question ouverte

Quelle expérience permettrait de distinguer :

1. un défaut géométrique statique ;
2. une circulation dynamique localisée ;
3. une excitation propagative ;
4. une structure possédant une réponse inertielle ?

---

## 11. Gravitation

## 11.1 Intuition explorée

Si la masse correspond à une contraction locale, la gravitation pourrait correspondre à la propagation ou au gradient de cette déformation dans le réseau.

### Formulation qualitative

Une région contractée modifie les longueurs et orientations des liaisons voisines. Une excitation se propageant dans ce fond pourrait alors suivre une trajectoire différente de celle observée dans un réseau non déformé.

### Apport conceptuel

La masse ne produirait pas une force ajoutée explicitement. Elle modifierait la géométrie d’équilibre du milieu.

### Limites

Aucune expérience n’a encore établi :

- une loi de décroissance avec la distance ;
- une attraction universelle ;
- une déviation reproductible d’une excitation autonome ;
- une équivalence entre masse inertielle et masse gravitationnelle ;
- une dynamique compatible avec la relativité ;
- une vitesse de propagation de l’influence ;
- l’absence d’instabilités ou de dissipation artificielle.

### Statut

**Spéculation structurante, mais non testée.**

Elle ne doit pas être présentée comme une conséquence du modèle actuel.

---

## 12. Propagation

## 12.1 Propagation programmée

Dans les prototypes, la phase de la particule est avancée explicitement. L’activité change donc de liaison selon une règle définie par le programme.

### Observation

Une séquence visuelle mobile peut être produite.

### Limite

Le déplacement observé ne constitue pas une propagation émergente. Il est le résultat direct du changement de phase programmé.

### Décision

Les prochaines expériences devront distinguer explicitement :

- **transport imposé** ;
- **propagation résultant des équations du milieu**.

---

## 12.2 Propagation mécanique

La déformation d’une liaison produit des forces sur ses nœuds, lesquelles modifient les liaisons adjacentes.

### Observation

Une perturbation mécanique locale influence le voisinage.

### Limites

- présence d’amortissement numérique ;
- vitesse dépendante des paramètres arbitraires du solveur ;
- réflexion aux frontières ;
- absence de démonstration d’une vitesse limite unique ;
- risque de dispersion liée au réseau.

### Question ouverte

Le symbole `c`, actuellement utilisé pour la longueur de repos, ne doit pas être confondu avec la vitesse de la lumière.

Il faudra choisir une notation différente ou définir explicitement les deux grandeurs avant de poursuivre.

---

## 13. Énergie et conservation

## 13.1 Énergies mesurées dans les prototypes

Plusieurs métriques ont été utilisées :

- activité absolue ;
- flux signé total ;
- norme d’une résultante vectorielle ;
- énergie associée aux facteurs de déformation ;
- énergie élastique géométrique ;
- déplacement maximal ou moyen des nœuds.

### Problème

Ces grandeurs ne forment pas encore un bilan énergétique fermé.

L’injection d’activité ajoute de l’énergie sans contrepartie explicitement comptabilisée. La relaxation et l’amortissement en dissipent.

### Décision méthodologique

Aucune expérience future ne devra être décrite comme conservant l’énergie tant qu’un bilan complet ne sera pas défini :

```text
énergie injectée
+ énergie initiale
= énergie stockée
+ énergie cinétique
+ énergie transportée
+ énergie dissipée
+ erreur numérique
```

### Question ouverte

Faut-il supprimer toute dissipation pour étudier les structures stables, ou conserver une dissipation contrôlée pour atteindre des états attracteurs ?

Les deux objectifs correspondent à des expériences différentes.

---

## 14. Chiralité, circulation et moment angulaire

## 14.1 Chiralité

Le sens de parcours d’un cycle tétraédrique a été représenté par un signe `+1` ou `-1`.

### Apport

La chiralité permet de construire deux états opposés sans modifier la géométrie du support.

### Limite

Le signe dépend actuellement de l’ordre arbitraire donné aux quatre liaisons. Une convention géométrique globale et reproductible reste à définir.

## 14.2 Moment angulaire

L’idée qu’une circulation locale puisse porter un moment angulaire ou un analogue du spin a été évoquée.

### État

Aucune grandeur géométrique de moment angulaire n’a été calculée dans les prototypes décrits.

### Question ouverte

Il faudra distinguer au minimum :

- circulation combinatoire sur un graphe ;
- rotation géométrique réelle ;
- moment angulaire mécanique ;
- quantité interne analogue au spin.

Ces notions ne sont pas interchangeables.

### Statut

**Piste ouverte, non formalisée.**

---

## 15. Conditions aux limites et taille du domaine

Les réseaux simulés sont finis, généralement tronqués selon un domaine sphérique.

### Effets connus

- nœuds de frontière de degré inférieur à quatre ;
- réflexions mécaniques ;
- recadrage du centre de masse ;
- déplacement global artificiellement supprimé ;
- comportement dépendant du rayon du domaine.

### Décision méthodologique

Les futurs comptes rendus devront indiquer :

- forme du domaine ;
- taille ;
- nombre de nœuds et d’arêtes ;
- règle de frontière ;
- présence ou non de nœuds fixés ;
- recentrage éventuel ;
- durée avant qu’une perturbation atteigne la frontière.

### Question ouverte

Comparer au moins trois stratégies :

1. frontière libre ;
2. frontière fixée ou absorbante ;
3. conditions périodiques.

---

## 16. Pistes explicitement écartées ou à ne pas réintroduire sans justification

Cette section sert à éviter la répétition d’essais déjà jugés insuffisants.

### 16.1 Particule rigide indépendante du réseau

**Écartée**, car elle réintroduit un objet se déplaçant dans un espace distinct du milieu.

### 16.2 Tétraèdre identifié directement à une particule

**Écarté**, car le tétraèdre est désormais considéré comme une structure locale du fond.

### 16.3 Grille cubique comme réseau principal

**Écartée**, en raison de directions privilégiées trop fortes.

### 16.4 Delaunay aléatoire comme réseau de référence

**Écarté**, en raison du désordre géométrique et de l’absence d’une longueur fondamentale unique.

### 16.5 Facteur géométrique aléatoire permanent

**Écarté** du cas de référence, car il masque les effets de la dynamique.

### 16.6 Mise en couleur assimilée à une déformation

**Écartée.** Une déformation doit modifier la géométrie réelle ou être explicitement qualifiée de champ scalaire non géométrique.

### 16.7 Propagation imposée présentée comme émergente

**Écartée.** Un changement de phase programmé est un mécanisme d’injection ou de transport, pas une émergence.

### 16.8 Analogie directe avec la matière noire

**Écartée comme conclusion.** Une activité interne à résultante nulle ne suffit pas à reproduire les observations astrophysiques attribuées à la matière noire.

### 16.9 Gravité déclarée à partir d’une simple contraction

**Écartée comme conclusion.** La contraction constitue seulement un mécanisme géométrique candidat.

---

## 17. État actuel des décisions

| ID provisoire | Élément | Statut | Niveau de confiance interne |
|---|---|---|---|
| D-001 | Utiliser un réseau discret comme fond spatial expérimental | Retenu | Élevé pour le programme de recherche |
| D-002 | Utiliser le réseau diamant comme géométrie de référence | Retenu | Élevé comme banc d’essai |
| D-003 | Imposer quatre voisins tétraédriques aux nœuds intérieurs | Retenu | Élevé |
| D-004 | Utiliser une longueur de repos homogène | Retenu | Élevé |
| D-005 | Porter la déformation élémentaire sur les liaisons | Retenu provisoirement | Moyen à élevé |
| D-006 | Distinguer flux signé et activité absolue | Retenu pour les métriques | Moyen |
| D-007 | Exiger une déformation géométrique réelle | Retenu | Élevé |
| D-008 | Considérer la particule comme configuration dynamique plutôt que comme objet rigide | Hypothèse principale | Moyen |
| D-009 | Associer la masse à une contraction persistante | Hypothèse ouverte | Faible |
| D-010 | Associer la gravitation à un gradient de déformation | Spéculation | Très faible |

Ces identifiants sont provisoires. Ils devront être remplacés par des ADR si les décisions sont confirmées.

---

## 18. État actuel des observations

### O-001 — Géométrie du réseau diamant

Un nœud intérieur possède quatre voisins de premier rang à distance identique.

### O-002 — Déformation imposée

Une réduction des longueurs cibles provoque une déformation géométrique du réseau avec un solveur de ressorts.

### O-003 — Transmission mécanique locale

La contraction d’une liaison influence les positions de nœuds communs et donc les longueurs des liaisons voisines.

### O-004 — Annulation du flux signé

Deux ensembles équilibrés de flux opposés peuvent produire une somme signée nulle.

### O-005 — Activité résiduelle

La somme signée peut être nulle tandis que l’activité absolue, la déformation et l’énergie élastique restent non nulles.

### O-006 — Déformation réelle distincte de l’affichage

Une amplification visuelle peut rendre le phénomène visible sans modifier les métriques physiques internes.

### O-007 — Absence actuelle d’émergence

Les cycles, leurs phases et leur activité sont encore pilotés explicitement par le programme.

---

## 19. Hypothèses actives à tester

## H-001 — Particule comme excitation localisée du milieu

Une particule peut être représentée par une configuration localisée de déformation et de transfert d’énergie.

### Critère minimal de progrès

Obtenir une structure qui persiste pendant une durée significative sans injection périodique prescrivant directement son cycle.

### Critère d’invalidation interne

Si toute excitation locale se disperse ou s’effondre pour une large classe de lois locales raisonnables, cette formulation devra être revue.

---

## H-002 — Circulation tétraédrique comme mécanisme de localisation

Une circulation utilisant les quatre directions locales pourrait contribuer à maintenir une excitation localisée.

### Expérience nécessaire

Comparer :

- impulsion non circulante ;
- cycle programmé ;
- circulation issue d’une loi locale ;
- deux chiralités opposées.

---

## H-003 — Masse comme état contracté persistant

Une structure énergétique persistante pourrait imposer ou produire une contraction locale durable.

### Expérience nécessaire

Définir une structure autonome, mesurer son énergie et sa réponse à une impulsion externe.

---

## H-004 — Déviation d’une excitation par un fond déformé

Une excitation propagative pourrait changer de trajectoire dans une région où les longueurs de repos ou la géométrie sont modifiées.

### Expérience nécessaire

Créer un défaut statique contrôlé puis mesurer la trajectoire d’une onde ou d’un paquet localisé, sans invoquer encore la gravitation.

---

## H-005 — Activité interne à résultante nulle

Des états opposés peuvent conserver une énergie interne tout en annulant certaines grandeurs macroscopiques signées.

### Expérience nécessaire

Construire un bilan d’énergie fermé et vérifier que l’effet ne provient pas simplement d’une double injection externe.

---

## 20. Questions ouvertes prioritaires

### Géométrie

1. Le réseau diamant est-il suffisamment isotrope aux grandes échelles ?
2. Quelle dispersion introduit-il selon la direction de propagation ?
3. Quelle taille de domaine permet de séparer dynamique locale et effets de bord ?
4. Les tétraèdres doivent-ils être explicitement identifiés ?

### Variables fondamentales

5. La variable fondamentale est-elle la position nodale, la longueur de liaison, une phase, une énergie, ou une combinaison ?
6. Le facteur `f_ij` est-il un état physique, une longueur de repos effective ou seulement un artifice de simulation ?
7. Faut-il autoriser extension et contraction, ou uniquement la contraction ?
8. Existe-t-il une borne physique ou géométrique naturelle ?

### Dynamique

9. Quelle loi locale remplace l’injection programmée ?
10. Comment définir une propagation sans déplacer explicitement une particule ?
11. Comment garantir ou mesurer la conservation de l’énergie ?
12. Quel rôle doit jouer l’amortissement ?
13. Une excitation stable nécessite-t-elle une non-linéarité ?
14. Quel mécanisme empêche la dispersion ?

### Particule

15. Quels critères permettent d’appeler une structure « particule » ?
16. Doit-elle être stable, propagative, quantifiée ou collisionnelle ?
17. Comment mesurer sa position, son énergie, son impulsion et sa chiralité ?
18. Deux structures peuvent-elles se traverser, fusionner ou s’annihiler ?

### Masse et gravitation

19. Comment définir l’inertie dans le modèle ?
20. Une contraction statique suffit-elle à modifier la propagation ?
21. Quelle loi de distance émerge d’un défaut local ?
22. Comment distinguer attraction géométrique et simple gradient de raideur ?

### Validation

23. Quels invariants numériques doivent être testés avant toute interprétation ?
24. Quelles expériences négatives permettraient de rejeter les hypothèses principales ?
25. Quelles observables de la physique connue pourraient être comparées sans ajustement arbitraire excessif ?

---

## 21. Programme expérimental recommandé avant toute nouvelle interprétation physique

## Étape A — Validation géométrique

Objectif : caractériser le réseau indépendamment de toute particule.

Expériences proposées :

- vérifier automatiquement le degré des nœuds intérieurs ;
- vérifier l’égalité des longueurs de repos ;
- mesurer l’isotropie statistique ;
- identifier explicitement les cellules tétraédriques ;
- comparer frontières libre, fixe et périodique.

## Étape B — Validation mécanique

Objectif : caractériser le milieu élastique seul.

Expériences proposées :

- réponse à une impulsion nodale ;
- réponse à une contraction d’une seule liaison ;
- propagation d’une onde ;
- mesure de la vitesse et de la dispersion selon plusieurs directions ;
- bilan énergétique sans amortissement ;
- bilan énergétique avec amortissement connu.

## Étape C — Localisation

Objectif : rechercher des structures localisées sans leur attribuer un nom physique.

Expériences proposées :

- défaut statique ;
- impulsion localisée ;
- circulation imposée ;
- circulation auto-entretenue par loi locale ;
- recherche de non-linéarités permettant une stabilité.

## Étape D — Interaction

Objectif : étudier deux excitations localisées.

Expériences proposées :

- même chiralité ;
- chiralités opposées ;
- collision frontale ;
- collision avec paramètre d’impact ;
- mesure du bilan énergétique et de la topologie après interaction.

## Étape E — Fond déformé

Objectif : tester la propagation dans une géométrie non uniforme.

Expériences proposées :

- défaut contracté statique ;
- défaut étendu ;
- trajectoire d’un paquet d’onde ;
- mesure de la déviation ;
- dépendance à la distance et à l’énergie de l’excitation.

Aucune de ces étapes ne doit être appelée « gravitation », « photon », « masse » ou « matière noire » avant que des critères opérationnels ne soient définis.

---

## 22. Exigences de traçabilité pour les futures expériences

Chaque expérience devra contenir au minimum :

- identifiant unique `EXP-XXXX` ;
- hypothèse testée ;
- résultat susceptible d’invalider l’hypothèse ;
- commit Git exact ;
- configuration complète ;
- graine aléatoire si applicable ;
- taille et type du réseau ;
- conditions aux limites ;
- durée et pas temporel ;
- paramètres du solveur ;
- méthode d’injection ;
- métriques calculées ;
- fichiers de sortie ;
- observation brute ;
- interprétation séparée ;
- décision.

Les animations ne doivent pas être utilisées seules comme preuve. Elles doivent être accompagnées de métriques quantitatives.

---

## 23. Séparation entre modèle physique et moteur logiciel

Une décision d’organisation a été prise :

- ChatGPT prend en charge la structuration conceptuelle, les hypothèses, les protocoles expérimentaux et l’analyse critique ;
- Claude prend en charge l’architecture logicielle, l’implémentation, les tests et les outils ;
- Lionel conserve la direction du projet, arbitre les choix et transmet les résultats entre les deux pistes ;
- le dépôt GitHub constitue la mémoire commune.

### Point de jonction

Le pont entre physique et logiciel doit être constitué par :

- les documents de modèle ;
- les ADR ;
- les fiches d’expériences ;
- les configurations versionnées ;
- les résultats reproductibles ;
- les pull requests et leurs revues.

### Principe

Le code ne doit pas devenir la spécification implicite de la physique.

Inversement, une hypothèse physique ne doit pas être intégrée au moteur générique sans interface explicite et sans expérience associée.

---

## 24. État du code au moment de la pause

Un prototype modulaire existe déjà. Il comprend notamment :

- génération d’un réseau diamant tronqué ;
- état des nœuds et des liaisons ;
- particules logicielles à cycle tétraédrique ;
- injection de flux ;
- évolution de facteurs de déformation ;
- solveur mécanique à ressorts amortis ;
- métriques CSV et résumé JSON ;
- rendu GIF ou MP4 ;
- configuration et interface en ligne de commande ;
- premiers tests automatisés.

### Limite principale

Ce code contient encore des hypothèses physiques directement intégrées à l’implémentation. Il doit être traité comme un prototype historique, non comme la spécification définitive.

### Décision

Pause sur l’ajout de nouvelles fonctionnalités physiques jusqu’à :

1. consolidation de l’état des lieux ;
2. formalisation du modèle minimal ;
3. définition des premières expériences reproductibles ;
4. clarification des interfaces entre moteur et lois expérimentales.

---

## 25. Synthèse de l’état actuel

### Éléments relativement stabilisés

- usage d’un réseau discret comme banc d’essai ;
- choix du réseau diamant comme géométrie de référence ;
- quatre voisins tétraédriques pour chaque nœud intérieur ;
- longueur de repos commune ;
- liaison comme support élémentaire de déformation ;
- distinction entre facteur interne et géométrie réelle ;
- nécessité d’une déformation géométrique mesurable ;
- distinction entre observation, interprétation, hypothèse et décision ;
- séparation entre travail physique et travail logiciel.

### Éléments utiles mais encore artificiels

- cycle tétraédrique programmé ;
- flux signé injecté ;
- loi de contraction liée à l’activité ;
- compatibilité locale ;
- relaxation vers l’état de repos ;
- ressorts amortis ;
- métrique d’activité cachée.

### Hypothèses principales non démontrées

- particule comme configuration stable de déformation ;
- masse comme contraction persistante ;
- gravitation comme gradient ou propagation de déformation ;
- relation entre chiralité et spin ;
- énergie interne observable malgré une résultante nulle ;
- émergence d’états quantifiés.

### Risque méthodologique principal

Le principal risque identifié est de programmer directement les comportements que le projet cherche ensuite à qualifier d’émergents.

La prochaine phase devra donc privilégier des lois locales minimales, des bilans fermés et des critères d’invalidation explicites.

---

## 26. Prochaine extraction documentaire

Après revue de ce document, les éléments pourront être distribués comme suit :

- `docs/00_vision.md` : portée du projet, méthode et limites ;
- `docs/01_hypotheses.md` : hypothèses actives, rejetées et en attente ;
- `docs/02_model.md` : uniquement les éléments stabilisés du modèle minimal ;
- `docs/03_experiments.md` : index des essais historiques reconstruits et des nouvelles expériences ;
- `docs/05_decisions/` : ADR scientifiques pour les choix réellement actés ;
- `experiments/` : fiches reproductibles, en commençant par la caractérisation du réseau et du solveur.

Ce document reste la source historique de synthèse. Il ne doit pas être utilisé pour déclarer une hypothèse validée sans passage par les documents correspondants.
