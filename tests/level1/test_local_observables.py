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
    GroupMoment,
    NormalizedMoment,
    build_local_charge_operator,
    build_local_flavor_generator,
    build_local_flavor_generators,
    charge_correlator_connected,
    charge_correlator_connected_group,
    charge_correlator_raw,
    charge_correlator_raw_group,
    connected_moment,
    expectation_value,
    flavor_correlator_connected,
    flavor_correlator_connected_group,
    flavor_correlator_raw,
    flavor_correlator_raw_group,
    local_charge_product,
    local_flavor_dot_product,
    normalized_charge_correlator,
    raw_moment,
    FlavorTotalSumValidation,
    FLAVOR_TOTAL_SUM_TOLERANCE,
    validate_flavor_total_sum,
)
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    canonical_multiplet_expectation,
    extract_group_state,
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


# ---------------------------------------------------------------------------
# Multiplet generalization (Level1B lot 1B-8a, docs/decisions/decisions.md
# D020): GroupMoment, charge_correlator_{raw,connected}_group,
# flavor_correlator_{raw,connected}_group.
# ---------------------------------------------------------------------------


def _random_hermitian_csr(dim: int, seed: int) -> sp.csr_matrix:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))
    return sp.csr_matrix(raw + raw.conj().T)


def _random_commuting_hermitian_csr(dim: int, seed: int) -> sp.csr_matrix:
    """A real diagonal matrix: Hermitian, and its product with any other
    diagonal matrix stays Hermitian -- mirroring the physical precondition
    (Q_i/Q_j and T_i^a/T_j^a for i != j are particle-number-conserving
    bilinears at different sites, hence commuting, hence their product is
    Hermitian too) without needing a real lattice for a purely synthetic
    wiring test."""
    rng = np.random.default_rng(seed)
    return sp.diags(rng.normal(size=dim)).tocsr()


def _random_orthonormal_columns(dim: int, multiplicity: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dim, multiplicity)) + 1j * rng.normal(size=(dim, multiplicity))
    q, _ = np.linalg.qr(raw)
    return q[:, :multiplicity]


def _random_unitary(dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))
    q, _ = np.linalg.qr(raw)
    return q


def _triangle_s1_eigenvectors(n_eigenvalues: int):
    lattice, report, key_index = _build("triangle", spin=1)
    params = HamiltonianParameters(
        J=tuple(1.0 for _ in lattice.nodes),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in lattice.nodes),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, SPIN, report.keys, key_index, params)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, SPIN, report, terms, params, spectrum_options=SpectrumOptions(n_eigenvalues=n_eigenvalues)
    )
    return lattice, report, key_index, level0_report, eigenvectors


# --- 10. GroupMoment rejects NaN/Inf and an invalid status ----------------


def test_group_moment_rejects_non_finite_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        GroupMoment(value=float("nan"), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="finite"):
        GroupMoment(value=float("inf"), status=PARTIAL_SUBSPACE)


def test_group_moment_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        GroupMoment(value=0.0, status="degenerate")


# --- 1. multiplicity 1 reduces exactly to the pure-state functions --------


def test_group_correlators_reduce_to_pure_state_at_multiplicity_one() -> None:
    lattice, report, key_index = _build("triangle")
    Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Qj = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)
    Ti = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Tj = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)

    dim = len(report.keys)
    rng = np.random.default_rng(0)
    psi = rng.normal(size=dim) + 1j * rng.normal(size=dim)
    psi = psi / np.linalg.norm(psi)
    group_state = SpectralGroupState(psi=psi.reshape(-1, 1), status=COMPLETE_MULTIPLET)

    assert charge_correlator_raw_group(Qi, Qj, group_state).value == pytest.approx(charge_correlator_raw(Qi, Qj, psi))
    assert charge_correlator_connected_group(Qi, Qj, group_state).value == pytest.approx(
        charge_correlator_connected(Qi, Qj, psi)
    )
    assert flavor_correlator_raw_group(Ti, Tj, group_state).value == pytest.approx(flavor_correlator_raw(Ti, Tj, psi))
    assert flavor_correlator_connected_group(Ti, Tj, group_state).value == pytest.approx(
        flavor_correlator_connected(Ti, Tj, psi)
    )


# --- 2. invariance under an arbitrary unitary rotation, synthetic ---------


