"""Unit tests for cosmobox.level2.adapter (lot L2-D2-LEVEL2-ADAPTER).

Every test uses hand-built synthetic objects only: a hand-assembled
Level0Report, diagonal operators, standard-basis eigenvector columns, and
(for build_case_operators) a minimal synthetic lattice-like object exposing
only `.nodes`, with the two Level1 builders it calls replaced by
monkeypatched fakes. No real lattice, basis, or diagonalization is built
anywhere in this file, and no catalog geometry (Level2's six frozen cases
or otherwise) is used.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.degeneracy import analyze_spectral_degeneracies
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
    charge_correlator_connected_group,
    flavor_correlator_connected_group,
    normalized_charge_correlator,
)
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, SpectralGroupState
from cosmobox.level2 import adapter as level2_adapter
from cosmobox.level2 import metrics, profiles
from cosmobox.level2.adapter import (
    CompleteMultiplet,
    MultipletProfileEntry,
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


def test_build_case_operators_wires_one_call_per_site_in_order(monkeypatch):
    # Synthetic, minimal lattice-like object exposing only what
    # build_case_operators reads: `.nodes`. Not build_lattice's Lattice,
    # not any catalog geometry.
    lattice = SimpleNamespace(nodes=(10, 20, 30))
    n_flavors = 2
    spin = 3
    keys = "synthetic-keys"
    key_index = {"synthetic": "key-index"}

    charge_calls: list[tuple] = []
    flavor_calls: list[tuple] = []

    def fake_build_local_charge_operator(lattice_arg, n_flavors_arg, spin_arg, keys_arg, key_index_arg, node):
        charge_calls.append((lattice_arg, n_flavors_arg, spin_arg, keys_arg, key_index_arg, node))
        return f"charge-operator-{node}"

    def fake_build_local_flavor_generators(lattice_arg, n_flavors_arg, spin_arg, keys_arg, key_index_arg, node):
        flavor_calls.append((lattice_arg, n_flavors_arg, spin_arg, keys_arg, key_index_arg, node))
        return {"x": f"flavor-x-{node}", "y": f"flavor-y-{node}", "z": f"flavor-z-{node}"}

    monkeypatch.setattr(level2_adapter, "build_local_charge_operator", fake_build_local_charge_operator)
    monkeypatch.setattr(level2_adapter, "build_local_flavor_generators", fake_build_local_flavor_generators)

    charge_operators, flavor_generators = build_case_operators(lattice, n_flavors, spin, keys, key_index)

    # exactly one call per site, in lattice.nodes order -- never rebuilt,
    # never called for anything spectral-group-related (build_case_operators
    # takes no group_state at all)
    expected_call_args = [(lattice, n_flavors, spin, keys, key_index, node) for node in lattice.nodes]
    assert charge_calls == expected_call_args
    assert flavor_calls == expected_call_args

    # the returned tuples are exactly the mocked builders' return values,
    # in the same site order
    assert charge_operators == tuple(f"charge-operator-{node}" for node in lattice.nodes)
    assert flavor_generators == tuple(
        {"x": f"flavor-x-{node}", "y": f"flavor-y-{node}", "z": f"flavor-z-{node}"} for node in lattice.nodes
    )


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

        # L2-E1: the retained raw observables are exactly the same
        # objects/values that fed m_tt/r_eff/a_qq/m_qq above -- never a
        # second, independently recomputed copy
        assert np.array_equal(entry.c_tt_conn, c_tt_conn)
        assert entry.c_tt_conn.shape == (len(charges), len(charges))
        n = len(charges)
        assert len(entry.rho_qq) == n * (n - 1)
        for key, expected_entry in rho_qq_pairs.items():
            assert entry.rho_qq[key].value == expected_entry.value
            assert entry.rho_qq[key].null_reason == expected_entry.null_reason


# ---------------------------------------------------------------------------
# L2-E1-RAW-OBSERVABLE-RETENTION: c_tt_conn/rho_qq retention, immutability,
# and null preservation on MultipletProfileEntry
# ---------------------------------------------------------------------------


def test_multiplet_profile_entry_retains_full_c_tt_conn_matrix_diagonal_included():
    report = _synthetic_report([0.0, 0.0, 2.0])
    eigenvectors = np.eye(3, dtype=complex)
    charges = [_diag([1.0, -1.0, 0.5]), _diag([0.0, 1.0, -0.5])]
    generators = [
        {"x": _diag([2.0, 0.0, 1.0]), "y": _zero(3), "z": _zero(3)},
        {"x": _diag([1.0, 2.0, 0.0]), "y": _zero(3), "z": _zero(3)},
    ]

    profile = build_case_multiplet_profile(report, eigenvectors, charges, generators)
    multiplets = extract_complete_multiplets(report, eigenvectors)

    for entry, multiplet in zip(profile, multiplets):
        expected = assemble_c_tt_conn(generators, multiplet.state)
        assert entry.c_tt_conn is not None
        assert entry.c_tt_conn.shape == (2, 2)
        # the diagonal is present in the retained matrix (never stripped
        # before persistence), whatever value this multiplet's own
        # connected moment happens to produce
        assert entry.c_tt_conn[0, 0] == pytest.approx(expected[0, 0])
        assert entry.c_tt_conn[1, 1] == pytest.approx(expected[1, 1])
        assert np.array_equal(entry.c_tt_conn, expected)


def test_multiplet_profile_entry_c_tt_conn_is_immutable():
    report = _synthetic_report([0.0, 0.0, 2.0])
    eigenvectors = np.eye(3, dtype=complex)
    charges = [_diag([1.0, -1.0, 0.5]), _diag([0.0, 1.0, -0.5])]
    generators = [
        {"x": _diag([2.0, 0.0, 1.0]), "y": _zero(3), "z": _zero(3)},
        {"x": _diag([1.0, 2.0, 0.0]), "y": _zero(3), "z": _zero(3)},
    ]

    profile = build_case_multiplet_profile(report, eigenvectors, charges, generators)

    entry = profile[0]
    assert entry.c_tt_conn.flags.writeable is False
    with pytest.raises(ValueError):
        entry.c_tt_conn[0, 0] = 999.0
    # setflags(write=False) alone would leave the underlying buffer itself
    # writeable and reversible by a caller via setflags(write=True); the
    # backing buffer must be genuinely non-writeable so this re-enable
    # attempt itself raises, not just direct element assignment above.
    with pytest.raises(ValueError):
        entry.c_tt_conn.setflags(write=True)
    assert entry.c_tt_conn.flags.writeable is False


def test_multiplet_profile_entry_rho_qq_is_immutable():
    report = _synthetic_report([0.0, 0.0, 2.0])
    eigenvectors = np.eye(3, dtype=complex)
    charges = [_diag([1.0, -1.0, 0.5]), _diag([0.0, 1.0, -0.5])]
    generators = [
        {"x": _diag([2.0, 0.0, 1.0]), "y": _zero(3), "z": _zero(3)},
        {"x": _diag([1.0, 2.0, 0.0]), "y": _zero(3), "z": _zero(3)},
    ]

    profile = build_case_multiplet_profile(report, eigenvectors, charges, generators)

    entry = profile[0]
    with pytest.raises(TypeError):
        entry.rho_qq[(0, 1)] = metrics.RhoQQEntry(0.0, None)


def test_multiplet_profile_entry_rho_qq_preserves_null_reason_without_imputation():
    n = 3
    state = _complete_state(n, [0, 1])  # multiplicity 2
    charges = [
        _diag([5.0, 5.0, 0.0]),  # constant over the group -> zero variance -> null
        _diag([1.0, 3.0, 0.0]),  # varies over the group -> numeric
    ]
    rho_qq_pairs = assemble_rho_qq(charges, state)

    report = _synthetic_report([0.0, 0.0, 2.0])
    eigenvectors = np.eye(3, dtype=complex)
    generators = [
        {"x": _diag([2.0, 0.0, 1.0]), "y": _zero(3), "z": _zero(3)},
        {"x": _diag([1.0, 2.0, 0.0]), "y": _zero(3), "z": _zero(3)},
    ]
    profile = build_case_multiplet_profile(report, eigenvectors, charges, generators)

    # cross-check: at least one pair from the same charges/state is null,
    # and MultipletProfileEntry.rho_qq preserves it exactly (never imputed to 0)
    assert rho_qq_pairs[(0, 1)].value is None
    assert rho_qq_pairs[(0, 1)].null_reason == "zero_local_charge_variance"

    entry = profile[0]
    assert entry.rho_qq[(0, 1)].value is None
    assert entry.rho_qq[(0, 1)].null_reason == "zero_local_charge_variance"


def test_multiplet_profile_entry_defaults_allow_backward_compatible_construction():
    # Direct construction without c_tt_conn/rho_qq must keep working
    # unchanged, for every synthetic fixture outside this lot's authorized
    # scope that already constructs MultipletProfileEntry this way.
    entry = MultipletProfileEntry(
        energy=0.0, multiplicity=1, epsilon=0.0, q_start=0.0, q_end=1.0, q_midpoint=0.5,
        m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
    )
    assert entry.c_tt_conn is None
    assert entry.rho_qq is None


def test_multiplet_profile_entry_rejects_non_square_c_tt_conn():
    with pytest.raises(ValueError):
        MultipletProfileEntry(
            energy=0.0, multiplicity=1, epsilon=0.0, q_start=0.0, q_end=1.0, q_midpoint=0.5,
            m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
            c_tt_conn=np.zeros((2, 3)),
        )


def test_multiplet_profile_entry_rejects_rho_qq_dimension_mismatch_with_c_tt_conn():
    with pytest.raises(ValueError):
        MultipletProfileEntry(
            energy=0.0, multiplicity=1, epsilon=0.0, q_start=0.0, q_end=1.0, q_midpoint=0.5,
            m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
            c_tt_conn=np.zeros((2, 2)),
            rho_qq={(0, 1): metrics.RhoQQEntry(0.0, None)},  # missing (1, 0)
        )


def test_multiplet_profile_entry_rejects_diagonal_key_in_rho_qq():
    with pytest.raises(ValueError):
        MultipletProfileEntry(
            energy=0.0, multiplicity=1, epsilon=0.0, q_start=0.0, q_end=1.0, q_midpoint=0.5,
            m_tt=1.0, r_eff=metrics.Available(0.5, None), a_qq=0.5, m_qq=metrics.Available(0.2, None),
            c_tt_conn=np.zeros((1, 1)),
            rho_qq={(0, 0): metrics.RhoQQEntry(0.0, None)},
        )


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
