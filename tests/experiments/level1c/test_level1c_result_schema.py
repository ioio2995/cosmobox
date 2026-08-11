from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator

from experiments.level1c.result_schema import _load_schema, validate_result_record


def test_schema_is_a_well_formed_draft202012_schema() -> None:
    Draft202012Validator.check_schema(_load_schema())


def _base_identity() -> dict:
    return {
        "geometry": "triangle",
        "spin": 2,
        "n_flavors": 2,
        "hamiltonian": {"J": [1.0, 1.0, 0.5], "h_is_zero": True, "t": 1.0, "g_E": 1.0, "K": 1.0},
        "sector": "default",
        "spectral_group": {
            "status": "complete_multiplet",
            "multiplicity": 1,
            "twice_T": 0,
            "spectral_window_group_index": 0,
            "group_start_index": 0,
            "group_end_index_exclusive": 1,
            "representative_energy": -1.5,
        },
        "path": [0, 1],
        "flavor_component": None,
        "normalization": None,
    }


def _base_provenance() -> dict:
    return {
        "spectral_status": "complete_multiplet",
        "source_type": "raw_observable",
        "source_module": "runner",
        "scientific_seed": 0,
        "solver_seed": 0,
        "validation_rotation_seed": None,
    }


def _ctt_document() -> dict:
    return {
        "schema_version": "level1c-result-record-v1",
        "repository_commit": "1f06ef91c1157389df7d325cb825ce7508eff52f",
        "manifest_fingerprint": "31e4c94f1758b426ef3ac05ecbc287ad7291d0b34b9a0c1329f5b746e22944e5",
        "campaign_id": "level1c-j0-response-v1",
        "identity": _base_identity(),
        "provenance": _base_provenance(),
        "record_kind": "raw_observable",
        "observable_kind": "C_TT_conn",
        "payload": 0.25,
    }


# ---------------------------------------------------------------------------
# Valid documents
# ---------------------------------------------------------------------------


def test_valid_ctt_document_is_accepted() -> None:
    validate_result_record(_ctt_document())


def test_valid_rho_document_is_accepted() -> None:
    document = _ctt_document()
    document["record_kind"] = "normalized_observable"
    document["observable_kind"] = "rho_QQ"
    document["payload"] = {"value": -0.5, "null_reason": None}
    validate_result_record(document)


def test_valid_null_rho_document_is_accepted() -> None:
    document = _ctt_document()
    document["record_kind"] = "normalized_observable"
    document["observable_kind"] = "rho_QQ"
    document["payload"] = {"value": None, "null_reason": "zero_local_charge_variance"}
    validate_result_record(document)


def test_valid_symmetry_label_document_is_accepted() -> None:
    document = _ctt_document()
    document["record_kind"] = "symmetry_label"
    document["observable_kind"] = "reflection_character"
    document["identity"] = dict(document["identity"])
    document["identity"]["path"] = None
    document["payload"] = {"kind": "numeric", "value": {"real": 1.0, "imag": 0.0}}
    validate_result_record(document)


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------


def test_rejects_ring4_geometry() -> None:
    document = _ctt_document()
    document["identity"] = copy.deepcopy(document["identity"])
    document["identity"]["geometry"] = "ring4"
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_rejects_spin_1() -> None:
    document = _ctt_document()
    document["identity"] = copy.deepcopy(document["identity"])
    document["identity"]["spin"] = 1
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_rejects_missing_group_start_index() -> None:
    document = _ctt_document()
    document["identity"] = copy.deepcopy(document["identity"])
    document["identity"]["spectral_group"] = copy.deepcopy(document["identity"]["spectral_group"])
    del document["identity"]["spectral_group"]["group_start_index"]
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_rejects_missing_group_end_index_exclusive() -> None:
    document = _ctt_document()
    document["identity"] = copy.deepcopy(document["identity"])
    document["identity"]["spectral_group"] = copy.deepcopy(document["identity"]["spectral_group"])
    del document["identity"]["spectral_group"]["group_end_index_exclusive"]
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_rejects_wrong_schema_version() -> None:
    document = _ctt_document()
    document["schema_version"] = "level1-correlators-v2"
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_rejects_wrong_campaign_id() -> None:
    document = _ctt_document()
    document["campaign_id"] = "level1b-reference-v1"
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_rejects_level1b_only_record_kind() -> None:
    document = _ctt_document()
    document["record_kind"] = "matching"
    document["observable_kind"] = "C_TT_conn"
    document["payload"] = {"status": "structurally_not_applicable", "matched_group": None}
    with pytest.raises(ValueError):
        validate_result_record(document)


# ---------------------------------------------------------------------------
# target_selection is deliberately never accepted here (1C-8b-fix):
# a target-selection outcome is a case-level concept (possibly with no
# selected group at all), never a ResultRecord tied to a real
# identity.spectral_group. It belongs exclusively to
# schemas/level1c/case-run-v1.schema.json (see test_level1c_case_artifact.py).
# ---------------------------------------------------------------------------


def test_target_selection_record_kind_is_rejected_even_with_a_real_spectral_group() -> None:
    """Even when identity.spectral_group is a perfectly well-formed real
    group (as if a fake one had been fabricated to carry a resolved
    selection), record_kind='target_selection' must still be rejected:
    the record_kind itself no longer exists in this schema, regardless
    of how identity is populated."""
    document = _ctt_document()
    document["record_kind"] = "target_selection"
    document["observable_kind"] = "target_selection"
    document["payload"] = {
        "target_id": "T_max",
        "role": "CALIBRATION_ONLY",
        "selection_status": "selected",
        "spectral_window_group_index": 3,
        "selected_group_status": "partial_subspace",
        "meets_normative_requirements": False,
    }
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_target_selection_observable_kind_is_rejected() -> None:
    document = _ctt_document()
    document["observable_kind"] = "target_selection"
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_schema_has_no_target_selection_record_definition() -> None:
    schema = _load_schema()
    assert "targetSelectionRecord" not in schema.get("$defs", {})
    assert "target_selection" not in schema["properties"]["record_kind"]["enum"]
    assert "target_selection" not in schema["properties"]["observable_kind"]["enum"]
