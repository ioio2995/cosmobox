"""Exact construction of the Level0 physical subspace (G_i = 0 for all i).

Charges are tracked as doubled integers to keep the whole enumeration free
of ``Fraction`` arithmetic: since ``Q_i = sum_alpha(n_i,alpha - 1/2)``,

    Q~_i = 2*Q_i = 2*sum_alpha(n_i,alpha) - M

is always an integer, even when M is odd. ``Fraction`` is only used at the
public API boundary to accept integer or half-integer external charges.

Gauss's law summed over all nodes gives ``Q_tot = -sum_i q_i^ext`` (each
internal flux appears once with each sign in the sum, so only the external
charges and matter charges survive) -- this fixes the sign of the cheap
total-charge sector filter applied before the per-sector flux search.
"""

from __future__ import annotations

import itertools
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from .charges import doubled_external_charges, normalize_external_charges
from .encoding import encode, validate_capacity, validate_spin
from .lattice import Lattice


@dataclass(frozen=True, slots=True)
class SectorReport:
    """Report for one charge sector Q = (Q_1, ..., Q_N)."""

    charge_vector: tuple[Fraction, ...]
    matter_multiplicity: int
    n_flux_admissible: int
    dimension: int


@dataclass(frozen=True, slots=True)
class BasisReport:
    """The exact physical basis and its per-sector breakdown.

    ``sectors`` lists every charge vector Q encountered (after the cheap
    Q_tot filter), including those with ``n_flux_admissible=0`` -- so
    ``matter_multiplicity`` is never lost for an excluded sector.
    ``excluded_sectors`` is the subset of ``sectors`` with
    ``n_flux_admissible=0``, kept as a convenience view (same
    ``SectorReport`` objects, not just their charge vectors).
    """

    keys: tuple[np.uint64, ...]
    sectors: tuple[SectorReport, ...]
    excluded_sectors: tuple[SectorReport, ...]
    mean_flux_configs_per_occupation: float
    max_flux_configs_per_occupation: int


def _incident_edges(lattice: Lattice) -> dict[int, list[tuple[int, int]]]:
    incident: dict[int, list[tuple[int, int]]] = {node: [] for node in lattice.nodes}
    for edge_index, edge in enumerate(lattice.edges):
        incident[edge.source].append((edge_index, 1))
        incident[edge.target].append((edge_index, -1))
    return incident


def _tree_parent_edges(
    lattice: Lattice, incident: dict[int, list[tuple[int, int]]]
) -> dict[int, tuple[int, int]]:
    """For each non-root node: (parent_edge_index, sense_from_node_to_parent)."""
    tree_edge_set = set(lattice.tree_edges)
    parent_edge: dict[int, tuple[int, int]] = {}
    visited = {lattice.root}
    queue = [lattice.root]
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        for edge_index, sense in incident[node]:
            if edge_index not in tree_edge_set:
                continue
            edge = lattice.edges[edge_index]
            neighbour = edge.target if sense == 1 else edge.source
            if neighbour not in visited:
                visited.add(neighbour)
                parent_edge[neighbour] = (edge_index, -sense)
                queue.append(neighbour)

    if len(parent_edge) != len(lattice.nodes) - 1:
        raise ValueError(
            "tree does not provide exactly one parent edge per non-root node "
            f"(got {len(parent_edge)}, expected {len(lattice.nodes) - 1}); "
            "tree_edges must form a spanning tree rooted at lattice.root"
        )
    return parent_edge


def _known_edges_for_resolution(
    lattice: Lattice,
    incident: dict[int, list[tuple[int, int]]],
    parent_edge: dict[int, tuple[int, int]],
) -> dict[int, list[tuple[int, int]]]:
    """Incident edges of each node excluding its own parent tree edge.

    For the root (which has no parent edge) this is simply all of its
    incident edges, which is exactly what the final Gauss-law check needs.
    """
    known: dict[int, list[tuple[int, int]]] = {}
    for node in lattice.nodes:
        parent_index = parent_edge[node][0] if node in parent_edge else None
        known[node] = [(idx, sense) for idx, sense in incident[node] if idx != parent_index]
    return known


