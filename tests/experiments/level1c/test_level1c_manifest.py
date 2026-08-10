from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from experiments.level1c import manifest as m


def _raw() -> dict:
    return m.load_manifest_json()


def _assert_invalid(raw: dict) -> None:
    errors = list(m._validator().iter_errors(raw))
    assert errors, "expected the manifest to be rejected by its schema"


# ---------------------------------------------------------------------------
# Schema well-formedness / validation / rejection
# ---------------------------------------------------------------------------


def test_manifest_schema_is_a_well_formed_draft202012_schema() -> None:
    Draft202012Validator.check_schema(m._load_schema())


def test_manifest_json_validates_against_its_schema() -> None:
    raw = _raw()
    assert raw["schema_version"] == "level1c-result-record-v1"
    assert raw["manifest_version"] == "level1c-campaign-manifest-v1"
    assert raw["campaign_id"] == "level1c-j0-response-v1"


def test_manifest_rejects_unknown_top_level_property() -> None:
    raw = _raw()
    raw["unexpected_field"] = 1
    _assert_invalid(raw)


def test_manifest_rejects_wrong_campaign_id() -> None:
    raw = _raw()
    raw["campaign_id"] = "something-else"
    _assert_invalid(raw)


def test_manifest_rejects_ring4_geometry() -> None:
    raw = _raw()
    raw["grid"][0]["geometry"] = "ring4"
    _assert_invalid(raw)


def test_manifest_rejects_spin_1() -> None:
    raw = _raw()
    raw["grid"][0]["spin"] = 1
    _assert_invalid(raw)


def test_manifest_rejects_two_hamiltonian_case_ids_on_one_grid_point() -> None:
    raw = _raw()
    raw["grid"][0]["hamiltonian_case_ids"] = ["j0-0.50", "j0-0.75"]
    _assert_invalid(raw)


def test_manifest_rejects_19_grid_points() -> None:
    raw = _raw()
    raw["grid"].pop()
    _assert_invalid(raw)


def test_manifest_rejects_unknown_role() -> None:
    raw = _raw()
    raw["target_groups"]["triangle"][2]["role"] = "OPTIONAL"
    _assert_invalid(raw)


def test_manifest_rejects_role_inferred_shortcut_missing_field() -> None:
    raw = _raw()
    del raw["target_groups"]["triangle"][0]["role"]
    _assert_invalid(raw)


def test_manifest_rejects_recalibrated_tolerance() -> None:
    raw = _raw()
    raw["non_regression_calibration"]["ctt_abs_tol"] = 1e-10
    _assert_invalid(raw)


def test_manifest_rejects_wrong_calibration_artifact_sha256() -> None:
    raw = _raw()
    raw["non_regression_calibration"]["calibration_artifact_sha256"] = "0" * 64
    _assert_invalid(raw)


def test_manifest_rejects_j_override_on_a_node_other_than_zero() -> None:
    raw = _raw()
    raw["hamiltonian_cases"][0]["J_override"]["node_index"] = 1
    _assert_invalid(raw)


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_is_stable_under_key_reordering() -> None:
    raw = _raw()
    reordered = json.loads(json.dumps(raw))
    shuffled = dict(reversed(list(reordered.items())))
    assert m.compute_manifest_fingerprint(raw) == m.compute_manifest_fingerprint(shuffled)


def test_fingerprint_changes_when_a_j0_value_changes() -> None:
    raw = _raw()
    baseline = m.compute_manifest_fingerprint(raw)
    mutated = copy.deepcopy(raw)
    mutated["hamiltonian_cases"][0]["J_override"]["value"] = 0.6
    assert m.compute_manifest_fingerprint(mutated) != baseline


def test_load_manifest_fingerprint_matches_compute_manifest_fingerprint() -> None:
    manifest = m.load_manifest()
    assert manifest.fingerprint == m.compute_manifest_fingerprint(manifest.raw)


# ---------------------------------------------------------------------------
# Structural counts (governance-mandated: 20/4/16/16/70)
# ---------------------------------------------------------------------------


def test_manifest_has_exactly_20_grid_points() -> None:
    manifest = m.load_manifest()
    assert len(manifest.grid) == 20


def test_manifest_has_exactly_5_hamiltonian_cases() -> None:
    manifest = m.load_manifest()
    assert len(manifest.hamiltonian_cases) == 5
    assert {case.hamiltonian_case_id for case in manifest.hamiltonian_cases} == {
        m.hamiltonian_case_id_for_j0(j0) for j0 in m.J0_GRID
    }


def test_manifest_grid_covers_exactly_triangle_and_ring5() -> None:
    manifest = m.load_manifest()
    assert {gp.geometry for gp in manifest.grid} == set(m.GEOMETRIES)


def test_manifest_grid_covers_exactly_spin_2_and_3() -> None:
    manifest = m.load_manifest()
    assert {gp.spin for gp in manifest.grid} == set(m.SPIN_VALUES)


