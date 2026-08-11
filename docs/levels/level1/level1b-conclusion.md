# Conclusion scientifique — Level 1B

Statut : **clos**

Branche : `research/level1-correlators`

Ce document clôt scientifiquement Level 1B à partir des résultats déjà acceptés de la chaîne d'analyse mécanique (1B-9b à 1B-9f) et de l'audit descriptif en lecture seule qui l'a suivie. Il ne recalcule rien, ne redéfinit aucune formule, aucun seuil, aucun verdict et n'introduit aucune `null_reason`. Toutes les valeurs numériques citées ici ont déjà été mesurées et rapportées dans le cadre des lots acceptés ; ce document les organise en conclusion, sans en produire de nouvelles.

## 1. Objet et périmètre

Level 1B a validé, sur un ensemble de géométries de graphe (`triangle`, `ring4`, `ring5`) et de valeurs du spin de lien `S`, une chaîne complète d'observables invariantes de jauge — corrélateurs habillés bruts et connectés, invariants de saveur, diagnostics spectraux restreints — puis a testé leur robustesse sous variation de la troncature en spin de lien `S` selon un critère de robustesse gelé (D018).

Ce document ne couvre que :

- la campagne normative pré-enregistrée (`campaign_id = level1b-reference-v1`) ;
- l'appariement inter-S exact tel que défini par 1B-9c (`match_spectral_group`, D022) ;
- les quatre observables inter-S effectivement évaluées par 1B-9d/1B-9e : `gamma_O`, `rho_QQ`, `C_TT_conn`, `flavor_singular_value_ratio` ;
- les résultats mesurés par la synthèse déterministe 1B-9f et par l'audit scientifique en lecture seule qui l'a suivie.

Il ne couvre ni `G_occ` ni `path_phase_coherence` (D013/D018), non produits par aucun module actuel, ni aucune hypothèse de plongement géométrique (voir §15).

## 2. Provenance

```text
campaign_id           = level1b-reference-v1
manifest_fingerprint  = 159660cac738518dc620b9627ec95fd67c5dbc283707fdf72e572886364693ab
repository_commit source = 0ff65ac66b4aa054f739b350cd384c26ecd19752
```

Chaîne d'analyse acceptée (immuable, jamais modifiée depuis) :

```text
CampaignArtifactIndex (1B-9b)
  → InterSMatchingReport (1B-9c)
  → InterSObservableComparisonReport (1B-9d)
  → InterSRobustnessReport (1B-9e)
  → InterSSynthesisReport (1B-9f)
```

HEAD d'analyse au moment de la clôture : `a6450e994b7b1ce5c8d7d1fec876128a2a9622e9`.

## 3. Résultat global de la campagne

```text
7 groupes spectraux appariés exactement (exact_label_match) entre S=3 et S=2
712 comparaisons source (liste fermée des 4 observables ci-dessus)
684 comparaisons évaluables (les deux valeurs source sont numériques)
28 comparaisons non évaluables (au moins une valeur source est null)

684 verdicts robust
0 verdict non_robust
0 verdict indeterminate
```

Ces chiffres sont ceux déjà acceptés par 1B-9f et reconfirmés à l'identique par l'audit de lecture seule qui a suivi son acceptation (`runs/` byte-identique avant/après, aucune campagne relancée).

## 4. Robustesse inter-S

Pour les groupes spectraux pouvant être appariés exactement entre S=3 et S=2 dans la campagne pré-enregistrée Level 1B, les observables inter-S testées ne présentent aucune sensibilité significative à cette variation de troncature selon le critère de robustesse gelé.

```text
ratio_to_threshold maximal observé = 0.0872

aucune des 684 évaluations ne dépasse 9 % de la frontière
du critère de robustesse

marge minimale absolue au seuil = 0.0456
```

La stabilité inter-S observée est obtenue avec une marge très importante vis-à-vis du seuil pré-enregistré. Deux points `S=2` et `S=3` ne démontrent pas une convergence : ce résultat est un test de robustesse ponctuel entre deux troncatures successives du degré de liberté de lien, pas une preuve de convergence d'une suite en `S` (voir §10 et §13).

## 5. Secteur de saveur maximale

