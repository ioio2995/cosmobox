"""Level1C baseline non-regression gate. Lot 1C-8d.

Implements the gate positioned exactly between PHASE_P and PHASE_T
(identifiability-preregistration.md section 20.19):

    P -> BASELINE_NON_REGRESSION_GATE -> T

Compares the four Level1C J0=1 baselines (triangle/ring5 x S in {2,3})
already produced by scripts.level1c_campaign.runner (PHASE_P, accepted)
against their Level1B reference counterparts, using the tolerances
frozen by the accepted calibration (1C-7c4/1C-7c5). This package never
diagonalizes, never calls run_level1c_case, and never launches a real
20-case campaign -- it only reads already-persisted artifacts
(runs/<case_id>/{run.json,records.jsonl}) from disk.

Historical target identity (fundamental/first_excited/T_3_2) is
established from the persisted Level1B corpus by structural proof, not
by any target_id ever written to disk (D022: the campaign never
persisted target_id -> spectral_window_group_index). fundamental/
first_excited are positional (rank 0/1, a direct consequence of how
spectral_window_group_index is built) and need no further proof.
ring5's T_3_2 (a flavor_label target) is established by exclusion:
every other historical target in the manifest is checked against its
own frozen, deterministic necessary condition for explaining a given
persisted group; if all of them are excluded and exactly one persisted
group remains consistent with T_3_2's own necessary condition
(twice_T == target_twice_T), that group is T_3_2's proven historical
counterpart. This is a closed-world proof by elimination over the
manifest's own frozen target list -- never a reconstruction of the
historical candidate pool, and never the rejected heuristic "the
unique group with a matching twice_T is the target".
"""
