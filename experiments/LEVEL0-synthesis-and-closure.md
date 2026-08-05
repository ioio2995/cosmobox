# Niveau 0 — synthèse et clôture

## 1. Objet du niveau 0

Le niveau 0 avait pour objectif de construire et caractériser un modèle quantique fini, exact et entièrement contrôlé servant de substrat minimal au programme Cosmobox.

Le périmètre retenu est un modèle de jauge compact U(1) sur graphe fini, avec fermions complexes sur les nœuds, liens quantiques de dimension finie, contrainte de Gauss imposée exactement et diagonalisation numérique du Hamiltonien dans la base physique.

Ce niveau ne cherche pas encore à démontrer l'émergence d'une métrique, d'une causalité ou d'une dynamique gravitationnelle. Il établit le socle mathématique, logiciel et spectral nécessaire pour aborder ensuite des observables relationnelles au niveau 1.

---

## 2. Conventions physiques gelées

### 2.1 Degrés de liberté

- Fermions complexes sur les nœuds.
- Deux saveurs fermioniques : `n_flavors = 2`.
- Liens de jauge U(1) tronqués à un spin fini `S`.
- Flux entiers sur chaque lien :

\[
E_e \in \{-S,\ldots,+S\}.
\]

### 2.2 Contrainte de Gauss

La base physique est constituée uniquement des états satisfaisant exactement la loi de Gauss sur chaque nœud.

La base encode simultanément :

- les occupations fermioniques de tous les modes ;
- les flux de tous les liens.

L'arbre couvrant n'est utilisé que pour la génération efficace de la base. Il ne définit pas la physique du modèle.

### 2.3 Hamiltonien

Le Hamiltonien final est :

\[
H = H_{\mathrm{dot}} + H_{\mathrm{hop}} + H_E + H_B.
\]

avec :

\[
H_E = \frac{g_E}{2}\sum_e E_e^2.
\]

Les quatre contributions sont :

- interaction locale sur les nœuds ;
- hopping fermionique couplé aux liens de jauge ;
- énergie électrique ;
- terme magnétique de plaquette.

Le modèle local à deux saveurs n'est pas un modèle SYK véritable. Il doit être décrit comme un dot local interactif fini à deux saveurs.

### 2.4 Géométries étudiées

Les géométries implémentées et testées sont :

- `triangle` ;
- `chain3` ;
- `ring4` ;
- `ring5` ;
- `ring6` ;
- `disk7`.

### 2.5 Troncature des liens

Les valeurs utilisées sont :

\[
S \in \{1,2,3\}.
\]

Le niveau 0 retient `S = 2` comme référence scientifique pour la caractérisation spectrale finale, avec `S = 3` comme contrôle lorsque le coût le permet.

Aucune interprétation physique robuste ne doit reposer sur un résultat qui varie fortement avec `S`.

---

## 3. Architecture logicielle finale

Le code du niveau 0 est organisé autour de cinq responsabilités distinctes :

1. construction des géométries ;
2. encodage et génération de la base physique ;
3. assemblage des termes du Hamiltonien ;
4. calcul spectral et production de rapports sérialisables ;
5. campagnes reproductibles, séparées du moteur.

Les principes suivants sont gelés :

- les vecteurs propres ne sont jamais sérialisés dans les rapports JSON ;
- les vecteurs propres ne sont conservés en mémoire que lorsqu'un diagnostic en a besoin ;
- les campagnes vivent sous `scripts/` et ne modifient pas le moteur ;
- les résultats sous `results/` sont des artefacts d'exécution et ne sont pas destinés à être commités ;
- les seuils numériques sont enregistrés avant exécution et ne sont pas ajustés après observation des résultats ;
- les observations, les interprétations et les conclusions autorisées doivent rester séparées.

---

## 4. Lots validés

### 4.1 Rapports et diagnostics spectraux

- Rapport de niveau 0 : `87b6611802b6b20e9df1b025fb69d6f7c20379d3`
- Runner de campagne 5A : `c4483cc834cd3619272c0a5bcdf7e2bd6f9d42ac`
- Outillage 5B : `dab062e1f518376b91e7a6a603ea3079cc44e1f1`

### 4.2 Dégénérescences spectrales

- Lot 6A initial : `f6855430fbf0f2d8928ba504e5af1f3c02340106`
- Correctif du groupement spectral par ancre : `35b2bca0cb638c1d68f3e39d209b3c58b7c0a821`

Le groupement des valeurs propres est défini par rapport à la première valeur de chaque groupe. Le groupement chaîné par valeurs adjacentes est explicitement rejeté.

