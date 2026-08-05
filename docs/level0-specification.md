# Spécification d’implémentation — niveau 0

## Environnement

- Python 3.11 minimum ;
- numpy ;
- scipy.sparse ;
- pytest ;
- numba optionnel, sans dépendance obligatoire ;
- pas de NetworkX dans le noyau.

## Arborescence cible

```text
src/cosmobox/level0/
  lattice.py
  encoding.py
  basis.py
  gauge.py
  operators.py
  hamiltonian.py
  reports.py
  params.py

tests/level0/
  test_lattice.py
  test_encoding.py
  test_basis.py
  test_gauge.py
  test_operators.py
  test_hamiltonian.py
```

## Géométries requises

- triangle ;
- chain3 ;
- ring4 ;
- ring5 ;
- ring6 ;
- disk7 : centre + anneau de six sommets, douze liens, six triangles.

Chaque géométrie fournit :

- nœuds ordonnés ;
- liens orientés et ordonnés ;
- arbre couvrant déterministe ;
- cordes hors arbre ;
- plaquettes orientées ;
- racine ;
- ordre des nœuds des feuilles vers la racine.

## Encodage canonique

Un état est représenté par la configuration complète :

(occupations fermioniques, flux de tous les liens).

### Occupations

- bits [0, N*M) ;
- bit b = i*M + alpha ;
- ordre Jordan–Wigner identique à l’ordre des bits.

### Flux

- trois bits par lien ;
- valeur stockée v_e = E_e + S ;
- 0 <= v_e <= 2S ;
- S supporté au niveau 0 : 1, 2, 3.

Lever une exception si N*M + 3L > 64.

La clé complète est un uint64. Les clés de la base sont triées. La recherche d’indice utilise searchsorted ou une table déterministe équivalente.

## Génération de la base physique

1. Énumérer les occupations dans le secteur de charge totale compatible avec les charges externes.
2. Regrouper les occupations par vecteur Q = (Q_1,…,Q_N).
3. Pour chaque Q, énumérer les flux des c = L-N+1 cordes.
4. Résoudre les flux de l’arbre des feuilles vers la racine avec G_i = 0.
5. Rejeter toute solution dont un flux sort de [-S,+S].
6. Vérifier explicitement la loi de Gauss à la racine.
7. Émettre les clés complètes occupation + flux.
8. Trier, dédupliquer et produire un rapport par secteur.

Le rapport doit contenir :

- multiplicité matière m(Q) ;
- nombre de flux admissibles n_flux(Q) ;
- dimension m(Q)*n_flux(Q) ;
- secteurs exclus ;
- moyenne et maximum de configurations de flux par occupation.

## Application des opérateurs

L’arbre couvrant sert uniquement à générer la base. Les opérateurs agissent sur la clé complète.

### Fermions

Le signe Jordan–Wigner est (-1)^P, où P est le nombre de bits occupés strictement entre les deux modes concernés.

### Quantum links

Pour m = -S,…,+S :

S^+|m> = sqrt(S(S+1)-m(m+1)) |m+1>.

Le code utilise U = S^+/sqrt(S(S+1)). Les amplitudes de bord nulles doivent être traitées sans générer d’état.

### H_hop

Pour chaque lien et saveur, générer explicitement le terme direct et son conjugué hermitien. Ne pas restaurer l’hermiticité par symétrisation a posteriori.

### H_B

Appliquer le produit orienté des opérateurs de lien autour de chaque plaquette, dans les deux sens. Rejeter l’image si un flux dépasse la troncation.

### H_dot et H_E

Construire séparément les contributions diagonales et hors-diagonales.

## Matrices creuses

- construire chaque terme séparément en COO puis CSR ;
- indices int32 tant que la dimension le permet ;
- valeurs complex128 ;
- conserver H_dot, H_hop, H_E et H_B séparés ;
- prévoir une évolution future matrix-free sans modifier les kernels d’application.

## Livrable du lot 1

Le premier lot ne contient que :

- lattice.py ;
- encoding.py ;
- leurs tests.

Le deuxième lot ajoute basis.py avec égalité exacte contre brute force comme critère d’acceptation.
