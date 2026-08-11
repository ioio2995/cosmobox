"""Machine-readable Level1C normative campaign manifest. Lot 1C-8b.

experiments/level1c/preregistered-manifest-v1.json is the normative
machine-readable transcription of the frozen J0 x S response campaign
contract (docs/levels/level1c/identifiability-preregistration.md
sections 15-20, especially 20.3/20.4/20.8/20.22-20.31). This module
performs no scientific computation: it loads, validates (Draft 2020-12,
schemas/level1c/campaign-manifest-v1.schema.json), computes
manifest_fingerprint, and exposes typed, frozen views.

experiments/level1/manifest.py (Level1B, D019-adjacent) is reused by
composition wherever its dataclasses carry no Level1B-only semantics
(HamiltonianCaseSpec, GridPointSpec, TargetGroupSpec,
ResourceGuardrailsSpec, compute_manifest_fingerprint) -- it is never
imported for its own Manifest class (which hardcodes
manifest_version=="level1b-reference-v1"/schema_version==
"level1-correlators-v2" in __post_init__, and would reject any other
manifest) and is never modified by this module.

TargetRole is the one genuinely new concept this module introduces:
Level1B's TargetGroupSpec has no notion of whether a target blocks
campaign_status on failure -- that never mattered for Level1B's single,
flat REQUIRED_NON_REGRESSION contract. Level1C's T_max is
CALIBRATION_ONLY (never blocking) while remaining
required_spectral_status=complete_multiplet if it is ever selected --
role and required_spectral_status are orthogonal, never one inferred
from the other (1C-8a-fix, accepted).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.level1.manifest import (
    GridPointSpec,
    HamiltonianCaseSpec,
    ResourceGuardrailsSpec,
    TargetGroupSpec,
    compute_manifest_fingerprint,
)

_MANIFEST_PATH = Path(__file__).resolve().parent / "preregistered-manifest-v1.json"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level1c" / "campaign-manifest-v1.schema.json"

GEOMETRIES = ("triangle", "ring5")
"""Level1C's normative geometry set (1C-8a section 6) -- deliberately
excludes ring4 (never part of the frozen J0 x S grid, section 20.3)."""

SPIN_VALUES = (2, 3)
"""Level1C's normative spin set (S=1 excluded by design, section 16.5)."""

J0_GRID = (0.5, 0.75, 1.0, 1.25, 1.5)
"""The frozen J0 grid (delta=0.25, section 17.1), symmetric around the
J0=1 calibration baseline."""

J0_BASELINE = 1.0

REQUIRED = "REQUIRED"
CALIBRATION_ONLY = "CALIBRATION_ONLY"
TARGET_ROLES = (REQUIRED, CALIBRATION_ONLY)
"""TargetRole (1C-8a-fix, accepted): whether a target's absence/
non-conformity blocks campaign_status. Orthogonal to
TargetGroupSpec.required_spectral_status -- never inferred from it."""

NON_REGRESSION_CALIBRATION_CONTRACT_VERSION = "level1c-nonregression-calibration-v2"

CALIBRATION_ARTIFACT_SHA256 = "05aa2e9d77c1314926350f8202e620b7537bdf9f6a7bab12a232151e9cf68da6"
"""The single accepted calibration artifact (1C-7c4/1C-7c5, CLOSED_ACCEPTED).
Referenced by identity only -- the artifact itself is never copied into
this manifest."""

CALIBRATION_CODE_COMMIT = "1f06ef91c1157389df7d325cb825ce7508eff52f"

NON_REGRESSION_CTT_ABS_TOL = 1e-15
NON_REGRESSION_RHO_ABS_TOL = 1e-15

MANIFEST_VERSION = "level1c-campaign-manifest-v1"
CAMPAIGN_ID = "level1c-j0-response-v1"
SCHEMA_VERSION = "level1c-result-record-v1"

# production_window(geometry, J0), frozen by the accepted preflight result
# (identifiability-preregistration.md section 19.8) -- an INPUT the
# manifest carries, never recomputed or rederived by this module or any
# future campaign runner (section 20.4).
FROZEN_PRODUCTION_WINDOWS = {
    ("triangle", 0.5): 5,
    ("triangle", 0.75): 5,
    ("triangle", 1.0): 9,
    ("triangle", 1.25): 5,
    ("triangle", 1.5): 5,
    ("ring5", 0.5): 11,
    ("ring5", 0.75): 11,
    ("ring5", 1.0): 15,
    ("ring5", 1.25): 11,
    ("ring5", 1.5): 11,
}

