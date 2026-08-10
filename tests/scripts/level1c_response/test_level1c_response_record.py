from __future__ import annotations

import pytest

from level1c_response_helpers import REPO_COMMIT

from scripts.level1c_response.response import (
    RESPONSE_AVAILABLE,
    RESPONSE_NOT_AVAILABLE,
    DeltaCTTPair,
    ResponseRecord,
    RhoPairControl,
    canonical_json_bytes,
    to_json_dict,
    validate_response_record_document,
)
from scripts.level1c_tracking.tracking import AMBIGUOUS as AMBIGUOUS_TRACKING_STATUS
from scripts.level1c_tracking.tracking import TRACKED_ONE_TO_ONE

_BASE_KWARGS = dict(
    schema_version="level1c-response-record-v1",
    campaign_id="level1c-j0-response-v1",
    repository_commit=REPO_COMMIT,
    manifest_fingerprint="fp",
    geometry="triangle",
    spin=2,
    baseline_case_id="baseline-case",
    perturbed_case_id="perturbed-case",
    baseline_hamiltonian_case_id="j0-1.00",
    perturbed_hamiltonian_case_id="j0-0.75",
    target_id="fundamental",
)


def _delta_pair() -> DeltaCTTPair:
    return DeltaCTTPair(i=0, j=1, baseline_value=0.5, perturbed_value=0.75, delta=0.25)


def _rho_control() -> RhoPairControl:
    return RhoPairControl(i=0, j=1, baseline_value=-0.5, baseline_null_reason=None, perturbed_value=-0.4, perturbed_null_reason=None)


def _available_record() -> ResponseRecord:
    return ResponseRecord(
        **_BASE_KWARGS,
        tracking_status=TRACKED_ONE_TO_ONE,
        response_eligibility=RESPONSE_AVAILABLE,
        baseline_group_index=0,
        perturbed_group_index=5,
        delta_ctt_pairs=(_delta_pair(),),
        rho_pair_controls=(_rho_control(),),
        failure_reasons=(),
    )


def test_delta_ctt_pair_self_consistency() -> None:
    with pytest.raises(ValueError, match="delta"):
        DeltaCTTPair(i=0, j=1, baseline_value=0.5, perturbed_value=0.75, delta=999.0)


def test_delta_ctt_pair_rejects_diagonal() -> None:
    with pytest.raises(ValueError, match="off-diagonal"):
        DeltaCTTPair(i=2, j=2, baseline_value=0.5, perturbed_value=0.75, delta=0.25)


def test_delta_ctt_pair_rejects_non_finite() -> None:
    with pytest.raises(ValueError):
        DeltaCTTPair(i=0, j=1, baseline_value=float("inf"), perturbed_value=0.75, delta=0.25)


def test_rho_pair_control_null_reason_pairing() -> None:
    with pytest.raises(ValueError, match="baseline_null_reason"):
        RhoPairControl(i=0, j=1, baseline_value=None, baseline_null_reason=None, perturbed_value=-0.4, perturbed_null_reason=None)


def test_rho_pair_control_allows_all_four_combinations() -> None:
    RhoPairControl(i=0, j=1, baseline_value=-0.5, baseline_null_reason=None, perturbed_value=-0.4, perturbed_null_reason=None)
    RhoPairControl(i=0, j=1, baseline_value=-0.5, baseline_null_reason=None, perturbed_value=None, perturbed_null_reason="zero_local_charge_variance")
    RhoPairControl(i=0, j=1, baseline_value=None, baseline_null_reason="zero_local_charge_variance", perturbed_value=-0.4, perturbed_null_reason=None)
    RhoPairControl(i=0, j=1, baseline_value=None, baseline_null_reason="x", perturbed_value=None, perturbed_null_reason="y")


def test_response_available_record_valid() -> None:
    record = _available_record()
    assert record.response_eligibility == RESPONSE_AVAILABLE


def test_response_available_requires_tracked_one_to_one() -> None:
    with pytest.raises(ValueError, match="TRACKED_ONE_TO_ONE"):
        ResponseRecord(
            **_BASE_KWARGS,
            tracking_status=AMBIGUOUS_TRACKING_STATUS,
            response_eligibility=RESPONSE_AVAILABLE,
            baseline_group_index=0,
            perturbed_group_index=5,
            delta_ctt_pairs=(_delta_pair(),),
            rho_pair_controls=(_rho_control(),),
            failure_reasons=(),
        )


