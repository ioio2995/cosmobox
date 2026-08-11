"""Level1C inter-J0 tracking. Lot 1C-8e.

Implements PHASE_T, positioned exactly after the baseline non-regression
gate (identifiability-preregistration.md section 20.19):

    P -> BASELINE_NON_REGRESSION_GATE -> T

For each of the 16 (perturbed_case_id, baseline_case_id) tracking edges
(section 20.10, INTER_J0_TRACKING_TOPOLOGY=BASELINE_CENTERED, never
chained) and each REQUIRED target of the edge's geometry, determines
whether the baseline's own selected branch has a unique, structurally
identifiable counterpart among the perturbed case's COMPLETE_MULTIPLET
groups (CLASS_POOL, section 20.12): same resolved twice_T and a matching
NUMERIC reflection character -- multiplicity is checked only after a
unique candidate is found (section 20.6 of the mandate), translation is
diagnostic-only and never an identity requirement, and representative_
energy/spectral rank/spectral_window_group_index are never discriminants.

This package never diagonalizes, never calls run_level1c_case, never
executes the baseline non-regression gate itself, and never launches a
real 20-case campaign -- it only reads already-persisted Level1C case
artifacts (runs/<case_id>/{run.json,records.jsonl}) from disk, reusing
scripts.level1c_baseline_gate.gate's own baseline-loading/structural-data
primitives for the baseline side and scripts.level1c_campaign.outputs's
shared integrity primitives for the perturbed side.

A perturbed case's own normative_case_valid (its REQUIRED targets'
selection verdict) is irrelevant to whether its structural groups can
feed CLASS_POOL construction (PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE=
IRRELEVANT_TO_STRUCTURAL_TRACKING): CLASS_POOL is built from every
COMPLETE_MULTIPLET group in the production window unconditionally
(section 20.6), never filtered by target-selection success. Only
run_status=='success' (a technical fact) is required of the perturbed
side; a technically-failed perturbed case yields AMBIGUOUS tracking
outcomes for its targets, never a silent exclusion and never a new
invented status ("un calcul non resolu ne prouve ni presence ni
absence", section 20.12).

This package never concludes RESPONSE_AVAILABLE and never computes
Delta_C_TT -- that belongs to PHASE_R.
"""
