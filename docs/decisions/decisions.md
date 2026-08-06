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

## D015 — Gouvernance des échanges et des responsabilités

**Statut : gelé**

La charte `docs/collaboration-governance.md` définit le protocole obligatoire de collaboration entre Lionel ORCIL, ChatGPT, Claude Code et, exceptionnellement, Claude Fable.

Les responsabilités sont gelées ainsi :

- Lionel supervise, arbitre et autorise les jalons et actions Git ;
- ChatGPT est responsable de la cohérence scientifique et conceptuelle ;
- Claude Code est responsable de l’ingénierie et de l’implémentation ;
- Claude Fable intervient uniquement comme audit externe exceptionnel sur demande explicite de Lionel.

Chaque lot suit la séquence : cadrage scientifique, audit préalable, revue conceptuelle, autorisation, implémentation, rapport de livraison et validation.

Toute nouvelle mission destinée à Claude Code doit commencer par la lecture de `docs/collaboration-governance.md` et `docs/documentation-governance.md`, puis utiliser le format standard défini par la charte.

La formule courte officielle de remise en conformité est :

```text
Applique `docs/collaboration-governance.md` et reprends au dernier jalon validé.
```

D015 est complétée et partiellement supersédée sur le traitement Git des lots d’implémentation par D016.

## D016 — Livraison directe des lots d’implémentation

**Statut : gelé**

Lorsqu’un lot d’implémentation ou un correctif est autorisé sur une branche de travail explicitement désignée, cette autorisation inclut par défaut la chaîne complète :

```text
modifier → tester → stager explicitement → committer → pousser → vérifier → rapporter
```

Claude Code pousse donc le commit du lot avant de remettre son rapport de livraison. Le rapport fournit le SHA distant et le diff vérifiable afin que ChatGPT puisse effectuer immédiatement la revue réelle du code, sans échange intermédiaire consacré uniquement à l’autorisation du commit ou du push.

Cette autorisation intégrée reste strictement bornée :

- seuls les fichiers du périmètre validé peuvent être inclus ;
- le push est limité à la branche de travail désignée ;
- tout fichier sans rapport doit rester exclu ;
- toute divergence de périmètre ou de branche impose un arrêt avant publication ;
- aucun force-push ou écrasement d’historique n’est autorisé ;
- aucune PR, fusion, release ou modification normative hors périmètre n’est autorisée implicitement ;
- le passage au lot suivant reste soumis à la revue de ChatGPT et à la validation de Lionel.

Un commit poussé ou une suite de tests réussie ne vaut pas acceptation scientifique du lot.

## D018 — Formule de gamma_O et labels de symétrie inter-S du niveau 1B

**Statut : gelé**

Ces décisions comblent les lacunes identifiées lors de l'audit du lot 1B-6 : `docs/levels/level1/specification.md` §9 et §12 nommaient `gamma_O` et les labels de symétrie sans en donner la formule exacte.

**Formule de `gamma_O`** (diagnostic primaire de robustesse, pour une observable scalaire réelle ou complexe `O` évaluée aux deux plus grandes valeurs disponibles de `S`) :

```text
difference = |O_high - O_low|
amplitude  = max(|O_high|, |O_low|)

si amplitude <= NORMALIZATION_FLOOR (1e-12) :
    gamma_O.value = null
    gamma_O.null_reason = "normalization_denominator_below_floor"
sinon :
    gamma_O = difference / amplitude
```

Le plancher sert à décider que la normalisation n'est pas physiquement interprétable ; il ne remplace jamais le dénominateur pour fabriquer une valeur artificielle. `gamma_O` est symétrique entre les deux valeurs de `S`, sans dimension, invariant sous une renormalisation multiplicative commune non nulle, et borné par 2 hors plancher.

Le verdict secondaire binaire reste celui déjà gelé par D013 : `robuste` si `difference <= max(0.05, 0.15 * amplitude)`, `non_robuste` sinon ; à la frontière exacte, le verdict est `robuste`. `gamma_O` (continu) et le verdict (binaire) ne sont pas redondants et sont tous deux conservés.

**`G_occ`** : la construction physique de `G_occ` (normalisation par les occupations locales) reste hors périmètre du lot 1B-6. L'infrastructure de robustesse accepte une valeur `G_occ` déjà calculée en amont et lui applique la même formule `gamma_O`/verdict qu'à tout autre scalaire de la liste fermée — elle n'invente jamais le calcul de `G_occ` lui-même.

**Label de saveur `T`** : pour un groupe complet, `c_T = Tr(rho · T²)` (Casimir moyen déjà calculable via les primitives 1B-2/1B-3 existantes). Le demi-entier `T` est celui qui résout `T(T+1) ≈ c_T`, stocké sous forme exacte `twice_T: int` (`T = twice_T / 2`). Le label n'est normatif que si le résidu `δ_T = |c_T - T(T+1)| <= 1e-8` ; sinon le label est indisponible et l'appariement exact est impossible pour ce groupe.

