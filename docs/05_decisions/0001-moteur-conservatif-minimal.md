# 0001. Moteur conservatif minimal pour EXP-0001

## Statut

Proposée

## Problème traité

`docs/research/0001-modele-minimal-reseau-au-repos.md` et
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
  (flux signé, cycle tétraédrique) — exactement ce que l'ADR 0001 physique
  exclut du modèle minimal ;
- à chaque sous-pas, il **recentre de force** la vitesse moyenne et la
  position moyenne du réseau (`matrix.velocities -= matrix.velocities.mean(...)`,
  puis idem sur `matrix.positions`) — une correction de centre de masse
  non déclarée, alors que l'ADR 0001 §10.2 exige qu'elle soit soit
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
existant, en réutilisant uniquement la couche géométrique déjà conforme au
modèle minimal :

**Réutilisé tel quel :**

- `DiamondMatrix._build_lattice` / `DiamondMatrix.__init__` : construction
  du réseau diamant (deux sous-réseaux CFC interpénétrés), découpe
  sphérique par `radius`, longueur de repos commune `c`, degré 4 pour les
  nœuds intérieurs — correspond point par point à l'ADR 0001 §3.

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
  directionnels).
- `experiments/exp0001/runner.py` (ou équivalent en `cosmobox/io/`) —
  orchestre la campagne EXP-0001 §8 (contrôle zéro, convergence temporelle,
  convergence spatiale, anisotropie, frontières, linéarité en amplitude) et
  écrit l'arborescence de sortie spécifiée en §13 :
  `output/EXP-0001/<run-id>/{config.yaml,metadata.json,metrics.csv,summary.json,energy.png,propagation.png,anisotropy.png,animation.gif}`.

**Non touché par cette décision :**

- `cosmobox/core/mechanics.py`, `cosmobox/physics/particle.py`,
  le flux CLI `--animate` existant : laissés en l'état, car ils restent la
  seule voie de démonstration actuelle et une migration complète de
  l'architecture (voir `04_architecture.md`) est un chantier séparé, non
  requis pour livrer EXP-0001.

## Alternatives étudiées

- **Adapter `MechanicsEngine` avec des drapeaux (`damping=0`,
  `factor_evolution=False`, etc.) pour désactiver les comportements
  exclus.** Écarté : multiplie les branches conditionnelles dans un code
  déjà couplé (recentrage CoM et facteurs de déformation entrelacés dans la
  même boucle de sous-pas), et rend impossible de garantir par construction
  qu'aucun comportement exclu ne reste actif par erreur — contraire à
  l'exigence de traçabilité de l'ADR 0001 physique (§14 : toute variable
  ajoutée doit justifier son énergie).
- **Migrer immédiatement toute l'architecture vers le layout cible
  (`core/particles/simulation/renderer/io`) avant d'écrire EXP-0001.**
  Écarté pour cette décision : périmètre plus large que ce qui est
  nécessaire pour livrer EXP-0001, retarderait la première expérience
  reproductible. La migration complète reste planifiée séparément.
- **Réécrire `DiamondMatrix` from scratch dans le nouveau module.** Écarté :
  la construction géométrique existante satisfait déjà exactement les
  invariants requis (§10.1 de l'ADR physique) ; la dupliquer introduirait un
  risque de divergence entre deux implémentations de la même géométrie.

## Justification

Séparer le chemin conservatif du prototype permet de livrer EXP-0001 sans
risquer de régression sur les démonstrations existantes, tout en évitant
d'accumuler de la dette dans `mechanics.py` (drapeaux pour désactiver des
comportements qui n'auraient jamais dû être couplés). Réutiliser la
géométrie évite une divergence entre deux réseaux diamant. Le nouveau code
est placé directement dans les emplacements du layout cible
(`physics/`, `simulation/`) pour que la migration future n'ait qu'à
déplacer/supprimer le prototype, pas à réécrire ce qui vient d'être créé.

## Conséquences

- Deux moteurs mécaniques coexistent temporairement dans le dépôt : le
  prototype amorti/piloté par facteur (legacy, non touché) et le moteur
  conservatif minimal (nouveau). Ceci doit être documenté dans
  `04_architecture.md` pour éviter toute confusion sur lequel utiliser.
- `physics/particle.py` (cycles tétraédriques, flux signé) n'est **pas**
  utilisé par EXP-0001 — aucune notion de particule n'entre dans cette
  expérience, conformément à l'ADR physique.
- Nécessite d'ajouter des tests dédiés : stabilité du contrôle zéro,
  décroissance de la dérive d'énergie avec `dt`, non-dérive de la quantité
  de mouvement hors injection.
- Une future migration complète de l'architecture devra statuer sur le sort
  du prototype (`core/mechanics.py`, `physics/particle.py`) : conservation
  en tant que mode de démonstration explicitement non scientifique, ou
  suppression. Cette décision n'est pas prise ici.
