# Modèle physique — piste A

## Degrés de liberté

Pour chaque nœud \(i\) :

- \(M\) fermions complexes \(c_{i,\alpha}\), \(\alpha=1,\ldots,M\) ;
- occupation \(n_{i,\alpha}=c^\dagger_{i,\alpha}c_{i,\alpha}\) ;
- charge locale \(Q_i=\sum_\alpha(n_{i,\alpha}-1/2)\).

Pour chaque lien orienté \(e=(i\rightarrow j)\) :

- champ électrique \(E_e=S^z_e\), valeurs \(m=-S,\ldots,+S\) ;
- opérateur de transport \(U_e=S^+_e/\sqrt{S(S+1)}\) ;
- \(U_e\) n’est pas unitaire pour une représentation finie : il s’agit d’un quantum link model, pas d’un rotateur compact exact.

## Loi de Gauss

Avec \(\epsilon_{ie}=+1\) si le lien sort de \(i\) et \(-1\) s’il entre dans \(i\) :

\[
G_i=\sum_e\epsilon_{ie}E_e-Q_i-q_i^{\mathrm{ext}}.
\]

Le sous-espace physique satisfait \(G_i=0\) pour tout \(i\).

Sans charges externes, la somme des lois de Gauss impose \(Q_{\mathrm{tot}}=0\). À \(M=2\), cela correspond au demi-remplissage global.

## Hamiltonien

\[
H=H_{\mathrm{dot}}+H_{\mathrm{hop}}+H_E+H_B.
\]

### Terme local à \(M=2\)

\[
H_{\mathrm{dot}}
=
\sum_i\left[
J_i(n_{i1}-1/2)(n_{i2}-1/2)
+
\sum_{\alpha,\beta}
h^{(i)}_{\alpha\beta}
c^\dagger_{i,\alpha}c_{i,\beta}
\right].
\]

- \(J_i\) est réel et peut être uniforme ou non uniforme ;
- le modèle général autorise un tirage gaussien pré-enregistré ;
- \(h^{(i)}\) est une matrice hermitienne \(2\times2\) ;
- terminologie : « dot fermionique interactif à deux saveurs » ;
- ne pas présenter \(M=2\) comme un régime SYK.

### Point de référence des campagnes de symétrie et du niveau 1B

Le point de référence utilise :

\[
J_i=1
\qquad\forall i.
\]

Ce choix préserve les automorphismes spatiaux exacts du Hamiltonien et permet les tests de covariance et les agrégations par orbites.

Un contrôle unique de brisure spatiale est défini par :

\[
J_0=1.5,
\qquad
J_{i\neq0}=1.
\]

Ce contrôle est nommé `j_break`. Les orbites y sont construites à partir du sous-groupe qui laisse le Hamiltonien invariant, et non à partir du groupe d’automorphismes du graphe nu.

Une campagne de désordre gaussien reste autorisée par le modèle général, mais elle est hors périmètre du niveau 1B.

### Transport matière-jauge

Pour un lien \(e=(i\rightarrow j)\) :

\[
H_{\mathrm{hop}}
=
-t\sum_{\langle ij\rangle,\alpha}
\left[
c^\dagger_{i,\alpha}U_ec_{j,\alpha}
+
c^\dagger_{j,\alpha}U_e^\dagger c_{i,\alpha}
\right].
\]

La convention est telle qu’un transport de charge de \(j\) vers \(i\) augmente \(E_e\) de \(+1\) et préserve les lois de Gauss aux deux extrémités.

### Énergie électrique

\[
H_E=\frac{g_E}{2}\sum_eE_e^2.
\]

### Terme magnétique de plaquette

\[
H_B=-K\sum_p(W_p+W_p^\dagger),
\]

avec \(W_p\) produit orienté des \(U_e\) ou \(U_e^\dagger\) autour de la plaquette \(p\).

## Paramètres du modèle

Le modèle doit accepter au minimum :

- \(M\) ;
- \(S\) ;
- \(J_i\) ;
- \(h^{(i)}\) ;
- \(t\) ;
- \(g_E\) ;
- \(K\) ;
- graine scientifique ou de désordre ;
- charges externes optionnelles.

## Interprétation limitée

Dans la piste A :

- la topologie et les voisins sont imposés ;
- la jauge et la contrainte physique sont dynamiques ;
- le niveau 1B mesure des corrélateurs relationnels invariants de jauge ;
- la distance de graphe ne sert qu’à sélectionner les chemins minimaux ;
- aucune métrique, distance effective, causalité ou gravité émergente n’est revendiquée au niveau 1B ;
- une future feature pré-enregistrée pourra étudier une distance informationnelle distincte de la distance du graphe.