def test_response_available_requires_group_indices() -> None:
    with pytest.raises(ValueError, match="group_index"):
        ResponseRecord(
            **_BASE_KWARGS,
            tracking_status=TRACKED_ONE_TO_ONE,
            response_eligibility=RESPONSE_AVAILABLE,
            baseline_group_index=None,
            perturbed_group_index=5,
            delta_ctt_pairs=(_delta_pair(),),
            rho_pair_controls=(_rho_control(),),
            failure_reasons=(),
        )


def test_response_available_requires_payloads() -> None:
    with pytest.raises(ValueError, match="delta_ctt_pairs"):
        ResponseRecord(
            **_BASE_KWARGS,
            tracking_status=TRACKED_ONE_TO_ONE,
            response_eligibility=RESPONSE_AVAILABLE,
            baseline_group_index=0,
            perturbed_group_index=5,
            delta_ctt_pairs=None,
            rho_pair_controls=(_rho_control(),),
            failure_reasons=(),
        )


def test_response_available_requires_empty_failure_reasons() -> None:
    with pytest.raises(ValueError, match="failure_reasons"):
        ResponseRecord(
            **_BASE_KWARGS,
            tracking_status=TRACKED_ONE_TO_ONE,
            response_eligibility=RESPONSE_AVAILABLE,
            baseline_group_index=0,
            perturbed_group_index=5,
            delta_ctt_pairs=(_delta_pair(),),
            rho_pair_controls=(_rho_control(),),
            failure_reasons=("oops",),
        )


def test_response_not_available_forbids_payloads() -> None:
    with pytest.raises(ValueError, match="partial scientific payload"):
        ResponseRecord(
            **_BASE_KWARGS,
            tracking_status=AMBIGUOUS_TRACKING_STATUS,
            response_eligibility=RESPONSE_NOT_AVAILABLE,
            baseline_group_index=None,
            perturbed_group_index=None,
            delta_ctt_pairs=(_delta_pair(),),
            rho_pair_controls=None,
            failure_reasons=("x",),
        )


def test_response_not_available_requires_nonempty_failure_reasons() -> None:
    with pytest.raises(ValueError, match="failure_reasons"):
        ResponseRecord(
            **_BASE_KWARGS,
            tracking_status=AMBIGUOUS_TRACKING_STATUS,
            response_eligibility=RESPONSE_NOT_AVAILABLE,
            baseline_group_index=None,
            perturbed_group_index=None,
            delta_ctt_pairs=None,
            rho_pair_controls=None,
            failure_reasons=(),
        )


def test_response_not_available_allows_diagnostic_group_indices() -> None:
    record = ResponseRecord(
        **_BASE_KWARGS,
        tracking_status=AMBIGUOUS_TRACKING_STATUS,
        response_eligibility=RESPONSE_NOT_AVAILABLE,
        baseline_group_index=0,
        perturbed_group_index=None,
        delta_ctt_pairs=None,
        rho_pair_controls=None,
        failure_reasons=("PERTURBED_UNAVAILABLE: x",),
    )
    assert record.baseline_group_index == 0
    assert record.delta_ctt_pairs is None


def test_to_json_dict_and_schema_validate_available() -> None:
    document = to_json_dict(_available_record())
    validate_response_record_document(document)
    assert document["response_eligibility"] == RESPONSE_AVAILABLE
    assert document["delta_ctt_pairs"] == [{"i": 0, "j": 1, "baseline_value": 0.5, "perturbed_value": 0.75, "delta": 0.25}]


def test_to_json_dict_and_schema_validate_not_available() -> None:
    record = ResponseRecord(
        **_BASE_KWARGS,
        tracking_status=AMBIGUOUS_TRACKING_STATUS,
        response_eligibility=RESPONSE_NOT_AVAILABLE,
        baseline_group_index=None,
        perturbed_group_index=None,
        delta_ctt_pairs=None,
        rho_pair_controls=None,
        failure_reasons=("TRACKING_STATUS_NOT_TRACKED_ONE_TO_ONE: AMBIGUOUS",),
    )
    document = to_json_dict(record)
    validate_response_record_document(document)
    assert document["delta_ctt_pairs"] is None
    assert document["rho_pair_controls"] is None


def test_canonical_json_bytes_deterministic() -> None:
    document = to_json_dict(_available_record())
    assert canonical_json_bytes(document) == canonical_json_bytes(dict(document))


def test_no_physical_verdict_or_incident_or_g_fields_in_schema() -> None:
    document = to_json_dict(_available_record())
    forbidden_substrings = ("physical", "incident", "significan", "gravity", "geometry_emerged", "response_score", "response_strength", "delta_rho", "ratio", "relative_change")
    for key in document:
        lowered = key.lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in lowered, f"unexpected field {key!r} suggests a forbidden concept ({forbidden!r})"
