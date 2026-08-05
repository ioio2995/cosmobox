# Niveau 1 — Corrélateurs relationnels invariants de jauge

Statut : **spécification scientifique en cours de validation — aucune implémentation autorisée**

Branche : `research/level1-correlators`

Base : niveau 0 clos par `experiments/LEVEL0-synthesis-and-closure.md`.

---

## 1. Question scientifique

Le niveau 1 introduit les premières observables relationnelles du programme Cosmobox.

Son objectif est de mesurer des corrélations invariantes de jauge entre degrés de liberté de matière sur l’espace de Hilbert physique exact établi au niveau 0.

La question principale est :

> Les corrélations invariantes de jauge de matière et de charge présentent-elles une organisation relationnelle reproductible entre états, classes d’automorphismes du graphe et troncatures finies des liens ?

Le niveau 1 mesure une structure de corrélation conditionnée par le graphe fini fourni en entrée.

Il ne démontre pas que la géométrie du graphe émerge dynamiquement.

Le niveau 1 ne définit pas :

- de distance effective ;
- de métrique ;
- de géodésique ;
- de courbure ;
- de structure causale ;
- de dynamique gravitationnelle ;
- de limite continue ;
- de limite thermodynamique.

Toute transformation de corrélations en objet assimilable à une distance devra faire l’objet d’une feature distincte, pré-enregistrée et validée séparément.

---

## 2. Périmètre

Cette feature couvre :

1. les corrélateurs de matière à deux points habillés par une ligne de Wilson ;
2. les observables locales de densité et de charge ;
3. les corrélateurs résolus en saveur et les invariants de saveur ;
4. la sélection, l’orientation et la dépendance au chemin ;
5. les états non dégénérés et les multiplets spectraux dégénérés ;
6. les conventions de normalisation ;
7. les validations exactes de jauge, d’adjoint, d’orientation et d’automorphisme ;
8. une campagne Level 1B limitée et pré-enregistrée ;
9. la production de données brutes utilisables par une future feature de distance effective.

Cette feature ne couvre pas :

- les chemins arbitraires non minimaux ;
- l’étude systématique du secteur de jauge pur, notamment \(\langle E_e\rangle\), \(\langle E_e^2\rangle\), \(\langle W_p\rangle\) et leurs corrélations ;
- les corrélations mixtes matière–jauge ;
- la construction d’un opérateur de distance ;
- l’ajustement d’un modèle géométrique ;
- la reconstruction d’une métrique ;
- les extrapolations en taille ou en troncature ;
- les revendications de géométrie ou de gravité émergente.

Le secteur de jauge pur et les corrélations matière–jauge feront l’objet d’une feature ultérieure dédiée.

---

## 3. Conventions du niveau 0 réutilisées sans modification

Le niveau 1 réutilise :

- la base physique et son encodage ;
- la projection exacte sur la loi de Gauss ;
- les conventions d’orientation des liens ;
- l’ordre de Jordan–Wigner des modes fermioniques ;
- les signes des opérateurs de création et d’annihilation ;
- les conventions des opérateurs de lien quantique ;
- les conventions de charge externe ;
- les termes et paramètres du Hamiltonien ;
- le groupement spectral par valeur d’ancrage ;
- la distinction entre groupes complets et groupes `lower_bound_only=true` ;
- les générateurs de saveur SU(2) et le Casimir \(T^2\) ;
- les opérateurs validés de translation et de réflexion ;
- \(S=2\) comme troncature scientifique de référence ;
- \(S=3\) comme contrôle de robustesse lorsque son coût est admissible.

Aucune convention physique du niveau 0 ne peut être modifiée pour simplifier les observables du niveau 1.

L’orientation exacte du transporteur de matière doit être dérivée des conventions de Gauss du niveau 0 avant toute implémentation.

---

## 4. États et sous-espaces spectraux

### 4.1 État non dégénéré

Pour un état propre normalisé \(|\psi\rangle\) :

\[
\langle O\rangle_\psi
=
\langle\psi|O|\psi\rangle.
\]

### 4.2 Groupe spectral dégénéré complet

Pour un groupe spectral complet \(\mathcal M\) de dimension \(d\), dont les vecteurs propres orthonormés sont les colonnes de \(\Psi\), on définit :

\[
\Pi_{\mathcal M}
=
\Psi\Psi^\dagger,
\]

puis l’état mixte canonique :

\[
\rho_{\mathcal M}
=
\frac{\Pi_{\mathcal M}}{d}.
\]

L’espérance canonique d’une observable \(O\) dans ce multiplet est :

\[
\langle O\rangle_{\mathcal M}
=
\operatorname{Tr}(\rho_{\mathcal M}O)
=
\frac{1}{d}
\operatorname{Tr}
\left(
\Psi^\dagger O\Psi
\right).
\]

Cette prescription est invariante sous toute rotation unitaire des vecteurs propres à l’intérieur du sous-espace dégénéré.

### 4.3 Corrélations connectées dans un multiplet

Les corrélations connectées doivent être construites à partir du même état mixte :

\[
C_{AB}(\rho_{\mathcal M})
=
\operatorname{Tr}(\rho_{\mathcal M}AB)
-
\operatorname{Tr}(\rho_{\mathcal M}A)
\operatorname{Tr}(\rho_{\mathcal M}B).
\]

Cette quantité n’est généralement pas égale à la moyenne des corrélations connectées calculées séparément sur les vecteurs propres retournés par LAPACK.

La prescription par état mixte est la seule prescription canonique du niveau 1 pour un multiplet complet.

