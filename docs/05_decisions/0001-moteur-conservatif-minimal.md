# 0001. Moteur conservatif minimal pour EXP-0001

## Statut

Proposée — corrections de revue scientifique intégrées, en attente de
validation finale.

## Problème traité

`docs/research/0001-modele-minimal-reseau-au-repos.md` (spécification
scientifique du modèle minimal — ce n'est pas un ADR, voir note de
terminologie en fin de document) et
`experiments/EXP-0001-propagation-perturbation-locale.md` définissent un
modèle de référence explicitement **sans** amortissement, sans facteur de
déformation piloté, sans flux signé et sans cycle tétraédrique, intégré par
un schéma symplectique ou Verlet, avec suivi quantitatif de la conservation
d'énergie.

Le solveur actuel (`cosmobox/core/mechanics.py`) ne satisfait aucune de ces
exigences :

- il applique un amortissement (`cfg.damping`) actif par défaut ;
- il fait évoluer un `deformation_factor` par liaison (`update_factors`),
  piloté par une notion d'« activité » issue de `physics/particle.py`
  (flux signé, cycle tétraédrique) — exactement ce que le modèle minimal
  exclut ;
- à chaque sous-pas, il **recentre de force** la vitesse moyenne et la
  position moyenne du réseau (`matrix.velocities -= matrix.velocities.mean(...)`,
  puis idem sur `matrix.positions`) — une correction de centre de masse
  non déclarée, alors que le modèle minimal §10.2 exige qu'elle soit soit
  désactivée en configuration de référence, soit explicitement enregistrée
  comme force externe ;
- il ne calcule l'énergie que pour le dernier sous-pas (terme élastique
  seul, sans énergie cinétique), sans suivi temporel ni erreur relative à
  l'énergie injectée — donc aucun contrôle de conservation possible.

Il faut décider comment obtenir un moteur capable d'exécuter EXP-0001 sans
casser le prototype existant, qui reste la référence pour les démonstrations
`--animate` actuelles et n'est pas encore désigné comme obsolète.

## Décision retenue

Ajouter un chemin de simulation conservatif minimal, séparé du prototype
existant, en réutilisant la couche géométrique **sous réserve de validation
géométrique automatisée** (voir section dédiée ci-dessous) :

**Réutilisé sous réserve de validation géométrique :**

- `DiamondMatrix._build_lattice` / `DiamondMatrix.__init__` : construction
  du réseau diamant (deux sous-réseaux CFC interpénétrés), découpe
  sphérique par `radius`, longueur de repos commune `c`, degré 4 pour les
  nœuds intérieurs — correspond a priori au modèle minimal §3, mais n'est
  pas encore couvert par des tests d'invariants automatisés.

**Nouveau, non partagé avec le prototype :**

- `cosmobox/physics/elasticity.py` — énergie et force d'une liaison
  purement harmonique, `E_ij = 1/2 k (L_ij - c)^2`, sans facteur de
  déformation ni flux.
- `cosmobox/simulation/engine.py` — intégrateur vitesse-Verlet (leapfrog),
  aucun amortissement par défaut, aucune correction de centre de masse
  implicite (translation globale mesurée, jamais soustraite sauf variante
  explicitement identifiée), conditions aux limites paramétrables
  (libre / fixe / couche absorbante) au sens d'EXP-0001 §4.3 et
  modèle minimal §9.
- `cosmobox/physics/diagnostics.py` — énergie cinétique/élastique/totale
  par pas, quantité de mouvement totale, détection de front (seuil relatif
  + méthode de contrôle par maximum local), largeur radiale du paquet
  d'énergie, mesures directionnelles (coquilles radiales, cônes
  directionnels), comptabilité énergétique spécifique à chaque type de
  frontière (voir section dédiée).
- `experiments/exp0001/runner.py` (ou équivalent en `cosmobox/io/`) —
  orchestre la campagne EXP-0001 §8 (contrôle zéro, convergence temporelle,
  convergence spatiale, anisotropie, frontières, linéarité en amplitude),
  supporte les différents types d'injection (voir section dédiée), et
  écrit l'arborescence de sortie spécifiée en §13 :
  `output/EXP-0001/<run-id>/{config.yaml,metadata.json,metrics.csv,summary.json,energy.png,propagation.png,anisotropy.png,animation.gif}`.