### 4.3 Symétrie de saveur SU(2)

- Lot 6B.1 : `9aa5efc063472fc5013b0144f6348a759a077f18`
- Correctif de normalisation des défauts de restriction : `385263f3cf9f988eff1c074e06e2f896a98543c9`

Les opérateurs validés sont :

\[
T_x,\quad T_y,\quad T_z,
\]

et le Casimir :

\[
T^2=T_x^2+T_y^2+T_z^2.
\]

Les défauts de restriction sont relatifs :

\[
\delta_{\mathrm{res}}=
\frac{\|O\Psi-\Psi O_{\mathrm{rest}}\|_F}
{\max(1,\|O\Psi\|_F)}.
\]

### 4.4 Automorphismes géométriques

- Lot 6B.2 : `024d6f384e4e231f920f41a4952931514ee3ca74`

Les opérateurs validés sont :

- translation cyclique `T` ;
- réflexion `R`.

Les relations vérifiées exactement sont :

\[
T^N=I,
\]

\[
R^2=I,
\]

\[
RTR=T^{-1}.
\]

La permutation fermionique inclut le signe global donné par la parité du nombre d'inversions des modes occupés permutés.

L'image des flux tient compte de l'orientation des liens :

- orientation conservée : `E -> E` ;
- orientation inversée : `E -> -E`.

Aucun opérateur naïf de conjugaison globale des flux n'est défini sur la base physique.

### 4.5 Campagne de symétrie 6C

- API de rapport avec vecteurs propres en mémoire : `f1f1f01b12a70b7a668a17cd7ab118f3e8defcc7`
- Outil de campagne : `b1d66ae0352d1d83d68f8aea17a6374f8ddd03e0`
- Correctif de provenance des seuils et des versions de schéma : `ec704a6e3f662250b7a4b83f57b1154f933aed4b`

La campagne réelle a été exécutée sur ce dernier commit.

---

## 5. Campagne de référence 5B

La campagne 5B comprend 72 exécutions :

- 15 contrôles ;
- 48 variations de `J`, `t`, `g_E` et `K` ;
- 3 contrôles de troncature `S` ;
- 6 points de sensibilité à un champ uniforme `h_η`.

Toutes les exécutions ont réussi. La reprise a ensuite ignoré les 72 résultats existants.

### 5.1 Résultat principal sur la troncature

Le critère de stabilité inférieur à 5 % n'est pas satisfait sur les observables testées :

- triangle : variation d'environ 7,1 % ;
- ring4 : variation d'environ 6,8 % ;
- certaines observables de flux varient d'environ 20 à 75 %.

Conclusion :

- `S = 1` est utile pour le développement et les contrôles rapides ;
- `S = 2` est retenu comme référence scientifique du niveau 0 ;
- `S = 3` reste un contrôle de troncature ;
- aucune convergence complète en `S` n'est revendiquée.

---

## 6. Campagne de symétrie 6C

### 6.1 Grille gelée

La campagne 6C comprend huit expériences, toutes avec :

- `n_flavors = 2` ;
- `S = 2` ;
- charges externes nulles ;
- seize valeurs propres publiées.

Les expériences sont :

- triangle, ring4 et ring5 au point de référence ;
- ring5 avec `η = 0.1`, `0.25` et `0.5` ;
- triangle et ring5 avec la brisure spatiale :

\[
J_0=1.5,\qquad J_{i\neq0}=1.
\]

### 6.2 Exécution

Premier lancement :

- 8 succès ;
- 0 échec.

Second lancement :

- 8 résultats ignorés par la reprise.

La suite complète comptait alors 609 tests réussis.

Les artefacts d'exécution restent hors Git, conformément au statut des répertoires `results/`.

---

## 7. Résultats spectraux consolidés

## 7.1 Triangle

### Fondamental

Le groupe fondamental a une multiplicité 4 et vérifie :

\[
T^2=\frac34,
\qquad
T=\frac12.
\]

Les valeurs propres de translation sont :

\[
e^{\pm 2\pi i/3}.
\]

La réflexion donne deux valeurs `+1` et deux valeurs `-1`.

Le fondamental se factorise donc comme :

\[
\boxed{
T=\frac12
\otimes
\left(k=+\frac{2\pi}{3},k=-\frac{2\pi}{3}\right)
}
\]

La multiplicité 4 provient d'un doublet de saveur multiplié par une paire de moments conjugués.

### Quartet excité

Le groupe à énergie approximative `-1.612369` vérifie :

\[
T^2=\frac{15}{4},
\qquad
T=\frac32,
\qquad
k=0,
\qquad
R=-1.
\]

