# Synthèse et clôture scientifique — Level 1

Statut : **clos**

Branche : `research/level1-correlators`

Ce document articule et clôt globalement Level 1 (Level 1B + Level 1C) à partir exclusivement des conclusions déjà gelées de `docs/levels/level1/level1b-conclusion.md` et `docs/levels/level1c/level1c-conclusion.md`. Il ne recalcule rien, ne relance rien, et ne tranche aucune question laissée explicitement ouverte par ces deux documents.

```text
LEVEL1 = CLOSED
```

## 1. Deux volets, deux natures de résultat

```text
LEVEL1B : successful robustness result
LEVEL1C : inconclusive physical-response result, because branch identifiability failed
```

Level 1B et Level 1C répondent à deux questions différentes, jamais fusionnées :

- Level 1B teste si des observables relationnelles invariantes de jauge, déjà mesurées, sont **robustes** vis-à-vis d'une variation de troncature du spin de lien `S`.
- Level 1C tente de mesurer la **réponse** de ces mêmes catégories d'observables sous une perturbation locale du Hamiltonien (`J0`), ce qui suppose au préalable de pouvoir **suivre** (« tracker ») une branche spectrale identifiée entre le point de référence et le point perturbé.

Level 1B a atteint son objectif dans le périmètre testé. Level 1C n'a pas atteint le sien, non pas parce que la réponse mesurée serait nulle ou non significative, mais parce que l'étape préalable d'identification de branche n'a abouti pour aucune des 40 comparaisons pré-enregistrées.

## 2. Résultat consolidé Level 1B (rappel, non recalculé)

```text
7 groupes spectraux appariés exactement (exact_label_match) entre S=3 et S=2

712 comparaisons source (liste fermée : gamma_O, rho_QQ, C_TT_conn, flavor_singular_value_ratio)
684 comparaisons évaluables
28 comparaisons non évaluables

684 verdicts robust
0 verdict non_robust
0 verdict indeterminate
```

Ces chiffres sont exactement ceux déjà acceptés et gelés par `level1b-conclusion.md` (§3) — ils ne sont pas recalculés ici.

**Précision de portée impérative, déjà explicite dans la clôture Level 1B (§4/§13/§14) et rappelée ici sans en changer le sens :**

```text
S=2 vs S=3 robustness != proof of convergence as S -> infini
```

La campagne Level 1B compare exactement deux points de troncature (`S=2`, `S=3`) ; elle ne démontre ni une limite continue, ni une convergence d'une suite en `S`, ni une extension à des valeurs `S > 3`.

## 3. Résultat consolidé Level 1C (rappel, non recalculé)

```text
LEVEL1C_NORMATIVE_EXECUTION = ACCEPTED
LEVEL1C_PHYSICAL_VERDICT    = INCONCLUSIVE
LEVEL1C_STOP_REASON         = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE

TRACKED_ONE_TO_ONE = 0 / 40
NOT_AVAILABLE      = 32 / 40  (CLASS_POOL_EMPTY)
AMBIGUOUS          = 8 / 40   (CLASS_POOL_NOT_UNIQUE)

RESPONSE_AVAILABLE     = 0 / 40
RESPONSE_NOT_AVAILABLE = 40 / 40

H0-H4 = NOT_EVALUABLE (H4 = NOT_EVALUABLE_FOR_LEVEL1C_RESPONSE)
PHASE_G = NOT_OPENED (NO_EVALUABLE_PHASE_R_RESPONSE)
```

Voir `docs/levels/level1c/level1c-conclusion.md` pour la provenance complète, les hashes d'artefacts, et l'interprétation obligatoire détaillée de `NOT_AVAILABLE`/`AMBIGUOUS`/`H0`–`H4`/`PHASE_G` — non répétée ici dans son intégralité.

## 4. Conclusion globale de Level 1

> Level 1 établit que, dans les groupes spectraux pouvant être appariés entre `S=2` et `S=3`, les observables relationnelles invariantes de jauge étudiées sont robustes vis-à-vis de cette variation de troncature selon le critère pré-enregistré. En revanche, la tentative de mesurer leur réponse sous perturbation locale `J0` n'a pas pu être menée jusqu'à une comparaison physique, car les composantes d'identité spectrale pré-enregistrées ne permettent pas de suivre sans ambiguïté les branches requises dans les fenêtres de production gelées.

> Le niveau ne fournit donc aucune preuve d'une géométrie émergente ni d'une réponse gravitationnelle effective.

Cette distinction — robustesse établie d'un côté, identifiabilité de l'évolution non acquise de l'autre — reste centrale et ne doit jamais être résumée en un verdict unique agrégé pour tout Level 1.

## 5. `METHODOLOGICAL_LESSON`

> La robustesse d'une observable et l'identifiabilité de son évolution sont deux problèmes différents. Level 1B valide la première dans le périmètre testé ; Level 1C montre que la seconde n'est pas acquise avec les seules identités spectrales et fenêtres retenues.

C'est la conclusion méthodologique la plus importante du niveau : un résultat de robustesse structurelle, même solide, ne garantit pas qu'une branche donnée reste identifiable sous une perturbation continue du Hamiltonien avec le seul jeu de composantes d'identité pré-enregistrées (`twice_T`, caractère de réflexion, `complete_multiplet`) — la multiplicité et l'organisation du spectre perturbé peuvent rendre cette identification structurellement non unique ou vide, indépendamment de toute question de robustesse.

## 6. `NEXT_SCIENTIFIC_AXIS`

> Le prochain niveau devra étudier la dépendance de l'organisation relationnelle au régime énergétique/spectral, plutôt que poursuivre immédiatement une reconstruction géométrique à partir d'une branche basse particulière.

Seul l'axe **exploration du régime énergétique/spectral** (`energy / spectral regime exploration`) est retenu ici comme direction. Ce document ne conçoit pas Level 2 : aucun nouveau Hamiltonien, aucun nouveau manifeste, aucune grille de température (`beta`), aucune fenêtre microcanonique, aucune implémentation de graphe dynamique, de temps émergent, ou de gravité n'est proposée ou autorisée par ce document. Ces choix restent entièrement ouverts pour un futur lot de conception de Level 2, non ouvert ici.

## 7. Ce que Level 1 (B+C) n'établit à aucun titre

Reprise consolidée des exclusions déjà gelées séparément par les deux clôtures (`level1b-conclusion.md` §14, `level1c-conclusion.md` §10) :

```text
- une limite S -> infini ;
- une distance physique émergente, une métrique, une courbure ;
- une causalité, une gravité émergente ;
- une topologie continue, une dimension émergente ;
- l'unicité d'un plongement géométrique quelconque ;
- une absence ou une présence de réponse physique à une perturbation locale ;
- une localité ou une non-localité de réponse ;
- une discontinuité physique de branche spectrale ;
- toute interprétation géométrique d'un secteur spectral particulier.
```

## 8. Séquençage

```text
Level 1B : clos (robustesse inter-S établie dans le périmètre testé)
    ↓
Level 1C : clos (réponse inter-J0 inconclusive — échec d'identifiabilité de branche)
    ↓
Level 1 : CLOSED
    ↓
Level 2 : non commencé, non conçu par ce document — axe retenu : régime énergétique/spectral (§6)
```

Aucun travail de Level 2 n'est démarré par ce document. Aucune nouvelle campagne normative n'est autorisée par ce document.
