from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import decode, encode
from cosmobox.level0.gauge import gauss_vector, node_charge
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir, build_flavor_generators
from cosmobox.level1.local_observables import (
    FLAVOR_COMPONENTS,
    NORMALIZATION_FLOOR,
    NormalizedMoment,
    build_local_charge_operator,
    build_local_flavor_generator,
    build_local_flavor_generators,
    charge_correlator_connected,
    charge_correlator_raw,
    connected_moment,
    expectation_value,
    flavor_correlator_connected,
    flavor_correlator_raw,
    local_charge_product,
    local_flavor_dot_product,
    normalized_charge_correlator,
    raw_moment,
)

N_FLAVORS = 2
SPIN = 1


def _build(geometry: str, spin: int = SPIN):
    lattice = build_lattice(geometry)
    report = build_basis(lattice, N_FLAVORS, spin)
    key_index = build_key_index(report.keys)
    return lattice, report, key_index


def _hermiticity_defect(matrix: sp.spmatrix) -> float:
    difference = (matrix - matrix.conj().T).tocsr()
    difference.eliminate_zeros()
    return float(np.max(np.abs(difference.data))) if difference.nnz else 0.0


def _frobenius_diff(a: sp.spmatrix, b: sp.spmatrix) -> float:
    diff = (a - b).tocsr()
    diff.eliminate_zeros()
    return float(np.sqrt(np.sum(np.abs(diff.data) ** 2))) if diff.nnz else 0.0


# ---------------------------------------------------------------------------
# build_local_charge_operator
# ---------------------------------------------------------------------------


def test_build_local_charge_operator_rejects_n_flavors_other_than_two() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, 3, SPIN)
    key_index = build_key_index(report.keys)
    with pytest.raises(ValueError, match="n_flavors == 2"):
        build_local_charge_operator(lattice, 3, SPIN, report.keys, key_index, 0)


@pytest.mark.parametrize("geometry", ["triangle", "ring4"])
def test_local_charge_operator_is_hermitian(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    assert _hermiticity_defect(Qi) < 1e-12


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5"])
def test_local_charge_operator_spectrum_is_subset_of_minus1_0_1(geometry: str) -> None:
    # spectrum(Q_i) subset of {-1, 0, 1} -- not every value need be present
    # for every node/basis.
    lattice, report, key_index = _build(geometry)
    for node in lattice.nodes:
        Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, node)
        diagonal = np.asarray(Qi.todense()).diagonal()
        off_diagonal = (Qi - sp.diags(diagonal)).tocsr()
        off_diagonal.eliminate_zeros()
        assert off_diagonal.nnz == 0  # Q_i is exactly diagonal
        rounded = {int(round(value.real)) for value in diagonal}
        assert rounded <= {-1, 0, 1}
        for value in diagonal:
            assert abs(value.imag) < 1e-12
            assert abs(value.real - round(value.real)) < 1e-12


@pytest.mark.parametrize("geometry", ["triangle", "ring4", "ring5"])
def test_local_charge_operator_diagonal_matches_gauge_node_charge(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    for node in lattice.nodes:
        Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, node)
        diagonal = np.asarray(Qi.todense()).diagonal()
        for key in report.keys:
            occupation, _flux = decode(lattice, N_FLAVORS, SPIN, key)
            expected = float(node_charge(occupation, node, N_FLAVORS))
            row = key_index[int(key)]
            assert diagonal[row].real == pytest.approx(expected, abs=1e-12)
            assert diagonal[row].imag == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# build_local_flavor_generator(s)
# ---------------------------------------------------------------------------


def test_build_local_flavor_generator_rejects_n_flavors_other_than_two() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, 3, SPIN)
    key_index = build_key_index(report.keys)
    with pytest.raises(ValueError, match="n_flavors == 2"):
        build_local_flavor_generator(lattice, 3, SPIN, report.keys, key_index, 0, "x")


def test_build_local_flavor_generator_rejects_unknown_component() -> None:
    lattice, report, key_index = _build("triangle")
    with pytest.raises(ValueError, match="component"):
        build_local_flavor_generator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0, "w")


@pytest.mark.parametrize("geometry", ["triangle", "ring4"])
def test_local_flavor_generators_are_hermitian(geometry: str) -> None:
    lattice, report, key_index = _build(geometry)
    generators = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    for component in FLAVOR_COMPONENTS:
        assert _hermiticity_defect(generators[component]) < 1e-12


