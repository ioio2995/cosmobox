"""Deterministic Level3 S5 campaign planning: manifest -> the three
ordered CaseSpec.

Performs no diagonalization and no observable computation: it only
cross-checks the manifest's own three cases against the frozen (geometry,
S=5) combinations -- never a subset, never reordered, never S=6, never
S=2/S=3/S=4 as an execution target (those come exclusively from the two
frozen references, cosmobox.level3.frozen_reference and
cosmobox.level3.frozen_s4_reference). Spin 5 is imposed by this
manifest's own contract alone -- nothing in cosmobox.level3.execution.
CaseSpec restricts spin globally.
"""

from __future__ import annotations

from cosmobox.level3.execution import CaseSpec
from experiments.level3.s5_manifest import Level3S5Manifest

EXPECTED_CASES: tuple[tuple[str, int], ...] = (("triangle", 5), ("ring4", 5), ("ring5", 5))
"""The three frozen Level3 S5 cases, geometry-major order -- the same
order as experiments.level3.s5_manifest's own _EXPECTED_CASE_ORDER."""


def plan_campaign(manifest: Level3S5Manifest) -> tuple[CaseSpec, ...]:
    """The three CaseSpec this campaign must execute, in the manifest's
    own order. Raises ValueError if the manifest's cases do not match
    exactly the three frozen (geometry, S=5) combinations -- S=6 and any
    additional/missing geometry are therefore structurally impossible to
    plan, regardless of what a caller might pass as `manifest`."""
    manifest_cases = tuple((case.geometry, case.spin) for case in manifest.cases)
    if set(manifest_cases) != set(EXPECTED_CASES) or len(manifest_cases) != len(EXPECTED_CASES):
        raise ValueError(
            f"manifest cases {manifest_cases} do not match the three frozen Level3 S5 cases {EXPECTED_CASES}"
        )
    return tuple(CaseSpec(geometry=case.geometry, spin=case.spin) for case in manifest.cases)