FROZEN_PHYSICAL_DIMENSIONS = {
    ("triangle", 2): 88,
    ("triangle", 3): 128,
    ("ring5", 2): 1000,
    ("ring5", 3): 1504,
}


def _validate_finite_real(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


def hamiltonian_case_id_for_j0(j0: float) -> str:
    """The deterministic hamiltonian_case_id naming convention for this
    campaign: 'j0-<value formatted to 2 decimals>', e.g. 'j0-0.50',
    'j0-1.00', 'j0-1.50'. A pure string convention, never re-derived by
    parsing a case_id back into a float elsewhere in this package --
    every consumer that needs the J0 value keeps it as a separate field."""
    if j0 not in J0_GRID:
        raise ValueError(f"j0 must be one of {J0_GRID}, got {j0!r}")
    return f"j0-{j0:.2f}"


@dataclass(frozen=True, slots=True)
class Level1CTargetSpec:
    """A Level1B TargetGroupSpec (reused verbatim, never modified) paired
    with its Level1C-only normative role (1C-8a-fix). `target.
    required_spectral_status` still governs whether a *selected* group
    satisfies this target's spectral requirement; `role` governs only
    whether this target's absence/non-conformity blocks
    campaign_status. The two are never conflated: T_max keeps
    required_spectral_status=complete_multiplet while role=
    CALIBRATION_ONLY."""

    target: TargetGroupSpec
    role: str

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetGroupSpec):
            raise ValueError(f"target must be a TargetGroupSpec, got {type(self.target)}")
        if self.role not in TARGET_ROLES:
            raise ValueError(f"role must be one of {TARGET_ROLES}, got {self.role!r}")


@dataclass(frozen=True, slots=True)
class NonRegressionCalibrationSpec:
    """The frozen, closed calibration decision (1C-7c4/1C-7c5,
    CALIBRATION_RUN_STATUS=CLOSED_ACCEPTED) consumed as a constant --
    never recomputed, never re-derived, no automatic recalibration
    mechanism anywhere in this package."""

    calibration_artifact_sha256: str
    code_commit: str
    contract_version: str
    ctt_abs_tol: float
    rho_abs_tol: float

    def __post_init__(self) -> None:
        if self.calibration_artifact_sha256 != CALIBRATION_ARTIFACT_SHA256:
            raise ValueError(
                f"calibration_artifact_sha256 must be the single accepted artifact hash "
                f"{CALIBRATION_ARTIFACT_SHA256!r}, got {self.calibration_artifact_sha256!r}"
            )
        if self.code_commit != CALIBRATION_CODE_COMMIT:
            raise ValueError(f"code_commit must be {CALIBRATION_CODE_COMMIT!r}, got {self.code_commit!r}")
        if self.contract_version != NON_REGRESSION_CALIBRATION_CONTRACT_VERSION:
            raise ValueError(
                f"contract_version must be {NON_REGRESSION_CALIBRATION_CONTRACT_VERSION!r}, "
                f"got {self.contract_version!r}"
            )
        if self.ctt_abs_tol != NON_REGRESSION_CTT_ABS_TOL:
            raise ValueError(f"ctt_abs_tol must be {NON_REGRESSION_CTT_ABS_TOL!r}, got {self.ctt_abs_tol!r}")
        if self.rho_abs_tol != NON_REGRESSION_RHO_ABS_TOL:
            raise ValueError(f"rho_abs_tol must be {NON_REGRESSION_RHO_ABS_TOL!r}, got {self.rho_abs_tol!r}")