def test_local_flavor_generators_satisfy_su2_algebra_at_the_same_node() -> None:
    lattice, report, key_index = _build("triangle")
    generators = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    tx, ty, tz = generators["x"], generators["y"], generators["z"]
    for a, b, c in ((tx, ty, tz), (ty, tz, tx), (tz, tx, ty)):
        commutator = (a @ b - b @ a).tocsr()
        expected = (1j * c).tocsr()
        assert _frobenius_diff(commutator, expected) < 1e-10


@pytest.mark.parametrize("geometry", ["triangle", "ring4"])
def test_local_flavor_generators_sum_to_the_global_generators(geometry: str) -> None:
    # The key non-redefinition proof: the LOCAL per-node construction,
    # summed over every node, must equal the EXISTING global
    # build_flavor_generators exactly -- not merely "by design", proven.
    lattice, report, key_index = _build(geometry)
    n_nodes = len(lattice.nodes)
    dim = len(report.keys)

    sums = {component: sp.csr_matrix((dim, dim), dtype=np.complex128) for component in FLAVOR_COMPONENTS}
    for node in range(n_nodes):
        generators = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, node)
        for component in FLAVOR_COMPONENTS:
            sums[component] = sums[component] + generators[component]

    global_x, global_y, global_z = build_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index)
    for component, expected in zip(FLAVOR_COMPONENTS, (global_x, global_y, global_z)):
        diff = (sums[component] - expected).tocsr()
        diff.eliminate_zeros()
        assert diff.nnz == 0 or np.max(np.abs(diff.data)) < 1e-12


# ---------------------------------------------------------------------------
# Gauss-law commutation (T3-style, full unconstrained space)
# ---------------------------------------------------------------------------


def _full_unconstrained_keys(lattice, n_flavors, spin):
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    return [
        encode(lattice, n_flavors, spin, occupation, flux)
        for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors)
        for flux in itertools.product(range(-spin, spin + 1), repeat=n_edges)
    ]


def _gauss_operator(lattice, n_flavors, spin, all_keys, node):
    values = np.empty(len(all_keys), dtype=np.complex128)
    for row, key in enumerate(all_keys):
        occupation, flux = decode(lattice, n_flavors, spin, key)
        values[row] = complex(float(gauss_vector(lattice, n_flavors, occupation, flux)[node]))
    return sp.diags(values).tocsr()


def test_local_charge_and_flavor_operators_commute_with_gauss_law() -> None:
    lattice = build_lattice("triangle")
    all_keys = _full_unconstrained_keys(lattice, N_FLAVORS, SPIN)
    key_index = build_key_index(all_keys)

    Q0 = build_local_charge_operator(lattice, N_FLAVORS, SPIN, all_keys, key_index, 0)
    generators = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, all_keys, key_index, 0)
    operators = [Q0, generators["x"], generators["y"], generators["z"]]

    for node in lattice.nodes:
        g_operator = _gauss_operator(lattice, N_FLAVORS, SPIN, all_keys, node)
        for operator in operators:
            commutator = (operator @ g_operator - g_operator @ operator).tocsr()
            commutator.eliminate_zeros()
            if commutator.nnz:
                assert np.max(np.abs(commutator.data)) < 1e-10


# ---------------------------------------------------------------------------
# Two-site products -- i == j required (rho_QQ's denominator)
# ---------------------------------------------------------------------------


def test_local_charge_product_accepts_i_equals_j() -> None:
    lattice, report, key_index = _build("triangle")
    Q0 = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    product = local_charge_product(Q0, Q0)
    # Q_i^2 has eigenvalues in {0, 1} since Q_i's eigenvalues are in {-1,0,1}.
    diagonal = np.asarray(product.todense()).diagonal()
    rounded = {int(round(value.real)) for value in diagonal}
    assert rounded <= {0, 1}


def test_local_flavor_dot_product_accepts_i_equals_j() -> None:
    lattice, report, key_index = _build("triangle")
    generators = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    product = local_flavor_dot_product(generators, generators)
    assert _hermiticity_defect(product) < 1e-10


def test_local_charge_product_distinct_nodes() -> None:
    lattice, report, key_index = _build("triangle")
    Q0 = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Q1 = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)
    product = local_charge_product(Q0, Q1)
    assert _hermiticity_defect(product) < 1e-10  # Q_0, Q_1 commute (both diagonal)


# ---------------------------------------------------------------------------
# expectation_value -- explicit exceptions (not bare asserts), shape and
# normalization contract
# ---------------------------------------------------------------------------


def test_expectation_value_hand_verified_case() -> None:
    operator = sp.csr_matrix(np.diag([1.0, -1.0]).astype(np.complex128))
    psi = np.array([1.0, 0.0], dtype=np.complex128)
    assert expectation_value(operator, psi) == pytest.approx(1.0)


