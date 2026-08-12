"""Deterministic Level2 campaign-summary serialization.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE. Converts already-computed, already-
validated D3/D4 objects (orchestration.CaseMetricAnalysis,
orchestration.PrimaryInterSComparison, orchestration.ControlMetricAnalysis,
execution.GeometryComparison) into JSON-compatible dicts, and validates
the result against schemas/level2/campaign-summary-v1.schema.json. This
module performs no scientific computation and never recomputes anything:
every value it emits was already produced by metrics.py/profiles.py/
orchestration.py/execution.py.

CASE_RESULT_SERIALIZATION = NOT_IMPLEMENTED_IN_THIS_LOT: a case result
requires the full C_TT_conn matrix and rho_QQ ordered-pair entries per
multiplet (schemas/level2/case-result-v1.schema.json,
C_TT_CONN_PERSISTENCE=REQUIRED / RHO_QQ_PERSISTENCE=REQUIRED,
docs/governance/current-task.md), which
cosmobox.level2.adapter.MultipletProfileEntry and
cosmobox.level2.execution.CaseExecutionResult do not currently carry
through from adapter.assemble_c_tt_conn/assemble_rho_qq. Extending them
is a D2/D4 change explicitly deferred to a separate, authorized
corrective lot (see the L2-E-CAMPAIGN-INFRASTRUCTURE delivery report) --
this module never recomputes those observables independently to work
around that gap.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from cosmobox.level2 import metrics, orchestration, profiles
from cosmobox.level2.execution import GeometryComparison

SCHEMA_VERSION = "level2-campaign-summary-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level2" / "campaign-summary-v1.schema.json"


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = _load_schema()
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


# ---------------------------------------------------------------------------
# Primitive payloads
# ---------------------------------------------------------------------------


def available_payload(value: metrics.Available) -> dict:
    if not isinstance(value, metrics.Available):
        raise ValueError(f"expected an Available, got {type(value)}")
    return {"value": value.value, "reason": value.reason}


def regime_mean_payload(regime_mean: profiles.RegimeMean) -> dict:
    if not isinstance(regime_mean, profiles.RegimeMean):
        raise ValueError(f"expected a RegimeMean, got {type(regime_mean)}")
    return {
        "value": regime_mean.value,
        "reason": regime_mean.reason,
        "evaluable_weight_fraction": regime_mean.evaluable_weight_fraction,
    }


def case_metric_analysis_payload(analysis: orchestration.CaseMetricAnalysis) -> dict:
    """low/mid/high + the three descriptive contrasts -- the
    "regime_analysis" shape shared by schemas/level2/case-result-v1 and
    reused here for the control-comparison payload below."""
    if not isinstance(analysis, orchestration.CaseMetricAnalysis):
        raise ValueError(f"expected a CaseMetricAnalysis, got {type(analysis)}")
    return {
        "low": regime_mean_payload(analysis.low),
        "mid": regime_mean_payload(analysis.mid),
        "high": regime_mean_payload(analysis.high),
        "delta_hl": available_payload(analysis.delta_hl),
        "delta_ml": available_payload(analysis.delta_ml),
        "delta_hm": available_payload(analysis.delta_hm),
    }


# ---------------------------------------------------------------------------
# Campaign-summary payloads
# ---------------------------------------------------------------------------


def primary_inter_s_comparison_payload(comparison: orchestration.PrimaryInterSComparison) -> dict:
    if not isinstance(comparison, orchestration.PrimaryInterSComparison):
        raise ValueError(f"expected a PrimaryInterSComparison, got {type(comparison)}")
    return {
        "metric": comparison.metric,
        "delta_hl_s2": available_payload(comparison.delta_hl_s2),
        "delta_hl_s3": available_payload(comparison.delta_hl_s3),
        "taxonomy": comparison.classification.taxonomy,
        "direction_s2": comparison.classification.direction_s2,
        "direction_s3": comparison.classification.direction_s3,
        "c_x_23": available_payload(comparison.c_x_23),
        "d_x_23": available_payload(comparison.d_x_23),
    }


def control_metric_analysis_payload(comparison: orchestration.ControlMetricAnalysis) -> dict:
    """Deliberately emits no taxonomy/c_x_23/d_x_23 key -- there is
    nothing on ControlMetricAnalysis to read one from. Structurally
    mirrors the schema's controlComparison $def (additionalProperties:
    false), not merely a documentary omission."""
    if not isinstance(comparison, orchestration.ControlMetricAnalysis):
        raise ValueError(f"expected a ControlMetricAnalysis, got {type(comparison)}")
    return {
        "metric": comparison.metric,
        "delta_hl_s2": available_payload(comparison.analysis_s2.delta_hl),
        "delta_ml_s2": available_payload(comparison.analysis_s2.delta_ml),
        "delta_hm_s2": available_payload(comparison.analysis_s2.delta_hm),
        "delta_hl_s3": available_payload(comparison.analysis_s3.delta_hl),
        "delta_ml_s3": available_payload(comparison.analysis_s3.delta_ml),
        "delta_hm_s3": available_payload(comparison.analysis_s3.delta_hm),
    }


def geometry_comparison_payload(comparison: GeometryComparison) -> dict:
    if not isinstance(comparison, GeometryComparison):
        raise ValueError(f"expected a GeometryComparison, got {type(comparison)}")
    return {
        "geometry": comparison.geometry,
        "m_tt": primary_inter_s_comparison_payload(comparison.m_tt),
        "r_eff": primary_inter_s_comparison_payload(comparison.r_eff),
        "a_qq": control_metric_analysis_payload(comparison.a_qq),
        "m_qq": control_metric_analysis_payload(comparison.m_qq),
    }


def campaign_summary_payload(
    geometry_comparisons: Sequence[GeometryComparison],
    *,
    campaign_id: str,
    manifest_fingerprint: str,
    repository_commit: str,
    branch: str,
    frozen_preregistration_commit: str,
) -> dict:
    """The complete campaign-summary document, validated against
    schemas/level2/campaign-summary-v1.schema.json before being returned.
    Requires exactly the three frozen geometries, each exactly once --
    never a partial or duplicated set (campaign_status is always
    "COMPLETE": this function is only ever called once completeness has
    already been established by the caller, per PARTIAL_CAMPAIGN_
    COMPLETE_STATUS = FORBIDDEN)."""
    geometries = {comparison.geometry for comparison in geometry_comparisons}
    if geometries != {"triangle", "ring4", "ring5"} or len(geometry_comparisons) != 3:
        raise ValueError(
            f"geometry_comparisons must contain exactly one comparison each for "
            f"triangle, ring4, ring5, got {[comparison.geometry for comparison in geometry_comparisons]}"
        )

    document = {
        "schema_version": SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "manifest_fingerprint": manifest_fingerprint,
        "repository_commit": repository_commit,
        "branch": branch,
        "frozen_preregistration_commit": frozen_preregistration_commit,
        "campaign_status": "COMPLETE",
        "geometries": [
            geometry_comparison_payload(comparison)
            for comparison in sorted(geometry_comparisons, key=lambda comparison: comparison.geometry)
        ],
    }
    validate_campaign_summary_document(document)
    return document
