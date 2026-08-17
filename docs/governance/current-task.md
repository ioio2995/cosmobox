# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md). Le contrat scientifique actif Level 3 est [`../levels/level3/s4-first-campaign-preregistration.md`](../levels/level3/s4-first-campaign-preregistration.md).

## État Git

```text
ACTIVE_BRANCH = research/level2-energy-regime

LEVEL3_A_SPIN_ENCODING_IMPLEMENTATION = c7e43771fdf3ed23720bfb245c8c8d3bb320a257
LEVEL3_B_GENERIC_EXECUTION_IMPLEMENTATION = ce2c7a16387490bb13ba1156249ea1129ec3bbc9
LEVEL3_C_GOVERNANCE_OPENING = 8cbefa7b712915b15a07e68686e92480062634e6
LEVEL3_D_GOVERNANCE_OPENING = fdade60527e5e51b896e90757c79b7c5c0fec9a0
LEVEL3_E_GOVERNANCE_OPENING = 2f03736021d626f00ec2f58c6d4dd67b84be1d44
LEVEL3_E_FULL_SPECTRUM_POLICY_IMPLEMENTATION = d8281b48b836a3ce14bb05cd739ea6b22f4a7ea4
LEVEL3_F_S4_SCIENTIFIC_PREREGISTRATION = 1c1d71f07dd6a7399b3965b2bb0acfa5c665991e
```

## État scientifique

```text
LEVEL0 = CLOSED
LEVEL1 = CLOSED
LEVEL2 = CLOSED
LEVEL3 = S4_PREREGISTERED

LAST_CLOSED_LEVEL = LEVEL2
LAST_ACCEPTED_SOFTWARE_LOT = L3-E-FULL-SPECTRUM-EXECUTION-POLICY
LAST_FROZEN_SCIENTIFIC_JALON = L3-F-S4-SCIENTIFIC-PREREGISTRATION

LEVEL2_PRIMARY_TEST = POSITIVE
CROSS_GEOMETRY_STATUS = CROSS_GEOMETRY_RECURRENT
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Référence scientifique Level 2

```text
CAMPAIGN_ID = level2-energy-regime-v1
MANIFEST_FINGERPRINT = 82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4
REPOSITORY_COMMIT = 1feb03f41f9e73078efbc760dd2cba2b667e2ed0
CAMPAIGN_STATUS = COMPLETE
```

Level 2 reste immuable et clos.

## Capacités Level 3 établies

```text
LEVEL0_SPIN_ENCODING_GENERIC = YES
LEVEL3_CASESPEC_GENERIC = YES
LEVEL3_RUN_CASE_IMPLEMENTED = YES
LEVEL3_SPIN_PAIR_COMPARISON = YES
LEVEL3_FULL_SPECTRUM_POLICY = IMPLEMENTED
LEVEL3_SPARSE_FALLBACK_POSSIBLE = NO

TRIANGLE_S4_DIMENSION = 168
RING4_S4_DIMENSION = 572
RING5_S4_DIMENSION = 2008
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008
```

Le benchmark L3-D a établi qu'un eigensystème Hermitien dense complet à `D=2008` est praticable dans l'environnement testé. L3-E garantit qu'une demande Level3 de spectre complet produit un eigensystème complet ou échoue explicitement avant toute observable.

Aucun Hamiltonien physique `S=4` n'a encore été construit ou diagonalisé.

## Contrat scientifique Level 3 gelé

Source normative :

```text
docs/levels/level3/s4-first-campaign-preregistration.md
```

Contrat :

```text
LEVEL3_FIRST_NEW_SPIN = 4
LEVEL3_NEW_CASES = triangle:S4, ring4:S4, ring5:S4
FULL_SPECTRUM = REQUIRED
PRIMARY_PAIR = S3_TO_S4
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
PRIMARY_CONTRAST = HIGH_MINUS_LOW
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
INTER_S_BRANCH_MATCHING = FORBIDDEN
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
NUMERICAL_GUARD_M_TT = 1e-16
NUMERICAL_GUARD_R_EFF = 1e-15
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Taxonomie primaire `S3 <-> S4` :

```text
S4_DIRECTION_PERSISTS
S4_DIRECTION_REVERSES
S4_CONTRAST_UNRESOLVED
NOT_EVALUABLE
```

La campagne publiera aussi la séquence `S=2,3,4` et les descripteurs continus pré-enregistrés `T_X_23`, `T_X_34`, `R_DELTA_X`, `C_X_34`, `D_X_34`, `R_D_X`, sans seuil de convergence.

Quelle que soit l'issue de `S=4` :

```text
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
PHASE_GEOMETRY = CLOSED
PHASE_GRAVITY = CLOSED
```

## Lot courant — L3-G

```text
LOT = L3-G-S4-CAMPAIGN-INFRASTRUCTURE-AUDIT
STATUS = OPEN
TYPE = SOFTWARE_AUDIT_ONLY

CODE_CHANGE_AUTHORIZED = NO
COMMIT_AUTHORIZED = NO
PUSH_AUTHORIZED = NO
REAL_S4_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S4_DIAGONALIZATION_AUTHORIZED = NO
S4_OBSERVABLES_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : auditer l'infrastructure minimale nécessaire pour matérialiser le pré-enregistrement scientifique gelé dans des contrats Level 3 dédiés : manifeste, schéma, sérialisation, runner, provenance et contrôles de campagne.

L'audit doit déterminer comment :

```text
- exécuter uniquement les trois nouveaux cas S=4 ;
- réutiliser les artefacts Level 2 gelés comme référence normative S2/S3 ;
- produire les comparaisons S3<->S4 sans recomputer silencieusement la provenance Level2 ;
- sérialiser la taxonomie S4_DIRECTION_* ;
- sérialiser les descripteurs T_X_23/T_X_34/R_DELTA_X/C_X_34/D_X_34/R_D_X ;
- garantir full spectrum / provenance / atomicité / reprise sans inspection partielle post-hoc ;
- empêcher toute ouverture implicite de S=5.
```

Aucun code ni aucune exécution physique ne sont autorisés pendant cet audit.

## Invariants Level 3

```text
- Level 2 reste immuable et clos.
- Les artefacts Level2 gelés sont les références normatives S2/S3.
- Aucune définition physique ne change.
- Aucun nouvel observable n'est créé.
- Aucun seuil de convergence scientifique n'est défini.
- Aucun matching multiplet-par-multiplet inter-S.
- Aucune donnée physique S>3 hors des trois cas S4 pré-enregistrés.
- Aucune exécution S4 avant implémentation, audit et autorisation explicite de campagne.
- Une demande full-spectrum ne peut jamais être satisfaite par un résultat partiel.
- PHASE_GEOMETRY reste CLOSED.
- PHASE_GRAVITY reste CLOSED.
```

## Étape suivante

```text
NEXT_STEP = L3_G_S4_CAMPAIGN_INFRASTRUCTURE_AUDIT
REAL_S4_EXECUTION = FORBIDDEN
```

Après audit Claude, ChatGPT arbitre l'architecture. Lionel autorise ensuite explicitement l'implémentation éventuelle. Aucune implémentation et aucune exécution `S=4` ne sont autorisées implicitement par l'ouverture de l'audit.

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation / audit

Claude:
software implementation / repository operations / execution

Lionel:
intuition / direction / final decision
```

## Règle de progression

Aucun lot suivant ne peut être ouvert implicitement par un `PASS`, une recommandation ou un rapport favorable. Toute nouvelle action de Claude exige un mandat explicite conforme à `docs/governance/collaboration-governance.md`.