def test_expectation_value_rejects_non_square_operator() -> None:
    operator = sp.csr_matrix((2, 3), dtype=np.complex128)
    psi = np.zeros(2, dtype=np.complex128)
    with pytest.raises(ValueError, match="square"):
        expectation_value(operator, psi)


def test_expectation_value_rejects_wrong_psi_length() -> None:
    operator = sp.identity(3, format="csr", dtype=np.complex128)
    psi = np.array([1.0, 0.0], dtype=np.complex128)
    with pytest.raises(ValueError, match="1-D array of length"):
        expectation_value(operator, psi)


def test_expectation_value_rejects_wrong_psi_ndim() -> None:
    operator = sp.identity(2, format="csr", dtype=np.complex128)
    psi = np.eye(2, dtype=np.complex128)
    with pytest.raises(ValueError, match="1-D array"):
        expectation_value(operator, psi)


def test_expectation_value_rejects_unnormalized_psi() -> None:
    operator = sp.identity(2, format="csr", dtype=np.complex128)
    psi = np.array([1.0, 1.0], dtype=np.complex128)  # ||psi|| = sqrt(2)
    with pytest.raises(ValueError, match="normalized"):
        expectation_value(operator, psi)


def test_expectation_value_rejects_non_negligible_imaginary_part() -> None:
    # A deliberately non-Hermitian operator: <psi|O|psi> is not guaranteed
    # real. <psi|O|psi> = conj([1,1j]) . O@[1,1j] / 2 = conj([1,1j]) . [1j,0] / 2
    # = (1*1j)/2 = 0.5j, purely imaginary.
    operator = sp.csr_matrix(np.array([[0, 1], [0, 0]], dtype=np.complex128))
    psi = np.array([1.0, 1.0j], dtype=np.complex128) / math.sqrt(2)
    with pytest.raises(ValueError, match="imaginary part"):
        expectation_value(operator, psi)


# ---------------------------------------------------------------------------
# raw_moment / connected_moment -- hand-verified, same-psi consistency
# ---------------------------------------------------------------------------


def test_raw_and_connected_moment_hand_verified() -> None:
    operator_i = sp.csr_matrix(np.diag([1.0, -1.0]).astype(np.complex128))
    operator_j = sp.csr_matrix(np.diag([2.0, 0.0]).astype(np.complex128))
    psi = np.array([1.0, 0.0], dtype=np.complex128)

    raw = raw_moment(operator_i, operator_j, psi)
    assert raw == pytest.approx(2.0)  # (1*2) on the |0> component

    connected = connected_moment(operator_i, operator_j, psi)
    expectation_i = expectation_value(operator_i, psi)
    expectation_j = expectation_value(operator_j, psi)
    assert connected == pytest.approx(raw - expectation_i * expectation_j)


def test_charge_and_flavor_correlators_accept_i_equals_j() -> None:
    lattice, report, key_index = _build("triangle")
    Q0 = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    T0 = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    dim = len(report.keys)
    psi = np.zeros(dim, dtype=np.complex128)
    psi[0] = 1.0

    c_qq_ii = charge_correlator_connected(Q0, Q0, psi)
    c_tt_ii = flavor_correlator_connected(T0, T0, psi)
    assert isinstance(c_qq_ii, float)
    assert isinstance(c_tt_ii, float)
    assert charge_correlator_raw(Q0, Q0, psi) >= 0.0  # <Q_i^2> >= 0


# ---------------------------------------------------------------------------
# NormalizedMoment / rho_QQ rule
# ---------------------------------------------------------------------------


def test_normalized_moment_rejects_value_without_reason() -> None:
    with pytest.raises(ValueError):
        NormalizedMoment(value=1.0, null_reason="zero_local_charge_variance")


def test_normalized_moment_rejects_reason_without_none_value() -> None:
    with pytest.raises(ValueError):
        NormalizedMoment(value=None, null_reason=None)


def test_rho_qq_normal_case() -> None:
    result = normalized_charge_correlator(0.5, 1.0, 1.0)
    assert result.null_reason is None
    assert result.value == pytest.approx(0.5)


def test_rho_qq_null_on_exactly_zero_variance() -> None:
    result = normalized_charge_correlator(0.0, 0.0, 1.0)
    assert result.value is None
    assert result.null_reason == "zero_local_charge_variance"


def test_rho_qq_clamps_small_negative_variance_then_nulls() -> None:
    tiny_negative = -NORMALIZATION_FLOOR / 2
    result = normalized_charge_correlator(0.0, tiny_negative, 1.0)
    assert result.value is None
    assert result.null_reason == "zero_local_charge_variance"


