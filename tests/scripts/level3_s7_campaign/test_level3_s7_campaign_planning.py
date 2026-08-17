"""Unit tests for scripts.level3_s7_campaign.planning (lot L3-AC). Uses
the real, frozen manifest (pure JSON loading, no diagonalization) and
hand-mutated copies of it.
"""

from __future__ import annotations

import pytest

from experiments.level3.s7_manifest import load_manifest
from scripts.level3_s7_campaign.planning import EXPECTED_CASES, plan_campaign


def test_plan_campaign_produces_exactly_three_s7_cases():
    manifest = load_manifest()
    planned = plan_campaign(manifest)
    assert len(planned) == 3
    assert {(spec.geometry, spec.spin) for spec in planned} == set(EXPECTED_CASES)
    assert all(spec.spin == 7 for spec in planned)


def test_plan_campaign_preserves_manifest_order():
    manifest = load_manifest()
    planned = plan_campaign(manifest)
    assert tuple((spec.geometry, spec.spin) for spec in planned) == tuple(
        (case.geometry, case.spin) for case in manifest.cases
    )


def test_plan_campaign_rejects_a_manifest_missing_a_case():
    manifest = load_manifest()
    object.__setattr__(manifest, "cases", manifest.cases[:2])
    with pytest.raises(ValueError):
        plan_campaign(manifest)


def test_plan_campaign_rejects_spin_8():
    manifest = load_manifest()
    bad_case = manifest.cases[0]
    object.__setattr__(bad_case, "spin", 8)
    object.__setattr__(manifest, "cases", (bad_case,) + manifest.cases[1:])
    with pytest.raises(ValueError):
        plan_campaign(manifest)


def test_plan_campaign_rejects_an_extra_geometry():
    manifest = load_manifest()
    from experiments.level3.s7_manifest import Level3S7ManifestCase

    extra = Level3S7ManifestCase(geometry="triangle", spin=7)
    object.__setattr__(manifest, "cases", manifest.cases + (extra,))
    with pytest.raises(ValueError):
        plan_campaign(manifest)