def test_group_correlators_are_invariant_under_synthetic_basis_rotation() -> None:
    dim = 6
    multiplicity = 3
    psi = _random_orthonormal_columns(dim, multiplicity, seed=11)
    group_state = SpectralGroupState(psi=psi, status=COMPLETE_MULTIPLET)
    unitary = _random_unitary(multiplicity, seed=12)
    rotated_state = SpectralGroupState(psi=psi @ unitary, status=COMPLETE_MULTIPLET)

    Qi = _random_commuting_hermitian_csr(dim, seed=13)
    Qj = _random_commuting_hermitian_csr(dim, seed=14)
    Ti = {component: _random_commuting_hermitian_csr(dim, seed=20 + index) for index, component in enumerate(FLAVOR_COMPONENTS)}
    Tj = {component: _random_commuting_hermitian_csr(dim, seed=30 + index) for index, component in enumerate(FLAVOR_COMPONENTS)}

    assert charge_correlator_raw_group(Qi, Qj, group_state).value == pytest.approx(
        charge_correlator_raw_group(Qi, Qj, rotated_state).value
    )
    assert charge_correlator_connected_group(Qi, Qj, group_state).value == pytest.approx(
        charge_correlator_connected_group(Qi, Qj, rotated_state).value
    )
    assert flavor_correlator_raw_group(Ti, Tj, group_state).value == pytest.approx(
        flavor_correlator_raw_group(Ti, Tj, rotated_state).value
    )
    assert flavor_correlator_connected_group(Ti, Tj, group_state).value == pytest.approx(
        flavor_correlator_connected_group(Ti, Tj, rotated_state).value
    )


# --- 3, 4. dispatch to canonical_multiplet_expectation (complete) or ------
# --- exploratory_partial_subspace_mean (partial), tested behaviorally -----
# --- by substituting both primitives with call-recording doubles ----------


def test_group_expectation_dispatches_to_canonical_for_a_complete_group(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"canonical": 0, "exploratory": 0}

    def fake_canonical(operator, group_state, *, hermitian, tolerance=1e-10):
        calls["canonical"] += 1
        return 0.0

    def fake_exploratory(operator, group_state, *, hermitian, tolerance=1e-10):
        calls["exploratory"] += 1
        return 0.0

    monkeypatch.setattr("cosmobox.level1.local_observables.canonical_multiplet_expectation", fake_canonical)
    monkeypatch.setattr("cosmobox.level1.local_observables.exploratory_partial_subspace_mean", fake_exploratory)

    dim = 4
    group_state = SpectralGroupState(psi=_random_orthonormal_columns(dim, 2, seed=40), status=COMPLETE_MULTIPLET)
    Qi = _random_hermitian_csr(dim, seed=41)
    Qj = _random_hermitian_csr(dim, seed=42)

    charge_correlator_raw_group(Qi, Qj, group_state)

    assert calls["canonical"] > 0
    assert calls["exploratory"] == 0


def test_group_expectation_dispatches_to_exploratory_for_a_partial_group(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"canonical": 0, "exploratory": 0}

    def fake_canonical(operator, group_state, *, hermitian, tolerance=1e-10):
        calls["canonical"] += 1
        return 0.0

    def fake_exploratory(operator, group_state, *, hermitian, tolerance=1e-10):
        calls["exploratory"] += 1
        return 0.0

    monkeypatch.setattr("cosmobox.level1.local_observables.canonical_multiplet_expectation", fake_canonical)
    monkeypatch.setattr("cosmobox.level1.local_observables.exploratory_partial_subspace_mean", fake_exploratory)

    dim = 4
    group_state = SpectralGroupState(psi=_random_orthonormal_columns(dim, 2, seed=50), status=PARTIAL_SUBSPACE)
    Qi = _random_hermitian_csr(dim, seed=51)
    Qj = _random_hermitian_csr(dim, seed=52)

    charge_correlator_raw_group(Qi, Qj, group_state)

    assert calls["exploratory"] > 0
    assert calls["canonical"] == 0


# --- 5. a partial group's status is never promoted ------------------------
# Built the production way: extract_group_state on a genuinely truncated
# window (n_eigenvalues=2 < the S=1 fundamental multiplicity of 4), so
# status == "partial_subspace" is DERIVED, never hand-set.


def test_group_moment_status_is_never_promoted_from_a_genuinely_truncated_group() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _triangle_s1_eigenvectors(n_eigenvalues=2)
    groups = level0_report.spectrum.degeneracy.groups
    assert len(groups) == 1
    assert groups[0].lower_bound_only is True  # window ended mid-multiplet: genuinely truncated

    group_state = extract_group_state(eigenvectors, groups[0])
    assert group_state.status == PARTIAL_SUBSPACE

    Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Qj = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)

    result = charge_correlator_raw_group(Qi, Qj, group_state)
    assert result.status == PARTIAL_SUBSPACE

    connected = charge_correlator_connected_group(Qi, Qj, group_state)
    assert connected.status == PARTIAL_SUBSPACE