### 4.4 Groupes spectraux tronqués

Pour un groupe marqué `lower_bound_only=true` :

- aucune moyenne de multiplet n’est définie ;
- aucun champ `multiplet_average` ne doit être émis ;
- une compression sur la tranche observée peut être conservée à titre exploratoire ;
- cette compression doit être nommée `partial_subspace` ;
- aucune conclusion physique définitive ne peut dépendre de cette tranche.

---

## 5. Observables locales invariantes de jauge

Pour le nœud \(i\) et la saveur \(\alpha\) :

\[
n_{i\alpha}
=
c^\dagger_{i\alpha}c_{i\alpha}.
\]

Occupation totale du nœud :

\[
n_i
=
\sum_\alpha n_{i\alpha}.
\]

Avec la convention de décalage gelée au niveau 0 :

\[
Q_i=n_i-1.
\]

Pour un état pur ou mixte \(\rho\), le corrélateur connecté de charge est :

\[
C^{QQ}_{ij}(\rho)
=
\operatorname{Tr}(\rho Q_iQ_j)
-
\operatorname{Tr}(\rho Q_i)
\operatorname{Tr}(\rho Q_j).
\]

Le coefficient de corrélation de charge normalisé est :

\[
\rho^{QQ}_{ij}
=
\frac{C^{QQ}_{ij}}
{\sqrt{C^{QQ}_{ii}C^{QQ}_{jj}}}.
\]

Cette quantité n’est définie que si :

\[
C^{QQ}_{ii}C^{QQ}_{jj}
>
\epsilon_{\mathrm{norm}}^2.
\]

Dans le cas contraire, la valeur sérialisée est `null`, accompagnée d’un code de raison explicite.

### 5.1 Corrélateurs locaux de saveur

Pour chaque nœud \(i\), on définit les générateurs locaux de saveur :

\[
T_i^a
=
\frac12
\sum_{\alpha,\beta}
c^\dagger_{i\alpha}
(\sigma^a)_{\alpha\beta}
c_{i\beta},
\qquad a\in\{x,y,z\}.
\]

Ces opérateurs sont locaux et invariants de jauge.

Le corrélateur saveur–saveur scalaire brut est :

\[
C^{TT,\mathrm{raw}}_{ij}(\rho)
=
\sum_{a=x,y,z}
\operatorname{Tr}(\rho T_i^aT_j^a).
\]

Le corrélateur connecté est :

\[
C^{TT,\mathrm{conn}}_{ij}(\rho)
=
\sum_{a=x,y,z}
\left[
\operatorname{Tr}(\rho T_i^aT_j^a)
-
\operatorname{Tr}(\rho T_i^a)
\operatorname{Tr}(\rho T_j^a)
\right].
\]

Les deux versions doivent être conservées. Elles coïncident dans un état SU(2)-invariant pour lequel les espérances à un point s’annulent, mais cette annulation ne doit pas être supposée pour un état individuel ou un sous-secteur non invariant.

### 5.2 Théorème du secteur de saveur maximale à demi-remplissage

Pour \(n\) fermions et \(n_d\) sites doublement occupés, chaque double occupation forme un singulet local de saveur. Le spin total de saveur satisfait donc :

\[
T\leq\frac{n-2n_d}{2}.
\]

Par conséquent :

\[
T=\frac n2
\quad\Longrightarrow\quad
n_d=0.
\]

À demi-remplissage, \(n=N_{\mathrm{sites}}\), l’absence de double occupation implique également l’absence de site vide. Chaque site est alors exactement simplement occupé :

\[
n_i=1,
\qquad
Q_i=0.
\]

Dans tout groupe complet à demi-remplissage portant la saveur maximale \(T=n/2\), on prédit donc exactement :

\[
C^{QQ}_{ij}=0
\]

pour toutes les paires \((i,j)\), ainsi que :

\[
C^{QQ}_{ii}=0.
\]

Le coefficient \(\rho^{QQ}_{ij}\) doit alors être sérialisé comme :

```text
value = null
reason = zero_local_charge_variance
```

Cette propriété constitue un test analytique exact. Elle ne s’applique pas à un groupe de saveur non maximale.

La parité du nombre de fermions contraint également les valeurs accessibles de \(T\) : pour un nombre pair de fermions, \(T\) est entier ; pour un nombre impair, \(T\) est demi-entier.

---

## 6. Chemins orientés et transporteurs

### 6.1 Chemin orienté

Un chemin simple orienté est défini par :

\[
P=(v_0,v_1,\ldots,v_\ell),
\]

avec :

\[
v_0=i,
\qquad
v_\ell=j.
\]

Chaque paire consécutive de nœuds doit correspondre à une arête du graphe.

Dans la campagne Level 1B, un chemin simple ne peut contenir deux fois le même nœud.

### 6.2 Transporteur élémentaire dirigé

Pour une arête stockée \(e=(a,b)\), on définit :

\[
T_{a\rightarrow b}
=
\mathcal U_e,
\]

et :

\[
T_{b\rightarrow a}
=
\mathcal U_e^\dagger.
\]

La notation \(\mathcal U_e^{-1}\) est interdite.

Dans une représentation de lien quantique de spin fini, \(\mathcal U_e\) n’est pas supposé unitaire et :

\[
\mathcal U_e^\dagger
\neq
\mathcal U_e^{-1}.
\]

### 6.3 Transporteur associé à un chemin

Pour :

\[
P=(v_0,v_1,\ldots,v_\ell),
\]

le transporteur est :