La spécification gelée (`docs/levels/level1/specification.md`, §5, « Théorème du secteur de saveur maximale ») établit analytiquement que pour `T = n/2`, le nombre de doubles occupations `n_d` est nul, et qu'à demi-remplissage l'absence de doubles occupations implique aussi l'absence de trous (`n_i = 1`, `Q_i = 0` pour tout site). Dans tout multiplet complet à demi-remplissage de saveur maximale, la spécification prédit donc `C_QQ(i,j) = 0`, donc `rho_QQ = null` avec `null_reason = zero_local_charge_variance` — résultat gouverné conjointement par V11 (Saveur maximale, théorème analytique) et V15 (Normalisation nulle, contrat de sérialisation) du plan de validation : V11 établit que la variance de charge est analytiquement nulle dans ce secteur, V15 fixe le contrat selon lequel cette nullité doit être sérialisée comme `null`/`zero_local_charge_variance`, jamais comme une valeur numérique fabriquée.

**Résultat observé** : le groupe spectral `triangle[1→1]` (`T = 3/2`, saveur maximale pour `triangle`) produit exactement 6 comparaisons `rho_QQ` non évaluables, toutes both-null, `zero_local_charge_variance`/`zero_local_charge_variance` des deux côtés. Ceci constitue une confirmation directe, dans les artefacts normatifs réels, de la conséquence normative du théorème de saveur maximale combinée au contrat de normalisation.

### Corrélateur habillé dans le secteur de saveur maximale (interprétation analytique dérivée)

