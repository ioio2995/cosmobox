"""Unit tests for cosmobox.level2.adapter (lot L2-D2-LEVEL2-ADAPTER).

Every test uses hand-built synthetic objects (a hand-assembled Level0Report,
diagonal operators, standard-basis eigenvector columns) -- never a real
diagonalization, and never one of the six frozen Level2 fixtures (triangle,
ring4, ring5 x S=2, S=3). The single exception is test_build_case_operators_*,
which exercises the adapter's per-site operator wiring against
cosmobox.level0.lattice's "chain3" geometry: this is not a Level2 fixture
(Level2's frozen fixture set is exactly {triangle, ring4, ring5}), and no
Hamiltonian is built and no diagonalization runs -- only the already-tested
Level1 basis/operator construction is exercised, to check the adapter wires
it correctly.
"""

from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.degeneracy import analyze_spectral_degeneracies
from cosmobox.level0.hamiltonian import build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import (
    EigenpairDiagnostic,
    Level0Report,
    SpectrumOptions,
    SpectrumReport,
    TermExpectations,
    TermStatistics,
)
from cosmobox.level1.local_observables import (
    build_local_charge_operator,
    build_local_flavor_generators,
    charge_correlator_connected_group,
    flavor_correlator_connected_group,
    normalized_charge_correlator,
)
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, SpectralGroupState
from cosmobox.level2 import metrics, profiles
from cosmobox.level2.adapter import (
    CompleteMultiplet,
    PartialSubspaceCaseRejected,
    assemble_c_tt_conn,
    assemble_rho_qq,
    build_case_multiplet_profile,
    build_case_operators,
    extract_complete_multiplets,
    spectrum_energy_bounds,
)

_TERM_NAMES = ("dot", "hopping", "electric", "magnetic", "total")


# ---------------------------------------------------------------------------
# Synthetic fixtures -- no lattice, no basis, no Hamiltonian, no solver
# ---------------------------------------------------------------------------


def _synthetic_report(
    eigenvalues: list[float],
    *,
    degeneracy_dimension: int | None = None,
    report_dimension: int | None = None,
) -> Level0Report:
    """A hand-built, fully synthetic Level0Report. `degeneracy_dimension`
    controls window_truncated/lower_bound_only inside
    analyze_spectral_degeneracies (defaults to len(eigenvalues), i.e. an
    untruncated spectrum); `report_dimension` controls the
    Level0Report.dimension field the adapter itself reads (defaults to the
    same value) -- kept independently settable so a coverage mismatch can
    be tested without relying on a window-truncated spectrum."""
    n = len(eigenvalues)
    degeneracy_dimension = n if degeneracy_dimension is None else degeneracy_dimension
    report_dimension = degeneracy_dimension if report_dimension is None else report_dimension

    degeneracy = analyze_spectral_degeneracies(eigenvalues, dimension=degeneracy_dimension)
    eigenpairs = tuple(
        EigenpairDiagnostic(
            index=i,
            eigenvalue=e,
            residual_norm=0.0,
            term_expectations=TermExpectations(dot=0.0, hopping=0.0, electric=0.0, magnetic=0.0, total=e),
        )
        for i, e in enumerate(eigenvalues)
    )
    spectrum = SpectrumReport(
        status="computed",
        method="dense",
        requested_eigenvalues=n,
        computed_eigenvalues=n,
        tolerance=1e-10,
        reason=None,
        eigenpairs=eigenpairs,
        spectral_gap=(eigenvalues[1] - eigenvalues[0]) if n >= 2 else None,
        degeneracy=degeneracy,
    )
    term_stats = tuple(
        TermStatistics(name=name, nnz=0, density=0.0, hermiticity_defect=0.0, frobenius_norm=0.0)
        for name in _TERM_NAMES
    )
    parameters = HamiltonianParameters(J=(1.0,), h=(np.zeros((2, 2), dtype=complex),), t=1.0, g_E=1.0, K=1.0)
    return Level0Report(
        lattice_name="synthetic",
        n_flavors=2,
        spin=1,
        external_charges=(),
        dimension=report_dimension,
        sector_count=0,
        excluded_sector_count=0,
        mean_flux_configs_per_occupation=0.0,
        max_flux_configs_per_occupation=0,
        terms=term_stats,
        spectrum=spectrum,
        spectrum_options=SpectrumOptions(n_eigenvalues=n),
        parameters=parameters,
    )


