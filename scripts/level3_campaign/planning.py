"""Deterministic Level3 S4 campaign planning: manifest -> the three
ordered CaseSpec.

Performs no diagonalization and no observable computation: it only
cross-checks the manifest's own three cases against the frozen (geometry,
S=4) combinations -- never a subset, never reordered, never S=5, never
S=2/S=3 as an execution target (those come exclusively from the frozen
Level2 reference, cosmobox.level3.frozen_reference).
"""

from __future__ import annotations

from cosmobox.level3.execution import CaseSpec
from experiments.level3.manifest import Level3Manifest

EXPECTED_CASES: tuple[tuple[str, int], ...] = (("triangle", 4), ("ring4", 4), ("ring5", 4))
"""The three frozen Level3 S4 cases, geometry-major order -- the same
order as experiments.level3.manifest's own _EXPECTED_CASE_ORDER."""


def plan_campaign(manifest: Level3Manifest) -> tuple[CaseSpec, ...]:
    """The three CaseSpec this campaign must execute, in the manifest's
    own order. Raises ValueError if the manifest's cases do not match
    exactly the three frozen (geometry, S=4) combinations -- S=5 and any
    additional/missing geometry are therefore structurally impossible to
    plan, regardless of what a caller might pass as `manifest`."""
    manifest_cases = tuple((case.geometry, case.spin) for case in manifest.cases)
    if set(manifest_cases) != set(EXPECTED_CASES) or len(manifest_cases) != len(EXPECTED_CASES):
        raise ValueError(
            f"manifest cases {manifest_cases} do not match the three frozen Level3 S4 cases {EXPECTED_CASES}"
        )
    return tuple(CaseSpec(geometry=case.geometry, spin=case.spin) for case in manifest.cases)
