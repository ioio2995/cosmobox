"""Structural, protocol-only validation gates for Level3 S4 campaign
results.

Every gate here checks protocol and structure only -- never the physical
value obtained: no effect threshold, no expected taxonomy, no minimum
C_X_34, no result-based retry.

full-spectrum/dense/window_truncated/partial_subspace_count are
deliberately NOT re-checked here as separate runtime conditions, for the
same reason scripts/level2_campaign/gates.py does not re-check them:
cosmobox.level3.execution.CaseExecutionResult does not carry
Level0Report/solver metadata through, and a successfully returned
CaseExecutionResult can only ever be the product of
cosmobox.level3.execution.run_case's own full-spectrum policy
(full_spectrum_options forcing the dense path, _check_dense_capability,
_assert_full_eigensystem raising IncompleteSpectrumRejected on anything
less) -- asserting it again here would be a redundant, unreachable check.

group_count has no pre-established reference: unlike Level2's L2-A1
preflight (real diagonalization, real degeneracy grouping), the L3-C
capability preflight only built the physical basis (dimension), never a
Hamiltonian or a spectrum -- so no group_count is known in advance for
S=4. Only dimension (established by L3-C) is cross-checked exactly;
group_count is checked structurally (>= 1) only.
"""

from __future__ import annotations

from collections.abc import Sequence

from cosmobox.level3.execution import CaseExecutionResult, SpinPairComparison
from experiments.level3.manifest import EXPECTED_S4_DIMENSIONS, SPIN


class CaseGateFailure(ValueError):
    """A case's structural/protocol invariants do not match the L3-C
    reference or the frozen full-spectrum/complete-multiplet contract."""


class CampaignGateFailure(ValueError):
    """The campaign as a whole is not eligible for COMPLETE status."""


def validate_case_result(result: CaseExecutionResult) -> None:
    """spin/geometry against the frozen Level3 S4 contract, dimension
    against EXPECTED_S4_DIMENSIONS (L3-C), and exact q coverage of [0,1]
    with no gap or overlap between consecutive multiplets.
    Multiplicity-sum-equals-dimension and per-metric labeling are already
    enforced by CaseExecutionResult.__post_init__ itself -- not repeated
    here."""
    if result.spec.spin != SPIN:
        raise CaseGateFailure(f"spin must be exactly {SPIN}, got {result.spec.spin!r}")
    if result.spec.geometry not in EXPECTED_S4_DIMENSIONS:
        raise CaseGateFailure(
            f"geometry {result.spec.geometry!r} is not one of the three frozen Level3 S4 cases "
            f"{sorted(EXPECTED_S4_DIMENSIONS)}"
        )

    expected_dimension = EXPECTED_S4_DIMENSIONS[result.spec.geometry]
    if result.dimension != expected_dimension:
        raise CaseGateFailure(
            f"{result.spec.geometry}: dimension {result.dimension} does not match the L3-C reference "
            f"{expected_dimension}"
        )
    if result.group_count < 1:
        raise CaseGateFailure(f"{result.spec.geometry}: group_count must be >= 1, got {result.group_count}")

    entries = result.entries
    if entries[0].q_start != 0.0 or entries[-1].q_end != 1.0:
        raise CaseGateFailure(f"{result.spec.geometry}: q coverage does not span exactly [0,1]")
    for previous, current in zip(entries, entries[1:]):
        if previous.q_end != current.q_start:
            raise CaseGateFailure(f"{result.spec.geometry}: q coverage has a gap or overlap between consecutive multiplets")


def validate_campaign_completeness(
    case_results: Sequence[CaseExecutionResult],
    geometry_comparisons: Sequence[SpinPairComparison],
) -> None:
    """3/3 cases present (exactly the three frozen S4 combinations, no
    duplicate) and 3/3 geometry comparisons present (exactly the three
    frozen geometries, no duplicate)."""
    expected_geometries = set(EXPECTED_S4_DIMENSIONS)

    actual_cases = [(result.spec.geometry, result.spec.spin) for result in case_results]
    if len(actual_cases) != len(set(actual_cases)):
        raise CampaignGateFailure(f"case_results contains duplicate cases: {actual_cases}")
    actual_case_geometries = {geometry for geometry, spin in actual_cases}
    if actual_case_geometries != expected_geometries or any(spin != SPIN for _, spin in actual_cases):
        raise CampaignGateFailure(
            f"case_results does not cover exactly the three frozen Level3 S4 cases -- got {actual_cases}"
        )

    actual_geometries = [comparison.geometry for comparison in geometry_comparisons]
    if len(actual_geometries) != len(set(actual_geometries)):
        raise CampaignGateFailure(f"geometry_comparisons contains duplicate geometries: {actual_geometries}")
    if set(actual_geometries) != expected_geometries:
        missing = sorted(expected_geometries - set(actual_geometries))
        unexpected = sorted(set(actual_geometries) - expected_geometries)
        raise CampaignGateFailure(
            f"geometry_comparisons does not cover exactly the three frozen geometries -- "
            f"missing={missing}, unexpected={unexpected}"
        )
