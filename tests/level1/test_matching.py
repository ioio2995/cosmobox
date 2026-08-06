from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.automorphisms import (
    reflection_unitary_automorphism,
    translation_unitary_automorphism,
)
from cosmobox.level1.matching import (
    AMBIGUOUS_CROSS_TRUNCATION_MATCH,
    EXACT_LABEL_MATCH,
    NOT_APPLICABLE,
    NUMERIC,
    STRUCTURALLY_NOT_APPLICABLE,
    TARGET_GROUP_NOT_IN_WINDOW,
    UNAVAILABLE,
    MatchOutcome,
    SpectralGroupMatchKey,
    SymmetryLabel,
    compute_restricted_symmetry_label,
    compute_twice_T,
    match_spectral_group,
    symmetry_labels_match,
)
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    canonical_multiplet_expectation,
    extract_group_state,
)

N_FLAVORS = 2


def _deterministic_unitary(dimension: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    q, r = np.linalg.qr(raw)
    phase = np.diag(r) / np.abs(np.diag(r))
    return q * phase


def _diagonalize(geometry: str, spin: int, n_eigenvalues: int, *, j_break: bool = False):
    lattice = build_lattice(geometry)
    n_nodes = len(lattice.nodes)
    report = build_basis(lattice, N_FLAVORS, spin)
    key_index = build_key_index(report.keys)
    J = tuple(1.5 if (j_break and node == 0) else 1.0 for node in range(n_nodes))
    params = HamiltonianParameters(
        J=J, h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)), t=1.0, g_E=1.0, K=1.0
    )
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)
    options = SpectrumOptions(n_eigenvalues=n_eigenvalues)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, spin, report, terms, params, spectrum_options=options
    )
    return lattice, report, key_index, terms, level0_report, eigenvectors


def _base_key(**overrides) -> SpectralGroupMatchKey:
    defaults = dict(
        geometry="triangle",
        hamiltonian_identity_without_spin="ref_j1",
        sector_identity="default",
        status=COMPLETE_MULTIPLET,
        multiplicity=2,
        twice_T=1,
        translation_label=SymmetryLabel(kind=NUMERIC, value=1 + 0j),
        reflection_label=SymmetryLabel(kind=NUMERIC, value=1 + 0j),
    )
    defaults.update(overrides)
    return SpectralGroupMatchKey(**defaults)


# ---------------------------------------------------------------------------
# SymmetryLabel
# ---------------------------------------------------------------------------


def test_symmetry_label_numeric_requires_a_value() -> None:
    with pytest.raises(ValueError, match="value must be set"):
        SymmetryLabel(kind=NUMERIC, value=None)


def test_symmetry_label_non_numeric_forbids_a_value() -> None:
    with pytest.raises(ValueError, match="value must be set"):
        SymmetryLabel(kind=NOT_APPLICABLE, value=1 + 0j)


def test_symmetry_label_rejects_invalid_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        SymmetryLabel(kind="bogus", value=None)


def test_symmetry_label_rejects_non_finite_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        SymmetryLabel(kind=NUMERIC, value=complex(float("nan"), 0.0))


def test_symmetry_labels_match_two_not_applicable() -> None:
    a = SymmetryLabel(kind=NOT_APPLICABLE, value=None)
    b = SymmetryLabel(kind=NOT_APPLICABLE, value=None)
    assert symmetry_labels_match(a, b)


def test_symmetry_labels_match_two_unavailable_never_match() -> None:
    a = SymmetryLabel(kind=UNAVAILABLE, value=None)
    b = SymmetryLabel(kind=UNAVAILABLE, value=None)
    assert not symmetry_labels_match(a, b)


def test_symmetry_labels_match_numeric_within_tolerance() -> None:
    a = SymmetryLabel(kind=NUMERIC, value=1.0 + 0j)
    b = SymmetryLabel(kind=NUMERIC, value=1.0 + 5e-9j)
    assert symmetry_labels_match(a, b, tolerance=1e-8)


def test_symmetry_labels_match_numeric_outside_tolerance() -> None:
    a = SymmetryLabel(kind=NUMERIC, value=1.0 + 0j)
    b = SymmetryLabel(kind=NUMERIC, value=1.1 + 0j)
    assert not symmetry_labels_match(a, b, tolerance=1e-8)


def test_symmetry_labels_match_kind_mismatch_never_matches() -> None:
    a = SymmetryLabel(kind=NOT_APPLICABLE, value=None)
    b = SymmetryLabel(kind=NUMERIC, value=1 + 0j)
    assert not symmetry_labels_match(a, b)


# ---------------------------------------------------------------------------
# compute_twice_T
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("casimir", "expected_twice_T"),
    [(0.0, 0), (0.75, 1), (2.0, 2), (3.75, 3)],
)
def test_compute_twice_t_hand_verified(casimir: float, expected_twice_T: int) -> None:
    assert compute_twice_T(casimir) == expected_twice_T


