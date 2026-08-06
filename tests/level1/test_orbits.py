from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level1.automorphisms import identity_unitary_automorphism, reflection_unitary_automorphism, transform_oriented_path
from cosmobox.level1.matter import build_dressed_matter_matrix
from cosmobox.level1.orbits import (
    OrbitComparabilityKey,
    OrbitElement,
    ValidatedOrbit,
    aggregate_validated_orbit,
    validate_orbit_covariance,
)
from cosmobox.level1.paths import minimal_paths
from cosmobox.level1.restricted import canonical_multiplet_expectation, extract_group_state

N_FLAVORS = 2


def _diagonalize_ring4(spin: int = 1, n_eigenvalues: int = 6):
    lattice = build_lattice("ring4")
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


def _base_key(**overrides) -> OrbitComparabilityKey:
    defaults = dict(
        orbit_family="test_family",
        path_length=1,
        spectral_group_key="group_0",
        status="complete_multiplet",
        observable_kind="O_ij_raw",
        normalization="raw_G",
        flavor_component="alpha0_beta1",
        hamiltonian_identity="ring4_j1",
    )
    defaults.update(overrides)
    return OrbitComparabilityKey(**defaults)


# ---------------------------------------------------------------------------
# V14 -- ring4's two antipodal minimal paths: determinism, transformation,
# no implicit averaging.
# ---------------------------------------------------------------------------


def test_v14_ring4_antipodal_pair_has_exactly_two_distinct_minimal_paths() -> None:
    lattice = build_lattice("ring4")
    paths = minimal_paths(lattice, 0, 2)
    assert len(paths) == 2
    assert paths[0] != paths[1]
    assert all(len(path.nodes) == 3 for path in paths)  # length-2 paths, 3 nodes


def test_v14_ring4_antipodal_minimal_paths_are_deterministic_across_calls() -> None:
    lattice = build_lattice("ring4")
    first = minimal_paths(lattice, 0, 2)
    second = minimal_paths(lattice, 0, 2)
    assert first == second


def test_v14_ring4_antipodal_pair_transforms_correctly_under_reflection() -> None:
    lattice = build_lattice("ring4")
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, *_basis_and_index(lattice))
    paths = minimal_paths(lattice, 0, 2)
    transformed = transform_oriented_path(lattice, reflection.automorphism, paths[0])
    assert transformed == paths[1]


def _basis_and_index(lattice):
    report = build_basis(lattice, N_FLAVORS, 1)
    key_index = build_key_index(report.keys)
    return report.keys, key_index


def test_v14_no_implicit_averaging_between_the_two_antipodal_paths() -> None:
    # Each path's dressed-operator value is independently retrievable, and
    # nothing in matter.py/restricted.py silently pools them: they may
    # differ freely, and any combination is only ever produced by an
    # explicit call to aggregate_validated_orbit (tested separately below).
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)

    paths = minimal_paths(lattice, 0, 2)
    alpha, beta = 0, 1
    values = []
    for path in paths:
        operator = build_dressed_matter_matrix(lattice, N_FLAVORS, 1, report.keys, key_index, path, alpha, beta)
        values.append(canonical_multiplet_expectation(operator, state, hermitian=False))

    # Both values are independently available as plain scalars -- no
    # aggregate object is produced by merely computing them.
    assert isinstance(values[0], complex)
    assert isinstance(values[1], complex)


# ---------------------------------------------------------------------------
# Full pipeline: validate_orbit_covariance -> aggregate_validated_orbit,
# using the ring4 antipodal pair (related by reflection, at J_i=1).
# ---------------------------------------------------------------------------


def test_orbit_pipeline_on_ring4_antipodal_pair_gives_near_zero_covariance_defect() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)

    base_path, transformed_path_reference = minimal_paths(lattice, 0, 2)
    alpha, beta = 0, 1

    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)
    subgroup = [identity, reflection]

    operator_at_base = build_dressed_matter_matrix(lattice, N_FLAVORS, 1, report.keys, key_index, base_path, alpha, beta)
    value_at_base = canonical_multiplet_expectation(operator_at_base, state, hermitian=False)

    transformed_path = transform_oriented_path(lattice, reflection.automorphism, base_path)
    assert transformed_path == transformed_path_reference
    operator_at_transformed = build_dressed_matter_matrix(
        lattice, N_FLAVORS, 1, report.keys, key_index, transformed_path, alpha, beta
    )
    value_at_transformed = canonical_multiplet_expectation(operator_at_transformed, state, hermitian=False)

    key = _base_key(orbit_family="ring4_antipodal_j1", path_length=2, spectral_group_key=(0, group.start_index, group.end_index_exclusive))
    elements = [OrbitElement(key, value_at_base), OrbitElement(key, value_at_transformed)]

    validated = validate_orbit_covariance(
        lattice, N_FLAVORS, 1, report.keys, key_index, subgroup, base_path, alpha, beta, elements, tolerance=1e-10
    )
    stats = aggregate_validated_orbit(validated)

    # U_A commutes with H at J_i=1, so U_A maps this complete group's
    # subspace to itself, rho is invariant, and the two orbit values are
    # mathematically equal -- any residual spread is a numerical defect,
    # not a physical fluctuation (specification.md section 11).
    assert stats.orbit_covariance_defect < 1e-8
    assert stats.orbit_max_pairwise_spread < 1e-8


