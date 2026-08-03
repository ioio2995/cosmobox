# EXP-0001 — Synthèse de l'implémentation du moteur minimal

## Statut

Étapes 1 à 9 de l'ordre d'implémentation défini par
[`docs/05_decisions/0001-moteur-conservatif-minimal.md`](../docs/05_decisions/0001-moteur-conservatif-minimal.md)
complètes et validées (revue par étape, cf. historique du dépôt).

## Objet de ce document

Ce document synthétise, en un seul endroit et de façon reproductible,
l'ensemble des résultats obtenus lors de l'implémentation du moteur
conservatif minimal spécifié par
[`docs/research/0001-modele-minimal-reseau-au-repos.md`](../docs/research/0001-modele-minimal-reseau-au-repos.md),
à travers l'expérience de propagation
([`EXP-0001-propagation-perturbation-locale.md`](EXP-0001-propagation-perturbation-locale.md))
et ses extensions (étapes 6 à 9, ajoutées en cours de revue : orientation,
rigidité, cisaillement, dynamique transverse, conditions aux limites).

Il ne remplace ni l'ADR, ni la spécification scientifique, ni les fiches
d'expérience individuelles — il en donne une vue d'ensemble, avec les
chiffres exacts mesurés et les modules/tests qui les produisent, pour
qu'un lecteur puisse reproduire ou vérifier chaque résultat sans
reparcourir l'historique complet des revues.

## Portée couverte

| Étape | Objet | Module(s) | Test(s) |
|---|---|---|---|
| 1 | Validation géométrique du réseau diamant | `core/matrix.py` (réutilisé, non modifié) | `test_diamond_matrix_invariants.py` |
| 2 | Moteur conservatif, velocity-Verlet, frontière libre | `physics/elasticity.py`, `physics/diagnostics.py`, `simulation/engine.py` | `test_conservative_engine.py` |
| 3 | Injection compensée, conservation formelle | `simulation/injection.py`, `simulation/analysis.py` | `test_compensated_injection.py` |
| 4 | Convergence en `dt` | `simulation/convergence.py` | `test_dt_convergence.py` |
| 5 | Propagation en frontière libre | `physics/propagation.py` | `test_propagation.py` |
| 6 | Orientation de la source, covariance de symétrie | `core/symmetry.py`, `physics/anisotropy.py` | `test_orientation_dependence.py`, `test_lattice_symmetry.py` |
| 7A | Matrice de rigidité, noyau linéarisé | `physics/rigidity.py` | `test_rigidity.py` |
| 7B-1 | Cisaillement affine statique | `physics/shear.py` | `test_shear.py` |
| 7B-2 | Relaxation intérieure non affine | `physics/relaxation.py` | `test_relaxation.py` |
| 7B-3 | Réponse transverse dynamique vs noyau | `physics/transverse.py` | `test_transverse.py` |
| 8 | Linéarité en amplitude (injection longitudinale) | `physics/amplitude_linearity.py` | `test_amplitude_linearity.py` |
| 9A | Frontière fixe | `simulation/boundary_engine.py`, `physics/reflection.py` | `test_boundary_reflection.py` |
| 9B | Frontière absorbante | `simulation/absorbing_engine.py` | `test_absorbing_boundary.py` |

**Non implémenté** (hors périmètre de cette synthèse) : runner
d'expérience unifié avec arborescence de sortie standardisée
(`output/EXP-0001/<run-id>/...` telle que décrite dans la spécification
originale) ; formes d'injection radiale symétrique et impulsion sur
nœud unique non compensée ; module de cisaillement effectif normalisé
par le volume ; extrapolation de Richardson indépendante pour la
référence de convergence en `dt`.

## Configuration de référence

- **Réseau** : `DiamondMatrix`, découpe sphérique. Tailles utilisées :
  invariants géométriques vérifiés sur `radius` = 3.0, 5.5, 8.2, 12.0
  (17 à 915 nœuds) ; configurations de travail standard `radius=5.5`
  (87 nœuds, 136 arêtes) et `radius=8.2` (293 nœuds, 500 arêtes).
