"""Deterministic Level2 campaign-summary and case-result serialization.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE (campaign-summary) and
L2-E2-CASE-RESULT-AND-END-TO-END-RUNNER (case-result). Converts already-
computed, already-validated D2/D3/D4 objects (adapter.MultipletProfileEntry,
orchestration.CaseMetricAnalysis, orchestration.PrimaryInterSComparison,
orchestration.ControlMetricAnalysis, execution.CaseExecutionResult,
execution.GeometryComparison) into JSON-compatible dicts, and validates
the result against schemas/level2/case-result-v1.schema.json /
schemas/level2/campaign-summary-v1.schema.json. This module performs no
scientific computation and never recomputes anything: every value it
emits was already produced by metrics.py/profiles.py/orchestration.py/
execution.py/adapter.py.

case_result_payload consumes entry.c_tt_conn/entry.rho_qq (retained
since lot L2-E1-RAW-OBSERVABLE-RETENTION) directly -- never a second,
independently recomputed copy -- and refuses (ValueError) any entry
whose c_tt_conn/rho_qq is still None: the None default on
MultipletProfileEntry exists only for pre-L2-E1 synthetic fixtures
outside the normative path (test_orchestration.py,
test_level2_serialization.py's own campaign-summary-only fixtures,
scripts/level2_campaign/test_gates.py), never for a case actually
destined for case-result persistence.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from cosmobox.level2 import metrics, orchestration, profiles
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import CaseExecutionResult, GeometryComparison

SCHEMA_VERSION = "level2-campaign-summary-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level2" / "campaign-summary-v1.schema.json"

CASE_RESULT_SCHEMA_VERSION = "level2-case-result-v1"
_CASE_RESULT_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level2" / "case-result-v1.schema.json"


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
# Case-result payloads
# ---------------------------------------------------------------------------


def numerical_guard_reference_payload(*, guard_m_tt: float, guard_r_eff: float, guard_scope: str) -> dict:
    """Plain scalars in, plain dict out -- deliberately not typed against
    experiments.level2.manifest.NumericalGuardReference: src/cosmobox
    never imports from experiments/ (a one-directional layering already
    respected throughout this project), so callers under scripts/ pass
    manifest.numerical_guard_reference's three fields individually."""
    return {"guard_m_tt": guard_m_tt, "guard_r_eff": guard_r_eff, "guard_scope": guard_scope}


def multiplet_entry_payload(entry: MultipletProfileEntry) -> dict:
    """One multiplet's full case-result entry: the D1 scalar metrics
    (reusing available_payload for r_eff/m_qq, exactly like
    case_metric_analysis_payload does) plus the retained raw source
    observables. Raises ValueError if entry.c_tt_conn or entry.rho_qq is
    still None -- a case-result entry must always carry its raw source
    observables (C_TT_CONN_PERSISTENCE=REQUIRED, RHO_QQ_PERSISTENCE=
    REQUIRED); the None default exists only for pre-L2-E1 synthetic
    fixtures outside this normative path.

    rho_qq is emitted in (i, j) sorted order via the plain nested loop
    below -- never via arbitrary dict iteration order -- matching the
    schema's own recommended deterministic ordering.
    """
    if not isinstance(entry, MultipletProfileEntry):
        raise ValueError(f"expected a MultipletProfileEntry, got {type(entry)}")
    if entry.c_tt_conn is None or entry.rho_qq is None:
        raise ValueError(
            "case-result serialization requires entry.c_tt_conn and entry.rho_qq to be present (not None); "
            "got c_tt_conn=None or rho_qq=None on a MultipletProfileEntry destined for case-result persistence"
        )
    n = entry.c_tt_conn.shape[0]
    return {
        "energy": entry.energy,
        "multiplicity": entry.multiplicity,
        "epsilon": entry.epsilon,
        "q_start": entry.q_start,
        "q_end": entry.q_end,
        "q_midpoint": entry.q_midpoint,
        "m_tt": entry.m_tt,
        "r_eff": available_payload(entry.r_eff),
        "a_qq": entry.a_qq,
        "m_qq": available_payload(entry.m_qq),
        "c_tt_conn": entry.c_tt_conn.tolist(),
        "rho_qq": [
            {"i": i, "j": j, "value": entry.rho_qq[(i, j)].value, "null_reason": entry.rho_qq[(i, j)].null_reason}
            for i in range(n)
            for j in range(n)
            if i != j
        ],
    }


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
    """The complete case-result document for one (geometry, spin) case,
    validated against schemas/level2/case-result-v1.schema.json before
    being returned. full_spectrum/solver_method/window_truncated/
    partial_subspace_count are emitted as their frozen constants (True,
    "dense", False, 0), never read from `result`: CaseExecutionResult
    carries no solver metadata (execution.run_case discards it after
    deriving the four metric analyses), and a successfully returned
    CaseExecutionResult can only ever have those exact values by
    construction of execution.run_case itself (see
    scripts/level2_campaign/gates.py's own docstring for the full
    argument) -- this is a restatement of an already-established
    invariant, not a new one asserted here for the first time.
    """
    if not isinstance(result, CaseExecutionResult):
        raise ValueError(f"expected a CaseExecutionResult, got {type(result)}")

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
    repository: str,
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
        "repository": repository,
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
