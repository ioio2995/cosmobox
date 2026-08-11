from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.degeneracy import SpectralLevelGroup
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level1.local_observables import (
    NORMALIZATION_FLOOR,
    build_local_charge_operator,
    charge_correlator_connected,
    expectation_value,
)
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    build_restricted_operator,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
    extract_group_state,
)

N_FLAVORS = 2
SPIN = 1


def _diagonalize(geometry: str, spin: int, n_eigenvalues: int):
    lattice = build_lattice(geometry)
    n_nodes = len(lattice.nodes)
    report = build_basis(lattice, N_FLAVORS, spin)
    key_index = build_key_index(report.keys)
    params = HamiltonianParameters(
        J=tuple(1.0 for _ in range(n_nodes)),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)
    options = SpectrumOptions(n_eigenvalues=n_eigenvalues)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, spin, report, terms, params, spectrum_options=options
    )
    return lattice, report, key_index, level0_report, eigenvectors


def _deterministic_unitary(dimension: int, seed: int) -> np.ndarray:
    """A deterministic complex unitary via QR, per the validated review request."""
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    q, r = np.linalg.qr(raw)
    phase = np.diag(r) / np.abs(np.diag(r))
    return q * phase  # fix QR's sign ambiguity so the result is a genuine deterministic unitary


# ---------------------------------------------------------------------------
# SpectralGroupState
# ---------------------------------------------------------------------------


def test_spectral_group_state_rejects_1d_psi() -> None:
    with pytest.raises(ValueError, match="2-D"):
        SpectralGroupState(psi=np.zeros(4, dtype=np.complex128), status=COMPLETE_MULTIPLET)


def test_spectral_group_state_rejects_empty_psi() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        SpectralGroupState(psi=np.zeros((4, 0), dtype=np.complex128), status=COMPLETE_MULTIPLET)


def test_spectral_group_state_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status="degenerate")


def test_spectral_group_state_multiplicity_is_derived_from_psi_shape() -> None:
    psi = np.eye(4, dtype=np.complex128)[:, :3]
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    assert state.multiplicity == 3 == psi.shape[1]


def test_spectral_group_state_is_complete_reflects_status() -> None:
    psi = np.eye(2, dtype=np.complex128)
    assert SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET).is_complete is True
    assert SpectralGroupState(psi=psi, status=PARTIAL_SUBSPACE).is_complete is False


def test_spectral_group_state_rejects_nan() -> None:
    psi = np.eye(2, dtype=np.complex128)
    psi[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)


def test_spectral_group_state_rejects_inf() -> None:
    psi = np.eye(2, dtype=np.complex128)
    psi[0, 0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)


def test_spectral_group_state_rejects_unnormalized_column() -> None:
    psi = np.eye(2, dtype=np.complex128)
    psi[0, 0] = 2.0  # column [2, 0] has norm 2, not 1
    with pytest.raises(ValueError, match="orthonormal"):
        SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)


def test_spectral_group_state_rejects_non_orthogonal_columns() -> None:
    psi = np.array([[1.0, 1.0], [0.0, 0.0]], dtype=np.complex128)  # both columns are [1, 0]
    with pytest.raises(ValueError, match="orthonormal"):
        SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)


def test_spectral_group_state_copies_source_array_independently() -> None:
    source = np.eye(2, dtype=np.complex128)
    state = SpectralGroupState(psi=source, status=COMPLETE_MULTIPLET)
    source[0, 0] = 999.0  # mutate the source after construction
    assert state.psi[0, 0] == 1.0  # unaffected -- __post_init__ copied, not viewed


def test_spectral_group_state_psi_is_read_only() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="read-only"):
        state.psi[0, 0] = 5.0


def test_spectral_group_state_converts_real_array_to_complex128() -> None:
    real_psi = np.eye(2, dtype=np.float64)
    state = SpectralGroupState(psi=real_psi, status=COMPLETE_MULTIPLET)
    assert state.psi.dtype == np.complex128


# ---------------------------------------------------------------------------
# extract_group_state
# ---------------------------------------------------------------------------


def test_extract_group_state_rejects_1d_eigenvectors() -> None:
    group = SpectralLevelGroup(
        start_index=0, end_index_exclusive=1, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=1, lower_bound_only=False,
    )
    with pytest.raises(ValueError, match="2-D"):
        extract_group_state(np.zeros(4, dtype=np.complex128), group)


