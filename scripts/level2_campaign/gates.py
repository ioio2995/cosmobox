"""Structural, protocol-only validation gates for Level2 campaign
results.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE. Every gate here checks protocol and
structure only -- never the physical value obtained: no effect
threshold, no expected Delta_HL sign/direction, no minimum C_X_23, no
result-based retry.

Several invariants the L2-E mandate lists (full spectrum, solver_method
== "dense", window_truncated == False, partial_subspace_count == 0) are
deliberately NOT re-checked here as separate runtime conditions: they
cannot be, because cosmobox.level2.execution.CaseExecutionResult does
not carry Level0Report/solver metadata through (execution.run_case
discards it after deriving the four metric analyses). They do not need
re-checking either: execution.run_case can only ever RETURN a
CaseExecutionResult when the full spectrum was requested
(SpectrumOptions(n_eigenvalues=dimension), hardcoded, never
overridable) and every spectral group was complete_multiplet
(adapter.extract_complete_multiplets raises PartialSubspaceCaseRejected
otherwise, never caught here) -- for a dimension within
SpectrumOptions.max_dense_dimension (2000; the six frozen cases' maximum
is ring5 S=3 at 1504), requesting n_eigenvalues == dimension on the
dense path always yields window_truncated == False and
solver_method == "dense" by construction (cosmobox.level0.reports.
_dense_spectrum never truncates when k == dimension). A successfully
returned CaseExecutionResult therefore already IS full-spectrum,
dense-solved, and free of partial subspaces; asserting it again here
would be a redundant, unreachable check, not a real gate.

The one genuinely new check this module adds -- knowledge execution.py
itself has no reason to carry, since it is a fact about the six frozen
cases specifically, not about the execution pipeline in general -- is
dimension/group_count against L2_A1_PREFLIGHT_REFERENCE.
"""

from __future__ import annotations

from collections.abc import Sequence

from cosmobox.level2.execution import GEOMETRIES, L2_A1_PREFLIGHT_REFERENCE, CaseExecutionResult, GeometryComparison


class CaseGateFailure(ValueError):
    """A case's structural/protocol invariants do not match the L2-A1
    reference or the frozen full-spectrum/complete-multiplet contract."""


class CampaignGateFailure(ValueError):
    """The campaign as a whole is not eligible for COMPLETE status."""


def validate_case_result(result: CaseExecutionResult) -> None:
    """dimension/group_count against L2_A1_PREFLIGHT_REFERENCE, and exact
    q coverage of [0,1] with no gap or overlap between consecutive
    multiplets. Multiplicity-sum-equals-dimension and per-metric
    labeling are already enforced by CaseExecutionResult.__post_init__
    itself -- not repeated here."""
    key = (result.spec.geometry, result.spec.spin)
    if key not in L2_A1_PREFLIGHT_REFERENCE:
        raise CaseGateFailure(f"{key} is not one of the six frozen Level2 cases")

    expected_dimension, expected_group_count = L2_A1_PREFLIGHT_REFERENCE[key]
    if result.dimension != expected_dimension:
        raise CaseGateFailure(
            f"{key}: dimension {result.dimension} does not match the L2-A1 reference {expected_dimension}"
        )
    if result.group_count != expected_group_count:
        raise CaseGateFailure(
            f"{key}: group_count {result.group_count} does not match the L2-A1 reference {expected_group_count}"
        )

    entries = result.entries
    if entries[0].q_start != 0.0 or entries[-1].q_end != 1.0:
        raise CaseGateFailure(f"{key}: q coverage does not span exactly [0,1]")
    for previous, current in zip(entries, entries[1:]):
        if previous.q_end != current.q_start:
            raise CaseGateFailure(f"{key}: q coverage has a gap or overlap between consecutive multiplets")


def validate_campaign_completeness(
    case_results: Sequence[CaseExecutionResult],
    geometry_comparisons: Sequence[GeometryComparison],
) -> None:
    """6/6 cases present (exactly the six frozen combinations, no
    duplicate) and 3/3 geometry comparisons present (exactly the three
    frozen geometries, no duplicate). Provenance consistency (same
    repository_commit/manifest_fingerprint/campaign_id across every
    case) is not re-checked here: it is guaranteed by construction, not
    by a stored, checkable field -- a campaign runner resolves a single
    CampaignProvenance once (provenance.resolve_campaign_provenance) and
    threads that same object through every case and comparison, so there
    is no code path by which two different commits/fingerprints could
    ever be mixed into one campaign run."""
    expected_cases = set(L2_A1_PREFLIGHT_REFERENCE)  # the six frozen (geometry, spin) keys, verbatim
    actual_cases = [(result.spec.geometry, result.spec.spin) for result in case_results]
    if len(actual_cases) != len(set(actual_cases)):
        raise CampaignGateFailure(f"case_results contains duplicate cases: {actual_cases}")
    if set(actual_cases) != expected_cases:
        missing = sorted(expected_cases - set(actual_cases))
        unexpected = sorted(set(actual_cases) - expected_cases)
        raise CampaignGateFailure(
            f"case_results does not cover exactly the six frozen Level2 cases -- missing={missing}, unexpected={unexpected}"
        )

    actual_geometries = [comparison.geometry for comparison in geometry_comparisons]
    if len(actual_geometries) != len(set(actual_geometries)):
        raise CampaignGateFailure(f"geometry_comparisons contains duplicate geometries: {actual_geometries}")
    if set(actual_geometries) != set(GEOMETRIES):
        missing = sorted(set(GEOMETRIES) - set(actual_geometries))
        unexpected = sorted(set(actual_geometries) - set(GEOMETRIES))
        raise CampaignGateFailure(
            f"geometry_comparisons does not cover exactly the three frozen geometries -- missing={missing}, unexpected={unexpected}"
        )