\[
W_P
=
T_{v_{\ell-1}\rightarrow v_\ell}
\cdots
T_{v_1\rightarrow v_2}
T_{v_0\rightarrow v_1}.
\]

Le transporteur situé le plus à droite agit en premier sur un ket.

Pour le chemin inversé :

\[
P^{-1}
=
(v_\ell,\ldots,v_1,v_0),
\]

on doit avoir exactement :

\[
W_{P^{-1}}
=
W_P^\dagger.
\]

### 6.4 Normalisation du transporteur en fonction de \(S\)

Le niveau 0 définit déjà le transporteur par :

\[
U_e^{\mathrm H}
=
\frac{S_e^+}{\sqrt{S(S+1)}},
\]

et son adjoint par :

\[
\left(U_e^{\mathrm H}\right)^\dagger
=
\frac{S_e^-}{\sqrt{S(S+1)}}.
\]

La convention du niveau 1 est donc gelée à :

\[
\mathcal U_e=U_e^{\mathrm H},
\qquad
\nu_S=1.
\]

Aucune normalisation supplémentaire ne doit être appliquée.

Les amplitudes non nulles de \(\mathcal U_e\) sont :

```text
S = 1 : {1, 1}
S = 2 : {2/sqrt(6), 1, 1, 2/sqrt(6)}
S = 3 : {sqrt(6)/sqrt(12), sqrt(10)/sqrt(12), 1, 1,
         sqrt(10)/sqrt(12), sqrt(6)/sqrt(12)}
```

L’amplitude maximale vaut exactement 1 pour \(S=1,2,3\).

Le manifeste doit enregistrer :

- la définition \(U_e^{\mathrm H}=S_e^+/\sqrt{S(S+1)}\) ;
- \(\nu_S=1\) ;
- la table des amplitudes pour chaque valeur de \(S\) utilisée ;
- la convention employée pour chaque observable sérialisée.

Les variations résiduelles entre valeurs de \(S\) peuvent provenir de la distribution des flux, de la saturation aux bornes \(m=\pm S\) et de la modification des états propres. Elles ne doivent pas être interprétées comme une simple renormalisation globale du transporteur.

---

## 7. Opérateur de matière habillé

Pour une source \(j\), une cible \(i\), une saveur source \(\beta\), une saveur cible \(\alpha\), et un chemin \(P:i\rightarrow j\), on définit :

\[
O^{\alpha\beta}_{ij}[P]
=
c^\dagger_{i\alpha}
W_P
c_{j\beta}.
\]

### 7.1 Dérivation de l’invariance de jauge

Pour une arête stockée \(e=(a\rightarrow b)\), le transporteur \(U_e\) augmente la divergence du champ électrique de \(+1\) en \(a\) et de \(-1\) en \(b\).

Le produit ordonné le long du chemin :

\[
P:i=v_0\rightarrow v_1\rightarrow\cdots\rightarrow v_\ell=j
\]

produit, par télescopage, une variation totale de divergence :

\[
+1\text{ en }i,
\qquad
-1\text{ en }j,
\qquad
0\text{ sur les nœuds intermédiaires}.
\]

Avec les conventions de charge du niveau 0, \(c^\dagger_{i\alpha}\) augmente la charge de matière en \(i\), tandis que \(c_{j\beta}\) la diminue en \(j\). Les variations de matière et de flux se compensent donc exactement dans chaque générateur de Gauss :

\[
[G_k,O^{\alpha\beta}_{ij}[P]]=0
\]

pour tout nœud \(k\).

Cette démonstration est indépendante des saveurs \(\alpha\) et \(\beta\), car la jauge U(1) est aveugle à la saveur. Elle couvre donc également les composantes hors diagonale \(\alpha\neq\beta\).

Le test numérique de commutation sur l’espace non projeté doit confirmer cette identité exacte.

### 7.2 Corrélateur habillé

Pour un état \(\rho\), le corrélateur habillé est :

\[
G^{\alpha\beta}_{ij}[P;\rho]
=
\operatorname{Tr}
\left(
\rho
O^{\alpha\beta}_{ij}[P]
\right).
\]

La relation d’adjoint exacte est :

\[
\left(
O^{\alpha\beta}_{ij}[P]
\right)^\dagger
=
O^{\beta\alpha}_{ji}[P^{-1}].
\]

Pour un état hermitien \(\rho\) :

\[
G^{\alpha\beta}_{ij}[P;\rho]
=
\left(
G^{\beta\alpha}_{ji}[P^{-1};\rho]
\right)^*.
\]

---

## 8. Décomposition en saveur

La matrice complète de saveur est :

\[
\mathbf G_{ij}[P]
=
\left(
G^{\alpha\beta}_{ij}[P]
\right)_{\alpha,\beta}.
\]

### 8.1 Singlet de saveur

L’observable scalaire primaire est :

\[
G^{(0)}_{ij}[P]
=
\operatorname{Tr}_{f}
\mathbf G_{ij}[P].
\]

### 8.2 Composantes vectorielles de saveur

Les composantes de type triplet sont :

\[
G^{(a)}_{ij}[P]
=
\operatorname{Tr}_{f}
\left(
\sigma_a
\mathbf G_{ij}[P]
\right).
\]

Ces composantes sont covariantes sous SU(2), mais ne sont pas des scalaires invariants de saveur.

### 8.3 Invariants de matrice

Les comparaisons indépendantes du repère de saveur peuvent utiliser :

\[
\operatorname{Tr}
\left(
\mathbf G^\dagger\mathbf G
\right),
\]

les valeurs singulières de \(\mathbf G\), ou toute autre quantité explicitement validée comme invariant de saveur.

