"""Machine-readable Level1B preregistered campaign manifest. Level1B lot
1B-8 (docs/decisions/decisions.md D019-adjacent operational decision).

experiments/level1/preregistered-manifest-v1.json is the normative
machine-readable transcription of the campaign. experiments/level1/
preregistered-manifest.md is a human-readable explanatory document only
-- it is never itself loaded, validated, or executed against. Any
divergence between the two blocks execution: the JSON is what this
module loads and exposes as frozen typed objects, and any ambiguity
discovered while transcribing it from the Markdown is documented in the
accompanying delivery report, not silently resolved here.

This module performs no scientific computation: it loads, validates
(Draft 2020-12, schemas/level1/preregistered-manifest-v1.schema.json),
computes manifest_fingerprint, and exposes typed, frozen views. It never
decides a target group, a seed, or a resource guardrail outcome -- those
live in planning.py/target_selection.py, which consume this module's
output.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

_MANIFEST_PATH = Path(__file__).resolve().parent / "preregistered-manifest-v1.json"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1" / "preregistered-manifest-v1.schema.json"

GEOMETRIES = ("triangle", "ring4", "ring5")

FUNDAMENTAL = "fundamental"
FIRST_EXCITED = "first_excited"
FLAVOR_LABEL = "flavor_label"
STRUCTURALLY_NOT_APPLICABLE = "structurally_not_applicable"
SELECTION_KINDS = (FUNDAMENTAL, FIRST_EXCITED, FLAVOR_LABEL, STRUCTURALLY_NOT_APPLICABLE)

LOWEST_REPRESENTATIVE_ENERGY = "lowest_representative_energy"

COMPLETE_MULTIPLET = "complete_multiplet"
PARTIAL_SUBSPACE = "partial_subspace"

ALL_ORDERED_DISTINCT_PAIRS = "all_ordered_distinct_pairs"
ALL_MINIMAL_PATHS = "all_minimal_paths"

_INTER_S_SECONDARY_OBSERVABLES = ("G_occ", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio", "path_phase_coherence")
_INTER_S_UNPRODUCED_OBSERVABLES = ("G_occ", "path_phase_coherence")
_ORBIT_STATISTICS_FIELDS = ("orbit_mean", "orbit_max_pairwise_spread", "orbit_covariance_defect")

# The single-case/inter-S normative policy transcribed from
# experiments/level1/preregistered-manifest.md's "Groupes spectraux
# ciblés" section: every category except structurally_not_applicable
# requires a complete_multiplet group; only first_excited additionally
# requires matching.EXACT_LABEL_MATCH at the (out-of-scope-here) inter-S
# step -- never claimed by a single-case selection.
_REQUIRED_SPECTRAL_STATUS_BY_SELECTION_KIND = {
    FUNDAMENTAL: COMPLETE_MULTIPLET,
    FIRST_EXCITED: COMPLETE_MULTIPLET,
    FLAVOR_LABEL: COMPLETE_MULTIPLET,
    STRUCTURALLY_NOT_APPLICABLE: None,
}
_REQUIRES_INTER_S_EXACT_MATCH_BY_SELECTION_KIND = {
    FUNDAMENTAL: False,
    FIRST_EXCITED: True,
    FLAVOR_LABEL: False,
    STRUCTURALLY_NOT_APPLICABLE: False,
}


def _validate_finite_real(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


@dataclass(frozen=True, slots=True)
class HamiltonianCaseSpec:
    """Public type, directly constructible: __post_init__ enforces the
    same invariants as preregistered-manifest-v1.schema.json's
    hamiltonianCase $def, independently of whether load_manifest_json's
    schema check already ran -- a caller building one by hand cannot
    smuggle a non-finite parameter or an out-of-shape J_override past it.
    """

    hamiltonian_case_id: str
    J_uniform: float
    J_override: tuple[int, float] | None
    h_is_zero: bool
    t: float
    g_E: float
    K: float

    def __post_init__(self) -> None:
        if not self.hamiltonian_case_id:
            raise ValueError("hamiltonian_case_id must be non-empty")
        _validate_finite_real(self.J_uniform, "J_uniform")
        if self.J_override is not None:
            node_index, value = self.J_override
            if isinstance(node_index, bool) or not isinstance(node_index, int) or node_index < 0:
                raise ValueError(f"J_override node_index must be a non-negative int, got {node_index!r}")
            _validate_finite_real(value, "J_override value")
        if self.h_is_zero is not True:
            raise ValueError(f"h_is_zero must be True (the only value the manifest schema admits), got {self.h_is_zero!r}")
        _validate_finite_real(self.t, "t")
        _validate_finite_real(self.g_E, "g_E")
        _validate_finite_real(self.K, "K")


@dataclass(frozen=True, slots=True)
class GridPointSpec:
    geometry: str
    spin: int
    physical_dimension: int
    spectral_window: int
    hamiltonian_case_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        for name, value in (
            ("spin", self.spin),
            ("physical_dimension", self.physical_dimension),
            ("spectral_window", self.spectral_window),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be an int >= 1, got {value!r}")
        if not self.hamiltonian_case_ids:
            raise ValueError("hamiltonian_case_ids must be non-empty")
        if len(self.hamiltonian_case_ids) != len(set(self.hamiltonian_case_ids)):
            raise ValueError(f"hamiltonian_case_ids must be unique, got {self.hamiltonian_case_ids}")


@dataclass(frozen=True, slots=True)
class TargetGroupSpec:
    """selection_kind==flavor_label requires target_twice_T (a
    non-negative int) and selection_within_label=="lowest_representative_
    energy"; selection_kind in (fundamental, first_excited) requires both
    None -- exactly preregistered-manifest-v1.schema.json's targetGroup
    if/then, re-checked here so this type is safe to construct directly.

    required_spectral_status and requires_inter_s_exact_match encode the
    normative policy transcribed from the human manifest's own "Groupes
    spectraux ciblés" section (complete_multiplet for every category
    except structurally_not_applicable; the inter-S exact-match
    requirement only for first_excited) -- both cross-checked here
    against selection_kind, exactly like target_twice_T/
    selection_within_label above, never left to whoever authored the
    manifest JSON to get right unchecked."""

    target_id: str
    selection_kind: str
    target_twice_T: int | None
    selection_within_label: str | None
    required_spectral_status: str | None
    requires_inter_s_exact_match: bool

    def __post_init__(self) -> None:
        if not self.target_id:
            raise ValueError("target_id must be non-empty")
        if self.selection_kind not in SELECTION_KINDS:
            raise ValueError(f"selection_kind must be one of {SELECTION_KINDS}, got {self.selection_kind!r}")
        if self.selection_within_label is not None and self.selection_within_label != LOWEST_REPRESENTATIVE_ENERGY:
            raise ValueError(
                f"selection_within_label must be None or {LOWEST_REPRESENTATIVE_ENERGY!r}, "
                f"got {self.selection_within_label!r}"
            )
        if self.target_twice_T is not None and (
            isinstance(self.target_twice_T, bool) or not isinstance(self.target_twice_T, int) or self.target_twice_T < 0
        ):
            raise ValueError(f"target_twice_T must be None or a non-negative int, got {self.target_twice_T!r}")
        if self.selection_kind == FLAVOR_LABEL:
            if self.target_twice_T is None or self.selection_within_label != LOWEST_REPRESENTATIVE_ENERGY:
                raise ValueError(
                    "selection_kind=='flavor_label' requires target_twice_T set and "
                    f"selection_within_label=={LOWEST_REPRESENTATIVE_ENERGY!r}"
                )
        elif self.selection_kind in (FUNDAMENTAL, FIRST_EXCITED):
            if self.target_twice_T is not None or self.selection_within_label is not None:
                raise ValueError(
                    f"selection_kind=={self.selection_kind!r} requires target_twice_T and "
                    "selection_within_label to both be None"
                )

        if self.required_spectral_status is not None and self.required_spectral_status != COMPLETE_MULTIPLET:
            raise ValueError(
                f"required_spectral_status must be None or {COMPLETE_MULTIPLET!r}, got {self.required_spectral_status!r}"
            )
        if not isinstance(self.requires_inter_s_exact_match, bool):
            raise ValueError(
                f"requires_inter_s_exact_match must be a bool, got {type(self.requires_inter_s_exact_match)}"
            )
        expected_required_status = _REQUIRED_SPECTRAL_STATUS_BY_SELECTION_KIND[self.selection_kind]
        if self.required_spectral_status != expected_required_status:
            raise ValueError(
                f"selection_kind=={self.selection_kind!r} requires required_spectral_status=={expected_required_status!r}, "
                f"got {self.required_spectral_status!r}"
            )
        expected_exact_match = _REQUIRES_INTER_S_EXACT_MATCH_BY_SELECTION_KIND[self.selection_kind]
        if self.requires_inter_s_exact_match != expected_exact_match:
            raise ValueError(
                f"selection_kind=={self.selection_kind!r} requires requires_inter_s_exact_match=={expected_exact_match!r}, "
                f"got {self.requires_inter_s_exact_match!r}"
            )


@dataclass(frozen=True, slots=True)
class RobustnessSpec:
    primary: str
    secondary: tuple[str, ...]
    absolute_tolerance: float
    relative_tolerance: float
    normalization_floor: float

    def __post_init__(self) -> None:
        if not self.primary:
            raise ValueError("primary must be non-empty")
        if len(self.secondary) != len(set(self.secondary)):
            raise ValueError(f"secondary must be unique, got {self.secondary}")
        for name, value in (
            ("absolute_tolerance", self.absolute_tolerance),
            ("relative_tolerance", self.relative_tolerance),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not (math.isfinite(value) and value >= 0):
                raise ValueError(f"{name} must be a finite number >= 0, got {value!r}")
        if (
            isinstance(self.normalization_floor, bool)
            or not isinstance(self.normalization_floor, (int, float))
            or not (math.isfinite(self.normalization_floor) and self.normalization_floor > 0)
        ):
            raise ValueError(f"normalization_floor must be a finite number > 0, got {self.normalization_floor!r}")


@dataclass(frozen=True, slots=True)
class InterSObservablesSpec:
    """gamma_O and its comparison partners are inherently inter-S (they
    compare two diagonalized cases at different spin), never a single-case
    quantity -- kept structurally separate from ProductionsSpec's other
    three fields, which are all single-case. `unproduced` names inter-S
    observables that are pre-registered (frozen by D013/D018) but have no
    physical producer implemented anywhere yet (G_occ, path_phase_coherence)
    -- a single-case runner must never claim to compute them."""

    primary: str
    secondary: tuple[str, ...]
    robustness_verdicts_included: bool
    unproduced: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.primary != "gamma_O":
            raise ValueError(f"primary must be 'gamma_O', got {self.primary!r}")
        if len(self.secondary) != len(set(self.secondary)):
            raise ValueError(f"secondary must be unique, got {self.secondary}")
        unknown_secondary = [name for name in self.secondary if name not in _INTER_S_SECONDARY_OBSERVABLES]
        if unknown_secondary:
            raise ValueError(f"secondary contains unknown observable(s) {unknown_secondary}")
        if self.robustness_verdicts_included is not True:
            raise ValueError(f"robustness_verdicts_included must be True, got {self.robustness_verdicts_included!r}")
        if len(self.unproduced) != len(set(self.unproduced)):
            raise ValueError(f"unproduced must be unique, got {self.unproduced}")
        unknown_unproduced = [name for name in self.unproduced if name not in _INTER_S_UNPRODUCED_OBSERVABLES]
        if unknown_unproduced:
            raise ValueError(f"unproduced contains unknown observable(s) {unknown_unproduced}")


@dataclass(frozen=True, slots=True)
class ProductionsSpec:
    """The taxonomy of what the campaign produces, structured by kind --
    replaces a single flat observable-name list, which conflated
    single-case quantities with the inherently inter-S gamma_O and
    silently omitted path/orbit statistics that the human manifest also
    requires."""

    single_case_observables: tuple[str, ...]
    single_case_diagnostics: tuple[str, ...]
    path_statistics: tuple[str, ...]
    orbit_statistics: tuple[str, ...]
    inter_s_observables: InterSObservablesSpec

    def __post_init__(self) -> None:
        for name, values in (
            ("single_case_observables", self.single_case_observables),
            ("single_case_diagnostics", self.single_case_diagnostics),
        ):
            if not values:
                raise ValueError(f"{name} must be non-empty")
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must be unique, got {values}")
        # path_statistics is currently always empty: path_selection ==
        # "all_minimal_paths" keeps every individual per-path value, and
        # no aggregate path statistic is frozen yet -- never populated
        # with an invented quantity (the human manifest never
        # pre-registered one).
        if len(self.path_statistics) != len(set(self.path_statistics)):
            raise ValueError(f"path_statistics must be unique, got {self.path_statistics}")
        if set(self.orbit_statistics) != set(_ORBIT_STATISTICS_FIELDS) or len(self.orbit_statistics) != len(
            _ORBIT_STATISTICS_FIELDS
        ):
            raise ValueError(f"orbit_statistics must be exactly {_ORBIT_STATISTICS_FIELDS}, got {self.orbit_statistics}")
        if not isinstance(self.inter_s_observables, InterSObservablesSpec):
            raise ValueError(f"inter_s_observables must be an InterSObservablesSpec, got {type(self.inter_s_observables)}")


@dataclass(frozen=True, slots=True)
class ResourceGuardrailsSpec:
    max_dense_dimension: int
    max_sparse_dimension: int

    def __post_init__(self) -> None:
        for name, value in (
            ("max_dense_dimension", self.max_dense_dimension),
            ("max_sparse_dimension", self.max_sparse_dimension),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if self.max_dense_dimension > self.max_sparse_dimension:
            raise ValueError(
                f"max_dense_dimension ({self.max_dense_dimension}) must be <= "
                f"max_sparse_dimension ({self.max_sparse_dimension})"
            )


@dataclass(frozen=True, slots=True)
class Manifest:
    """The typed, frozen view of the machine-readable manifest.
    `fingerprint` is computed by parse_manifest from exactly the same
    `raw` dict carried alongside it -- never recomputed differently
    elsewhere, so the two can never silently diverge."""

    manifest_version: str
    campaign_id: str
    schema_version: str
    branch: str
    n_flavors: int
    external_charges_all_zero: bool
    scientific_seed: int
    hamiltonian_cases: tuple[HamiltonianCaseSpec, ...]
    grid: tuple[GridPointSpec, ...]
    sectors: tuple[str, ...]
    target_groups: dict[str, tuple[TargetGroupSpec, ...]]
    productions: ProductionsSpec
    robustness: RobustnessSpec
    resource_guardrails: ResourceGuardrailsSpec
    degeneracy_tolerance: float
    pair_selection: str
    path_selection: str
    fingerprint: str
    raw: dict

    def __post_init__(self) -> None:
        if self.manifest_version != "level1b-reference-v1":
            raise ValueError(f"manifest_version must be 'level1b-reference-v1', got {self.manifest_version!r}")
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if self.schema_version != "level1-correlators-v2":
            raise ValueError(f"schema_version must be 'level1-correlators-v2', got {self.schema_version!r}")
        if not self.branch:
            raise ValueError("branch must be non-empty")
        if self.n_flavors != 2:
            raise ValueError(f"n_flavors must be 2, got {self.n_flavors!r}")
        if self.external_charges_all_zero is not True:
            raise ValueError(f"external_charges_all_zero must be True, got {self.external_charges_all_zero!r}")
        if isinstance(self.scientific_seed, bool) or not isinstance(self.scientific_seed, int) or self.scientific_seed < 0:
            raise ValueError(f"scientific_seed must be a non-negative int, got {self.scientific_seed!r}")
        if not self.hamiltonian_cases:
            raise ValueError("hamiltonian_cases must be non-empty")
        hamiltonian_case_ids = {case.hamiltonian_case_id for case in self.hamiltonian_cases}
        if len(hamiltonian_case_ids) != len(self.hamiltonian_cases):
            raise ValueError("hamiltonian_cases must have unique hamiltonian_case_id values")
        if not self.grid:
            raise ValueError("grid must be non-empty")
        for grid_point in self.grid:
            unknown_ids = [
                case_id for case_id in grid_point.hamiltonian_case_ids if case_id not in hamiltonian_case_ids
            ]
            if unknown_ids:
                raise ValueError(
                    f"grid point ({grid_point.geometry!r}, spin={grid_point.spin}) references unknown "
                    f"hamiltonian_case_id(s) {unknown_ids}; known ids are {sorted(hamiltonian_case_ids)}"
                )
        if not self.sectors:
            raise ValueError("sectors must be non-empty")
        if len(self.sectors) != len(set(self.sectors)):
            raise ValueError(f"sectors must be unique, got {self.sectors}")
        geometries_in_grid = {grid_point.geometry for grid_point in self.grid}
        missing_target_groups = geometries_in_grid - self.target_groups.keys()
        if missing_target_groups:
            raise ValueError(f"target_groups is missing entries for geometries {sorted(missing_target_groups)}")
        for geometry, groups in self.target_groups.items():
            if geometry not in GEOMETRIES:
                raise ValueError(f"target_groups key {geometry!r} is not a known geometry {GEOMETRIES}")
            if not groups:
                raise ValueError(f"target_groups[{geometry!r}] must be non-empty")
            target_ids = [group.target_id for group in groups]
            if len(target_ids) != len(set(target_ids)):
                raise ValueError(f"target_groups[{geometry!r}] has duplicate target_id(s): {target_ids}")
        if not isinstance(self.productions, ProductionsSpec):
            raise ValueError(f"productions must be a ProductionsSpec, got {type(self.productions)}")
        if (
            isinstance(self.degeneracy_tolerance, bool)
            or not isinstance(self.degeneracy_tolerance, (int, float))
            or not (math.isfinite(self.degeneracy_tolerance) and self.degeneracy_tolerance > 0)
        ):
            raise ValueError(f"degeneracy_tolerance must be a finite number > 0, got {self.degeneracy_tolerance!r}")
        if self.pair_selection != ALL_ORDERED_DISTINCT_PAIRS:
            raise ValueError(f"pair_selection must be {ALL_ORDERED_DISTINCT_PAIRS!r}, got {self.pair_selection!r}")
        if self.path_selection != ALL_MINIMAL_PATHS:
            raise ValueError(f"path_selection must be {ALL_MINIMAL_PATHS!r}, got {self.path_selection!r}")


def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def load_manifest_json(path: Path = _MANIFEST_PATH) -> dict:
    """Load and validate the raw manifest JSON against its Draft 2020-12
    schema. Raises ValueError (never a bare jsonschema exception) listing
    every violation, not just the first."""
    with Path(path).open() as handle:
        raw = json.load(handle)
    errors = sorted(_validator().iter_errors(raw), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"manifest does not validate against its schema: {messages}")
    return raw


def compute_manifest_fingerprint(raw: dict) -> str:
    """SHA-256 of the canonical (sorted-key, compact-separator) JSON
    serialization of the already-validated manifest dict. Every field in
    `raw` can affect a scientific result or the decision to execute a
    case (grid, Hamiltonians, targets, observables, thresholds, seeds
    policy, guardrails, schema version) -- there is deliberately no
    operational-only field (output directory, parallelism, logging,
    dates) anywhere in the manifest JSON to exclude, so the entire
    validated dict is fingerprinted directly. sort_keys+compact
    separators make the result insensitive to key order and whitespace
    by construction; since the manifest is JSON, not a text file with
    comments, there is nothing else to strip.
    """
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_hamiltonian_case(entry: dict) -> HamiltonianCaseSpec:
    override = entry["J_override"]
    return HamiltonianCaseSpec(
        hamiltonian_case_id=entry["hamiltonian_case_id"],
        J_uniform=entry["J_uniform"],
        J_override=(override["node_index"], override["value"]) if override is not None else None,
        h_is_zero=entry["h_is_zero"],
        t=entry["t"],
        g_E=entry["g_E"],
        K=entry["K"],
    )


def _parse_grid_point(entry: dict) -> GridPointSpec:
    return GridPointSpec(
        geometry=entry["geometry"],
        spin=entry["spin"],
        physical_dimension=entry["physical_dimension"],
        spectral_window=entry["spectral_window"],
        hamiltonian_case_ids=tuple(entry["hamiltonian_case_ids"]),
    )


def _parse_target_group(entry: dict) -> TargetGroupSpec:
    return TargetGroupSpec(
        target_id=entry["target_id"],
        selection_kind=entry["selection_kind"],
        target_twice_T=entry["target_twice_T"],
        selection_within_label=entry["selection_within_label"],
        required_spectral_status=entry["required_spectral_status"],
        requires_inter_s_exact_match=entry["requires_inter_s_exact_match"],
    )


def _parse_inter_s_observables(entry: dict) -> InterSObservablesSpec:
    return InterSObservablesSpec(
        primary=entry["primary"],
        secondary=tuple(entry["secondary"]),
        robustness_verdicts_included=entry["robustness_verdicts_included"],
        unproduced=tuple(entry["unproduced"]),
    )


def _parse_productions(entry: dict) -> ProductionsSpec:
    return ProductionsSpec(
        single_case_observables=tuple(entry["single_case_observables"]),
        single_case_diagnostics=tuple(entry["single_case_diagnostics"]),
        path_statistics=tuple(entry["path_statistics"]),
        orbit_statistics=tuple(entry["orbit_statistics"]),
        inter_s_observables=_parse_inter_s_observables(entry["inter_s_observables"]),
    )


def parse_manifest(raw: dict) -> Manifest:
    """Build the typed, frozen view from an already-schema-validated raw
    dict (load_manifest_json's job, not repeated here) -- pure
    transcription into typed objects, plus the fingerprint of `raw`
    itself."""
    return Manifest(
        manifest_version=raw["manifest_version"],
        campaign_id=raw["campaign_id"],
        schema_version=raw["schema_version"],
        branch=raw["branch"],
        n_flavors=raw["n_flavors"],
        external_charges_all_zero=raw["external_charges_all_zero"],
        scientific_seed=raw["scientific_seed"],
        hamiltonian_cases=tuple(_parse_hamiltonian_case(entry) for entry in raw["hamiltonian_cases"]),
        grid=tuple(_parse_grid_point(entry) for entry in raw["grid"]),
        sectors=tuple(raw["sectors"]),
        target_groups={
            geometry: tuple(_parse_target_group(entry) for entry in entries)
            for geometry, entries in raw["target_groups"].items()
        },
        productions=_parse_productions(raw["productions"]),
        robustness=RobustnessSpec(
            primary=raw["robustness"]["primary"],
            secondary=tuple(raw["robustness"]["secondary"]),
            absolute_tolerance=raw["robustness"]["absolute_tolerance"],
            relative_tolerance=raw["robustness"]["relative_tolerance"],
            normalization_floor=raw["robustness"]["normalization_floor"],
        ),
        resource_guardrails=ResourceGuardrailsSpec(
            max_dense_dimension=raw["resource_guardrails"]["max_dense_dimension"],
            max_sparse_dimension=raw["resource_guardrails"]["max_sparse_dimension"],
        ),
        degeneracy_tolerance=raw["degeneracy_tolerance"],
        pair_selection=raw["pair_selection"],
        path_selection=raw["path_selection"],
        fingerprint=compute_manifest_fingerprint(raw),
        raw=raw,
    )


def load_manifest(path: Path = _MANIFEST_PATH) -> Manifest:
    """The single entry point: load, validate, fingerprint, and parse."""
    raw = load_manifest_json(path)
    return parse_manifest(raw)