def test_manifest_target_outcomes_count_is_70() -> None:
    """4 targets x 10 triangle cases + 4 targets x 10 ring5 cases = 70
    (identifiability-preregistration.md section 19.10, confirmed by the
    accepted preflight result)."""
    manifest = m.load_manifest()
    triangle_cases = sum(1 for gp in manifest.grid if gp.geometry == "triangle")
    ring5_cases = sum(1 for gp in manifest.grid if gp.geometry == "ring5")
    total = triangle_cases * len(manifest.target_groups["triangle"]) + ring5_cases * len(manifest.target_groups["ring5"])
    assert total == 70


def test_production_windows_match_frozen_table() -> None:
    manifest = m.load_manifest()
    m.validate_production_windows_match_frozen_table(manifest)


def test_production_window_mismatch_is_detected() -> None:
    raw = _raw()
    mutated = copy.deepcopy(raw)
    mutated["grid"][0]["spectral_window"] = 999
    manifest = m.parse_manifest(mutated)
    with pytest.raises(ValueError, match="does not match the frozen production_window"):
        m.validate_production_windows_match_frozen_table(manifest)


# ---------------------------------------------------------------------------
# TargetRole / Level1CTargetSpec (1C-8a-fix)
# ---------------------------------------------------------------------------


def test_t_max_is_calibration_only_but_requires_complete_multiplet_if_selected() -> None:
    manifest = m.load_manifest()
    for geometry in m.GEOMETRIES:
        t_max = next(spec for spec in manifest.target_groups[geometry] if spec.target.target_id == "T_max")
        assert t_max.role == m.CALIBRATION_ONLY
        assert t_max.target.required_spectral_status == "complete_multiplet"


def test_t_3_2_is_required() -> None:
    manifest = m.load_manifest()
    t_3_2 = next(spec for spec in manifest.target_groups["ring5"] if spec.target.target_id == "T_3_2")
    assert t_3_2.role == m.REQUIRED


def test_fundamental_and_first_excited_are_required_for_both_geometries() -> None:
    manifest = m.load_manifest()
    for geometry in m.GEOMETRIES:
        for target_id in ("fundamental", "first_excited"):
            spec = next(spec for spec in manifest.target_groups[geometry] if spec.target.target_id == target_id)
            assert spec.role == m.REQUIRED


def test_level1c_target_spec_rejects_unknown_role() -> None:
    from experiments.level1.manifest import TargetGroupSpec

    target = TargetGroupSpec(
        target_id="fundamental",
        selection_kind="fundamental",
        target_twice_T=None,
        selection_within_label=None,
        required_spectral_status="complete_multiplet",
        requires_inter_s_exact_match=False,
    )
    with pytest.raises(ValueError, match="role must be one of"):
        m.Level1CTargetSpec(target=target, role="SOMETIMES")


# ---------------------------------------------------------------------------
# Non-regression calibration provenance block
# ---------------------------------------------------------------------------


def test_non_regression_calibration_matches_the_accepted_artifact() -> None:
    manifest = m.load_manifest()
    calibration = manifest.non_regression_calibration
    assert calibration.calibration_artifact_sha256 == "05aa2e9d77c1314926350f8202e620b7537bdf9f6a7bab12a232151e9cf68da6"
    assert calibration.code_commit == "1f06ef91c1157389df7d325cb825ce7508eff52f"
    assert calibration.contract_version == "level1c-nonregression-calibration-v2"
    assert calibration.ctt_abs_tol == 1e-15
    assert calibration.rho_abs_tol == 1e-15


def test_non_regression_calibration_rejects_a_different_hash() -> None:
    from experiments.level1c.manifest import NonRegressionCalibrationSpec

    with pytest.raises(ValueError, match="calibration_artifact_sha256"):
        NonRegressionCalibrationSpec(
            calibration_artifact_sha256="0" * 64,
            code_commit="1f06ef91c1157389df7d325cb825ce7508eff52f",
            contract_version="level1c-nonregression-calibration-v2",
            ctt_abs_tol=1e-15,
            rho_abs_tol=1e-15,
        )


# ---------------------------------------------------------------------------
# Manifest never modifies Level1B
# ---------------------------------------------------------------------------


def test_level1c_manifest_is_never_an_instance_of_the_level1b_manifest_class() -> None:
    from experiments.level1.manifest import Manifest as Level1BManifest

    manifest = m.load_manifest()
    assert not isinstance(manifest, Level1BManifest)


def test_level1b_manifest_still_loads_unmodified() -> None:
    from experiments.level1.manifest import load_manifest as load_level1b_manifest

    level1b_manifest = load_level1b_manifest()
    assert level1b_manifest.manifest_version == "level1b-reference-v1"
    assert level1b_manifest.campaign_id == "level1b-reference-v1"
