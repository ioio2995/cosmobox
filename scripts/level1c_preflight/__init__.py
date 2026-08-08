"""Exploratory, non-normative preflight tooling for Level 1C (1C-4a).

jbreak_spectral_preflight.py checks, in a disposable and read-only way,
whether the j_break Hamiltonian case remains spectrally exploitable at
S=3 for a future inter-S comparison -- reusing only already-accepted
Level0/Level1 primitives, never writing under
/workspaces/level1b_campaign_output/, never calling
launch_normative_campaign/run_campaign, never modifying the manifest or
the schema. This package produces no normative result.
"""
