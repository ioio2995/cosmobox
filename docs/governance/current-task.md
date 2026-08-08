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
a6450e994b7b1ce5c8d7d1fec876128a2a9622e9
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
- `77899f123bae83d687e38053870de0b7202bb057` — 1B-9e (application des verdicts de robustesse existants), **accepté définitivement** (mandat 1B-9f : « Les lots suivants sont considérés comme acceptés... 1B-9e »). Résultat accepté sur la campagne normative : 684 évaluations (`gamma_O` 416, `rho_QQ` 90, `C_TT_conn` 96, `flavor_singular_value_ratio` 82), 28 non évaluables (source null), 684 `robust`/0 `non_robust`/0 `indeterminate`, 252 `gamma_O` null tous verdict `robust`.
- `8a14a040f569d4eb85de9572b7d23bb587737549` — livraison candidate 1B-9f (synthèse déterministe des résultats inter-S), conforme sur la synthèse statistique elle-même mais acceptation initialement suspendue : les groupes/couples étaient découverts depuis `comparison_report.comparisons` au lieu de `matching_report.matches`, faisant disparaître silencieusement de `groups`/`couples` tout `exact_label_match` sans comparaison 1B-9d.
- `a6450e994b7b1ce5c8d7d1fec876128a2a9622e9` — correctif structurel 1B-9f (source `groups`/`couples` depuis `matching_report.matches`, plus l'invariant `len(groups) == exact_match_count`). **1B-9f est désormais accepté définitivement dans son ensemble** (`8a14a040...` + `a6450e99...`). Résultat accepté sur la campagne normative : 7 groupes appariés (7 `exact_label_match`), 712 comparaisons source → 684 évaluées / 28 non évaluables, 684 `robust`/0 `non_robust`/0 `indeterminate` (global, par couple, par groupe, par observable). Voir « Lot 1B-9f » ci-dessous.

**Le pointeur ci-dessus (`a6450e994b7b1ce5c8d7d1fec876128a2a9622e9`) reste le dernier commit formellement accepté.**

1B-9a — conception de la couche d'analyse inter-S sur artefacts normatifs — **conception acceptée, y compris son addendum**, aucun code livré par ce lot (design uniquement). Décisions gelées pour l'implémentation, reprises et mises en œuvre par 1B-9c/1B-9d/1B-9e/1B-9f ci-dessous :

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

## Lot 1B-9e (accepté définitivement, `77899f123bae83d687e38053870de0b7202bb057`)

Application des verdicts de robustesse aux comparaisons inter-S. Associe chaque comparaison à son `InterSGroupMatch` source exact, puis appelle STRICTEMENT `cosmobox.level1.robustness.evaluate_robustness(...)` pour chaque comparaison disposant de deux valeurs numériques, en conservant intégralement le `RobustnessResult` produit. Aucune formule, aucun seuil, aucun `null_reason` de robustesse recodé.

**Audit préalable des nulls réels** : les trois observables scalaires ne présentent jamais de null asymétrique — uniquement « les deux numériques » ou « les deux null » : `rho_QQ` 90/6, `flavor_singular_value_ratio` 82/22, `C_TT_conn` 96/0. Aucune décision scientifique supplémentaire nécessaire.

**`GammaOComparison`** : `evaluate_robustness` appelé systématiquement (`high_value`/`low_value` toujours présents). `comparison.gamma_o.value is None` (floor) n'empêche JAMAIS un verdict définitif — `gamma_o` null et verdict `robust`/`non_robust` sont deux faits indépendants du même appel, jamais fusionnés en `indeterminate`. Vérification de cohérence : `result.gamma_o == comparison.gamma_o`.

**Comparaisons scalaires** : `evaluate_robustness` appelé seulement si `high_value is not None and low_value is not None`. Sinon : aucun appel, aucun `RobustnessResult` fabriqué, aucune nouvelle `null_reason` scientifique inventée — conservée dans `unevaluable_comparisons`.

**Association comparaison → `InterSGroupMatch`** : par identité d'objet (`id()`), jamais par égalité de dataclass (`IndexedSpectralGroup`/`CampaignCaseSpec` portent des `numpy.ndarray` non hashables). 0 ou >1 match trouvé → `InterSRobustnessError`.

Fichiers de ce lot : `scripts/level1b_analysis/robustness_evaluation.py` (`InterSRobustnessEvaluation`, `InterSRobustnessReport`, `InterSRobustnessError`, `build_inter_s_robustness_report`), `tests/scripts/level1b_analysis/test_robustness_evaluation.py`.

**Résultat accepté sur la campagne normative** : 712 comparaisons source → 684 évaluées, 28 non évaluables (6 `rho_QQ` + 0 `C_TT_conn` + 22 `flavor_singular_value_ratio`). Par observable : `gamma_O` 416, `rho_QQ` 90, `C_TT_conn` 96, `flavor_singular_value_ratio` 82. Par verdict : 684 `robust`, 0 `non_robust`, 0 `indeterminate`. `gamma_O` null parmi les évaluations : 252, toutes verdict `robust`. 0 groupe `partial_subspace`.

## Lot 1B-9f (accepté définitivement, `8a14a040f569d4eb85de9572b7d23bb587737549` + `a6450e994b7b1ce5c8d7d1fec876128a2a9622e9`)

Synthèse déterministe des résultats inter-S.

**Lot de synthèse descriptive uniquement.** Aucune nouvelle physique, aucun contrat scientifique modifié, aucune conclusion physique automatique. Consomme exclusivement `InterSMatchingReport` + `InterSObservableComparisonReport` + `InterSRobustnessReport` acceptés ; ne recalcule jamais `difference`/`amplitude`/`gamma_O`/`threshold`/`verdict`/`null_reason` quand un `RobustnessResult` existe déjà — celui-ci reste l'unique source de vérité. N'appelle jamais `evaluate_robustness`/`compute_gamma_o`/`match_spectral_group`, ne relit jamais `records.jsonl`, ne diagonalise rien. Ne fusionne jamais les verdicts élémentaires en un verdict global (`global_robust`, `geometry_is_stable`, etc. explicitement interdits), ne moyenne rien entre observables ou groupes différents, n'extrapole rien en `S`.

**Historique de ce sous-lot** : livraison candidate `8a14a040f569d4eb85de9572b7d23bb587737549` — conforme sur la synthèse statistique elle-même, mais acceptation initialement suspendue : les groupes/couples étaient découverts en parcourant `comparison_report.comparisons` plutôt que `matching_report.matches`, si bien qu'un `exact_label_match` valide sans aucune comparaison 1B-9d (liste fermée) disparaissait silencieusement de `groups`/`couples` tout en restant compté dans `matching_count`/`exact_match_count` → **correctif purement structurel décrit ci-dessous, livré au commit indiqué dans « Dernier commit accepté » ; aucune valeur scientifique modifiée**.

**Unité de synthèse et sa source de vérité (corrigé)** : le groupe spectral apparié inter-S (`InterSGroupMatch`, identifié par sa paire de `SpectralGroupMatchKey`, jamais par `representative_energy`/rang/ordre de fichier). La source de vérité pour l'EXISTENCE et l'ORDRE des groupes est `matching_report.matches` lui-même, jamais `comparison_report.comparisons` : un `InterSGroupSynthesis` est produit pour chaque match portant un `low_group` concret (`exact_label_match`), même sans aucune comparaison 1B-9d — un groupe vide (0 évaluation, 0 non-évaluable, verdicts 0/0/0, les 4 `observable_counts` à zéro) est légitime, jamais une erreur. Un match sans `low_group` concret (non exact) reste compté dans `matching_count`, mais ne produit jamais de `InterSGroupSynthesis`. Invariant vérifié avant implémentation : `InterSGroupMatch.__post_init__` (1B-9c, inchangé) garantit déjà `exact_label_match ⟺ low_group is not None` — d'où l'invariant global ajouté `len(groups) == exact_match_count`. `spectral_window_group_index` reste une métadonnée d'affichage intra-cas uniquement.

**Quatre niveaux de synthèse indépendants** :
- **Globale** (`InterSSynthesisReport`) : `matching_count`, `exact_match_count`, `source_comparison_count`, `evaluated_count`, `unevaluable_count`, `verdicts: VerdictCounts`, avec `len(groups) == exact_match_count`.
- **Par couple** (`InterSCoupleSynthesis`) : `high_spin`/`low_spin`, `groups` (ordre dérivé de `matching_report.matches`), comptages d'évaluations/non-évaluables/verdicts/par-observable dérivés exclusivement de `groups` (jamais un compte indépendant).
- **Par groupe apparié** (`InterSGroupSynthesis`) : couple, les deux `SpectralGroupMatchKey`, les deux `spectral_window_group_index`, `match_status`, et les `InterSRobustnessEvaluation`/`ScalarObservableComparison` SOURCES elles-mêmes (références directes, jamais copiées ni remplacées par une agrégation) — **durci** : chaque évaluation/comparaison non-évaluable est vérifiée appartenir exactement à CE groupe (`match_key` ET index intra-cas des deux côtés, via `evaluation.match`/`comparison.high_group`/`low_group` — jamais l'énergie, jamais la proximité, jamais l'ordre), pour empêcher qu'une évaluation d'un autre groupe du même couple ne s'y glisse silencieusement.
- **Par observable** (`InterSObservableSynthesis`, 4 exemplaires, ordre fixe `gamma_O`/`rho_QQ`/`C_TT_conn`/`flavor_singular_value_ratio`) : comptages + statistiques descriptives.

**Invariants `observable_counts`** : pour `InterSGroupSynthesis` et `InterSCoupleSynthesis`, `observable_counts` doit contenir EXACTEMENT les quatre `observable_kind` de `ROBUSTNESS_EVALUATION_ORDER`, dans cet ordre — pas seulement quatre comptes dont la somme tombe juste.

**Statistiques descriptives** (`DescriptiveStatistics` : `count`/`minimum`/`maximum`/`median`, `count == 0 ⟺` les trois autres `None`) : `difference` et `amplitude` lues directement sur chaque `RobustnessResult` ; `median` = `statistics.median` du stdlib, jamais réimplémenté (règle pair/impair déjà standard). `gamma_O` (`GammaOStatistics` : `defined_count`/`null_count`/`values`) calculé pour CHAQUE observable (chaque `RobustnessResult`, quel que soit l'`observable_kind` évalué, porte son propre `gamma_o` — champ générique de la primitive, pas spécifique à `"gamma_O"`).

**Association comparaison → groupe déjà existant** (jamais une recherche d'existence) : réutilise directement `robustness_evaluation._index_matches_by_group_identity`/`_find_source_match` (import direct de primitives privées, aucune duplication) — même mécanisme d'identité d'objet que 1B-9e, pour la même raison (`numpy.ndarray` non hashables) — uniquement pour répartir chaque comparaison dans le groupe déjà déterminé par `matching_report.matches`, jamais pour décider si ce groupe existe.

**Provenance** : `campaign_id`/`manifest_fingerprint`/`repository_commit` conservés depuis les rapports source ; les trois rapports d'entrée doivent partager exactement la même provenance, sinon `InterSSynthesisError` avant toute construction.

**Ordre** : dérivé de `matching_report.matches` (couples/groupes, restreint aux entrées à `low_group` concret) et de l'ordre fixe des 4 observables — jamais un tri par `difference`/`gamma_O`/`amplitude`/`verdict`/`representative_energy` (le tri interne pour la médiane reste transitoire, jamais l'ordre de sortie).

**Interdictions strictes de ce lot** : aucune modification de `src/cosmobox/level1/{matching,robustness,results,serialization}.py`, `scripts/level1b_campaign/*`, `experiments/level1/*`, `schemas/*`, `.github/workflows/*` ; aucun `evaluate_robustness`/`compute_gamma_o`/`match_spectral_group`/`run_single_case`/`run_campaign`/`launch_normative_campaign`/`run_level1b_campaign` ; aucun nouveau seuil/formule/`null_reason`/verdict ; aucun fichier écrit sous `/workspaces/level1b_campaign_output` ni ailleurs.

Fichiers de ce lot : `scripts/level1b_analysis/synthesis.py` (`InterSSynthesisReport`, `InterSCoupleSynthesis`, `InterSGroupSynthesis`, `InterSObservableSynthesis`, `DescriptiveStatistics`, `GammaOStatistics`, `VerdictCounts`, `ObservableEvaluationCounts`, `InterSSynthesisError`, `build_inter_s_synthesis_report`), `tests/scripts/level1b_analysis/test_synthesis.py`.

**Smoke-test réel mesuré** (`/workspaces/level1b_campaign_output`, lecture seule, non hardcodé, invariants 1B-9e exactement reproduits, inchangés après correctif) : 7 groupes appariés (7 `exact_label_match`, `len(groups) == exact_match_count` vérifié), 712 comparaisons source → 684 évaluées / 28 non évaluables. Par observable : `gamma_O` 416 (`gamma_o` défini=164/null=252), `rho_QQ` 90 (unevaluable=6), `C_TT_conn` 96 (unevaluable=0), `flavor_singular_value_ratio` 82 (unevaluable=22). Verdicts : 684 `robust`/0 `non_robust`/0 `indeterminate` partout (global, par couple, par groupe, par observable). Par couple : `triangle` 2 groupes/72 éval/12 non-éval ; `ring4` 2 groupes/192 éval/16 non-éval ; `ring5` 3 groupes/420 éval/0 non-éval. Statistiques (`difference`/`amplitude`/`gamma_O`) mesurées par observable, non hardcodées. `runs/` inchangé. Ceci est un relevé technique, aucune conclusion physique.

1B-9f clôt la chaîne d'analyse mécanique (artefacts → indexation → matching → comparaisons → verdicts → synthèse). Il ne clôt pas, par lui-même, la science de Level 1B : cette clôture scientifique documentaire est le périmètre exact du lot 1B-9g ci-dessous, écrit sous responsabilité conceptuelle de ChatGPT et livré par Claude Code en documentaire uniquement, aucune conclusion de type « géométrie robuste »/« limite continue confirmée » n'ayant jamais été autorisée dans le code de 1B-9f.

**État local de `.gitignore`** : modification volontaire de Lionel (ajout de `results/` aux chemins ignorés), hors périmètre de ce lot — laissée telle quelle, non stagée, non commitée.

## Lot actif

1B-9g — clôture scientifique documentaire de Level 1B.

**Lot documentaire uniquement.** Aucun nouveau calcul scientifique, aucune campagne, aucun code, aucune nouvelle observable, aucune nouvelle formule, aucun nouveau seuil, aucun nouveau verdict, aucune nouvelle `null_reason`. Consomme exclusivement les résultats déjà acceptés de 1B-9f (`campaign_id=level1b-reference-v1`, `manifest_fingerprint=159660cac738518dc620b9627ec95fd67c5dbc283707fdf72e572886364693ab`, `repository_commit source=0ff65ac66b4aa054f739b350cd384c26ecd19752`) et l'audit scientifique en lecture seule qui l'a suivi (aucune campagne relancée, artefacts `runs/` inchangés).

**Livrable** : `docs/levels/level1/level1b-conclusion.md` (structure fixe en 16 sections : objet et périmètre, provenance, résultat global, robustesse inter-S, secteur de saveur maximale, structure SU(2), valeurs singulières et invariance de saveur, traitement des nulls, `gamma_O` défini vs sous floor, sensibilité par observable, groupe le plus discriminant, ce qui est établi, ce qui est compatible mais non établi, ce qui n'est pas démontré, relation avec le scénario général, transition vers Level 1C). Distingue explicitement les résultats normatifs (théorème du secteur de saveur maximale V11, contrat de normalisation nulle V15) des interprétations analytiques dérivées (annulation du corrélateur habillé en secteur de saveur maximale, structure SU(2) proportionnelle à l'identité — cross-check de V16, jamais un nouveau théorème pré-enregistré).

**Fichiers autorisés (strict)** : `docs/governance/current-task.md`, `docs/levels/level1/level1b-conclusion.md`, `docs/README.md`. Aucun autre fichier. Aucun Python, aucun manifeste, aucun schéma, aucun artefact, aucun test scientifique modifié.

**1B-9g livré / Level 1B clos / aucun Level 1C démarré / aucune nouvelle campagne autorisée.** Le pointeur « Dernier commit accepté » ci-dessus reste `a6450e994b7b1ce5c8d7d1fec876128a2a9622e9` : le commit portant ce lot n'est pas encore formellement accepté, en attente d'audit — même règle que pour chaque lot précédent avant son acceptation.

**Historique de ce sous-lot** : livraison candidate `60ab94f89237a6489b89d2af08b459fc2cb1db23` — conforme scientifiquement sur le fond, mais acceptation initialement suspendue pour deux corrections terminologiques/de portée strictement bornées, aucune valeur ni conclusion scientifique modifiée :

1. confusion terminologique « troncature spectrale `S` » (`S` désigne la troncature en spin de lien / degré de liberté de jauge, notion distincte de la troncature spectrale — `spectral_window`/fenêtre d'eigenvalues/`partial_subspace`/`lower_bound_only`) — corrigé dans `level1b-conclusion.md` §1 et §4 (et vérifié absent ailleurs dans le document) ;
2. formulation de §13 laissant entendre qu'une robustesse inter-S avait déjà été testée sous `j_break` — corrigée : les cas `j_break` de `triangle`/`ring5` n'ont qu'un seul point `S` chacun dans cette campagne et ne produisent donc aucun couple inter-S admissible ; `j_break` a servi ailleurs de contrôle de réduction de symétrie sur cas unique, jamais de comparaison de robustesse inter-S.

Correctif livré au commit indiqué dans « Dernier commit accepté » une fois audité. Le pointeur ci-dessus reste `a6450e994b7b1ce5c8d7d1fec876128a2a9622e9` jusqu'à l'audit de ce correctif.

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
