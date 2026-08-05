# Journal des décisions

## D001 — Séparation de l’ancien prototype

**Statut : gelé**

L’ancien simulateur classique de maillage déformable n’est pas utilisé comme fondation du solveur quantique. Il reste dans l’historique et pourra fournir ultérieurement des outils de visualisation.

## D002 — Deux pistes indépendantes

**Statut : gelé**

- piste A : topologie imposée, jauge et métrique effective ;
- piste B : graphe dynamique et recherche d’une dimension finie.

Aucun Hamiltonien unique ne doit mélanger ces deux problèmes au niveau 0.

## D003 — Périmètre du niveau 0

**Statut : gelé**

Le niveau 0 porte uniquement sur la construction exacte du modèle de jauge fini : géométries, encodage, base physique, opérateurs, Hamiltonien et tests.

## D004 — Représentation canonique des états

**Statut : gelé**

Chaque état est stocké comme occupations fermioniques + flux de tous les liens. Les coordonnées de cycles ne servent qu’à générer efficacement la base.

## D005 — Quantum link fini

**Statut : gelé pour le prototype**

Les liens utilisent une représentation de spin S = 1,2,3. U = S^+/sqrt(S(S+1)) n’est pas unitaire. La robustesse vis-à-vis de S doit être testée avant toute interprétation physique.

## D006 — Modèle local à M = 2

**Statut : gelé pour le lot 1**

Le site local est appelé « dot fermionique interactif à deux saveurs ». Il contient une interaction quartique unique de type Hubbard symétrisé et une matrice quadratique hermitienne 2x2. Il n’est pas présenté comme un régime SYK.

## D007 — Géométries du niveau 0

**Statut : gelé**

triangle, chain3, ring4, ring5, ring6 et disk7.

## D008 — Langage et bibliothèques

**Statut : gelé pour le niveau 0**

Python >= 3.11, numpy, scipy.sparse, pytest. Numba est optionnel. NetworkX n’est pas utilisé par le noyau.

## D009 — Développement incrémental

**Statut : gelé**

Ordre des lots :

1. lattice.py + encoding.py ;
2. basis.py et comparaison brute force ;
3. gauge.py + operators.py ;
4. hamiltonian.py ;
5. rapports et tests de troncation ;
6. seulement ensuite, protocole du niveau 1.

## D010 — Critère scientifique

**Statut : gelé**

Un résultat négatif doit rester possible. Les seuils et diagnostics ne sont pas ajustés après observation pour sauver l’hypothèse.

## Questions ouvertes

- valeur finale de h/J après le lot 1 ;
- taille maximale accessible en diagonalisation exacte ;
- définition finale des distances du niveau 1 ;
- protocole d’injection d’énergie des niveaux 2 et 3 ;
- mécanisme éventuel de la piste B pour obtenir une phase non-expandeur.
