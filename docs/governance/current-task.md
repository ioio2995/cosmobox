# Contrat de continuité — lot actif (anti-compactage)

Ce document est un contrat de reprise, pas une documentation scientifique. Il doit être relu intégralement (avec les documents qu'il référence) avant toute action de code, commit ou push si le contexte conversationnel a été compacté ou paraît incomplet.

## Dernier commit accepté

```text
4f04e62a5e0af5f2316071c066daa5d2220c61a9
```

1B-8e — point d'entrée de lancement normatif (design + implémentation + correctif de normalisation des erreurs de précondition) accepté à ce commit, sur `research/level1-correlators`.

## Lot actif

1B-8f — préflight réel avant première campagne normative.

**Inspection opérationnelle uniquement.** Aucun code scientifique nouveau, aucune modification de formule, aucune exécution de `run_campaign`/`launch_normative_campaign`/`run_single_case`, aucune diagonalisation, aucun `records.jsonl`/`run.json` créé. Le seul changement de fichier autorisé pour ce lot est cette mise à jour de `current-task.md` elle-même, si un commit de préflight s'avère nécessaire.

Objectif : produire, sur le dépôt réel au commit accepté, le constat exact (état Git, manifeste chargé, plan de campagne complet, vérifications structurelles, proposition de répertoire de sortie externe non créé, estimation purement opérationnelle) qui permettra d'autoriser ou non le premier lancement scientifique réel dans un lot ultérieur. Verdict rendu séparément dans le rapport de préflight livré à l'utilisateur — pas dans ce document.

## Référence : lanceur normatif 1B-8e (accepté, non modifié par 1B-8f)

Entrée de lancement explicite (`prepare_normative_launch`/`launch_normative_campaign` dans `scripts/level1b_campaign/launch.py`, plus une CLI mince `scripts/run_level1b_campaign.py`) qui vérifie toutes les préconditions normatives de la campagne puis appelle `run_campaign` (lot 1B-8d, inchangé) exactement comme celui-ci est déjà défini. Aucune logique scientifique nouvelle ; aucune reconstruction du plan (`run_campaign` construit déjà `build_campaign_plan(manifest)` exactement une fois).

## Préconditions et TOCTOU

`repository_commit` n'est jamais un paramètre libre : il est dérivé exclusivement via `git rev-parse HEAD` depuis `repo_root` (40 hex minuscules exigés, jamais un SHA court). La branche attendue n'est jamais une constante codée dans `launch.py` : elle est comparée à `manifest.branch` (déjà `"research/level1-correlators"` dans le manifeste normatif actuel). Le manifeste est chargé exclusivement via `load_manifest()` sans argument — aucun `manifest_path` n'est jamais exposé. `check_repository_cleanliness` (campaign.py, inchangée sauf export public de sa liste de chemins) est réutilisée telle quelle, jamais réimplémentée.

`launch_normative_campaign` effectue une SECONDE vérification (HEAD, branche, propreté) immédiatement avant `run_campaign`, après le premier passage complet de `prepare_normative_launch` — mitigation explicite et documentée honnêtement comme non atomique (aucun verrou Git introduit) : une fenêtre résiduelle subsiste entre cette seconde vérification et le premier appel interne de `run_campaign`. Le `repository_commit` transmis à `run_campaign` est exactement celui de cette seconde vérification.

Toute erreur de précondition lève `NormativeLaunchError` (avec `dirty_paths` peuplé uniquement pour une erreur de propreté) **avant** tout appel à `run_campaign` — aucun `run.json` de cas n'est jamais créé pour ce type d'échec. Ceci inclut les erreurs des primitives de précondition elles-mêmes : `load_manifest()` (via le helper privé `_load_normative_manifest`) et `check_repository_cleanliness()` (via `_check_repository_cleanliness_or_fail`, aux deux points d'appel — premier et second contrôle TOCTOU) normalisent toute exception sous-jacente en `NormativeLaunchError` (`raise ... from exc`, cause préservée dans `__cause__`), avec `dirty_paths=()` quand aucune liste fiable de chemins sales n'a pu être obtenue. `_resolve_head_sha`/`_current_branch` faisaient déjà cette normalisation depuis la livraison initiale. Cette normalisation reste strictement bornée aux appels de précondition : `launch_normative_campaign` n'enveloppe jamais `run_campaign` dans un `except Exception` — une exception levée par `run_campaign` reste son propre comportement, jamais requalifiée en échec de précondition.

## Périmètre autorisé (fichiers)

- `docs/governance/current-task.md` (ce fichier).
- `scripts/level1b_campaign/launch.py` (nouveau).
- `tests/scripts/level1b_campaign/test_launch.py` (nouveau).
- `scripts/run_level1b_campaign.py` (nouveau, CLI mince).
- `scripts/level1b_campaign/campaign.py` : adaptation minimale unique (export public de `NORMATIVE_REPOSITORY_PATHS`, remplaçant l'ancienne constante privée `_CLEANLINESS_PATHS`, utilisée à la fois par `check_repository_cleanliness` et par `launch.py`).
- Documents Level 1 directement concernés, mise à jour minimale, uniquement si nécessaire.

Ne modifie pas : `runner.py`, `outputs.py`, `planning.py`, le manifeste, `results.py`, `serialization.py`, `assembly.py`, les schémas, `target_selection.py`, `local_observables.py`, `matching.py`, le niveau 0, D020/D021/D022. `run_campaign` lui-même (logique interne) n'est pas modifié.

## Hors périmètre strict

Comparaisons inter-S, `gamma_O`, verdicts de robustesse, `G_occ`, `path_phase_coherence`, agrégation scientifique entre cas, lecture de payload physique pour comparer des cas. Aucun fichier global de campagne (`campaign.json`, résumé/index global) : `CampaignExecutionReport` reste un objet Python en mémoire.

## API de l'orchestrateur (campaign.py, inchangée depuis 1B-8d/correctif)

`CASE_ORCHESTRATION_STATUSES = ("success", "skipped_existing_valid", "resource_guardrail_exceeded", "failed")`. `CaseOrchestrationOutcome(case_id, status, errors)` et `CampaignExecutionReport(case_outcomes, total_required, executed_success_count, reused_success_count, resource_guardrail_exceeded_count, failed_count, global_success)`, tous deux `frozen`/auto-vérifiants. `run_campaign(manifest, *, output_dir, repository_commit) -> CampaignExecutionReport` : construit `build_campaign_plan(manifest)` exactement une fois, aucun tri supplémentaire, aucune liste libre de cas acceptée ; `repository_commit` non vide obligatoire ; `global_success` vrai ssi tous les statuts sont `success`/`skipped_existing_valid`. Un cas `spectrum_options.force is not False` est rejeté avant tout contrôle de garde-fou, comme `failed` ordinaire, jamais `resource_guardrail_exceeded`.

`check_repository_cleanliness(repo_root) -> tuple[bool, tuple[str, ...]]` : fonction séparée, lecture seule (`git status --porcelain`), jamais appelée automatiquement par `run_campaign`, jamais de paramètre de contournement. Utilise désormais `NORMATIVE_REPOSITORY_PATHS` (publique) — seule source de vérité, réutilisée par `launch.py` pour les restrictions de sortie. Une entrée de renommage (`old -> new`) est non propre si le chemin source OU le chemin destination commence par un préfixe normatif. Le répertoire racine `results/` reste hors filtre.

## API du lanceur normatif (launch.py, nouveau)

`NormativeLaunchError(RuntimeError)` avec `dirty_paths: tuple[str, ...]` (vide sauf erreur de propreté). `NormativeLaunchContext(repository_commit, branch, manifest, output_dir)` — `frozen`, invariants auto-vérifiés (SHA 40 hex, branche non vide et != `"HEAD"`, `branch == manifest.branch`, `output_dir` absolu/résolu) ; ne duplique jamais `campaign_id`/`fingerprint` (accessibles via `context.manifest.campaign_id`/`context.manifest.fingerprint`). `prepare_normative_launch(repo_root, *, output_dir) -> NormativeLaunchContext` : vérifie tout une fois, n'appelle jamais `run_campaign`. `launch_normative_campaign(repo_root, *, output_dir) -> CampaignExecutionReport` : `prepare_normative_launch` puis seconde vérification HEAD/branche/propreté, puis `run_campaign`. `output_dir` relatif est résolu par rapport à `repo_root`, jamais au cwd implicite ; rejette `repo_root` lui-même, `repo_root/results`, et tout chemin sous `NORMATIVE_REPOSITORY_PATHS`.

`scripts/run_level1b_campaign.py` : CLI mince (`--output-dir` obligatoire, `--repo-root` optionnel, défaut dérivé de l'emplacement du script) — aucune logique normative hors `launch.py`, aucun paramètre `repository_commit`/`manifest_path`/`branch`/`force`/contournement de propreté. Codes de sortie : `0` succès global, `1` campagne exécutée mais `global_success=False`, `2` `NormativeLaunchError`.

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
