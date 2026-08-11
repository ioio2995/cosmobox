from __future__ import annotations

from cosmobox.level1.matching import SymmetryLabel

from level1c_response_helpers import (
    REPO_COMMIT,
    build_group_documents,
    make_run_document,
    make_target_selection,
    make_tracking_document,
    symmetry_label_payload,
)

from scripts.level1c_response.response import RESPONSE_AVAILABLE, RESPONSE_NOT_AVAILABLE, build_response_record

OTHER_NUMERIC = SymmetryLabel(kind="numeric", value=complex(2.0, 0.0))
UNAVAILABLE = SymmetryLabel(kind="unavailable", value=None)

_COMMON = dict(campaign_id="level1c-j0-response-v1", repository_commit=REPO_COMMIT, manifest_fingerprint="fp")


def _baseline_loaded(run_document, records, failure_reason=None):
    return (run_document, records, failure_reason)


def _perturbed_loaded(run_document, records, failure_reason=None):
    return (run_document, records, failure_reason)


def _default_baseline():
    run_document = make_run_document([make_target_selection("fundamental", group_index=0)])
    records = build_group_documents(geometry="triangle", spin=2, group_index=0, twice_T=0, ctt_records=[(0, 1, 0.5), (1, 0, -0.5)], rho_records=[(0, 1, -0.5, None), (1, 0, -0.5, None)])
    return run_document, records


def _default_perturbed(*, group_index=5, target_group_index=None):
    if target_group_index is None:
        target_group_index = group_index
    run_document = make_run_document([make_target_selection("fundamental", group_index=target_group_index)])
    records = build_group_documents(
        geometry="triangle", spin=2, group_index=group_index, twice_T=0, hamiltonian_case_id="j0-0.75",
        ctt_records=[(0, 1, 0.75), (1, 0, -0.25)], rho_records=[(0, 1, -0.4, None), (1, 0, -0.4, None)],
    )
    return run_document, records


def test_tracked_one_to_one_full_available() -> None:
    tracking_document = make_tracking_document()
    baseline_run, baseline_records = _default_baseline()
    perturbed_run, perturbed_records = _default_perturbed()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_AVAILABLE
    assert record.failure_reasons == ()
    assert {(pair.i, pair.j): pair.delta for pair in record.delta_ctt_pairs} == {(0, 1): 0.25, (1, 0): 0.25}
    assert len(record.rho_pair_controls) == 2


def test_ambiguous_tracking_is_response_not_available() -> None:
    tracking_document = make_tracking_document(status="AMBIGUOUS", candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label={"kind": "unavailable", "value": None})
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert any("TRACKING_STATUS_NOT_TRACKED_ONE_TO_ONE" in reason for reason in record.failure_reasons)


def test_not_available_tracking_is_response_not_available() -> None:
    tracking_document = make_tracking_document(status="NOT_AVAILABLE", candidate_group_index=None, candidate_multiplicity=None, candidate_twice_T=None, candidate_reflection_label={"kind": "unavailable", "value": None})
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE


def test_perturbed_selected_different_group_than_tracking_candidate() -> None:
    """section 20.17's crucial point: TRACKED_ONE_TO_ONE structurally,
    but the perturbed case's own target selection landed on a DIFFERENT
    group than the tracked candidate -- never a post-hoc recomputation."""
    tracking_document = make_tracking_document(candidate_group_index=5)
    perturbed_run, perturbed_records = _default_perturbed(group_index=5, target_group_index=7)
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "PERTURBED_TARGET_SELECTION_MISMATCH" in record.failure_reasons


def test_perturbed_normative_case_valid_false_globally_but_this_target_available() -> None:
    """PERTURBED_NORMATIVE_CASE_VALIDITY_ROLE_IN_R=NOT_A_DIRECT_GATE: a
    case-level normative_case_valid=false (driven by a DIFFERENT
    REQUIRED target) must never block a locally-valid target-edge."""
    tracking_document = make_tracking_document(target_id="fundamental", candidate_group_index=5)
    perturbed_run = make_run_document([
        make_target_selection("fundamental", group_index=5, meets_normative=True),
        make_target_selection("first_excited", selected=False),  # ambiguous, unrelated failure
    ])
    _, perturbed_records = _default_perturbed(group_index=5)
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_AVAILABLE


