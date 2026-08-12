"""Unit tests for experiments.level2.manifest (lot L2-E-CAMPAIGN-INFRASTRUCTURE).

Exercises the real, frozen experiments/level2/preregistered-manifest-v1.json
(pure JSON loading + schema validation -- no diagonalization, no physics),
plus synthetic raw dicts for fingerprint/rejection behavior.
"""

from __future__ import annotations

import copy
import json

import pytest

from experiments.level1.manifest import compute_manifest_fingerprint
from experiments.level2.manifest import (
    CONTROL_METRICS,
    GEOMETRIES,
    PRIMARY_METRICS,
    SPINS,
    Level2Manifest,
    Level2ManifestCase,
    load_manifest,
    load_manifest_json,
    parse_manifest,
)


def _raw_manifest() -> dict:
    # A fresh copy of the real, frozen manifest content -- never mutate
    # the module-level cache load_manifest_json returns.
    return json.loads(json.dumps(load_manifest_json()))


# ---------------------------------------------------------------------------
# The real frozen manifest
# ---------------------------------------------------------------------------


def test_load_manifest_loads_and_validates_the_real_frozen_manifest():
    manifest = load_manifest()
    assert isinstance(manifest, Level2Manifest)
    assert manifest.manifest_version == "level2-reference-v1"
    assert manifest.frozen_preregistration_commit == "2d4c859db7939da51ee7d919889a18f4c7e229ed"
    assert manifest.full_spectrum_required is True
    assert manifest.primary_metrics == PRIMARY_METRICS
    assert manifest.control_metrics == CONTROL_METRICS
    assert manifest.primary_contrast == "HIGH_MINUS_LOW"


def test_frozen_manifest_covers_exactly_the_six_cases_in_deterministic_order():
    manifest = load_manifest()
    expected_order = tuple((geometry, spin) for geometry in GEOMETRIES for spin in SPINS)
    actual_order = tuple((case.geometry, case.spin) for case in manifest.cases)
    assert actual_order == expected_order


def test_frozen_manifest_numerical_guard_reference_matches_l2_c1():
    manifest = load_manifest()
    assert manifest.numerical_guard_reference.guard_m_tt == 1e-16
    assert manifest.numerical_guard_reference.guard_r_eff == 1e-15
    assert manifest.numerical_guard_reference.guard_scope == "DELTA_HL_ONLY"


def test_frozen_manifest_inter_s_policy_matches_l2_d3_arbitration():
    manifest = load_manifest()
    assert set(manifest.inter_s_policy.primary) == {"taxonomy", "C_X_23", "D_X_23"}
    assert manifest.inter_s_policy.control == "descriptive_only"


# ---------------------------------------------------------------------------
# No physical degree of freedom in the manifest schema/type
# ---------------------------------------------------------------------------


def test_manifest_carries_no_physical_hamiltonian_parameter():
    raw = _raw_manifest()
    forbidden = {"n_flavors", "J", "h", "t", "g_E", "K", "external_charges", "hamiltonian_params"}
    assert set(raw.keys()) & forbidden == set()

    import dataclasses

    field_names = {field.name for field in dataclasses.fields(Level2Manifest)}
    assert field_names & forbidden == set()


# ---------------------------------------------------------------------------
# Fingerprint: deterministic, order-stable, content-sensitive
# ---------------------------------------------------------------------------


def test_fingerprint_is_deterministic():
    raw = _raw_manifest()
    assert compute_manifest_fingerprint(raw) == compute_manifest_fingerprint(json.loads(json.dumps(raw)))


def test_fingerprint_is_independent_of_key_order():
    raw = _raw_manifest()
    reordered = json.loads(json.dumps(raw))  # re-parse preserves top-level order as written
    # Build a dict with reversed top-level key insertion order -- same content
    reversed_raw = dict(reversed(list(reordered.items())))
    assert compute_manifest_fingerprint(raw) == compute_manifest_fingerprint(reversed_raw)


def test_fingerprint_changes_when_normative_content_changes():
    raw = _raw_manifest()
    mutated = copy.deepcopy(raw)
    mutated["primary_contrast"] = "LOW_MINUS_HIGH"
    assert compute_manifest_fingerprint(raw) != compute_manifest_fingerprint(mutated)


# ---------------------------------------------------------------------------
# Schema validation rejects off-contract manifests
# ---------------------------------------------------------------------------


def test_schema_rejects_extra_physical_parameter(tmp_path):
    raw = _raw_manifest()
    raw["n_flavors"] = 2
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest_json(path)


def test_schema_rejects_missing_case(tmp_path):
    raw = _raw_manifest()
    raw["cases"] = raw["cases"][:5]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest_json(path)


def test_schema_rejects_duplicate_case(tmp_path):
    raw = _raw_manifest()
    raw["cases"] = [raw["cases"][0]] * 6
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest_json(path)


def test_schema_rejects_widened_numerical_guard(tmp_path):
    raw = _raw_manifest()
    raw["numerical_guard_reference"]["guard_m_tt"] = 1e-10
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        load_manifest_json(path)


# ---------------------------------------------------------------------------
# parse_manifest rejects a wrong case order even if individually valid
# ---------------------------------------------------------------------------


def test_parse_manifest_rejects_non_deterministic_case_order():
    raw = _raw_manifest()
    raw["cases"] = list(reversed(raw["cases"]))
    with pytest.raises(ValueError, match="geometry-major"):
        parse_manifest(raw)


def test_level2_manifest_case_rejects_out_of_contract_geometry():
    with pytest.raises(ValueError):
        Level2ManifestCase(geometry="ring6", spin=2)


def test_level2_manifest_case_rejects_out_of_contract_spin():
    with pytest.raises(ValueError):
        Level2ManifestCase(geometry="triangle", spin=1)
