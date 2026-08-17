"""Level3 S6 campaign serialization: case-result and campaign-summary
JSON documents (lot L3-W-S6-CAMPAIGN-INFRASTRUCTURE).

Reuses cosmobox.level2.serialization's purely structural/generic payload
builders unchanged (available_payload, case_metric_analysis_payload,
multiplet_entry_payload, numerical_guard_reference_payload) and
cosmobox.level3.serialization's own generic, zero-S-branding math
primitives (t_x, r_delta_x, r_d_x -- pure functions of two Available
deltas, already reused as-is for T_X_56/R_DELTA_X_56_45/R_D_X_56_45,
never duplicated). Every payload that DOES carry spin-explicit semantics
(S6_DIRECTION_* taxonomy, the five-spin REVERSAL_COUNT_23456, and the
two-step LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS descriptor) is
written fresh here, under Level3's own S6 schema, never S4's or S5's.

No physics and no recomputation of S=2/S=3/S=4/S=5 anywhere in this
module: delta_hl_s2/s3/s4/s5, direction_s2/s3/s4/s5, t_x_34/t_x_45,
c_x_34/d_x_34/c_x_45/d_x_45 are always taken from an already-loaded
frozen Level3 S5 campaign-summary document, passed in by the caller (the
S5 document itself already embeds a pinned copy of the S2/S3/S4 values
Level2 and the S4 campaign produced, plus its own level2_reference and
level3_s4_reference blocks -- read here, never re-derived). This module
never touches the filesystem and never imports
cosmobox.level3.frozen_s5_reference, keeping "load the frozen
S5/S4/S2/S3 reference" and "compute/serialize the S5<->S6 comparison" as
two independently testable concerns, exactly as
cosmobox.level3.s5_serialization already separates itself from
cosmobox.level3.frozen_s4_reference.

primary_s5_s6_taxonomy is a direct renaming of
cosmobox.level2.profiles's own SAME_INTER_S_DIRECTION/
OPPOSITE_INTER_S_DIRECTION/NO_RESOLVED_SPECTRAL_CONTRAST/NOT_EVALUABLE
taxonomy (computed by cosmobox.level3.execution.compare_spin_pair, which
reuses cosmobox.level2.orchestration.compare_primary_metric_inter_s
verbatim) into the L3-T preregistration's own vocabulary -- no new
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
from cosmobox.level3.serialization import r_d_x, r_delta_x, t_x

SCHEMA_VERSION = "level3-s6-campaign-summary-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level3" / "s6-campaign-summary-v1.schema.json"

CASE_RESULT_SCHEMA_VERSION = "level3-s6-case-result-v1"
_CASE_RESULT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level3" / "s6-case-result-v1.schema.json"

S6_DIRECTION_PERSISTS = "S6_DIRECTION_PERSISTS"
S6_DIRECTION_REVERSES = "S6_DIRECTION_REVERSES"
S6_CONTRAST_UNRESOLVED = "S6_CONTRAST_UNRESOLVED"
NOT_EVALUABLE = "NOT_EVALUABLE"

REVERSAL_COUNT_NOT_EVALUABLE = "NOT_EVALUABLE"

LAST_TWO_TRANSITIONS_YES = "YES"
LAST_TWO_TRANSITIONS_NO = "NO"
LAST_TWO_TRANSITIONS_NOT_EVALUABLE = "NOT_EVALUABLE"

_PRIMARY_TAXONOMY_MAP: dict[str, str] = {
    profiles.SAME_INTER_S_DIRECTION: S6_DIRECTION_PERSISTS,
    profiles.OPPOSITE_INTER_S_DIRECTION: S6_DIRECTION_REVERSES,
    profiles.NO_RESOLVED_SPECTRAL_CONTRAST: S6_CONTRAST_UNRESOLVED,
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
# Case-result payload (one new S6 case)
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
    """The complete case-result document for one Level3 S=6 case,
    validated against schemas/level3/s6-case-result-v1.schema.json
    before being returned. Same shape as the S5 case-result payload,
    restricted to spin=6."""
    if not isinstance(result, CaseExecutionResult):
        raise ValueError(f"expected a CaseExecutionResult, got {type(result)}")
    if result.spec.spin != 6:
        raise ValueError(f"case_result_payload is Level3 S=6-only, got spin={result.spec.spin!r}")

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
# S5<->S6 taxonomy, five-spin sequence, and two-step continuity descriptor
# (pure functions, no I/O)
# ---------------------------------------------------------------------------


def primary_s5_s6_taxonomy(inter_s_taxonomy: str) -> str:
    """Renames cosmobox.level2.profiles's SAME_INTER_S_DIRECTION/
    OPPOSITE_INTER_S_DIRECTION/NO_RESOLVED_SPECTRAL_CONTRAST/
    NOT_EVALUABLE (as produced by compare_spin_pair's own reuse of
    orchestration.compare_primary_metric_inter_s) into the L3-T
    preregistration's own S6_DIRECTION_PERSISTS/S6_DIRECTION_REVERSES/
    S6_CONTRAST_UNRESOLVED/NOT_EVALUABLE vocabulary. Pure renaming: same
    classification, same numerical guard, no new logic."""
    if inter_s_taxonomy not in _PRIMARY_TAXONOMY_MAP:
        raise ValueError(f"unknown inter-S taxonomy {inter_s_taxonomy!r}")
    return _PRIMARY_TAXONOMY_MAP[inter_s_taxonomy]


_RESOLVED_DIRECTIONS = frozenset({"POSITIVE", "NEGATIVE"})


def reversal_count_23456(
    direction_s2: str | None,
    direction_s3: str | None,
    direction_s4: str | None,
    direction_s5: str | None,
    direction_s6: str | None,
) -> int | str:
    """REVERSAL_COUNT_23456 per
    docs/levels/level3/s6-third-extension-preregistration.md section 11:
    I[sign(S2)!=sign(S3)] + I[sign(S3)!=sign(S4)] + I[sign(S4)!=sign(S5)]
    + I[sign(S5)!=sign(S6)], only when all five directions are resolved
    (POSITIVE/NEGATIVE) -- else the literal string "NOT_EVALUABLE".
    Purely descriptive: never interpreted here as a convergence
    criterion."""
    directions = (direction_s2, direction_s3, direction_s4, direction_s5, direction_s6)
    if any(direction not in _RESOLVED_DIRECTIONS for direction in directions):
        return REVERSAL_COUNT_NOT_EVALUABLE
    return (
        int(direction_s2 != direction_s3)
        + int(direction_s3 != direction_s4)
        + int(direction_s4 != direction_s5)
        + int(direction_s5 != direction_s6)
    )


def last_two_transitions_directionally_continuous(
    direction_s4: str | None, direction_s5: str | None, direction_s6: str | None
) -> str:
    """LAST_TWO_TRANSITIONS_DIRECTIONALLY_CONTINUOUS per
    docs/levels/level3/s6-third-extension-preregistration.md section 12:

    YES if sign(S4) = sign(S5) = sign(S6);
    NO if the three signs are resolved and at least one of S4->S5 or
        S5->S6 changes sign;
    NOT_EVALUABLE if any of the three signs is not resolved.

    A finite descriptor of exactly the last two transitions -- never a
    convergence criterion, never interpreted here."""
    directions = (direction_s4, direction_s5, direction_s6)
    if any(direction not in _RESOLVED_DIRECTIONS for direction in directions):
        return LAST_TWO_TRANSITIONS_NOT_EVALUABLE
    if direction_s4 == direction_s5 == direction_s6:
        return LAST_TWO_TRANSITIONS_YES
    return LAST_TWO_TRANSITIONS_NO


def _available_from_payload(payload: Mapping) -> Available:
    return Available(payload["value"], payload["reason"])


# ---------------------------------------------------------------------------
# Campaign-summary payload
# ---------------------------------------------------------------------------


def primary_comparison_payload(comparison: SpinPairPrimaryComparison, *, frozen_s2_s3_s4_s5: Mapping) -> dict:
    """One primary metric's full S2/S3/S4/S5/S6 comparison. `comparison`
    is compare_spin_pair's own S5<->S6 result (comparison.delta_hl_lower/
    direction_lower describe the reconstructed S5, comparison.
    delta_hl_higher/direction_higher describe the real S6,
    comparison.cross_profile_correlation/cross_profile_distance ARE
    C_X_56/D_X_56). `frozen_s2_s3_s4_s5` is the already-loaded frozen
    Level3 S5 campaign-summary entry for this geometry/metric (carries
    the pinned delta_hl_s2/s3/s4/s5, direction_s2/s3/s4/s5, t_x_34/t_x_45,
    c_x_34/d_x_34/c_x_45/d_x_45) -- never recomputed here."""
    if not isinstance(comparison, SpinPairPrimaryComparison):
        raise ValueError(f"expected a SpinPairPrimaryComparison, got {type(comparison)}")

    delta_hl_s2 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s2"])
    delta_hl_s3 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s3"])
    delta_hl_s4 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s4"])
    delta_hl_s5 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s5"])
    direction_s2 = frozen_s2_s3_s4_s5["direction_s2"]
    direction_s3 = frozen_s2_s3_s4_s5["direction_s3"]
    direction_s4 = frozen_s2_s3_s4_s5["direction_s4"]
    direction_s5 = frozen_s2_s3_s4_s5["direction_s5"]
    t_x_45 = _available_from_payload(frozen_s2_s3_s4_s5["t_x_45"])
    c_x_45 = _available_from_payload(frozen_s2_s3_s4_s5["c_x_45"])
    d_x_45 = _available_from_payload(frozen_s2_s3_s4_s5["d_x_45"])

    delta_hl_s6 = comparison.delta_hl_higher
    direction_s6 = comparison.direction_higher
    c_x_56 = comparison.cross_profile_correlation
    d_x_56 = comparison.cross_profile_distance

    t_x_56 = t_x(delta_hl_s5, delta_hl_s6)

    return {
        "metric": comparison.metric,
        "delta_hl_s2": available_payload(delta_hl_s2),
        "delta_hl_s3": available_payload(delta_hl_s3),
        "delta_hl_s4": available_payload(delta_hl_s4),
        "delta_hl_s5": available_payload(delta_hl_s5),
        "delta_hl_s6": available_payload(delta_hl_s6),
        "direction_s2": direction_s2,
        "direction_s3": direction_s3,
        "direction_s4": direction_s4,
        "direction_s5": direction_s5,
        "direction_s6": direction_s6,
        "primary_s5_s6_taxonomy": primary_s5_s6_taxonomy(comparison.taxonomy),
        "reversal_count_23456": reversal_count_23456(direction_s2, direction_s3, direction_s4, direction_s5, direction_s6),
        "last_two_transitions_directionally_continuous": last_two_transitions_directionally_continuous(
            direction_s4, direction_s5, direction_s6
        ),
        "t_x_45": available_payload(t_x_45),
        "t_x_56": available_payload(t_x_56),
        "r_delta_x_56_45": available_payload(r_delta_x(t_x_45, t_x_56)),
        "c_x_45": available_payload(c_x_45),
        "d_x_45": available_payload(d_x_45),
        "c_x_56": available_payload(c_x_56),
        "d_x_56": available_payload(d_x_56),
        "r_d_x_56_45": available_payload(r_d_x(d_x_45, d_x_56)),
    }


def control_comparison_payload(comparison: SpinPairControlComparison, *, frozen_s2_s3_s4_s5: Mapping) -> dict:
    """One control metric's descriptive S2/S3/S4/S5/S6 comparison.
    Deliberately emits no taxonomy/reversal-count/continuity/
    shape-descriptor key -- structurally mirrors the schema's
    controlS5S6Comparison $def (additionalProperties: false)."""
    if not isinstance(comparison, SpinPairControlComparison):
        raise ValueError(f"expected a SpinPairControlComparison, got {type(comparison)}")

    delta_hl_s2 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s2"])
    delta_hl_s3 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s3"])
    delta_hl_s4 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s4"])
    delta_hl_s5 = _available_from_payload(frozen_s2_s3_s4_s5["delta_hl_s5"])
    delta_hl_s6 = comparison.analysis_b.delta_hl

    return {
        "metric": comparison.metric,
        "delta_hl_s2": available_payload(delta_hl_s2),
        "delta_hl_s3": available_payload(delta_hl_s3),
        "delta_hl_s4": available_payload(delta_hl_s4),
        "delta_hl_s5": available_payload(delta_hl_s5),
        "delta_hl_s6": available_payload(delta_hl_s6),
    }


def geometry_s6_comparison_payload(
    geometry: str, comparison: SpinPairComparison, *, frozen_s5_geometry_entry: Mapping
) -> dict:
    if not isinstance(comparison, SpinPairComparison):
        raise ValueError(f"expected a SpinPairComparison, got {type(comparison)}")
    if comparison.geometry != geometry:
        raise ValueError(f"comparison.geometry ({comparison.geometry!r}) does not match geometry ({geometry!r})")

    return {
        "geometry": geometry,
        "m_tt": primary_comparison_payload(comparison.m_tt, frozen_s2_s3_s4_s5=frozen_s5_geometry_entry["m_tt"]),
        "r_eff": primary_comparison_payload(comparison.r_eff, frozen_s2_s3_s4_s5=frozen_s5_geometry_entry["r_eff"]),
        "a_qq": control_comparison_payload(comparison.a_qq, frozen_s2_s3_s4_s5=frozen_s5_geometry_entry["a_qq"]),
        "m_qq": control_comparison_payload(comparison.m_qq, frozen_s2_s3_s4_s5=frozen_s5_geometry_entry["m_qq"]),
    }


def campaign_summary_payload(
    geometry_comparisons: Sequence[SpinPairComparison],
    *,
    frozen_s5_campaign_summary: Mapping,
    campaign_id: str,
    manifest_fingerprint: str,
    repository: str,
    repository_commit: str,
    branch: str,
    frozen_preregistration_commit: str,
) -> dict:
    """The complete Level3 S6 campaign-summary document, validated
    against schemas/level3/s6-campaign-summary-v1.schema.json before
    being returned. Requires exactly the three frozen geometries, each
    exactly once. `frozen_s5_campaign_summary` is the already-loaded,
    already-validated frozen Level3 S5 campaign-summary document: its own
    provenance fields become this document's level3_s5_reference block,
    and its own embedded level2_reference/level3_s4_reference blocks
    (recorded once, at L3-P time) become this document's level2_reference
    and level3_s4_reference blocks -- all read verbatim, never
    re-derived, never re-fetched from a second source."""
    geometries = {comparison.geometry for comparison in geometry_comparisons}
    if geometries != {"triangle", "ring4", "ring5"} or len(geometry_comparisons) != 3:
        raise ValueError(
            f"geometry_comparisons must contain exactly one comparison each for "
            f"triangle, ring4, ring5, got {[comparison.geometry for comparison in geometry_comparisons]}"
        )

    frozen_by_geometry = {entry["geometry"]: entry for entry in frozen_s5_campaign_summary["geometries"]}

    document = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
        "repository": repository,
        "repository_commit": repository_commit,
        "branch": branch,
        "frozen_preregistration_commit": frozen_preregistration_commit,
        "campaign_status": "COMPLETE",
        "level2_reference": dict(frozen_s5_campaign_summary["level2_reference"]),
        "level3_s4_reference": dict(frozen_s5_campaign_summary["level3_s4_reference"]),
        "level3_s5_reference": {
            "campaign_id": frozen_s5_campaign_summary["campaign_id"],
            "manifest_fingerprint": frozen_s5_campaign_summary["manifest_fingerprint"],
            "repository_commit": frozen_s5_campaign_summary["repository_commit"],
            "frozen_preregistration_commit": frozen_s5_campaign_summary["frozen_preregistration_commit"],
        },
        "geometries": [
            geometry_s6_comparison_payload(
                comparison.geometry, comparison, frozen_s5_geometry_entry=frozen_by_geometry[comparison.geometry]
            )
            for comparison in sorted(geometry_comparisons, key=lambda comparison: comparison.geometry)
        ],
    }
    validate_campaign_summary_document(document)
    return document
