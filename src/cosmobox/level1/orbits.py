"""Covariance-validated orbit statistics. Level1B lot 1B-4
(docs/levels/level1/specification.md section 11,
docs/levels/level1/implementation-design.md section 7.3).

"L'agrégat n'est produit qu'après validation de covariance" is enforced by
type, not by caller discipline: aggregate_validated_orbit only accepts a
ValidatedOrbit, and the only way to construct one is
validate_orbit_covariance, which re-derives and checks the V06/V07
covariance identity U_A O_ij[P] U_A^dagger == O_{A(i)A(j)}[A(P)] for every
automorphism in the subgroup before bundling any values -- and, per the
1B-4 review fix, COMPUTES those values itself (via
canonical_multiplet_expectation / exploratory_partial_subspace_mean on
each automorphism's own image_operator) rather than accepting them from
the caller. There is no parameter through which a caller can inject an
OrbitElement.value unrelated to the verified operator identity.

"Aucune moyenne entre catégories incompatibles" is enforced by
OrbitComparabilityKey: every element entering an orbit must carry an
IDENTICAL key (orbit family, path length, spectral group, complete/partial
status, observable kind, normalization level, flavor component,
Hamiltonian-parameter identity) -- checked by validate_orbit_covariance
before any aggregate is computed, not merely documented. The four fields
that are locally derivable from the function's own other arguments
(path_length, status, observable_kind, flavor_component) are cross-checked
against `key` rather than trusted at face value -- a key that lies about
any of them raises ValueError before any ValidatedOrbit is built. The
remaining fields (orbit_family, spectral_group_key, normalization,
hamiltonian_identity) are not derivable from what this function sees and
remain caller-supplied.

ValidatedOrbit itself is only constructible through validate_orbit_covariance:
its __post_init__ requires a private token that only this module holds a
reference to (never exported), so direct construction
`ValidatedOrbit(key=..., elements=...)` from outside this module cannot
succeed even though the type is public -- closing the gap where a
caller-fabricated ValidatedOrbit could previously be handed straight to
aggregate_validated_orbit.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field

import numpy as np

from cosmobox.level0.lattice import Lattice

from .automorphisms import UnitaryAutomorphism, transform_oriented_path
from .matter import build_dressed_matter_matrix
from .paths import OrientedPath
from .restricted import SpectralGroupState, canonical_multiplet_expectation, exploratory_partial_subspace_mean

DRESSED_MATTER_OBSERVABLE_KIND = "O_ij_raw"

# Private, never exported (not in __init__.py, not re-exported by this
# module's own public surface): the only way another module can obtain a
# reference to this exact object is by reaching into orbits._VALIDATION_TOKEN
# directly, an explicit, conscious bypass -- not an accidental one. This is
# the mechanism, not caller discipline, that makes validate_orbit_covariance
# the only ordinary way to construct a ValidatedOrbit.
_VALIDATION_TOKEN = object()


def flavor_component_label(alpha: int, beta: int) -> str:
    """Canonical OrbitComparabilityKey.flavor_component string for a given
    (alpha, beta) pair -- the format validate_orbit_covariance checks
    key.flavor_component against, exported so callers can build a
    conforming key rather than guess the format."""
    return f"alpha{alpha}_beta{beta}"


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
    aggregate is computed from `elements`.

    Despite being a public type, direct construction from outside this
    module cannot succeed: `_token` must be this module's private
    _VALIDATION_TOKEN object, which is never exported. __post_init__ also
    enforces the invariants a validated orbit must satisfy regardless of
    who holds the token: a non-empty element list, every element's key
    identical to self.key, and every element's value a finite complex
    number.
    """

    key: OrbitComparabilityKey
    elements: tuple[OrbitElement, ...]
    _token: object = field(repr=False)

    def __post_init__(self) -> None:
        if self._token is not _VALIDATION_TOKEN:
            raise ValueError(
                "ValidatedOrbit may only be constructed by validate_orbit_covariance -- "
                "direct construction from outside cosmobox.level1.orbits is not a validated orbit"
            )
        if not self.elements:
            raise ValueError("a ValidatedOrbit must contain at least one element")
        for element in self.elements:
            if element.key != self.key:
                raise ValueError(
                    f"orbit element key {element.key} does not match ValidatedOrbit.key {self.key}"
                )
            value = complex(element.value)
            if not (math.isfinite(value.real) and math.isfinite(value.imag)):
                raise ValueError(f"orbit element value is not finite: {element.value}")


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
    group_state: SpectralGroupState,
    base_path: OrientedPath,
    alpha: int,
    beta: int,
    key: OrbitComparabilityKey,
    *,
    tolerance: float = 1e-10,
) -> ValidatedOrbit:
    """For every automorphism A in `subgroup`: transform base_path, build
    the image operator O_{A(i)A(j)}^{alpha,beta}[A(base_path)], verify
    U_A @ O_ij^{alpha,beta}[base_path] @ U_A^dagger == image_operator (the
    V06/V07 covariance identity), and ONLY THEN compute that element's
    value from image_operator itself (canonical_multiplet_expectation for
    a complete_multiplet group_state, exploratory_partial_subspace_mean
    for a partial_subspace one) -- there is no parameter through which a
    caller can supply an OrbitElement.value directly, so every value in
    the returned ValidatedOrbit is provably the one belonging to its own
    subgroup element's verified image_operator, not an arbitrary number
    merely tagged with a matching key.

    `key` carries the shared OrbitComparabilityKey identifying this orbit
    (family, path length, spectral group, status, observable kind,
    normalization, flavor component, Hamiltonian identity) -- it is
    metadata, not a value, and is attached identically to every produced
    element. The four fields derivable from this function's own other
    arguments (path_length, status, observable_kind, flavor_component)
    are cross-checked against `base_path`/`group_state`/`alpha`/`beta`
    before anything else is built; a key that lies about any of them
    raises ValueError. Raises ValueError if the covariance identity fails
    for any automorphism -- this is the only way to obtain a ValidatedOrbit.
    """
    if not subgroup:
        raise ValueError("an orbit must contain at least one subgroup element")

    if key.path_length != base_path.length:
        raise ValueError(f"key.path_length ({key.path_length}) does not match base_path.length ({base_path.length})")
    if key.status != group_state.status:
        raise ValueError(f"key.status ({key.status!r}) does not match group_state.status ({group_state.status!r})")
    if key.observable_kind != DRESSED_MATTER_OBSERVABLE_KIND:
        raise ValueError(
            f"key.observable_kind ({key.observable_kind!r}) does not match the dressed matter operator's "
            f"canonical observable_kind ({DRESSED_MATTER_OBSERVABLE_KIND!r})"
        )
    expected_flavor_component = flavor_component_label(alpha, beta)
    if key.flavor_component != expected_flavor_component:
        raise ValueError(
            f"key.flavor_component ({key.flavor_component!r}) does not match (alpha={alpha}, beta={beta}) "
            f"-- expected {expected_flavor_component!r}"
        )

    expectation = canonical_multiplet_expectation if group_state.is_complete else exploratory_partial_subspace_mean

    base_operator = build_dressed_matter_matrix(lattice, n_flavors, spin, keys, key_index, base_path, alpha, beta)
    elements: list[OrbitElement] = []
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

        value = expectation(image_operator, group_state, hermitian=False)
        elements.append(OrbitElement(key, value))

    return ValidatedOrbit(key=key, elements=tuple(elements), _token=_VALIDATION_TOKEN)


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
