"""Deterministic Level3 S6 campaign planning: manifest -> the three
ordered CaseSpec.

Performs no diagonalization and no observable computation: it only
cross-checks the manifest's own three cases against the frozen (geometry,
S=6) combinations -- never a subset, never reordered, never S=7, never
S=2/S=3/S=4/S=5 as an execution target (those come exclusively from the
three frozen references, cosmobox.level3.frozen_reference,
cosmobox.level3.frozen_s4_reference, and cosmobox.level3.frozen_s5_reference).
Spin 6 is imposed by this manifest's own contract alone -- nothing in
cosmobox.level3.execution.CaseSpec restricts spin globally.
"""

from __future__ import annotations

from cosmobox.level3.execution import CaseSpec
from experiments.level3.s6_manifest import Level3S6Manifest

EXPECTED_CASES: tuple[tuple[str, int], ...] = (("triangle", 6), ("ring4", 6), ("ring5", 6))
"""The three frozen Level3 S6 cases, geometry-major order -- the same
order as experiments.level3.s6_manifest's own _EXPECTED_CASE_ORDER."""


def plan_campaign(manifest: Level3S6Manifest) -> tuple[CaseSpec, ...]:
    """The three CaseSpec this campaign must execute, in the manifest's
    own order. Raises ValueError if the manifest's cases do not match
    exactly the three frozen (geometry, S=6) combinations -- S=7 and any
    additional/missing geometry are therefore structurally impossible to
    plan, regardless of what a caller might pass as `manifest`."""
    manifest_cases = tuple((case.geometry, case.spin) for case in manifest.cases)
    if set(manifest_cases) != set(EXPECTED_CASES) or len(manifest_cases) != len(EXPECTED_CASES):
        raise ValueError(
            f"manifest cases {manifest_cases} do not match the three frozen Level3 S6 cases {EXPECTED_CASES}"
        )
    return tuple(CaseSpec(geometry=case.geometry, spin=case.spin) for case in manifest.cases)
