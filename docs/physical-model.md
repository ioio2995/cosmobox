# Modèle physique — piste A, niveau 0

## Degrés de liberté

Pour chaque nœud i :

- M fermions complexes c_{i,alpha}, alpha = 1…M ;
- occupation n_{i,alpha} = c†_{i,alpha} c_{i,alpha} ;
- charge locale Q_i = somme_alpha (n_{i,alpha} - 1/2).

Pour chaque lien orienté e = (i -> j) :

- champ électrique E_e = S^z_e, valeurs m = -S,…,+S ;
- opérateur de transport U_e = S^+_e / sqrt(S(S+1)) ;
- U_e n’est pas unitaire pour une représentation finie : il s’agit d’un quantum link model, pas d’un rotateur compact exact.

## Loi de Gauss

Avec epsilon_{ie} = +1 si le lien sort de i et -1 s’il entre dans i :

G_i = somme_e epsilon_{ie} E_e - Q_i - q_i^ext.

Le sous-espace physique satisfait G_i = 0 pour tout i.

Sans charges externes, la somme des lois de Gauss impose Q_tot = 0. À M = 2, cela correspond au demi-remplissage global.

## Hamiltonien

H = H_dot + H_hop + H_E + H_B.

### Terme local à M = 2

À deux saveurs, il n’existe qu’un terme quartique indépendant. Le lot 1 utilise :

H_dot = somme_i [ J_i (n_{i1}-1/2)(n_{i2}-1/2)
                  + somme_{alpha,beta} h^{(i)}_{alpha,beta} c†_{i,alpha} c_{i,beta} ].

- J_i réel, tirage gaussien ;
- h^{(i)} matrice hermitienne 2x2 ;
- terminologie : « dot fermionique interactif à deux saveurs » ;
- ne pas présenter M = 2 comme un régime SYK.

### Transport matière-jauge

Pour un lien e = (i -> j) :

H_hop = -t somme_{<ij>,alpha} [ U_e c†_{i,alpha} c_{j,alpha} + h.c. ].

La convention doit être telle qu’un transport de charge de j vers i augmente E_e de +1 et préserve G_i = G_j = 0.

### Énergie électrique

H_E = (g_E/2) somme_e E_e^2.

Le paramètre est nommé g_E dans le code pour éviter la collision entre l’énergie électrique U et l’opérateur de lien U_e.

### Terme magnétique de plaquette

H_B = -K somme_p (W_p + W_p†),

avec W_p produit orienté des U_e ou U_e† autour de la plaquette p.

## Paramètres du premier lot

Le niveau 0 doit accepter au minimum :

- M ;
- S ;
- J ;
- h ;
- t ;
- g_E ;
- K ;
- graine de désordre ;
- charges externes optionnelles.

## Interprétation limitée

Dans la piste A :

- la topologie et les voisins sont imposés ;
- la jauge et la contrainte physique sont dynamiques ;
- une future métrique informationnelle pourra différer de la distance de graphe ;
- le niveau 0 ne mesure aucune géométrie émergente.
