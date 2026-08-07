# Contrat de continuité — lot actif (anti-compactage)

Ce document est un contrat de reprise, pas une documentation scientifique. Il doit être relu intégralement (avec les documents qu'il référence) avant toute action de code, commit ou push si le contexte conversationnel a été compacté ou paraît incomplet.

## Dernier commit accepté

```text
514181cab2a2f9c4f0e28cec63b7ad75832a31d6
```

Persistance atomique et reprise par cas (lot 1B-8c) acceptée à ce commit, sur `research/level1-correlators`.

## Lot actif

1B-8d — orchestration multi-cas avec reprise.

**Rapport de conception validé. Implémentation autorisée.** Aucune campagne scientifique réelle ou complète n'est lancée par ce lot.

## Objectif

Construire l'orchestrateur qui exécute le plan déterministe complet du manifeste (`experiments.level1.planning.build_campaign_plan`), cas par cas, dans l'ordre exact du plan, en réutilisant exclusivement `validate_existing_case_run`/`run_single_case`/`write_case_success`/`write_case_failure` (inchangés). Les erreurs isolées d'un cas sont enregistrées via `write_case_failure` sans interrompre les autres cas, sauf `KeyboardInterrupt`/`SystemExit` (jamais avalés) et un échec de `write_case_failure` lui-même (propagé, jamais avalé). Aucune agrégation inter-S dans ce lot.

## Signal de garde-fou (point essentiel du rapport de conception)

Level0 ne lève jamais d'exception pour un dépassement de dimension : `SpectrumReport.status == "not_computed"` est son signal typé, exclusif, mais `run_single_case` (inchangé) ne le vérifie pas avant de déréférencer `.degeneracy.groups`. L'orchestrateur ne s'appuie donc jamais sur une exception Level0 ni sur un texte de message : il pré-vérifie, avant tout appel à `run_single_case`, `case.physical_dimension > case.spectrum_options.max_sparse_dimension` (uniquement si `case.spectrum_options.force is False`, seule valeur produite par `planning.py`). `max_dense_dimension` ne sélectionne que dense vs sparse, ce n'est jamais un seuil d'échec.

## Périmètre autorisé (fichiers)

- `docs/governance/current-task.md` (ce fichier).
- `scripts/level1b_campaign/campaign.py` (nouveau).
- `tests/scripts/level1b_campaign/test_campaign.py` (nouveau).
- Documents Level 1 directement concernés, mise à jour minimale, uniquement si nécessaire.

Ne modifie pas : `runner.py`, `outputs.py`, `planning.py`, le manifeste, `results.py`, `serialization.py`, `assembly.py`, les schémas, `target_selection.py`, `local_observables.py`, `matching.py`, le niveau 0, D020/D021/D022.

## Hors périmètre strict

Comparaisons inter-S, `gamma_O`, verdicts de robustesse, `G_occ`, `path_phase_coherence`, agrégation scientifique entre cas, lecture de payload physique pour comparer des cas. Aucun fichier global de campagne (`campaign.json`, résumé/index global) : `CampaignExecutionReport` reste un objet Python en mémoire pour ce lot.

## API de l'orchestrateur (campaign.py)

`CASE_ORCHESTRATION_STATUSES = ("success", "skipped_existing_valid", "resource_guardrail_exceeded", "failed")`. `CaseOrchestrationOutcome(case_id, status, errors)` et `CampaignExecutionReport(case_outcomes, total_required, executed_success_count, reused_success_count, resource_guardrail_exceeded_count, failed_count, global_success)`, tous deux `frozen`/auto-vérifiants. `run_campaign(manifest, *, output_dir, repository_commit) -> CampaignExecutionReport` : construit `build_campaign_plan(manifest)` exactement une fois, aucun tri supplémentaire, aucune liste libre de cas acceptée ; `repository_commit` non vide obligatoire ; `global_success` vrai ssi tous les statuts sont `success`/`skipped_existing_valid`.

`check_repository_cleanliness(repo_root) -> tuple[bool, tuple[str, ...]]` : fonction séparée, lecture seule (`git status --porcelain`), jamais appelée automatiquement par `run_campaign`, jamais de paramètre de contournement. Une future entrée de lancement scientifique normatif DOIT l'appeler et refuser de lancer si `is_clean` est faux. Le répertoire racine `results/` reste hors filtre.

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
