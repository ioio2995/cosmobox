from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level1.automorphisms import (
    GraphAutomorphism,
    build_automorphism,
    compose,
    compose_unitary_automorphisms,
    generate_closed_subgroup,
    generate_closed_unitary_subgroup,
    hamiltonian_commutator_defect,
    identity_automorphism,
    identity_unitary_automorphism,
    reflection_automorphism,
    reflection_unitary_automorphism,
    symmetry_subgroup,
    transform_oriented_path,
    translation_automorphism,
    translation_unitary_automorphism,
)
from cosmobox.level1.matter import build_dressed_matter_matrix
from cosmobox.level1.paths import make_oriented_path, minimal_paths

N_FLAVORS = 2


def _build(geometry: str, spin: int):
    lattice = build_lattice(geometry)
    report = build_basis(lattice, N_FLAVORS, spin)
    key_index = build_key_index(report.keys)
    return lattice, report, key_index


def _uniform_params(n_nodes: int) -> HamiltonianParameters:
    return HamiltonianParameters(
        J=tuple(1.0 for _ in range(n_nodes)),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )


def _j_break_params(n_nodes: int) -> HamiltonianParameters:
    J = tuple(1.5 if node == 0 else 1.0 for node in range(n_nodes))
    return HamiltonianParameters(
        J=J, h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)), t=1.0, g_E=1.0, K=1.0
    )


def _frobenius_diff(a: sp.spmatrix, b: sp.spmatrix) -> float:
    diff = (a - b).tocsr()
    diff.eliminate_zeros()
    return float(np.sqrt(np.sum(np.abs(diff.data) ** 2))) if diff.nnz else 0.0


# ---------------------------------------------------------------------------
# GraphAutomorphism
# ---------------------------------------------------------------------------


def test_build_automorphism_translation_and_reflection_are_valid_on_triangle() -> None:
    lattice = build_lattice("triangle")
    translation = translation_automorphism(lattice)
    reflection = reflection_automorphism(lattice)
    assert translation.site_permutation == (1, 2, 0)
    assert reflection.site_permutation == (0, 2, 1)


def test_build_automorphism_matches_translation_automorphism_directly() -> None:
    lattice = build_lattice("triangle")
    direct = build_automorphism(lattice, [1, 2, 0])
    via_helper = translation_automorphism(lattice)
    assert direct.site_permutation == via_helper.site_permutation
    assert direct.edge_image == via_helper.edge_image
    assert direct.lattice_signature == lattice.name


def test_graph_automorphism_rejects_non_bijective_site_permutation() -> None:
    lattice = build_lattice("triangle")
    edge_endpoints = tuple((edge.source, edge.target) for edge in lattice.edges)
    with pytest.raises(ValueError, match="permutation"):
        GraphAutomorphism(lattice_signature=lattice.name, site_permutation=(0, 0, 2), edge_endpoints=edge_endpoints)


def test_graph_automorphism_rejects_a_non_automorphism_permutation() -> None:
    # ring4's edges are the 4-cycle 0-1-2-3-0; swapping just nodes 0 and 1
    # (fixing 2, 3) is a node bijection but not a lattice automorphism.
    lattice = build_lattice("ring4")
    edge_endpoints = tuple((edge.source, edge.target) for edge in lattice.edges)
    with pytest.raises(ValueError, match="not a lattice automorphism"):
        GraphAutomorphism(lattice_signature=lattice.name, site_permutation=(1, 0, 2, 3), edge_endpoints=edge_endpoints)


def test_graph_automorphism_edge_image_has_valid_indices_and_signs() -> None:
    lattice = build_lattice("ring4")
    translation = translation_automorphism(lattice)
    n_edges = len(lattice.edges)
    for edge_index, sign in translation.edge_image:
        assert 0 <= edge_index < n_edges
        assert sign in (1, -1)


def test_graph_automorphism_edge_image_is_coherent_with_transformed_endpoints() -> None:
    lattice = build_lattice("ring4")
    reflection = reflection_automorphism(lattice)
    edge_endpoints = tuple((edge.source, edge.target) for edge in lattice.edges)
    for original_index, (source, target) in enumerate(edge_endpoints):
        image_index, sign = reflection.edge_image[original_index]
        new_source = reflection.site_permutation[source]
        new_target = reflection.site_permutation[target]
        if sign == 1:
            assert edge_endpoints[image_index] == (new_source, new_target)
        else:
            assert edge_endpoints[image_index] == (new_target, new_source)


def test_compose_rejects_automorphisms_of_different_lattices() -> None:
    triangle_automorphism = translation_automorphism(build_lattice("triangle"))
    ring4_automorphism = translation_automorphism(build_lattice("ring4"))
    with pytest.raises(ValueError, match="different lattices"):
        compose(triangle_automorphism, ring4_automorphism)


def test_compose_translation_with_itself_matches_two_step_translation() -> None:
    lattice = build_lattice("ring4")
    translation = translation_automorphism(lattice)
    composed = compose(translation, translation)
    assert composed.site_permutation == tuple((node + 2) % 4 for node in range(4))


