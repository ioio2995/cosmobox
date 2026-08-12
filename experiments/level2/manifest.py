"""Machine-readable Level2 campaign manifest.

experiments/level2/preregistered-manifest-v1.json is the normative
machine-readable transcription of the Level2 first-test scientific
contract (docs/levels/level2/spectral-regime-design.md,
docs/levels/level2/profile-comparison-preregistration.md,
docs/levels/level2/numerical-guard-protocol.md, frozen at commit
2d4c859db7939da51ee7d919889a18f4c7e229ed). This module performs no
scientific computation: it loads, validates (Draft 2020-12,
schemas/level2/campaign-manifest-v1.schema.json), computes
manifest_fingerprint (reusing experiments.level1.manifest.
compute_manifest_fingerprint verbatim -- a generic SHA-256-of-canonical-
JSON utility with no Level1-specific content, already reused the exact
same way by experiments/level1c/manifest.py), and exposes typed, frozen
views.

This module is deliberately independent of cosmobox.level2.execution:
Level2ManifestCase describes the manifest's own (geometry, spin) data; it
is never cosmobox.level2.execution.CaseSpec itself -- the same
architectural separation experiments/level1/manifest.py already
maintains from cosmobox.level0/level1 (HamiltonianCaseSpec is a plain
data description, never a cosmobox.level0.params.HamiltonianParameters).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from experiments.level1.manifest import compute_manifest_fingerprint

_MANIFEST_PATH = Path(__file__).resolve().parent / "preregistered-manifest-v1.json"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "level2" / "campaign-manifest-v1.schema.json"

GEOMETRIES = ("triangle", "ring4", "ring5")
SPINS = (2, 3)
PRIMARY_METRICS = ("M_TT", "R_eff")
CONTROL_METRICS = ("A_QQ", "M_QQ")

_EXPECTED_CASE_ORDER = tuple((geometry, spin) for geometry in GEOMETRIES for spin in SPINS)
"""Geometry-major, spin-minor -- the same deterministic order as
cosmobox.level2.execution.build_all_reference_case_specs()."""


@dataclass(frozen=True, slots=True)
class Level2ManifestCase:
    geometry: str
    spin: int

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        if self.spin not in SPINS:
            raise ValueError(f"spin must be one of {SPINS}, got {self.spin!r}")


@dataclass(frozen=True, slots=True)
class NumericalGuardReference:
    """The frozen L2-C1 reproducibility guards, transcribed -- never
    recomputed, never widened."""

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
class InterSPolicy:
    """The L2-D3 control-metric arbitration, transcribed as data: primary
    metrics get a taxonomy and both shape descriptors; control metrics
    stay descriptive only."""

    primary: tuple[str, ...]
    control: str

    def __post_init__(self) -> None:
        if set(self.primary) != {"taxonomy", "C_X_23", "D_X_23"}:
            raise ValueError(
                f"primary inter-S policy must be exactly {{'taxonomy','C_X_23','D_X_23'}}, got {set(self.primary)}"
            )
        if self.control != "descriptive_only":
            raise ValueError(f"control inter-S policy must be 'descriptive_only', got {self.control!r}")


@dataclass(frozen=True, slots=True)
class Level2Manifest:
    manifest_version: str
    campaign_id: str
    schema_version: str
    branch: str
    frozen_preregistration_commit: str
    numerical_guard_reference: NumericalGuardReference
    cases: tuple[Level2ManifestCase, ...]
    full_spectrum_required: bool
    primary_metrics: tuple[str, ...]
    control_metrics: tuple[str, ...]
    primary_contrast: str
    inter_s_policy: InterSPolicy
    fingerprint: str
    raw: dict

    def __post_init__(self) -> None:
        if self.manifest_version != "level2-reference-v1":
            raise ValueError(f"manifest_version must be 'level2-reference-v1', got {self.manifest_version!r}")
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.schema_version:
            raise ValueError("schema_version must be non-empty")
        if not self.branch:
            raise ValueError("branch must be non-empty")
        commit = self.frozen_preregistration_commit
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            raise ValueError(f"frozen_preregistration_commit must be a 40-character lowercase hex string, got {commit!r}")
        if not isinstance(self.numerical_guard_reference, NumericalGuardReference):
            raise ValueError(f"numerical_guard_reference must be a NumericalGuardReference, got {type(self.numerical_guard_reference)}")
        if not self.full_spectrum_required:
            raise ValueError("full_spectrum_required must be true for the first Level2 normative test")
        if tuple(self.primary_metrics) != PRIMARY_METRICS:
            raise ValueError(f"primary_metrics must be exactly {PRIMARY_METRICS}, got {tuple(self.primary_metrics)}")
        if tuple(self.control_metrics) != CONTROL_METRICS:
            raise ValueError(f"control_metrics must be exactly {CONTROL_METRICS}, got {tuple(self.control_metrics)}")
        if self.primary_contrast != "HIGH_MINUS_LOW":
            raise ValueError(f"primary_contrast must be 'HIGH_MINUS_LOW', got {self.primary_contrast!r}")
        if not isinstance(self.inter_s_policy, InterSPolicy):
            raise ValueError(f"inter_s_policy must be an InterSPolicy, got {type(self.inter_s_policy)}")

        actual_order = tuple((case.geometry, case.spin) for case in self.cases)
        if len(actual_order) != 6:
            raise ValueError(f"cases must contain exactly 6 entries, got {len(actual_order)}")
        if len(set(actual_order)) != 6:
            raise ValueError(f"cases must not contain duplicates, got {actual_order}")
        if actual_order != _EXPECTED_CASE_ORDER:
            raise ValueError(
                f"cases must be exactly the six frozen Level2 combinations in geometry-major, "
                f"spin-minor order {_EXPECTED_CASE_ORDER}, got {actual_order}"
            )
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


def parse_manifest(raw: dict) -> Level2Manifest:
    """Build the typed, frozen view from an already-schema-validated raw
    dict (load_manifest_json's job, not repeated here) -- pure
    transcription into typed objects, plus the fingerprint of `raw`
    itself."""
    guard = raw["numerical_guard_reference"]
    policy = raw["inter_s_policy"]
    return Level2Manifest(
        manifest_version=raw["manifest_version"],
        campaign_id=raw["campaign_id"],
        schema_version=raw["schema_version"],
        branch=raw["branch"],
        frozen_preregistration_commit=raw["frozen_preregistration_commit"],
        numerical_guard_reference=NumericalGuardReference(
            guard_m_tt=guard["guard_m_tt"], guard_r_eff=guard["guard_r_eff"], guard_scope=guard["guard_scope"]
        ),
        cases=tuple(Level2ManifestCase(geometry=entry["geometry"], spin=entry["spin"]) for entry in raw["cases"]),
        full_spectrum_required=raw["full_spectrum_required"],
        primary_metrics=tuple(raw["primary_metrics"]),
        control_metrics=tuple(raw["control_metrics"]),
        primary_contrast=raw["primary_contrast"],
        inter_s_policy=InterSPolicy(primary=tuple(policy["primary"]), control=policy["control"]),
        fingerprint=compute_manifest_fingerprint(raw),
        raw=raw,
    )


def load_manifest(path: Path = _MANIFEST_PATH) -> Level2Manifest:
    """The single entry point: load, validate, fingerprint, and parse."""
    raw = load_manifest_json(path)
    return parse_manifest(raw)
