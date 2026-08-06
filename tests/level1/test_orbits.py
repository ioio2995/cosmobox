from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level1.automorphisms import (
    UnitaryAutomorphism,
    identity_unitary_automorphism,
    reflection_unitary_automorphism,
    transform_oriented_path,
)
from cosmobox.level1.matter import build_dressed_matter_matrix
from cosmobox.level1.orbits import (
    DRESSED_MATTER_OBSERVABLE_KIND,
    OrbitComparabilityKey,
    OrbitElement,
    ValidatedOrbit,
    _VALIDATION_TOKEN,
    aggregate_validated_orbit,
    flavor_component_label,
    validate_orbit_covariance,
)
from cosmobox.level1.paths import minimal_paths
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, canonical_multiplet_expectation, extract_group_state

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
        status=COMPLETE_MULTIPLET,
        observable_kind=DRESSED_MATTER_OBSERVABLE_KIND,
        normalization="raw_G",
        flavor_component=flavor_component_label(0, 1),
        hamiltonian_identity="ring4_j1",
    )
    defaults.update(overrides)
    return OrbitComparabilityKey(**defaults)


def _ring4_antipodal_orbit_key(group, base_path):
    return _base_key(
        orbit_family="ring4_antipodal_j1",
        path_length=base_path.length,
        spectral_group_key=(0, group.start_index, group.end_index_exclusive),
        status=COMPLETE_MULTIPLET,
    )


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

    # Independent reference values, computed OUTSIDE the pipeline, to check
    # against what validate_orbit_covariance computes internally.
    operator_at_base = build_dressed_matter_matrix(lattice, N_FLAVORS, 1, report.keys, key_index, base_path, alpha, beta)
    reference_value_at_base = canonical_multiplet_expectation(operator_at_base, state, hermitian=False)
    transformed_path = transform_oriented_path(lattice, reflection.automorphism, base_path)
    assert transformed_path == transformed_path_reference
    operator_at_transformed = build_dressed_matter_matrix(
        lattice, N_FLAVORS, 1, report.keys, key_index, transformed_path, alpha, beta
    )
    reference_value_at_transformed = canonical_multiplet_expectation(operator_at_transformed, state, hermitian=False)

    key = _ring4_antipodal_orbit_key(group, base_path)
    validated = validate_orbit_covariance(
        lattice, N_FLAVORS, 1, report.keys, key_index, subgroup, state, base_path, alpha, beta, key, tolerance=1e-10
    )

    assert validated.elements[0].value == pytest.approx(reference_value_at_base)
    assert validated.elements[1].value == pytest.approx(reference_value_at_transformed)

    stats = aggregate_validated_orbit(validated)

    # U_A commutes with H at J_i=1, so U_A maps this complete group's
    # subspace to itself, rho is invariant, and the two orbit values are
    # mathematically equal -- any residual spread is a numerical defect,
    # not a physical fluctuation (specification.md section 11).
    assert stats.orbit_covariance_defect < 1e-8
    assert stats.orbit_max_pairwise_spread < 1e-8


def test_validate_orbit_covariance_has_no_parameter_to_inject_a_value() -> None:
    # The old signature accepted `elements: Sequence[OrbitElement]`, letting
    # a caller place an arbitrary value in a ValidatedOrbit as long as the
    # keys matched and the (unrelated) operator covariance check passed.
    # That parameter no longer exists -- confirm the new signature rejects
    # it outright, rather than silently ignoring it.
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)

    key = _ring4_antipodal_orbit_key(group, base_path)
    forged_elements = [OrbitElement(key, complex(999.0)), OrbitElement(key, complex(999.0))]
    with pytest.raises(TypeError):
        validate_orbit_covariance(
            lattice,
            N_FLAVORS,
            1,
            report.keys,
            key_index,
            [identity, reflection],
            state,
            base_path,
            0,
            1,
            key,
            elements=forged_elements,  # type: ignore[call-arg]
            tolerance=1e-10,
        )


def test_validate_orbit_covariance_rejects_empty_subgroup() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    key = _ring4_antipodal_orbit_key(group, base_path)
    with pytest.raises(ValueError, match="at least one subgroup element"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [], state, base_path, 0, 1, key, tolerance=1e-10
        )


def test_validate_orbit_covariance_detects_a_genuine_covariance_violation() -> None:
    # Supply a subgroup unitary that is NOT the automorphism's real U_A
    # (swap identity's and reflection's unitaries) so the identity check
    # fails -- and, since values are now computed internally, there is no
    # way for a forged value to mask this.
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)

    broken_identity = UnitaryAutomorphism(label="identity", automorphism=identity.automorphism, unitary=reflection.unitary)
    key = _ring4_antipodal_orbit_key(group, base_path)
    with pytest.raises(ValueError, match="covariance identity failed"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [broken_identity, reflection], state, base_path, 0, 1, key, tolerance=1e-10
        )


# ---------------------------------------------------------------------------
# Key coherence -- path_length / status / observable_kind / flavor_component
# must match what validate_orbit_covariance's own arguments imply.
# ---------------------------------------------------------------------------


