"""Post-processing analysis layer over already-validated, immutable
Level1B campaign artifacts. loader.py/indexing.py (1B-9b) build a
validated loader and an immutable intra-case spectral-group index;
inter_s.py (1B-9c) matches S_high spectral groups to S_low ones via
cosmobox.level1.matching.match_spectral_group, unmodified;
comparisons.py (1B-9d) extracts and compares the high/low observable
values of each exact_label_match couple (O_ij_raw -> gamma_O via
cosmobox.level1.robustness.compute_gamma_o, unmodified; rho_QQ/
C_TT_conn/flavor_singular_value_ratio -> raw numeric pairs). No
robustness verdict (evaluate_robustness) anywhere in this package.
"""