@dataclass(frozen=True, slots=True)
class Level1CManifest:
    """The typed, frozen view of the Level1C machine-readable manifest.
    Deliberately NOT a subclass or instance of experiments.level1.
    manifest.Manifest -- that class's own __post_init__ hardcodes
    Level1B's manifest_version/schema_version constants and would
    reject this manifest outright. Every reused field type
    (HamiltonianCaseSpec, GridPointSpec, TargetGroupSpec via
    Level1CTargetSpec, ResourceGuardrailsSpec) is imported unchanged
    from experiments.level1.manifest."""

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
    target_groups: dict[str, tuple[Level1CTargetSpec, ...]]
    resource_guardrails: ResourceGuardrailsSpec
    degeneracy_tolerance: float
    pair_selection: str
    path_selection: str
    non_regression_calibration: NonRegressionCalibrationSpec
    fingerprint: str
    raw: dict

    def __post_init__(self) -> None:
        if self.manifest_version != MANIFEST_VERSION:
            raise ValueError(f"manifest_version must be {MANIFEST_VERSION!r}, got {self.manifest_version!r}")
        if self.campaign_id != CAMPAIGN_ID:
            raise ValueError(f"campaign_id must be {CAMPAIGN_ID!r}, got {self.campaign_id!r}")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}, got {self.schema_version!r}")
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
        expected_case_ids = {hamiltonian_case_id_for_j0(j0) for j0 in J0_GRID}
        if hamiltonian_case_ids != expected_case_ids:
            raise ValueError(
                f"hamiltonian_cases must be exactly {sorted(expected_case_ids)}, got {sorted(hamiltonian_case_ids)}"
            )
        for case in self.hamiltonian_cases:
            if case.J_override is None or case.J_override[0] != 0:
                raise ValueError(
                    f"hamiltonian case {case.hamiltonian_case_id!r}: J_override must perturb node_index=0 "
                    f"(the single-site J0 probe, DB1), got {case.J_override!r}"
                )

        if not self.grid:
            raise ValueError("grid must be non-empty")
        if len(self.grid) != len(GEOMETRIES) * len(SPIN_VALUES) * len(J0_GRID):
            raise ValueError(
                f"grid must contain exactly {len(GEOMETRIES) * len(SPIN_VALUES) * len(J0_GRID)} points "
                f"(one per (geometry, spin, J0) triple), got {len(self.grid)}"
            )
        seen_triples: set[tuple[str, int, str]] = set()
        for grid_point in self.grid:
            if grid_point.geometry not in GEOMETRIES:
                raise ValueError(f"grid point geometry must be one of {GEOMETRIES}, got {grid_point.geometry!r}")
            if grid_point.spin not in SPIN_VALUES:
                raise ValueError(f"grid point spin must be one of {SPIN_VALUES}, got {grid_point.spin!r}")
            if len(grid_point.hamiltonian_case_ids) != 1:
                raise ValueError(
                    "each Level1C grid point must reference exactly one hamiltonian_case_id (one J0 per "
                    f"grid point, since production_window varies by J0 -- section 19.8), got "
                    f"{grid_point.hamiltonian_case_ids!r}"
                )
            case_id = grid_point.hamiltonian_case_ids[0]
            if case_id not in hamiltonian_case_ids:
                raise ValueError(f"grid point references unknown hamiltonian_case_id {case_id!r}")
            triple = (grid_point.geometry, grid_point.spin, case_id)
            if triple in seen_triples:
                raise ValueError(f"grid contains a duplicate (geometry, spin, hamiltonian_case_id) triple: {triple}")
            seen_triples.add(triple)
            expected_dimension = FROZEN_PHYSICAL_DIMENSIONS[(grid_point.geometry, grid_point.spin)]
            if grid_point.physical_dimension != expected_dimension:
                raise ValueError(
                    f"grid point ({grid_point.geometry!r}, S={grid_point.spin}) physical_dimension must be "
                    f"{expected_dimension}, got {grid_point.physical_dimension}"
                )

        if not self.sectors:
            raise ValueError("sectors must be non-empty")
        if tuple(self.sectors) != ("default",):
            raise ValueError(f"sectors must be exactly ('default',), got {tuple(self.sectors)}")

        geometries_in_grid = {grid_point.geometry for grid_point in self.grid}
        if geometries_in_grid != set(GEOMETRIES):
            raise ValueError(f"grid must cover exactly {GEOMETRIES}, got {sorted(geometries_in_grid)}")
        missing_target_groups = geometries_in_grid - self.target_groups.keys()
        if missing_target_groups:
            raise ValueError(f"target_groups is missing entries for geometries {sorted(missing_target_groups)}")
        for geometry, specs in self.target_groups.items():
            if geometry not in GEOMETRIES:
                raise ValueError(f"target_groups key {geometry!r} is not a known Level1C geometry {GEOMETRIES}")
            if not specs:
                raise ValueError(f"target_groups[{geometry!r}] must be non-empty")
            target_ids = [spec.target.target_id for spec in specs]
            if len(target_ids) != len(set(target_ids)):
                raise ValueError(f"target_groups[{geometry!r}] has duplicate target_id(s): {target_ids}")

        if not isinstance(self.resource_guardrails, ResourceGuardrailsSpec):
            raise ValueError(f"resource_guardrails must be a ResourceGuardrailsSpec, got {type(self.resource_guardrails)}")
        if (
            isinstance(self.degeneracy_tolerance, bool)
            or not isinstance(self.degeneracy_tolerance, (int, float))
            or not (math.isfinite(self.degeneracy_tolerance) and self.degeneracy_tolerance > 0)
        ):
            raise ValueError(f"degeneracy_tolerance must be a finite number > 0, got {self.degeneracy_tolerance!r}")
        if self.pair_selection != "all_ordered_distinct_pairs":
            raise ValueError(f"pair_selection must be 'all_ordered_distinct_pairs', got {self.pair_selection!r}")
        if self.path_selection != "all_minimal_paths":
            raise ValueError(f"path_selection must be 'all_minimal_paths', got {self.path_selection!r}")
        if not isinstance(self.non_regression_calibration, NonRegressionCalibrationSpec):
            raise ValueError(
                f"non_regression_calibration must be a NonRegressionCalibrationSpec, "
                f"got {type(self.non_regression_calibration)}"
            )


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


