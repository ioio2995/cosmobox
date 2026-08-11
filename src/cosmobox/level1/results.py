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

from cosmobox.level0.degeneracy import SpectralLevelGroup

from .diagnostics import HermitianRestrictedDiagnostics, NonHermitianRestrictedDiagnostics
from .flavor import FlavorCorrelatorMatrix
from .local_observables import NormalizedMoment
from .matching import EXACT_LABEL_MATCH, MatchOutcome, SymmetryLabel
from .orbits import OrbitComparabilityKey, OrbitStatistics, ValidatedOrbit, aggregate_validated_orbit
from .restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, SpectralGroupState
from .robustness import INDETERMINATE, RobustnessResult

# ---------------------------------------------------------------------------
# Closed enumerations, audited against the actual lot 1B-1..1B-6 code
# ---------------------------------------------------------------------------

RAW_OBSERVABLE_KINDS = ("C_QQ_raw", "C_QQ_conn", "C_TT_raw", "C_TT_conn", "O_ij_raw")
NORMALIZED_OBSERVABLE_KINDS = ("rho_QQ", "G_occ", "gamma_O")
FLAVOR_DIAGNOSTIC_KINDS = ("raw_G", "flavor_singlet", "flavor_frobenius_squared", "flavor_singular_values", "flavor_singular_value_ratio")
SYMMETRY_LABEL_KINDS = ("flavor_casimir_label", "translation_character", "reflection_character")

