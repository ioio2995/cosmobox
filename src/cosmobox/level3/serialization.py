"""Level3 S4 campaign serialization: case-result and campaign-summary
JSON documents (lot L3-I-S4-CAMPAIGN-INFRASTRUCTURE).

Reuses cosmobox.level2.serialization's purely structural/generic payload
builders unchanged (available_payload, regime_mean_payload,
case_metric_analysis_payload, multiplet_entry_payload,
numerical_guard_reference_payload -- none of these carry any S2/S3
semantics in their signature or body: they take a plain metrics.Available/
profiles.RegimeMean/orchestration.CaseMetricAnalysis/adapter.
MultipletProfileEntry and emit a dict). Every payload that DOES carry
spin-explicit semantics (S2/S3/S4-branded field names, the
S4_DIRECTION_*/THREE_SPIN_* taxonomy) is written fresh here, under
Level3's own schema (schemas/level3/*), never Level2's.

No physics and no recomputation of S=2/S=3 anywhere in this module:
delta_hl_s2/delta_hl_s3/c_x_23/d_x_23 are always taken from an
already-loaded frozen Level2 campaign-summary document, passed in by the
caller -- this module never touches the filesystem and never imports
cosmobox.level3.frozen_reference, keeping "load the frozen S2/S3
reference" and "compute/serialize the S3<->S4 comparison" as two
independently testable concerns.

primary_s3_s4_taxonomy is a direct renaming of
cosmobox.level2.profiles's own SAME_INTER_S_DIRECTION/
OPPOSITE_INTER_S_DIRECTION/NO_RESOLVED_SPECTRAL_CONTRAST/NOT_EVALUABLE
taxonomy (computed by cosmobox.level3.execution.compare_spin_pair, which
reuses cosmobox.level2.orchestration.compare_primary_metric_inter_s
verbatim) into the L3-F preregistration's own vocabulary -- no new
classification logic, no new numerical guard, no new threshold.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from cosmobox.level2 import profiles
from cosmobox.level2.metrics import Available
from cosmobox.level2.serialization import (
    available_payload,
    case_metric_analysis_payload,
    multiplet_entry_payload,
    numerical_guard_reference_payload,
)
from cosmobox.level3.execution import CaseExecutionResult, SpinPairComparison, SpinPairControlComparison, SpinPairPrimaryComparison

SCHEMA_VERSION = "level3-s4-campaign-summary-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level3" / "s4-campaign-summary-v1.schema.json"

CASE_RESULT_SCHEMA_VERSION = "level3-s4-case-result-v1"
_CASE_RESULT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level3" / "s4-case-result-v1.schema.json"

S4_DIRECTION_PERSISTS = "S4_DIRECTION_PERSISTS"
S4_DIRECTION_REVERSES = "S4_DIRECTION_REVERSES"
S4_CONTRAST_UNRESOLVED = "S4_CONTRAST_UNRESOLVED"
NOT_EVALUABLE = "NOT_EVALUABLE"

THREE_SPIN_SAME_DIRECTION = "THREE_SPIN_SAME_DIRECTION"
S3_S4_PERSIST_AFTER_S2_S3_REVERSAL = "S3_S4_PERSIST_AFTER_S2_S3_REVERSAL"
SECOND_DIRECTION_REVERSAL_AT_S4 = "SECOND_DIRECTION_REVERSAL_AT_S4"
THREE_SPIN_DIRECTION_NOT_EVALUABLE = "THREE_SPIN_DIRECTION_NOT_EVALUABLE"

_PRIMARY_TAXONOMY_MAP: dict[str, str] = {
    profiles.SAME_INTER_S_DIRECTION: S4_DIRECTION_PERSISTS,
    profiles.OPPOSITE_INTER_S_DIRECTION: S4_DIRECTION_REVERSES,
    profiles.NO_RESOLVED_SPECTRAL_CONTRAST: S4_CONTRAST_UNRESOLVED,
    profiles.NOT_EVALUABLE: NOT_EVALUABLE,
}


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@lru_cache(maxsize=1)
def _load_case_result_schema() -> dict:
    with _CASE_RESULT_SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _case_result_validator() -> Draft202012Validator:
    schema = _load_case_result_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_campaign_summary_document(document: dict) -> None:
    """Raises ValueError (never a bare jsonschema exception) listing
    every violation, not just the first."""
    if not isinstance(document, dict):
        raise ValueError(f"document must be a dict, got {type(document)}")
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against {SCHEMA_VERSION}: {messages}")


def validate_case_result_document(document: dict) -> None:
    """Raises ValueError (never a bare jsonschema exception) listing
    every violation, not just the first."""
    if not isinstance(document, dict):
        raise ValueError(f"document must be a dict, got {type(document)}")
    errors = sorted(_case_result_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against {CASE_RESULT_SCHEMA_VERSION}: {messages}")


# ---------------------------------------------------------------------------
# Case-result payload (one new S4 case)
# ---------------------------------------------------------------------------


def case_result_payload(
    result: CaseExecutionResult,
    *,
    campaign_id: str,
    manifest_fingerprint: str,
    repository: str,
    repository_commit: str,
    branch: str,
    frozen_preregistration_commit: str,
    numerical_guard_m_tt: float,
    numerical_guard_r_eff: float,
    numerical_guard_scope: str,
) -> dict:
    """The complete case-result document for one Level3 S=4 case,
    validated against schemas/level3/s4-case-result-v1.schema.json
    before being returned. Same shape as Level2's own case_result_payload
    (full_spectrum/solver_method/window_truncated/partial_subspace_count
    are emitted as their frozen constants, never read from `result`, for
    the exact same reason Level2's own function does this -- a
    successfully returned CaseExecutionResult can only ever have those
    exact values by construction of cosmobox.level3.execution.run_case),
    restricted to spin=4."""
    if not isinstance(result, CaseExecutionResult):
        raise ValueError(f"expected a CaseExecutionResult, got {type(result)}")
    if result.spec.spin != 4:
        raise ValueError(f"case_result_payload is Level3 S=4-only, got spin={result.spec.spin!r}")

    document = {
        "schema_version": CASE_RESULT_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
        "repository": repository,
        "repository_commit": repository_commit,
        "branch": branch,
        "frozen_preregistration_commit": frozen_preregistration_commit,
        "numerical_guard_reference": numerical_guard_reference_payload(
            guard_m_tt=numerical_guard_m_tt, guard_r_eff=numerical_guard_r_eff, guard_scope=numerical_guard_scope
        ),
        "geometry": result.spec.geometry,
        "spin": result.spec.spin,
        "dimension": result.dimension,
        "group_count": result.group_count,
        "full_spectrum": True,
        "solver_method": "dense",
        "window_truncated": False,
        "partial_subspace_count": 0,
        "multiplet_entries": [multiplet_entry_payload(entry) for entry in result.entries],
        "regime_analyses": {
            "M_TT": case_metric_analysis_payload(result.m_tt_analysis),
            "R_eff": case_metric_analysis_payload(result.r_eff_analysis),
            "A_QQ": case_metric_analysis_payload(result.a_qq_analysis),
            "M_QQ": case_metric_analysis_payload(result.m_qq_analysis),
        },
    }
    validate_case_result_document(document)
    return document


# ---------------------------------------------------------------------------
# S3<->S4 taxonomy and continuous descriptors (pure functions, no I/O)
# ---------------------------------------------------------------------------


def primary_s3_s4_taxonomy(inter_s_taxonomy: str) -> str:
    """Renames cosmobox.level2.profiles's SAME_INTER_S_DIRECTION/
    OPPOSITE_INTER_S_DIRECTION/NO_RESOLVED_SPECTRAL_CONTRAST/
    NOT_EVALUABLE (as produced by compare_spin_pair's own reuse of
    orchestration.compare_primary_metric_inter_s) into the L3-F
    preregistration's own S4_DIRECTION_PERSISTS/S4_DIRECTION_REVERSES/
    S4_CONTRAST_UNRESOLVED/NOT_EVALUABLE vocabulary. Pure renaming: same
    classification, same numerical guard, no new logic."""
    if inter_s_taxonomy not in _PRIMARY_TAXONOMY_MAP:
        raise ValueError(f"unknown inter-S taxonomy {inter_s_taxonomy!r}")
    return _PRIMARY_TAXONOMY_MAP[inter_s_taxonomy]


_RESOLVED_DIRECTIONS = frozenset({"POSITIVE", "NEGATIVE"})


def three_spin_sequence_taxonomy(
    direction_s2: str | None, direction_s3: str | None, direction_s4: str | None
) -> str:
    """Classifies the S2,S3,S4 sign sequence per
    docs/levels/level3/s4-first-campaign-preregistration.md section 9.
    Any of the three directions outside {POSITIVE, NEGATIVE} (i.e. None
    or NUMERICALLY_UNRESOLVED) makes the whole sequence
    THREE_SPIN_DIRECTION_NOT_EVALUABLE. SECOND_DIRECTION_REVERSAL_AT_S4
    is checked before the S2<->S3 relationship, exactly matching its own
    unconditional definition ("S3 et S4 ont des signes opposes")."""
    if (
        direction_s2 not in _RESOLVED_DIRECTIONS
        or direction_s3 not in _RESOLVED_DIRECTIONS
        or direction_s4 not in _RESOLVED_DIRECTIONS
    ):
        return THREE_SPIN_DIRECTION_NOT_EVALUABLE
    if direction_s3 != direction_s4:
        return SECOND_DIRECTION_REVERSAL_AT_S4
    if direction_s2 == direction_s3:
        return THREE_SPIN_SAME_DIRECTION
    return S3_S4_PERSIST_AFTER_S2_S3_REVERSAL


def t_x(delta_a: Available, delta_b: Available) -> Available:
    """abs(delta_b - delta_a), NOT_AVAILABLE if either input is."""
    if delta_a.value is None or delta_b.value is None:
        return Available(None, "DELTA_HL_NOT_AVAILABLE")
    return Available(abs(delta_b.value - delta_a.value), None)


def r_delta_x(t_x_23: Available, t_x_34: Available) -> Available:
    """t_x_34 / t_x_23, only when t_x_23 > 0 -- no threshold, no
    tolerance, per docs/levels/level3/s4-first-campaign-preregistration.md
    section 10.1."""
    if t_x_23.value is None or t_x_34.value is None:
        return Available(None, "T_X_NOT_AVAILABLE")
    if not t_x_23.value > 0:
        return Available(None, "T_X_23_NOT_POSITIVE")
    return Available(t_x_34.value / t_x_23.value, None)


def r_d_x(d_x_23: Available, d_x_34: Available) -> Available:
    """d_x_34 / d_x_23, only when d_x_23 > 0 and both are available -- no
    threshold, per section 10.2."""
    if d_x_23.value is None or d_x_34.value is None:
        return Available(None, "D_X_NOT_AVAILABLE")
    if not d_x_23.value > 0:
        return Available(None, "D_X_23_NOT_POSITIVE")
    return Available(d_x_34.value / d_x_23.value, None)


def _available_from_payload(payload: Mapping) -> Available:
    return Available(payload["value"], payload["reason"])


# ---------------------------------------------------------------------------
# Campaign-summary payload
# ---------------------------------------------------------------------------


def primary_comparison_payload(comparison: SpinPairPrimaryComparison, *, frozen_s2_s3: Mapping) -> dict:
    """One primary metric's full S2/S3/S4 comparison. `comparison` is
    compare_spin_pair's own S3<->S4 result (comparison.delta_hl_lower/
    direction_lower describe the reconstructed S3, comparison.
    delta_hl_higher/direction_higher describe the real S4,
    comparison.cross_profile_correlation/cross_profile_distance ARE
    C_X_34/D_X_34). `frozen_s2_s3` is the already-loaded frozen Level2
    campaign-summary entry for this geometry/metric (carries the pinned
    delta_hl_s2/delta_hl_s3/direction_s2/direction_s3/c_x_23/d_x_23) --
    never recomputed here."""
    if not isinstance(comparison, SpinPairPrimaryComparison):
        raise ValueError(f"expected a SpinPairPrimaryComparison, got {type(comparison)}")

    delta_hl_s2 = _available_from_payload(frozen_s2_s3["delta_hl_s2"])
    delta_hl_s3 = _available_from_payload(frozen_s2_s3["delta_hl_s3"])
    direction_s2 = frozen_s2_s3["direction_s2"]
    direction_s3 = frozen_s2_s3["direction_s3"]
    c_x_23 = _available_from_payload(frozen_s2_s3["c_x_23"])
    d_x_23 = _available_from_payload(frozen_s2_s3["d_x_23"])

    delta_hl_s4 = comparison.delta_hl_higher
    direction_s4 = comparison.direction_higher
    c_x_34 = comparison.cross_profile_correlation
    d_x_34 = comparison.cross_profile_distance

    t23 = t_x(delta_hl_s2, delta_hl_s3)
    t34 = t_x(delta_hl_s3, delta_hl_s4)

    return {
        "metric": comparison.metric,
        "delta_hl_s2": available_payload(delta_hl_s2),
        "delta_hl_s3": available_payload(delta_hl_s3),
        "delta_hl_s4": available_payload(delta_hl_s4),
        "direction_s2": direction_s2,
        "direction_s3": direction_s3,
        "direction_s4": direction_s4,
        "primary_s3_s4_taxonomy": primary_s3_s4_taxonomy(comparison.taxonomy),
        "three_spin_sequence_taxonomy": three_spin_sequence_taxonomy(direction_s2, direction_s3, direction_s4),
        "t_x_23": available_payload(t23),
        "t_x_34": available_payload(t34),
        "r_delta_x": available_payload(r_delta_x(t23, t34)),
        "c_x_23": available_payload(c_x_23),
        "d_x_23": available_payload(d_x_23),
        "c_x_34": available_payload(c_x_34),
        "d_x_34": available_payload(d_x_34),
        "r_d_x": available_payload(r_d_x(d_x_23, d_x_34)),
    }


def control_comparison_payload(comparison: SpinPairControlComparison, *, frozen_s2_s3: Mapping) -> dict:
    """One control metric's descriptive S2/S3/S4 comparison. Deliberately
    emits no taxonomy/shape-descriptor key -- structurally mirrors the
    schema's controlS3S4Comparison $def (additionalProperties: false)."""
    if not isinstance(comparison, SpinPairControlComparison):
        raise ValueError(f"expected a SpinPairControlComparison, got {type(comparison)}")

    delta_hl_s2 = _available_from_payload(frozen_s2_s3["delta_hl_s2"])
    delta_hl_s3 = _available_from_payload(frozen_s2_s3["delta_hl_s3"])
    delta_hl_s4 = comparison.analysis_b.delta_hl

    return {
        "metric": comparison.metric,
        "delta_hl_s2": available_payload(delta_hl_s2),
        "delta_hl_s3": available_payload(delta_hl_s3),
        "delta_hl_s4": available_payload(delta_hl_s4),
    }


