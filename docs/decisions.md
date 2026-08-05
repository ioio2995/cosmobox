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

## D011 — Hamiltonien niveau 0 implémenté (lots 4A-4C)

**Statut : gelé**

H = H_dot + H_hop + H_E + H_B est implémenté dans `src/cosmobox/level0/hamiltonian.py`, assemblé sur la base physique exacte produite par `basis.py` :

- H_dot = Σ_i [ J_i(n_i1-1/2)(n_i2-1/2) + Σ_αβ h^(i)_αβ c†_iα c_iβ ], M=2 uniquement (D006).
- H_hop = -t Σ_{e=(i→j),α} [ c†_iα U_e c_jα + c†_jα U_e† c_iα ], `t` scalaire réel global, diagonal en saveur — aucune matrice `t_{e,αβ}` au niveau 0.
- H_E = (g_E/2) Σ_e E_e², linéaire en g_E.
- H_B = -K Σ_p (W_p + W_p†). `W_p` est le produit ordonné des opérateurs de lien suivant `Plaquette.steps` parcouru en ordre inversé, sens inchangés (`+1→U_e`, `-1→U_e†`). `W_p†` parcourt `Plaquette.steps` dans l'ordre original avec chaque sens inversé — jamais construit comme le conjugué numérique de l'amplitude de `W_p` sur la même clé.

Chaque terme est assemblé séparément (COO puis CSR), indexé par une correspondance clé→ligne (`build_key_index`) partagée et validée (`validate_key_index`) ; toute transition vers une clé hors base lève une exception d'invariant, jamais ignorée silencieusement. `HamiltonianTerms` regroupe les quatre termes (copie défensive à la construction, `dtype=complex128`, forme carrée commune vérifiée) et expose `.total`, recalculé à chaque accès (non mis en cache).

Couverture de tests (voir `docs/validation-plan.md`) : T1, T2, T3, T7, T8, T9 validés pour les quatre termes et le total dans `tests/level0/test_hamiltonian.py`. `disk7` est validé au niveau des actions élémentaires (`W_p`/`W_p†` sur un échantillon déterministe de la base réelle), jamais par assemblage matriciel complet — sa base physique dépasse 450 000 états, coût jugé déraisonnable pour la suite de tests courante.

## Questions ouvertes

- valeur finale de h/J après le lot 1 ;
- taille maximale accessible en diagonalisation exacte (point de repère empirique : `disk7` à M=2,S=1 dépasse 450 000 états dans la base physique, cf. D011 — question toujours ouverte, non tranchée) ;
- définition finale des distances du niveau 1 ;
- protocole d’injection d’énergie des niveaux 2 et 3 ;
- mécanisme éventuel de la piste B pour obtenir une phase non-expandeur.
