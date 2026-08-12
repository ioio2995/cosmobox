"""Unit tests for scripts.level2_campaign.planning (lot
L2-E-CAMPAIGN-INFRASTRUCTURE). Uses the real, frozen manifest (pure JSON
loading, no diagonalization) and hand-mutated copies of it.
"""

from __future__ import annotations

import pytest

from cosmobox.level2.execution import build_all_reference_case_specs
from experiments.level2.manifest import load_manifest
from scripts.level2_campaign.planning import plan_campaign


def test_plan_campaign_matches_build_all_reference_case_specs_exactly():
    manifest = load_manifest()
    planned = plan_campaign(manifest)
    expected = build_all_reference_case_specs()
    assert planned == expected


def test_plan_campaign_preserves_manifest_order():
    manifest = load_manifest()
    planned = plan_campaign(manifest)
    assert tuple((spec.geometry, spec.spin) for spec in planned) == tuple(
        (case.geometry, case.spin) for case in manifest.cases
    )


def test_plan_campaign_rejects_a_manifest_missing_a_case():
    # Level2Manifest.__post_init__ already refuses an incomplete case
    # list on construction, so the only way to exercise plan_campaign's
    # own, independent cross-check against
    # execution.build_all_reference_case_specs() is to bypass the frozen
    # dataclass directly -- the same object.__setattr__ pattern already
    # established elsewhere in this project for testing an inner
    # invariant in isolation.
    manifest = load_manifest()
    object.__setattr__(manifest, "cases", manifest.cases[:5])
    with pytest.raises(ValueError):
        plan_campaign(manifest)
