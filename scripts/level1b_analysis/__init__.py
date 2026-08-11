"""Post-processing analysis layer over already-validated, immutable
Level1B campaign artifacts. loader.py/indexing.py (1B-9b) build a
validated loader and an immutable intra-case spectral-group index;
inter_s.py (1B-9c) matches S_high spectral groups to S_low ones via
cosmobox.level1.matching.match_spectral_group, unmodified;
comparisons.py (1B-9d) extracts and compares the high/low observable
values of each exact_label_match couple (O_ij_raw -> gamma_O via
cosmobox.level1.robustness.compute_gamma_o, unmodified; rho_QQ/
C_TT_conn/flavor_singular_value_ratio -> raw numeric pairs);
robustness_evaluation.py (1B-9e) applies cosmobox.level1.robustness.
evaluate_robustness, unmodified, to every comparison whose source values
are both numeric -- a comparison with a null source value is carried
unevaluated, never given a fabricated verdict or a new null_reason;
synthesis.py (1B-9f) reorganizes and counts the results of 1B-9c/9d/9e
into deterministic global/per-couple/per-group/per-observable views --
it never re-matches, never recomputes a RobustnessResult field, and
never fuses individual verdicts into a new aggregate one.
"""
