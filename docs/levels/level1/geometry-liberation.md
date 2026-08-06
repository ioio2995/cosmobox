# Libération de la géométrie — orientation post-1B

Statut : **orientation conceptuelle — non normative pour la campagne 1B en cours**

Branche : `research/level1-correlators`

Point d’introduction : après le lot **1B-6**, avant toute spécification d’une distance ou d’une métrique effective.

## 1. État réel du modèle

Cosmobox n’est fondamentalement ni cartésien ni sphérique.

Sa structure intrinsèque est celle d’un graphe orienté fini :

- nœuds ;
- liens orientés ;
- incidence ;
- plaquettes ;
- chemins ;
- automorphismes du graphe et du Hamiltonien.

Les constructions physiques validées aux niveaux 0 et 1B dépendent de cette structure combinatoire, pas d’un plongement préalable dans un espace de coordonnées.

En particulier, les éléments suivants restent intrinsèques :

- loi de Gauss ;
- opérateurs de lien ;
- transporteurs de Wilson ;
- chemins minimaux ;
- corrélateurs habillés ;
- translation et réflexion lorsqu’elles appartiennent au groupe de symétrie du Hamiltonien ;
- moyennes sur multiplets et orbites.

## 2. Décision d’orientation

La géométrie de fond ne doit pas être fixée implicitement comme cartésienne.

Les coordonnées éventuelles sont séparées en trois catégories :

1. **coordonnées de visualisation** : sans effet sur le Hamiltonien ni sur les observables ;
2. **plongement externe imposé** : coordonnées utilisées explicitement dans les couplages ou les normalisations, donc nouvelle donnée physique de fond ;
3. **géométrie reconstruite** : plongement testé a posteriori à partir de données relationnelles calculées sans coordonnées.

Le projet privilégie la troisième catégorie pour toute future revendication géométrique.

Aucune coordonnée cartésienne, circulaire ou sphérique ne doit entrer silencieusement dans une primitive du niveau 1B.

## 3. Cercle et sphère

Pour un anneau `ringN`, la représentation externe naturelle est circulaire :

```text
theta_i = 2 pi i / N
```

La translation discrète correspond alors à une rotation et ses caractères sont les phases :

```text
exp(i k), avec k = 2 pi n / N.
```

Cette lecture fournit une hypothèse de plongement sur `S1`, mais elle ne transforme pas le graphe en géométrie émergente : le cercle est encore une représentation externe du cycle.

Une hypothèse sphérique `S2` exige une structure bidimensionnelle fermée — par exemple une triangulation de sphère, un tétraèdre, un octaèdre ou un icosaèdre — et deux directions angulaires indépendantes. Les anneaux actuels ne représentent au mieux qu’un grand cercle ou un équateur.

Par conséquent :

- `ringN` est un contrôle naturel pour une hypothèse `S1` ;
- une hypothèse `S2` nécessitera de nouvelles géométries de graphe explicitement spécifiées ;
- aucune conclusion sphérique ne peut être tirée des seuls secteurs de translation des anneaux.

## 4. Effet sur le niveau 1B en cours

Cette orientation ne modifie pas :

- la spécification scientifique gelée du niveau 1B ;
- le manifeste pré-enregistré ;
- les observables ;
- les seuils ;
- les normalisations ;
- les lots déjà validés ;
- l’appariement inter-S ;
- les verdicts de robustesse.

Le niveau 1B continue d’utiliser exclusivement :

- la distance combinatoire pour sélectionner les chemins minimaux ;
- les paires ordonnées de nœuds ;
- les chemins orientés ;
- les orbites du groupe de symétrie effectif du Hamiltonien.

La distance combinatoire reste un outil de sélection du graphe et ne devient pas une distance physique émergente.

## 5. Extension proposée après clôture de 1B

Une étape ultérieure, provisoirement nommée **niveau 1C — reconstruction et comparaison de plongements**, pourra recevoir comme entrée les observables relationnelles validées de 1B.

Elle devra comparer plusieurs hypothèses sans en privilégier une a priori :

```text
aucun plongement classique simple
R1
R2
S1
S2
```

L’entrée primaire devra être une matrice relationnelle construite à partir d’observables approuvées, avec une prescription gelée avant calcul. La transformation d’un corrélateur en dissimilarité ou distance devra faire l’objet d’une décision scientifique séparée.

Aucune formule du type :

```text
d_eff = -xi log(|C_ij| / C0)
```

n’est autorisée par le présent document. Une telle transformation devra être pré-enregistrée, justifiée, testée sur ses domaines de définition et comparée à des alternatives.

## 6. Critères minimaux d’une future reconstruction

Toute future procédure devra au minimum :

- utiliser uniquement des groupes spectraux complets pour les conclusions normatives ;
- conserver les valeurs relationnelles brutes ;
- être invariante sous relabellage des nœuds ;
- distinguer plongement imposé et plongement inféré ;
- quantifier le résidu d’ajustement de chaque hypothèse ;
- comparer plusieurs dimensions et topologies candidates ;
- tester la robustesse sous variation de `S` ;
- ne pas interpréter un bon ajustement comme preuve unique d’une géométrie fondamentale ;
- permettre explicitement le verdict « aucune variété classique simple ne convient ».

## 7. Conséquences architecturales

Le noyau `level1` doit rester indépendant de toute classe de coordonnées.

Une future couche de reconstruction devra être extérieure aux modules :

```text
paths
transporters
matter
local_observables
restricted
flavor
orbits
matching
robustness
```

Elle pourra consommer leurs résultats sérialisés, mais ne devra pas modifier rétroactivement le calcul des observables.

Les identifiants de géométrie actuels (`triangle`, `ring4`, `ring5`, etc.) désignent des topologies de graphe et des conventions d’incidence, pas des plongements cartésiens.

## 8. Statut scientifique

### Établi

- le modèle est intrinsèquement combinatoire ;
- les anneaux portent une symétrie cyclique et des secteurs de phase ;
- le niveau 1B peut être achevé sans coordonnées externes.

### Hypothèses ouvertes

- les données relationnelles peuvent éventuellement admettre un plongement circulaire ou sphérique approximatif ;
- une topologie candidate peut dépendre de l’état spectral et des paramètres ;
- la meilleure représentation peut ne correspondre à aucune variété classique simple.

### Non démontré

- que la géométrie physique de Cosmobox est sphérique ;
- que les phases de translation constituent des coordonnées spatiales ;
- qu’une métrique ou une courbure émerge des corrélateurs de niveau 1B ;
- qu’un plongement ajusté est unique ou fondamental.

## 9. Décision de séquençage

Le niveau 1B doit être terminé et clôturé avec ses conventions actuelles.

La libération de la géométrie est enregistrée dès maintenant comme orientation de conception, mais son implémentation est différée jusqu’à ce que :

1. les observables 1B soient entièrement validées ;
2. la campagne 1B soit exécutée sans adaptation postérieure ;
3. les données relationnelles disponibles soient inventoriées ;
4. une feature distincte de reconstruction géométrique soit rédigée et pré-enregistrée.

Cette séparation évite d’introduire une hypothèse sphérique après observation des résultats et protège la falsifiabilité du niveau suivant.
