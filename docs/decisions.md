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

H = H_dot + H_hop + H_E + H_B est implémenté dans `src/cosmobox/level0/hamiltonian.py`, assemblé sur la base physique exacte produite par `basis.py`.

Toute transition vers une clé hors base lève une exception d’invariant, jamais ignorée silencieusement.

## D012 — Re-périmétrage du niveau 1

**Statut : gelé**

La trajectoire scientifique est désormais :

1. niveau 0 : substrat physique exact, spectre, dégénérescences et symétries ;
2. niveau 1A : classification des symétries, close dans la campagne historique du niveau 0 ;
3. niveau 1B : corrélateurs relationnels invariants de jauge ;
4. niveau futur : construction et validation d’une distance effective ;
5. niveau futur : structure causale ou cône relationnel ;
6. niveau futur : corrélations du secteur de jauge pur et matière–jauge.

La distance combinatoire du graphe sert uniquement à sélectionner les chemins minimaux. Elle n’est pas une observable émergente.

Aucune transformation logarithmique des corrélateurs en distance n’est autorisée au niveau 1B.

La spécification normative du niveau 1B est `docs/level1-specification.md`, conformément à l’organisation documentaire du niveau 0.

## D013 — Gel scientifique du niveau 1B

**Statut : gelé**

Les décisions suivantes sont figées :

- transporteur U_e=S_e^+/sqrt(S(S+1)), nu_S=1 ;
- état mixte canonique rho=Pi/d pour les multiplets complets ;
- groupes tronqués marqués `partial_subspace`, sans conclusion définitive ;
- C_TT_raw et C_TT_conn inclus ;
- secteur de jauge pur et corrélations matière–jauge hors périmètre ;
- gamma_O observable primaire de robustesse ;
- verdicts secondaires limités à G_occ, rho_QQ, C_TT_conn, `flavor_singular_value_ratio` et `path_phase_coherence` ;
- seuil absolu 0.05 et relatif 0.15 ;
- fenêtres spectrales : triangle 16, ring4 20, ring5 24 ;
- `ring5`, S=3, admis avec une dimension physique de 1504 ;
- dimensions de référence S=1,2,3 :
  - triangle : 48 / 88 / 128 ;
  - ring4 : 152 / 292 / 432 ;
  - ring5 : 496 / 1000 / 1504 ;
- point de référence J_i=1 ;
- contrôle `j_break` : triangle et ring5 à S=2, fenêtres 16 et 24, J_0=1.5 et J_i=1 ailleurs ;
- désordre gaussien hors niveau 1B ;
- orbites déterminées par le groupe de symétrie du Hamiltonien ;
- statistiques d’orbite gelées : moyenne, dispersion maximale par paire et défaut de covariance ;
- aucune moyenne entre orbites, longueurs de chemin, groupes spectraux ou définitions d’observables distincts ;
- diagnostics non hermitiens limités à la trace normalisée, aux valeurs singulières et à la norme de Frobenius ;
- décomposition de Schur, spectre complexe et vecteurs propres non hermitiens exclus ;
- schéma de sortie v1, manifeste pré-enregistré et plan de validation obligatoires.

Aucune de ces décisions ne peut être modifiée après observation des corrélateurs sans nouvelle décision explicite.

## D014 — Gouvernance normative de la documentation

**Statut : gelé**

La charte `docs/documentation-governance.md` définit l’architecture documentaire obligatoire du dépôt.

Les règles suivantes sont notamment gelées :

- une spécification normative de niveau réside dans `docs/levelN-specification.md` ;
- `features/` est réservé aux propositions temporaires et non gelées ;
- une feature validée est migrée vers `docs/`, `experiments/`, `schemas/` et le plan de validation approprié, puis supprimée ;
- une information normative possède une source de vérité principale ;
- le README est une synthèse et ne remplace aucun document normatif ;
- aucun gel ne peut être déclaré tant que des contradictions de statut ou de valeur subsistent ;
- tout push documentaire final doit être vérifié sur le diff réel, fichier par fichier ;
- le succès d’une mise à jour de référence Git ne prouve pas qu’un contenu annoncé a été modifié.

Toute évolution de ces règles exige une nouvelle décision explicite.

## Questions ouvertes

- organisation logicielle des utilitaires de campagne, mutualisés ou locaux ;
- protocole d’injection d’énergie des niveaux 2 et 3 ;
- mécanisme éventuel de la piste B pour obtenir une phase non-expandeur ;
- définition et validation d’une future distance effective ;
- admissibilité de `disk7` après comptage de base et garde-fous de ressources.