La matrice complète peut être sérialisée pour auditabilité.

Toute interprétation physique indépendante de la base de saveur doit reposer sur le singlet ou sur des invariants de matrice.

---

## 9. Chemin de longueur nulle

Pour \(i=j\), le chemin est :

\[
P=(i),
\]

et :

\[
W_P=I.
\]

Alors :

\[
O^{\alpha\beta}_{ii}[P]
=
c^\dagger_{i\alpha}c_{i\beta}.
\]

Pour \(\alpha=\beta\) :

\[
G^{\alpha\alpha}_{ii}[P]
=
\langle n_{i\alpha}\rangle.
\]

Un chemin vide ou de longueur nulle avec des extrémités distinctes est invalide.

---

## 10. Famille canonique de chemins

Pour chaque paire ordonnée \((i,j)\), la campagne Level 1B énumère tous les chemins simples de longueur minimale dans le graphe non orienté sous-jacent.

La longueur utilisée est le nombre non pondéré d’arêtes.

Cette convention dépend de la géométrie combinatoire fournie en entrée.

Elle ne constitue pas une distance émergente.

L’énumération doit être déterministe et indépendante de l’ordre d’itération des dictionnaires ou ensembles.

Après validation, les chemins sont ordonnés lexicographiquement selon leur tuple de nœuds.

Pour chaque chemin, les données suivantes doivent être enregistrées :

- la suite ordonnée des nœuds ;
- la suite des arêtes dirigées ;
- la longueur combinatoire ;
- le sens du transporteur sur chaque arête ;
- les corrélateurs complexes individuels.

Les chemins non minimaux sont exclus de la campagne Level 1B.

---

## 11. Traitement des chemins minimaux multiples

Pour :

\[
SP(i,j)
=
\{P_1,\ldots,P_N\},
\]

chaque résultat individuel doit être conservé.

La moyenne complexe est :

\[
\overline G_{ij}
=
\frac{1}{N}
\sum_{P\in SP(i,j)}
G_{ij}[P].
\]

La moyenne des modules est :

\[
\overline{|G|}_{ij}
=
\frac{1}{N}
\sum_{P\in SP(i,j)}
|G_{ij}[P]|.
\]

La valeur quadratique moyenne est :

\[
G^{\mathrm{rms}}_{ij}
=
\sqrt{
\frac{1}{N}
\sum_{P\in SP(i,j)}
|G_{ij}[P]|^2
}.
\]

La dispersion maximale entre chemins est :

\[
\Delta^{\mathrm{path}}_{ij}
=
\max_{P,Q\in SP(i,j)}
|G_{ij}[P]-G_{ij}[Q]|.
\]

Lorsque :

\[
\sum_P|G_{ij}[P]|
>
\epsilon_{\mathrm{norm}},
\]

on définit l’indicateur de cohérence de phase :

\[
\chi^{\mathrm{path}}_{ij}
=
\frac{
\left|
\sum_PG_{ij}[P]
\right|
}{
\sum_P|G_{ij}[P]|
}.
\]

Sinon, cet indicateur vaut `null`.

La moyenne complexe ne peut jamais être utilisée seule pour conclure à une corrélation faible, car des contributions de grande amplitude peuvent s’annuler par leur phase.

Dans la campagne de référence, une multiplicité non triviale de chemins minimaux n’existe que pour les paires antipodales de `ring4`, qui possèdent deux arcs minimaux de longueur 2. `triangle` et `ring5` ne fournissent qu’un chemin minimal par paire distincte. La dépendance aux chemins multiples n’a donc qu’un banc d’essai scientifique limité dans la campagne principale.

`disk7` peut être ajouté comme extension conditionnelle uniquement après un comptage préalable de la base physique et une estimation pré-enregistrée du coût mémoire et du temps de calcul.

---

## 12. Normalisations des corrélateurs

### 12.1 Corrélateur brut

La valeur complexe brute doit toujours être conservée.

### 12.2 Normalisation par les occupations aux extrémités

On définit :

\[
G^{\mathrm{occ}}_{ij}[P]
=
\frac{
G^{(0)}_{ij}[P]
}{
\sqrt{
\langle n_i\rangle
\langle n_j\rangle
}
}.
\]

Cette quantité n’est définie que si le dénominateur est supérieur au seuil gelé.

Elle est sans dimension, mais elle n’est pas supposée être bornée par 1.

Elle doit être décrite comme un corrélateur normalisé par les occupations aux extrémités, et non comme un coefficient de cohérence universel.

### 12.3 Cohérence normalisée par l’opérateur

Pour un opérateur \(O\) et un état \(\rho\), on peut définir :

\[
\gamma_O(\rho)
=
\frac{
\operatorname{Tr}(\rho O)
}{
\sqrt{
\operatorname{Tr}(\rho OO^\dagger)
\operatorname{Tr}(\rho O^\dagger O)
}
}.
\]

Cette quantité n’est définie que lorsque les deux facteurs du dénominateur dépassent le seuil gelé.

La normalisation par les occupations et la normalisation par l’opérateur répondent à deux questions différentes et doivent être sérialisées séparément.

Pour les comparaisons entre troncatures, \(\gamma_O\) est l’observable sans dimension primaire du verdict de robustesse. \(G^{\mathrm{occ}}\) est un diagnostic secondaire, tandis que le corrélateur brut reste toujours conservé sans recevoir de verdict binaire automatique.

