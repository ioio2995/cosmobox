"""Machine-readable Level3 S4 campaign manifest.

experiments/level3/preregistered-s4-manifest-v1.json is the normative
machine-readable transcription of the Level3 S4 first-campaign scientific
contract (docs/levels/level3/s4-first-campaign-preregistration.md, frozen
at commit 1c1d71f07dd6a7399b3965b2bb0acfa5c665991e). This module performs
no scientific computation: it loads, validates (Draft 2020-12,
schemas/level3/s4-campaign-manifest-v1.schema.json), computes
manifest_fingerprint (reusing experiments.level1.manifest.
compute_manifest_fingerprint verbatim -- the same generic SHA-256-of-
canonical-JSON utility already reused unchanged by Level1c and Level2),
and exposes typed, frozen views.

Deliberately independent of experiments.level2.manifest.Level2Manifest and
of cosmobox.level3.execution: this manifest pins the frozen Level2
reference identity (level2_reference) and the validated dense capability
as explicit, literal data, never by importing Level2's own manifest or
cosmobox.level3.execution.LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT at
runtime -- the same architectural separation experiments/level2/
manifest.py already maintains from cosmobox.level2/level0 (a plain data
description, never a runtime object from the execution layer). Kept in
sync with cosmobox.level3.execution's own constant by a dedicated test,
not by import.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.level1.manifest import compute_manifest_fingerprint

_MANIFEST_PATH = Path(__file__).resolve().parent / "preregistered-s4-manifest-v1.json"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level3" / "s4-campaign-manifest-v1.schema.json"

GEOMETRIES = ("triangle", "ring4", "ring5")
SPIN = 4
"""The only spin this manifest's cases may declare -- Level3's first
campaign extends the frozen Level2 reference by exactly one new
truncation, per docs/levels/level3/s4-first-campaign-preregistration.md.
Never a whitelist: a single frozen value, checked by equality."""

PRIMARY_METRICS = ("M_TT", "R_eff")
CONTROL_METRICS = ("A_QQ", "M_QQ")

_EXPECTED_CASE_ORDER = tuple((geometry, SPIN) for geometry in GEOMETRIES)
"""triangle, ring4, ring5, all at S=4 -- geometry-major order, mirroring
cosmobox.level3.execution's own GEOMETRIES order. Never S=2/S=3 (those
are the frozen Level2 reference, never a case this manifest executes) and
never S=5 (a future, separately pre-registered extension)."""

EXPECTED_S4_DIMENSIONS: dict[str, int] = {"triangle": 168, "ring4": 572, "ring5": 2008}
"""Hilbert-space dimensions established by the L3-C capability preflight
(docs/governance/current-task.md) -- reference data only, cross-checked
by the future campaign's gates against the real run_case(...).dimension,
never assumed without that check."""

VALIDATED_DENSE_CAPABILITY = 2008
"""Must stay equal to cosmobox.level3.execution.LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT
(L3-E) -- duplicated here as a literal, not imported, per this module's
own architectural-independence rule above. Cross-checked by
tests/experiments/level3/test_level3_manifest.py, not by a runtime
import."""


@dataclass(frozen=True, slots=True)
class Level3ManifestCase:
    geometry: str
    spin: int

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        if self.spin != SPIN:
            raise ValueError(f"spin must be exactly {SPIN} (the only Level3 S4 campaign case), got {self.spin!r}")


@dataclass(frozen=True, slots=True)
class NumericalGuardReference:
    """The frozen L2-C1 reproducibility guards, transcribed -- never
    recomputed, never widened. Identical values to Level2's own frozen
    guards: the Level3 S3<->S4 taxonomy reuses exactly the same numerical
    zero-resolution policy, per the L3-F preregistration."""

    guard_m_tt: float
    guard_r_eff: float
    guard_scope: str

    def __post_init__(self) -> None:
        if self.guard_m_tt != 1e-16:
            raise ValueError(f"guard_m_tt must be exactly 1e-16 (L2-C1, frozen), got {self.guard_m_tt!r}")
        if self.guard_r_eff != 1e-15:
            raise ValueError(f"guard_r_eff must be exactly 1e-15 (L2-C1, frozen), got {self.guard_r_eff!r}")
        if self.guard_scope != "DELTA_HL_ONLY":
            raise ValueError(f"guard_scope must be 'DELTA_HL_ONLY', got {self.guard_scope!r}")


@dataclass(frozen=True, slots=True)
class PhysicalParameters:
    """Documentary transcription of the frozen reference Hamiltonian
    (docs/levels/level3/s4-first-campaign-preregistration.md SS3). Not
    consumed by any execution path: the real, enforced values live in
    cosmobox.level2.execution.REFERENCE_N_FLAVORS/
    build_reference_hamiltonian_parameters/REFERENCE_EXTERNAL_CHARGES,
    reused unchanged by cosmobox.level3.execution.run_case. This block
    exists so the manifest is a self-contained, auditable record of the
    physical contract, without becoming a second, independently
    consumed source of it."""

    n_flavors: int
    j: float
    h: float
    t: float
    g_e: float
    k: float
    external_charges: float

    def __post_init__(self) -> None:
        if self.n_flavors != 2:
            raise ValueError(f"n_flavors must be exactly 2, got {self.n_flavors!r}")
        if self.j != 1.0:
            raise ValueError(f"j must be exactly 1.0, got {self.j!r}")
        if self.h != 0.0:
            raise ValueError(f"h must be exactly 0.0, got {self.h!r}")
        if self.t != 1.0:
            raise ValueError(f"t must be exactly 1.0, got {self.t!r}")
        if self.g_e != 1.0:
            raise ValueError(f"g_e must be exactly 1.0, got {self.g_e!r}")
        if self.k != 1.0:
            raise ValueError(f"k must be exactly 1.0, got {self.k!r}")
        if self.external_charges != 0.0:
            raise ValueError(f"external_charges must be exactly 0.0, got {self.external_charges!r}")


@dataclass(frozen=True, slots=True)
class Level2ReferenceIdentity:
    """The frozen Level2 campaign identity Level3 pins as its exclusive
    S=2/S=3 source -- literal, hard-checked values, never re-derived by
    loading experiments.level2.manifest at runtime."""

    campaign_id: str
    manifest_fingerprint: str
    repository_commit: str
    frozen_preregistration_commit: str

    def __post_init__(self) -> None:
        if self.campaign_id != "level2-energy-regime-v1":
            raise ValueError(f"level2_reference.campaign_id must be 'level2-energy-regime-v1', got {self.campaign_id!r}")
        if self.manifest_fingerprint != "82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4":
            raise ValueError(
                "level2_reference.manifest_fingerprint must be "
                f"'82dca9dee756f531375b31540b4f7d05c2c8ba1760150f2d9972f12a5da06fa4', got {self.manifest_fingerprint!r}"
            )
        if self.repository_commit != "1feb03f41f9e73078efbc760dd2cba2b667e2ed0":
            raise ValueError(
                f"level2_reference.repository_commit must be '1feb03f41f9e73078efbc760dd2cba2b667e2ed0', "
                f"got {self.repository_commit!r}"
            )
        if self.frozen_preregistration_commit != "2d4c859db7939da51ee7d919889a18f4c7e229ed":
            raise ValueError(
                "level2_reference.frozen_preregistration_commit must be "
                f"'2d4c859db7939da51ee7d919889a18f4c7e229ed', got {self.frozen_preregistration_commit!r}"
            )


@dataclass(frozen=True, slots=True)
class Level3Manifest:
    manifest_version: str
    campaign_id: str
    schema_version: str
    branch: str
    frozen_preregistration_commit: str
    cases: tuple[Level3ManifestCase, ...]
    physical_parameters: PhysicalParameters
    full_spectrum_required: bool
    primary_metrics: tuple[str, ...]
    control_metrics: tuple[str, ...]
    primary_contrast: str
    numerical_guard_reference: NumericalGuardReference
    level2_reference: Level2ReferenceIdentity
    expected_s4_dimensions: dict[str, int]
    validated_dense_capability: int
    forbidden_extensions: tuple[str, ...]
    fingerprint: str
    raw: dict

    def __post_init__(self) -> None:
        if self.manifest_version != "level3-s4-reference-v1":
            raise ValueError(f"manifest_version must be 'level3-s4-reference-v1', got {self.manifest_version!r}")
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.schema_version:
            raise ValueError("schema_version must be non-empty")
        if not self.branch:
            raise ValueError("branch must be non-empty")
        commit = self.frozen_preregistration_commit
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            raise ValueError(f"frozen_preregistration_commit must be a 40-character lowercase hex string, got {commit!r}")
        if commit != "1c1d71f07dd6a7399b3965b2bb0acfa5c665991e":
            raise ValueError(
                f"frozen_preregistration_commit must be the frozen L3-F commit "
                f"'1c1d71f07dd6a7399b3965b2bb0acfa5c665991e', got {commit!r}"
            )
        if not isinstance(self.physical_parameters, PhysicalParameters):
            raise ValueError(f"physical_parameters must be a PhysicalParameters, got {type(self.physical_parameters)}")
        if not self.full_spectrum_required:
            raise ValueError("full_spectrum_required must be true for the Level3 S4 campaign")
        if tuple(self.primary_metrics) != PRIMARY_METRICS:
            raise ValueError(f"primary_metrics must be exactly {PRIMARY_METRICS}, got {tuple(self.primary_metrics)}")
        if tuple(self.control_metrics) != CONTROL_METRICS:
            raise ValueError(f"control_metrics must be exactly {CONTROL_METRICS}, got {tuple(self.control_metrics)}")
        if self.primary_contrast != "HIGH_MINUS_LOW":
            raise ValueError(f"primary_contrast must be 'HIGH_MINUS_LOW', got {self.primary_contrast!r}")
        if not isinstance(self.numerical_guard_reference, NumericalGuardReference):
            raise ValueError(
                f"numerical_guard_reference must be a NumericalGuardReference, got {type(self.numerical_guard_reference)}"
            )
        if not isinstance(self.level2_reference, Level2ReferenceIdentity):
            raise ValueError(f"level2_reference must be a Level2ReferenceIdentity, got {type(self.level2_reference)}")

        actual_order = tuple((case.geometry, case.spin) for case in self.cases)
        if len(actual_order) != 3:
            raise ValueError(f"cases must contain exactly 3 entries, got {len(actual_order)}")
        if len(set(actual_order)) != 3:
            raise ValueError(f"cases must not contain duplicates, got {actual_order}")
        if actual_order != _EXPECTED_CASE_ORDER:
            raise ValueError(
                f"cases must be exactly the three frozen Level3 S4 combinations in geometry-major "
                f"order {_EXPECTED_CASE_ORDER}, got {actual_order}"
            )

        if dict(self.expected_s4_dimensions) != EXPECTED_S4_DIMENSIONS:
            raise ValueError(
                f"expected_s4_dimensions must be exactly {EXPECTED_S4_DIMENSIONS}, got {dict(self.expected_s4_dimensions)}"
            )
        if self.validated_dense_capability != VALIDATED_DENSE_CAPABILITY:
            raise ValueError(
                f"validated_dense_capability must be exactly {VALIDATED_DENSE_CAPABILITY}, "
                f"got {self.validated_dense_capability!r}"
            )
        if "S5" not in self.forbidden_extensions:
            raise ValueError(f"forbidden_extensions must include 'S5', got {self.forbidden_extensions!r}")

        if not self.fingerprint:
            raise ValueError("fingerprint must be non-empty")
        if not isinstance(self.raw, dict):
            raise ValueError(f"raw must be a dict, got {type(self.raw)}")


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def load_manifest_json(path: Path = _MANIFEST_PATH) -> dict:
    """Load and schema-validate the raw manifest dict. Raises ValueError
    (never a bare jsonschema exception) listing every violation."""
    with Path(path).open() as handle:
        raw = json.load(handle)
    errors = sorted(_validator().iter_errors(raw), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"manifest does not validate against its schema: {messages}")
    return raw


def parse_manifest(raw: dict) -> Level3Manifest:
    """Build the typed, frozen view from an already-schema-validated raw
    dict (load_manifest_json's job, not repeated here) -- pure
    transcription into typed objects, plus the fingerprint of `raw`
    itself."""
    guard = raw["numerical_guard_reference"]
    physical = raw["physical_parameters"]
    level2_reference = raw["level2_reference"]
    return Level3Manifest(
        manifest_version=raw["manifest_version"],
        campaign_id=raw["campaign_id"],
        schema_version=raw["schema_version"],
        branch=raw["branch"],
        frozen_preregistration_commit=raw["frozen_preregistration_commit"],
        cases=tuple(Level3ManifestCase(geometry=entry["geometry"], spin=entry["spin"]) for entry in raw["cases"]),
        physical_parameters=PhysicalParameters(
            n_flavors=physical["n_flavors"],
            j=physical["j"],
            h=physical["h"],
            t=physical["t"],
            g_e=physical["g_e"],
            k=physical["k"],
            external_charges=physical["external_charges"],
        ),
        full_spectrum_required=raw["full_spectrum_required"],
        primary_metrics=tuple(raw["primary_metrics"]),
        control_metrics=tuple(raw["control_metrics"]),
        primary_contrast=raw["primary_contrast"],
        numerical_guard_reference=NumericalGuardReference(
            guard_m_tt=guard["guard_m_tt"], guard_r_eff=guard["guard_r_eff"], guard_scope=guard["guard_scope"]
        ),
        level2_reference=Level2ReferenceIdentity(
            campaign_id=level2_reference["campaign_id"],
            manifest_fingerprint=level2_reference["manifest_fingerprint"],
            repository_commit=level2_reference["repository_commit"],
            frozen_preregistration_commit=level2_reference["frozen_preregistration_commit"],
        ),
        expected_s4_dimensions=dict(raw["expected_s4_dimensions"]),
        validated_dense_capability=raw["validated_dense_capability"],
        forbidden_extensions=tuple(raw["forbidden_extensions"]),
        fingerprint=compute_manifest_fingerprint(raw),
        raw=raw,
    )


def load_manifest(path: Path = _MANIFEST_PATH) -> Level3Manifest:
    """The single entry point: load, validate, fingerprint, and parse."""
    raw = load_manifest_json(path)
    return parse_manifest(raw)
