from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level1.flavor import (
    FlavorCorrelatorMatrix,
    build_flavor_correlator_matrix,
    flavor_frobenius_squared,
    flavor_singlet,
    flavor_singular_value_ratio,
    flavor_singular_values,
)
from cosmobox.level1.local_observables import NORMALIZATION_FLOOR
from cosmobox.level1.paths import make_oriented_path
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, extract_group_state

N_FLAVORS = 2


def _deterministic_unitary(dimension: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    q, r = np.linalg.qr(raw)
    phase = np.diag(r) / np.abs(np.diag(r))
    return q * phase


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


# ---------------------------------------------------------------------------
# FlavorCorrelatorMatrix
# ---------------------------------------------------------------------------


def test_flavor_correlator_matrix_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError, match="shape"):
        FlavorCorrelatorMatrix(matrix=np.eye(3, dtype=np.complex128), status=COMPLETE_MULTIPLET)


def test_flavor_correlator_matrix_rejects_non_finite() -> None:
    matrix = np.eye(2, dtype=np.complex128)
    matrix[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        FlavorCorrelatorMatrix(matrix=matrix, status=COMPLETE_MULTIPLET)


def test_flavor_correlator_matrix_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        FlavorCorrelatorMatrix(matrix=np.eye(2, dtype=np.complex128), status="degenerate")


def test_flavor_correlator_matrix_is_read_only_and_an_independent_copy() -> None:
    source = np.eye(2, dtype=np.complex128)
    correlator = FlavorCorrelatorMatrix(matrix=source, status=COMPLETE_MULTIPLET)
    source[0, 0] = 999.0
    assert correlator.matrix[0, 0] == 1.0
    with pytest.raises(ValueError, match="read-only"):
        correlator.matrix[0, 0] = 5.0


def test_flavor_correlator_matrix_converts_real_array_to_complex128() -> None:
    correlator = FlavorCorrelatorMatrix(matrix=np.eye(2, dtype=np.float64), status=PARTIAL_SUBSPACE)
    assert correlator.matrix.dtype == np.complex128


# ---------------------------------------------------------------------------
# build_flavor_correlator_matrix
# ---------------------------------------------------------------------------


def test_build_flavor_correlator_matrix_rejects_n_flavors_other_than_two() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize("triangle", 1, 6)
    group = level0_report.spectrum.degeneracy.groups[0]
    state = extract_group_state(eigenvectors, group)
    path = make_oriented_path(lattice, (0,))
    with pytest.raises(ValueError, match="n_flavors"):
        build_flavor_correlator_matrix(lattice, 3, 1, report.keys, key_index, state, path)


def test_build_flavor_correlator_matrix_diagonal_matches_local_charge_relation_at_ground_state() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize("triangle", 1, 6)
    group = level0_report.spectrum.degeneracy.groups[0]
    state = extract_group_state(eigenvectors, group)
    zero_path = make_oriented_path(lattice, (0,))
    correlator = build_flavor_correlator_matrix(lattice, N_FLAVORS, 1, report.keys, key_index, state, zero_path)
    assert correlator.status == COMPLETE_MULTIPLET
    # G^{alpha,alpha}[empty] = <n_alpha> is real and in [0, 1] for any physical state.
    for alpha in range(2):
        assert abs(correlator.matrix[alpha, alpha].imag) < 1e-8
        assert -1e-8 <= correlator.matrix[alpha, alpha].real <= 1 + 1e-8


def test_build_flavor_correlator_matrix_uses_exploratory_path_for_partial_group() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize("triangle", 1, 6)
    groups = level0_report.spectrum.degeneracy.groups
    partial_group = next(g for g in groups if g.lower_bound_only)
    state = extract_group_state(eigenvectors, partial_group)
    zero_path = make_oriented_path(lattice, (0,))
    correlator = build_flavor_correlator_matrix(lattice, N_FLAVORS, 1, report.keys, key_index, state, zero_path)
    assert correlator.status == PARTIAL_SUBSPACE


# ---------------------------------------------------------------------------
# Flavor invariants -- hand-verified
# ---------------------------------------------------------------------------


def _hand_matrix() -> FlavorCorrelatorMatrix:
    matrix = np.array([[1 + 2j, 0.5 - 1j], [0.3j, 2 - 0.1j]], dtype=np.complex128)
    return FlavorCorrelatorMatrix(matrix=matrix, status=COMPLETE_MULTIPLET)


def test_flavor_singlet_hand_verified() -> None:
    correlator = _hand_matrix()
    assert flavor_singlet(correlator) == pytest.approx((1 + 2j) + (2 - 0.1j))


def test_flavor_frobenius_squared_hand_verified() -> None:
    correlator = _hand_matrix()
    expected = abs(1 + 2j) ** 2 + abs(0.5 - 1j) ** 2 + abs(0.3j) ** 2 + abs(2 - 0.1j) ** 2
    assert flavor_frobenius_squared(correlator) == pytest.approx(expected)


def test_flavor_singular_values_are_descending_and_nonnegative() -> None:
    correlator = _hand_matrix()
    sigma_1, sigma_2 = flavor_singular_values(correlator)
    assert sigma_1 >= sigma_2 >= 0.0
    reference = np.linalg.svd(correlator.matrix, compute_uv=False)
    assert (sigma_1, sigma_2) == pytest.approx((reference[0], reference[1]))


def test_flavor_singular_value_ratio_normal_case() -> None:
    correlator = _hand_matrix()
    sigma_1, sigma_2 = flavor_singular_values(correlator)
    ratio = flavor_singular_value_ratio(correlator)
    assert ratio.null_reason is None
    assert ratio.value == pytest.approx(sigma_2 / sigma_1)


def test_flavor_singular_value_ratio_null_below_floor_uses_schema_authorized_reason() -> None:
    correlator = FlavorCorrelatorMatrix(matrix=np.zeros((2, 2), dtype=np.complex128), status=COMPLETE_MULTIPLET)
    ratio = flavor_singular_value_ratio(correlator, floor=NORMALIZATION_FLOOR)
    assert ratio.value is None
    assert ratio.null_reason == "normalization_denominator_below_floor"


def test_flavor_singular_value_ratio_null_reason_is_in_the_schema_enum() -> None:
    import json
    from pathlib import Path

    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "level1" / "correlators-v1.schema.json"
    schema = json.loads(schema_path.read_text())
    allowed = schema["properties"]["null_reason"]["enum"]
    assert "normalization_denominator_below_floor" in allowed
    assert "sigma_1_below_floor" not in allowed  # never invented by analogy


# ---------------------------------------------------------------------------
# V16 -- invariance under flavor rotations
# ---------------------------------------------------------------------------


def test_v16_frobenius_and_singular_values_invariant_under_independent_left_right_rotation() -> None:
    correlator = _hand_matrix()
    left = _deterministic_unitary(2, seed=101)
    right = _deterministic_unitary(2, seed=202)
    rotated = FlavorCorrelatorMatrix(matrix=left.conj().T @ correlator.matrix @ right, status=COMPLETE_MULTIPLET)

    assert flavor_frobenius_squared(rotated) == pytest.approx(flavor_frobenius_squared(correlator), abs=1e-10)
    assert flavor_singular_values(rotated) == pytest.approx(flavor_singular_values(correlator), abs=1e-10)


def test_v16_singlet_invariant_under_simultaneous_same_side_rotation() -> None:
    correlator = _hand_matrix()
    rotation = _deterministic_unitary(2, seed=303)
    rotated = FlavorCorrelatorMatrix(
        matrix=rotation.conj().T @ correlator.matrix @ rotation, status=COMPLETE_MULTIPLET
    )
    assert flavor_singlet(rotated) == pytest.approx(flavor_singlet(correlator), abs=1e-10)


def test_v16_singlet_not_invariant_under_independent_left_right_rotation() -> None:
    correlator = _hand_matrix()
    left = _deterministic_unitary(2, seed=404)
    right = _deterministic_unitary(2, seed=505)
    rotated = FlavorCorrelatorMatrix(matrix=left.conj().T @ correlator.matrix @ right, status=COMPLETE_MULTIPLET)
    assert flavor_singlet(rotated) != pytest.approx(flavor_singlet(correlator), abs=1e-6)