La normalisation \(\gamma_O\) élimine une renormalisation multiplicative globale de l’opérateur. Elle n’élimine pas nécessairement les effets de saturation aux bornes \(m=\pm S\), ni les variations dépendant de l’état de flux traversé.

### 12.4 Transformations interdites au niveau 1

Les expressions suivantes sont exclues :

\[
-\log|G|,
\]

\[
-\log|G^{\mathrm{occ}}|,
\]

ainsi que toute autre transformation en distance ou pseudo-distance.

Leur domaine, leur régularisation, leur comportement sous changement de chemin et leur compatibilité éventuelle avec une inégalité triangulaire devront être étudiés dans une feature ultérieure.

---

## 13. Compression dans un sous-espace dégénéré

Pour un groupe spectral complet :

\[
O_{\mathrm{rest}}
=
\Psi^\dagger O\Psi.
\]

Il s’agit d’une compression de l’opérateur dans le sous-espace.

Cette opération ne suppose pas que le sous-espace propre de \(H\) soit invariant sous \(O\).

Il n’est donc pas exigé que :

\[
O\Psi
\simeq
\Psi O_{\mathrm{rest}}.
\]

Un tel défaut de restriction n’est pertinent que pour un opérateur supposé préserver le sous-espace, notamment un opérateur de symétrie commutant avec \(H\).

Il ne doit pas être utilisé comme critère général pour les corrélateurs de matière ou de charge.

Pour un opérateur hermitien comprimé, on rapporte :

- la trace normalisée ;
- les valeurs propres ;
- le minimum ;
- le maximum ;
- l’étendue spectrale.

Pour un opérateur non hermitien comprimé, on rapporte :

- la trace normalisée ;
- les valeurs singulières ;
- la norme de Frobenius.

Ces quantités doivent être invariantes sous :

\[
\Psi
\longmapsto
\Psi V,
\]

pour toute matrice unitaire \(V\) agissant à l’intérieur du sous-espace dégénéré.

Les rotations unitaires aléatoires sont des tests de validation et non des observables scientifiques.

---

## 14. Covariance sous automorphismes

Pour un automorphisme validé \(A\) du graphe :

\[
U_A
O_{ij}[P]
U_A^\dagger
=
O_{A(i)A(j)}[A(P)].
\]

Il s’agit d’une covariance de la famille d’opérateurs.

Un opérateur associé à une paire fixe \((i,j)\) n’a pas à commuter individuellement avec l’automorphisme.

Les résultats doivent être produits à deux niveaux :

1. paire ordonnée et chemin individuel ;
2. orbite de paires ordonnées sous le groupe d’automorphismes validé.

Les comparaisons entre géométries ne peuvent porter que sur des classes partageant des descripteurs explicitement déclarés :

- longueur combinatoire minimale ;
- nombre de chemins minimaux ;
- type d’orbite de la paire ordonnée ;
- règle de sélection de l’état ;
- définition de l’observable ;
- convention de normalisation du transporteur.

Les numéros de nœuds ne doivent jamais servir d’identifiants physiques entre géométries différentes.

---

## 15. Appariement des états entre valeurs de \(S\)

Les états calculés pour différentes valeurs de \(S\) ne doivent pas être appariés uniquement selon leur rang énergétique.

Un groupe candidat doit être comparé selon les étiquettes disponibles et validées :

- géométrie ;
- paramètres du Hamiltonien ;
- statut de groupe complet ;
- valeur de \(T\) ;
- secteur de translation ;
- information de réflexion lorsqu’elle est simultanément définie ;
- multiplicité.

L’ordre énergétique ne peut être utilisé qu’après accord de ces étiquettes.

Le statut d’appariement est :

```text
exact_label_match
partial_label_match
ambiguous
unavailable
```

Seuls les groupes `exact_label_match` peuvent soutenir une conclusion définitive de robustesse état par état entre troncatures.

Le groupe fondamental complet peut être comparé séparément lorsqu’il est identifié sans ambiguïté pour toutes les valeurs de \(S\).

---

## 16. Robustesse sous troncature

Le verdict automatique de robustesse porte en priorité sur \(\gamma_O\). Le corrélateur \(G^{\mathrm{occ}}\) reçoit un verdict secondaire. Les quantités brutes dépendant de l’amplitude et de la structure détaillée du transporteur ne reçoivent pas de verdict binaire automatique.

Pour une observable sans dimension approuvée \(x\), on compare les deux valeurs de \(S\) les plus élevées disponibles :

\[
D_S(x)
=
|x_{S_{\mathrm{haut}}}-x_{S_{\mathrm{bas}}}|.
\]

L’observable est classée stable si :

\[
D_S(x)
\le
\max
\left[
\tau_{\mathrm{abs}},
\tau_{\mathrm{rel}}
\max
\left(
|x_{S_{\mathrm{haut}}}|,
|x_{S_{\mathrm{bas}}}|
\right)
\right].
\]

Seuils initiaux proposés :

```text
truncation_absolute_tolerance = 0.05
truncation_relative_tolerance = 0.15
```

Ces valeurs doivent être validées avant exécution de la campagne.

La différence réelle doit toujours être enregistrée, indépendamment de sa classification.

Aucune conclusion du niveau 1 ne peut dépendre d’une observable classée :

- instable ;
- ambiguë ;
- indisponible ;
- ou non comparable.

---

## 17. Diagnostics numériques et seuils

Les seuils initiaux proposés sont :