def _diag(values) -> sp.spmatrix:
    return sp.diags(np.asarray(values, dtype=complex)).tocsr()


def _zero(n: int) -> sp.spmatrix:
    return sp.csr_matrix((n, n), dtype=complex)


def _orthonormal_columns(n: int, indices: list[int]) -> np.ndarray:
    """Standard-basis columns e_k for k in `indices` -- trivially
    orthonormal by construction, no QR/random matrix needed."""
    columns = np.zeros((n, len(indices)), dtype=complex)
    for column, index in enumerate(indices):
        columns[index, column] = 1.0
    return columns


def _complete_state(n: int, indices: list[int]) -> SpectralGroupState:
    return SpectralGroupState(psi=_orthonormal_columns(n, indices), status=COMPLETE_MULTIPLET)


def _partial_state(n: int, indices: list[int]) -> SpectralGroupState:
    return SpectralGroupState(psi=_orthonormal_columns(n, indices), status=PARTIAL_SUBSPACE)


# ---------------------------------------------------------------------------
# 1. extract_complete_multiplets
# ---------------------------------------------------------------------------


def test_extract_complete_multiplets_ordered_with_correct_multiplicities():
    eigenvalues = [0.0, 0.0, 1.0]  # group0 multiplicity 2, group1 multiplicity 1
    report = _synthetic_report(eigenvalues)
    eigenvectors = np.eye(3, dtype=complex)

    multiplets = extract_complete_multiplets(report, eigenvectors)

    assert len(multiplets) == 2
    assert [m.group.multiplicity_observed for m in multiplets] == [2, 1]
    assert [m.state.status for m in multiplets] == [COMPLETE_MULTIPLET, COMPLETE_MULTIPLET]
    assert [m.group.representative_energy for m in multiplets] == [0.0, 1.0]


def test_extract_complete_multiplets_rejects_any_partial_subspace():
    # window-truncated spectrum: 2 eigenvalues computed out of a declared
    # dimension of 5 -- the last group is lower_bound_only
    report = _synthetic_report([0.0, 1.0], degeneracy_dimension=5)
    eigenvectors = np.eye(2, dtype=complex)

    with pytest.raises(PartialSubspaceCaseRejected):
        extract_complete_multiplets(report, eigenvectors)


def test_extract_complete_multiplets_rejects_multiplicity_mismatch():
    # a fully untruncated spectrum (no partial_subspace group at all), but
    # a Level0Report.dimension field deliberately inconsistent with the
    # observed multiplicities
    report = _synthetic_report([0.0, 1.0, 2.0], report_dimension=5)
    eigenvectors = np.eye(3, dtype=complex)

    with pytest.raises(ValueError, match="does not cover the full spectrum"):
        extract_complete_multiplets(report, eigenvectors)


# ---------------------------------------------------------------------------
# CompleteMultiplet
# ---------------------------------------------------------------------------


def test_complete_multiplet_rejects_partial_subspace_state():
    group = _synthetic_report([0.0, 1.0]).spectrum.degeneracy.groups[0]
    state = _partial_state(2, [0])
    with pytest.raises(ValueError):
        CompleteMultiplet(group=group, state=state)


def test_complete_multiplet_rejects_multiplicity_mismatch():
    group = _synthetic_report([0.0, 1.0]).spectrum.degeneracy.groups[0]  # multiplicity 1
    state = _complete_state(2, [0, 1])  # multiplicity 2, mismatched
    with pytest.raises(ValueError):
        CompleteMultiplet(group=group, state=state)


# ---------------------------------------------------------------------------
# spectrum_energy_bounds
# ---------------------------------------------------------------------------


def test_spectrum_energy_bounds():
    report = _synthetic_report([-1.0, 0.5, 2.0])
    e_min, e_max = spectrum_energy_bounds(report)
    assert e_min == pytest.approx(-1.0)
    assert e_max == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# 2. assemble_c_tt_conn
# ---------------------------------------------------------------------------


