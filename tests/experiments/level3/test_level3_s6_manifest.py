"""Unit tests for experiments.level3.s6_manifest (lot L3-W-S6-CAMPAIGN-INFRASTRUCTURE).

Exercises the real, frozen experiments/level3/preregistered-s6-manifest-v1.json
(pure JSON loading + schema validation -- no diagonalization, no physics),
plus synthetic raw dicts for fingerprint/rejection behavior. Also confirms
the historical S4 and S5 manifest fingerprints are unaffected by this
module's existence (experiments/level3/manifest.py and
experiments/level3/s5_manifest.py are never imported or modified here).
"""

from __future__ import annotations

import json

import pytest

from experiments.level3.s6_manifest import (
    CONTROL_METRICS,
    EXPECTED_S6_DIMENSIONS,
    GEOMETRIES,
    PRIMARY_METRICS,
    SPIN,
    VALIDATED_DENSE_CAPABILITY,
    Level2ReferenceIdentity,
    Level3S4ReferenceIdentity,
    Level3S5ReferenceIdentity,
    Level3S6Manifest,
    Level3S6ManifestCase,
    load_manifest,
    load_manifest_json,
    parse_manifest,
)

S4_HISTORICAL_FINGERPRINT = "3498677a4addc9c62c5e9c220cedb0dca135c9b293eee205420dcbce346d7cba"
S5_HISTORICAL_FINGERPRINT = "3160a8e6e0f9ae4a21c027a865e4d56527303ad644e3f45137baa2120f0c5d04"


def _raw_manifest() -> dict:
    return json.loads(json.dumps(load_manifest_json()))


# ---------------------------------------------------------------------------
# The real frozen manifest
# ---------------------------------------------------------------------------


def test_load_manifest_loads_and_validates_the_real_frozen_manifest():
    manifest = load_manifest()
    assert isinstance(manifest, Level3S6Manifest)
    assert manifest.manifest_version == "level3-s6-reference-v1"
    assert manifest.frozen_preregistration_commit == "1c19a01e051c3df6f547afe0816a795989fdac3b"
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


def test_frozen_manifest_pins_the_level3_s4_reference_identity():
    manifest = load_manifest()
    assert manifest.level3_s4_reference.campaign_id == "level3-s4-truncation-extension-v1"
    assert manifest.level3_s4_reference.manifest_fingerprint == S4_HISTORICAL_FINGERPRINT
    assert manifest.level3_s4_reference.repository_commit == "ffb49da84111f778e45aa95b6d9e80b45d68f34c"
    assert manifest.level3_s4_reference.frozen_preregistration_commit == "1c1d71f07dd6a7399b3965b2bb0acfa5c665991e"


def test_frozen_manifest_pins_the_level3_s5_reference_identity():
    manifest = load_manifest()
    assert manifest.level3_s5_reference.campaign_id == "level3-s5-truncation-extension-v1"
    assert manifest.level3_s5_reference.manifest_fingerprint == S5_HISTORICAL_FINGERPRINT
    assert manifest.level3_s5_reference.repository_commit == "782f29eb9dcbc21ca2168e109997b0f59a12402f"
    assert manifest.level3_s5_reference.frozen_preregistration_commit == "496ba9484a6d7df9beb738607a5ffe23a75219ad"


def test_frozen_manifest_expected_s6_dimensions_and_capability():
    manifest = load_manifest()
    assert manifest.expected_s6_dimensions == EXPECTED_S6_DIMENSIONS == {"triangle": 248, "ring4": 852, "ring5": 3016}
    assert manifest.validated_dense_capability == VALIDATED_DENSE_CAPABILITY == 3016


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


def test_frozen_manifest_forbids_s7():
    manifest = load_manifest()
    assert "S7" in manifest.forbidden_extensions


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
    mutated["campaign_id"] = "level3-s6-truncation-extension-v1-mutated"
    assert parse_manifest(raw).fingerprint != parse_manifest(mutated).fingerprint


def test_s4_historical_fingerprint_unchanged_by_s6_manifest_module():
    # experiments/level3/manifest.py (the S4 manifest loader) is never
    # imported by this module -- verified by loading it independently
    # here and confirming the frozen S4 fingerprint is exactly what L3-I
    # produced, unaffected by s6_manifest.py's existence.
    from experiments.level3.manifest import load_manifest as load_s4_manifest

    s4_manifest = load_s4_manifest()
    assert s4_manifest.fingerprint == S4_HISTORICAL_FINGERPRINT


def test_s5_historical_fingerprint_unchanged_by_s6_manifest_module():
    # experiments/level3/s5_manifest.py (the S5 manifest loader) is never
    # imported by this module -- verified by loading it independently
    # here and confirming the frozen S5 fingerprint is exactly what L3-P
    # produced, unaffected by s6_manifest.py's existence.
    from experiments.level3.s5_manifest import load_manifest as load_s5_manifest

    s5_manifest = load_s5_manifest()
    assert s5_manifest.fingerprint == S5_HISTORICAL_FINGERPRINT


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


def test_schema_rejects_spin_7(tmp_path):
    raw = _raw_manifest()
    raw["cases"][0]["spin"] = 7
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


def test_schema_rejects_wrong_level3_s4_reference_identity(tmp_path):
    raw = _raw_manifest()
    raw["level3_s4_reference"]["manifest_fingerprint"] = "f" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_schema_rejects_wrong_level3_s5_reference_identity(tmp_path):
    raw = _raw_manifest()
    raw["level3_s5_reference"]["manifest_fingerprint"] = "f" * 64
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
# Direct dataclass construction
# ---------------------------------------------------------------------------


def test_level3_s6_manifest_case_rejects_out_of_contract_geometry():
    with pytest.raises(ValueError):
        Level3S6ManifestCase(geometry="hexagon", spin=6)


def test_level3_s6_manifest_case_rejects_spin_other_than_6():
    with pytest.raises(ValueError):
        Level3S6ManifestCase(geometry="triangle", spin=7)
    with pytest.raises(ValueError):
        Level3S6ManifestCase(geometry="triangle", spin=5)


def test_level2_reference_identity_rejects_wrong_manifest_fingerprint():
    with pytest.raises(ValueError):
        Level2ReferenceIdentity(
            campaign_id="level2-energy-regime-v1",
            manifest_fingerprint="0" * 64,
            repository_commit="1feb03f41f9e73078efbc760dd2cba2b667e2ed0",
            frozen_preregistration_commit="2d4c859db7939da51ee7d919889a18f4c7e229ed",
        )


def test_level3_s4_reference_identity_rejects_wrong_repository_commit():
    with pytest.raises(ValueError):
        Level3S4ReferenceIdentity(
            campaign_id="level3-s4-truncation-extension-v1",
            manifest_fingerprint=S4_HISTORICAL_FINGERPRINT,
            repository_commit="0" * 40,
            frozen_preregistration_commit="1c1d71f07dd6a7399b3965b2bb0acfa5c665991e",
        )


def test_level3_s5_reference_identity_rejects_wrong_repository_commit():
    with pytest.raises(ValueError):
        Level3S5ReferenceIdentity(
            campaign_id="level3-s5-truncation-extension-v1",
            manifest_fingerprint=S5_HISTORICAL_FINGERPRINT,
            repository_commit="0" * 40,
            frozen_preregistration_commit="496ba9484a6d7df9beb738607a5ffe23a75219ad",
        )
