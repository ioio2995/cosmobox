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


def _target_selection_document(**payload_overrides) -> dict:
    document = _ctt_document()
    document["record_kind"] = "target_selection"
    document["observable_kind"] = "target_selection"
    payload = {
        "target_id": "T_max",
        "role": "CALIBRATION_ONLY",
        "selection_status": "selected",
        "spectral_window_group_index": 3,
        "selected_group_status": "partial_subspace",
        "meets_normative_requirements": False,
    }
    payload.update(payload_overrides)
    document["payload"] = payload
    return document


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


def test_valid_target_selection_document_selected_is_accepted() -> None:
    validate_result_record(_target_selection_document())


def test_valid_target_selection_document_not_selected_is_accepted() -> None:
    document = _target_selection_document(
        selection_status="not_in_window",
        spectral_window_group_index=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
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


def test_target_selection_selected_requires_group_fields() -> None:
    document = _target_selection_document(
        selection_status="selected",
        spectral_window_group_index=None,
        selected_group_status=None,
        meets_normative_requirements=None,
    )
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_target_selection_rejects_unknown_role() -> None:
    document = _target_selection_document(role="OPTIONAL")
    with pytest.raises(ValueError):
        validate_result_record(document)


def test_target_selection_rejects_unknown_selection_status() -> None:
    document = _target_selection_document(selection_status="found")
    with pytest.raises(ValueError):
        validate_result_record(document)