# --- 6. connected = raw - product of canonical expectations ---------------


def test_charge_correlator_connected_group_equals_raw_minus_canonical_products() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _triangle_s1_eigenvectors(n_eigenvalues=16)
    fundamental = level0_report.spectrum.degeneracy.groups[0]
    assert fundamental.lower_bound_only is False  # genuinely complete (a higher group follows it)

    group_state = extract_group_state(eigenvectors, fundamental)
    Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Qj = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)

    connected = charge_correlator_connected_group(Qi, Qj, group_state)
    raw = charge_correlator_raw_group(Qi, Qj, group_state).value
    expectation_i = canonical_multiplet_expectation(Qi, group_state, hermitian=True)
    expectation_j = canonical_multiplet_expectation(Qj, group_state, hermitian=True)
    assert connected.value == pytest.approx(raw - expectation_i * expectation_j)


# --- 7. the flavor connected correlator is summed component by component,
# never as (sum raw) - (sum <T_i>)(sum <T_j>) -----------------------------


def test_flavor_correlator_connected_group_is_computed_component_by_component() -> None:
    dim = 5
    group_state = SpectralGroupState(psi=_random_orthonormal_columns(dim, 3, seed=60), status=COMPLETE_MULTIPLET)
    generators_i = {
        component: _random_commuting_hermitian_csr(dim, seed=100 + index) for index, component in enumerate(FLAVOR_COMPONENTS)
    }
    generators_j = {
        component: _random_commuting_hermitian_csr(dim, seed=200 + index) for index, component in enumerate(FLAVOR_COMPONENTS)
    }

    result = flavor_correlator_connected_group(generators_i, generators_j, group_state)

    expected_correct = 0.0
    for component in FLAVOR_COMPONENTS:
        raw_component = canonical_multiplet_expectation(
            (generators_i[component] @ generators_j[component]).tocsr(), group_state, hermitian=True
        )
        expectation_i = canonical_multiplet_expectation(generators_i[component], group_state, hermitian=True)
        expectation_j = canonical_multiplet_expectation(generators_j[component], group_state, hermitian=True)
        expected_correct += raw_component - expectation_i * expectation_j
    assert result.value == pytest.approx(expected_correct)

    # The forbidden formula (sum raw) - (sum <T_i>)(sum <T_j>) must give a
    # DIFFERENT answer for this generic random operator set, proving the
    # implementation is not silently equivalent to it.
    raw_sum = sum(
        canonical_multiplet_expectation(
            (generators_i[component] @ generators_j[component]).tocsr(), group_state, hermitian=True
        )
        for component in FLAVOR_COMPONENTS
    )
    expectation_i_sum = sum(
        canonical_multiplet_expectation(generators_i[component], group_state, hermitian=True)
        for component in FLAVOR_COMPONENTS
    )
    expectation_j_sum = sum(
        canonical_multiplet_expectation(generators_j[component], group_state, hermitian=True)
        for component in FLAVOR_COMPONENTS
    )
    forbidden = raw_sum - expectation_i_sum * expectation_j_sum
    assert result.value != pytest.approx(forbidden)


# --- 8. rho_QQ null at the (group-level) maximal-flavor sector ------------


def test_rho_qq_group_is_null_at_the_maximal_flavor_sector() -> None:
    lattice = build_lattice("triangle")
    spin = 2
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
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, spin, report, terms, params, spectrum_options=SpectrumOptions(n_eigenvalues=12)
    )
    groups = level0_report.spectrum.degeneracy.groups
    casimir = build_flavor_casimir(lattice, N_FLAVORS, spin, report.keys, key_index)

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

    group_state = extract_group_state(eigenvectors, target_group)
    charge_operators = [
        build_local_charge_operator(lattice, N_FLAVORS, spin, report.keys, key_index, node) for node in lattice.nodes
    ]
    variances = [charge_correlator_connected_group(Qi, Qi, group_state).value for Qi in charge_operators]
    for variance in variances:
        assert abs(variance) <= NORMALIZATION_FLOOR

    for i in range(n_nodes):
        for j in range(n_nodes):
            connected = charge_correlator_connected_group(charge_operators[i], charge_operators[j], group_state).value
            result = normalized_charge_correlator(connected, variances[i], variances[j])
            assert result.value is None
            assert result.null_reason == "zero_local_charge_variance"


# --- 9. no artificial epsilon substitution, at the exact floor boundary ---


def test_normalized_charge_correlator_uses_no_artificial_epsilon_for_group_sourced_values() -> None:
    result = normalized_charge_correlator(0.1, NORMALIZATION_FLOOR, 1.0)
    assert result.value is None
    assert result.null_reason == "zero_local_charge_variance"


