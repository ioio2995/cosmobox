# Contrat de continuité — lot actif (anti-compactage)

Ce document est un contrat de reprise, pas une documentation scientifique. Il doit être relu intégralement (avec les documents qu'il référence) avant toute action de code, commit ou push si le contexte conversationnel a été compacté ou paraît incomplet.

## Lot outillage/performance CI-tests (parallèle, indépendant de la chaîne 1B)

Diagnostic de performance du workflow de test, aucune logique scientifique modifiée.

**Sous-lot 1 — CI/diagnostic, accepté au commit `8c7f92e41f375390e73c983fb39065dcf08b2b79`** : `on.push.branches` retiré de `research/**` — désormais `push`/`pull_request` limités à `main` uniquement, plus `workflow_dispatch: {}` pour un lancement manuel de la suite complète à tout moment ; `actions/setup-python` gagne `cache: "pip"`. Baseline mesurée : suite complète (1441 tests) = **293.56s** (real 4m56s), ~77 % du temps concentré dans `tests/scripts/level1b_campaign/test_runner.py`. Diagnostic : le vrai goulot n'était pas la diagonalisation/BLAS mais `serialization._validator()` non caché (reconstruit et re-valide le méta-schéma à chaque `validate_document`).

**Sous-lot 2 — PERF-VALIDATOR-CACHE, accepté** : `@lru_cache(maxsize=1)` ajouté à `serialization._validator()` (une ligne, même motif que `_load_schema()` juste au-dessus), confirmé sans effet de bord (`Draft202012Validator.iter_errors(instance)` ne stocke aucun état par document entre appels, vérifié dans le code de `jsonschema==4.26.0`). Résultat mesuré :

```text
run_single_case (triangle S1, profilé isolément) : ~123s → 0,54s (≈228×)
test_runner.py (57 tests)                        : ~231-293s → 12,81s (real 16,6s)  (≈14-18×)
suite complète (1449 tests, +8 tests de cache)    : 293,56s → 40,99s (real 44,69s)   (≈7,2×)
```

Nouveau profil de coût (`--durations=30` après correction) : plus aucun test dominant — le plus lent est `tests/test_symmetry_campaign.py::test_run_campaign_full_grid_all_succeed_and_no_truncated_group_failure` à 4,54s ; tout le reste est sous ~2s.

**xdist re-benchmarké sur le nouveau profil (suite complète, non capée)** : `-n2` = 170,48s (**4,2× plus lent** que série), `-n4` = 182,24s (encore pire). Arrêt des benchmarks à ce point (résultat sans ambiguïté). Explication : le coût dominant est désormais réparti sur des centaines de tests courts (≈28ms/test en moyenne) — la coordination inter-processus de xdist (IPC par test, démarrage des workers) domine largement tout gain de parallélisme possible sur un tel profil. **Recommandation finale : série, pas de xdist.** `pytest-xdist` reste installé dans le venv local pour le benchmark uniquement, jamais ajouté aux dépendances du projet.

**Stratégie FAST/SUBSYSTEM/FULL révisée** : FAST = fichier(s) directement concerné(s) (quasiment tout le dépôt tient maintenant sous quelques secondes) ; SUBSYSTEM = suite du sous-système + dépendances proches ; FULL = suite complète — **~41-45s en série, redevenue lançable localement à chaque itération**, plus de raison de la réserver à un jalon ou à la CI seule.

**État local volontaire de `.gitignore`** : modification de Lionel (ajout de `results/`), non liée à ce lot, non stagée, non commitée, laissée telle quelle.

**1B-9b** : accepté définitivement depuis, voir « Dernier commit accepté » et « Lot 1B-9b » ci-dessous.

## Dernier commit accepté

```text
994efe0ef19a18023a19697516f9ca66311adf65
```

Historique récent accepté, dans l'ordre (aucun réécrit, aucun rebase/cherry-pick) :

- `0ff65ac66b4aa054f739b350cd384c26ecd19752` — 1B-8g, première exécution normative Level1B. Verdict validé : `CAMPAGNE NORMATIVE 1B — EXÉCUTION VALIDÉE` (11/11 cas `success`, 11/11 `validate_existing_case_run(...).is_valid == True`, 8 286 `ResultRecord` v2). Les 11 runs mono-cas sous `/workspaces/level1b_campaign_output/runs/` sont **immuables** : aucun recalcul mono-cas, aucune réécriture.
- `3e4b393c8fa5dc4a2cb06353502b80593b060376` — livraison initiale du sous-lot 1B-9b (chargement, provenance, reconstruction de `SpectralGroupMatchKey`).
- `efb917f6eb6f3a12101526ba93a734044c097741` — premier correctif d'immutabilité de 1B-9b (gel profond `_freeze`/`_freeze_document`, accepté sur le fond, avec un défaut résiduel borné corrigé ci-dessous).
- `8c7f92e41f375390e73c983fb39065dcf08b2b79` — lot CI/performance, **accepté**, indépendant de la chaîne 1B (voir section dédiée ci-dessus).
- `f67642b542be964febcffee31b51f5678f2d2a77` — PERF-VALIDATOR-CACHE, **accepté**, indépendant de la chaîne 1B (voir section dédiée ci-dessus).
- `540b08096b7d67278a6f2eea8ce93dbf039887fe` — second correctif d'immutabilité de 1B-9b (`_is_deeply_frozen`, validation récursive de la forme gelée), **accepté**. **1B-9b est désormais accepté définitivement dans son ensemble** (livraison initiale + les deux correctifs).
- `89fbfc27dc57469bcb9cbf818b9b6a4f405630ad` — livraison candidate 1B-9c (matching inter-S), conforme sur le matching lui-même mais acceptation initialement suspendue : défaut principal (`low_window_truncated` incorrect sur le chemin sparse) et durcissement secondaire (sélection des deux plus grands spins non garantie distincte).
- `e4cc72598f0b334a41220d1873f539cd0210c8f6` — correctif 1B-9c (les deux points ci-dessus). **1B-9c est désormais accepté définitivement dans son ensemble** (`89fbfc27...` + `e4cc725...`). Résultat structurel accepté sur la campagne normative : 3 couples inter-S (`triangle`/`ring4`/`ring5` reference S3→S2), 7 groupes high analysés, 7 `exact_label_match`.
- `7ef4669b92f1986a507313c5ef5a62e6dddfe839` — livraison candidate 1B-9d (extraction/comparaison des observables inter-S), conforme sur l'extraction/comparaison elle-même mais acceptation initialement suspendue pour deux défauts de contrat strictement bornés.
- `994efe0ef19a18023a19697516f9ca66311adf65` — correctif 1B-9d (exigence `normalization == "raw_G"` pour `flavor_singular_value_ratio` ; durcissement des constructeurs publics). **1B-9d est désormais accepté définitivement dans son ensemble** (`7ef4669...` + `994efe0...`). Résultat accepté sur la campagne normative : 712 comparaisons inter-S — `O_ij_raw` 416 (252 `gamma_O` null), `rho_QQ` 96 (28 null high, 28 null low), `C_TT_conn` 96 (0 null), `flavor_singular_value_ratio` 104.

1B-9a — conception de la couche d'analyse inter-S sur artefacts normatifs — **conception acceptée, y compris son addendum**, aucun code livré par ce lot (design uniquement). Décisions gelées pour l'implémentation, reprises et mises en œuvre par 1B-9c/1B-9d/1B-9e ci-dessous :

- exactement 3 couples inter-S potentiels dans cette campagne : `triangle` reference S3→S2, `ring4` reference S3→S2, `ring5` reference S3→S2 (les cas `j_break` de `triangle`/`ring5`, à un seul point S, n'ont aucune comparaison admissible) ;
- unité scientifique inter-S = **groupe spectral sérialisé** (déduplicé par `spectral_window_group_index`), jamais `target_id` — jamais reconstruit ni inventé ;
- `spectral_window_group_index`/`representative_energy` : identité intra-cas uniquement, jamais dans un `SpectralGroupMatchKey`, jamais critère de matching inter-S (D022) ;
- `twice_T is None` : bloqué dès la construction de `CampaignArtifactIndex` (1B-9b) — 1B-9c peut considérer cet invariant garanti, aucun nouveau statut de matching pour ce cas ;
- aucun changement de `matching.py`/`robustness.py` dans aucun lot 1B-9 tant que non explicitement autorisé ;
- `flavor_singular_value_ratio` est path-dependent (chemin minimal complet requis, pas seulement `(i,j)`) ;
- `flavor_singlet` n'est pas éligible à un verdict de robustesse (liste fermée `ROBUSTNESS_OBSERVABLE_KINDS`).

## Lot 1B-9b (accepté définitivement au commit `540b08096b7d67278a6f2eea8ce93dbf039887fe`)

Chargement validé et index immuable des artefacts mono-cas. Aucun matching inter-S, aucun `gamma_O`, aucun verdict de robustesse. Charge le manifeste, reconstruit `build_campaign_plan(manifest)`, valide les runs existants (`validate_existing_case_run`, inchangée), charge leurs documents v2 (`load_case_records`, inchangée), vérifie leur provenance croisée, regroupe les records par groupe spectral intra-cas (`spectral_window_group_index`), reconstruit exactement un `SpectralGroupMatchKey` par groupe, et fournit un index immuable (`CampaignArtifactIndex`).

**Historique de ce sous-lot** : livraison initiale `3e4b393c8fa5dc4a2cb06353502b80593b060376` → premier correctif d'immutabilité `efb917f6eb6f3a12101526ba93a734044c097741` (gel profond `_freeze`/`_freeze_document` accepté sur le fond, mais `LoadedCase`/`IndexedSpectralGroup` ne vérifiaient que le type du document RACINE, `types.MappingProxyType`, sans prouver que son contenu imbriqué était lui-même gelé) → second correctif de validation récursive `540b08096b7d67278a6f2eea8ce93dbf039887fe` : `loader._is_deeply_frozen(value)` ajoutée comme primitive récursive unique, partagée par `loader.LoadedCase` et `indexing.IndexedSpectralGroup` (import direct, aucune duplication de logique) — accepte uniquement, récursivement : `types.MappingProxyType` (toutes les clés `str`, toutes les valeurs elles-mêmes conformes), `tuple` (tous les éléments conformes), ou un scalaire JSON (`str`/`int`/`float`/`bool`/`None`). Un document forgé partiellement gelé est **rejeté à la construction**, jamais re-gelé silencieusement.

Fichiers de ce lot : `scripts/level1b_analysis/loader.py` (`LoadedCase`, `CampaignLoadError`, `FrozenDocument`, `_is_deeply_frozen`, `load_validated_cases`), `scripts/level1b_analysis/indexing.py` (`IndexedSpectralGroup`, `CampaignArtifactIndex`, `SpectralGroupIndexError`, `UnresolvedFlavorLabelError`, `build_campaign_artifact_index`), `tests/scripts/level1b_analysis/test_loader_and_indexing.py`.

## Lot 1B-9c (accepté définitivement, `89fbfc27dc57469bcb9cbf818b9b6a4f405630ad` + `e4cc72598f0b334a41220d1873f539cd0210c8f6`)

Matching inter-S sur index normatif. Prend le `CampaignArtifactIndex` accepté (1B-9b) et produit uniquement les appariements spectraux inter-S admissibles via la primitive scientifique existante `match_spectral_group` (`src/cosmobox/level1/matching.py`, inchangée). Aucun `gamma_O`, aucun verdict de robustesse, aucune comparaison `rho_QQ`/`C_TT_conn`/`flavor_singular_value_ratio` dans ce lot.

**Construction des couples** : deux `CampaignCaseSpec` forment un couple admissible ssi même `geometry`, même `hamiltonian_identity_without_spin` (réutilise `indexing._case_hamiltonian_identity_tuple`, jamais dupliqué), même `sector_id`. Les cas sont regroupés par leur propre `spin` ; seules les deux plus grandes valeurs de `spin` DISTINCTES sont retenues comme `(S_high, S_low)`. Une identité avec moins de deux spins distincts ne produit aucun couple (pas d'erreur). Sépare naturellement `reference`/`j_break` sans filtrage par nom. Si plusieurs `CampaignCaseSpec` partagent la même identité physique ET le même spin retenu, `_build_case_pairs` lève `InterSMatchingError` plutôt que de choisir arbitrairement (jamais observé dans la campagne actuelle).

**`structurally_applicable`** : toujours `True` — la construction du couple garantit déjà même geometry/hamiltonian identity/sector.

**`low_window_truncated`** : reconstruit depuis `CampaignCaseSpec`/`SpectrumOptions` du cas low en reproduisant uniquement la logique de COMPTAGE déjà figée par `cosmobox.level0.reports._compute_spectrum` (`_reconstruct_computed_eigenvalue_count`), jamais une diagonalisation : `dimension == 0` et le cas non calculable selon les guardrails lèvent `InterSMatchingError` ; `dimension == 1` → toujours 1 eigenvalue ; dense → `min(spectral_window, dimension)` ; sparse → `min(spectral_window, dimension - 1)` (donc toujours tronqué dès `dimension >= 2`, quel que soit `spectral_window` — correction du premier candidat, qui utilisait à tort `spectral_window < physical_dimension` sans distinguer dense/sparse).

**Résolution `MatchOutcome.matched_group` → `IndexedSpectralGroup` low concret** : exige exactement un groupe low dont `match_key == outcome.matched_group` ; 0 ou >1 → `InterSMatchingError`.

Fichiers de ce lot : `scripts/level1b_analysis/inter_s.py` (`InterSGroupMatch`, `InterSMatchingReport`, `InterSMatchingError`, `build_inter_s_matching_report`), `tests/scripts/level1b_analysis/test_inter_s.py`.

**Résultat structurel accepté sur la campagne normative** : 3 couples inter-S (`triangle`/`ring4`/`ring5` reference S3→S2), 7 groupes high analysés, 7 `exact_label_match` (2/2/3 groupes respectivement).

## Lot 1B-9d (accepté définitivement, `7ef4669b92f1986a507313c5ef5a62e6dddfe839` + `994efe0ef19a18023a19697516f9ca66311adf65`)

Extraction et comparaison des observables inter-S. Sélectionne les documents high/low réellement comparables pour la liste FERMÉE `O_ij_raw`/`rho_QQ`/`C_TT_conn`/`flavor_singular_value_ratio`, calcule `gamma_O` (uniquement pour `O_ij_raw`, via `cosmobox.level1.robustness.compute_gamma_o` — inchangée, jamais recodée), expose les paires numériques brutes des trois autres. Aucun verdict de robustesse dans ce lot.

**Désambiguïsation `record_kind` pour `O_ij_raw`** : `observable_kind == "O_ij_raw"` est produit sous TROIS `record_kind` différents partageant le même `identity.path`/`flavor_component` (`raw_observable`, `orbit_statistic`, `restricted_diagnostic`) — `record_kind` est toujours fixé en plus de `observable_kind` (dérivé des tables closes de `results.py`) avant toute recherche de correspondance. `C_TT_conn` est un `record_kind="raw_observable"` à payload `float` nu, jamais `NormalizedMoment` (écart constaté au mandat initial, corrigé sans blocage).

**Comparabilité (1B-9a, gelée)** : `identity.path` (tuple complet), `identity.flavor_component`, `identity.normalization` — tous exactement égaux, dans le contexte du groupe spectral déjà apparié. Pour `flavor_singular_value_ratio` spécifiquement, `identity.normalization` doit en outre valoir exactement `"raw_G"` des DEUX côtés (pas seulement leur égalité mutuelle) — un artefact `None`/`None` ou toute autre chaîne identique invalide est rejeté (`InterSObservableComparisonError`).

**Cardinalité** : document low dupliqué à la même clé → erreur ; document high éligible sans exactement un low correspondant → erreur ; document low sans high correspondant → jamais visité, jamais une erreur.

**API** : `GammaOComparison` (`O_ij_raw` : `high_value`/`low_value` complexes toujours présents et finis, `gamma_o: NormalizedMoment` jamais `None`) et `ScalarObservableComparison` (les 3 autres : `high_value`/`low_value: float | None` finis si non-null, `high_null_reason`/`low_null_reason`, aucun champ `gamma_o`) — constructeurs publics durcis : `InterSObservableComparisonReport.comparisons` doit être réellement un `tuple` d'éléments du bon type ; `ScalarObservableComparison` rejette `str`/`bool`/`NaN`/`±Inf` pour une valeur non-null et exige, pour `C_TT_conn` spécifiquement, `high_value`/`low_value` toujours non-`None` et `null_reason` toujours `None`.

**Ordre** : celui de `InterSMatchingReport.matches`, puis l'ordre canonique exact de `high_group.documents` (assembly.py) au sein d'un couple.

Fichiers de ce lot : `scripts/level1b_analysis/comparisons.py` (`GammaOComparison`, `ScalarObservableComparison`, `InterSObservableComparisonReport`, `InterSObservableComparisonError`, `build_inter_s_observable_comparison_report`), `tests/scripts/level1b_analysis/test_comparisons.py`.

**Résultat accepté sur la campagne normative** : 712 comparaisons — `O_ij_raw` 416 (252 `gamma_O` null par floor), `rho_QQ` 96 (28 null high, 28 null low), `C_TT_conn` 96 (0 null), `flavor_singular_value_ratio` 104.

## Lot actif

1B-9e — application des verdicts de robustesse aux comparaisons inter-S.

Objectif exact : à partir de `InterSMatchingReport` + `InterSObservableComparisonReport` acceptés, associer chaque comparaison à son `InterSGroupMatch` source exact, puis appeler STRICTEMENT `cosmobox.level1.robustness.evaluate_robustness(...)` pour chaque comparaison disposant de deux valeurs numériques, en conservant intégralement le `RobustnessResult` produit. Aucune formule, aucun seuil, aucun `null_reason` de robustesse n'est recodé — toute cette logique reste exclusivement dans `evaluate_robustness`.

**Audit préalable des nulls réels (lecture seule, avant implémentation)** : sur la campagne normative acceptée, les trois observables scalaires ne présentent jamais de null asymétrique (un côté null, l'autre numérique) — uniquement « les deux numériques » ou « les deux null » : `rho_QQ` 90 both-numeric / 6 both-null (`zero_local_charge_variance`/`zero_local_charge_variance`) ; `flavor_singular_value_ratio` 82 both-numeric / 22 both-null (`normalization_denominator_below_floor`/`normalization_denominator_below_floor`) ; `C_TT_conn` 96/96 numérique (0 null), conforme à son contrat 1B-9d. Aucun cas incompatible avec le contrat ci-dessous — aucune décision scientifique supplémentaire nécessaire, implémentation poursuivie sans blocage.

**`GammaOComparison`** : `high_value`/`low_value` toujours présents → `evaluate_robustness(match.outcome, comparison.high_value, comparison.low_value)` appelé systématiquement. `comparison.gamma_o.value is None` (floor) n'empêche JAMAIS un verdict définitif : `gamma_o` null et verdict `robust`/`non_robust` sont deux faits indépendants produits par le même appel — jamais fusionnés en `indeterminate`. Vérification de cohérence : `result.gamma_o == comparison.gamma_o` (une divergence est une erreur structurelle).

**Comparaisons scalaires (`rho_QQ`/`C_TT_conn`/`flavor_singular_value_ratio`)** : si `high_value is not None and low_value is not None` → `evaluate_robustness(match.outcome, complex(high_value), complex(low_value))`. Sinon (au moins un côté `None`) → **aucun appel**, **aucun `RobustnessResult` fabriqué**, **aucune nouvelle `null_reason` scientifique inventée** (`source_value_null` et assimilés sont formellement interdits) — la comparaison est conservée telle quelle dans `unevaluable_comparisons`, son propre `high_null_reason`/`low_null_reason` restant l'unique explication.

**Association comparaison → `InterSGroupMatch`** : aucun nouveau matching, aucun rappel à `match_spectral_group`. Le match source exact est retrouvé par identité d'objet (`id()`) sur `(high_case_id, low_case_id, high_group, low_group)` — jamais par égalité de dataclass (`IndexedSpectralGroup`/`CampaignCaseSpec` portent des `numpy.ndarray` non hashables dont `==` renvoie un tableau, pas un booléen) — jamais par énergie/index/ordre/proximité. 0 ou >1 match trouvé → `InterSRobustnessError`.

**`match.outcome`** transmis tel quel à `evaluate_robustness` ; un groupe `partial_subspace` produit exactement `verdict=indeterminate, null_reason="truncated_spectral_group"` (jamais réécrit). Aucun groupe `partial_subspace` dans la campagne actuelle.

**API** : `InterSRobustnessEvaluation(comparison, match, observable_kind, result: RobustnessResult)` — invariants : types attendus, `case_id`/`high_group`/`low_group` cohérents avec `match` (identité d'objet), `observable_kind` cohérent (`"gamma_O"` pour `GammaOComparison`, `comparison.observable_kind` sinon, toujours dans la liste fermée), `result.gamma_o == comparison.gamma_o` pour `GammaOComparison`, refuse une `ScalarObservableComparison` à valeur null. `InterSRobustnessReport(campaign_id, manifest_fingerprint, repository_commit, evaluations, unevaluable_comparisons)` — provenance exigée identique entre `matching_report` et `comparison_report` avant toute évaluation (sinon erreur) ; les deux tuples réellement des `tuple`, aucun élément de type inattendu, aucun chevauchement entre les deux ; ordre relatif de chaque tuple dérivé uniquement de `comparison_report.comparisons`. `RobustnessResult` existant reste l'unique source de vérité — aucune dataclass parallèle ne recopie `verdict`/`difference`/`amplitude`/`gamma_o`/`null_reason`.

**Interdictions strictes de ce lot** : aucune modification de `src/cosmobox/level1/{matching,robustness,results,serialization}.py`, `scripts/level1b_campaign/*`, `experiments/level1/*`, `schemas/*`, `.github/workflows/*` ; aucun `run_single_case`/`run_campaign`/`launch_normative_campaign`/`run_level1b_campaign` ; aucune diagonalisation ; aucun nouveau seuil/formule/`null_reason` scientifique ; aucun fichier écrit sous `/workspaces/level1b_campaign_output` ni ailleurs.

Fichiers de ce lot : `scripts/level1b_analysis/robustness_evaluation.py` (`InterSRobustnessEvaluation`, `InterSRobustnessReport`, `InterSRobustnessError`, `build_inter_s_robustness_report`), `scripts/level1b_analysis/__init__.py` (docstring, ajustement mineur), `tests/scripts/level1b_analysis/test_robustness_evaluation.py`.

**Smoke-test réel mesuré** (`/workspaces/level1b_campaign_output`, lecture seule, non hardcodé) : 712 comparaisons source → 684 évaluées, 28 non évaluables (source null : 6 `rho_QQ` + 0 `C_TT_conn` + 22 `flavor_singular_value_ratio`). Par observable évalué : `gamma_O` 416, `rho_QQ` 90, `C_TT_conn` 96, `flavor_singular_value_ratio` 82. Par verdict : 684 `robust`, 0 `non_robust`, 0 `indeterminate` (aucun `null_reason` de `RobustnessResult`). `gamma_O` null parmi les évaluations : 252, réparties `{robust: 252}` — confirmant que le floor n'empêche jamais un verdict définitif. 0 groupe `partial_subspace` évalué. Statistiques (684 évaluations) : `difference` min=0 max≈0,00436 médiane≈5,66e-15 ; `amplitude` min≈9,77e-19 max=1 médiane≈0,0859 ; `gamma_O` non-null (432 valeurs) min=0 max≈0,281 médiane≈0,00672. Ceci est un relevé technique de valeurs, aucune conclusion physique.

**Aucune fonctionnalité 1B-9f n'est autorisée** — ce lot ferme l'application des verdicts de robustesse aux comparaisons déjà construites.

**État local de `.gitignore`** : modification volontaire de Lionel (ajout de `results/` aux chemins ignorés), hors périmètre de ce lot — laissée telle quelle, non stagée, non commitée.

## Référence : lanceur normatif 1B-8e (accepté, non modifié depuis)

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