```text
operator_identity_tolerance             = 1e-10
gauss_commutator_tolerance              = 1e-10
adjoint_reversal_tolerance              = 1e-10
zero_path_tolerance                     = 1e-10
automorphism_covariance_tolerance       = 1e-10
multiplet_orthonormality_tolerance      = 1e-8
multiplet_basis_invariance_tolerance    = 1e-8
normalization_floor                     = 1e-12
truncation_absolute_tolerance           = 0.05
truncation_relative_tolerance           = 0.15
```

Ces seuils doivent être enregistrés dans le manifeste avant toute exécution scientifique.

Ils ne peuvent pas être modifiés après observation des résultats.

Chaque observable construite doit vérifier ou rapporter :

- la dimension de la matrice ;
- la finitude des coefficients ;
- la fermeture exacte dans la base physique ;
- le défaut de commutation avec les générateurs de Gauss ;
- le défaut de la relation d’adjoint ;
- le défaut de réduction du chemin nul ;
- le défaut de covariance sous automorphisme ;
- l’orthonormalité du sous-espace spectral ;
- l’invariance de base des diagnostics de multiplet ;
- la validité des dénominateurs de normalisation ;
- le statut complet ou tronqué du groupe spectral.

---

## 18. Validations scientifiques obligatoires

Avant toute campagne réelle, il faut :

1. dériver analytiquement la transformation de jauge de l’opérateur habillé ;
2. vérifier sa commutation avec tous les générateurs de Gauss dans un espace non projeté tractable ;
3. vérifier la convention de normalisation des liens pour chaque valeur de \(S\) ;
4. vérifier l’identité exacte entre chemin inversé et adjoint ;
5. vérifier la réduction au chemin de longueur nulle ;
6. vérifier l’énumération déterministe des chemins minimaux ;
7. vérifier la fermeture dans la base physique sans suppression silencieuse de transitions ;
8. vérifier la covariance de la famille d’opérateurs sous translation et réflexion ;
9. vérifier l’invariance des diagnostics dans les sous-espaces dégénérés complets ;
10. vérifier que les corrélations connectées de multiplet utilisent bien l’état mixte \(\Pi/d\) ;
11. vérifier l’invariance du singlet de saveur et la covariance des composantes de triplet ;
12. vérifier au moins un élément de matrice calculé à la main, incluant le signe fermionique et l’amplitude du transporteur ;
13. vérifier la sérialisation `null` sous les seuils de normalisation ;
14. vérifier qu’un groupe tronqué ne peut jamais être émis comme multiplet complet ;
15. vérifier la déterminisme du manifeste, des empreintes, de la reprise et des écritures atomiques.

---

## 19. API publique proposée

Les noms exacts restent soumis à revue d’implémentation.

```python
@dataclass(frozen=True, slots=True)
class OrientedPath:
    nodes: tuple[int, ...]


def enumerate_shortest_paths(
    lattice: Lattice,
    source: int,
    target: int,
) -> tuple[OrientedPath, ...]:
    ...


def build_dressed_matter_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    source: int,
    target: int,
    source_flavor: int,
    target_flavor: int,
    path: OrientedPath,
) -> sp.csr_matrix:
    ...


def build_charge_operator(
    ...,
    node: int,
) -> sp.csr_matrix:
    ...


def build_local_flavor_operator(
    ...,
    node: int,
    component: Literal["x", "y", "z"],
) -> sp.csr_matrix:
    ...


def analyze_observable_in_subspaces(
    operator: sp.csr_matrix,
    operator_name: str,
    operator_kind: OperatorKind,
    eigenvectors: np.ndarray,
    degeneracy: DegeneracyReport,
) -> tuple[ObservableSectorDiagnostic, ...]:
    ...
```

L’API ne doit pas exposer une notion de distance au niveau 1.

---

## 20. Campagne de référence Level 1B

### 20.1 Paramètres de référence

```text
n_flavors = 2
external_charges = 0
S = 2
J_i = 1
t = 1
g_E = 1
K = 1
h = 0
```

Géométries :

- `triangle` ;
- `ring4` ;
- `ring5`.

### 20.2 Contrôles de robustesse

Les fenêtres spectrales sont gelées par géométrie :

```text
triangle = 16
ring4    = 20
ring5    = 24
```

Ces fenêtres sont utilisées pour toutes les valeurs de \(S\) de la géométrie concernée. Elles ne peuvent pas être augmentées après inspection des corrélateurs.

Sous réserve du coût mesuré et des garde-fous de dimension :

- `triangle` pour \(S=1,2,3\) ;
- `ring4` pour \(S=1,2,3\) ;
- `ring5` pour \(S=1,2\) ;
- `ring5` pour \(S=3\) uniquement si ce point est accepté avant l’exécution ;
- `disk7` uniquement comme extension conditionnelle après comptage de base et estimation de coût pré-enregistrés.

### 20.3 Sélection des groupes spectraux

Les analyses principales portent sur :

1. le groupe fondamental complet ;
2. le plus bas groupe excité complet disposant d’un `exact_label_match` entre valeurs de \(S\) ;
3. le plus bas groupe complet de saveur maximale \(T=n/2\), lorsqu’il est présent dans la fenêtre gelée ;
4. pour les géométries impaires, le plus bas groupe complet \(T=3/2\) disposant d’un `exact_label_match`, lorsqu’il est distinct du groupe de saveur maximale ;
5. aucun groupe tronqué ou apparié de manière ambiguë.

Application à la campagne :

```text
triangle : T_max = 3/2 ; la cible T=3/2 est aussi la cible maximale
ring4    : T_max = 2   ; T=3/2 est interdit par la parité
ring5    : T_max = 5/2 ; T=3/2 est une cible supplémentaire possible
```