# D013/D018's own closed list of observables that ever receive an
# automatic binary robustness verdict: gamma_O (primary), G_occ, rho_QQ,
# C_TT_conn, flavor_singular_value_ratio (secondary). path_phase_coherence
# is ALSO frozen by D013 as a secondary robustness observable, but is
# deliberately NOT included here: no level1 module computes it yet, and
# this enumeration only ever lists observable_kinds a real function
# actually produces (see the module docstring). Add it here the day a
# module implements it -- not before.
ROBUSTNESS_OBSERVABLE_KINDS = ("gamma_O", "G_occ", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio")

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
    # Narrower than "matching" deliberately: D013/D018 close the list of
    # observables that may ever receive a robust/non_robust/indeterminate
    # verdict, unlike matching (which may legitimately be checked for any
    # observable one wants to investigate for S-dependence, verdict or not).
    "robustness": frozenset(ROBUSTNESS_OBSERVABLE_KINDS),
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
    """(status, multiplicity, twice_T) alone is insufficient to identify a
    spectral group within a single case: two distinct complete multiplets
    at the same (geometry, spin, Hamiltonian, sector) can share the same
    status/multiplicity/twice_T (observed on triangle S=2 j_break -- D022).
    spectral_window_group_index (the group's own position in the
    diagonalized case's full, unfiltered spectral-window sequence) is the
    exact discriminant added to resolve this; representative_energy is a
    descriptive, exact metadata field, never itself the discriminant and
    never compared with a tolerance. Neither field may ever be used as an
    inter-S matching criterion (matching.py, D022) -- a spectral window
    index is only ever meaningful within the single case that produced
    it."""

    status: str
    multiplicity: int
    twice_T: int | None
    spectral_window_group_index: int
    representative_energy: float

    def __post_init__(self) -> None:
        if self.status not in (COMPLETE_MULTIPLET, PARTIAL_SUBSPACE):
            raise ValueError(f"status must be one of ({COMPLETE_MULTIPLET!r}, {PARTIAL_SUBSPACE!r}), got {self.status!r}")
        if self.multiplicity <= 0:
            raise ValueError(f"multiplicity must be > 0, got {self.multiplicity}")
        if self.twice_T is not None and self.twice_T < 0:
            raise ValueError(f"twice_T must be >= 0 or None, got {self.twice_T}")
        if (
            isinstance(self.spectral_window_group_index, bool)
            or not isinstance(self.spectral_window_group_index, int)
            or self.spectral_window_group_index < 0
        ):
            raise ValueError(
                f"spectral_window_group_index must be a non-negative int, got {self.spectral_window_group_index!r}"
            )
        if isinstance(self.representative_energy, bool) or not isinstance(self.representative_energy, (int, float)):
            raise ValueError(f"representative_energy must be a real number, got {self.representative_energy!r}")
        if not math.isfinite(self.representative_energy):
            raise ValueError(f"representative_energy must be finite, got {self.representative_energy!r}")


def build_spectral_group_identity(
    group: SpectralLevelGroup,
    group_state: SpectralGroupState,
    *,
    spectral_window_group_index: int,
    twice_T: int | None,
) -> SpectralGroupIdentity:
    """The recommended way to construct a SpectralGroupIdentity. status/
    multiplicity/representative_energy are derived directly from `group`/
    `group_state` -- never recomputed, never rounded, never re-derived
    from individual eigenlevels or a fresh diagonalization.
    spectral_window_group_index and twice_T remain caller-supplied: the
    index must come from enumerating the case's own full, unfiltered
    `groups` sequence (cosmobox.level0.degeneracy.DegeneracyReport.groups,
    e.g. via `enumerate(groups)`) BEFORE any filtering -- never a rank
    reassigned after dropping some groups, never a target's rank in the
    manifest, never an inter-S matching criterion; twice_T comes from
    matching.compute_twice_T, already computed upstream.

    Cross-checks (defense in depth -- catches a caller passing a `group`/
    `group_state` pair that do not actually describe the same spectral
    group):
    - group_state.status == "partial_subspace" iff group.lower_bound_only
      is True;
    - group_state.multiplicity == group.multiplicity_observed;
    - group.end_index_exclusive - group.start_index ==
      group.multiplicity_observed (SpectralLevelGroup's own invariant,
      re-checked here rather than trusted blindly);
    - group_state.psi.shape[1] == group_state.multiplicity (SpectralGroupState's
      own invariant, re-checked here rather than trusted blindly).
    """
    if not isinstance(group, SpectralLevelGroup):
        raise ValueError(f"group must be a SpectralLevelGroup, got {type(group)}")
    if not isinstance(group_state, SpectralGroupState):
        raise ValueError(f"group_state must be a SpectralGroupState, got {type(group_state)}")

    is_partial = group_state.status == PARTIAL_SUBSPACE
    if is_partial != group.lower_bound_only:
        raise ValueError(
            f"group_state.status ({group_state.status!r}) does not match group.lower_bound_only "
            f"({group.lower_bound_only!r}) -- group and group_state do not describe the same spectral group"
        )
    if group_state.multiplicity != group.multiplicity_observed:
        raise ValueError(
            f"group_state.multiplicity ({group_state.multiplicity}) does not match "
            f"group.multiplicity_observed ({group.multiplicity_observed}) -- group and group_state do not "
            "describe the same spectral group"
        )
    if group.end_index_exclusive - group.start_index != group.multiplicity_observed:
        raise ValueError(
            f"group.end_index_exclusive - group.start_index ({group.end_index_exclusive - group.start_index}) "
            f"does not match group.multiplicity_observed ({group.multiplicity_observed})"
        )
    if group_state.psi.shape[1] != group_state.multiplicity:
        raise ValueError(
            f"group_state.psi.shape[1] ({group_state.psi.shape[1]}) does not match "
            f"group_state.multiplicity ({group_state.multiplicity})"
        )

    return SpectralGroupIdentity(
        status=group_state.status,
        multiplicity=group_state.multiplicity,
        twice_T=twice_T,
        spectral_window_group_index=spectral_window_group_index,
        representative_energy=group.representative_energy,
    )


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
    this record, None when not applicable.

    scientific_seed/solver_seed/validation_rotation_seed record the
    per-case seeds actually used to produce this result (Level1B lot
    1B-8, docs/decisions/decisions.md). scientific_seed and solver_seed
    are the two seeds every campaign execution derives per case (see
    experiments/level1/planning.py's derive_case_seed) and are always
    non-negative ints here; validation_rotation_seed is a non-negative
    int only when a randomized validation step was actually replayed to
    produce this record, None otherwise -- never a placeholder value."""

    spectral_status: str
    source_type: str
    source_module: str
    match_status: str | None
    covariance_validated: bool | None
    scientific_seed: int
    solver_seed: int
    validation_rotation_seed: int | None

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
        for name, value in (("scientific_seed", self.scientific_seed), ("solver_seed", self.solver_seed)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if self.validation_rotation_seed is not None and (
            isinstance(self.validation_rotation_seed, bool)
            or not isinstance(self.validation_rotation_seed, int)
            or self.validation_rotation_seed < 0
        ):
            raise ValueError(
                f"validation_rotation_seed must be None or a non-negative int, "
                f"got {self.validation_rotation_seed!r}"
            )


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


def _payload_spectral_status(payload: object) -> str | None:
    """The spectral status embedded in `payload` itself, if any -- None
    for payload types that carry no status of their own (a bare float/
    complex/tuple, a SymmetryLabel, a MatchOutcome with no matched_group).
    Used to cross-check every payload-embedded status against
    identity.spectral_group.status, so a mismatched status can never
    slip through silently."""
    if isinstance(payload, (FlavorCorrelatorMatrix, HermitianRestrictedDiagnostics, NonHermitianRestrictedDiagnostics)):
        return payload.status
    if isinstance(payload, OrbitResultPayload):
        return payload.comparability_key.status
    if isinstance(payload, MatchOutcome) and payload.matched_group is not None:
        return payload.matched_group.status
    return None


def _derive_source(payload: object) -> tuple[str, str]:
    """source_type/source_module are ALWAYS derived from type(payload)
    itself -- Python's own type system, not a hand-maintained table that
    could silently drift out of sync as new observable_kinds are added.
    This is the strongest available guarantee that provenance cannot lie
    about a payload's origin: for a bare float/complex/tuple payload,
    source_module is honestly "builtins" (Python's built-in numeric types
    carry no richer origin tag) -- a deliberately modest but truthful
    value, not an invented one."""
    return type(payload).__name__, type(payload).__module__


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

        # Provenance must be derived, never freely supplied: source_type/
        # source_module are checked against type(payload) itself (the one
        # value a caller cannot lie about), and spectral_status against
        # identity.spectral_group.status -- even a direct ResultRecord(...)
        # construction cannot claim a payload came from a different
        # type/module, or that the group's status was something else.
        expected_source_type, expected_source_module = _derive_source(self.payload)
        if self.provenance.source_type != expected_source_type:
            raise ValueError(
                f"provenance.source_type ({self.provenance.source_type!r}) does not match type(payload).__name__ "
                f"({expected_source_type!r}) -- provenance must be derived, never freely supplied"
            )
        if self.provenance.source_module != expected_source_module:
            raise ValueError(
                f"provenance.source_module ({self.provenance.source_module!r}) does not match "
                f"type(payload).__module__ ({expected_source_module!r}) -- provenance must be derived, "
                "never freely supplied"
            )
        if self.provenance.spectral_status != self.identity.spectral_group.status:
            raise ValueError(
                f"provenance.spectral_status ({self.provenance.spectral_status!r}) does not match "
                f"identity.spectral_group.status ({self.identity.spectral_group.status!r})"
            )

        # Every payload type that carries its own spectral status must
        # agree with identity.spectral_group.status -- never two
        # different, silently-diverging opinions about the same group.
        payload_status = _payload_spectral_status(self.payload)
        if payload_status is not None and payload_status != self.identity.spectral_group.status:
            raise ValueError(
                f"payload's own spectral status ({payload_status!r}) does not match "
                f"identity.spectral_group.status ({self.identity.spectral_group.status!r})"
            )

        # Cross-object guard rail: a RobustnessResult's own __post_init__
        # cannot see the group's status (it is a separate object), so a
        # definitive verdict attached to a partial_subspace identity would
        # otherwise slip through undetected -- this is exactly the
        # "aucun verdict definitif pour partial_subspace" contract,
        # enforced here where both objects are visible together.
        if self.record_kind == "robustness" and self.identity.spectral_group.status == PARTIAL_SUBSPACE:
            if self.payload.verdict != INDETERMINATE:
                raise ValueError(
                    "a robustness record whose spectral_group.status is 'partial_subspace' must carry an "
                    f"'indeterminate' verdict, got {self.payload.verdict!r}"
                )

        # A "matching" record with status == exact_label_match may never
        # carry a partial_subspace matched_group, even if MatchOutcome
        # itself would structurally allow constructing one by hand
        # (matching.py's own type does not know this semantic rule) --
        # truncation can never be promoted to a normative exact match.
        if self.record_kind == "matching" and self.payload.status == EXACT_LABEL_MATCH:
            if self.payload.matched_group.status != COMPLETE_MULTIPLET:
                raise ValueError(
                    "a 'matching' record with status='exact_label_match' must have "
                    f"matched_group.status == {COMPLETE_MULTIPLET!r}, got {self.payload.matched_group.status!r} "
                    "-- a partial_subspace group can never produce a normative exact match"
                )

        # Orbit-specific cross-checks between the payload's own
        # comparability_key and the record's identity/observable_kind.
        # hamiltonian_identity is deliberately NOT cross-checked: it is an
        # arbitrary caller-supplied Hashable (matching.py/orbits.py) with
        # no canonical format shared with identity.hamiltonian
        # (a structured HamiltonianIdentity) today -- this specific
        # cross-check is not performed and not guaranteed by this lot.
        if self.record_kind == "orbit_statistic":
            key = self.payload.comparability_key
            if key.observable_kind != self.observable_kind:
                raise ValueError(
                    f"payload.comparability_key.observable_kind ({key.observable_kind!r}) does not match "
                    f"the record's own observable_kind ({self.observable_kind!r})"
                )
            if key.normalization != self.identity.normalization:
                raise ValueError(
                    f"payload.comparability_key.normalization ({key.normalization!r}) does not match "
                    f"identity.normalization ({self.identity.normalization!r})"
                )
            if key.flavor_component != self.identity.flavor_component:
                raise ValueError(
                    f"payload.comparability_key.flavor_component ({key.flavor_component!r}) does not match "
                    f"identity.flavor_component ({self.identity.flavor_component!r})"
                )


def build_result_record(
    identity: ScientificIdentity,
    record_kind: str,
    observable_kind: str,
    payload: object,
    *,
    scientific_seed: int,
    solver_seed: int,
    validation_rotation_seed: int | None = None,
    match_status: str | None = None,
    covariance_validated: bool | None = None,
) -> ResultRecord:
    """The recommended way to construct a ResultRecord. source_type/
    source_module are derived mechanically from type(payload), and
    spectral_status is derived from identity.spectral_group.status --
    only match_status, covariance_validated, and the three seed fields
    remain caller-supplied, because they are genuinely external facts
    already established upstream (by matching.match_spectral_group /
    orbits.validate_orbit_covariance / the campaign's own per-case seed
    derivation, experiments/level1/planning.py's derive_case_seed), not
    something derivable from payload/identity alone. Direct
    ResultRecord(...) construction remains possible (results.py's public
    types are all directly constructible, matching the project's
    established pattern), but its own __post_init__ independently
    re-derives and checks source_type/source_module/spectral_status, so
    it cannot be used to smuggle a lying provenance past this factory.
    """
    source_type, source_module = _derive_source(payload)
    provenance = Provenance(
        spectral_status=identity.spectral_group.status,
        source_type=source_type,
        source_module=source_module,
        match_status=match_status,
        covariance_validated=covariance_validated,
        scientific_seed=scientific_seed,
        solver_seed=solver_seed,
        validation_rotation_seed=validation_rotation_seed,
    )
    return ResultRecord(
        identity=identity, provenance=provenance, record_kind=record_kind, observable_kind=observable_kind, payload=payload
    )
