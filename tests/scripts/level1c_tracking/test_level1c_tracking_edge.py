from __future__ import annotations

from cosmobox.level1.matching import SymmetryLabel

from level1c_tracking_helpers import REPO_COMMIT, _group_documents, make_group_structural_data

from scripts.level1c_tracking.tracking import AMBIGUOUS, NOT_AVAILABLE, TRACKED_ONE_TO_ONE, track_target_edge

NUMERIC = SymmetryLabel(kind="numeric", value=complex(1.0, 0.0))
OTHER_NUMERIC = SymmetryLabel(kind="numeric", value=complex(2.0, 0.0))
NOT_APPLICABLE = SymmetryLabel(kind="not_applicable", value=None)
UNAVAILABLE = SymmetryLabel(kind="unavailable", value=None)

_COMMON = dict(
    target_id="fundamental",
    geometry="triangle",
    spin=2,
    baseline_case_id="baseline-case",
    perturbed_case_id="perturbed-case",
    baseline_hamiltonian_case_id="j0-1.00",
    perturbed_hamiltonian_case_id="j0-0.75",
    campaign_id="level1c-j0-response-v1",
    repository_commit=REPO_COMMIT,
    manifest_fingerprint="fp",
)


def _baseline_run_document(group_index: int = 0) -> dict:
    return {
        "target_selections": [
            {"target_id": "fundamental", "selection_status": "selected", "spectral_window_group_index": group_index}
        ]
    }


def _baseline_records(data) -> tuple[dict, ...]:
    return tuple(
        _group_documents(
            geometry="triangle", spin=2, repository_commit=REPO_COMMIT, manifest_fingerprint="fp",
            campaign_id="level1c-j0-response-v1", group_index=data.spectral_window_group_index, data=data,
        )
    )


def test_tracked_one_to_one_unique_match_same_multiplicity() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, multiplicity=2, reflection=NUMERIC)
    candidate = make_group_structural_data(5, twice_T=1, multiplicity=2, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE
    assert record.candidate_group_index == 5
    assert record.class_pool_size == 1
    assert record.failure_reasons == ()


def test_unique_match_but_multiplicity_mismatch_is_ambiguous_never_not_available() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, multiplicity=2, reflection=NUMERIC)
    candidate = make_group_structural_data(5, twice_T=1, multiplicity=3, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == AMBIGUOUS
    assert "MULTIPLICITY_MISMATCH" in record.failure_reasons[0]
    assert record.class_pool_size == 1


def test_two_candidates_ambiguous() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    candidate_a = make_group_structural_data(5, twice_T=1, reflection=NUMERIC)
    candidate_b = make_group_structural_data(6, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate_a, candidate_b),
        perturbed_failure_reason=None,
    )
    assert record.status == AMBIGUOUS
    assert record.class_pool_size == 2
    assert "CLASS_POOL_NOT_UNIQUE" in record.failure_reasons[0]


def test_clean_empty_pool_is_not_available() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    other = make_group_structural_data(5, twice_T=9, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(other,),
        perturbed_failure_reason=None,
    )
    assert record.status == NOT_AVAILABLE
    assert record.class_pool_size == 0


def test_no_perturbed_groups_at_all_is_not_available() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(),
        perturbed_failure_reason=None,
    )
    assert record.status == NOT_AVAILABLE


def test_baseline_unresolved_twice_t_is_ambiguous() -> None:
    baseline_data = make_group_structural_data(0, twice_T=None, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(make_group_structural_data(5, twice_T=1, reflection=NUMERIC),),
        perturbed_failure_reason=None,
    )
    assert record.status == AMBIGUOUS
    assert record.class_pool_size is None
    assert any("BASELINE_TWICE_T_UNRESOLVED" in reason for reason in record.failure_reasons)
    # even though the baseline branch is unresolved, its own known facts
    # (group index/multiplicity/reflection) are still reported.
    assert record.baseline_group_index == 0


