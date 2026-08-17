# Contrat de continuité — état courant

Ce document contient uniquement l'état actif du projet. La clôture scientifique de Level 2 est figée dans [`../levels/level2/synthesis-and-closure.md`](../levels/level2/synthesis-and-closure.md). Le contrat scientifique actif Level 3 est [`../levels/level3/s4-first-campaign-preregistration.md`](../levels/level3/s4-first-campaign-preregistration.md).

## État Git

```text
ACTIVE_BRANCH = research/level2-energy-regime

LEVEL3_A_SPIN_ENCODING_IMPLEMENTATION = c7e43771fdf3ed23720bfb245c8c8d3bb320a257
LEVEL3_B_GENERIC_EXECUTION_IMPLEMENTATION = ce2c7a16387490bb13ba1156249ea1129ec3bbc9
LEVEL3_E_FULL_SPECTRUM_POLICY_IMPLEMENTATION = d8281b48b836a3ce14bb05cd739ea6b22f4a7ea4
LEVEL3_F_S4_SCIENTIFIC_PREREGISTRATION = 1c1d71f07dd6a7399b3965b2bb0acfa5c665991e
LEVEL3_G_GOVERNANCE_OPENING = 39dac03a67de3c3907d08e9cdddd2fd9b4d09db7
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
LAST_ACCEPTED_AUDIT = L3-G-S4-CAMPAIGN-INFRASTRUCTURE-AUDIT

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

L'audit L3-G a vérifié que les artefacts locaux existants de cette campagne contiennent les profils spectraux complets S=2/S=3 nécessaires à Level3 :

```text
LEVEL2_FROZEN_S2_PROFILE_AVAILABLE = YES
LEVEL2_FROZEN_S3_PROFILE_AVAILABLE = YES
LEVEL2_RECOMPUTATION_REQUIRED = NO
LEVEL2_RECOMPUTATION_AUTHORIZED = NO
```

Mais ces artefacts sont actuellement sous `results/`, répertoire ignoré par Git. Ils ne constituent donc pas encore une référence durable reproductible pour Level3.

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
INTER_S_BRANCH_MATCHING = FORBIDDEN
PHYSICAL_EFFECT_THRESHOLD = NOT_APPLICABLE
P_VALUE = NOT_APPLICABLE
COMPOSITE_SCORE = FORBIDDEN
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Aucune donnée physique S=4 n'a encore été produite.

## Audit L3-G — verdict accepté

```text
L3_G_S4_CAMPAIGN_INFRASTRUCTURE_AUDIT = PASS
LEVEL3_MANIFEST_DESIGN = READY
LEVEL3_SCHEMA_DESIGN = READY
LEVEL3_SERIALIZATION_DESIGN = READY
LEVEL3_RUNNER_DESIGN = READY
LEVEL3_ATOMICITY_DESIGN = READY
```

Blocker identifié avant implémentation de la campagne :

```text
BLOCKER = FROZEN_LEVEL2_REFERENCE_ARTIFACTS_NOT_VERSIONED
```

Décision d'architecture : les artefacts Level2 existants doivent être gelés dans Git exactement tels qu'ils existent, sans recalcul, sans transformation et sans remplacement de provenance.

## Lot courant — L3-H

```text
LOT = L3-H-FREEZE-LEVEL2-REFERENCE-ARTIFACTS
STATUS = OPEN
TYPE = ARCHIVAL_IMPLEMENTATION

CODE_CHANGE_AUTHORIZED = YES
COMMIT_AUTHORIZED = YES
PUSH_AUTHORIZED = YES

LEVEL2_RECOMPUTATION_AUTHORIZED = NO
LEVEL2_ARTIFACT_CONTENT_MUTATION_AUTHORIZED = NO
REAL_S4_HAMILTONIAN_BUILD_AUTHORIZED = NO
REAL_S4_DIAGONALIZATION_AUTHORIZED = NO
S4_OBSERVABLES_AUTHORIZED = NO
LEVEL3_NORMATIVE_CAMPAIGN_AUTHORIZED = NO
```

Objectif : rendre durable et reproductible la référence scientifique Level2 utilisée par Level3 en intégrant dans Git les artefacts existants de :

```text
results/level2/level2-energy-regime-v1/
```

Le lot doit archiver les octets existants, pas régénérer la campagne.

Périmètre attendu :

```text
.gitignore
results/level2/level2-energy-regime-v1/manifest.json
results/level2/level2-energy-regime-v1/campaign-summary.json
results/level2/level2-energy-regime-v1/cases/triangle-S2.json
results/level2/level2-energy-regime-v1/cases/triangle-S3.json
results/level2/level2-energy-regime-v1/cases/ring4-S2.json
results/level2/level2-energy-regime-v1/cases/ring4-S3.json
results/level2/level2-energy-regime-v1/cases/ring5-S2.json
results/level2/level2-energy-regime-v1/cases/ring5-S3.json
```

Un petit document d'intégrité peut être ajouté sous `results/level2/level2-energy-regime-v1/` ou dans `docs/levels/level2/` s'il ne duplique aucune définition scientifique et contient uniquement les SHA-256 des artefacts gelés et leur identité de campagne.

## Invariants L3-H

```text
LEVEL2 = CLOSED
LEVEL2_CAMPAIGN_REEXECUTION = FORBIDDEN
LEVEL2_ARTIFACT_REGENERATION = FORBIDDEN
LEVEL2_ARTIFACT_CONTENT_CHANGE = FORBIDDEN
LEVEL2_ARTIFACTS = FROZEN_REFERENCE

REAL_S4_EXECUTION = FORBIDDEN
S5_EXECUTION = FORBIDDEN

PHYSICAL_MODEL_CHANGE = NO
NEW_METRIC = NO
NEW_THRESHOLD = NO
S_TO_INFINITY_CONVERGENCE = NOT_ESTABLISHED
```

Avant staging, Claude doit calculer les SHA-256 des artefacts locaux existants. Après staging/commit, il doit vérifier que les octets versionnés produisent exactement les mêmes SHA-256.

Toute différence entre l'artefact local préexistant et le contenu destiné au commit provoque STOP.

## Étape suivante

```text
NEXT_STEP = L3_H_FREEZE_LEVEL2_REFERENCE_ARTIFACTS
LEVEL3_CAMPAIGN_IMPLEMENTATION = BLOCKED_UNTIL_L3_H_ACCEPTED
REAL_S4_EXECUTION = FORBIDDEN
```

Après livraison L3-H, ChatGPT audite le commit distant et vérifie les artefacts versionnés. Lionel accepte ou non le lot. L'implémentation de campagne Level3 reste un lot séparé.

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
