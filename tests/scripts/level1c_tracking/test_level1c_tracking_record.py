from __future__ import annotations

import pytest
from cosmobox.level1.matching import SymmetryLabel

from level1c_tracking_helpers import REPO_COMMIT

from scripts.level1c_tracking.tracking import (
    AMBIGUOUS,
    NOT_AVAILABLE,
    TRACKED_ONE_TO_ONE,
    TrackingRecord,
    canonical_json_bytes,
    to_json_dict,
    validate_tracking_record_document,
)

NUMERIC_LABEL = SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))

_BASE_KWARGS = dict(
    schema_version="level1c-tracking-record-v1",
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


def _tracked_one_to_one_record() -> TrackingRecord:
    return TrackingRecord(
        **_BASE_KWARGS,
        baseline_group_index=0,
        baseline_multiplicity=1,
        baseline_twice_T=1,
        baseline_reflection_label=NUMERIC_LABEL,
        status=TRACKED_ONE_TO_ONE,
        candidate_group_index=3,
        candidate_multiplicity=1,
        candidate_twice_T=1,
        candidate_reflection_label=NUMERIC_LABEL,
        class_pool_size=1,
        failure_reasons=(),
    )


def test_tracked_one_to_one_record_valid() -> None:
    record = _tracked_one_to_one_record()
    assert record.status == TRACKED_ONE_TO_ONE


def test_tracked_one_to_one_requires_empty_failure_reasons() -> None:
    with pytest.raises(ValueError, match="failure_reasons"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
            status=TRACKED_ONE_TO_ONE,
            candidate_group_index=3, candidate_multiplicity=1, candidate_twice_T=1, candidate_reflection_label=NUMERIC_LABEL,
            class_pool_size=1, failure_reasons=("oops",),
        )


def test_tracked_one_to_one_requires_candidate_fields() -> None:
    with pytest.raises(ValueError, match="candidate_"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
            status=TRACKED_ONE_TO_ONE,
            candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
            class_pool_size=1, failure_reasons=(),
        )


def test_tracked_one_to_one_requires_class_pool_size_one() -> None:
    with pytest.raises(ValueError, match="class_pool_size"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
            status=TRACKED_ONE_TO_ONE,
            candidate_group_index=3, candidate_multiplicity=1, candidate_twice_T=1, candidate_reflection_label=NUMERIC_LABEL,
            class_pool_size=2, failure_reasons=(),
        )


def test_ambiguous_requires_nonempty_failure_reasons() -> None:
    with pytest.raises(ValueError, match="failure_reasons"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
            status=AMBIGUOUS,
            candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
            class_pool_size=2, failure_reasons=(),
        )


def test_ambiguous_forbids_candidate_fields() -> None:
    with pytest.raises(ValueError, match="candidate_"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
            status=AMBIGUOUS,
            candidate_group_index=3, candidate_multiplicity=1, candidate_twice_T=1, candidate_reflection_label=NUMERIC_LABEL,
            class_pool_size=2, failure_reasons=("CLASS_POOL_NOT_UNIQUE: size=2",),
        )


def test_not_available_valid_with_zero_pool() -> None:
    record = TrackingRecord(
        **_BASE_KWARGS,
        baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
        status=NOT_AVAILABLE,
        candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
        class_pool_size=0, failure_reasons=("CLASS_POOL_EMPTY",),
    )
    assert record.class_pool_size == 0


def test_baseline_unavailable_requires_all_baseline_fields_none_together() -> None:
    with pytest.raises(ValueError, match="baseline_group_index and baseline_multiplicity"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=None, baseline_multiplicity=1, baseline_twice_T=None, baseline_reflection_label=None,
            status=AMBIGUOUS,
            candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
            class_pool_size=None, failure_reasons=("BASELINE_UNAVAILABLE: x",),
        )


def test_baseline_unavailable_forbids_class_pool_size() -> None:
    with pytest.raises(ValueError, match="class_pool_size"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=None, baseline_multiplicity=None, baseline_twice_T=None, baseline_reflection_label=None,
            status=AMBIGUOUS,
            candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
            class_pool_size=0, failure_reasons=("BASELINE_UNAVAILABLE: x",),
        )


def test_baseline_twice_t_unresolved_but_group_known_is_allowed() -> None:
    """baseline_group_index/multiplicity/reflection_label known, but
    baseline_twice_T legitimately None (its own casimir label computation
    failed) -- a distinct, expected state, never conflated with
    BASELINE_UNAVAILABLE."""
    record = TrackingRecord(
        **_BASE_KWARGS,
        baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=None, baseline_reflection_label=NUMERIC_LABEL,
        status=AMBIGUOUS,
        candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
        class_pool_size=None, failure_reasons=("BASELINE_TWICE_T_UNRESOLVED",),
    )
    assert record.baseline_twice_T is None
    assert record.baseline_group_index == 0


def test_invalid_status_rejected() -> None:
    with pytest.raises(ValueError, match="status"):
        TrackingRecord(
            **_BASE_KWARGS,
            baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
            status="TRACKED_SPLIT_BRANCH",
            candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
            class_pool_size=None, failure_reasons=("x",),
        )


def test_to_json_dict_and_schema_validate_tracked_one_to_one() -> None:
    document = to_json_dict(_tracked_one_to_one_record())
    validate_tracking_record_document(document)
    assert document["status"] == TRACKED_ONE_TO_ONE
    assert document["candidate_reflection_label"] == {"kind": "numeric", "value": {"real": 1.0, "imag": 0.0}}


def test_to_json_dict_and_schema_validate_not_available() -> None:
    record = TrackingRecord(
        **_BASE_KWARGS,
        baseline_group_index=0, baseline_multiplicity=1, baseline_twice_T=1, baseline_reflection_label=NUMERIC_LABEL,
        status=NOT_AVAILABLE,
        candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
        class_pool_size=0, failure_reasons=("CLASS_POOL_EMPTY",),
    )
    document = to_json_dict(record)
    validate_tracking_record_document(document)
    assert document["candidate_group_index"] is None


def test_to_json_dict_and_schema_validate_baseline_unavailable() -> None:
    record = TrackingRecord(
        **_BASE_KWARGS,
        baseline_group_index=None, baseline_multiplicity=None, baseline_twice_T=None, baseline_reflection_label=None,
        status=AMBIGUOUS,
        candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label=None,
        class_pool_size=None, failure_reasons=("BASELINE_UNAVAILABLE: x",),
    )
    document = to_json_dict(record)
    validate_tracking_record_document(document)
    assert document["baseline_reflection_label"] is None
    assert document["class_pool_size"] is None


def test_canonical_json_bytes_deterministic() -> None:
    document = to_json_dict(_tracked_one_to_one_record())
    assert canonical_json_bytes(document) == canonical_json_bytes(dict(document))
