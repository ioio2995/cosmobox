# Conventions gelées — niveau 0

## Indexation

- nœuds indexés de 0 à N-1 ;
- saveurs indexées de 0 à M-1 ;
- liens indexés dans un ordre déterministe propre à chaque géométrie ;
- plaquettes indexées dans un ordre déterministe.

## Orientation des liens

Chaque lien est stocké une seule fois comme (source, destination). Cette orientation fixe le signe de E_e dans la divergence discrète.

Pour un nœud i :

- +E_e si e sort de i ;
- -E_e si e entre dans i.

## Charge

Q_i = somme_alpha (n_{i,alpha} - 1/2).

La loi de Gauss est :

G_i = somme_e epsilon_{ie} E_e - Q_i - q_i^ext.

Un état physique satisfait G_i = 0 pour tout i.

## Convention transport

Pour e = (i -> j), le terme U_e c†_i c_j transporte une charge de j vers i et augmente E_e de +1.

Cette convention doit être vérifiée par [H_hop, G_i] = 0 dans le petit espace complet.

## Jordan–Wigner

Ordre global des modes :

b = i*M + alpha.

Pour c†_a c_b, le signe est calculé à partir du nombre de modes occupés strictement entre a et b. Aucun ordre alternatif n’est permis dans le niveau 0.

## Plaquettes

Une plaquette est une liste ordonnée de couples :

(edge_index, sens),

avec sens = +1 si le parcours suit l’orientation du lien et -1 sinon.

Le produit W_p utilise U_e pour sens +1 et U_e† pour sens -1.

## Arbre couvrant

- choix déterministe par parcours BFS depuis une racine fixée ;
- les liens de l’arbre sont ordonnés selon l’ordre des liens du graphe ;
- les cordes sont les liens hors arbre dans le même ordre global ;
- la résolution des flux traite les nœuds par profondeur décroissante ;
- la racine est vérifiée en dernier.

## Encodage

- occupations dans les N*M bits de poids faible ;
- puis trois bits par lien ;
- v_e = E_e + S ;
- aucune valeur non canonique dans les bits inutilisés ;
- encode(decode(key)) doit rendre exactement key.

## Reproductibilité

- toutes les graines de désordre sont explicites ;
- aucun ordre dérivé d’un set ou d’un dict non trié ;
- les rapports et matrices doivent être reproductibles bit à bit lorsque les bibliothèques le permettent.

## Terminologie

Au niveau 0, employer :

- « site » ou « dot fermionique interactif » ;
- « quantum link U(1) » ;
- « sous-espace physique » ;
- « topologie imposée ».

Ne pas employer comme résultat acquis :

- gravité émergente ;
- espace-temps émergent ;
- graviton ;
- invariance de Lorentz émergente ;
- régime SYK pour M = 2.