**Unités et échelles explicites.** Le triplet minimal `c` (longueur de
repos), `m` (masse nodale), `k` (raideur) définit une échelle de temps
naturelle `t0 = sqrt(m / k)` et une échelle de vitesse `v0 = c * sqrt(k / m)`.
Configuration de référence en unités réduites : `c0 = 1`, `m0 = 1`, `k0 = 1`.
Le nom `c` reste réservé à la longueur de repos ; aucune vitesse issue du
modèle ne doit être nommée `c`, pour éviter toute confusion avec la vitesse
de la lumière — une éventuelle vitesse limite émergente recevra un nom
distinct si et seulement si elle est observée.

**Intégrateur — pas de promesse de conservation exacte.** Le schéma
vitesse-Verlet est symplectique pour un système hamiltonien à forces
dépendant uniquement des positions ; il produit une erreur d'énergie
**bornée et oscillante**, pas une énergie strictement constante. Les
critères de validation (repris dans `physics/diagnostics.py` et dans les
critères de réussite d'EXP-0001 §14) portent donc sur :

- l'absence de dérive séculaire significative de l'énergie ;
- la diminution de l'erreur lorsque `dt` diminue ;
- l'ordre de convergence observé, comparé à l'ordre attendu du schéma ;
- la stabilité sur la durée complète de l'expérience.

**Non touché par cette décision :**

- `cosmobox/core/mechanics.py`, `cosmobox/physics/particle.py`,
  le flux CLI `--animate` existant : laissés en l'état, car ils restent la
  seule voie de démonstration actuelle et une migration complète de
  l'architecture (voir `04_architecture.md`) est un chantier séparé, non
  requis pour livrer EXP-0001.

## Risque physique identifié

Un réseau diamant à interactions centrales de premier voisin uniquement
peut présenter des modes mous ou une rigidité de cisaillement insuffisante :
chaque nœud intérieur ne porte que quatre liaisons en trois dimensions, ce
qui peut être insuffisant pour supprimer tous les mécanismes non rigides
dans un réseau générique de ressorts centraux.

Cela ne rend pas le réseau inutilisable, mais EXP-0001 doit le caractériser
avant toute interprétation : stabilité mécanique au repos, existence de
modes à fréquence nulle en dehors des translations/rotations globales,
réponse à une perturbation transversale, réponse à une déformation de
cisaillement, déplacements importants pour une énergie élastique faible.

`physics/diagnostics.py` doit donc exposer, en plus des métriques de
propagation déjà prévues, de quoi détecter ces signatures (ex. rapport
déplacement/énergie anormalement élevé, réponse transversale non amortie).
Aucun terme stabilisateur (ressort angulaire, contrainte volumique,
couplage multi-voisins) ne doit être ajouté implicitement pour corriger ce
comportement — il doit d'abord être observé et mesuré, pas masqué.

## Comptabilité énergétique aux frontières

Les trois variantes de frontière prévues par EXP-0001 §4.3 / modèle minimal
§9 ne partagent pas le même bilan et `diagnostics.py` doit les traiter
distinctement plutôt que de calculer une seule grandeur « énergie totale » :

- **Frontière libre** — le système est isolé (aux erreurs numériques près) :
  `E_tot = E_cin + E_élast` doit rester approximativement constante, et la
  quantité de mouvement totale doit rester constante après l'impulsion
  initiale.
- **Frontière fixe** — les nœuds immobilisés constituent une contrainte
  externe ; la quantité de mouvement du domaine mobile n'est pas
  nécessairement conservée. Il faut mesurer les forces de réaction aux
  nœuds fixes, l'impulsion transmise à la frontière, et le cas échéant le
  travail de la contrainte.
- **Couche absorbante** — l'énergie mécanique du réseau n'est
  volontairement pas conservée. Une grandeur distincte `E_absorbée(t)` doit
  être enregistrée, avec vérification `E_réseau(t) + E_absorbée(t) ≈
  E_initiale`. Sans ce suivi séparé, une couche absorbante mal implémentée
  serait indiscernable d'une erreur numérique de conservation.

## Types d'injection

Le runner EXP-0001 doit distinguer au minimum quatre formes d'injection,
qui ne répondent pas à la même question :

1. **impulsion sur un nœud unique** — injecte une quantité de mouvement
   globale non nulle ; le centre de masse du réseau se déplace en
   conséquence, et ce déplacement est physique — il ne doit **jamais** être
   soustrait ni traité comme un artefact numérique ;
2. **impulsion compensée** (quantité de mouvement totale nulle) — permet
   d'étudier la propagation locale sans translation globale du réseau ;
3. **perturbation radiale symétrique** ;
4. **perturbation transversale** — utile en particulier pour le risque de
   modes mous décrit ci-dessus.

Chaque exécution doit enregistrer explicitement le type d'injection utilisé
dans `metadata.json`, pour éviter de comparer des résultats répondant à des
questions différentes.

## Alternatives étudiées

- **Adapter `MechanicsEngine` avec des drapeaux (`damping=0`,
  `factor_evolution=False`, etc.) pour désactiver les comportements
  exclus.** Écarté : multiplie les branches conditionnelles dans un code
  déjà couplé (recentrage CoM et facteurs de déformation entrelacés dans la
  même boucle de sous-pas), et rend impossible de garantir par construction
  qu'aucun comportement exclu ne reste actif par erreur — contraire à
  l'exigence de traçabilité du modèle minimal (§14 : toute variable ajoutée
  doit justifier son énergie).