Ce quartet reste exactement de multiplicité 4 sous la perturbation `J_0=1.5`.

Son espérance de hopping est nulle :

\[
\langle H_{\mathrm{hop}}\rangle=0.
\]

Son énergie suit :

\[
E=-\frac14\sum_iJ_i+E_{\mathrm{flux}}.
\]

Le passage de `ΣJ_i = 3` à `ΣJ_i = 3.5` produit exactement :

\[
\Delta E=-0.125,
\]

vérifié numériquement à environ `10^-10`.

Conclusion : ce quartet `T = 3/2` est Pauli-bloqué dans le modèle fini étudié.

---

## 7.2 Ring4

Les groupes complets principaux sont :

### Fondamental

\[
T=0,
\qquad
k=\pi,
\qquad
R=-1.
\]

### Premier triplet

\[
T=1,
\qquad
k=0,
\qquad
R=-1.
\]

### Deux singulets suivants

Premier singulet :

\[
T=0,
\qquad
k=\pi,
\qquad
R=+1.
\]

Second singulet :

\[
T=0,
\qquad
k=0,
\qquad
R=+1.
\]

### Sextuplet

Le groupe de multiplicité 6 vérifie :

\[
T=1,
\qquad
k=\pm\frac{\pi}{2}.
\]

Il se factorise comme :

\[
\boxed{
3\text{ états de saveur}
\times
2\text{ moments conjugués}
}
\]

La réflexion donne trois valeurs `+1` et trois valeurs `-1`.

---

## 7.3 Ring5

### Fondamental

Le groupe fondamental a une multiplicité 4 et vérifie :

\[
T=\frac12,
\qquad
k=\pm\frac{2\pi}{5}.
\]

Il se factorise comme :

\[
\boxed{
T=\frac12
\otimes
\left(k=+\frac{2\pi}{5},k=-\frac{2\pi}{5}\right)
}
\]

### Doublet suivant

\[
T=\frac12,
\qquad
k=0,
\qquad
R=+1.
\]

### Octuplet

Le groupe de multiplicité 8 vérifie :

\[
T=\frac32,
\qquad
k=\pm\frac{4\pi}{5}.
\]

Il se factorise comme :

\[
\boxed{
4\text{ états de saveur}
\times
2\text{ moments conjugués}
}
\]

---

## 8. Réponse au champ uniforme de saveur

Pour le champ uniforme gelé dans la campagne :

\[
h_\eta=\eta\frac{\sigma_x+\sigma_z}{2},
\]

les diagnostics montrent :

\[
[T^2,H]\simeq0,
\qquad
[T,H]\simeq0,
\qquad
[R,H]\simeq0.
\]

Le champ conserve donc :

- le Casimir de saveur ;
- la translation ;
- la réflexion.

Il lève la dégénérescence interne selon la projection `m` sur l'axe sélectionné.

Pour un doublet `T = 1/2`, l'écart entre les deux branches vaut :

\[
\Delta E=\sqrt2\,\eta.
\]

Pour un multiplet `T = 3/2`, les branches successives sont également espacées de `√2 η`.

Les spectres observés sont reconstruits par :

\[
E(\eta)=E(0)+m\eta\sqrt2,
\]

à environ `10^-15` près dans la fenêtre étudiée.

Les groupes supplémentaires observés dans les fenêtres à `η != 0` sont expliqués par des descendants de groupes parents situés hors de la fenêtre de référence, y compris le descendant du groupe final tronqué.

La spectroscopie de Zeeman est donc exhaustive dans la fenêtre observée.

### Croisement exact sur ring5

La branche basse du doublet de saveur :

\[
E_d(\eta)=-4.729753-\frac{\eta\sqrt2}{2},
\]

et la branche `m = -3/2` de l'octuplet :

\[
E_o(\eta)=-4.323307-\frac{3\eta\sqrt2}{2},
\]

se croisent pour :

\[
\eta_*=
\frac{4.729753-4.323307}{\sqrt2}
\simeq0.2874.
\]

Ce croisement est encadré par les points `η = 0.25` et `η = 0.5`.

Les deux branches portant des projections `m` différentes, le croisement est protégé par la conservation de la projection sur l'axe de saveur sélectionné.

---

## 9. Brisure spatiale contrôlée

La perturbation :

\[
J_0=1.5,
\qquad
J_{i\neq0}=1,
\]

brise la translation mais préserve la réflexion fixant le nœud 0 et la symétrie globale de saveur.

Les commutateurs observés vérifient :