def geometry_s4_comparison_payload(
    geometry: str, comparison: SpinPairComparison, *, frozen_geometry_entry: Mapping
) -> dict:
    if not isinstance(comparison, SpinPairComparison):
        raise ValueError(f"expected a SpinPairComparison, got {type(comparison)}")
    if comparison.geometry != geometry:
        raise ValueError(f"comparison.geometry ({comparison.geometry!r}) does not match geometry ({geometry!r})")

    return {
        "geometry": geometry,
        "m_tt": primary_comparison_payload(comparison.m_tt, frozen_s2_s3=frozen_geometry_entry["m_tt"]),
        "r_eff": primary_comparison_payload(comparison.r_eff, frozen_s2_s3=frozen_geometry_entry["r_eff"]),
        "a_qq": control_comparison_payload(comparison.a_qq, frozen_s2_s3=frozen_geometry_entry["a_qq"]),
        "m_qq": control_comparison_payload(comparison.m_qq, frozen_s2_s3=frozen_geometry_entry["m_qq"]),
    }


def campaign_summary_payload(
    geometry_comparisons: Sequence[SpinPairComparison],
    *,
    frozen_campaign_summary: Mapping,
    campaign_id: str,
    manifest_fingerprint: str,
    repository: str,
    repository_commit: str,
    branch: str,
    frozen_preregistration_commit: str,
) -> dict:
    """The complete Level3 S4 campaign-summary document, validated
    against schemas/level3/s4-campaign-summary-v1.schema.json before
    being returned. Requires exactly the three frozen geometries, each
    exactly once. `frozen_campaign_summary` is the already-loaded,
    already-validated frozen Level2 campaign-summary document (its own
    provenance fields become this document's level2_reference block,
    read verbatim, never re-derived)."""
    geometries = {comparison.geometry for comparison in geometry_comparisons}
    if geometries != {"triangle", "ring4", "ring5"} or len(geometry_comparisons) != 3:
        raise ValueError(
            f"geometry_comparisons must contain exactly one comparison each for "
            f"triangle, ring4, ring5, got {[comparison.geometry for comparison in geometry_comparisons]}"
        )

    frozen_by_geometry = {entry["geometry"]: entry for entry in frozen_campaign_summary["geometries"]}

    document = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
        "repository": repository,
        "repository_commit": repository_commit,
        "branch": branch,
        "frozen_preregistration_commit": frozen_preregistration_commit,
        "campaign_status": "COMPLETE",
        "level2_reference": {
            "campaign_id": frozen_campaign_summary["campaign_id"],
            "manifest_fingerprint": frozen_campaign_summary["manifest_fingerprint"],
            "repository_commit": frozen_campaign_summary["repository_commit"],
            "frozen_preregistration_commit": frozen_campaign_summary["frozen_preregistration_commit"],
        },
        "geometries": [
            geometry_s4_comparison_payload(
                comparison.geometry, comparison, frozen_geometry_entry=frozen_by_geometry[comparison.geometry]
            )
            for comparison in sorted(geometry_comparisons, key=lambda comparison: comparison.geometry)
        ],
    }
    validate_campaign_summary_document(document)
    return document