def test_assemble_c_tt_conn_includes_diagonal_and_matches_direct_calls():
    n = 3
    state = _complete_state(n, [0, 1])
    generators = [
        {"x": _diag([1.0, 0.0, 2.0]), "y": _diag([0.0, 1.0, -1.0]), "z": _zero(n)},
        {"x": _diag([0.5, -0.5, 1.0]), "y": _zero(n), "z": _diag([2.0, 1.0, 0.0])},
    ]

    matrix = assemble_c_tt_conn(generators, state)

    assert matrix.shape == (2, 2)
    for i in range(2):
        for j in range(2):
            expected = flavor_correlator_connected_group(generators[i], generators[j], state).value
            assert matrix[i, j] == pytest.approx(expected)


def test_assemble_c_tt_conn_rejects_partial_subspace():
    n = 3
    state = _partial_state(n, [0, 1])
    generators = [
        {"x": _diag([1.0, 0.0, 2.0]), "y": _zero(n), "z": _zero(n)},
        {"x": _diag([0.5, -0.5, 1.0]), "y": _zero(n), "z": _zero(n)},
    ]
    with pytest.raises(ValueError, match=COMPLETE_MULTIPLET):
        assemble_c_tt_conn(generators, state)


# ---------------------------------------------------------------------------
# 3. assemble_rho_qq
# ---------------------------------------------------------------------------


def test_assemble_rho_qq_covers_all_ordered_pairs_and_matches_direct_calls():
    n = 4
    state = _complete_state(n, [0, 1])
    charges = [_diag([1.0, -1.0, 0.0, 0.0]), _diag([0.0, 1.0, 0.0, 0.0]), _diag([1.0, 0.0, 0.0, 0.0])]

    pairs = assemble_rho_qq(charges, state)

    expected_keys = {(i, j) for i in range(3) for j in range(3) if i != j}
    assert set(pairs.keys()) == expected_keys
    for (i, j), entry in pairs.items():
        connected_ij = charge_correlator_connected_group(charges[i], charges[j], state).value
        variance_i = charge_correlator_connected_group(charges[i], charges[i], state).value
        variance_j = charge_correlator_connected_group(charges[j], charges[j], state).value
        expected = normalized_charge_correlator(connected_ij, variance_i, variance_j)
        assert entry.value == expected.value
        assert entry.null_reason == expected.null_reason


def test_assemble_rho_qq_propagates_null_reason_without_imputation():
    n = 4
    state = _complete_state(n, [0, 1])  # multiplicity 2
    charges = [
        _diag([5.0, 5.0, 0.0, 0.0]),  # constant over the group -> zero variance
        _diag([1.0, 3.0, 0.0, 0.0]),  # varies over the group -> nonzero variance
        _diag([2.0, 4.0, 0.0, 0.0]),  # varies over the group -> nonzero variance
    ]

    pairs = assemble_rho_qq(charges, state)

    # every pair touching site 0 (zero-variance) is null, never imputed
    for pair in ((0, 1), (1, 0), (0, 2), (2, 0)):
        assert pairs[pair].value is None
        assert pairs[pair].null_reason == "zero_local_charge_variance"
    # the pair between the two nonzero-variance sites carries a numeric value
    assert pairs[(1, 2)].value is not None
    assert pairs[(1, 2)].null_reason is None
    assert pairs[(2, 1)].value is not None
    assert pairs[(2, 1)].null_reason is None


def test_assemble_rho_qq_rejects_partial_subspace():
    n = 2
    state = _partial_state(n, [0])
    charges = [_diag([1.0, 0.0]), _diag([0.0, 1.0])]
    with pytest.raises(ValueError, match=COMPLETE_MULTIPLET):
        assemble_rho_qq(charges, state)


# ---------------------------------------------------------------------------
# 5. build_case_operators
# ---------------------------------------------------------------------------


def test_build_case_operators_matches_direct_calls_on_a_non_level2_geometry():
    lattice = build_lattice("chain3")
    spin = 1
    n_flavors = 2
    basis = build_basis(lattice, n_flavors, spin)
    key_index = build_key_index(basis.keys)

    charge_operators, flavor_generators = build_case_operators(lattice, n_flavors, spin, basis.keys, key_index)

    assert len(charge_operators) == len(lattice.nodes)
    assert len(flavor_generators) == len(lattice.nodes)
    for position, node in enumerate(lattice.nodes):
        expected_charge = build_local_charge_operator(lattice, n_flavors, spin, basis.keys, key_index, node)
        assert (charge_operators[position] != expected_charge).nnz == 0

        expected_flavor = build_local_flavor_generators(lattice, n_flavors, spin, basis.keys, key_index, node)
        for component in ("x", "y", "z"):
            assert (flavor_generators[position][component] != expected_flavor[component]).nnz == 0