def test_compute_twice_t_none_on_large_residual() -> None:
    assert compute_twice_T(1.0) is None  # no half-integer T solves T(T+1)=1 exactly


def test_compute_twice_t_none_on_negative_casimir() -> None:
    assert compute_twice_T(-0.1) is None


def test_compute_twice_t_accepts_small_numerical_noise() -> None:
    assert compute_twice_T(3.75 + 1e-10) == 3


# ---------------------------------------------------------------------------
# compute_restricted_symmetry_label -- real integration
# ---------------------------------------------------------------------------


def test_compute_restricted_symmetry_label_numeric_at_j_i_1() -> None:
    spin = 1
    lattice, report, key_index, terms, level0_report, eigenvectors = _diagonalize("triangle", spin, 8)
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)

    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    label = compute_restricted_symmetry_label(terms.total, translation, state)
    assert label.kind == NUMERIC
    assert label.value is not None


def test_compute_restricted_symmetry_label_not_applicable_under_j_break() -> None:
    spin = 2
    lattice, report, key_index, terms, level0_report, eigenvectors = _diagonalize("triangle", spin, 12, j_break=True)
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)

    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    label = compute_restricted_symmetry_label(terms.total, translation, state)
    assert label.kind == NOT_APPLICABLE

    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    reflection_label = compute_restricted_symmetry_label(terms.total, reflection, state)
    assert reflection_label.kind == NUMERIC


def test_compute_restricted_symmetry_label_invariant_under_internal_rotation() -> None:
    spin = 1
    lattice, report, key_index, terms, level0_report, eigenvectors = _diagonalize("triangle", spin, 8)
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)

    label = compute_restricted_symmetry_label(terms.total, reflection, state)
    assert label.kind == NUMERIC

    rotation = _deterministic_unitary(state.multiplicity, seed=5)
    rotated_state = SpectralGroupState(psi=state.psi @ rotation, status=state.status)
    rotated_label = compute_restricted_symmetry_label(terms.total, reflection, rotated_state)

    assert rotated_label.kind == NUMERIC
    assert rotated_label.value == pytest.approx(label.value, abs=1e-8)


def test_compute_restricted_symmetry_label_matches_flavor_casimir_scenario() -> None:
    # Reuses the 1B-2 V11 triangle T=3/2 scenario: identity is trivially a
    # symmetry, its restricted character must equal the group's multiplicity.
    spin = 2
    lattice, report, key_index, terms, level0_report, eigenvectors = _diagonalize("triangle", spin, 12)
    casimir = build_flavor_casimir(lattice, N_FLAVORS, spin, report.keys, key_index)
    groups = level0_report.spectrum.degeneracy.groups

    target_group = None
    for group in groups:
        if group.multiplicity_observed != 4 or group.lower_bound_only:
            continue
        state = extract_group_state(eigenvectors, group)
        c_t = canonical_multiplet_expectation(casimir, state, hermitian=True)
        if abs(c_t - 3.75) < 1e-8:
            target_group = group
            break
    assert target_group is not None
    state = extract_group_state(eigenvectors, target_group)
    c_t = canonical_multiplet_expectation(casimir, state, hermitian=True)
    assert compute_twice_T(c_t) == 3


# ---------------------------------------------------------------------------
# SpectralGroupMatchKey
# ---------------------------------------------------------------------------


def test_spectral_group_match_key_valid_construction() -> None:
    key = _base_key()
    assert key.multiplicity == 2


def test_spectral_group_match_key_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        _base_key(status="degenerate")


def test_spectral_group_match_key_rejects_nonpositive_multiplicity() -> None:
    with pytest.raises(ValueError, match="multiplicity"):
        _base_key(multiplicity=0)


def test_spectral_group_match_key_rejects_negative_twice_t() -> None:
    with pytest.raises(ValueError, match="twice_T"):
        _base_key(twice_T=-1)


def test_spectral_group_match_key_rejects_non_symmetry_label_type() -> None:
    with pytest.raises(ValueError, match="translation_label"):
        _base_key(translation_label="not a label")


# ---------------------------------------------------------------------------
# MatchOutcome
# ---------------------------------------------------------------------------


def test_match_outcome_requires_matched_group_for_exact_label_match() -> None:
    with pytest.raises(ValueError, match="matched_group"):
        MatchOutcome(EXACT_LABEL_MATCH, None)


def test_match_outcome_forbids_matched_group_for_non_exact_status() -> None:
    with pytest.raises(ValueError, match="matched_group"):
        MatchOutcome(TARGET_GROUP_NOT_IN_WINDOW, _base_key())


# ---------------------------------------------------------------------------
# match_spectral_group
# ---------------------------------------------------------------------------


def test_match_spectral_group_structurally_not_applicable() -> None:
    outcome = match_spectral_group(
        _base_key(), [_base_key()], structurally_applicable=False, low_window_truncated=False
    )
    assert outcome.status == STRUCTURALLY_NOT_APPLICABLE