- **Élasticité** : loi harmonique `E = 1/2 k (L-c)²`, avec `k=1.0` et
  `c=matrix.c≈1.7321` comme longueur de repos commune dans le système
  de coordonnées actuel.
- **Masse nodale** : `m=1.0`. Les résultats sont exprimés dans les
  unités numériques du modèle ; aucune identification de `c` avec une
  vitesse physique n'est faite.
- **Intégrateur** : velocity-Verlet, `dt` de 0.005 à 0.04 selon
  l'étude ; ordre de convergence 2 vérifié (étape 4).
- **Injection de référence** : paire compensée (`ΔP=0` exact), nœud
  central intérieur (degré 4, unique plus proche de l'origine) et son
  voisin sélectionné par tri lexicographique des directions de
  liaison — jamais un indice arbitraire.

## Résultats principaux, par étape

Chaque énoncé ci-dessous porte sur **le domaine, la durée et les
paramètres effectivement testés** — voir la section Limites pour ce qui
n'a pas été généralisé.

### 1 — Géométrie

Longueur de repos uniforme, absence de doublon/nœud isolé, connexité,
degré ≤ 4, bipartition exacte entre les deux sous-réseaux CFC (0 arête
intra-sous-réseau, recalculée indépendamment par parité de
coordonnées), centre géométrique à l'origine, sélection non ambiguë du
nœud central — vérifiés sur 4 tailles de réseau. `DiamondMatrix` n'a
nécessité aucune correction.

### 2-4 — Moteur conservatif et convergence

Solveur séparé du prototype historique (`core/mechanics.py`, non
modifié : amortissement, facteur de déformation et recentrage de
centre de masse implicite y restent actifs et hors périmètre du moteur
minimal). Ordre de convergence observé : **2.001, 2.000, 2.000** sur
trois doublements successifs de `dt` (0.04 → 0.005, `T=2.0`), erreur
énergétique relative maximale de `9.4×10⁻⁴` à `1.5×10⁻⁵`. Conservation
de la quantité de mouvement et somme des forces internes nulle
vérifiées à chaque pas.

### 5 — Propagation

Distinction empirique entre deux observables qui ne mesurent pas la
même vitesse : un **front rapide** (seuil relatif au maximum global,
atteint la zone périphérique du domaine vers `t≈17` pour `radius=8.2`,
régression bruitée `R²≈0,45-0,60`) et le **transport en masse** (rayon
pondéré par l'énergie, pente `≈0,156-0,166` unité/temps, régression
propre `R²≈0,97-0,99`).

### 6 — Orientation et covariance

Les 4 directions tétraédriques sont reliées par des symétries exactes
du réseau fini (3 rotations de 180° autour des axes de coordonnées),
vérifiées nœud par nœud et arête par arête — pas supposées depuis le
réseau infini. Covariance de position **et** de vitesse entre
trajectoires simulées le long de directions reliées par symétrie,
vérifiée à `<10⁻⁹` près (mesuré `~10⁻¹⁵`-`10⁻¹⁶`). Énergie injectée
identique aux 4 directions (exact, par construction).

### 7A — Rigidité linéarisée

**Résultat principal** : le réseau à ressorts centraux entre premiers
voisins uniquement (coordination 4) est massivement sous-contraint au
niveau linéarisé. Le rang numérique de `B`, calculé par SVD, est égal
au nombre d'arêtes pour les trois tailles testées ; aucune redondance de
contrainte n'est détectée à la tolérance numérique utilisée :

| `radius` | ddl (`3N`) | arêtes | modes nuls | % ddl |
|---|---|---|---|---|
| 3.0 | 51 | 16 | 35 | 68,6 % |
| 5.5 | 261 | 136 | 125 | 47,9 % |
| 8.2 | 879 | 500 | 379 | 43,1 % |

Les 6 mouvements rigides vérifiés directement (`‖K·v‖ ≈ 10⁻¹⁶`).
Analyse invariante du sous-espace (projecteur, pas les vecteurs propres
individuels, dont l'interprétation mode-à-mode n'est pas fiable dans un
noyau aussi dégénéré) : **69,9 %** du poids du noyau porté par les
degrés de liberté de bord, contre **59,8 %** de nœuds effectivement de
bord — enrichi au bord mais pas exclusivement surfacique (existence
vérifiée d'un vecteur du noyau quasi purement intérieur et d'un autre
quasi purement de bord).

### 7B — Cisaillement et dynamique transverse

- **7B-1** (statique, non relaxé) : cisaillement affine global
  `x'=x+γy`. Coefficient quadratique mesuré `a2≈22,67` (`radius=5,5`),
  strictement positif malgré ~98 % de la norme du générateur de
  cisaillement située dans le noyau — fait d'algèbre linéaire vérifié
  numériquement : `uᵀKu` ne dépend que de la composante hors noyau,
  donc `a2` est identique pour la direction brute et sa version
  projetée (accord à `10⁻⁶` relatif). `a2` mesuré ≈ `a2` exact
  (`0,5·uᵀKu`) à `10⁻⁶` près.
- **7B-2** (relaxation intérieure, frontière fixée à sa position
  cisaillée) : deux définitions de frontière indépendantes
  (`degré<4` ; `r≥0,85R`). Rapport `ρ=E_relaxée/E_affine` constant en
  `γ` dans le régime linéaire (vérifié). Mesuré **0,353** (frontière
  par degré, 18 mécanismes intérieurs résiduels) et **0,176**
  (frontière par rayon, 29 mécanismes intérieurs) — accommodation
  substantielle du cisaillement par les mécanismes internes, mais
  rigidité quadratique résiduelle non nulle dans les deux cas.
- **7B-3** (dynamique) : impulsion transverse décomposée sur le noyau
  et son complément. Chevauchement noyau mesuré **≈34,6 %** pour les
  deux polarisations transverses testées, contre **<10⁻⁹** pour
  l'injection longitudinale des étapes 3 à 6. À énergie injectée égale
  (renormalisée) : ratio pic d'énergie élastique/injectée **≈0,017**
  pour la composante noyau, **≈0,898** pour son complément. Loi
  d'échelle mesurée pour la composante noyau : énergie élastique de
  pic `∝ vitesse^p`, `p≈3,9-4,0` sur 4 amplitudes, cohérent avec
  l'argument géométrique local `Bq=0 ⟹ δl=O(q²) ⟹ énergie=O(q⁴)`,
  sans démonstration analytique complète de la loi du pic dynamique
  sur une fenêtre temporelle finie.

### 8 — Linéarité en amplitude (injection longitudinale)

Sur `v=0,05` à `0,8` (`radius=8,2`, `T=15`, toutes les exécutions
confirmées à l'écart de la zone de prudence de frontière) : énergie
injectée exactement `∝ v²` (ordre mesuré **2,000000**). Pente de
propagation quasi indépendante de l'amplitude sur les 3 plus petites
vitesses (écart relatif **2,0 %**), croissant une fois les grandes
amplitudes incluses (**6,5 %**). Profils radiaux normalisés
superposables à petite amplitude, déviation RMS croissant
monotoniquement avec l'amplitude : **0 ; 0,0008 ; 0,0026 ; 0,0072 ;
0,0168**.

### 9 — Conditions aux limites

- **9A (fixe)** : nœuds de bord maintenus exactement (dérive position/
  vitesse `<10⁻¹²`). Bilan d'impulsion `ΔP_mobile = J_réaction` vérifié
  à `~10⁻¹⁵` près. Énergie mécanique bornée (`<10⁻³` relatif sur
  `T=80`). Comparaison agrégée (8 instants, `radius=5,5`, `T=80`) :
  fraction moyenne d'énergie en coquille externe (`r≥0,7R`) inférieure
  pour la frontière fixe que pour la frontière libre, aux deux
  définitions de masque — mais pas à chaque instant individuel pour le
  masque radial ; une inversion ponctuelle, compatible avec des
  interférences liées aux réflexions multiples, a été conservée plutôt
  que masquée par une assertion point par point.
- **9B (absorbante)** : bilan mécanique + absorbée fermé à `<10⁻³`
  (mesuré `~10⁻⁵`, non dégradé par le splitting de Strang). Étude de
  sensibilité (3 `γmax`, 2 exposants, 2 largeurs de couronne) :
  compromis non monotone confirmé, pas supposé — trop faible
  (`γmax=0,1`) absorbe **53 %**, intermédiaire (`γmax=2`) absorbe
  **71 %**, trop forte (`γmax=50`) absorbe **58 %** (compatible avec
  une réflexion à l'entrée de la couronne, sans que ce soit une
  observable isolée directement mesurée). Moyenne (8 instants) de la
  fraction d'énergie en coquille externe : absorbante (**0,056**) <
  fixe (**0,132**) < libre (**0,328**).

## Conclusions autorisées

Chaque énoncé porte sur le modèle numérique tel qu'implémenté (réseau
diamant, interactions centrales premiers voisins, domaines finis
testés) — aucun ne constitue une validation d'une particule, d'une
gravité émergente, ou d'une correspondance avec un vide physique.

1. Le moteur conservatif minimal implémenté satisfait les propriétés
   attendues d'un intégrateur symplectique : convergence d'ordre 2,
   conservation de la quantité de mouvement, erreur énergétique bornée
   et non séculaire sur les fenêtres testées.
2. Le réseau à interactions centrales de premiers voisins uniquement
   possède un sous-espace **extensif** de mécanismes infinitésimaux
   sans coût énergétique quadratique (43 à 69 % des degrés de liberté
   selon la taille testée), très au-delà des 6 mouvements rigides — au
   sens linéarisé, infinitésimal, sur les domaines finis testés, avec
   interactions centrales de premiers voisins uniquement.
3. Ce noyau n'est pas uniquement un artefact de surface : il contient
   des directions de déplacement presque entièrement portées par les
   nœuds intérieurs, tout en étant globalement enrichi sur les degrés
   de liberté de bord.
4. Certaines déformations globales particulières (le cisaillement
   affine testé) et certaines composantes d'excitation (le complément
   du noyau) conservent une rigidité élastique réelle et mesurable, y
   compris après relaxation non affine substantielle.