def test_perturbed_target_selected_but_meets_normative_false() -> None:
    tracking_document = make_tracking_document(candidate_group_index=5)
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5, meets_normative=False)])
    _, perturbed_records = _default_perturbed(group_index=5)
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "PERTURBED_TARGET_SELECTION_MISMATCH" in record.failure_reasons


def test_baseline_target_mismatch() -> None:
    tracking_document = make_tracking_document(baseline_group_index=0)
    baseline_run = make_run_document([make_target_selection("fundamental", group_index=3)])
    _, baseline_records = _default_baseline()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "BASELINE_TARGET_SELECTION_MISMATCH" in record.failure_reasons


def test_baseline_unavailable() -> None:
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(None, None, "run_status is 'failed'"), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert any("BASELINE_UNAVAILABLE" in reason for reason in record.failure_reasons)


def test_perturbed_unavailable() -> None:
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(None, None, "run_status is 'failed'"), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert any("PERTURBED_UNAVAILABLE" in reason for reason in record.failure_reasons)


def test_tracking_p_multiplicity_mismatch() -> None:
    tracking_document = make_tracking_document(baseline_multiplicity=99)
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "TRACKING_P_BASELINE_MULTIPLICITY_MISMATCH" in record.failure_reasons


def test_tracking_p_twice_t_mismatch() -> None:
    tracking_document = make_tracking_document(candidate_twice_T=99)
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "TRACKING_P_CANDIDATE_TWICE_T_MISMATCH" in record.failure_reasons


def test_tracking_p_reflection_mismatch() -> None:
    tracking_document = make_tracking_document(candidate_reflection_label=symmetry_label_payload(OTHER_NUMERIC))
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "TRACKING_P_CANDIDATE_REFLECTION_MISMATCH" in record.failure_reasons


def test_ctt_pair_set_exact_available() -> None:
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert record.response_eligibility == RESPONSE_AVAILABLE


def test_ctt_missing_pair_unavailable() -> None:
    baseline_run, baseline_records = _default_baseline()
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5)])
    perturbed_records = build_group_documents(geometry="triangle", spin=2, group_index=5, twice_T=0, hamiltonian_case_id="j0-0.75", ctt_records=[(0, 1, 0.75)], rho_records=[(0, 1, -0.4, None)])
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "CTT_PAIR_SET_MISMATCH" in record.failure_reasons


def test_ctt_extra_pair_unavailable() -> None:
    baseline_run, baseline_records = _default_baseline()
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5)])
    perturbed_records = build_group_documents(
        geometry="triangle", spin=2, group_index=5, twice_T=0, hamiltonian_case_id="j0-0.75",
        ctt_records=[(0, 1, 0.75), (1, 0, -0.25), (0, 2, 0.1)], rho_records=[(0, 1, -0.4, None), (1, 0, -0.4, None), (0, 2, -0.1, None)],
    )
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "CTT_PAIR_SET_MISMATCH" in record.failure_reasons


def test_ctt_duplicate_unavailable() -> None:
    baseline_run, baseline_records = _default_baseline()
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5)])
    perturbed_records = build_group_documents(
        geometry="triangle", spin=2, group_index=5, twice_T=0, hamiltonian_case_id="j0-0.75",
        ctt_records=[(0, 1, 0.75), (0, 1, 0.76), (1, 0, -0.25)], rho_records=[(0, 1, -0.4, None), (1, 0, -0.4, None)],
    )
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert any("PERTURBED_CTT_DUPLICATE_PAIR" in reason for reason in record.failure_reasons)


def test_delta_ctt_exact_arithmetic() -> None:
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    for pair in record.delta_ctt_pairs:
        assert pair.delta == pair.perturbed_value - pair.baseline_value