def test_match_spectral_group_target_none() -> None:
    outcome = match_spectral_group(None, [_base_key()], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == TARGET_GROUP_NOT_IN_WINDOW


def test_match_spectral_group_exact_match() -> None:
    target = _base_key()
    candidate = _base_key()
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == EXACT_LABEL_MATCH
    assert outcome.matched_group == candidate


def test_match_spectral_group_rejects_multiplicity_mismatch() -> None:
    target = _base_key(multiplicity=2)
    candidate = _base_key(multiplicity=4)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == TARGET_GROUP_NOT_IN_WINDOW  # zero exact candidates, window not marked truncated


def test_match_spectral_group_multiple_exact_candidates_is_ambiguous() -> None:
    target = _base_key()
    candidate_a = _base_key()
    candidate_b = _base_key()
    outcome = match_spectral_group(
        target, [candidate_a, candidate_b], structurally_applicable=True, low_window_truncated=False
    )
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH


def test_match_spectral_group_zero_candidates_with_truncated_window_is_ambiguous() -> None:
    target = _base_key()
    outcome = match_spectral_group(target, [], structurally_applicable=True, low_window_truncated=True)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH


def test_match_spectral_group_zero_candidates_without_truncation_is_not_in_window() -> None:
    target = _base_key()
    outcome = match_spectral_group(target, [], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == TARGET_GROUP_NOT_IN_WINDOW


def test_match_spectral_group_unavailable_label_among_candidates_is_ambiguous() -> None:
    target = _base_key()
    candidate = _base_key(
        multiplicity=999,  # never exact, but present in the comparable bucket
        translation_label=SymmetryLabel(kind=UNAVAILABLE, value=None),
    )
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH


def test_match_spectral_group_different_geometry_is_never_a_candidate() -> None:
    target = _base_key(geometry="triangle")
    candidate = _base_key(geometry="ring4")
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == TARGET_GROUP_NOT_IN_WINDOW


def test_match_spectral_group_different_hamiltonian_identity_is_never_a_candidate() -> None:
    target = _base_key(hamiltonian_identity_without_spin="ref_j1")
    candidate = _base_key(hamiltonian_identity_without_spin="j_break")
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == TARGET_GROUP_NOT_IN_WINDOW


def test_match_spectral_group_complete_target_never_matches_partial_candidate() -> None:
    target = _base_key(status=COMPLETE_MULTIPLET)
    candidate = _base_key(status=PARTIAL_SUBSPACE)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status != EXACT_LABEL_MATCH
    assert outcome.status == TARGET_GROUP_NOT_IN_WINDOW


def test_match_spectral_group_partial_target_never_matches_complete_candidate() -> None:
    target = _base_key(status=PARTIAL_SUBSPACE)
    candidate = _base_key(status=COMPLETE_MULTIPLET)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status != EXACT_LABEL_MATCH


def test_match_spectral_group_partial_vs_partial_with_identical_labels_is_ambiguous_not_exact() -> None:
    # Even when the observed labels coincide exactly, a partial_subspace
    # target or candidate can never produce exact_label_match: truncation
    # means the group's true multiplicity may exceed the observed one, so
    # its identity as a complete multiplet can never be proven.
    target = _base_key(status=PARTIAL_SUBSPACE)
    candidate = _base_key(status=PARTIAL_SUBSPACE)
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH
    assert outcome.matched_group is None


def test_match_spectral_group_target_translation_unavailable_is_ambiguous_not_absent() -> None:
    # The group is NOT absent from the window -- its identity simply
    # cannot be established -- so this must never be reported as
    # target_group_not_in_window.
    target = _base_key(translation_label=SymmetryLabel(kind=UNAVAILABLE, value=None))
    candidate = _base_key()
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH


def test_match_spectral_group_target_reflection_unavailable_is_ambiguous_not_absent() -> None:
    target = _base_key(reflection_label=SymmetryLabel(kind=UNAVAILABLE, value=None))
    candidate = _base_key()
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH


def test_match_spectral_group_target_unavailable_label_with_no_candidates_is_still_ambiguous() -> None:
    target = _base_key(translation_label=SymmetryLabel(kind=UNAVAILABLE, value=None))
    outcome = match_spectral_group(target, [], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == AMBIGUOUS_CROSS_TRUNCATION_MATCH


def test_match_spectral_group_not_applicable_labels_on_both_sides_are_compatible() -> None:
    target = _base_key(translation_label=SymmetryLabel(kind=NOT_APPLICABLE, value=None))
    candidate = _base_key(translation_label=SymmetryLabel(kind=NOT_APPLICABLE, value=None))
    outcome = match_spectral_group(target, [candidate], structurally_applicable=True, low_window_truncated=False)
    assert outcome.status == EXACT_LABEL_MATCH