def test_extract_group_state_rejects_out_of_range_group() -> None:
    eigenvectors = np.eye(3, dtype=np.complex128)
    group = SpectralLevelGroup(
        start_index=2, end_index_exclusive=5, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=3, lower_bound_only=False,
    )
    with pytest.raises(ValueError, match="out of range"):
        extract_group_state(eigenvectors, group)


def test_extract_group_state_rejects_non_finite_eigenvectors() -> None:
    eigenvectors = np.eye(2, dtype=np.complex128)
    eigenvectors[0, 0] = np.nan
    group = SpectralLevelGroup(
        start_index=0, end_index_exclusive=2, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=2, lower_bound_only=False,
    )
    with pytest.raises(ValueError, match="non-finite"):
        extract_group_state(eigenvectors, group)


def test_extract_group_state_rejects_non_orthonormal_columns() -> None:
    eigenvectors = np.array([[1.0, 1.0], [0.0, 0.1]], dtype=np.complex128)  # not orthonormal
    group = SpectralLevelGroup(
        start_index=0, end_index_exclusive=2, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=2, lower_bound_only=False,
    )
    with pytest.raises(ValueError, match="orthonormal"):
        extract_group_state(eigenvectors, group)


def test_extract_group_state_derives_complete_status_from_lower_bound_only_false() -> None:
    eigenvectors = np.eye(3, dtype=np.complex128)
    group = SpectralLevelGroup(
        start_index=0, end_index_exclusive=2, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=2, lower_bound_only=False,
    )
    state = extract_group_state(eigenvectors, group)
    assert state.status == COMPLETE_MULTIPLET


def test_extract_group_state_derives_partial_status_from_lower_bound_only_true() -> None:
    eigenvectors = np.eye(3, dtype=np.complex128)
    group = SpectralLevelGroup(
        start_index=1, end_index_exclusive=3, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=2, lower_bound_only=True,
    )
    state = extract_group_state(eigenvectors, group)
    assert state.status == PARTIAL_SUBSPACE


def test_extract_group_state_psi_is_read_only() -> None:
    eigenvectors = np.eye(2, dtype=np.complex128)
    group = SpectralLevelGroup(
        start_index=0, end_index_exclusive=2, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=2, lower_bound_only=False,
    )
    state = extract_group_state(eigenvectors, group)
    with pytest.raises(ValueError, match="read-only"):
        state.psi[0, 0] = 5.0


def test_extract_group_state_psi_is_independent_copy_of_source() -> None:
    eigenvectors = np.eye(2, dtype=np.complex128)
    group = SpectralLevelGroup(
        start_index=0, end_index_exclusive=2, representative_energy=0.0,
        min_energy=0.0, max_energy=0.0, multiplicity_observed=2, lower_bound_only=False,
    )
    state = extract_group_state(eigenvectors, group)
    eigenvectors[0, 0] = 999.0  # mutate the source after extraction
    assert state.psi[0, 0] == 1.0  # unaffected -- extract_group_state copied, not viewed


def test_extract_group_state_matches_real_level0_diagonalization() -> None:
    _, _, _, level0_report, eigenvectors = _diagonalize("triangle", SPIN, n_eigenvalues=8)
    groups = level0_report.spectrum.degeneracy.groups
    assert any(not g.lower_bound_only for g in groups)
    assert any(g.lower_bound_only for g in groups)

    complete_group = next(g for g in groups if not g.lower_bound_only)
    partial_group = next(g for g in groups if g.lower_bound_only)

    complete_state = extract_group_state(eigenvectors, complete_group)
    partial_state = extract_group_state(eigenvectors, partial_group)
    assert complete_state.status == COMPLETE_MULTIPLET
    assert partial_state.status == PARTIAL_SUBSPACE
    assert complete_state.multiplicity == complete_group.multiplicity_observed
    assert partial_state.multiplicity == partial_group.multiplicity_observed


# ---------------------------------------------------------------------------
# build_restricted_operator
# ---------------------------------------------------------------------------