def _parse_level1c_target_spec(entry: dict) -> Level1CTargetSpec:
    return Level1CTargetSpec(target=_parse_target_group(entry["target"]), role=entry["role"])


def _parse_non_regression_calibration(entry: dict) -> NonRegressionCalibrationSpec:
    return NonRegressionCalibrationSpec(
        calibration_artifact_sha256=entry["calibration_artifact_sha256"],
        code_commit=entry["code_commit"],
        contract_version=entry["contract_version"],
        ctt_abs_tol=entry["ctt_abs_tol"],
        rho_abs_tol=entry["rho_abs_tol"],
    )


def parse_manifest(raw: dict) -> Level1CManifest:
    """Build the typed, frozen view from an already-schema-validated raw
    dict -- pure transcription into typed objects, plus the fingerprint
    of `raw` itself (compute_manifest_fingerprint, reused verbatim from
    experiments.level1.manifest -- same canonical SHA-256 convention)."""
    return Level1CManifest(
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
            geometry: tuple(_parse_level1c_target_spec(entry) for entry in entries)
            for geometry, entries in raw["target_groups"].items()
        },
        resource_guardrails=ResourceGuardrailsSpec(
            max_dense_dimension=raw["resource_guardrails"]["max_dense_dimension"],
            max_sparse_dimension=raw["resource_guardrails"]["max_sparse_dimension"],
        ),
        degeneracy_tolerance=raw["degeneracy_tolerance"],
        pair_selection=raw["pair_selection"],
        path_selection=raw["path_selection"],
        non_regression_calibration=_parse_non_regression_calibration(raw["non_regression_calibration"]),
        fingerprint=compute_manifest_fingerprint(raw),
        raw=raw,
    )


def load_manifest(path: Path = _MANIFEST_PATH) -> Level1CManifest:
    """The single entry point: load, validate, fingerprint, and parse."""
    raw = load_manifest_json(path)
    return parse_manifest(raw)


def validate_production_windows_match_frozen_table(manifest: Level1CManifest) -> None:
    """Cross-check every grid point's spectral_window against
    FROZEN_PRODUCTION_WINDOWS (the accepted preflight result, section
    19.8) -- production_window is an INPUT this manifest carries, never
    recomputed (section 20.4); this only detects a transcription error
    in the manifest JSON, it never derives a value."""
    for grid_point in manifest.grid:
        case_id = grid_point.hamiltonian_case_ids[0]
        j0 = next(case.J_override[1] for case in manifest.hamiltonian_cases if case.hamiltonian_case_id == case_id)
        expected = FROZEN_PRODUCTION_WINDOWS[(grid_point.geometry, j0)]
        if grid_point.spectral_window != expected:
            raise ValueError(
                f"grid point ({grid_point.geometry!r}, S={grid_point.spin}, J0={j0}): spectral_window "
                f"({grid_point.spectral_window}) does not match the frozen production_window ({expected})"
            )