Si un groupe ciblé n’est pas complet dans la fenêtre gelée, il est déclaré `unavailable` ou `lower_bound_only` selon le cas.

Il est interdit d’augmenter la fenêtre après inspection des corrélateurs afin de récupérer un groupe ou un résultat souhaité.

---

## 21. Sorties requises

Chaque résultat doit enregistrer :

- le commit du dépôt ;
- la version du schéma ;
- l’empreinte du manifeste ;
- la géométrie ;
- les paramètres du Hamiltonien ;
- la valeur de \(S\) ;
- la convention du transporteur ;
- le facteur de normalisation du transporteur ;
- l’identité du groupe spectral ;
- le statut complet ou tronqué ;
- le statut d’appariement entre valeurs de \(S\) ;
- la prescription d’état pur ou mixte ;
- la paire ordonnée de nœuds ;
- l’identifiant de l’orbite d’automorphisme ;
- tous les chemins minimaux ;
- la matrice brute complète de saveur ;
- le singlet de saveur ;
- les invariants de saveur approuvés ;
- la normalisation par les occupations ;
- la cohérence normalisée par l’opérateur ;
- le corrélateur connecté de charge ;
- le coefficient de charge normalisé ;
- les corrélateurs de saveur `C_TT_raw` et `C_TT_connected` ;
- la moyenne complexe sur les chemins ;
- la moyenne des modules ;
- la valeur RMS ;
- la dispersion maximale entre chemins ;
- l’indicateur de cohérence de phase ;
- tous les défauts numériques applicables ;
- les raisons explicites des valeurs `null` ou exclues.

---

## 22. Tests minimums

### T1 — validation des chemins

Rejeter :

- un chemin nul entre extrémités distinctes ;
- un chemin simple contenant un nœud répété ;
- une étape ne correspondant pas à une arête ;
- des extrémités incohérentes ;
- un nœud hors plage.

### T2 — chemins minimaux déterministes

Vérifier l’ordre exact des chemins sur :

- `triangle` ;
- `ring4` ;
- `ring5`.

### T3 — fermeture de la base physique

Toute transition non nulle doit aboutir dans la base physique.

Une transition non nulle absente de la base physique doit provoquer une erreur explicite.

### T4 — commutation avec la loi de Gauss

Vérifier la commutation exacte dans un espace complet tractable.

Le test doit couvrir :

- un chemin suivant les orientations stockées ;
- un chemin contenant au moins une arête parcourue en sens inverse ;
- un chemin de longueur nulle ;
- une composante hors diagonale en saveur.

### T5 — inversion du chemin

Vérifier :

\[
O_{ij}[P]^\dagger
=
O_{ji}[P^{-1}].
\]

### T6 — réduction au chemin nul

Vérifier l’égalité avec les opérateurs locaux à un corps.

### T7 — covariance sous automorphismes

Vérifier :

\[
U_AO_{ij}[P]U_A^\dagger
=
O_{A(i)A(j)}[A(P)].
\]

### T8 — invariance de base des multiplets

Appliquer des rotations unitaires aléatoires dans un sous-espace dégénéré synthétique.

Vérifier l’invariance :

- de la trace normalisée ;
- des valeurs propres pour un opérateur hermitien ;
- des valeurs singulières ;
- de la norme de Frobenius.

### T9 — état mixte du multiplet

Vérifier que le corrélateur connecté est calculé à partir de \(\rho_{\mathcal M}=\Pi_{\mathcal M}/d\), et non comme moyenne des corrélateurs connectés des vecteurs LAPACK.

### T10 — groupes tronqués

Vérifier qu’aucun groupe `lower_bound_only=true` ne peut être sérialisé comme multiplet complet.

### T11 — seuils de normalisation

Vérifier la valeur `null` et le code de raison sous le seuil gelé.

### T12 — cas analytique minimal

Valider au moins un cas calculé à la main :

- signe fermionique ;
- orientation ;
- amplitude du lien ;
- conjugaison complexe.

### T13 — convention du transporteur en \(S\)

Vérifier explicitement que le transporteur du niveau 0 est déjà :

\[
U_e=S_e^+/\sqrt{S(S+1)}
\]

et reproduire la table gelée des amplitudes pour \(S=1,2,3\), sans normalisation supplémentaire.

### T14 — secteur de saveur maximale

À demi-remplissage, pour tout groupe complet portant \(T=n/2\), vérifier :

\[
\max_{i,j}|C^{QQ}_{ij}|
<
\texttt{operator\_identity\_tolerance}.
\]

Vérifier également que \(\rho^{QQ}_{ij}\) vaut `null` avec la raison `zero_local_charge_variance`.

### T15 — corrélateurs locaux de saveur

Vérifier la construction de \(C^{TT,\mathrm{raw}}\) et \(C^{TT,\mathrm{conn}}\), ainsi que leur invariance de jauge et leur covariance SU(2).

### T16 — déterminisme et reprise

Vérifier :

- les empreintes ;
- les sorties atomiques ;
- le manifeste pré-enregistré ;
- la reprise complète ;
- l’absence de dépendance à l’ordre d’itération.

---

## 23. Lots d’implémentation

### Lot 1A — modèle de chemin et transporteur

- validation de `OrientedPath` ;
- énumération déterministe des chemins minimaux ;
- transporteur orienté exact ;
- normalisation explicite en \(S\) ;
- tests T1, T2, T5 et T13.

### Lot 1B — opérateurs de matière, de charge et de saveur

