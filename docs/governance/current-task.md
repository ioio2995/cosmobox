# Contrat de continuité — lot actif (anti-compactage)

Ce document est un contrat de reprise, pas une documentation scientifique. Il doit être relu intégralement (avec les documents qu'il référence) avant toute action de code, commit ou push si le contexte conversationnel a été compacté ou paraît incomplet.

## Dernier commit accepté

```text
b2cb6b1cd3c94e36e5da50063d095b95a1030015
```

Runner mono-cas (lot 1B-8, y compris son correctif) accepté à ce commit, sur `research/level1-correlators`.

## Lot actif

1B-8c — persistance atomique et reprise par cas.

**Rapport de conception validé. Implémentation autorisée.** Aucune campagne complète.

## Objectif

Ajouter la couche de persistance d'un résultat mono-cas déjà produit par `run_single_case` (lot 1B-8), sans modifier le calcul scientifique. Aucune campagne scientifique complète n'est lancée par ce lot.

Format obligatoire :

```text
runs/<case_id>/records.jsonl
runs/<case_id>/run.json
```

## Périmètre autorisé (fichiers)

- `docs/governance/current-task.md` (ce fichier).
- `scripts/level1b_campaign/outputs.py` (nouveau).
- `tests/scripts/level1b_campaign/test_outputs.py` (nouveau).
- Documents Level 1 directement concernés, mise à jour minimale.

`scripts/level1b_campaign/runner.py` n'est **pas** modifié par ce lot (confirmé au rapport de conception : `CaseExecutionResult` porte déjà tout ce dont la couche de persistance a besoin).

## Hors périmètre strict

Boucle multi-cas, lancement complet de la campagne, comparaisons inter-S, `gamma_O`, verdicts de robustesse, `G_occ`, `path_phase_coherence`. Ne pas modifier : `results.py`, `serialization.py`, `assembly.py`, les schémas, le manifeste, le niveau 0, `target_selection.py`, `local_observables.py`, `matching.py`, D020, D021, D022.

## records.jsonl

Contient exactement les documents v2 retournés par `run_single_case().documents`, un document JSON par ligne, dans l'ordre déterministe déjà fourni par `assemble_execution` — jamais réordonnés. Canonicalisation de chaque ligne : `json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`, terminée par `\n`.

`records_sha256` : SHA-256 sur les octets exacts du fichier `records.jsonl` final (retours à la ligne inclus). `record_count` : nombre exact de lignes/documents.

## run.json

Contient au minimum : `case_id`, `campaign_id`, `manifest_fingerprint`, `repository_commit`, `run_status`, `record_count`, `records_sha256`, `errors`.

Statuts finaux autorisés pour ce sous-lot : `success`, `resource_guardrail_exceeded`, `failed`. `running` n'existe que comme état interne/temporaire, jamais comme marqueur de complétion. `skipped_existing_valid` est un résultat de la logique de reprise, pas un statut stocké dans `run.json` — un `run.json` valide réutilisé n'est jamais réécrit.

## Ordre d'écriture (succès)

1. `records.jsonl` écrit dans un fichier temporaire du même répertoire/filesystem ;
2. flush ;
3. fsync ;
4. `os.replace()` vers `records.jsonl` ;
5. `run.json` temporaire ;
6. flush ;
7. fsync ;
8. `os.replace()` vers `run.json` (marqueur de complétion, toujours écrit en dernier).

Aucun fichier temporaire ou partiel n'est jamais considéré valide.

## Validation d'un run existant (reprise)

Réutilisable seulement si : `run.json` existe et est un JSON valide ; `run_status == "success"` ; `case_id`/`campaign_id`/`manifest_fingerprint`/`repository_commit` correspondent exactement ; `records.jsonl` existe, son SHA-256 correspond à `records_sha256`, son nombre de lignes correspond à `record_count` ; chaque ligne est un JSON objet valide passant `validate_document` et portant le même `campaign_id`/`manifest_fingerprint`/`repository_commit` ; l'assemblage de l'ensemble ne produit ni contradiction ni divergence de métadonnées, et l'ordre assemblé est identique à l'ordre du fichier. Au moindre échec : non réutilisable — jamais réparé silencieusement. Retourne `CaseRunValidation(is_valid, reason)`, jamais une exception, pour une simple invalidité de run réutilisable.

## API finalisée (décisions du rapport de conception validé)

`output_dir` désigne le parent de `runs/` : toute fonction construit elle-même `<output_dir>/runs/<case_id>/` ; l'appelant ne fournit jamais directement un chemin `runs/<case_id>` à une fonction d'écriture. `load_case_records(case_dir)` est la seule exception : elle reçoit le répertoire précis du cas.

`write_case_success(output_dir, result)` dérive `case_id`/`campaign_id`/`manifest_fingerprint`/`repository_commit` exclusivement de `result` (jamais des paramètres libres), et vérifie défensivement avant toute écriture : documents non vides, chacun valide (`validate_document`), métadonnées homogènes, `assemble_execution` réussit sans doublon et égal à `tuple(result.documents)`.

`write_case_failure(output_dir, case_id, *, campaign_id, manifest_fingerprint, repository_commit, run_status, errors)` : `run_status` ∈ {`failed`, `resource_guardrail_exceeded`} exclusivement, `errors: list[str]` non vide. **N'écrit jamais `records.jsonl`** — un échec n'a pas de résultats exploitables. Si un ancien `records.jsonl` existe (run antérieur), il est supprimé avant l'écriture du nouveau `run.json` d'échec, pour qu'il ne soit jamais pris à tort pour les résultats du nouveau run. `record_count=0`, `records_sha256=null`.

## Garde-fous

Seuls `max_dense_dimension = 2000` et `max_sparse_dimension = 200000` restent normatifs ; aucun nouveau seuil mémoire/temps inventé. `resource_guardrail_exceeded`/`failed` appartiennent à `run.json`, jamais à un `ResultRecord` synthétique.

## Règle « un mandat = un commit »

Toute la portée de ce lot est livrée en un seul commit, après validation explicite du rapport de conception. `results/` reste exclu de tout commit.

## Procédure en cas de compactage

Si le contexte conversationnel a été compacté ou paraît incomplet :

1. ne rien coder ;
2. ne rien commiter ;
3. ne rien pousser ;
4. relire ce fichier et les documents normatifs qu'il référence (`docs/decisions/decisions.md`, `docs/levels/level1/specification.md`, `docs/levels/level1/implementation-design.md`, `docs/levels/level1/validation-plan.md`, `docs/governance/collaboration-governance.md`) ;
5. produire une synthèse de reprise explicite (dernier commit accepté, lot actif, périmètre autorisé, ce qui reste à faire) ;
6. ne poursuivre que si toutes les contraintes ci-dessus sont retrouvées sans ambiguïté — sinon, signaler le blocage plutôt que d'inventer.