def test_build_restricted_operator_hand_verified() -> None:
    operator = sp.csr_matrix(np.diag([1.0, 2.0, 3.0]).astype(np.complex128))
    psi = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)  # picks out modes 0, 1
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    o_rest = build_restricted_operator(operator, state)
    np.testing.assert_allclose(o_rest, np.diag([1.0, 2.0]))


def test_build_restricted_operator_rejects_non_square_operator() -> None:
    operator = sp.csr_matrix(np.zeros((2, 3), dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="square"):
        build_restricted_operator(operator, state)


def test_build_restricted_operator_rejects_dimension_mismatch() -> None:
    operator = sp.csr_matrix(np.eye(3, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="dimension"):
        build_restricted_operator(operator, state)


def test_build_restricted_operator_never_larger_than_multiplicity_squared() -> None:
    # O_rest must be (multiplicity, multiplicity), never (dimension, dimension) --
    # the whole point of routing through O_rest instead of Pi = Psi Psi^dagger.
    dimension, multiplicity = 50, 3
    operator = sp.identity(dimension, format="csr", dtype=np.complex128)
    psi = np.eye(dimension, dtype=np.complex128)[:, :multiplicity]
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    o_rest = build_restricted_operator(operator, state)
    assert o_rest.shape == (multiplicity, multiplicity)


def test_build_restricted_operator_rejects_non_finite_operator_data() -> None:
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    operator.data[0] = np.nan
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="operator.data"):
        build_restricted_operator(operator, state)


def test_build_restricted_operator_defense_in_depth_rejects_non_finite_psi_bypassing_readonly() -> None:
    # SpectralGroupState.psi is read-only, but numpy's writeable flag can be
    # reverted with setflags(write=True) -- the same bypass-and-prove pattern
    # already used by transporters.py's tests against OrientedPath's own
    # frozen-dataclass guarantee. This proves build_restricted_operator's own
    # finite check is real defense in depth, not dead code shadowed by
    # SpectralGroupState's constructor-time guarantee.
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    state.psi.setflags(write=True)
    state.psi[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        build_restricted_operator(operator, state)


def test_build_restricted_operator_defense_in_depth_rejects_non_orthonormal_psi_bypassing_readonly() -> None:
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    state.psi.setflags(write=True)
    state.psi[0, 1] = 5.0  # breaks orthonormality without introducing non-finite values
    with pytest.raises(ValueError, match="orthonormal"):
        build_restricted_operator(operator, state)


# ---------------------------------------------------------------------------
# canonical_multiplet_expectation / exploratory_partial_subspace_mean
# ---------------------------------------------------------------------------


def test_canonical_multiplet_expectation_rejects_partial_group() -> None:
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=PARTIAL_SUBSPACE)
    with pytest.raises(ValueError, match=PARTIAL_SUBSPACE):
        canonical_multiplet_expectation(operator, state, hermitian=True)


def test_exploratory_partial_subspace_mean_rejects_complete_group() -> None:
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match=COMPLETE_MULTIPLET):
        exploratory_partial_subspace_mean(operator, state, hermitian=True)