5. La réponse dynamique différentielle entre les injections
   longitudinale et transverse utilisées jusqu'ici s'explique en
   grande partie par leur projection respective sur le noyau
   linéarisé, pas seulement par leur orientation géométrique brute.
6. Le régime longitudinal à petite amplitude est compatible avec un
   comportement approximativement linéaire (énergie `∝v²`,
   superposition des profils, pente quasi indépendante de
   l'amplitude) ; des non-linéarités mesurables et croissantes
   apparaissent aux amplitudes plus élevées testées.
7. Les trois conditions de bord disposent d'une comptabilité
   énergétique adaptée. La quantité de mouvement est conservée pour la
   frontière libre et son échange avec la contrainte est explicitement
   comptabilisé pour la frontière fixe. La couche absorbante ferme
   correctement le bilan mécanique plus énergie dissipée. Elles se
   distinguent quantitativement par la quantité d'énergie mécanique
   qu'elles laissent circuler tardivement en périphérie du domaine.

## Limites explicites

- Les résultats de rigidité, covariance, cisaillement et dynamique
  transverse (étapes 6, 7, 9) portent principalement sur `radius=5,5`
  (87 nœuds), avec des vérifications ponctuelles à d'autres tailles
  limitées à la géométrie (étape 1) et à la rigidité linéarisée
  (étape 7A) — pas d'étude systématique de taille pour le module de
  cisaillement effectif, la loi d'échelle transverse, ou les seuils de
  réflexion/absorption.
- Le « front rapide » (mesure par seuil, étapes 5, 8, 9) reste une
  observable bruitée (`R²≈0,45-0,60`) ; les conclusions de vitesse
  s'appuient préférentiellement sur le rayon pondéré par l'énergie
  (`R²≥0,97`).
- Aucun flux radial signé n'a été mesuré directement ; les
  comparaisons de réflexion (9A, 9B) reposent sur des fractions
  d'énergie par coquille — une redistribution comparative, pas la
  trajectoire d'un front réfléchi identifié individuellement.
- Les interprétations mode-par-mode du noyau linéarisé (7A) sont
  explicitement écartées comme non robustes (dégénérescence à 125+
  dimensions) ; seules les quantités invariantes par changement de
  base (dimension, projecteur, poids de bord agrégé, plage de
  localisation extrémale) sont considérées fiables.
- La référence de convergence en `dt` (étape 4) utilise le pas le plus
  fin de la série testée comme référence provisoire, pas une
  extrapolation de Richardson indépendante ni une résolution
  analytique.
- Un seul type d'injection compensée (paire, vitesses opposées) a été
  testé de façon extensive ; les formes radiale symétrique et
  impulsion sur nœud unique non compensée, prévues par la
  spécification EXP-0001 originale, ne sont pas implémentées.
- Aucun runner d'expérience unifié ni arborescence de sortie
  standardisée (`output/EXP-0001/<run-id>/...`) n'existe encore ;
  chaque étape produit ses propres tables/CSV via des fonctions de
  sérialisation dédiées, dispersées par module (voir la colonne
  Module(s) de la table de portée ci-dessus).

## Questions laissées ouvertes

- Le réseau à ressorts centraux nécessite-t-il un terme stabilisateur
  (angulaire, volumique, multi-voisins) pour se comporter comme un
  milieu élastique conventionnel à grande échelle, ou le noyau
  extensif est-il une propriété à exploiter plutôt qu'à corriger ?
- Isotropie effective à grande échelle : non établie — seule la
  covariance exacte sous le groupe de symétrie discret du réseau fini
  a été vérifiée (étape 6), pas une isotropie continue à grande
  distance.
- Module de cisaillement effectif macroscopique : nécessite
  normalisation par le volume, étude de taille, condition aux limites
  explicitement fixée — non entrepris (mentionné comme prochaine étape
  possible lors de la revue de 7B-2).
- Dérivation analytique de la loi d'échelle `v⁴` pour la composante
  noyau, au-delà de l'argument géométrique qualitatif, et vérification
  à des amplitudes/durées au-delà de celles testées.
- Caractérisation quantitative (ordre dominant) de la non-linéarité
  longitudinale observée à grande amplitude (étape 8).
- Flux radial signé et corrélation signal incident/signal réfléchi
  (amélioration suggérée lors de la revue de 9A, non implémentée).
- Devenir du prototype historique (`core/mechanics.py`,
  `physics/particle.py`) : conservation comme mode de démonstration
  explicitement non scientifique, ou suppression — décision non prise
  (cf. ADR 0001, section Conséquences).

## Références

- [`docs/05_decisions/0001-moteur-conservatif-minimal.md`](../docs/05_decisions/0001-moteur-conservatif-minimal.md) — décision architecturale et ordre d'implémentation.
- [`docs/research/0001-modele-minimal-reseau-au-repos.md`](../docs/research/0001-modele-minimal-reseau-au-repos.md) — spécification scientifique du modèle minimal.
- [`EXP-0001-propagation-perturbation-locale.md`](EXP-0001-propagation-perturbation-locale.md) — spécification originale de l'expérience de propagation.
- Modules et tests : voir la table « Portée couverte » ci-dessus.