def test_validate_orbit_covariance_rejects_key_with_wrong_path_length() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)
    key = _ring4_antipodal_orbit_key(group, base_path)
    lying_key = replace(key, path_length=key.path_length + 1)
    with pytest.raises(ValueError, match="path_length"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [identity, reflection], state, base_path, 0, 1, lying_key, tolerance=1e-10
        )


def test_validate_orbit_covariance_rejects_key_with_wrong_status() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)
    key = _ring4_antipodal_orbit_key(group, base_path)
    lying_key = replace(key, status="partial_subspace")
    with pytest.raises(ValueError, match="status"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [identity, reflection], state, base_path, 0, 1, lying_key, tolerance=1e-10
        )


def test_validate_orbit_covariance_rejects_key_with_wrong_observable_kind() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)
    key = _ring4_antipodal_orbit_key(group, base_path)
    lying_key = replace(key, observable_kind="flavor_singlet")
    with pytest.raises(ValueError, match="observable_kind"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [identity, reflection], state, base_path, 0, 1, lying_key, tolerance=1e-10
        )


def test_validate_orbit_covariance_rejects_key_with_wrong_flavor_component() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize_ring4()
    group = next(g for g in level0_report.spectrum.degeneracy.groups if not g.lower_bound_only)
    state = extract_group_state(eigenvectors, group)
    base_path = minimal_paths(lattice, 0, 2)[0]
    identity = identity_unitary_automorphism(lattice, report.keys)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, 1, report.keys, key_index)
    key = _ring4_antipodal_orbit_key(group, base_path)  # alpha=0, beta=1 implied by flavor_component_label(0, 1)
    lying_key = replace(key, flavor_component=flavor_component_label(1, 0))
    with pytest.raises(ValueError, match="flavor_component"):
        validate_orbit_covariance(
            lattice, N_FLAVORS, 1, report.keys, key_index, [identity, reflection], state, base_path, 0, 1, lying_key, tolerance=1e-10
        )


# ---------------------------------------------------------------------------
# ValidatedOrbit -- constructible only via validate_orbit_covariance
# ---------------------------------------------------------------------------


def test_validated_orbit_direct_construction_without_token_is_rejected() -> None:
    key = _base_key()
    with pytest.raises(TypeError):
        ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),))  # type: ignore[call-arg]


def test_validated_orbit_direct_construction_with_wrong_token_is_rejected() -> None:
    key = _base_key()
    with pytest.raises(ValueError, match="validate_orbit_covariance"):
        ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=object())


def test_validated_orbit_direct_construction_with_the_real_token_succeeds() -> None:
    # The token is intentionally reachable by an EXPLICIT, conscious
    # bypass (importing orbits._VALIDATION_TOKEN directly) for testing --
    # exactly like OrientedPath's frozen dataclass or SpectralGroupState's
    # read-only psi are bypassed elsewhere in this test suite to prove a
    # downstream check is not dead code.
    key = _base_key()
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    assert orbit.elements[0].value == 1 + 1j


def test_validated_orbit_rejects_empty_elements() -> None:
    key = _base_key()
    with pytest.raises(ValueError, match="at least one element"):
        ValidatedOrbit(key=key, elements=(), _token=_VALIDATION_TOKEN)


def test_validated_orbit_rejects_element_with_a_divergent_key() -> None:
    key = _base_key()
    other_key = _base_key(orbit_family="other_family")
    with pytest.raises(ValueError, match="does not match"):
        ValidatedOrbit(key=key, elements=(OrbitElement(other_key, 1 + 1j),), _token=_VALIDATION_TOKEN)


@pytest.mark.parametrize("bad_value", [complex(float("nan"), 0.0), complex(0.0, float("nan")), complex(float("inf"), 0.0)])
def test_validated_orbit_rejects_non_finite_values(bad_value: complex) -> None:
    key = _base_key()
    with pytest.raises(ValueError, match="not finite"):
        ValidatedOrbit(key=key, elements=(OrbitElement(key, bad_value),), _token=_VALIDATION_TOKEN)


# ---------------------------------------------------------------------------
# aggregate_validated_orbit -- hand-verified arithmetic, type gate
# ---------------------------------------------------------------------------


def test_aggregate_validated_orbit_hand_verified_arithmetic() -> None:
    key = _base_key()
    values = [1 + 1j, 3 + 1j, 1 + 5j]
    orbit = ValidatedOrbit(key=key, elements=tuple(OrbitElement(key, value) for value in values), _token=_VALIDATION_TOKEN)
    stats = aggregate_validated_orbit(orbit)

    expected_mean = sum(values) / 3
    assert stats.orbit_mean == pytest.approx(expected_mean)
    expected_max_pairwise = max(abs(a - b) for a in values for b in values)
    assert stats.orbit_max_pairwise_spread == pytest.approx(expected_max_pairwise)
    expected_defect = max(abs(v - expected_mean) for v in values)
    assert stats.orbit_covariance_defect == pytest.approx(expected_defect)


def test_aggregate_validated_orbit_single_element_has_zero_spread() -> None:
    key = _base_key()
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 3 + 4j),), _token=_VALIDATION_TOKEN)
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
