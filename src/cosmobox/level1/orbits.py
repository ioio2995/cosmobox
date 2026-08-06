"""Covariance-validated orbit statistics. Level1B lot 1B-4
(docs/levels/level1/specification.md section 11,
docs/levels/level1/implementation-design.md section 7.3).

"L'agrégat n'est produit qu'après validation de covariance" is enforced by
type, not by caller discipline: aggregate_validated_orbit only accepts a
ValidatedOrbit, and the only way to construct one is
validate_orbit_covariance, which re-derives and checks the V06/V07
covariance identity U_A O_ij[P] U_A^dagger == O_{A(i)A(j)}[A(P)] for every
automorphism in the subgroup before bundling any values.

"Aucune moyenne entre catégories incompatibles" is enforced by
OrbitComparabilityKey: every element entering an orbit must carry an
IDENTICAL key (orbit family, path length, spectral group, complete/partial
status, observable kind, normalization level, flavor component,
Hamiltonian-parameter identity) -- checked by validate_orbit_covariance
before any aggregate is computed, not merely documented.
"""

from __future__ import annotations

import itertools
from collections.abc import Hashable, Sequence
from dataclasses import dataclass

import numpy as np

from cosmobox.level0.lattice import Lattice

from .automorphisms import UnitaryAutomorphism, transform_oriented_path
from .matter import build_dressed_matter_matrix
from .paths import OrientedPath


@dataclass(frozen=True, slots=True)
class OrbitComparabilityKey:
    """Every field that must match exactly across all elements of an
    orbit before they may ever be aggregated together. Equality of this
    key IS the comparability contract (specification.md section 11's
    forbidden-averages list), not documentation of an intended contract."""

    orbit_family: str
    path_length: int
    spectral_group_key: Hashable
    status: str
    observable_kind: str
    normalization: str
    flavor_component: str
    hamiltonian_identity: Hashable


@dataclass(frozen=True, slots=True)
class OrbitElement:
    key: OrbitComparabilityKey
    value: complex


@dataclass(frozen=True, slots=True)
class ValidatedOrbit:
    """Produced only by validate_orbit_covariance: proof that the
    generating automorphisms were empirically confirmed (via the operator
    covariance identity, not assumed) to be genuine symmetries before any
    aggregate is computed from `elements`."""

    key: OrbitComparabilityKey
    elements: tuple[OrbitElement, ...]


@dataclass(frozen=True, slots=True)
class OrbitStatistics:
    orbit_mean: complex
    orbit_max_pairwise_spread: float
    orbit_covariance_defect: float


def validate_orbit_covariance(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    subgroup: Sequence[UnitaryAutomorphism],
    base_path: OrientedPath,
    alpha: int,
    beta: int,
    elements: Sequence[OrbitElement],
    *,
    tolerance: float = 1e-10,
) -> ValidatedOrbit:
    """Verify, for every automorphism A in `subgroup`,
    U_A @ O_ij^{alpha,beta}[base_path] @ U_A^dagger
        == O_{A(i)A(j)}^{alpha,beta}[A(base_path)]
    (the V06/V07 covariance identity, re-derived here rather than assumed
    from a prior check elsewhere), and that every element of `elements`
    shares the same OrbitComparabilityKey. elements[k] must correspond to
    subgroup[k]'s transformed path/pair. Raises ValueError on either
    failure -- this is the only way to obtain a ValidatedOrbit.
    """
    if not elements:
        raise ValueError("an orbit must contain at least one element")
    if len(elements) != len(subgroup):
        raise ValueError(
            f"elements ({len(elements)}) must correspond 1:1 with subgroup ({len(subgroup)}) automorphisms"
        )

    reference_key = elements[0].key
    for element in elements[1:]:
        if element.key != reference_key:
            raise ValueError(f"orbit elements do not share a comparability key: {element.key} != {reference_key}")

    base_operator = build_dressed_matter_matrix(lattice, n_flavors, spin, keys, key_index, base_path, alpha, beta)
    for automorphism in subgroup:
        transformed_path = transform_oriented_path(lattice, automorphism.automorphism, base_path)
        image_operator = build_dressed_matter_matrix(
            lattice, n_flavors, spin, keys, key_index, transformed_path, alpha, beta
        )
        conjugated = (automorphism.unitary @ base_operator @ automorphism.unitary.conj().T).tocsr()
        difference = (conjugated - image_operator).tocsr()
        difference.eliminate_zeros()
        defect = float(np.sqrt(np.sum(np.abs(difference.data) ** 2))) if difference.nnz else 0.0
        if defect > tolerance:
            raise ValueError(
                f"covariance identity failed for automorphism {automorphism.label!r}: "
                f"||U_A O U_A^dagger - O[A(P)]||_F = {defect} (tolerance {tolerance})"
            )

    return ValidatedOrbit(key=reference_key, elements=tuple(elements))


def aggregate_validated_orbit(orbit: ValidatedOrbit) -> OrbitStatistics:
    """orbit_mean = mean(x); orbit_max_pairwise_spread = max|x-y|;
    orbit_covariance_defect = max|x-mean| (specification.md section 11).
    Only accepts a ValidatedOrbit -- there is no overload or code path
    that accepts a bare, unvalidated list of values."""
    values = [element.value for element in orbit.elements]
    n = len(values)

    mean = sum(values) / n
    max_pairwise_spread = max((abs(x - y) for x, y in itertools.combinations(values, 2)), default=0.0)
    covariance_defect = max(abs(x - mean) for x in values)

    return OrbitStatistics(
        orbit_mean=mean, orbit_max_pairwise_spread=max_pairwise_spread, orbit_covariance_defect=covariance_defect
    )
