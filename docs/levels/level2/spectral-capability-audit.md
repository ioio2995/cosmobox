# Audit scientifique des capacités spectrales — Level 2

Statut : **audit L2-A — read-only sur l'implémentation existante**

Base scientifique : `docs/levels/level2/conceptual-framing.md`.

Cet audit répond à la question ouverte par le cadrage Level 2 : quelle portion du spectre Cosmobox peut-il réellement calculer et caractériser aujourd'hui, sans introduire une nouvelle approximation susceptible de masquer la dépendance énergétique recherchée ?

Aucun résultat scientifique nouveau n'est produit ici. Aucun calcul n'est relancé. L'audit porte uniquement sur les capacités déjà présentes dans le code et sur les dimensions déjà gelées dans le manifeste Level 1B.

## 1. Conclusion principale

Sur le sous-ensemble actuellement pertinent pour Level 2 — `triangle`, `ring4`, `ring5`, avec `S in {1,2,3}` — **le spectre complet est numériquement accessible par le chemin dense déjà existant**.

La dimension maximale de ces neuf cas est :

```text
ring5, S=3 : dimension = 1504
```

alors que la politique actuelle de `SpectrumOptions` fixe :

```text
max_dense_dimension = 2000
```

Tous ces cas passent donc par `numpy.linalg.eigh`.

Point crucial pour Level 2 : le chemin dense calcule déjà l'eigendecomposition **complète** de `H_total`, puis tronque seulement ce qui est conservé dans le rapport à `n_eigenvalues`.

Autrement dit : dans les cas ci-dessus, passer d'une fenêtre basse de 16/20/24 valeurs propres au spectre complet ne change pas la nature du solveur spectral et ne demande pas une nouvelle approximation. Le coût principal de l'eigendecomposition complète est déjà payé par `np.linalg.eigh`; ce qui augmente est surtout la quantité d'eigenpaires conservées, diagnostiquées et ensuite traitées par les observables Level 1.

Cette constatation change fortement le design possible de Level 2 : il n'est pas nécessaire de construire une méthode approximative pour atteindre artificiellement le milieu ou le haut du spectre sur ces systèmes.

## 2. Dimensions actuellement documentées

Le manifeste Level 1B fournit les dimensions physiques suivantes :

```text
triangle:
  S=1   48
  S=2   88
  S=3  128

ring4:
  S=1  152
  S=2  292
  S=3  432

ring5:
  S=1  496
  S=2 1000
  S=3 1504
```

Toutes satisfont `dimension <= 2000`.

Les fenêtres historiques Level 1B (`16`, `20`, `24`) étaient donc des **fenêtres de restitution et de production scientifique**, pas une limite imposée par l'algorithme spectral dense lui-même.

## 3. Ce que le solveur sait déjà fournir

Pour chaque cas dense, l'implémentation actuelle :

1. construit `H_total` dans le sous-espace physique exact ;
2. exécute `np.linalg.eigh(H_total.toarray())` ;
3. obtient l'ensemble des valeurs propres et vecteurs propres ;
4. conserve seulement les `k = min(n_eigenvalues, dimension)` premières eigenpaires ;
5. calcule pour chaque eigenpaire conservée :
   - valeur propre ;
   - résidu `||H psi - E psi||` ;
   - espérance de chacun des quatre termes du Hamiltonien ;
   - contrôle de cohérence de la somme des énergies ;
6. regroupe les eigenvaleurs conservées en multiplets spectraux via la tolérance de dégénérescence.

`build_level0_report_with_eigenvectors` peut en outre restituer les vecteurs propres correspondant exactement aux eigenpaires publiées, sans seconde diagonalisation.

Il suffit donc conceptuellement, pour un cas Level 2 plein spectre, de demander :

```text
n_eigenvalues = physical_dimension
```

pour conserver le spectre complet déjà calculé par le chemin dense.

## 4. Conséquence sur la coordonnée énergétique

Le cadrage Level 2 envisageait avec prudence :

```text
epsilon = (E - E_min) / (E_max - E_min)
```

Cette coordonnée devient **exactement disponible** pour les neuf cas ci-dessus dès lors que le spectre complet est conservé.

Il n'est donc pas nécessaire, sur ce périmètre, de remplacer `E_max` par une estimation, un quantile d'une fenêtre tronquée ou une densité d'états extrapolée.

Level 2 peut conserver deux coordonnées descriptives complémentaires :

```text
epsilon : position énergétique normalisée exacte dans [0,1]
q       : fraction cumulative des états dans le spectre, pondérée par multiplicité
```