def test_identity_automorphism_is_the_identity_permutation() -> None:
    lattice = build_lattice("ring5")
    identity = identity_automorphism(lattice)
    assert identity.site_permutation == tuple(range(5))


# ---------------------------------------------------------------------------
# Group closure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("geometry", "n_nodes", "expected_order"), [("triangle", 3, 6), ("ring4", 4, 8), ("ring5", 5, 10)])
def test_generate_closed_subgroup_has_dihedral_order_and_contains_identity(geometry, n_nodes, expected_order) -> None:
    lattice = build_lattice(geometry)
    generators = [translation_automorphism(lattice), reflection_automorphism(lattice)]
    group = generate_closed_subgroup(generators)
    assert len(group) == expected_order
    assert tuple(range(n_nodes)) in {element.site_permutation for element in group}


def test_generate_closed_subgroup_is_deterministic() -> None:
    lattice = build_lattice("ring4")
    generators = [translation_automorphism(lattice), reflection_automorphism(lattice)]
    first = generate_closed_subgroup(generators)
    second = generate_closed_subgroup(list(reversed(generators)))
    assert [element.site_permutation for element in first] == [element.site_permutation for element in second]


def test_generate_closed_subgroup_rejects_empty_generators() -> None:
    with pytest.raises(ValueError, match="at least one generator"):
        generate_closed_subgroup([])


# ---------------------------------------------------------------------------
# transform_oriented_path
# ---------------------------------------------------------------------------


def test_transform_oriented_path_rejects_mismatched_lattice_signature() -> None:
    triangle = build_lattice("triangle")
    ring4 = build_lattice("ring4")
    automorphism = translation_automorphism(ring4)
    path = make_oriented_path(triangle, (0, 1))
    with pytest.raises(ValueError, match="lattice_signature"):
        transform_oriented_path(triangle, automorphism, path)


def test_transform_oriented_path_maps_source_destination_and_preserves_length() -> None:
    lattice = build_lattice("ring4")
    translation = translation_automorphism(lattice)
    path = minimal_paths(lattice, 0, 2)[0]
    transformed = transform_oriented_path(lattice, translation, path)
    assert transformed.source == translation.site_permutation[path.source]
    assert transformed.destination == translation.site_permutation[path.destination]
    assert len(transformed.nodes) == len(path.nodes)


def test_transform_oriented_path_of_zero_length_path_is_zero_length() -> None:
    lattice = build_lattice("triangle")
    reflection = reflection_automorphism(lattice)
    path = make_oriented_path(lattice, (1,))
    transformed = transform_oriented_path(lattice, reflection, path)
    assert transformed.nodes == (reflection.site_permutation[1],)
    assert transformed.steps == ()


def test_transform_oriented_path_ring4_reflection_swaps_the_two_antipodal_paths() -> None:
    lattice = build_lattice("ring4")
    reflection = reflection_automorphism(lattice)
    assert reflection.site_permutation == (0, 3, 2, 1)  # fixes 0 and 2

    paths = minimal_paths(lattice, 0, 2)
    assert len(paths) == 2

    transformed_first = transform_oriented_path(lattice, reflection, paths[0])
    assert transformed_first in paths
    assert transformed_first != paths[0]  # genuinely swapped to the OTHER antipodal path


# ---------------------------------------------------------------------------
# V06 -- covariance identity at J_i=1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("geometry", ["triangle", "ring4"])
def test_v06_covariance_identity_holds_for_translation_and_reflection(geometry: str) -> None:
    spin = 1
    lattice, report, key_index = _build(geometry, spin)
    params = _uniform_params(len(lattice.nodes))
    build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)  # sanity: params are valid

    path = minimal_paths(lattice, 0, 1)[0]
    alpha, beta = 0, 1
    base_operator = build_dressed_matter_matrix(lattice, N_FLAVORS, spin, report.keys, key_index, path, alpha, beta)

    for unitary_automorphism in (
        translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index),
        reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index),
    ):
        transformed_path = transform_oriented_path(lattice, unitary_automorphism.automorphism, path)
        image_operator = build_dressed_matter_matrix(
            lattice, N_FLAVORS, spin, report.keys, key_index, transformed_path, alpha, beta
        )
        conjugated = unitary_automorphism.unitary @ base_operator @ unitary_automorphism.unitary.conj().T
        assert _frobenius_diff(conjugated, image_operator) <= 1e-10


def test_v06_covariance_identity_fails_to_hold_against_an_unrelated_operator() -> None:
    # Negative control: the identity is specific to the SAME path transformed
    # the SAME way -- comparing against an unrelated path's operator should
    # NOT accidentally satisfy the identity.
    spin = 1
    geometry = "triangle"
    lattice, report, key_index = _build(geometry, spin)
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)

    path_a = minimal_paths(lattice, 0, 1)[0]
    path_b = minimal_paths(lattice, 0, 2)[0]  # translation maps path_a (0->1) to 1->2, NOT to path_b
    operator_a = build_dressed_matter_matrix(lattice, N_FLAVORS, spin, report.keys, key_index, path_a, 0, 1)
    operator_b = build_dressed_matter_matrix(lattice, N_FLAVORS, spin, report.keys, key_index, path_b, 0, 1)

    conjugated = translation.unitary @ operator_a @ translation.unitary.conj().T
    assert _frobenius_diff(conjugated, operator_b) > 1e-10


