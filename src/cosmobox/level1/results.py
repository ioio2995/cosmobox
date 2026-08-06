"""Internal result model and scientific identity, independent of any
particular schema version. Level1B lot 1B-7
(docs/levels/level1/specification.md, docs/decisions/decisions.md D019).

A ResultRecord bundles a scientific identity (ScientificIdentity), a
provenance record (Provenance), a record_kind/observable_kind pair drawn
from closed, audited enumerations, and a PAYLOAD that is always one of the
already-existing, already-validated Python result types from lots 1B-1
through 1B-6 (NormalizedMoment, HermitianRestrictedDiagnostics,
NonHermitianRestrictedDiagnostics, FlavorCorrelatorMatrix, SymmetryLabel,
MatchOutcome, RobustnessResult, OrbitResultPayload) or a bare
float/complex/tuple already produced by an existing function. This module
performs NO scientific computation: every payload it accepts was already
computed and validated elsewhere. Its only job is to attach identity and
provenance, and to enforce -- via a closed, audited table, never a free
string supplied by the caller -- that record_kind, observable_kind, and
the payload's own Python type are mutually consistent.

observable_kind was fixed by auditing every level1 module that produces a
named, reportable quantity as of lot 1B-6 (local_observables.py,
matter.py/orbits.py's DRESSED_MATTER_OBSERVABLE_KIND, flavor.py,
matching.py). path_phase_coherence (docs/decisions/decisions.md D013's
own secondary robustness list) is deliberately NOT included: no module
computes it yet. Extending this enumeration when a new observable is
implemented is a normal, expected evolution -- it is closed only in the
sense that nothing here may be added by a caller at record-construction
time, not that it can never grow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .diagnostics import HermitianRestrictedDiagnostics, NonHermitianRestrictedDiagnostics
from .flavor import FlavorCorrelatorMatrix
from .local_observables import NormalizedMoment
from .matching import MatchOutcome, SymmetryLabel
from .orbits import OrbitComparabilityKey, OrbitStatistics, ValidatedOrbit, aggregate_validated_orbit
from .restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from .robustness import RobustnessResult

# ---------------------------------------------------------------------------
# Closed enumerations, audited against the actual lot 1B-1..1B-6 code
# ---------------------------------------------------------------------------

RAW_OBSERVABLE_KINDS = ("C_QQ_raw", "C_QQ_conn", "C_TT_raw", "C_TT_conn", "O_ij_raw")
NORMALIZED_OBSERVABLE_KINDS = ("rho_QQ", "G_occ", "gamma_O")
FLAVOR_DIAGNOSTIC_KINDS = ("raw_G", "flavor_singlet", "flavor_frobenius_squared", "flavor_singular_values", "flavor_singular_value_ratio")
SYMMETRY_LABEL_KINDS = ("flavor_casimir_label", "translation_character", "reflection_character")

OBSERVABLE_KINDS = RAW_OBSERVABLE_KINDS + NORMALIZED_OBSERVABLE_KINDS + FLAVOR_DIAGNOSTIC_KINDS + SYMMETRY_LABEL_KINDS

RECORD_KINDS = (
    "raw_observable",
    "normalized_observable",
    "restricted_diagnostic",
    "flavor_diagnostic",
    "orbit_statistic",
    "symmetry_label",
    "matching",
    "robustness",
)

_BASE_OBSERVABLE_KINDS = frozenset(RAW_OBSERVABLE_KINDS) | frozenset(NORMALIZED_OBSERVABLE_KINDS) | frozenset(FLAVOR_DIAGNOSTIC_KINDS)

_ALLOWED_OBSERVABLE_KINDS_BY_RECORD_KIND: dict[str, frozenset[str]] = {
    "raw_observable": frozenset(RAW_OBSERVABLE_KINDS),
    "normalized_observable": frozenset(NORMALIZED_OBSERVABLE_KINDS),
    "restricted_diagnostic": _BASE_OBSERVABLE_KINDS,
    "flavor_diagnostic": frozenset(FLAVOR_DIAGNOSTIC_KINDS),
    "orbit_statistic": _BASE_OBSERVABLE_KINDS,
    "symmetry_label": frozenset(SYMMETRY_LABEL_KINDS),
    "matching": _BASE_OBSERVABLE_KINDS | frozenset(SYMMETRY_LABEL_KINDS),
    "robustness": _BASE_OBSERVABLE_KINDS | frozenset(SYMMETRY_LABEL_KINDS),
}

_FLAVOR_DIAGNOSTIC_PAYLOAD_TYPES: dict[str, tuple[type, ...]] = {
    "raw_G": (FlavorCorrelatorMatrix,),
    "flavor_singlet": (complex,),
    "flavor_frobenius_squared": (float,),
    "flavor_singular_values": (tuple,),
    "flavor_singular_value_ratio": (NormalizedMoment,),
}


# ---------------------------------------------------------------------------
# Scientific identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HamiltonianIdentity:
    """The Hamiltonian parameters that are part of a result's scientific
    identity. h is represented only as `h_is_zero` -- the only value ever
    produced by any level1 code so far (the frozen reference campaign and
    j_break control both use h=0); a genuinely nonzero h has no producer
    to audit against yet, so no richer shape is invented here."""

    J: tuple[float, ...]
    h_is_zero: bool
    t: float
    g_E: float
    K: float

    def __post_init__(self) -> None:
        if not self.J:
            raise ValueError("J must be non-empty")
        for index, value in enumerate(self.J):
            if not math.isfinite(value):
                raise ValueError(f"J[{index}] must be finite, got {value}")
        for name, value in (("t", self.t), ("g_E", self.g_E), ("K", self.K)):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")


@dataclass(frozen=True, slots=True)
class SpectralGroupIdentity:
    status: str
    multiplicity: int
    twice_T: int | None

    def __post_init__(self) -> None:
        if self.status not in (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE):
            raise ValueError(f"status must be one of ({COMPLETE_MULTIPLET!r}, {PARTIAL_SUBSPACE!r}), got {self.status!r}")
        if self.multiplicity <= 0:
            raise ValueError(f"multiplicity must be > 0, got {self.multiplicity}")
        if self.twice_T is not None and self.twice_T < 0:
            raise ValueError(f"twice_T must be >= 0 or None, got {self.twice_T}")


@dataclass(frozen=True, slots=True)
class ScientificIdentity:
    """Every field here must be derived from an already-typed source
    object (a Lattice, HamiltonianParameters, SpectralGroupState/
    SpectralLevelGroup, OrientedPath, ...) -- never invented by
    serialization.py. path/flavor_component/normalization are optional
    (None) for results that are not tied to a single ordered pair/path
    (e.g. a symmetry label or a whole-campaign matching statistic)."""

    geometry: str
    spin: int
    n_flavors: int
    hamiltonian: HamiltonianIdentity
    sector: str
    spectral_group: SpectralGroupIdentity
    path: tuple[int, ...] | None
    flavor_component: str | None
    normalization: str | None

    def __post_init__(self) -> None:
        if not self.geometry:
            raise ValueError("geometry must be non-empty")
        if self.spin < 1:
            raise ValueError(f"spin must be >= 1, got {self.spin}")
        if self.n_flavors != 2:
            raise ValueError(f"n_flavors must be 2 (M=2, per D006), got {self.n_flavors}")
        if not isinstance(self.hamiltonian, HamiltonianIdentity):
            raise ValueError(f"hamiltonian must be a HamiltonianIdentity, got {type(self.hamiltonian)}")
        if not self.sector:
            raise ValueError("sector must be non-empty")
        if not isinstance(self.spectral_group, SpectralGroupIdentity):
            raise ValueError(f"spectral_group must be a SpectralGroupIdentity, got {type(self.spectral_group)}")
        if self.path is not None and len(self.path) == 0:
            raise ValueError("path, if provided, must be non-empty (use None when not applicable)")


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Provenance:
    """Transcribed, never recomputed: spectral_status mirrors the source
    group's own status; source_type/source_module record which Python
    type and module actually produced the payload (an audit trail, not a
    scientific claim); match_status/covariance_validated are copied from
    an existing MatchOutcome/ValidatedOrbit when one exists upstream of
    this record, None when not applicable."""

    spectral_status: str
    source_type: str
    source_module: str
    match_status: str | None
    covariance_validated: bool | None

    def __post_init__(self) -> None:
        if self.spectral_status not in (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE):
            raise ValueError(
                f"spectral_status must be one of ({COMPLETE_MULTIPLET!r}, {PARTIAL_SUBSPACE!r}), "
                f"got {self.spectral_status!r}"
            )
        if not self.source_type:
            raise ValueError("source_type must be non-empty")
        if not self.source_module:
            raise ValueError("source_module must be non-empty")


# ---------------------------------------------------------------------------
# Orbit result payload -- constructible only from a real ValidatedOrbit
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OrbitResultPayload:
    statistics: OrbitStatistics
    comparability_key: OrbitComparabilityKey
    element_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.statistics, OrbitStatistics):
            raise ValueError(f"statistics must be an OrbitStatistics, got {type(self.statistics)}")
        if not isinstance(self.comparability_key, OrbitComparabilityKey):
            raise ValueError(f"comparability_key must be an OrbitComparabilityKey, got {type(self.comparability_key)}")
        if self.element_count <= 0:
            raise ValueError(f"element_count must be > 0, got {self.element_count}")


def build_orbit_result_payload(orbit: ValidatedOrbit) -> OrbitResultPayload:
    """The only way to obtain an OrbitResultPayload: statistics are
    computed HERE, from the ValidatedOrbit itself (via
    aggregate_validated_orbit, orbits.py, never recomputed independently),
    so there is no way to pass in statistics unrelated to `orbit` --
    "n'accepte que les résultats provenant du pipeline validé" is
    structural, not a documentation promise, since ValidatedOrbit is
    itself only constructible via validate_orbit_covariance (1B-4's
    private token)."""
    if not isinstance(orbit, ValidatedOrbit):
        raise ValueError(f"orbit must be a ValidatedOrbit, got {type(orbit)}")
    statistics = aggregate_validated_orbit(orbit)
    return OrbitResultPayload(statistics=statistics, comparability_key=orbit.key, element_count=len(orbit.elements))


# ---------------------------------------------------------------------------
# Result record
# ---------------------------------------------------------------------------

_PAYLOAD_TYPES_BY_RECORD_KIND: dict[str, tuple[type, ...]] = {
    "restricted_diagnostic": (HermitianRestrictedDiagnostics, NonHermitianRestrictedDiagnostics),
    "orbit_statistic": (OrbitResultPayload,),
    "symmetry_label": (SymmetryLabel,),
    "matching": (MatchOutcome,),
    "robustness": (RobustnessResult,),
}


def _expected_payload_types(record_kind: str, observable_kind: str) -> tuple[type, ...]:
    if record_kind == "raw_observable":
        return (complex,) if observable_kind == "O_ij_raw" else (float,)
    if record_kind == "normalized_observable":
        return (NormalizedMoment,)
    if record_kind == "flavor_diagnostic":
        return _FLAVOR_DIAGNOSTIC_PAYLOAD_TYPES[observable_kind]
    return _PAYLOAD_TYPES_BY_RECORD_KIND[record_kind]


@dataclass(frozen=True, slots=True)
class ResultRecord:
    """A single Level1 scientific result, ready for serialization.py to
    convert to JSON. Every field is derived from already-validated
    sources; record_kind/observable_kind/payload-type coherence is
    enforced here via the closed tables above, never a free string."""

    identity: ScientificIdentity
    provenance: Provenance
    record_kind: str
    observable_kind: str
    payload: object

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ScientificIdentity):
            raise ValueError(f"identity must be a ScientificIdentity, got {type(self.identity)}")
        if not isinstance(self.provenance, Provenance):
            raise ValueError(f"provenance must be a Provenance, got {type(self.provenance)}")
        if self.record_kind not in RECORD_KINDS:
            raise ValueError(f"record_kind must be one of {RECORD_KINDS}, got {self.record_kind!r}")

        allowed_observable_kinds = _ALLOWED_OBSERVABLE_KINDS_BY_RECORD_KIND[self.record_kind]
        if self.observable_kind not in allowed_observable_kinds:
            raise ValueError(
                f"observable_kind {self.observable_kind!r} is not valid for record_kind {self.record_kind!r}; "
                f"expected one of {sorted(allowed_observable_kinds)}"
            )

        expected_types = _expected_payload_types(self.record_kind, self.observable_kind)
        # complex/float require an exact type match: bool is an int
        # subclass and float is not a complex subclass in Python's type
        # system, so isinstance() alone would be either too permissive
        # (bool passing as int-like) or too strict (float rejected by an
        # isinstance(..., complex) check) -- exact `type(...) is ...` is
        # unambiguous for these two.
        if complex in expected_types or float in expected_types:
            if type(self.payload) not in expected_types:
                raise ValueError(
                    f"payload for record_kind={self.record_kind!r}, observable_kind={self.observable_kind!r} "
                    f"must be exactly one of {expected_types}, got {type(self.payload)}"
                )
        elif not isinstance(self.payload, expected_types):
            raise ValueError(
                f"payload for record_kind={self.record_kind!r}, observable_kind={self.observable_kind!r} "
                f"must be an instance of {expected_types}, got {type(self.payload)}"
            )

        # Cross-object guard rail: a RobustnessResult's own __post_init__
        # cannot see the group's status (it is a separate object), so a
        # definitive verdict attached to a partial_subspace identity would
        # otherwise slip through undetected -- this is exactly the
        # "aucun verdict definitif pour partial_subspace" contract,
        # enforced here where both objects are visible together.
        if self.record_kind == "robustness" and self.identity.spectral_group.status == PARTIAL_SUBSPACE:
            if self.payload.verdict != "indeterminate":
                raise ValueError(
                    "a robustness record whose spectral_group.status is 'partial_subspace' must carry an "
                    f"'indeterminate' verdict, got {self.payload.verdict!r}"
                )