def test_rho_numeric_numeric_preserved() -> None:
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    control = next(c for c in record.rho_pair_controls if (c.i, c.j) == (0, 1))
    assert control.baseline_value == -0.5
    assert control.perturbed_value == -0.4
    assert control.baseline_null_reason is None
    assert control.perturbed_null_reason is None


def test_rho_numeric_null_preserved() -> None:
    baseline_run, baseline_records = _default_baseline()
    baseline_records = build_group_documents(geometry="triangle", spin=2, group_index=0, twice_T=0, ctt_records=[(0, 1, 0.5), (1, 0, -0.5)], rho_records=[(0, 1, -0.5, None), (1, 0, None, "zero_local_charge_variance")])
    perturbed_run, perturbed_records = _default_perturbed()
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_AVAILABLE
    control = next(c for c in record.rho_pair_controls if (c.i, c.j) == (1, 0))
    assert control.baseline_value is None
    assert control.baseline_null_reason == "zero_local_charge_variance"
    assert control.perturbed_value == -0.4


def test_rho_null_numeric_preserved() -> None:
    baseline_run, baseline_records = _default_baseline()
    perturbed_records = build_group_documents(geometry="triangle", spin=2, group_index=5, twice_T=0, hamiltonian_case_id="j0-0.75", ctt_records=[(0, 1, 0.75), (1, 0, -0.25)], rho_records=[(0, 1, None, "zero_local_charge_variance"), (1, 0, -0.4, None)])
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5)])
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_AVAILABLE
    control = next(c for c in record.rho_pair_controls if (c.i, c.j) == (0, 1))
    assert control.baseline_value == -0.5
    assert control.perturbed_value is None
    assert control.perturbed_null_reason == "zero_local_charge_variance"


def test_rho_null_null_preserved_with_reasons_each_side() -> None:
    baseline_records = build_group_documents(geometry="triangle", spin=2, group_index=0, twice_T=0, ctt_records=[(0, 1, 0.5), (1, 0, -0.5)], rho_records=[(0, 1, None, "zero_local_charge_variance"), (1, 0, -0.5, None)])
    baseline_run = make_run_document([make_target_selection("fundamental", group_index=0)])
    perturbed_records = build_group_documents(geometry="triangle", spin=2, group_index=5, twice_T=0, hamiltonian_case_id="j0-0.75", ctt_records=[(0, 1, 0.75), (1, 0, -0.25)], rho_records=[(0, 1, None, "normalization_denominator_below_floor"), (1, 0, -0.4, None)])
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5)])
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_AVAILABLE
    control = next(c for c in record.rho_pair_controls if (c.i, c.j) == (0, 1))
    assert control.baseline_value is None and control.baseline_null_reason == "zero_local_charge_variance"
    assert control.perturbed_value is None and control.perturbed_null_reason == "normalization_denominator_below_floor"


def test_rho_pair_set_mismatch_unavailable() -> None:
    baseline_run, baseline_records = _default_baseline()
    perturbed_run = make_run_document([make_target_selection("fundamental", group_index=5)])
    perturbed_records = build_group_documents(
        geometry="triangle", spin=2, group_index=5, twice_T=0, hamiltonian_case_id="j0-0.75",
        ctt_records=[(0, 1, 0.75), (1, 0, -0.25)], rho_records=[(0, 1, -0.4, None)],
    )
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(baseline_run, baseline_records), _perturbed_loaded(perturbed_run, perturbed_records), **_COMMON)
    assert record.response_eligibility == RESPONSE_NOT_AVAILABLE
    assert "RHO_PAIR_SET_MISMATCH" in record.failure_reasons


def test_no_physical_or_incident_or_g_content_in_available_record() -> None:
    tracking_document = make_tracking_document()
    record = build_response_record(tracking_document, _baseline_loaded(*_default_baseline()), _perturbed_loaded(*_default_perturbed()), **_COMMON)
    assert not hasattr(record, "incident")
    assert not hasattr(record, "physical_response")
    assert not hasattr(record, "g_value")
