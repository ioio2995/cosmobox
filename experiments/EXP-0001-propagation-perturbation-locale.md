# EXP-0001 — Propagation d'une perturbation locale

## Statut

À implémenter.

## 1. Objectif

Caractériser la réponse élémentaire du réseau diamant au repos lorsqu'une impulsion locale unique lui est appliquée.

L'expérience doit établir :

- si la perturbation se propage ;
- à quelle vitesse apparente ;
- avec quelle anisotropie ;
- avec quelle dispersion ;
- avec quelle conservation de l'énergie ;
- à partir de quel instant les frontières contaminent la mesure.

Cette expérience ne cherche pas à produire une particule stable.

## 2. Référence conceptuelle

- `docs/research/0001-modele-minimal-reseau-au-repos.md`
- hypothèses concernées à créer dans `docs/01_hypotheses.md` après validation de la présente spécification.

## 3. Hypothèses testées

### H-EXP1-A

Un réseau diamant muni uniquement de liaisons élastiques centrales transmet une perturbation locale à distance.

### H-EXP1-B

L'énergie mécanique totale reste approximativement conservée dans une simulation non amortie, et l'erreur diminue lorsque le pas de temps est réduit.

### H-EXP1-C

La vitesse et l'amplitude de propagation présentent une anisotropie mesurable liée à la structure discrète du réseau.

### H-EXP1-D

Avant le retour des réflexions de frontière, les mesures centrales convergent lorsque la taille du domaine augmente.

## 4. Système simulé

### 4.1 Réseau

- topologie : diamant tridimensionnel ;
- domaine : sphérique ;
- topologie fixe ;
- longueur de repos uniforme : `c` ;
- nœuds intérieurs de degré 4 ;
- masse nodale uniforme : `m` ;
- raideur uniforme : `k`.

### 4.2 Loi mécanique

Pour chaque liaison `(i,j)` :

`E_ij = 1/2 k (L_ij - c)^2`.

Les forces doivent être obtenues par dérivation de cette énergie.

Aucun facteur de contraction piloté, flux signé, cycle ou source persistante n'est autorisé dans cette expérience.

### 4.3 Intégration

L'intégrateur de référence doit être symplectique ou de type Verlet.

Le nom exact de l'intégrateur et son implémentation doivent être consignés dans les résultats.

## 5. État initial

À `t = 0-` :

- tous les nœuds sont à leur position de référence ;
- toutes les vitesses sont nulles ;
- toutes les liaisons ont une longueur `c` ;
- l'énergie mécanique est nulle à la tolérance numérique près.

Le nœud d'injection est le nœud intérieur le plus proche du centre géométrique.

## 6. Injection

À `t = 0`, une vitesse initiale `v0 n` est affectée au nœud central, où `n` est une direction unitaire.

Énergie cinétique injectée :

`E0 = 1/2 m v0^2`.

Après cette initialisation :

- aucune force extérieure n'est appliquée ;
- aucune longueur de repos n'est modifiée ;
- aucune énergie supplémentaire n'est injectée.

## 7. Directions testées

Au minimum :

1. une direction parallèle à une liaison issue du nœud central ;
2. une deuxième direction tétraédrique non colinéaire ;
3. un axe cartésien global ;
4. une direction générique normalisée, non parallèle à une liaison ni à un axe principal.

Les vecteurs exacts doivent être enregistrés dans la configuration.

## 8. Plan de campagne

### 8.1 Contrôle zéro — repos

Exécuter le réseau sans injection pendant la durée nominale.

Critères :

- déplacement maximal proche de zéro ;
- vitesse maximale proche de zéro ;
- énergie totale proche de zéro.

Tout mouvement significatif invalide la suite de la campagne.

### 8.2 Convergence temporelle

Exécuter la même impulsion avec au moins trois pas de temps :

- `dt_ref` ;
- `dt_ref / 2` ;
- `dt_ref / 4`.

Comparer :

- dérive d'énergie ;
- temps d'arrivée ;
- amplitude maximale ;
- position du front.

### 8.3 Convergence spatiale

Exécuter au moins trois tailles de domaine avec les mêmes paramètres locaux.

Comparer uniquement la fenêtre temporelle antérieure aux premières réflexions.

### 8.4 Anisotropie

Répéter la simulation pour toutes les directions définies à la section 7.

### 8.5 Conditions aux limites

Comparer :

- frontière libre ;
- couche absorbante approximative.

La frontière fixe est conservée comme variante diagnostique, mais ne fait pas partie de l'exécution de référence.

### 8.6 Linéarité en amplitude

Exécuter au moins trois amplitudes d'impulsion dans un régime de faible déformation :

- `v0 / 2` ;
- `v0` ;
- `2 v0`.

Vérifier si les temps d'arrivée restent constants et si les amplitudes évoluent proportionnellement à l'impulsion.

## 9. Paramètres à fixer par l'implémentation initiale

Les valeurs numériques ne sont pas encore imposées. Elles doivent être choisies de façon dimensionless et documentée.

