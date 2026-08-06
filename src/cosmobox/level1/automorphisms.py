"""Graph automorphisms and their combinatorial action on nodes, edges, and
oriented paths, paired with the Level0 unitary operators U_A that realize
them on the physical basis. Level1B lot 1B-4
(docs/levels/level1/specification.md section 11,
docs/levels/level1/implementation-design.md section 7).

The node<->edge correspondence logic here (site_permutation -> edge_image)
mirrors cosmobox.level0.symmetries' own private _edge_image, but is
reimplemented independently against Lattice's PUBLIC nodes/edges only --
level0 is frozen and not modified for this lot. Correctness of this
independent reimplementation is established not by comparing internal
tables against symmetries.py's private helper, but by the covariance
identity itself (V06/V07): U_A @ O_ij[P] @ U_A^dagger == O_{A(i)A(j)}[A(P)],
built from level0.symmetries.build_translation_operator /
build_reflection_operator (U_A, unmodified) and
level1.matter.build_dressed_matter_matrix (O), using the exact same
site_permutation on both sides -- a stronger, end-to-end proof than a
private-table comparison would be.

V07's subgroup reduction under j_break is determined empirically, from the
commutator of each candidate U_A with the actual Hamiltonian
(symmetry_subgroup), never assumed from the bare graph's automorphism
group -- matching docs/model/physical-model.md's explicit statement that
orbits are built from the subgroup that leaves the perturbed Hamiltonian
invariant.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

from cosmobox.level0.lattice import Lattice
from cosmobox.level0.symmetries import build_reflection_operator, build_translation_operator

from .paths import OrientedPath
from .transporters import _validate_steps_against_lattice

# ---------------------------------------------------------------------------
# Combinatorial automorphisms
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GraphAutomorphism:
    """A validated bijection on lattice nodes together with its induced,
    self-derived action on lattice edges (image edge index + orientation
    sign per original edge).

    lattice_signature ties this automorphism to one specific lattice
    (lattice.name -- Level0's lattices are deterministic pure functions of
    their name, so any two build_lattice(name) calls are interchangeable
    for this purpose). compose() refuses to combine automorphisms whose
    lattice_signature differs.

    edge_image is NOT a constructor argument: it is entirely derived and
    validated inside __post_init__ from site_permutation and
    edge_endpoints, so a GraphAutomorphism cannot be constructed with an
    edge_image inconsistent with its own site_permutation -- there is no
    way to pass one in directly.
    """

    lattice_signature: str
    site_permutation: tuple[int, ...]
    edge_endpoints: tuple[tuple[int, int], ...]  # lattice.edges as (source, target)
    edge_image: tuple[tuple[int, int], ...] = field(init=False)

    def __post_init__(self) -> None:
        n_nodes = len(self.site_permutation)
        if sorted(self.site_permutation) != list(range(n_nodes)):
            raise ValueError(
                f"site_permutation must be a permutation of range({n_nodes}), got {self.site_permutation!r}"
            )

        n_edges = len(self.edge_endpoints)
        lookup: dict[tuple[int, int], int] = {}
        for index, endpoints in enumerate(self.edge_endpoints):
            if endpoints in lookup:
                raise ValueError(f"edge_endpoints contains a duplicate (source, target) pair: {endpoints}")
            lookup[endpoints] = index

        edge_image: list[tuple[int, int]] = []
        for source, target in self.edge_endpoints:
            new_source, new_target = self.site_permutation[source], self.site_permutation[target]
            if (new_source, new_target) in lookup:
                edge_image.append((lookup[(new_source, new_target)], 1))
            elif (new_target, new_source) in lookup:
                edge_image.append((lookup[(new_target, new_source)], -1))
            else:
                raise ValueError(
                    f"site_permutation does not map edge ({source}, {target}) onto any stored edge "
                    f"in either orientation (image is ({new_source}, {new_target})) -- not a lattice automorphism"
                )

        # The induced edge map's bijectivity is a consequence of
        # site_permutation being a node bijection and the edge set being
        # preserved (checked explicitly here rather than left implicit):
        # distinct original edges have distinct permuted endpoint pairs,
        # hence distinct images; a finite injective self-map is bijective.
        image_indices = [index for index, _ in edge_image]
        if sorted(image_indices) != list(range(n_edges)):
            raise ValueError(
                f"the induced edge map is not bijective: image indices {image_indices!r} "
                f"do not cover range({n_edges}) exactly once"
            )
        for edge_index, sign in edge_image:
            if not (0 <= edge_index < n_edges):
                raise ValueError(f"edge_image entry references out-of-range edge index {edge_index}")
            if sign not in (1, -1):
                raise ValueError(f"edge_image sign must be +1 or -1, got {sign}")

        object.__setattr__(self, "edge_image", tuple(edge_image))


def build_automorphism(lattice: Lattice, site_permutation: Sequence[int]) -> GraphAutomorphism:
    edge_endpoints = tuple((edge.source, edge.target) for edge in lattice.edges)
    return GraphAutomorphism(
        lattice_signature=lattice.name,
        site_permutation=tuple(site_permutation),
        edge_endpoints=edge_endpoints,
    )


def identity_automorphism(lattice: Lattice) -> GraphAutomorphism:
    return build_automorphism(lattice, range(len(lattice.nodes)))


def translation_automorphism(lattice: Lattice) -> GraphAutomorphism:
    """node i -> (i+1) mod N -- the SAME site_permutation used internally
    by level0.symmetries.build_translation_operator; this identity between
    the two independently-computed permutations is exactly what V06
    verifies, not merely assumed."""
    n_nodes = len(lattice.nodes)
    return build_automorphism(lattice, [(node + 1) % n_nodes for node in range(n_nodes)])


def reflection_automorphism(lattice: Lattice) -> GraphAutomorphism:
    """node i -> (N-i) mod N -- the SAME site_permutation used internally
    by level0.symmetries.build_reflection_operator."""
    n_nodes = len(lattice.nodes)
    return build_automorphism(lattice, [(n_nodes - node) % n_nodes for node in range(n_nodes)])


def compose(a: GraphAutomorphism, b: GraphAutomorphism) -> GraphAutomorphism:
    """The automorphism obtained by applying `a` first, then `b`:
    composed.site_permutation[i] = b.site_permutation[a.site_permutation[i]].

    Both must be automorphisms of the SAME lattice; raises ValueError
    (never silently produces a nonsensical composite) if lattice_signature
    or edge_endpoints differ.
    """
    if a.lattice_signature != b.lattice_signature:
        raise ValueError(
            f"cannot compose automorphisms of different lattices: "
            f"{a.lattice_signature!r} != {b.lattice_signature!r}"
        )
    if a.edge_endpoints != b.edge_endpoints:
        raise ValueError(
            "automorphisms share a lattice_signature but have different edge_endpoints -- refusing to compose"
        )
    site_permutation = tuple(b.site_permutation[a.site_permutation[node]] for node in range(len(a.site_permutation)))
    return GraphAutomorphism(
        lattice_signature=a.lattice_signature, site_permutation=site_permutation, edge_endpoints=a.edge_endpoints
    )


def generate_closed_subgroup(generators: Sequence[GraphAutomorphism]) -> tuple[GraphAutomorphism, ...]:
    """The finite group generated by `generators` under compose(), closed
    by repeated composition (breadth-first) until no new site_permutation
    is produced. Always contains the identity (seeded explicitly, not
    assumed to emerge from the generators). Deterministic: returned sorted
    by site_permutation for a canonical, reproducible ordering regardless
    of generator order.
    """
    if not generators:
        raise ValueError("generate_closed_subgroup requires at least one generator")
    lattice_signature = generators[0].lattice_signature
    for generator in generators:
        if generator.lattice_signature != lattice_signature:
            raise ValueError("all generators must belong to the same lattice")

    n_nodes = len(generators[0].site_permutation)
    identity_permutation = tuple(range(n_nodes))
    identity_element = GraphAutomorphism(
        lattice_signature=lattice_signature,
        site_permutation=identity_permutation,
        edge_endpoints=generators[0].edge_endpoints,
    )

    seen: dict[tuple[int, ...], GraphAutomorphism] = {identity_permutation: identity_element}
    queue = [identity_element]
    for generator in generators:
        if generator.site_permutation not in seen:
            seen[generator.site_permutation] = generator
            queue.append(generator)

    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for generator in generators:
            candidate = compose(current, generator)
            if candidate.site_permutation not in seen:
                seen[candidate.site_permutation] = candidate
                queue.append(candidate)

    return tuple(sorted(seen.values(), key=lambda element: element.site_permutation))


def transform_oriented_path(lattice: Lattice, automorphism: GraphAutomorphism, path: OrientedPath) -> OrientedPath:
    """A(P): nodes mapped through automorphism.site_permutation, each step
    (edge_index, sense) mapped to (image_edge_index, sense * orientation_sign).

    Both the source path and the transformed path are independently
    validated against `lattice` via transporters._validate_steps_against_lattice
    -- the same node<->edge<->sense connectivity check already exhaustively
    tested in lot 1B-1 (test_transporters.py), reused here rather than
    duplicated (an intra-package private import of already-tested logic,
    not a reach into level0's private namespace). OrientedPath.__post_init__
    alone only checks lattice-independent shape invariants (sense in
    {+1,-1}, edge_index >= 0), which is not sufficient for this
    network-bound validation.
    """
    if automorphism.lattice_signature != lattice.name:
        raise ValueError(
            f"automorphism.lattice_signature ({automorphism.lattice_signature!r}) does not match "
            f"lattice.name ({lattice.name!r})"
        )
    _validate_steps_against_lattice(lattice, path)

    new_nodes = tuple(automorphism.site_permutation[node] for node in path.nodes)
    new_steps = tuple(
        (automorphism.edge_image[edge_index][0], sense * automorphism.edge_image[edge_index][1])
        for edge_index, sense in path.steps
    )
    transformed = OrientedPath(nodes=new_nodes, steps=new_steps)
    _validate_steps_against_lattice(lattice, transformed)

    # Explicit, even though guaranteed by the construction above -- kept as
    # a readable, self-contained restatement of the contract (mirrors
    # SpectralLevelGroup's own style of asserting derived invariants
    # explicitly rather than only implicitly).
    if transformed.source != automorphism.site_permutation[path.source]:
        raise ValueError("transformed path's source does not match automorphism applied to the original source")
    if transformed.destination != automorphism.site_permutation[path.destination]:
        raise ValueError(
            "transformed path's destination does not match automorphism applied to the original destination"
        )
    if len(transformed.nodes) != len(path.nodes):
        raise ValueError(
            f"transformed path length ({len(transformed.nodes)}) does not match original length ({len(path.nodes)})"
        )

    return transformed


# ---------------------------------------------------------------------------
# Pairing with the Level0 unitary U_A
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnitaryAutomorphism:
    """A GraphAutomorphism paired with its Level0 unitary operator U_A,
    built from the SAME site_permutation. `label` identifies the
    generator lineage (e.g. "identity", "translation", "reflection", or a
    composed label for group-closure elements)."""

    label: str
    automorphism: GraphAutomorphism
    unitary: sp.csr_matrix


def identity_unitary_automorphism(lattice: Lattice, keys: Sequence[np.uint64]) -> UnitaryAutomorphism:
    return UnitaryAutomorphism(
        label="identity",
        automorphism=identity_automorphism(lattice),
        unitary=sp.identity(len(keys), format="csr", dtype=np.complex128),
    )


def translation_unitary_automorphism(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    *,
    external_charges: Sequence[object] | None = None,
) -> UnitaryAutomorphism:
    return UnitaryAutomorphism(
        label="translation",
        automorphism=translation_automorphism(lattice),
        unitary=build_translation_operator(
            lattice, n_flavors, spin, keys, key_index, external_charges=external_charges
        ),
    )


def reflection_unitary_automorphism(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    *,
    external_charges: Sequence[object] | None = None,
) -> UnitaryAutomorphism:
    return UnitaryAutomorphism(
        label="reflection",
        automorphism=reflection_automorphism(lattice),
        unitary=build_reflection_operator(
            lattice, n_flavors, spin, keys, key_index, external_charges=external_charges
        ),
    )


def compose_unitary_automorphisms(a: UnitaryAutomorphism, b: UnitaryAutomorphism) -> UnitaryAutomorphism:
    """Apply `a` first, then `b`, matching compose()'s own convention:
    the combined operator is b.unitary @ a.unitary (act with U_a on a
    state first, then U_b)."""
    return UnitaryAutomorphism(
        label=f"({a.label})then({b.label})",
        automorphism=compose(a.automorphism, b.automorphism),
        unitary=(b.unitary @ a.unitary).tocsr(),
    )


def generate_closed_unitary_subgroup(generators: Sequence[UnitaryAutomorphism]) -> tuple[UnitaryAutomorphism, ...]:
    """Same breadth-first closure as generate_closed_subgroup, but over
    UnitaryAutomorphism: every composite element carries its own U_A,
    built compositionally (sparse matrix products) rather than by calling
    back into level0 for anything beyond the elementary generators."""
    if not generators:
        raise ValueError("generate_closed_unitary_subgroup requires at least one generator")
    lattice_signature = generators[0].automorphism.lattice_signature
    for generator in generators:
        if generator.automorphism.lattice_signature != lattice_signature:
            raise ValueError("all generators must belong to the same lattice")

    dimension = generators[0].unitary.shape[0]
    n_nodes = len(generators[0].automorphism.site_permutation)
    identity_permutation = tuple(range(n_nodes))
    identity_element = UnitaryAutomorphism(
        label="identity",
        automorphism=GraphAutomorphism(
            lattice_signature=lattice_signature,
            site_permutation=identity_permutation,
            edge_endpoints=generators[0].automorphism.edge_endpoints,
        ),
        unitary=sp.identity(dimension, format="csr", dtype=np.complex128),
    )

    seen: dict[tuple[int, ...], UnitaryAutomorphism] = {identity_permutation: identity_element}
    queue = [identity_element]
    for generator in generators:
        if generator.automorphism.site_permutation not in seen:
            seen[generator.automorphism.site_permutation] = generator
            queue.append(generator)

    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for generator in generators:
            candidate = compose_unitary_automorphisms(current, generator)
            key = candidate.automorphism.site_permutation
            if key not in seen:
                seen[key] = candidate
                queue.append(candidate)

    return tuple(sorted(seen.values(), key=lambda element: element.automorphism.site_permutation))


# ---------------------------------------------------------------------------
# V07: empirical subgroup reduction by commutation with the Hamiltonian
# ---------------------------------------------------------------------------


def hamiltonian_commutator_defect(unitary: sp.spmatrix, hamiltonian: sp.spmatrix) -> float:
    """||U_A H - H U_A||_F / max(||H||_F, 1) -- a relative defect, so the
    tolerance is comparable across Hamiltonians of different overall scale."""
    commutator = (unitary @ hamiltonian - hamiltonian @ unitary).tocsr()
    commutator.eliminate_zeros()
    commutator_norm = float(np.sqrt(np.sum(np.abs(commutator.data) ** 2))) if commutator.nnz else 0.0

    hamiltonian_csr = hamiltonian.tocsr()
    hamiltonian_norm = float(np.sqrt(np.sum(np.abs(hamiltonian_csr.data) ** 2))) if hamiltonian_csr.nnz else 0.0

    return commutator_norm / max(hamiltonian_norm, 1.0)


def symmetry_subgroup(
    closed_candidates: Sequence[UnitaryAutomorphism], hamiltonian: sp.spmatrix, *, tolerance: float
) -> tuple[UnitaryAutomorphism, ...]:
    """Filter closed_candidates (expected to already be closed under
    composition, e.g. generate_closed_unitary_subgroup's output) to those
    whose U_A commutes with `hamiltonian` within `tolerance` -- purely
    empirical, from the measured commutator defect; the algorithm never
    assumes in advance which elements will survive.

    The result is closed under composition by construction (the
    centralizer of any operator within a group is itself a subgroup: if
    [H,A]=0 and [H,B]=0 then [H,AB]=0), verified explicitly below rather
    than only asserted mathematically -- raises ValueError if the input
    was not itself a closed group, which would break this guarantee.
    """
    survivors = tuple(
        candidate
        for candidate in closed_candidates
        if hamiltonian_commutator_defect(candidate.unitary, hamiltonian) <= tolerance
    )
    if not survivors:
        raise ValueError("no candidate automorphism (not even identity) commutes with hamiltonian within tolerance")

    survivor_permutations = {element.automorphism.site_permutation for element in survivors}
    for first in survivors:
        for second in survivors:
            composed = compose(first.automorphism, second.automorphism)
            if composed.site_permutation not in survivor_permutations:
                raise ValueError(
                    "the commutator-filtered subgroup is not closed under composition -- "
                    "closed_candidates was likely not itself a closed group"
                )
    return survivors