- construction exacte des opérateurs creux ;
- opérateurs locaux de charge ;
- générateurs locaux de saveur ;
- corrélateurs \(C^{TT,\mathrm{raw}}\) et \(C^{TT,\mathrm{conn}}\) ;
- fermeture dans la base physique ;
- validation de jauge ;
- tests T3, T4, T6, T12, T14 et T15.

### Lot 1C — diagnostics spectraux

- état mixte canonique des multiplets complets ;
- compression des observables ;
- diagnostics hermitiens et non hermitiens ;
- contrat des groupes tronqués ;
- tests T8, T9, T10 et T11.

### Lot 1D — saveur et automorphismes

- singlet et composantes covariantes de saveur ;
- invariants de matrice ;
- covariance sous translation et réflexion ;
- agrégation par orbite ;
- test T7.

### Lot 1E — outillage de campagne

- grille Level 1B gelée ;
- schéma JSON versionné ;
- manifeste et seuils ;
- sorties JSON et CSV ;
- reprise et écritures atomiques ;
- test T16 ;
- aucune exécution scientifique réelle.

### Lot 1F — campagne scientifique

- exécution de la grille pré-enregistrée ;
- conservation des artefacts hors Git ;
- rapport des observations brutes ;
- classification des structures robustes ou non robustes ;
- absence de toute construction de distance.

Chaque lot doit faire l’objet d’une revue indépendante avant le début du suivant.

---

## 24. Critères d’acceptation

Le niveau 1B est considéré comme terminé lorsque :

1. la définition de l’opérateur habillé est dérivée analytiquement ;
2. son invariance de jauge est vérifiée avec les conventions exactes du niveau 0 ;
3. les conventions d’orientation et d’adjoint sont validées ;
4. la normalisation du transporteur entre valeurs de \(S\) est gelée et testée ;
5. les moyennes de multiplet sont invariantes sous changement de base ;
6. les corrélations connectées utilisent l’état mixte canonique ;
7. les groupes tronqués ne sont jamais interprétés comme multiplets complets ;
8. les corrélateurs bruts et normalisés sont disponibles pour chaque chemin minimal ;
9. la dépendance au chemin est quantifiée sans masquer les annulations de phase ;
10. la covariance sous automorphismes est vérifiée ;
11. les comparaisons entre géométries utilisent des classes d’orbites et non les numéros de nœuds ;
12. l’appariement entre valeurs de \(S\) est explicite et non fondé uniquement sur le rang énergétique ;
13. les corrélateurs locaux de saveur brut et connecté sont disponibles ;
14. les zéros structurels du secteur de saveur maximale sont vérifiés ;
15. la robustesse sous troncature est évaluée selon les seuils pré-enregistrés ;
16. aucune définition ou seuil n’est modifié après observation des résultats ;
17. les conclusions restent limitées à la structure relationnelle des corrélations.

---

## 25. Conclusions autorisées

Si les critères d’acceptation sont satisfaits, le niveau 1B peut établir :

- que les opérateurs de matière habillés sont bien définis et invariants de jauge dans le modèle fini exact ;
- que leurs corrélateurs sont reproductibles dans les multiplets dégénérés complets ;
- que les familles de corrélateurs sont covariantes sous les automorphismes validés ;
- que des paires appartenant à une même orbite présentent ou non des résultats équivalents ;
- que les chemins minimaux multiples produisent des résultats identiques, faiblement différents ou fortement différents ;
- que certaines observables sans dimension sont ou non robustes sous les troncatures testées ;
- que les données justifient ou non l’ouverture d’une future feature consacrée à une distance effective.

Le niveau 1B ne peut pas établir :

- que la distance combinatoire du graphe a émergé ;
- que l’indépendance au chemin est générale au-delà de la famille testée ;
- qu’une métrique effective existe ;
- qu’une inégalité triangulaire est satisfaite ;
- qu’une courbure a émergé ;
- qu’une structure causale a émergé ;
- qu’une dynamique gravitationnelle a émergé.

---

## 26. Décisions restant à valider avant implémentation

Les décisions suivantes sont gelées par la présente spécification :

- le transporteur du niveau 0 est déjà normalisé par \(\sqrt{S(S+1)}\) ;
- \(\nu_S=1\) ;
- l’opérateur habillé est \(c_i^\dagger W_Pc_j\) avec la convention d’orientation du §7 ;
- \(\gamma_O\) est l’observable primaire du verdict de robustesse ;
- \(G^{\mathrm{occ}}\) est secondaire ;
- le corrélateur brut est conservé sans verdict automatique ;
- les fenêtres spectrales sont `triangle=16`, `ring4=20`, `ring5=24` ;
- les corrélateurs \(C^{TT,\mathrm{raw}}\) et \(C^{TT,\mathrm{conn}}\) appartiennent au périmètre ;
- le secteur de jauge pur est reporté à une feature ultérieure ;
- `disk7` est une extension conditionnelle soumise à un comptage préalable.

Restent à valider avant le lot 1A :

1. les valeurs définitives de `truncation_absolute_tolerance` et `truncation_relative_tolerance` ;
2. l’admissibilité de `ring5` à \(S=3\) selon les garde-fous de ressources ;
3. le schéma JSON final et sa version ;
4. la liste exacte des invariants de saveur sérialisés ;
5. la liste des diagnostics non hermitiens conservés ;
6. les règles d’agrégation par orbite d’automorphisme ;
7. les utilitaires de campagne mutualisés ou locaux.

Aucun code scientifique du niveau 1 ne doit être écrit avant validation de ces décisions restantes et inscription de leurs valeurs dans le manifeste pré-enregistré.