| Paramètre | Signification | Exigence |
|---|---|---|
| `c` | longueur de repos | unité de longueur recommandée : `c = 1` |
| `m` | masse nodale | uniforme, valeur de référence documentée |
| `k` | raideur des liaisons | uniforme, valeur de référence documentée |
| `v0` | amplitude de l'impulsion | faible déformation initiale |
| `dt` | pas de temps | soumis à convergence |
| `T` | durée | suffisante pour observer le front avant réflexion |
| `R` | rayon du domaine | soumis à convergence spatiale |
| `seed` | graine | non applicable si construction déterministe |

Le choix naturel de normalisation initiale est `c = m = k = 1`, sans associer ces unités à des dimensions physiques réelles.

## 10. Capteurs virtuels et échantillonnage

Les mesures doivent être réalisées :

- sur chaque nœud ;
- par coquilles radiales autour du point d'injection ;
- par cônes directionnels centrés sur les directions testées.

Pour chaque échantillon temporel, enregistrer au minimum :

- position et vitesse nodales ou un format permettant de les reconstruire ;
- énergie cinétique par nœud ;
- énergie élastique par liaison ;
- énergie totale ;
- quantité de mouvement totale ;
- déplacement maximal ;
- distance du maximum d'énergie au centre.

## 11. Détection du front

Le temps d'arrivée à une distance donnée doit être défini avant l'analyse.

Méthode proposée : premier instant où l'énergie locale ou l'amplitude dépasse un seuil relatif déterminé par rapport au maximum global de l'expérience.

Le seuil doit être testé afin de vérifier que la vitesse mesurée n'est pas un artefact du choix de détection.

Une seconde méthode, par exemple le temps du maximum local, doit être conservée comme contrôle.

## 12. Métriques principales

### Énergie

- `E_total(t)` ;
- erreur relative `(E_total(t) - E0) / E0` ;
- maximum absolu de l'erreur ;
- dérive moyenne sur la durée utile.

### Propagation

- temps d'arrivée par rayon et direction ;
- vitesse apparente obtenue par régression distance/temps ;
- coefficient de détermination de cette régression ;
- amplitude en fonction de la distance.

### Anisotropie

Pour une distance donnée :

- vitesse minimale et maximale selon la direction ;
- écart relatif `(v_max - v_min) / v_mean` ;
- variation relative d'amplitude.

### Dispersion

- largeur radiale du paquet d'énergie ;
- évolution de cette largeur avec le temps et la distance ;
- décalage entre front, maximum et centre énergétique.

### Frontières

- temps estimé de première contamination ;
- différence entre domaine de référence et domaine agrandi avant ce temps ;
- amplitude des réflexions après ce temps.

## 13. Sorties attendues

Chaque exécution doit produire :

- configuration résolue complète ;
- commit Git exact ;
- version de Python et des dépendances ;
- CSV ou format structuré des métriques temporelles ;
- résumé JSON ;
- graphiques énergie/temps ;
- graphiques distance/temps ;
- comparaison directionnelle ;
- animation facultative, uniquement comme aide visuelle.

Arborescence recommandée :

```text
output/EXP-0001/<run-id>/
├── config.yaml
├── metadata.json
├── metrics.csv
├── summary.json
├── energy.png
├── propagation.png
├── anisotropy.png
└── animation.gif
```

## 14. Critères de réussite de l'expérience

L'expérience est considérée comme exploitable si :

1. le contrôle zéro reste stationnaire ;
2. l'énergie initiale calculée correspond à l'énergie observée après injection ;
3. la dérive d'énergie diminue avec le pas de temps ;
4. le front est détectable sur plusieurs distances avant réflexion ;
5. la vitesse apparente est reproductible ;
6. l'anisotropie est quantifiée ;
7. les résultats avant réflexion convergent avec la taille du domaine ;
8. toutes les exécutions sont reproductibles à partir des données versionnées.

## 15. Critères d'invalidation technique

Les résultats ne doivent pas être interprétés si l'un des cas suivants apparaît :

- instabilité du réseau au repos ;
- énergie créée ou perdue sans convergence avec `dt` ;
- suppression artificielle du mouvement du centre de masse ;
- changement silencieux de paramètres entre deux exécutions ;
- mesure effectuée après contamination par les frontières sans l'indiquer ;
- utilisation de l'amplification visuelle dans les métriques physiques ;
- source maintenue active après `t = 0`.

## 16. Interprétation autorisée

Si les critères sont satisfaits, il sera possible de conclure uniquement sur :

- la dynamique ondulatoire du réseau numérique ;
- sa vitesse de propagation dans les unités du modèle ;
- son anisotropie ;
- sa dispersion ;
- la qualité de la conservation numérique.

Il ne sera pas possible de conclure à ce stade sur l'existence de particules, la lumière, la masse, la gravitation ou la structure réelle de l'espace.

## 17. Décisions possibles après résultat

### Résultat A — propagation propre et caractérisable

Passer à l'étude des modes propres, de la dispersion fréquentielle et des perturbations spatialement étendues.

### Résultat B — anisotropie forte

Décider si cette anisotropie est une propriété acceptée du modèle microscopique, si elle disparaît à grande échelle, ou si la topologie doit être remise en question.

### Résultat C — instabilité ou mauvaise conservation

Corriger d'abord le solveur, le pas de temps ou la loi mécanique. Ne pas ajouter de nouvelle physique.

### Résultat D — absence de propagation utile

Réexaminer la loi locale minimale avant toute hypothèse de particule.