`epsilon` décrit la position en énergie ; `q` décrit la position dans la population spectrale. Elles ne sont pas équivalentes lorsque la densité d'états varie fortement.

Aucune des deux ne doit être interprétée comme une distance spatiale ou un temps.

## 5. Capacités d'observables déjà présentes

L'infrastructure Level 1 sait déjà construire, pour un `SpectralGroupState` :

```text
C_QQ_raw(i,j)
rho_QQ(i,j)
C_TT_raw(i,j)
C_TT_conn(i,j)
```

pour les paires de sites, ainsi que le diagonal :

```text
C_TT_conn(i,i)
```

Elle sait traiter un multiplet complet par l'espérance canonique du multiplet et distingue explicitement les sous-espaces partiels.

Elle sait également produire les labels de symétrie, les observables habillées dépendant d'un chemin et plusieurs invariants de saveur. Ces derniers ne sont pas nécessaires à la première expérience Level 2.

Le point important est donc : **les primitives nécessaires à une matrice complète `C_TT_conn` et au contrôle `rho_QQ` par groupe spectral existent déjà.**

## 6. Limitation réelle de l'infrastructure Level 1B

Le runner Level 1B ne produit pas ces observables pour tous les groupes du spectre.

Il construit bien la séquence complète des groupes présents dans la fenêtre calculée, mais il produit ensuite les observables uniquement pour les groupes sélectionnés par les `target_groups` du manifeste (`fundamental`, `first_excited`, labels de saveur, etc.).

Cette architecture était correcte pour Level 1B, mais elle ne convient pas directement à Level 2.

Level 2 ne doit donc **pas** réutiliser le mécanisme de sélection de cibles comme définition de ses données.

La nouvelle unité naturelle est :

```text
chaque multiplet spectral complet du spectre complet
```

avec ses coordonnées `(epsilon, q)` et ses observables relationnelles.

Cela évite précisément le problème de Level 1C : aucune branche n'a besoin d'être suivie entre deux Hamiltoniens différents.

## 7. Coût réel attendu

### 7.1 Diagonalisation

Pour les neuf cas du manifeste Level 1B : pas de nouvelle méthode spectrale nécessaire.

Le chemin dense effectue déjà l'eigendecomposition complète avant troncature de restitution.

Le passage au plein spectre n'augmente donc pas l'ordre de complexité du solveur spectral dans ces cas.

### 7.2 Diagnostics par eigenpaire

Le coût augmente linéairement avec le nombre d'eigenpaires conservées pour les résidus et les espérances des termes du Hamiltonien.

C'est un coût réel mais conceptuellement simple.

### 7.3 Observables relationnelles

C'est ici que se trouve probablement le coût supplémentaire principal de Level 2.

Le runner historique reconstruit actuellement plusieurs opérateurs locaux et calcule beaucoup de familles d'observables pour chaque groupe sélectionné. Le faire naïvement pour tous les groupes du spectre et toutes les familles Level 1 serait inutilement coûteux.

La première campagne Level 2 doit donc rester volontairement étroite :

```text
PRIMARY = C_TT_conn
CONTROL = rho_QQ
```

et ne pas produire `G[P]`, les diagnostics de chemins, les statistiques d'orbites ou les invariants de saveur tant qu'ils ne sont pas nécessaires à la question énergétique.

## 8. Proposition de représentation scientifique par groupe

Pour chaque multiplet complet `g`, conserver :

```text
spectral_group_index
multiplicity
E_rep
E_min_group
E_max_group
epsilon
q_low
q_high
q_mid
C_TT_conn matrix
rho_QQ matrix / nullity mask
```

La pondération par `multiplicity` est essentielle : une moyenne de régime censée représenter les états du spectre doit compter chaque état, pas chaque multiplet comme une unité arbitrairement égale.

## 9. Métriques structurelles proposées pour L2-B

Aucun seuil binaire de « réponse physique » ne doit être réintroduit.

Pour `C_TT_conn`, deux diagnostics simples ont une interprétation directe :

### 9.1 Amplitude relationnelle hors diagonale

```text
TT_OFFDIAG_RMS = sqrt(mean_{i != j} C_TT_conn(i,j)^2)
```

Cette quantité mesure l'amplitude typique des corrélations de saveur entre sites distincts.

### 9.2 Rapport relationnel / local

```text
TT_RELATIONAL_RATIO =
    sqrt(sum_{i != j} C_TT_conn(i,j)^2)
    / sqrt(sum_i C_TT_conn(i,i)^2)
```

si le dénominateur est non nul.

Cette quantité est dimensionless et distingue une augmentation générale des fluctuations locales d'une redistribution vers les corrélations entre sites.