def test_canonical_multiplet_expectation_hermitian_hand_verified() -> None:
    operator = sp.csr_matrix(np.diag([1.0, 3.0]).astype(np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    value = canonical_multiplet_expectation(operator, state, hermitian=True)
    assert value == pytest.approx(2.0)  # Tr(diag(1,3))/2
    assert isinstance(value, float)


def test_exploratory_partial_subspace_mean_hand_verified() -> None:
    operator = sp.csr_matrix(np.diag([1.0, 3.0]).astype(np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=PARTIAL_SUBSPACE)
    value = exploratory_partial_subspace_mean(operator, state, hermitian=True)
    assert value == pytest.approx(2.0)


def test_canonical_multiplet_expectation_non_hermitian_returns_complex() -> None:
    operator = sp.csr_matrix(np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    value = canonical_multiplet_expectation(operator, state, hermitian=False)
    assert isinstance(value, complex)
    assert value == pytest.approx(0.0)  # Tr(strictly upper triangular) == 0


def test_canonical_multiplet_expectation_raises_on_non_hermitian_o_rest_when_hermitian_true() -> None:
    operator = sp.csr_matrix(np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="Hermitian"):
        canonical_multiplet_expectation(operator, state, hermitian=True)


def test_canonical_multiplet_expectation_raises_on_nonnegligible_imaginary_trace() -> None:
    # A diagonal operator whose per-entry Hermiticity defect (8e-9) passes the
    # Hermiticity check (tolerance 1e-8) but whose diagonal imaginary parts do
    # NOT cancel in the trace (both +4e-9j), so the summed imaginary part
    # (8e-9) exceeds the separate, tighter trace tolerance (1e-10). This
    # shows the two checks are independent, not that one subsumes the other.
    psi = np.eye(2, dtype=np.complex128)
    operator = sp.csr_matrix(np.diag([2 + 4e-9j, 3 + 4e-9j]))
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="imaginary part"):
        canonical_multiplet_expectation(operator, state, hermitian=True)


# ---------------------------------------------------------------------------
# Reuse of the 1B-2 V11 scenario (triangle T=3/2 group): the mixed-state
# pathway must reproduce the pure-state result, since every eigenvector in
# that group individually gives <Q_i> = 0.
# ---------------------------------------------------------------------------


def test_canonical_multiplet_expectation_reproduces_triangle_t_3_2_zero_charge() -> None:
    from cosmobox.level0.symmetries import build_flavor_casimir

    lattice, report, key_index, level0_report, eigenvectors = _diagonalize("triangle", spin=2, n_eigenvalues=12)
    groups = level0_report.spectrum.degeneracy.groups
    casimir = build_flavor_casimir(lattice, N_FLAVORS, 2, report.keys, key_index)

    target_group = None
    for group in groups:
        if group.multiplicity_observed != 4 or group.lower_bound_only:
            continue
        psi_columns = eigenvectors[:, group.start_index : group.end_index_exclusive]
        t2_values = [expectation_value(casimir, psi_columns[:, k]) for k in range(psi_columns.shape[1])]
        if all(abs(value - 3.75) < 1e-8 for value in t2_values):
            target_group = group
            break
    assert target_group is not None, "no complete multiplicity-4 T^2=15/4 group found"

    state = extract_group_state(eigenvectors, target_group)
    assert state.status == COMPLETE_MULTIPLET

    for node in lattice.nodes:
        charge_operator = build_local_charge_operator(lattice, N_FLAVORS, 2, report.keys, key_index, node)
        value = canonical_multiplet_expectation(charge_operator, state, hermitian=True)
        assert value == pytest.approx(0.0, abs=1e-8)

    charge_operator_0 = build_local_charge_operator(lattice, N_FLAVORS, 2, report.keys, key_index, 0)
    variance = charge_correlator_connected(charge_operator_0, charge_operator_0, eigenvectors[:, target_group.start_index])
    assert abs(variance) <= NORMALIZATION_FLOOR


# ---------------------------------------------------------------------------
# V08 -- multiplet basis invariance under a random unitary rotation
# ---------------------------------------------------------------------------


def test_v08_canonical_expectation_invariant_under_unitary_rotation() -> None:
    dimension, multiplicity = 6, 3
    rng = np.random.default_rng(2026)
    raw_operator = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    hermitian_operator = sp.csr_matrix(raw_operator + raw_operator.conj().T)

    basis_matrix, _ = np.linalg.qr(rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension)))
    psi = basis_matrix[:, :multiplicity]
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)

    rotation = _deterministic_unitary(multiplicity, seed=7)
    rotated_state = SpectralGroupState(psi=psi @ rotation, status=COMPLETE_MULTIPLET)

    o_rest = build_restricted_operator(hermitian_operator, state)
    o_rest_rotated = build_restricted_operator(hermitian_operator, rotated_state)
    np.testing.assert_allclose(o_rest_rotated, rotation.conj().T @ o_rest @ rotation, atol=1e-8)

    value = canonical_multiplet_expectation(hermitian_operator, state, hermitian=True)
    rotated_value = canonical_multiplet_expectation(hermitian_operator, rotated_state, hermitian=True)
    assert rotated_value == pytest.approx(value, abs=1e-8)


def test_v08_rotation_is_genuinely_nontrivial() -> None:
    # Guards against a degenerate/near-identity rotation silently making the
    # invariance test above vacuous.
    rotation = _deterministic_unitary(3, seed=7)
    assert np.max(np.abs(rotation - np.eye(3))) > 0.1


