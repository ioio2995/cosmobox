"""Unit tests for experiments.level3.manifest (lot L3-I-S4-CAMPAIGN-INFRASTRUCTURE).

Exercises the real, frozen experiments/level3/preregistered-s4-manifest-v1.json
(pure JSON loading + schema validation -- no diagonalization, no physics),
plus synthetic raw dicts for fingerprint/rejection behavior.
"""

from __future__ import annotations

import json

import pytest

from experiments.level3.manifest import (
    CONTROL_METRICS,
    EXPECTED_S4_DIMENSIONS,
    GEOMETRIES,
    PRIMARY_METRICS,
    SPIN,
    VALIDATED_DENSE_CAPABILITY,
    Level2ReferenceIdentity,
    Level3Manifest,
    Level3ManifestCase,
    load_manifest,
    load_manifest_json,
    parse_manifest,
)


def _raw_manifest() -> dict:
    return json.loads(json.dumps(load_manifest_json()))


# ---------------------------------------------------------------------------
# The real frozen manifest
# ---------------------------------------------------------------------------


def test_load_manifest_loads_and_validates_the_real_frozen_manifest():
    manifest = load_manifest()
    assert isinstance(manifest, Level3Manifest)
    assert manifest.manifest_version == "level3-s4-reference-v1"
    assert manifest.frozen_preregistration_commit == "1c1d71f07dd6a7399b3965b2bb0acfa5c665991e"
    assert manifest.full_spectrum_required is True
    assert manifest.primary_contrast == "HIGH_MINUS_LOW"


def test_frozen_manifest_covers_exactly_the_three_cases_in_deterministic_order():
    manifest = load_manifest()
    combos = tuple((case.geometry, case.spin) for case in manifest.cases)
    assert combos == tuple((geometry, SPIN) for geometry in GEOMETRIES)
    assert len(manifest.cases) == 3


def test_frozen_manifest_numerical_guard_reference_matches_l2_c1():
    manifest = load_manifest()
    assert manifest.numerical_guard_reference.guard_m_tt == 1e-16
    assert manifest.numerical_guard_reference.guard_r_eff == 1e-15
    assert manifest.numerical_guard_reference.guard_scope == "DELTA_HL_ONLY"


def test_frozen_manifest_pins_the_level2_reference_identity():
    manifest = load_manifest()
    assert manifest.level2_reference.campaign_id == "level2-energy-regime-v1"
    assert manifest.level2_reference.manifest_fingerprint == (
        "82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4"
    )
    assert manifest.level2_reference.repository_commit == "1feb03f41f9e73078efbc760dd2cba2b667e2ed0"
    assert manifest.level2_reference.frozen_preregistration_commit == "2d4c859db7939da51ee7d919889a18f4c7e229ed"


def test_frozen_manifest_expected_s4_dimensions_and_capability():
    manifest = load_manifest()
    assert manifest.expected_s4_dimensions == EXPECTED_S4_DIMENSIONS == {"triangle": 168, "ring4": 572, "ring5": 2008}
    assert manifest.validated_dense_capability == VALIDATED_DENSE_CAPABILITY == 2008


def test_frozen_manifest_physical_parameters_match_the_frozen_contract():
    manifest = load_manifest()
    physical = manifest.physical_parameters
    assert physical.n_flavors == 2
    assert physical.j == 1.0
    assert physical.h == 0.0
    assert physical.t == 1.0
    assert physical.g_e == 1.0
    assert physical.k == 1.0
    assert physical.external_charges == 0.0


def test_frozen_manifest_forbids_s5():
    manifest = load_manifest()
    assert "S5" in manifest.forbidden_extensions


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_is_deterministic():
    raw = _raw_manifest()
    first = parse_manifest(raw).fingerprint
    second = parse_manifest(json.loads(json.dumps(raw))).fingerprint
    assert first == second


def test_fingerprint_is_independent_of_key_order():
    raw = _raw_manifest()
    reordered = json.loads(json.dumps(raw))
    reordered_reversed = dict(reversed(list(reordered.items())))
    assert parse_manifest(raw).fingerprint == parse_manifest(reordered_reversed).fingerprint


def test_fingerprint_changes_when_normative_content_changes():
    raw = _raw_manifest()
    mutated = json.loads(json.dumps(raw))
    mutated["campaign_id"] = "level3-s4-truncation-extension-v1-mutated"
    assert parse_manifest(raw).fingerprint != parse_manifest(mutated).fingerprint


# ---------------------------------------------------------------------------
# Schema rejection (synthetic mutations of the real manifest)
# ---------------------------------------------------------------------------


def test_schema_rejects_missing_case(tmp_path):
    raw = _raw_manifest()
    raw["cases"] = raw["cases"][:2]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_schema_rejects_duplicate_case(tmp_path):
    raw = _raw_manifest()
    raw["cases"] = [raw["cases"][0], raw["cases"][0], raw["cases"][1]]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_schema_rejects_spin_5(tmp_path):
    raw = _raw_manifest()
    raw["cases"][0]["spin"] = 5
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_schema_rejects_unknown_geometry(tmp_path):
    raw = _raw_manifest()
    raw["cases"][0]["geometry"] = "hexagon"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_schema_rejects_wrong_level2_reference_identity(tmp_path):
    raw = _raw_manifest()
    raw["level2_reference"]["repository_commit"] = "f" * 40
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_schema_rejects_widened_numerical_guard(tmp_path):
    raw = _raw_manifest()
    raw["numerical_guard_reference"]["guard_m_tt"] = 1e-10
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_parse_manifest_rejects_non_deterministic_case_order():
    raw = _raw_manifest()
    raw["cases"] = list(reversed(raw["cases"]))
    with pytest.raises(ValueError):
        parse_manifest(raw)


# ---------------------------------------------------------------------------
# Level3ManifestCase / Level2ReferenceIdentity direct construction
# ---------------------------------------------------------------------------


def test_level3_manifest_case_rejects_out_of_contract_geometry():
    with pytest.raises(ValueError):
        Level3ManifestCase(geometry="hexagon", spin=4)


def test_level3_manifest_case_rejects_spin_other_than_4():
    with pytest.raises(ValueError):
        Level3ManifestCase(geometry="triangle", spin=5)
    with pytest.raises(ValueError):
        Level3ManifestCase(geometry="triangle", spin=3)


def test_level2_reference_identity_rejects_wrong_manifest_fingerprint():
    with pytest.raises(ValueError):
        Level2ReferenceIdentity(
            campaign_id="level2-energy-regime-v1",
            manifest_fingerprint="0" * 64,
            repository_commit="1feb03f41f9e73078efbc760dd2cba2b667e2ed0",
            frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
        )