def test_rho_qq_raises_on_variance_more_negative_than_floor() -> None:
    with pytest.raises(ValueError, match="not numerical noise"):
        normalized_charge_correlator(0.0, -10 * NORMALIZATION_FLOOR, 1.0)


def test_rho_qq_never_produces_denominator_below_floor_reason() -> None:
    # With both variances individually above the floor, the product's
    # sqrt cannot itself be below the floor (each factor >= floor), so
    # the case exhaustively sampled here must always be either a normal
    # value or "zero_local_charge_variance" -- never any other reason.
    for variance_i in (NORMALIZATION_FLOOR, NORMALIZATION_FLOOR * 1.0001, 1e-6, 1.0):
        for variance_j in (NORMALIZATION_FLOOR, NORMALIZATION_FLOOR * 1.0001, 1e-6, 1.0):
            result = normalized_charge_correlator(0.1, variance_i, variance_j)
            assert result.null_reason in (None, "zero_local_charge_variance")


# ---------------------------------------------------------------------------
# V12 -- parity of T, ring4: purely structural/combinatorial, no diagonalization
# ---------------------------------------------------------------------------


def test_v12_ring4_total_occupation_is_always_even_so_t_3_2_is_impossible() -> None:
    lattice = build_lattice("ring4")
    report = build_basis(lattice, N_FLAVORS, SPIN, external_charges=None)
    for key in report.keys:
        occupation, _flux = decode(lattice, N_FLAVORS, SPIN, key)
        n_tot = sum(occupation)
        assert n_tot % 2 == 0  # n even => T integer everywhere => T=3/2 impossible


def test_v12_ring4_flavor_casimir_spectrum_never_reaches_15_over_4() -> None:
    # Empirical confirmation on the full physical basis (dim=152 at S=1,
    # cheap and exhaustive -- not sampled).
    lattice, report, key_index = _build("ring4")
    casimir = build_flavor_casimir(lattice, N_FLAVORS, SPIN, report.keys, key_index)
    eigenvalues = np.linalg.eigvalsh(casimir.toarray())
    assert not np.any(np.abs(eigenvalues - 3.75) < 1e-8)


# ---------------------------------------------------------------------------
# V11 -- maximal-flavor sector, triangle: identified by computed labels
# (T^2, multiplicity, non-truncation), never by energy rank alone
# ---------------------------------------------------------------------------


def test_v11_maximal_flavor_sector_gives_null_rho_qq_and_zero_charge_correlators() -> None:
    lattice = build_lattice("triangle")
    spin = 2  # S=2 scientific reference, per docs/model/physical-model.md
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
    options = SpectrumOptions(n_eigenvalues=12)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, spin, report, terms, params, spectrum_options=options
    )
    groups = level0_report.spectrum.degeneracy.groups
    casimir = build_flavor_casimir(lattice, N_FLAVORS, spin, report.keys, key_index)

    # Identify the target group by its COMPUTED labels -- T^2 = 15/4 and a
    # complete (non-truncated) multiplicity-4 group -- never by energy.
    target_group = None
    for group in groups:
        if group.multiplicity_observed != 4 or group.lower_bound_only:
            continue
        psi_columns = eigenvectors[:, group.start_index : group.end_index_exclusive]
        t2_values = [
            expectation_value(casimir, psi_columns[:, k]) for k in range(psi_columns.shape[1])
        ]
        if all(abs(value - 3.75) < 1e-8 for value in t2_values):
            target_group = group
            break

    assert target_group is not None, "no complete multiplicity-4 T^2=15/4 group found"
    # Energy is only a secondary sanity check here, never the selector.
    assert target_group.representative_energy == pytest.approx(-1.612369, abs=1e-3)

    psi = eigenvectors[:, target_group.start_index]

    charge_operators = [
        build_local_charge_operator(lattice, N_FLAVORS, spin, report.keys, key_index, node)
        for node in lattice.nodes
    ]

    for node, Qi in enumerate(charge_operators):
        assert expectation_value(Qi, psi) == pytest.approx(0.0, abs=1e-8)

    variances = [charge_correlator_connected(Qi, Qi, psi) for Qi in charge_operators]
    for variance in variances:
        assert abs(variance) <= NORMALIZATION_FLOOR

    for i in range(n_nodes):
        for j in range(n_nodes):
            c_qq = charge_correlator_connected(charge_operators[i], charge_operators[j], psi)
            assert abs(c_qq) <= NORMALIZATION_FLOOR

            # V15: only the internal null representation is tested here --
            # JSON serialization and schema conformance are out of scope
            # for this lot.
            result = normalized_charge_correlator(c_qq, variances[i], variances[j])
            assert result.value is None
            assert result.null_reason == "zero_local_charge_variance"
