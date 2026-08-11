# Conclusion scientifique — Level 1C

Statut : **clos**

Branche : `research/level1-correlators`

Ce document clôt scientifiquement Level 1C à partir exclusivement des résultats déjà obtenus et acceptés de l'unique exécution normative réelle (lot `1C-8l`, exécution acceptée, aucun commit associé) et des artefacts qu'elle a produits. Il ne recalcule rien, ne relance rien, ne répare rien, ne complète rien, n'extrapole rien. Toutes les valeurs numériques citées ici ont déjà été mesurées et rapportées dans le cadre du lot accepté ; ce document les organise en conclusion, sans en produire de nouvelles.

## 1. Objet et périmètre

Level 1C a exécuté, une seule fois, la campagne normative pré-enregistrée `J0×S` (`geometry ∈ {triangle, ring5}`, `S ∈ {2,3}`, `J0 ∈ {0.5,0.75,1.0,1.25,1.5}`, 20 cas) au travers du pipeline gelé :

```text
PHASE_P → BASELINE_NON_REGRESSION_GATE → PHASE_T → PHASE_R
```

jamais `PHASE_G`. Ce document ne couvre que le résultat de cette unique exécution acceptée et sa lecture méthodologique. Il ne couvre ni une reconstruction géométrique, ni une interprétation physique du régime de réponse, ni une comparaison inter-S de robustesse (`INTER_S_LEVEL1C_ROLE = ROBUSTNESS_ONLY`, non exécutée par ce lot).

## 2. Provenance

```text
campaign_id          = level1c-j0-response-v1
repository_commit    = 7d9ab03b1c6a386b9897a71ac89b558457d4ce80
manifest_fingerprint = 31e4c94f1758b426ef3ac05ecbc287ad7291d0b34b9a0c1329f5b746e22944e5
```

Artefacts produits par l'exécution normative (`1C-8l`), tous identiques et uniques sur ces trois champs de provenance :

```text
baseline-nonregression.json
  SHA-256 = 5032429ce20bb0ef0cc7d583a82a13b1576593fec366593e0b9d0f449c40b82c

tracking.jsonl
  SHA-256 = 60dd9336f559712be501c26f5c9d5e2a75a8a8fd77b8d812e77d7056d2105ce7

response.jsonl
  SHA-256 = 9d8ab45b3cbef0d131bddf28bc658c95b2533ff839a260836cb004c29e180be5
```

Ces artefacts, ainsi que les 20 répertoires `runs/<case_id>/{run.json,records.jsonl}` de `PHASE_P`, restent **non versionnés** sous `results/level1c/campaign/` (chemin ignoré par Git, conformément à la convention déjà établie pour la calibration et le préflight Level 1C) — ce document est la référence documentaire permettant de les identifier et de les vérifier ultérieurement, jamais une copie de leur contenu.

## 3. Résultat global de l'exécution

```text
PHASE_P                          : 20 / 20 cas success (global_success = true)
BASELINE_NON_REGRESSION_GATE     : PASS (e_ctt = 0.0, e_rho = 0.0, sur les 4 baselines)
PHASE_T                          : 40 records
  TRACKED_ONE_TO_ONE = 0
  NOT_AVAILABLE      = 32  (raison : CLASS_POOL_EMPTY)
  AMBIGUOUS          = 8   (raison : CLASS_POOL_NOT_UNIQUE, exclusivement sur target_id=first_excited)
PHASE_R                          : 40 records
  RESPONSE_AVAILABLE     = 0
  RESPONSE_NOT_AVAILABLE = 40
PHASE_G                          : NOT_OPENED
```

## 4. Verdict scientifique Level 1C

```text
LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
```

> La campagne normative Level 1C n'a produit aucune réponse physique évaluable, car aucune des 40 comparaisons inter-J0 pré-enregistrées n'a permis d'identifier une branche spectrale `TRACKED_ONE_TO_ONE`.

Conséquence directe et mécanique de ce résultat de tracking : `0` `Delta_C_TT` évaluable, `0` verdict de réponse physique produit par `PHASE_R` — chaque enregistrement `PHASE_R` porte exclusivement la raison `TRACKING_STATUS_NOT_TRACKED_ONE_TO_ONE`, jamais un échec d'intégrité, jamais un désaccord de provenance.

## 5. Interprétation obligatoire de `NOT_AVAILABLE`

Le contrat déjà gelé (`identifiability-preregistration.md` §20.12/20.13) établit :

```text
absence in production_window != physical discontinuity
```