**Labels de translation et de réflexion** : pour chaque générateur de symétrie `A` appartenant réellement au sous-groupe qui laisse le Hamiltonien invariant (jamais supposé depuis le seul graphe nu, conformément au résultat V07 déjà accepté), le label normatif est le caractère restreint `chi_A = Tr(Psi† U_A Psi)` sur le multiplet complet. Il n'est accepté comme label normatif qu'après validation de la stabilité du sous-espace sous `U_A` (`||(I - Pi) U_A Psi||_F <= 1e-8`) et de l'unitarité de l'opérateur restreint (`||Psi† U_A Psi)† (Psi† U_A Psi) - I||_F <= 1e-8`). `chi_A` est invariant sous `Psi -> Psi V`.

Le qualificatif « lorsqu'elle est définie » (spécification §12) s'applique **à chaque générateur individuellement**, translation et réflexion également : un générateur qui n'appartient pas au sous-groupe de symétrie du Hamiltonien effectif (par exemple la translation sous `j_break`) est marqué `not_applicable`, jamais remplacé par une valeur numérique arbitraire. Trois états distincts sont représentés pour chaque label de symétrie — `numeric` (valeur calculée et validée), `not_applicable` (générateur non symétrique à ce point), `unavailable` (générateur applicable mais calcul invalide, résidu au-dessus de la tolérance) — jamais confondus dans une simple valeur `None`.

Deux caractères sont considérés égaux si `|chi_A^(1) - chi_A^(2)| <= 1e-8 * max(1, |chi_A^(1)|, |chi_A^(2)|)`.

**Clé d'appariement inter-S** : géométrie, identité du Hamiltonien à l'exception de `S` (paramètres `J`, `h`, `t`, `g_E`, `K`, secteur physique, charges externes éventuelles), statut (`complete_multiplet`/`partial_subspace`), multiplicité, `twice_T`, label de translation, label de réflexion. Le rang énergétique n'entre jamais dans cette clé — il sert uniquement à rechercher les candidats et à détecter une fenêtre incomplète.

L'appariement inter-S exige un Hamiltonien identique à l'exception de `S` : le point de référence `J_i=1` s'apparie uniquement avec lui-même, un cas `j_break` s'apparie uniquement avec exactement le même cas `j_break` ; comparer la référence à `j_break`, ou deux perturbations différentes entre elles, est interdit.

Statuts d'appariement (déjà nommés en §12, formalisés ici) : `exact_label_match` (exactement un candidat de multiplicité et labels identiques), `ambiguous_cross_truncation_match` (plusieurs candidats, label requis indisponible d'un seul côté, ou troncature empêchant une décision), `target_group_not_in_window` (groupe attendu absent de la fenêtre), `structurally_not_applicable` (catégorie physique inexistante pour cette géométrie, ex. `ring4`/T=3/2). Une multiplicité différente interdit toujours `exact_label_match`, même si `T` ou un caractère coïncident par ailleurs. Un groupe `partial_subspace` ne produit jamais d'`exact_label_match` normatif.

**Groupes tronqués et verdicts** : pour un groupe `partial_subspace`, une différence ou un `gamma_O` exploratoire peut être calculé si les deux valeurs existent, mais aucun verdict `robuste`/`non_robuste` n'est produit — `verdict = indeterminate`, `null_reason = "truncated_spectral_group"`. Cette raison décrit l'impossibilité de conclure à partir du statut du groupe lui-même, distincte de `"ambiguous_cross_truncation_match"` qui décrit l'échec du processus d'appariement ; les deux ne sont jamais fusionnées.

**Types comparables** : les verdicts de robustesse ne s'appliquent qu'aux scalaires (réels ou complexes) de la liste fermée déjà gelée par D013 (`gamma_O`, `G_occ`, `rho_QQ`, `C_TT_conn`, `flavor_singular_value_ratio`, `path_phase_coherence`). Aucune métrique n'est définie sur les listes (valeurs propres, valeurs singulières), la matrice `G` complète, `flavor_frobenius_squared`, ou les statistiques d'orbite non inscrites dans cette liste.

## Questions ouvertes

- organisation logicielle des utilitaires de campagne, mutualisés ou locaux ;
- protocole d’injection d’énergie des niveaux 2 et 3 ;
- mécanisme éventuel de la piste B pour obtenir une phase non-expandeur ;
- définition et validation d’une future distance effective ;
- admissibilité de `disk7` après comptage de base et garde-fous de ressources.
