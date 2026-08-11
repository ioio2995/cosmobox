# Cadrage conceptuel — Level 2

Statut : **cadrage scientifique initial**

Branche : `research/level2-energy-regime`

Base d'ouverture : `main @ 24e457b182c7fec41f3cb93f3101f02fef1f65cb`

## 1. Pourquoi Level 2 existe

Level 0 a établi un laboratoire quantique fini cohérent : modèle de jauge U(1) compact sur graphe fini, fermions complexes sur les nœuds, liens quantiques de spin fini, projection exacte sur la contrainte de Gauss et Hamiltonien complet dans le sous-espace physique.

Level 1 a ensuite étudié des observables relationnelles invariantes de jauge. Level 1B a montré que, dans les groupes spectraux appariables entre `S=2` et `S=3`, les observables étudiées sont robustes selon le critère pré-enregistré. Level 1C n'a en revanche pas permis de mesurer leur réponse sous perturbation locale `J0`, car aucune des 40 comparaisons inter-J0 pré-enregistrées n'a produit une identité de branche `TRACKED_ONE_TO_ONE`.

La leçon méthodologique héritée de Level 1 est donc double :

```text
robustesse d'une observable
!=
identifiabilité de son évolution sur une branche spectrale donnée
```

et :

```text
une branche particulière du bas du spectre
ne doit pas devenir implicitement le support privilégié
pour toute tentative d'émergence géométrique
```

Level 2 change donc volontairement d'axe. Il ne cherche pas encore à reconstruire une géométrie. Il cherche d'abord à savoir si **l'organisation relationnelle elle-même dépend du régime énergétique/spectral**.

## 2. Question scientifique centrale

Question de Level 2 :

> **L'organisation des corrélations relationnelles invariantes de jauge change-t-elle de manière systématique entre différents régimes du spectre, ou reste-t-elle essentiellement de même nature sur toute la partie accessible du spectre ?**

Cette question est plus primitive que :

```text
"quelle géométrie peut-on ajuster sur les corrélations ?"
```

Elle demande d'abord s'il existe plusieurs régimes d'organisation relationnelle distinguables dans le même système quantique fini.

Le but est de rechercher une **dépendance de régime**, éventuellement une réorganisation qualitative, et non de forcer l'apparition d'une phase géométrique.

## 3. Hypothèse de travail

Hypothèse de travail Level 2 :

> Un même Hamiltonien relationnel peut présenter des organisations de corrélations différentes selon la région du spectre considérée. Les états de basse énergie pourraient être plus structurés ou plus contraints, tandis que des régions plus excitées pourraient présenter une organisation plus diffuse, différente, ou au contraire révéler une structure qui n'est pas visible au voisinage du fondamental.

Cette hypothèse ne préjuge pas du sens de la variation.

Level 2 doit autoriser comme résultats valides :

```text
- organisation plus structurée à basse énergie ;
- organisation plus structurée à énergie intermédiaire ;
- organisation plus structurée à haute énergie ;
- variation continue sans séparation nette de régimes ;
- absence de dépendance détectable au régime spectral ;
- comportement différent selon la géométrie microscopique ;
- résultat non identifiable dans le périmètre numérique accessible.
```

Aucun de ces résultats n'est privilégié a priori.

## 4. ASSUMED — ce que Level 2 conserve

Level 2 conserve volontairement les hypothèses structurelles suivantes afin de ne modifier qu'un axe scientifique à la fois :

```text
ASSUMED:
- mécanique quantique standard ;
- Hamiltonien actuel du laboratoire Cosmobox ;
- contrainte de Gauss exacte ;
- fermions complexes sur les nœuds ;
- liens quantiques U(1) de spin fini ;
- connectivité microscopique du graphe imposée ;
- temps externe du formalisme quantique standard ;
- observables relationnelles invariantes de jauge déjà validées.
```

Ces éléments ne sont donc **pas** testés par Level 2.

En particulier, Level 2 ne teste pas encore l'émergence de la connectivité, de la matière, du temps ou de la dynamique gravitationnelle.

## 5. HYPOTHESIZED — ce qui reste conjectural

```text
HYPOTHESIZED:
- l'organisation relationnelle peut dépendre du régime spectral ;
- certains régimes peuvent être plus facilement compressibles par une description géométrique effective que d'autres ;
- une transition ou un crossover d'organisation pourrait exister ;
- la basse énergie n'est pas nécessairement le seul régime physiquement informatif pour l'émergence.
```