# --- 11, 12. triangle S=1's genuinely degenerate fundamental multiplet, ---
# and unitary-rotation invariance evaluated on it -------------------------


def test_group_correlators_on_triangle_s1_degenerate_fundamental_multiplet() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _triangle_s1_eigenvectors(n_eigenvalues=16)
    fundamental = level0_report.spectrum.degeneracy.groups[0]
    assert fundamental.multiplicity_observed > 1  # a genuinely degenerate fundamental multiplet
    assert fundamental.lower_bound_only is False

    group_state = extract_group_state(eigenvectors, fundamental)
    Qi = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Qj = build_local_charge_operator(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)
    Ti = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 0)
    Tj = build_local_flavor_generators(lattice, N_FLAVORS, SPIN, report.keys, key_index, 1)

    raw_q = charge_correlator_raw_group(Qi, Qj, group_state)
    conn_q = charge_correlator_connected_group(Qi, Qj, group_state)
    raw_t = flavor_correlator_raw_group(Ti, Tj, group_state)
    conn_t = flavor_correlator_connected_group(Ti, Tj, group_state)
    for moment in (raw_q, conn_q, raw_t, conn_t):
        assert math.isfinite(moment.value)
        assert moment.status == COMPLETE_MULTIPLET

    dim = group_state.multiplicity
    unitary = _random_unitary(dim, seed=70)
    rotated_state = SpectralGroupState(psi=group_state.psi @ unitary, status=COMPLETE_MULTIPLET)

    assert charge_correlator_raw_group(Qi, Qj, rotated_state).value == pytest.approx(raw_q.value, abs=1e-10)
    assert charge_correlator_connected_group(Qi, Qj, rotated_state).value == pytest.approx(conn_q.value, abs=1e-10)
    assert flavor_correlator_raw_group(Ti, Tj, rotated_state).value == pytest.approx(raw_t.value, abs=1e-10)
    assert flavor_correlator_connected_group(Ti, Tj, rotated_state).value == pytest.approx(conn_t.value, abs=1e-10)


# ---------------------------------------------------------------------------
# validate_flavor_total_sum -- T(T+1) sum rule contract (1C-3b,
# docs/governance/current-task.md). Pure-logic tests only: real
# end-to-end coverage against actually-produced C_TT_conn records lives
# in tests/scripts/level1b_campaign/test_runner.py.
# ---------------------------------------------------------------------------


def test_validate_flavor_total_sum_not_applicable_for_partial_subspace() -> None:
    result = validate_flavor_total_sum(PARTIAL_SUBSPACE, 1, {0: 0.5}, {(0, 1): 0.1, (1, 0): 0.1})
    assert result.applicable is False
    assert result.measured is None
    assert result.expected is None
    assert result.residual is None
    assert result.is_valid is None


def test_validate_flavor_total_sum_not_applicable_when_twice_t_unresolved() -> None:
    result = validate_flavor_total_sum(COMPLETE_MULTIPLET, None, {0: 0.5}, {(0, 1): 0.1, (1, 0): 0.1})
    assert result.applicable is False


def test_validate_flavor_total_sum_exact_match_is_valid() -> None:
    # T = 1/2, T(T+1) = 0.75, split arbitrarily across 3 diagonal + 6
    # off-diagonal (ordered) terms summing exactly to 0.75.
    diagonal = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    result = validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)
    assert result.applicable is True
    assert result.measured == pytest.approx(0.75)
    assert result.expected == pytest.approx(0.75)
    assert result.residual == pytest.approx(0.0, abs=1e-15)
    assert result.is_valid is True


def test_validate_flavor_total_sum_residual_outside_tolerance_is_invalid() -> None:
    diagonal = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.01, (1, 0): 0.01, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    result = validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)
    assert result.residual == pytest.approx(0.02)
    assert result.residual > FLAVOR_TOTAL_SUM_TOLERANCE
    assert result.is_valid is False


def test_validate_flavor_total_sum_both_orders_counted_no_accidental_halving() -> None:
    # A structurally complete corpus with both orders present: summing
    # them must reproduce T(T+1) exactly -- if the implementation ever
    # divided the off-diagonal sum by two, this would silently fail.
    diagonal = {0: 0.0, 1: 0.0}
    both_orders = {(0, 1): 0.375, (1, 0): 0.375}
    result = validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, both_orders)
    assert result.applicable is True
    assert result.measured == pytest.approx(0.75)
    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Structural completeness (1C-3b corrective,
# docs/governance/current-task.md): an incomplete or inconsistent corpus
# must raise ValueError, never silently produce is_valid=False or, worse,
# a coincidental is_valid=True.
# ---------------------------------------------------------------------------


def test_validate_flavor_total_sum_c1_complete_corpus_still_valid() -> None:
    diagonal = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    result = validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)
    assert result.applicable is True
    assert result.is_valid is True


