"""Post-processing analysis layer over already-validated, immutable
Level1B campaign artifacts. loader.py/indexing.py (1B-9b) build a
validated loader and an immutable intra-case spectral-group index;
inter_s.py (1B-9c) matches S_high spectral groups to S_low ones via
cosmobox.level1.matching.match_spectral_group, unmodified. No gamma_O,
no robustness verdict, anywhere in this package.
"""
