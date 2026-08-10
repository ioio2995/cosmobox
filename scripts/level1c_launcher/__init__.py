"""Level1C normative launcher. Lot 1C-8j.

Implements the single normative entry point capable of executing, in
strict order:

    P -> BASELINE_NON_REGRESSION_GATE -> T -> R

never PHASE_G. This package introduces no scientific logic whatsoever:
it only verifies launch preconditions (Git HEAD/branch/cleanliness, the
single normative manifest, output_dir/historical_output_dir safety),
then calls the four already-accepted phase entry points --
scripts.level1c_campaign.campaign.run_level1c_campaign,
scripts.level1c_baseline_gate.gate.run_baseline_nonregression_gate (+
its own write_gate_artifact, 1C-8j), scripts.level1c_tracking.tracking.
run_inter_j0_tracking (+ write_tracking_records), and scripts.level1c_
response.response.run_phase_r (+ write_response_records) -- unmodified,
never reimplemented, never given a parallel code path.

Governance (1C-8g/1C-8i, ratified):

  P_GLOBAL_SUCCESS == false  -> STOP_BEFORE_GATE (P/gate/T/R never
    silently promote a technically incomplete production)
  BASELINE_NON_REGRESSION_GATE == FAIL
    -> STOP_NORMATIVE_PIPELINE_BEFORE_T (no exception, never diagnostic
       T/R inside this launcher -- GATE_FAIL_DOWNSTREAM_DIAGNOSTICS=
       EXPLICIT_NON_NORMATIVE_ONLY belongs to a separate, explicit,
       non-normative tool, never this module)
  T_R_CACHE_REUSE_IMPLEMENTED = NO (1C-8i, ratified): tracking.jsonl/
    response.jsonl are always fully recomputed and atomically rewritten
    on every admitted launch -- no invalidation-cache policy is invented
    here.

repository_commit is never a free parameter anywhere in this package's
public API (prepare_normative_launch, launch_normative_campaign, or the
CLI in scripts/run_level1c_campaign.py) -- it is always derived from
`repo_root` itself via `git rev-parse HEAD`, exactly once at launch
time, and the SAME value is threaded through P, the gate, T, and R --
never replaced by a later re-read of HEAD, even though HEAD is
re-verified (never re-adopted) both immediately before PHASE_P and
immediately after PHASE_P/before the gate. A drift detected at either
checkpoint aborts the whole launch attempt (NormativeLaunchError) --
never a continuation under a different provenance. This narrows, but
never claims to close, the TOCTOU window: no Git lock is introduced.

Level1CNormativeLaunchReport is a purely in-memory, TECHNICAL
orchestration report -- it never computes or claims NORMATIVE_CAMPAIGN_
VALID, a physical verdict, or any scientific conclusion. No new
campaign-wide artifact is written by this package beyond the gate's own
baseline-nonregression.json (1C-8j) and T/R's own already-accepted
tracking.jsonl/response.jsonl.
"""
