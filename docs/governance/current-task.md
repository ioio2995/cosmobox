# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. L'historique complet de gouvernance jusqu'à la clôture de Level 1 est archivé par snapshot Git dans [`../archive/current-task-through-level1.md`](../archive/current-task-through-level1.md).

## État Git

```text
BASE_BRANCH = main
BASE_COMMIT = 24e457b182c7fec41f3cb93f3101f02fef1f65cb
ACTIVE_BRANCH = research/level2-energy-regime
LEVEL2_L2B_DESIGN_CANDIDATE = bb16f57838cdddfb4eca94b8a78cce5a7ccebe1b
LEVEL2_L2C_PREREGISTRATION_CANDIDATE = 3169671bdfe1daaafdeb985aa175f35c49950576
LEVEL2_NUMERICAL_GUARD_PROTOCOL_CANDIDATE = f2a08b73e7109aa8ae8c8d3c30365b64f91f21d6
```

## État scientifique

```text
LEVEL0  = CLOSED
LEVEL1B = CLOSED
LEVEL1C = CLOSED
LEVEL1  = CLOSED
LEVEL2  = L2_C_NUMERICAL_GUARD_CALIBRATION

LAST_CLOSED_LEVEL = LEVEL1

LEVEL1C_PHYSICAL_VERDICT = INCONCLUSIVE
LEVEL1C_STOP_REASON      = INTER_J0_BRANCH_IDENTIFIABILITY_FAILURE
PHASE_G_OPENED           = NO

LEVEL2_PRIMARY_AXIS = ENERGY_SPECTRAL_REGIME
LEVEL2_IMPLEMENTATION = NOT_STARTED
LEVEL2_NORMATIVE_CAMPAIGN = NOT_STARTED
```

## Documents scientifiques actifs

- `docs/levels/level2/conceptual-framing.md`
- `docs/levels/level2/spectral-capability-audit.md`
- `docs/levels/level2/spectral-regime-design.md`
- `docs/levels/level2/profile-comparison-preregistration.md`
- `docs/levels/level2/numerical-guard-protocol.md`

## Résultat L2-A1 — préflight plein spectre

Le préflight technique non interprétatif a confirmé les six cas proposés :

```text
triangle S=2 : 88/88 eigenpairs, 22 groupes complets
triangle S=3 : 128/128 eigenpairs, 32 groupes complets
ring4    S=2 : 292/292 eigenpairs, 106 groupes complets
ring4    S=3 : 432/432 eigenpairs, 158 groupes complets
ring5    S=2 : 1000/1000 eigenpairs, 226 groupes complets
ring5    S=3 : 1504/1504 eigenpairs, 342 groupes complets

ALL_6_CASES_FULL_SPECTRUM_AVAILABLE = YES
PARTIAL_SUBSPACES = 0
NEW_SPECTRAL_APPROXIMATION_REQUIRED = NO
```

Aucune observable physique Level 2 n'a été inspectée pendant ce préflight.

## Design L2-B

Unité scientifique :

```text
complete spectral multiplet over the full spectrum
```

Coordonnées descriptives :

```text
epsilon = normalized exact energy position
q       = cumulative state-population coordinate, multiplicity-aware
```

Observable primaire et contrôle :

```text
PRIMARY = C_TT_conn
CONTROL = rho_QQ
```

Diagnostics gelés avant toute observation plein spectre :

```text
M_TT   = off-diagonal RMS strength of C_TT_conn
R_eff  = normalized entropy effective rank of C_TT_conn
A_QQ   = fraction of numeric rho_QQ ordered pairs
M_QQ   = RMS of numeric rho_QQ pairs only
```

Description primaire : profils continus en `q` et `epsilon`.

Synthèse secondaire : LOW/MID/HIGH = tiers égaux de population cumulative d'états.

## Pré-enregistrement L2-C — comparaison inter-S

```text
PROFILE_DOMAIN = q in [0,1]
PROFILE_REPRESENTATION = multiplicity-weighted exact step function
PRIMARY_CONTRAST = HIGH_MINUS_LOW
PRIMARY_METRICS = M_TT, R_eff
CONTROL_METRICS = A_QQ, M_QQ
INTER_S_BRANCH_MATCHING = FORBIDDEN
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
INTER_S_SHAPE_DESCRIPTORS = C_X_23, D_X_23
```

Taxonomie descriptive :

```text
NO_RESOLVED_SPECTRAL_CONTRAST
OPPOSITE_INTER_S_DIRECTION
SAME_INTER_S_DIRECTION
NOT_EVALUABLE
```

## Protocole de garde numérique

`docs/levels/level2/numerical-guard-protocol.md` gèle la méthode de calibration avant toute campagne normative.

Principe : comparer deux représentations mathématiquement équivalentes de chaque multiplet complet, obtenues par rotation unitaire déterministe de sa base interne, et publier uniquement les écarts numériques entre résultats.

```text
CALIBRATION_ROTATION_SEEDS = [0,1,2,3]
CALIBRATION_CASES = all six frozen Level2 cases
PUBLIC_ARTIFACT = discrepancies only
RAW_PHYSICAL_VALUES_EXPOSED = NO
NUMERICAL_GUARD_ROLE = REPRODUCIBILITY_ONLY
```

Pour chaque métrique primaire `X in {M_TT,R_eff}` :

```text
E_X = max over cases/seeds |Delta_HL(A) - Delta_HL(B_seed)|
```

Si `E_X > 0`, la candidate guard est le plafond de décennie `10^ceil(log10(E_X))`. Si `E_X == 0`, aucune garde arbitraire n'est inventée : statut `ZERO_EMPIRICAL_DISCREPANCY`, puis audit analytique requis.

Toute divergence de disponibilité ou de sémantique `rho_QQ` sous rotation fait échouer la calibration ; elle ne peut pas être absorbée dans une garde plus large.

## Prochaine étape

```text
NEXT_STEP = EXECUTE_NUMERICAL_ZERO_GUARD_CALIBRATION
NUMERICAL_GUARD_PROTOCOL = FROZEN
NUMERICAL_GUARD_VALUE = PENDING_CALIBRATION
```

Aucune campagne normative Level 2 n'est autorisée tant que la calibration n'est pas exécutée et auditée.

## Rôles de collaboration

```text
ChatGPT:
scientific lead / conceptual design / scientific documentation

Claude:
software implementation / repository operations / execution

Lionel:
intuition / direction / final decision
```

## Règles de progression

```text
- L'unité de progrès est l'expérience scientifique, pas le lot logiciel.
- Aucun résultat de Level 1C ne doit être réparé post-hoc : Level 1 est clos.
- Un défaut logiciel ne bloque que s'il peut altérer le résultat physique,
  sa provenance ou son interprétation.
- Aucun seuil binaire de réponse physique ne doit être réintroduit.
- Aucun observable physique plein spectre ne doit être exposé avant gel complet de L2-C.
- Aucune nouvelle métrique ne sera ajoutée après ouverture de la campagne pour améliorer le résultat.
- Aucun matching multiplet-par-multiplet S=2 vers S=3 n'est autorisé dans Level 2.
- La calibration numérique ne peut publier que des écarts entre calculs mathématiquement équivalents.
```

## Archive

Historique de gouvernance jusqu'à Level 1 :

- [`docs/archive/current-task-through-level1.md`](../archive/current-task-through-level1.md)

Le snapshot historique de référence de la clôture Level 1 est le commit :

```text
f2c63722e69f552a85212db5c4dd787d0c10c7cf
```