- **Migrer immédiatement toute l'architecture vers le layout cible
  (`core/particles/simulation/renderer/io`) avant d'écrire EXP-0001.**
  Écarté pour cette décision : périmètre plus large que ce qui est
  nécessaire pour livrer EXP-0001, retarderait la première expérience
  reproductible. La migration complète reste planifiée séparément.
- **Réécrire `DiamondMatrix` from scratch dans le nouveau module.** Écarté :
  la construction géométrique existante satisfait a priori les invariants
  requis (modèle minimal §10.1) ; la dupliquer introduirait un risque de
  divergence entre deux implémentations de la même géométrie. Cette
  réutilisation reste conditionnée à la validation géométrique décrite
  plus haut plutôt qu'affirmée sans preuve.

## Justification

Séparer le chemin conservatif du prototype permet de livrer EXP-0001 sans
risquer de régression sur les démonstrations existantes, tout en évitant
d'accumuler de la dette dans `mechanics.py` (drapeaux pour désactiver des
comportements qui n'auraient jamais dû être couplés). Réutiliser la
géométrie — une fois validée — évite une divergence entre deux réseaux
diamant. Le nouveau code est placé directement dans les emplacements du
layout cible (`physics/`, `simulation/`) pour que la migration future n'ait
qu'à déplacer/supprimer le prototype, pas à réécrire ce qui vient d'être
créé.

## Conséquences

- Deux moteurs mécaniques coexistent temporairement dans le dépôt : le
  prototype amorti/piloté par facteur (legacy, non touché) et le moteur
  conservatif minimal (nouveau). Ceci doit être documenté dans
  `04_architecture.md` pour éviter toute confusion sur lequel utiliser.
- `physics/particle.py` (cycles tétraédriques, flux signé) n'est **pas**
  utilisé par EXP-0001 — aucune notion de particule n'entre dans cette
  expérience, conformément au modèle minimal.
- Avant tout calcul physique sur le nouveau moteur, `DiamondMatrix` doit
  passer une suite de tests d'invariants géométriques dédiée : longueur de
  repos identique pour toutes les arêtes, absence de doublon d'arête,
  absence de nœud isolé, connexité du réseau, degré quatre pour les nœuds
  intérieurs, classification explicite des nœuds de frontière, absence de
  biais dans la sélection du nœud central, identification correcte du
  centre géométrique et des deux sous-réseaux. Si un de ces invariants
  échoue, `DiamondMatrix` devra être corrigé ou remplacé avant EXP-0001.
- La comptabilité énergétique différenciée par type de frontière et le
  support de plusieurs types d'injection ajoutent de la complexité au
  runner et aux diagnostics par rapport à une version « énergie totale
  unique » — accepté car nécessaire pour ne pas confondre un défaut
  numérique avec un comportement physique attendu (couche absorbante,
  translation du centre de masse).
- Nécessite d'ajouter des tests dédiés : stabilité du contrôle zéro,
  décroissance de la dérive d'énergie avec `dt` avec l'ordre de convergence
  attendu, non-dérive de la quantité de mouvement hors injection (cas
  frontière libre uniquement).
- Une future migration complète de l'architecture devra statuer sur le sort
  du prototype (`core/mechanics.py`, `physics/particle.py`) : conservation
  en tant que mode de démonstration explicitement non scientifique, ou
  suppression. Cette décision n'est pas prise ici.

## Note de terminologie

`docs/research/0001-modele-minimal-reseau-au-repos.md` n'est pas un ADR :
c'est un document de spécification scientifique du modèle expérimental,
numéroté dans la séquence de `docs/research/`. Le présent document est un
ADR logiciel, numéroté séparément dans `docs/05_decisions/`. Les deux
partagent le numéro `0001` par coïncidence de séquences indépendantes ; ce
document évite désormais l'expression ambiguë « ADR 0001 physique » et
référence systématiquement le fichier par son chemin complet.