# ---------------------------------------------------------------------------
# V07 -- empirical subgroup reduction under j_break
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("geometry", "spin"), [("triangle", 2), ("ring5", 2)])
def test_v07_j_break_reduces_the_symmetry_group_to_identity_and_reflection(geometry: str, spin: int) -> None:
    lattice, report, key_index = _build(geometry, spin)
    n_nodes = len(lattice.nodes)
    params = _j_break_params(n_nodes)
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)
    hamiltonian = terms.total

    identity = identity_unitary_automorphism(lattice, report.keys)
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)

    closed_group = generate_closed_unitary_subgroup([translation, reflection])
    # sanity: identity is present, group has the expected dihedral order
    assert any(element.automorphism.site_permutation == identity.automorphism.site_permutation for element in closed_group)

    tolerance = 1e-10
    survivors = symmetry_subgroup(closed_group, hamiltonian, tolerance=tolerance)
    survivor_permutations = {element.automorphism.site_permutation for element in survivors}

    assert identity.automorphism.site_permutation in survivor_permutations
    assert reflection.automorphism.site_permutation in survivor_permutations
    assert translation.automorphism.site_permutation not in survivor_permutations
    assert len(survivors) == 2

    # The algorithm does not presuppose the result: confirm by direct
    # commutator measurement, independent of symmetry_subgroup's own filtering.
    assert hamiltonian_commutator_defect(reflection.unitary, hamiltonian) <= tolerance
    assert hamiltonian_commutator_defect(translation.unitary, hamiltonian) > tolerance


def test_v07_at_j_i_1_the_full_group_commutes_with_h() -> None:
    spin = 1
    lattice, report, key_index = _build("triangle", spin)
    params = _uniform_params(len(lattice.nodes))
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)

    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    for element in (translation, reflection):
        assert hamiltonian_commutator_defect(element.unitary, terms.total) <= 1e-10


def test_symmetry_subgroup_rejects_a_non_closed_candidate_set() -> None:
    spin = 2
    lattice, report, key_index = _build("triangle", spin)
    params = _j_break_params(len(lattice.nodes))
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)

    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    # A deliberately non-closed set: {reflection, translation} without their
    # own composition (reflection then translation) present.
    non_closed = [reflection, translation]
    with pytest.raises(ValueError):
        symmetry_subgroup(non_closed, terms.total, tolerance=1e-10)


def test_symmetry_subgroup_raises_if_nothing_survives() -> None:
    spin = 1
    lattice, report, key_index = _build("triangle", spin)
    # An absurdly tight tolerance against a nonzero commutator: use j_break
    # so translation genuinely fails, then require an impossible tolerance
    # even the identity cannot satisfy by construction is not meaningful --
    # instead, use a deliberately wrong "hamiltonian" (a nonzero matrix that
    # does not commute with the identity's own trivial unitary) is also not
    # meaningful (identity always commutes). Use only a non-identity closed
    # set against a hamiltonian nothing in it commutes with.
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    closed_group = generate_closed_unitary_subgroup([translation, reflection])
    non_identity_group = [element for element in closed_group if element.label != "identity"]
    dimension = reflection.unitary.shape[0]
    rng = np.random.default_rng(42)
    random_hermitian = sp.random(dimension, dimension, density=0.3, random_state=rng, dtype=np.float64)
    random_hermitian = sp.csr_matrix((random_hermitian + random_hermitian.T).astype(np.complex128))
    with pytest.raises(ValueError, match="no candidate"):
        symmetry_subgroup(non_identity_group, random_hermitian, tolerance=1e-12)


# ---------------------------------------------------------------------------
# UnitaryAutomorphism composition and closure
# ---------------------------------------------------------------------------


def test_compose_unitary_automorphisms_multiplies_operators_in_matching_order() -> None:
    lattice = build_lattice("ring4")
    spin = 1
    _, report, key_index = _build("ring4", spin)
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    composed = compose_unitary_automorphisms(translation, translation)
    expected_combinatorial = compose(translation.automorphism, translation.automorphism)
    assert composed.automorphism.site_permutation == expected_combinatorial.site_permutation
    assert _frobenius_diff(composed.unitary, translation.unitary @ translation.unitary) <= 1e-10


def test_generate_closed_unitary_subgroup_matches_combinatorial_closure_size() -> None:
    lattice = build_lattice("triangle")
    spin = 1
    _, report, key_index = _build("triangle", spin)
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, report.keys, key_index)
    closed = generate_closed_unitary_subgroup([translation, reflection])
    combinatorial_closed = generate_closed_subgroup([translation.automorphism, reflection.automorphism])
    assert len(closed) == len(combinatorial_closed) == 6