def test_validate_flavor_total_sum_c2_missing_one_direction_raises() -> None:
    diagonal = {0: 0.0, 1: 0.0}
    off_diagonal = {(0, 1): 0.375}  # (1, 0) missing
    with pytest.raises(ValueError, match="N\\*\\(N-1\\) ordered pairs"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)


def test_validate_flavor_total_sum_c3_missing_pair_entirely_raises() -> None:
    diagonal = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 2): 0.0, (2, 0): 0.0}  # (1,2)/(2,1) entirely absent
    with pytest.raises(ValueError, match="N\\*\\(N-1\\) ordered pairs"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)


def test_validate_flavor_total_sum_c4_diagonal_pair_in_off_diagonal_raises() -> None:
    diagonal = {0: 0.25, 1: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 0): 0.25}  # (0,0) does not belong here
    with pytest.raises(ValueError, match="N\\*\\(N-1\\) ordered pairs"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)


def test_validate_flavor_total_sum_c5_foreign_site_raises() -> None:
    diagonal = {0: 0.25, 1: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 2): 0.0}  # site 2 not in diagonal_values
    with pytest.raises(ValueError, match="N\\*\\(N-1\\) ordered pairs"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)


def test_validate_flavor_total_sum_c6_empty_diagonal_raises() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, {}, {})


def test_validate_flavor_total_sum_c7_structurally_complete_but_wrong_sum_is_invalid_not_an_error() -> None:
    # The essential distinction: a structurally COMPLETE corpus that
    # simply fails the physical sum rule is a normal scientific outcome
    # (is_valid=False), never an exception.
    diagonal = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.01, (1, 0): 0.01, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    result = validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)
    assert result.applicable is True
    assert result.residual > FLAVOR_TOTAL_SUM_TOLERANCE
    assert result.is_valid is False


def test_validate_flavor_total_sum_c8_partial_subspace_never_checks_completeness() -> None:
    # applicable=False is returned before any structural check -- an
    # incomplete/inconsistent corpus on a partial_subspace group must
    # never raise, since no verdict is ever attempted for it.
    incomplete_diagonal = {0: 0.5}
    incomplete_off_diagonal = {(0, 1): 0.1, (1, 0): 0.1}  # site 1 foreign to diagonal_values
    result = validate_flavor_total_sum(PARTIAL_SUBSPACE, 1, incomplete_diagonal, incomplete_off_diagonal)
    assert result.applicable is False
    assert result.measured is None
    assert result.expected is None
    assert result.residual is None
    assert result.is_valid is None


def test_validate_flavor_total_sum_rejects_non_int_twice_t() -> None:
    diagonal = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    with pytest.raises(ValueError, match="twice_T must be a non-negative int"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, True, diagonal, off_diagonal)  # bool, not a real int
    with pytest.raises(ValueError, match="twice_T must be a non-negative int"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, -1, diagonal, off_diagonal)
    with pytest.raises(ValueError, match="twice_T must be a non-negative int"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1.5, diagonal, off_diagonal)  # float, not int


def test_validate_flavor_total_sum_rejects_non_finite_values() -> None:
    diagonal = {0: float("nan"), 1: 0.25, 2: 0.25}
    off_diagonal = {(0, 1): 0.0, (1, 0): 0.0, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    with pytest.raises(ValueError, match="finite number"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal, off_diagonal)

    diagonal_ok = {0: 0.25, 1: 0.25, 2: 0.25}
    off_diagonal_inf = {(0, 1): float("inf"), (1, 0): 0.0, (0, 2): 0.0, (2, 0): 0.0, (1, 2): 0.0, (2, 1): 0.0}
    with pytest.raises(ValueError, match="finite number"):
        validate_flavor_total_sum(COMPLETE_MULTIPLET, 1, diagonal_ok, off_diagonal_inf)


def test_flavor_total_sum_validation_rejects_inconsistent_non_applicable() -> None:
    with pytest.raises(ValueError, match="non-applicable"):
        FlavorTotalSumValidation(applicable=False, measured=0.0, expected=None, residual=None, is_valid=None)


def test_flavor_total_sum_validation_rejects_incomplete_applicable() -> None:
    with pytest.raises(ValueError, match="applicable"):
        FlavorTotalSumValidation(applicable=True, measured=0.75, expected=0.75, residual=None, is_valid=None)
