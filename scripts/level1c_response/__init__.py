"""Level1C PHASE_R response core. Lot 1C-8f-impl.

Implements PHASE_R, positioned exactly after inter-J0 tracking
(identifiability-preregistration.md section 20.19):

    P -> BASELINE_NON_REGRESSION_GATE -> T -> R

For each of the 40 tracking-record-v1 documents already persisted in
`tracking.jsonl` (1C-8e), produces exactly one response-record-v1
document: RESPONSE_AVAILABLE only if the tracking status is
TRACKED_ONE_TO_ONE AND the tracked branch on BOTH sides (baseline and
perturbed) is exactly the target's own pre-registered SELECTED,
normatively-conformant group (section 20.17: a structurally-continued
group is never conflated with a pre-registered target -- no post-hoc
observable recomputation for a candidate that was never selected).

RHO_RESPONSE_ROLE = PAIRWISE_CONCORDANCE_CONTROL (1C-8f-design, ratified):
rho_QQ keeps exactly its already-frozen role (contrôle de concordance
indépendant charge/jauge, jamais une sonde primaire) -- PHASE_R never
derives Delta_rho, a ratio, or any relative-change quantity from it. A
RESPONSE_AVAILABLE record juxtaposes rho_QQ_baseline(i,j) and
rho_QQ_perturbed(i,j) side by side as a descriptive control, preserving
numeric/null semantics and null_reason exactly, never coercing null to
0 and never deriving a verdict from a numeric/null mismatch (that
strict-equality discipline belongs to the baseline non-regression gate,
never to this descriptive PHASE_R control).

INCIDENT_NON_INCIDENT_CLASSIFICATION = DEFERRED_WITHIN_R (1C-8f-design):
no field, no function, no test for this classification exists anywhere
in this package.

PHYSICAL_RESPONSE_THRESHOLD = OPEN, always: this package never produces
a physical PASS/FAIL, a "significant"/"not significant" verdict,
geometry_emerged, gravity_detected, or any equivalent. G remains
DEFERRED -- no field, computation, or import related to G exists here.

This package performs no diagonalization, no re-tracking, and no
re-execution of PHASE_P or the baseline non-regression gate -- it only
reads already-persisted artifacts (runs/<case_id>/{run.json,
records.jsonl}, tracking.jsonl), reusing scripts.level1c_tracking's own
loading/integrity primitives and scripts.level1c_baseline_gate's own
structural-data extraction primitives verbatim.
"""
