"""Strict Python -> JSON conversion and Draft 2020-12 validation against
schemas/level1/correlators-v2.schema.json. Level1B lot 1B-7.

This module performs NO scientific computation. It converts already-typed,
already-validated result objects (results.ResultRecord and its payload)
into a JSON-compatible dict, applies domain checks that JSON Schema alone
cannot express (a closed null_reason set per observable_kind -- never a
generic "any string in the schema's overall enum" check), and validates
the result against the v2 schema as a final safety net, never the only
check. It never recomputes an observable, redoes a match, decides a
spectral status, invents a missing value, or produces a verdict absent
from the source RobustnessResult/MatchOutcome.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .diagnostics import HermitianRestrictedDiagnostics, NonHermitianRestrictedDiagnostics
from .flavor import FlavorCorrelatorMatrix
from .local_observables import NormalizedMoment
from .matching import MatchOutcome, SpectralGroupMatchKey, SymmetryLabel
from .orbits import OrbitComparabilityKey
from .results import (
    HamiltonianIdentity,
    OrbitResultPayload,
    Provenance,
    ResultRecord,
    ScientificIdentity,
    SpectralGroupIdentity,
)
from .robustness import RobustnessResult

SCHEMA_VERSION = "level1-correlators-v2"
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "level1" / "correlators-v2.schema.json"
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")

# Closed, per-observable_kind null_reason sets -- deliberately NOT a single
# shared set. A NormalizedMoment carries no information about which
# function produced it, so this table is the only place that knowledge is
# recorded; it must be updated by hand if a new normalized observable is
# introduced, never inferred generically from the schema's overall enum.
_NORMALIZED_OBSERVABLE_NULL_REASONS: dict[str, frozenset[str]] = {
    "rho_QQ": frozenset({"zero_local_charge_variance"}),
    "G_occ": frozenset({"normalization_denominator_below_floor"}),
    "gamma_O": frozenset({"normalization_denominator_below_floor"}),
}
_FLAVOR_NORMALIZED_NULL_REASONS: dict[str, frozenset[str]] = {
    "flavor_singular_value_ratio": frozenset({"normalization_denominator_below_floor"}),
}
_GAMMA_O_NULL_REASONS = frozenset({"normalization_denominator_below_floor"})


@lru_cache(maxsize=1)
def _load_schema() -> dict:
    with _SCHEMA_PATH.open() as handle:
        return json.load(handle)


def _validator() -> Draft202012Validator:
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


# ---------------------------------------------------------------------------
# Primitive conversions
# ---------------------------------------------------------------------------


def _finite_number(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    return value


def _complex_payload(value: complex) -> dict:
    value = complex(value)
    if not (math.isfinite(value.real) and math.isfinite(value.imag)):
        raise ValueError(f"complex value is not finite: {value}")
    return {"real": value.real, "imag": value.imag}


def _json_safe_hashable(value: object) -> object:
    """Converts the caller-supplied Hashable fields of OrbitComparabilityKey
    (spectral_group_key, hamiltonian_identity) to JSON. Their Python type
    is intentionally unconstrained upstream (matching.py/orbits.py), so
    only the safe, actually-used subset (str/int/float/bool/None/tuple,
    recursively) is accepted here -- anything else fails loudly rather
    than being silently stringified. A float is additionally required to
    be finite: NaN/Inf would otherwise slip through this function (JSON
    itself has no representation for them) and only be caught, much less
    clearly, by schema validation downstream -- or not at all, since the
    schema's untyped {} for these two fields does not constrain them.
    """
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"cannot represent non-finite float {value!r} as a JSON-safe value")
        return value
    if isinstance(value, tuple):
        return [_json_safe_hashable(item) for item in value]
    raise ValueError(f"cannot represent {value!r} ({type(value)}) as a JSON-safe value")


def _normalized_moment_payload(moment: NormalizedMoment, *, allowed_null_reasons: frozenset[str]) -> dict:
    if not isinstance(moment, NormalizedMoment):
        raise ValueError(f"expected a NormalizedMoment, got {type(moment)}")
    if moment.value is not None:
        return {"value": _finite_number(moment.value, "value"), "null_reason": None}
    if moment.null_reason not in allowed_null_reasons:
        raise ValueError(
            f"null_reason {moment.null_reason!r} is not among the reasons this observable may legitimately "
            f"produce: {sorted(allowed_null_reasons)}"
        )
    return {"value": None, "null_reason": moment.null_reason}


# ---------------------------------------------------------------------------
# Identity / provenance
# ---------------------------------------------------------------------------


def _hamiltonian_identity_payload(hamiltonian: HamiltonianIdentity) -> dict:
    return {
        "J": [_finite_number(value, "J[i]") for value in hamiltonian.J],
        "h_is_zero": hamiltonian.h_is_zero,
        "t": _finite_number(hamiltonian.t, "t"),
        "g_E": _finite_number(hamiltonian.g_E, "g_E"),
        "K": _finite_number(hamiltonian.K, "K"),
    }


def _spectral_group_identity_payload(group: SpectralGroupIdentity) -> dict:
    return {
        "status": group.status,
        "multiplicity": group.multiplicity,
        "twice_T": group.twice_T,
        "spectral_window_group_index": group.spectral_window_group_index,
        "representative_energy": _finite_number(group.representative_energy, "representative_energy"),
    }


def _identity_payload(identity: ScientificIdentity) -> dict:
    return {
        "geometry": identity.geometry,
        "spin": identity.spin,
        "n_flavors": identity.n_flavors,
        "hamiltonian": _hamiltonian_identity_payload(identity.hamiltonian),
        "sector": identity.sector,
        "spectral_group": _spectral_group_identity_payload(identity.spectral_group),
        "path": list(identity.path) if identity.path is not None else None,
        "flavor_component": identity.flavor_component,
        "normalization": identity.normalization,
    }


def _provenance_payload(provenance: Provenance) -> dict:
    return {
        "spectral_status": provenance.spectral_status,
        "source_type": provenance.source_type,
        "source_module": provenance.source_module,
        "match_status": provenance.match_status,
        "covariance_validated": provenance.covariance_validated,
        "scientific_seed": provenance.scientific_seed,
        "solver_seed": provenance.solver_seed,
        "validation_rotation_seed": provenance.validation_rotation_seed,
    }


# ---------------------------------------------------------------------------
# Payload conversions, one function per Python source type
# ---------------------------------------------------------------------------


def _hermitian_diagnostic_payload(diagnostic: HermitianRestrictedDiagnostics) -> dict:
    return {
        "operator_kind": "hermitian",
        "status": diagnostic.status,
        "trace": _finite_number(diagnostic.trace, "trace"),
        "eigenvalues": [_finite_number(value, "eigenvalues[i]") for value in diagnostic.eigenvalues],
        "minimum": _finite_number(diagnostic.minimum, "minimum"),
        "maximum": _finite_number(diagnostic.maximum, "maximum"),
        "spectral_range": _finite_number(diagnostic.spectral_range, "spectral_range"),
        "frobenius_norm": _finite_number(diagnostic.frobenius_norm, "frobenius_norm"),
        "hermiticity_defect": _finite_number(diagnostic.hermiticity_defect, "hermiticity_defect"),
    }


def _non_hermitian_diagnostic_payload(diagnostic: NonHermitianRestrictedDiagnostics) -> dict:
    return {
        "operator_kind": "non_hermitian",
        "status": diagnostic.status,
        "trace": _complex_payload(diagnostic.trace),
        "singular_values": [_finite_number(value, "singular_values[i]") for value in diagnostic.singular_values],
        "frobenius_norm": _finite_number(diagnostic.frobenius_norm, "frobenius_norm"),
    }


def _flavor_matrix_payload(matrix: FlavorCorrelatorMatrix) -> dict:
    rows = [[_complex_payload(value) for value in row] for row in matrix.matrix]
    return {"status": matrix.status, "matrix": rows}


def _symmetry_label_payload(label: SymmetryLabel) -> dict:
    if label.kind == "numeric":
        return {"kind": "numeric", "value": _complex_payload(label.value)}
    return {"kind": label.kind, "value": None}


def _matched_group_payload(key: SpectralGroupMatchKey) -> dict:
    return {
        "status": key.status,
        "multiplicity": key.multiplicity,
        "twice_T": key.twice_T,
        "translation_label": _symmetry_label_payload(key.translation_label),
        "reflection_label": _symmetry_label_payload(key.reflection_label),
    }


def _match_outcome_payload(outcome: MatchOutcome) -> dict:
    matched_group = _matched_group_payload(outcome.matched_group) if outcome.matched_group is not None else None
    return {"status": outcome.status, "matched_group": matched_group}


def _robustness_result_payload(result: RobustnessResult) -> dict:
    gamma_o = _normalized_moment_payload(result.gamma_o, allowed_null_reasons=_GAMMA_O_NULL_REASONS) if result.gamma_o is not None else None
    return {
        "verdict": result.verdict,
        "null_reason": result.null_reason,
        "gamma_o": gamma_o,
        "difference": _finite_number(result.difference, "difference") if result.difference is not None else None,
        "amplitude": _finite_number(result.amplitude, "amplitude") if result.amplitude is not None else None,
    }


def _orbit_comparability_key_payload(key: OrbitComparabilityKey) -> dict:
    return {
        "orbit_family": key.orbit_family,
        "path_length": key.path_length,
        "spectral_group_key": _json_safe_hashable(key.spectral_group_key),
        "status": key.status,
        "observable_kind": key.observable_kind,
        "normalization": key.normalization,
        "flavor_component": key.flavor_component,
        "hamiltonian_identity": _json_safe_hashable(key.hamiltonian_identity),
    }


def _orbit_result_payload(payload: OrbitResultPayload) -> dict:
    return {
        "orbit_mean": _complex_payload(payload.statistics.orbit_mean),
        "orbit_max_pairwise_spread": _finite_number(payload.statistics.orbit_max_pairwise_spread, "orbit_max_pairwise_spread"),
        "orbit_covariance_defect": _finite_number(payload.statistics.orbit_covariance_defect, "orbit_covariance_defect"),
        "comparability_key": _orbit_comparability_key_payload(payload.comparability_key),
        "element_count": payload.element_count,
    }


def _payload_json(record: ResultRecord) -> object:
    record_kind = record.record_kind
    observable_kind = record.observable_kind
    payload = record.payload

    if record_kind == "raw_observable":
        if observable_kind == "O_ij_raw":
            return _complex_payload(payload)
        return _finite_number(payload, observable_kind)

    if record_kind == "normalized_observable":
        return _normalized_moment_payload(payload, allowed_null_reasons=_NORMALIZED_OBSERVABLE_NULL_REASONS[observable_kind])

    if record_kind == "restricted_diagnostic":
        if isinstance(payload, HermitianRestrictedDiagnostics):
            return _hermitian_diagnostic_payload(payload)
        return _non_hermitian_diagnostic_payload(payload)

    if record_kind == "flavor_diagnostic":
        if observable_kind == "raw_G":
            return _flavor_matrix_payload(payload)
        if observable_kind == "flavor_singlet":
            return _complex_payload(payload)
        if observable_kind == "flavor_frobenius_squared":
            return _finite_number(payload, "flavor_frobenius_squared")
        if observable_kind == "flavor_singular_values":
            return [_finite_number(value, "flavor_singular_values[i]") for value in payload]
        return _normalized_moment_payload(payload, allowed_null_reasons=_FLAVOR_NORMALIZED_NULL_REASONS[observable_kind])

    if record_kind == "orbit_statistic":
        return _orbit_result_payload(payload)

    if record_kind == "symmetry_label":
        return _symmetry_label_payload(payload)

    if record_kind == "matching":
        return _match_outcome_payload(payload)

    if record_kind == "robustness":
        return _robustness_result_payload(payload)

    raise AssertionError(f"unreachable: record_kind {record_kind!r} already validated by results.ResultRecord")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def validate_document(document: dict) -> None:
    """Validate an already-built document dict against the v2 schema.
    Shared by serialize_result_record's own final check and by
    assembly.py, so schema-loading/validation logic exists in exactly
    one place. Raises ValueError (never lets a jsonschema exception type
    leak to callers that only expect ValueError) with every violation
    listed, not just the first one.
    """
    if not isinstance(document, dict):
        raise ValueError(f"document must be a dict, got {type(document)}")
    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise ValueError(f"document does not validate against {SCHEMA_VERSION}: {messages}")


def serialize_result_record(
    record: ResultRecord,
    *,
    repository_commit: str,
    manifest_fingerprint: str,
    campaign_id: str,
) -> dict:
    """The main entry point. Converts `record` (already fully validated
    by results.ResultRecord's own __post_init__) into a JSON-compatible
    dict, applies the closed per-observable_kind null_reason checks
    above, and validates the result against correlators-v2.schema.json
    via validate_document -- the schema is the final safety net, not the
    only check. Raises ValueError before ever reaching the schema if a
    domain-level invariant this schema cannot express is violated.
    """
    if not isinstance(record, ResultRecord):
        raise ValueError(f"record must be a ResultRecord, got {type(record)}")
    if not _COMMIT_PATTERN.match(repository_commit):
        raise ValueError(f"repository_commit must be a 40-character lowercase hex string, got {repository_commit!r}")
    if not manifest_fingerprint:
        raise ValueError("manifest_fingerprint must be non-empty")
    if not campaign_id:
        raise ValueError("campaign_id must be non-empty")

    document = {
        "schema_version": SCHEMA_VERSION,
        "repository_commit": repository_commit,
        "manifest_fingerprint": manifest_fingerprint,
        "campaign_id": campaign_id,
        "identity": _identity_payload(record.identity),
        "provenance": _provenance_payload(record.provenance),
        "record_kind": record.record_kind,
        "observable_kind": record.observable_kind,
        "payload": _payload_json(record),
    }

    validate_document(document)
    return document