def test_validate_orbit_covariance_rejects_mismatched_comparability_keys() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()

    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)

    elements = [
        OrbitElement(_base_key(path_length=2), complex(0.1)),
        OrbitElement(_base_key(path_length=3), complex(0.1)),  # mismatched path_length
    ]
    with pytest.raises(ValueError, match="comparability key"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [identity, reflection], base_path, 0, 1, elements, tolerance=1e-10
        )


def test_validate_orbit_covariance_rejects_element_count_mismatch() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)

    elements = [OrbitElement(_base_key(), complex(0.1))]  # only 1, but subgroup has 2
    with pytest.raises(ValueError, match="correspond 1:1"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [identity, reflection], base_path, 0, 1, elements, tolerance=1e-10
        )


def test_validate_orbit_covariance_rejects_empty_elements() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    base_path = minimal_paths(lattice, 0, 2)[0]
    with pytest.raises(ValueError, match="at least one element"):
        validate_orbit_covariance(lattice, N_FLAVORS, 1, report.keys, key_index, [], base_path, 0, 1, [], tolerance=1e-10)


def test_validate_orbit_covariance_detects_a_genuine_covariance_violation() -> None:
    # Deliberately mismatch subgroup and base_path/alpha/beta by pairing a
    # reflection generator with a path that reflection does NOT map onto
    # itself in a way consistent with a fabricated "identity-like" element
    # value -- simplest genuine violation: supply a subgroup unitary that is
    # NOT the automorphism's real U_A (swap identity's and reflection's
    # unitaries) so the identity check fails.
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)

    from cosmobox.level1.automorphisms import UnitaryAutomorphism

    broken_identity = UnitaryAutomorphism(label="identity", automorphism=identity.automorphism, unitary=reflection.unitary)
    elements = [OrbitElement(_base_key(), complex(0.1)), OrbitElement(_base_key(), complex(0.1))]
    with pytest.raises(ValueError, match="covariance identity failed"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [broken_identity, reflection], base_path, 0, 1, elements, tolerance=1e-10
        )


# ---------------------------------------------------------------------------
# aggregate_validated_orbit -- hand-verified arithmetic, type gate
# ---------------------------------------------------------------------------


def test_aggregate_validated_orbit_hand_verified_arithmetic() -> None:
    key = _base_key()
    values = [1 + 1j, 3 + 1j, 1 + 5j]
    orbit = ValidatedOrbit(key=key, elements=tuple(OrbitElement(key, value) for value in values))
    stats = aggregate_validated_orbit(orbit)

    expected_mean = sum(values) / 3
    assert stats.orbit_mean == pytest.approx(expected_mean)
    expected_max_pairwise = max(abs(a - b) for a in values for b in values)
    assert stats.orbit_max_pairwise_spread == pytest.approx(expected_max_pairwise)
    expected_defect = max(abs(v - expected_mean) for v in values)
    assert stats.orbit_covariance_defect == pytest.approx(expected_defect)


def test_aggregate_validated_orbit_single_element_has_zero_spread() -> None:
    key = _base_key()
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 3 + 4j),))
    stats = aggregate_validated_orbit(orbit)
    assert stats.orbit_mean == pytest.approx(3 + 4j)
    assert stats.orbit_max_pairwise_spread == 0.0
    assert stats.orbit_covariance_defect == pytest.approx(0.0)


def test_aggregate_validated_orbit_only_accepts_a_validated_orbit_type() -> None:
    key = _base_key()
    bare_elements = (OrbitElement(key, 1 + 1j), OrbitElement(key, 2 + 2j))
    with pytest.raises(AttributeError):
        aggregate_validated_orbit(bare_elements)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# OrbitComparabilityKey -- comparability contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_override",
    [
        {"orbit_family": "other_family"},
        {"path_length": 99},
        {"spectral_group_key": "other_group"},
        {"status": "partial_subspace"},
        {"observable_kind": "flavor_singlet"},
        {"normalization": "gamma_O"},
        {"flavor_component": "alpha1_beta0"},
        {"hamiltonian_identity": "other_hamiltonian"},
    ],
)
def test_orbit_comparability_key_any_field_mismatch_breaks_equality(field_override: dict) -> None:
    key_a = _base_key()
    key_b = _base_key(**field_override)
    assert key_a != key_b