Ces points sont des hypothèses de programme, pas des résultats acquis.

Le mot « transition » doit rester utilisé avec prudence : sur les petits systèmes finis actuels, Level 2 peut au mieux mettre en évidence une réorganisation ou un crossover spectral. Une véritable transition de phase demanderait ensuite une étude de taille finie et, idéalement, une limite appropriée.

## 6. TESTED IN LEVEL 2 — ce que nous voulons réellement mesurer

Level 2 doit tester seulement :

```text
TESTED_IN_LEVEL2:
- dépendance des observables relationnelles au régime spectral ;
- stabilité ou changement de leur structure statistique entre régimes ;
- robustesse inter-S des tendances observées ;
- reproductibilité de ces tendances entre groupes/secteurs comparables ;
- existence éventuelle d'un régime spectral qualitativement distinct.
```

La variable indépendante principale est donc le **régime spectral**, pas une branche individuelle suivie sous perturbation.

## 7. Pourquoi partir du spectre plutôt que de la température

Une description thermique via

\[
\rho_\beta = \frac{e^{-\beta H}}{Z}
\]

serait parfaitement définie dans le modèle actuel, mais elle mélange immédiatement plusieurs niveaux d'interprétation : distribution statistique, température, pondération de nombreux états et choix d'un paramètre thermodynamique.

Pour le premier sous-niveau de Level 2, il est préférable de rester plus proche des données exactes déjà disponibles et de travailler directement dans le spectre.

La première formulation visée est donc :

```text
LOW / MID / HIGH spectral regimes
```

ou, plus généralement, des fenêtres spectrales définies de manière pré-enregistrée.

La température pourra devenir un axe secondaire ultérieur si les résultats spectraux justifient une formulation thermodynamique.

## 8. Coordonnée énergétique

Comparer directement des énergies absolues entre géométries ou spins différents peut être trompeur, car l'échelle et l'étendue du spectre changent avec le système.

Level 2 devra donc examiner une coordonnée spectrale normalisée, par exemple :

\[
\epsilon = \frac{E-E_{\min}}{E_{\max}-E_{\min}}
\]

avec

\[
0 \le \epsilon \le 1,
\]

**uniquement si** `E_max` est réellement disponible et numériquement fiable dans le cas étudié.

Si le spectre complet n'est pas disponible, Level 2 ne devra pas prétendre utiliser cette normalisation. Une alternative basée sur rang spectral, quantile d'une fenêtre calculée ou densité locale d'états devra alors être explicitement conçue et pré-enregistrée.

Aucune convention n'est gelée par ce document.

## 9. Observables candidates

Le point de départ naturel reste le couple déjà étudié :

```text
PRIMARY CANDIDATE:
C_TT_conn

CONTROL CANDIDATE:
rho_QQ
```

`C_TT_conn` reste particulièrement intéressant parce qu'il est relationnel et ne dépend pas d'un choix de chemin minimal imposé par la distance combinatoire du graphe.

`rho_QQ` reste un contrôle utile pour vérifier si une éventuelle réorganisation est spécifique au canal de corrélation principal ou reflète plus largement l'organisation de la charge.

`G[P]` ne devient pas automatiquement admissible en Level 2 : son utilisation de chemins sélectionnés à partir de la structure du graphe peut réintroduire une circularité si l'on tente ensuite de parler de géométrie émergente.

## 10. Type d'analyse recherché

Level 2 doit privilégier des grandeurs continues décrivant la **structure globale** des corrélations plutôt qu'un nouveau seuil binaire arbitraire.

Familles de diagnostics envisageables, à auditer avant gel :

```text
- norme globale des corrélations connectées ;
- distribution des amplitudes hors diagonale ;
- dispersion entre classes de relations ;
- structure en valeurs singulières / rang effectif si mathématiquement justifié ;
- similarité entre matrices de corrélation appartenant à différents régimes ;
- robustesse inter-S de ces tendances.
```

Aucune de ces métriques n'est encore normative.

Le choix devra respecter une règle simple :

> une métrique n'est conservée que si elle mesure une propriété physique ou structurelle clairement interprétable et si son comportement nul peut être compris sans tuning post-hoc.

## 11. Ce que Level 2 doit éviter de reproduire de Level 1C

Level 2 ne doit pas dépendre de l'identification continue d'une branche spectrale unique entre deux Hamiltoniens différents.

Le problème Level 1C était :

```text
baseline branch
→ perturbation du Hamiltonien
→ retrouver exactement la même branche
→ mesurer la réponse
```