Les 32 cas `NOT_AVAILABLE` (raison `CLASS_POOL_EMPTY`) signifient exclusivement :

> aucune branche compatible n'a pu être identifiée dans la fenêtre de production pré-enregistrée avec les composantes d'identité autorisées.

`CLASS_POOL_EMPTY` ne signifie jamais qu'une branche a physiquement disparu, ni qu'une réponse locale est absente. C'est un résultat d'identifiabilité structurelle du tracking pré-enregistré, jamais un résultat de dynamique physique.

## 6. Interprétation obligatoire de `AMBIGUOUS`

Les 8 cas `AMBIGUOUS` (raison `CLASS_POOL_NOT_UNIQUE`, tous sur `target_id=first_excited`) signifient exclusivement :

> plusieurs groupes perturbés satisfont les critères structurels autorisés, de sorte que l'identité de la branche ne peut pas être attribuée sans introduire un critère supplémentaire non pré-enregistré.

Aucune continuité n'est reconstruite post-hoc à partir de ces 8 cas. En particulier, ce document ne choisit et n'autorise aucun départage par `nearest energy`, `nearest spectral rank`, ou `nearest group_index` — ces critères sont explicitement interdits comme discriminants d'identité par le contrat de tracking déjà gelé (§20.11 : `representative_energy`/rang spectral/`spectral_window_group_index` jamais des identités inter-J0).

## 7. Verdict `H0`–`H4`

```text
H0 = NOT_EVALUABLE
H1 = NOT_EVALUABLE
H2 = NOT_EVALUABLE
H3 = NOT_EVALUABLE
H4 = NOT_EVALUABLE_FOR_LEVEL1C_RESPONSE
```

L'expérience n'a jamais atteint le stade permettant une conclusion sur ces hypothèses. Ce document n'écrit et n'autorise aucune formulation du type « H0 supported », « no physical response », « response absent », ou « local response absent » : ces hypothèses ne sont pas réfutées, elles ne sont **pas évaluables** à partir des données produites.

## 8. `PHASE_G`

```text
PHASE_G = NOT_OPENED
PHASE_G_STOP_REASON = NO_EVALUABLE_PHASE_R_RESPONSE
```

Aucune reconstruction métrique ou géométrique n'est justifiée par ce résultat. Ce document n'affirme jamais que la géométrie est réfutée (`geometry disproved`) ; la formulation correcte et seule autorisée est :

> les préconditions scientifiques nécessaires à l'ouverture de la phase géométrique n'ont pas été satisfaites.

## 9. Ce que Level 1C établit

- La campagne normative `J0×S` (20 cas) est numériquement exécutable de bout en bout, en une seule exécution, sans échec technique (`PHASE_P` : 20/20 `success`).
- Les quatre baselines `J0=1` (`triangle`/`ring5` × `S∈{2,3}`) reproduisent exactement le corpus historique Level 1B dans les tolérances de non-régression gelées (`gate PASS`, `e_ctt=e_rho=0.0`, tolérances `1e-15`/`1e-15`).
- Le pipeline `PHASE_P → BASELINE_NON_REGRESSION_GATE → PHASE_T → PHASE_R` fonctionne conformément à son contrat déjà accepté (aucune anomalie, aucune contradiction de provenance, aucun artefact incohérent).
- Le tracking inter-J0 pré-enregistré, avec les composantes d'identité et les fenêtres de production gelées, **ne permet pas** d'identifier de manière unique les branches spectrales requises sous variation de `J0` pour aucune des 40 comparaisons cible/arête.
- Aucune réponse physique inter-J0 n'est donc évaluable à partir de cette exécution.

Ce dernier point est une conclusion d'**identifiabilité**, jamais une conclusion de dynamique physique.

## 10. Ce que Level 1C n'établit pas

```text
Level 1C ne démontre pas :

- absence de réponse à une perturbation locale ;
- présence d'une réponse distribuée ;
- localité émergente ;
- non-localité ;
- distance effective ;
- métrique ;
- dimension ;
- topologie émergente ;
- courbure ;
- gravité ;
- convergence S → infini ;
- discontinuité physique des branches.
```

## 11. Ce qui reste hors périmètre de ce document

Toute nouvelle campagne, toute modification des fenêtres de production, toute nouvelle règle de tracking, tout élargissement de la grille `J0×S`, toute conception de Level 2 — voir `docs/levels/level1/level1-synthesis-and-closure.md` pour l'axe scientifique suivant retenu, non conçu ici.
