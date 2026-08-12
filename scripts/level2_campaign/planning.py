"""Deterministic Level2 campaign planning: manifest -> the six ordered
CaseSpec.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE. Performs no diagonalization and no
observable computation: it only cross-checks the manifest's own six
cases against cosmobox.level2.execution.build_all_reference_case_specs()
(the same frozen, physically-locked case set) and returns them in the
manifest's own order -- never a subset, never reordered, never an
implicit normative selection.
"""

from __future__ import annotations

from experiments.level2.manifest import Level2Manifest
from cosmobox.level2.execution import CaseSpec, build_all_reference_case_specs


def plan_campaign(manifest: Level2Manifest) -> tuple[CaseSpec, ...]:
    """The six CaseSpec this campaign must execute, in the manifest's own
    order. Raises ValueError if the manifest's cases do not match exactly
    the six frozen (geometry, spin) combinations
    build_all_reference_case_specs() itself produces."""
    expected = {(spec.geometry, spec.spin) for spec in build_all_reference_case_specs()}
    manifest_cases = {(case.geometry, case.spin) for case in manifest.cases}
    if manifest_cases != expected:
        raise ValueError(
            f"manifest cases {sorted(manifest_cases)} do not match the six frozen Level2 cases {sorted(expected)}"
        )
    return tuple(CaseSpec(geometry=case.geometry, spin=case.spin) for case in manifest.cases)