Level 2 doit être formulé plutôt comme :

```text
un seul Hamiltonien fixé
→ plusieurs régions du spectre
→ caractériser statistiquement/structurellement les observables
→ comparer les régimes
```

Cela ne supprime pas tous les problèmes d'identifiabilité, mais retire l'hypothèse la plus fragile révélée par Level 1C.

## 12. Robustesse en S

Le spin de lien `S` conserve le même rôle méthodologique que dans Level 1 :

```text
S = finite-link truncation control
```

et jamais :

```text
S = spatial dimension
```

Une tendance observée dans un régime spectral ne pourra être considérée comme robuste que si elle ne disparaît pas immédiatement entre les valeurs de `S` retenues pour le contrôle.

Même dans ce cas :

```text
robustness between finite S values
!=
proof of S -> infinity convergence
```

## 13. Critère de succès scientifique

Level 2 ne nécessite pas de découvrir une géométrie pour réussir.

Un résultat positif minimal serait :

> montrer de manière reproductible qu'au moins une caractéristique relationnelle pré-enregistrée varie systématiquement avec le régime spectral, avec une tendance compatible entre les contrôles de troncature retenus.

Un résultat négatif valide serait :

> aucune dépendance structurée au régime spectral n'est détectée dans le périmètre accessible avec les observables et contrôles pré-enregistrés.

Un résultat inconclusif valide serait :

> les limitations de spectre, de statistiques d'états, de comparaison inter-S ou de résolution numérique empêchent de distinguer ces deux situations.

## 14. Géométrie : volontairement hors du premier test

Même si un régime spectral particulier présente une structure remarquable, Level 2 ne doit pas immédiatement ajuster :

```text
ligne
cercle
sphère
tore
métrique euclidienne
```

Le premier test doit établir l'existence éventuelle d'une **organisation dépendante du régime** avant toute reconstruction géométrique.

Une phase géométrique future ne serait ouverte que si les données montrent qu'il existe quelque chose de suffisamment stable et non trivial à reconstruire.

## 15. Lien avec l'hypothèse générale Cosmobox

Le programme de recherche plus large envisage qu'espace, temps, gravité et éventuellement matière puissent être des descriptions effectives de comportements collectifs d'un substrat relationnel plus fondamental.

Level 2 ne teste qu'un fragment très limité de cette idée :

```text
régime spectral
      ↓
organisation relationnelle différente ?
```

Il ne teste pas :

```text
organisation relationnelle
→ espace émergent
→ temps émergent
→ gravité
→ matière
```

Une éventuelle dépendance au régime énergétique serait seulement un indice qu'un même substrat quantique peut supporter plusieurs formes d'organisation collective.

## 16. Non-claims

Aucun résultat de Level 2, dans le périmètre défini ici, ne devra être présenté comme preuve de :

```text
- transition cosmologique réelle ;
- refroidissement de l'Univers ;
- émergence de l'espace ou du temps ;
- géométrie classique ;
- gravité ou courbure ;
- matière émergente ;
- dimension spatiale ;
- topologie émergente ;
- limite thermodynamique ;
- convergence S -> infini.
```

## 17. Séquençage proposé

Le séquençage scientifique de Level 2 est volontairement court :

```text
L2-A  cadrage et audit des données/spectres accessibles
  ↓
L2-B  définition des régimes spectraux et observables statistiques
  ↓
L2-C  pré-enregistrement de la première campagne
  ↓
L2-D  implémentation minimale
  ↓
L2-E  exécution normative
  ↓
L2-F  analyse et clôture
```

Ce document ouvre uniquement **L2-A**.

Aucun manifeste, aucune grille numérique, aucun seuil, aucune campagne et aucune implémentation ne sont autorisés par ce seul cadrage.

## 18. Première décision à prendre après ce cadrage

La prochaine question n'est pas « quel code écrire ? » mais :

> **Quelle portion du spectre est réellement accessible, avec quelles informations par état ou par multiplet, sur les systèmes actuels, sans introduire une nouvelle approximation qui masquerait précisément la dépendance énergétique que nous voulons mesurer ?**

La première action après acceptation de ce document doit donc être un **audit scientifique read-only des capacités spectrales actuelles** : spectre complet ou partiel selon géométrie/spin, nombre de groupes accessibles, observables déjà persistées par groupe, et coût réel d'une extension vers le milieu ou le haut du spectre.

Ce résultat déterminera le design expérimental de Level 2 ; il ne doit pas être présupposé.