Pour `rho_QQ`, le contrôle naturel est :

```text
RHO_OFFDIAG_RMS = sqrt(mean_{i != j, numeric} rho_QQ(i,j)^2)
```

avec conservation explicite de la fraction de paires nulles. Une nullité de `rho_QQ` n'est jamais remplacée par zéro.

Ces trois métriques sont candidates pour pré-enregistrement ; elles ne sont pas encore normatives dans cet audit.

## 10. Régimes spectraux : recommandation

Je ne recommande pas de commencer par des seuils arbitraires en `epsilon`.

Le design le plus robuste est de conserver d'abord chaque multiplet comme point dans le spectre, puis de définir des régimes descriptifs par **fraction cumulative d'états** :

```text
LOW  : q in [0, 1/3)
MID  : q in [1/3, 2/3)
HIGH : q in [2/3, 1]
```

avec affectation d'un multiplet par son `q_mid`.

Avantages :

- les trois régimes contiennent par construction des quantités d'états comparables ;
- la densité d'états ne vide pas artificiellement les bords ;
- aucune énergie particulière n'est choisie après observation des corrélations ;
- `epsilon` reste disponible comme coordonnée continue indépendante.

Les analyses principales devraient cependant conserver les métriques **continues en fonction de `epsilon` et `q`** ; LOW/MID/HIGH ne serviraient qu'à une synthèse pré-enregistrée facilement lisible.

## 11. Contrôle inter-S sans tracking de branche

Level 2 ne doit pas apparier une branche individuelle `S=3 -> S=2`.

La robustesse inter-S peut être définie au niveau des **profils de régime** :

```text
metric(epsilon or q) at S=2
vs
metric(epsilon or q) at S=3
```

ou des résumés multiplicité-pondérés LOW/MID/HIGH.

Ainsi, la question devient :

> la dépendance au régime spectral observée à `S=2` conserve-t-elle la même organisation qualitative à `S=3` ?

Ce test est transversal au spectre et ne nécessite aucune identité de branche inter-S.

Comme toujours :

```text
agreement S=2/S=3 != convergence S -> infinity
```

## 12. Périmètre expérimental recommandé

Pour la première campagne normative Level 2 :

```text
Hamiltonien : reference uniquement
n_flavors   : 2
charges ext : 0
geometries  : triangle, ring4, ring5
spin        : S=2, S=3
spectre     : complet
```

soit **6 cas physiques principaux**.

`S=1` peut être conservé dans un second rôle exploratoire/calibration, mais ne doit pas participer au verdict principal de robustesse puisque Level 0/1 ont déjà montré qu'il ne peut pas être traité comme un point de convergence établi.

Ce choix permet :

- trois géométries distinctes ;
- deux valeurs de troncature directement comparables ;
- un spectre complet exact au sens du modèle fini ;
- aucune perturbation `J0` ;
- aucun tracking de branche ;
- aucune reconstruction géométrique.

## 13. Préflight indispensable avant gel L2-C

Une seule étape de calcul exploratoire est encore nécessaire avant le pré-enregistrement définitif : mesurer le **coût et le nombre réel de groupes complets** sur les six cas proposés avec `n_eigenvalues = physical_dimension`.

Ce préflight ne doit produire aucun verdict physique et ne doit pas analyser les valeurs de `C_TT_conn` ou `rho_QQ`.

Il doit seulement rapporter :

```text
dimension
solver_method
wall time / mémoire si disponible
computed_eigenvalues
number_of_spectral_groups
number_of_complete_multiplets
number_of_partial_subspaces
multiplicity distribution
E_min
E_max
```

Puis, sur un nombre très limité de groupes synthétiques ou de cas de test, vérifier que la production de `C_TT_conn`/`rho_QQ` pour tous les groupes est techniquement viable sans lancer la campagne scientifique.

## 14. Décision L2-A proposée

```text
FULL_SPECTRUM_FOR_LEVEL2_CORE_CASES = AVAILABLE
NEW_SPECTRAL_APPROXIMATION_REQUIRED = NO
E_MAX_EXACTLY_AVAILABLE = YES
PRIMARY_OBSERVABLE = C_TT_conn
CONTROL_OBSERVABLE = rho_QQ
BRANCH_TRACKING_REQUIRED = NO
PHASE_G = OUT_OF_SCOPE
NEXT_STEP = FULL_SPECTRUM_RESOURCE_PREFLIGHT
```

Cette décision est limitée aux cas `triangle/ring4/ring5`, `S=2/3`, dont les dimensions restent sous le seuil dense actuel. Elle ne doit pas être extrapolée à `disk7` ou à de futurs systèmes de dimension supérieure.