# ---------------------------------------------------------------------------
# V09 -- canonical mixed state rho = Pi / d
# ---------------------------------------------------------------------------


def test_v09_psi_dagger_psi_is_identity() -> None:
    _, _, _, level0_report, eigenvectors = _diagonalize("triangle", SPIN, n_eigenvalues=8)
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    gram = state.psi.conj().T @ state.psi
    np.testing.assert_allclose(gram, np.eye(state.multiplicity), atol=1e-10)


def test_v09_trace_of_rho_is_one() -> None:
    dimension, multiplicity = 8, 4
    basis_matrix, _ = np.linalg.qr(
        np.random.default_rng(3).normal(size=(dimension, dimension))
        + 1j * np.random.default_rng(4).normal(size=(dimension, dimension))
    )
    psi = basis_matrix[:, :multiplicity]
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    identity = sp.identity(dimension, format="csr", dtype=np.complex128)
    trace_of_rho = canonical_multiplet_expectation(identity, state, hermitian=True)
    assert trace_of_rho == pytest.approx(1.0, abs=1e-10)


def test_v09_o_rest_trace_matches_explicit_dense_pi_reference() -> None:
    dimension, multiplicity = 6, 3
    rng = np.random.default_rng(5)
    raw_operator = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    operator = sp.csr_matrix(raw_operator + raw_operator.conj().T)

    basis_matrix, _ = np.linalg.qr(rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension)))
    psi = basis_matrix[:, :multiplicity]
    state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)

    # Reference computation: rho = Psi Psi^dagger / d, materialized explicitly
    # as a dense (dimension, dimension) matrix. Only ever done here, in a
    # small test, never inside restricted.py itself.
    pi_matrix = psi @ psi.conj().T
    rho = pi_matrix / multiplicity
    reference_trace = np.trace(operator.toarray() @ rho)

    value = canonical_multiplet_expectation(operator, state, hermitian=True)
    assert value == pytest.approx(reference_trace.real, abs=1e-10)
    assert abs(reference_trace.imag) < 1e-10


# ---------------------------------------------------------------------------
# V10 -- truncated group contract
# ---------------------------------------------------------------------------


def test_v10_complete_group_accepted_by_canonical_api_and_rejected_by_partial_api() -> None:
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    assert canonical_multiplet_expectation(operator, state, hermitian=True) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        exploratory_partial_subspace_mean(operator, state, hermitian=True)


def test_v10_partial_group_accepted_by_exploratory_api_and_rejected_by_canonical_api() -> None:
    operator = sp.csr_matrix(np.eye(2, dtype=np.complex128))
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=PARTIAL_SUBSPACE)
    assert exploratory_partial_subspace_mean(operator, state, hermitian=True) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        canonical_multiplet_expectation(operator, state, hermitian=True)


def test_v10_status_unchanged_after_internal_rotation() -> None:
    psi = np.eye(3, dtype=np.complex128)[:, :2]
    rotation = _deterministic_unitary(2, seed=11)

    complete_state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    rotated_complete = SpectralGroupState(psi=psi @ rotation, status=complete_state.status)
    assert rotated_complete.status == COMPLETE_MULTIPLET

    partial_state = SpectralGroupState(psi=psi, status=PARTIAL_SUBSPACE)
    rotated_partial = SpectralGroupState(psi=psi @ rotation, status=partial_state.status)
    assert rotated_partial.status == PARTIAL_SUBSPACE


def test_v10_real_truncated_group_from_level0_diagonalization() -> None:
    _, _, _, level0_report, eigenvectors = _diagonalize("triangle", SPIN, n_eigenvalues=8)
    groups = level0_report.spectrum.degeneracy.groups
    partial_group = next(g for g in groups if g.lower_bound_only)
    state = extract_group_state(eigenvectors, partial_group)
    assert state.status == PARTIAL_SUBSPACE

    identity = sp.identity(eigenvectors.shape[0], format="csr", dtype=np.complex128)
    value = exploratory_partial_subspace_mean(identity, state, hermitian=True)
    assert value == pytest.approx(1.0, abs=1e-10)
    with pytest.raises(ValueError):
        canonical_multiplet_expectation(identity, state, hermitian=True)