def _resolve_flux(
    lattice: Lattice,
    known_edges: dict[int, list[tuple[int, int]]],
    parent_edge: dict[int, tuple[int, int]],
    doubled_charge: tuple[int, ...],
    spin: int,
    chord_flux: dict[int, int],
) -> list[int] | None:
    """Solve G_i = 0 leaves -> root for one chord flux assignment, doubled-integer exact.

    Returns the full per-edge E_e list on success, or None if the chord
    assignment is incompatible with this charge sector (non-integer or
    out-of-[-S,S] intermediate flux, or a failed root closure).
    """
    n_edges = len(lattice.edges)
    flux: list[int | None] = [None] * n_edges
    for edge_index, value in chord_flux.items():
        flux[edge_index] = value

    for node in lattice.resolution_order:
        if node == lattice.root:
            continue
        parent_index, sense_to_parent = parent_edge[node]
        known_sum = sum(sense * flux[idx] for idx, sense in known_edges[node])  # type: ignore[misc]
        numerator = doubled_charge[node] - 2 * known_sum
        if numerator % 2 != 0:
            return None
        electric_field = sense_to_parent * (numerator // 2)
        if not (-spin <= electric_field <= spin):
            return None
        flux[parent_index] = electric_field

    root = lattice.root
    root_known_sum = sum(sense * flux[idx] for idx, sense in known_edges[root])  # type: ignore[misc]
    if 2 * root_known_sum != doubled_charge[root]:
        return None

    return flux  # type: ignore[return-value]


def build_basis(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    external_charges: Sequence[object] | None = None,
) -> BasisReport:
    """Enumerate the exact physical basis via the spanning-tree Gauss-law resolution."""
    validate_spin(spin)
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    validate_capacity(n_nodes, n_flavors, n_edges)

    q2_ext = doubled_external_charges(normalize_external_charges(n_nodes, external_charges))
    target_q2_tot = -sum(q2_ext)

    incident = _incident_edges(lattice)
    parent_edge = _tree_parent_edges(lattice, incident)
    known_edges = _known_edges_for_resolution(lattice, incident, parent_edge)

    occupations_by_sector: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
    for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors):
        charge_vector_q2 = tuple(
            2 * sum(occupation[node * n_flavors : (node + 1) * n_flavors]) - n_flavors
            for node in lattice.nodes
        )
        if sum(charge_vector_q2) != target_q2_tot:
            continue
        occupations_by_sector.setdefault(charge_vector_q2, []).append(occupation)

    keys: list[int] = []
    sectors: list[SectorReport] = []
    flux_configs_per_occupation: list[int] = []

    for charge_vector_q2 in sorted(occupations_by_sector):
        occupation_list = occupations_by_sector[charge_vector_q2]
        doubled_charge = tuple(charge_vector_q2[i] + q2_ext[i] for i in lattice.nodes)

        admissible_flux_configs: list[list[int]] = []
        for chord_values in itertools.product(range(-spin, spin + 1), repeat=len(lattice.chords)):
            chord_flux = dict(zip(lattice.chords, chord_values))
            resolved = _resolve_flux(lattice, known_edges, parent_edge, doubled_charge, spin, chord_flux)
            if resolved is not None:
                admissible_flux_configs.append(resolved)

        n_flux = len(admissible_flux_configs)
        matter_multiplicity = len(occupation_list)
        charge_vector = tuple(Fraction(q2, 2) for q2 in charge_vector_q2)
        flux_configs_per_occupation.extend([n_flux] * matter_multiplicity)

        sectors.append(
            SectorReport(
                charge_vector=charge_vector,
                matter_multiplicity=matter_multiplicity,
                n_flux_admissible=n_flux,
                dimension=matter_multiplicity * n_flux,
            )
        )
        for occupation in occupation_list:
            for flux in admissible_flux_configs:
                keys.append(int(encode(lattice, n_flavors, spin, occupation, flux)))

    if len(keys) != len(set(keys)):
        raise RuntimeError(
            "basis generation emitted duplicate physical states; "
            "this indicates a bug in the tree resolution or the encoding, not a case to silently repair"
        )
    sorted_keys = tuple(np.uint64(key) for key in sorted(keys))
    excluded_sectors = tuple(sector for sector in sectors if sector.n_flux_admissible == 0)

    return BasisReport(
        keys=sorted_keys,
        sectors=tuple(sectors),
        excluded_sectors=excluded_sectors,
        mean_flux_configs_per_occupation=(
            statistics.fmean(flux_configs_per_occupation) if flux_configs_per_occupation else 0.0
        ),
        max_flux_configs_per_occupation=(
            max(flux_configs_per_occupation) if flux_configs_per_occupation else 0
        ),
    )