\[
[T,H]\neq0,
\qquad
[R,H]\simeq0,
\qquad
[T^2,H]\simeq0.
\]

### Triangle

Le quartet fondamental se sépare en deux doublets :

\[
T=\frac12,
\qquad
R=+1,
\]

et :

\[
T=\frac12,
\qquad
R=-1.
\]

### Ring5

Le fondamental `T = 1/2 \otimes (k,-k)` se sépare en deux doublets de parité `R = ±1`.

L'octuplet `T = 3/2 \otimes (k,-k)` se sépare en deux quartets de parité `R = ±1`.

Dans les deux géométries, le secteur `R = +1` descend en énergie :

- écart d'environ `0.0482` sur le triangle ;
- écart d'environ `0.0209` sur ring5.

La combinaison symétrique par rapport au site renforcé est donc favorisée dans ces deux contrôles.

---

## 10. Groupes spectraux tronqués

La fenêtre spectrale ne contient pas toujours un multiplet complet.

Le dernier groupe est alors marqué :

```text
lower_bound_only = true
```

Sur un tel groupe, la restriction d'un opérateur exact de symétrie peut présenter :

- une valeur propre de translation de module différent de 1 ;
- une valeur propre de réflexion différente de `±1` ;
- un défaut de restriction important.

Ces effets ne constituent pas une brisure de symétrie lorsque le commutateur global reste nul. Ils indiquent que le sous-espace observé n'est qu'une projection partielle d'un multiplet plus grand.

Aucune classification complète ne doit être attribuée à un groupe marqué `lower_bound_only = true`.

---

## 11. Résultat scientifique central du niveau 0

Pour les groupes spectraux complets étudiés, les multiplicités se factorisent selon :

\[
\boxed{
\text{multiplicité spectrale}
=
\text{multiplicité de saveur}
\times
\text{multiplicité spatiale}
}
\]

Cette factorisation est établie par les valeurs propres restreintes de :

- `T^2` ;
- la translation ;
- la réflexion.

Elle ne repose plus sur la seule inspection des multiplicités.

---

## 12. Conclusions autorisées

Le niveau 0 établit :

1. une base physique exacte satisfaisant la loi de Gauss ;
2. un Hamiltonien fini hermitien et contrôlé ;
3. des opérateurs exacts de saveur, translation et réflexion ;
4. une classification des multiplets spectraux complets ;
5. une réponse prédictive aux perturbations de saveur ;
6. une réponse discriminante aux brisures spatiales ;
7. un contrôle explicite des effets de troncature de la fenêtre spectrale ;
8. un contrôle partiel, mais non convergé, de la troncature des liens `S`.

---

## 13. Affirmations non démontrées

Le niveau 0 ne démontre pas :

- l'émergence d'une métrique ;
- l'émergence d'une distance physique ;
- l'émergence d'une causalité ;
- une dynamique gravitationnelle ;
- une limite continue ;
- une convergence complète lorsque `S -> infinity` ;
- l'universalité des motifs observés au-delà des géométries et paramètres étudiés.

Aucun de ces résultats ne doit être présenté comme acquis avant les niveaux suivants.

---

## 14. Questions transférées au niveau 1

Le niveau 1 devra définir avant implémentation :

1. les corrélateurs invariants de jauge à mesurer ;
2. la convention de moyenne dans un multiplet dégénéré ;
3. les normalisations nécessaires pour comparer différentes géométries ;
4. les comparaisons entre `S = 1`, `2` et `3` ;
5. la distinction entre corrélation, proximité relationnelle et distance effective ;
6. les critères minimaux permettant de parler d'une structure géométrique émergente ;
7. les observables qui doivent rester descriptives et celles qui peuvent être interprétées physiquement ;
8. les contrôles de symétrie et de troncature à conserver pour chaque nouvelle observable.

Aucune définition de distance ne devra être introduite avant la définition et la validation des corrélateurs sous-jacents.

---

## 15. Décision de clôture

Le niveau 0 est déclaré clos lorsque les conditions suivantes sont réunies :

- conventions physiques documentées et gelées ;
- base et Hamiltonien validés ;
- rapports spectraux et campagnes reproductibles ;
- symétries de saveur et géométriques validées ;
- multiplets complets classifiés ;
- groupes tronqués explicitement signalés ;
- limites scientifiques documentées ;
- questions ouvertes transférées au niveau 1.

Toutes ces conditions sont satisfaites.

\[
\boxed{\text{Niveau 0 clos}}
\]

La suite du programme peut passer à la conception du niveau 1, sans modification rétroactive des conventions du niveau 0 sauf découverte d'une erreur démontrée et documentée.