Le même groupe `triangle[1→1]` produit également 24 comparaisons `O_ij_raw` (l'observable source de `gamma_O`), toutes sous le plancher de normalisation (`amplitude <= NORMALIZATION_FLOOR`).

Une interprétation analytique dérivée — à distinguer explicitement du théorème normatif ci-dessus — est la suivante : pour `i != j`, l'opérateur `c†_{i,alpha} W_P c_{j,beta}` appliqué à un état où tous les sites sont simplement occupés crée localement une lacune et une double occupation ; cette configuration sort du sous-espace de saveur maximale. Dans la prescription canonique sur le multiplet complet (`rho_M = Pi_M / d`, spécification §4), cela explique l'annulation de l'espérance du corrélateur habillé dans ce secteur.

Cette explication est une **conséquence analytique cohérente avec le résultat observé** — elle n'est pas elle-même un théorème pré-enregistré dans la spécification Level 1B.

## 6. Structure SU(2) des corrélateurs

Sur les 416 comparaisons `gamma_O` (observable `O_ij_raw`), 252 sont sous le plancher de normalisation, réparties par composante de saveur :

```text
alpha0_beta0 =  22
alpha0_beta1 = 104
alpha1_beta0 = 104
alpha1_beta1 =  22
```

Les deux composantes hors diagonale de la matrice de saveur (`alpha0_beta1`, `alpha1_beta0`) représentent ensemble 208 des 252 cas sous plancher.

Pour un multiplet complet traité par la prescription canonique `rho_M = Pi_M / d` (invariante sous toute rotation unitaire interne `Psi -> Psi V`, spécification §4), et dans le régime SU(2) non brisé du point de référence de la campagne (`J_i = 1` uniforme, aucun terme de brisure de saveur), une matrice de corrélation de saveur covariante est attendue proportionnelle à l'identité dans l'espace de saveur (`G^{alpha beta} ∝ delta^{alpha beta}`). La suppression numérique systématique des composantes hors diagonale observée dans les artefacts est donc cohérente avec cette structure.

Il s'agit d'un **cross-check structurel de la covariance SU(2) et de la prescription canonique en multiplet complet** — pas de la mesure de 208 tests statistiquement indépendants de SU(2) : ces 208 occurrences sont des manifestations répétées d'un même invariant structurel, pas 208 confirmations indépendantes.

## 7. Valeurs singulières et invariance de saveur

Pour les 82 comparaisons `flavor_singular_value_ratio` évaluables (liste fermée, V16 « Invariance de saveur »), la valeur source (`sigma_2 / sigma_1`) vaut 1 à la précision numérique sur les deux valeurs de `S` comparées (`amplitude = 1` sur les 82 cas), avec des différences inter-S de l'ordre de `1e-15` (maximum mesuré `≈ 7.327e-15`).

Dans une matrice de saveur proportionnelle à l'identité (§6), les deux valeurs singulières sont égales : ce résultat constitue une seconde représentation numérique de la même invariance SU(2), et non une preuve indépendante distincte.

**La suppression des composantes hors diagonale (§6) et `flavor_singular_value_ratio ≈ 1` (présente section) ne constituent pas deux preuves indépendantes d'une nouvelle physique.** Ce sont deux manifestations cohérentes de la même structure de saveur, dont le plan de validation gelé porte déjà l'exigence sous l'identifiant V16. Les résultats de campagne fournissent un cross-check numérique de cette structure dans les artefacts normatifs réels — ils ne constituent pas une nouvelle démonstration analytique.

## 8. Traitement des nulls

```text
28 comparaisons non évaluables au total

rho_QQ : 6 both-null, zero_local_charge_variance / zero_local_charge_variance
flavor_singular_value_ratio : 22 both-null, normalization_denominator_below_floor / normalization_denominator_below_floor
```

Aucun null asymétrique high/low n'a été observé sur l'ensemble de la campagne. Aucune valeur artificielle, aucun zéro injecté, aucun epsilon, aucun `RobustnessResult` fabriqué pour une comparaison source-null (1B-9e/1B-9f).

**Conclusion autorisée** : les nulls observés sont structurellement cohérents avec les domaines de définition des observables et sont conservés symétriquement entre `S=3` et `S=2` dans la campagne. Cette conclusion ne s'étend à aucune affirmation physique plus générale.

## 9. gamma_O : défini vs sous floor

Sur les 416 comparaisons `gamma_O` (observable `O_ij_raw`) :

```text
164 gamma_O définis    : median = 0.00967   max = 0.03828
252 gamma_O non définis (normalization_denominator_below_floor)
```

Les 164 valeurs définies portent une information de variation relative directement interprétable. Les 252 valeurs non définies ne portent aucune information relative : elles montrent seulement que des amplitudes déjà quasi nulles restent quasi nulles en valeur absolue entre `S=3` et `S=2` — leur `gamma_O` est **non défini**, jamais `gamma_O = 0` ni `gamma_O ≈ 0`.

## 10. Sensibilité par observable

Les trois observables scalaires évaluables ne sont pas réductibles à une même distribution ; chacune est rapportée séparément, sans moyenne inter-observable.

- **`rho_QQ`** (90 évaluables) : `amplitude` médiane ≈ 0.351, `difference` médiane ≈ 0.00194, `gamma_o` (champ générique de `RobustnessResult`) médian ≈ 0.00450, maximum ≈ 0.0366. La robustesse observée sur cet observable n'est pas réductible uniquement à des quantités quasi nulles : les amplitudes sont d'ordre 0.1 à 0.5, pas concentrées près de zéro.

- **`C_TT_conn`** (96 évaluables) : `difference` médiane ≈ 8.19e-4, maximum ≈ 1.148e-3. Nuance nécessaire : le `gamma_o` générique de `RobustnessResult` atteint jusqu'à ≈ 0.281 sur certaines amplitudes faibles de cet observable. `robust` selon le critère gelé ne signifie donc pas automatiquement une variation relative infinitésimale ; cette nuance n'est pas masquée par le résultat global 684/684 `robust`.

- **`gamma_O`** (observable `O_ij_raw`, 164 définis / 252 sous floor) : catégorie conservée séparément, voir §9.

- **`flavor_singular_value_ratio`** (82 évaluables) : quasi constant à 1, différences d'ordre `1e-15` — voir §7, résultat dominé par l'invariance de saveur structurelle plutôt que par une propriété générique de robustesse.

Ces données permettent de distinguer ultérieurement, hors périmètre de ce document, dans quelle mesure le résultat global `684/684 robust` provient de différences réellement uniformes, de seuils permissifs relativement aux amplitudes, d'un grand nombre de quantités quasi nulles, ou d'un mélange de ces effets — aucune de ces hypothèses n'est tranchée ici.

## 11. Groupe le plus discriminant

Le groupe spectral `ring5-S3[groupe 1] → ring5-S2[groupe 1]` présente la plus forte sensibilité inter-S observée dans la campagne :

```text
gamma_O max ≈ 0.03828
ratio_to_threshold max ≈ 0.0872
```

Les 10 comparaisons les plus proches de la frontière du critère de robustesse, toutes observables confondus, proviennent de ce même groupe.

Ce groupe constitue un candidat prioritaire pour une future étude de convergence ou de perturbation, car c'est actuellement le cas le plus discriminant observé dans la campagne. Cette phrase n'autorise aucune nouvelle campagne : aucune n'est démarrée par ce document.

Sans démonstration supplémentaire à partir des labels spectraux déjà acceptés, aucune interprétation de représentation spatiale (par exemple un moment angulaire de translation `k = 0`, ou toute affirmation qu'il s'agirait du « multiplet le moins protégé par la symétrie spatiale ») n'est attribuée à ce groupe dans ce document.

## 12. Ce que Level 1B établit

- Les groupes spectraux normatifs considérés sont appariables exactement entre `S=3` et `S=2` dans les 7 cas retenus de la campagne pré-enregistrée.
- Les 684 comparaisons évaluables passent le critère de robustesse gelé (D018) : 684 `robust`, 0 `non_robust`, 0 `indeterminate`.
- Aucune comparaison n'est proche de la frontière du seuil (`ratio_to_threshold` maximal ≈ 0.087).
- Les patterns de nullité de charge dans le secteur de saveur maximale (`rho_QQ` both-null sur `triangle[1→1]`, `T=3/2`) correspondent à la structure analytique attendue par le théorème du secteur de saveur maximale (V11) combiné au contrat de normalisation nulle (V15).
- La structure de saveur des corrélateurs au point SU(2)-symétrique de référence est cohérente avec une matrice proportionnelle à l'identité, observée via la suppression systématique des composantes hors diagonale de `O_ij_raw` et l'égalité des valeurs singulières (`flavor_singular_value_ratio ≈ 1`) — cross-check numérique de V16, pas une nouvelle démonstration analytique.
- La sérialisation et la propagation des nulls sont cohérentes avec les domaines de définition des observables : aucun null asymétrique, aucune valeur fabriquée, sur l'ensemble de la campagne.

## 13. Ce qui est compatible avec les données mais non établi

- Une convergence des observables lorsque `S` augmente au-delà de `S=3`.
- L'existence d'une limite asymptotique en `S`.
- Une stabilité similaire à des valeurs `S > 3`.
- Une robustesse inter-S similaire sous des perturbations du Hamiltonien telles que `j_break`, qui n'ont pas été comparées entre plusieurs valeurs de `S` dans la présente campagne.

Ces énoncés sont compatibles avec les résultats mesurés (aucune contradiction observée) mais ne sont établis par aucun résultat de cette campagne : la campagne compare exactement deux points, `S=3` et `S=2`.

Précision sur `j_break` : dans cette campagne, les cas `j_break` de `triangle`/`ring5` ne disposent que d'un seul point `S` chacun et ne produisent donc aucun couple inter-S admissible (1B-9a/1B-9c). `j_break` a été utilisé ailleurs dans Level 1B comme contrôle de réduction du groupe de symétrie sur un cas unique — cet usage ne doit jamais être confondu avec une comparaison de robustesse inter-S, qui n'a pas été effectuée sous `j_break`.

## 14. Ce qui n'est pas testé ou démontré

- La limite `S → infini`.
- Une distance physique émergente.
- Une métrique.
- Une courbure.
- Une causalité.
- Une gravité émergente.
- L'unicité d'un éventuel plongement géométrique.
- Une topologie continue.
- Toute interprétation géométrique d'un secteur spectral particulier (y compris celui de `ring5[1→1]`, §11).

## 15. Relation avec le scénario général et avec `geometry-liberation.md`

`docs/levels/level1/geometry-liberation.md` reste une orientation conceptuelle non normative pour Level 1B. Aucune hypothèse de plongement qui y est décrite (`R1`, `R2`, `S1`, `S2`, ou toute autre) n'est transférée dans la présente conclusion. Level 1B valide des structures relationnelles robustes ; il ne définit aucune distance effective ni aucune métrique.

Formulations autorisées pour la portée du résultat vis-à-vis du scénario général étudié :

> Une précondition nécessaire du scénario étudié — à savoir que les structures relationnelles ne soient pas un artefact fragile d'une valeur particulière de la troncature `S` — passe un test non trivial entre `S=2` et `S=3` dans le domaine pré-enregistré.

> Ces structures conservent simultanément les propriétés de symétrie internes attendues dans les corrélateurs.

Sont explicitement exclues de ce document les formulations : « la théorie est confirmée », « la géométrie est démontrée », « l'espace émerge ».

### Portée exacte concernant `S`

La campagne compare uniquement `S=3` et `S=2`. Elle ne compare aucun observable Level 1B à `S=1`. Il est donc exclu d'affirmer que Level 1B réhabilite `S=1`, valide `S=1`, ou démontre une convergence `S=1 → 2 → 3`. Si des choix de conception antérieurs avaient motivé `S=2` comme troncature de référence, la formulation autorisée est :

> La robustesse des observables de corrélation entre `S=2` et `S=3` est compatible avec le choix de `S=2` comme troncature de référence pour le domaine testé.

Ceci n'est pas une preuve de limite continue (§14).

## 16. Transition vers Level 1C

Level 1B est clos avec les conventions actuelles. Conformément à `geometry-liberation.md` §9, la libération de la géométrie reste enregistrée comme orientation de conception dont l'implémentation est différée. Le séquençage reste :

```text
Level 1B clos
    ↓
conception / pré-enregistrement séparé de Level 1C
    ↓
reconstruction et comparaison de plongements
```

Aucun travail Level 1C n'est démarré par ce document. Aucune nouvelle campagne normative n'est autorisée par ce document.