# ---------------------------------------------------------------------------
# 4/6/7. build_case_multiplet_profile -- end-to-end continuity into D1
# ---------------------------------------------------------------------------


def test_build_case_multiplet_profile_end_to_end_matches_manual_assembly_and_covers_q():
    eigenvalues = [0.0, 0.0, 2.0]  # group0 multiplicity 2, group1 multiplicity 1
    report = _synthetic_report(eigenvalues)
    eigenvectors = np.eye(3, dtype=complex)

    charges = [_diag([1.0, -1.0, 0.5]), _diag([0.0, 1.0, -0.5])]
    generators = [
        {"x": _diag([2.0, 0.0, 1.0]), "y": _zero(3), "z": _zero(3)},
        {"x": _diag([1.0, 2.0, 0.0]), "y": _zero(3), "z": _zero(3)},
    ]

    profile = build_case_multiplet_profile(report, eigenvectors, charges, generators)

    assert len(profile) == 2
    assert [entry.multiplicity for entry in profile] == [2, 1]
    assert sum(entry.multiplicity for entry in profile) == report.dimension

    # exact coverage of q in [0,1], contiguous, no gap or overlap
    assert profile[0].q_start == pytest.approx(0.0)
    assert profile[-1].q_end == pytest.approx(1.0)
    for previous, current in zip(profile, profile[1:]):
        assert previous.q_end == pytest.approx(current.q_start)

    # continuity: every field independently re-derived from the already
    # individually tested primitives, compared exactly
    multiplets = extract_complete_multiplets(report, eigenvectors)
    e_min, e_max = spectrum_energy_bounds(report)
    for entry, multiplet in zip(profile, multiplets):
        group = multiplet.group
        interval = profiles.spectral_interval(group.start_index, group.multiplicity_observed, report.dimension)
        c_tt_conn = assemble_c_tt_conn(generators, multiplet.state)
        rho_qq_pairs = assemble_rho_qq(charges, multiplet.state)

        assert entry.energy == pytest.approx(group.representative_energy)
        assert entry.multiplicity == group.multiplicity_observed
        assert entry.epsilon == pytest.approx(profiles.epsilon(group.representative_energy, e_min, e_max))
        assert entry.q_start == pytest.approx(interval.start)
        assert entry.q_end == pytest.approx(interval.end)
        assert entry.q_midpoint == pytest.approx(interval.q_mid)
        assert entry.m_tt == pytest.approx(metrics.m_tt(c_tt_conn))
        assert entry.a_qq == pytest.approx(metrics.a_qq(rho_qq_pairs, len(charges)))

        expected_r_eff = metrics.r_eff(c_tt_conn)
        assert entry.r_eff.value == expected_r_eff.value
        assert entry.r_eff.reason == expected_r_eff.reason

        expected_m_qq = metrics.m_qq(rho_qq_pairs, len(charges))
        assert entry.m_qq.value == expected_m_qq.value
        assert entry.m_qq.reason == expected_m_qq.reason


def test_build_case_multiplet_profile_rejects_partial_subspace_case():
    report = _synthetic_report([0.0, 1.0], degeneracy_dimension=5)
    eigenvectors = np.eye(2, dtype=complex)
    charges = [_diag([1.0, 0.0]), _diag([0.0, 1.0])]
    generators = [
        {"x": _diag([1.0, 0.0]), "y": _zero(2), "z": _zero(2)},
        {"x": _diag([0.0, 1.0]), "y": _zero(2), "z": _zero(2)},
    ]
    with pytest.raises(PartialSubspaceCaseRejected):
        build_case_multiplet_profile(report, eigenvectors, charges, generators)


def test_build_case_multiplet_profile_rejects_mismatched_operator_counts():
    report = _synthetic_report([0.0, 1.0])
    eigenvectors = np.eye(2, dtype=complex)
    charges = [_diag([1.0, 0.0])]
    generators = [
        {"x": _diag([1.0, 0.0]), "y": _zero(2), "z": _zero(2)},
        {"x": _diag([0.0, 1.0]), "y": _zero(2), "z": _zero(2)},
    ]
    with pytest.raises(ValueError, match="charge_operators"):
        build_case_multiplet_profile(report, eigenvectors, charges, generators)