def test_baseline_reflection_non_numeric_is_ambiguous() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=UNAVAILABLE)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(make_group_structural_data(5, twice_T=1, reflection=NUMERIC),),
        perturbed_failure_reason=None,
    )
    assert record.status == AMBIGUOUS
    assert any("BASELINE_REFLECTION_NOT_NUMERIC" in reason for reason in record.failure_reasons)


def test_perturbed_relevant_candidate_unresolved_reflection_is_ambiguous() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    unresolved_candidate = make_group_structural_data(5, twice_T=1, reflection=UNAVAILABLE)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(unresolved_candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == AMBIGUOUS
    assert record.class_pool_size == 0
    assert any("PERTURBED_CANDIDATE_UNRESOLVED" in reason for reason in record.failure_reasons)


def test_translation_mismatch_never_blocks_tracked_one_to_one() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC, translation=NUMERIC)
    candidate = make_group_structural_data(5, twice_T=1, reflection=NUMERIC, translation=NOT_APPLICABLE)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE


def test_energy_mismatch_never_blocks_tracked_one_to_one() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC, representative_energy=-50.0)
    candidate = make_group_structural_data(5, twice_T=1, reflection=NUMERIC, representative_energy=1e9)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE


def test_spectral_index_mismatch_never_blocks_tracked_one_to_one() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    candidate = make_group_structural_data(777, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE
    assert record.candidate_group_index == 777


def test_wrong_twice_t_group_excluded_from_pool() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    wrong = make_group_structural_data(5, twice_T=9, reflection=NUMERIC)
    right = make_group_structural_data(6, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(wrong, right),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE
    assert record.candidate_group_index == 6


def test_wrong_reflection_group_excluded_from_pool() -> None:
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    wrong = make_group_structural_data(5, twice_T=1, reflection=OTHER_NUMERIC)
    right = make_group_structural_data(6, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(wrong, right),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE
    assert record.candidate_group_index == 6


def test_baseline_unavailable_is_ambiguous() -> None:
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=None,
        baseline_records=None,
        baseline_failure_reason="run_status is 'failed', not 'success'",
        perturbed_groups=None,
        perturbed_failure_reason=None,
    )
    assert record.status == AMBIGUOUS
    assert record.baseline_group_index is None
    assert record.class_pool_size is None
    assert any("BASELINE_UNAVAILABLE" in reason for reason in record.failure_reasons)


def test_perturbed_technical_failure_is_ambiguous_never_not_available() -> None:
    """PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE design question (section
    14): a technically-failed perturbed case (run_status != success)
    must yield AMBIGUOUS, never a silent exclusion and never
    NOT_AVAILABLE (an unresolved computation proves neither presence nor
    absence)."""
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=None,
        perturbed_failure_reason="run_status is 'failed', not 'success'",
    )
    assert record.status == AMBIGUOUS
    assert record.class_pool_size is None
    assert any("PERTURBED_UNAVAILABLE" in reason for reason in record.failure_reasons)
    # the baseline's own known facts are still reported even though the
    # perturbed side is unusable.
    assert record.baseline_group_index == 0


def test_perturbed_normative_case_valid_false_is_irrelevant_when_run_status_success() -> None:
    """PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE: a perturbed case that
    technically succeeded but is normatively invalid (some OTHER
    REQUIRED target failed selection) must still be fully usable for
    tracking -- normative_case_valid is never consulted by
    track_target_edge at all (only perturbed_failure_reason, which
    reflects run_status/integrity, ever gates the perturbed side)."""
    baseline_data = make_group_structural_data(0, twice_T=1, reflection=NUMERIC)
    candidate = make_group_structural_data(5, twice_T=1, reflection=NUMERIC)
    record = track_target_edge(
        **_COMMON,
        baseline_run_document=_baseline_run_document(0),
        baseline_records=_baseline_records(baseline_data),
        baseline_failure_reason=None,
        perturbed_groups=(candidate,),
        perturbed_failure_reason=None,
    )
    assert record.status == TRACKED_ONE_TO_ONE
