from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from cosmobox.level1.diagnostics import HermitianRestrictedDiagnostics, NonHermitianRestrictedDiagnostics
from cosmobox.level1.flavor import FlavorCorrelatorMatrix
from cosmobox.level1.local_observables import NormalizedMoment
from cosmobox.level1.matching import (
    EXACT_LABEL_MATCH,
    NOT_APPLICABLE,
    NUMERIC,
    TARGET_GROUP_NOT_IN_WINDOW,
    UNAVAILABLE,
    MatchOutcome,
    SpectralGroupMatchKey,
    SymmetryLabel,
)
from cosmobox.level1.orbits import OrbitComparabilityKey, OrbitElement, ValidatedOrbit, _VALIDATION_TOKEN
from cosmobox.level1.restricted import COMPLETE_MULTIPLET
from cosmobox.level1.results import (
    HamiltonianIdentity,
    ScientificIdentity,
    SpectralGroupIdentity,
    build_orbit_result_payload,
)
from cosmobox.level1.results import build_result_record as _build_result_record_impl
from cosmobox.level1.robustness import INDETERMINATE, ROBUST, RobustnessResult
from cosmobox.level1.serialization import SCHEMA_VERSION, _load_schema, serialize_result_record

REPO_COMMIT = "a" * 40
_TEST_SCIENTIFIC_SEED = 1001
_TEST_SOLVER_SEED = 2002


def build_result_record(*args, **kwargs):
    """Shadows cosmobox.level1.results.build_result_record with fixed
    default seeds -- see tests/level1/test_results.py's own copy of this
    wrapper for the rationale."""
    kwargs.setdefault("scientific_seed", _TEST_SCIENTIFIC_SEED)
    kwargs.setdefault("solver_seed", _TEST_SOLVER_SEED)
    return _build_result_record_impl(*args, **kwargs)


def _hamiltonian(**overrides) -> HamiltonianIdentity:
    defaults = dict(J=(1.0, 1.0, 1.0), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)
    defaults.update(overrides)
    return HamiltonianIdentity(**defaults)


def _identity(**overrides) -> ScientificIdentity:
    defaults = dict(
        geometry="triangle",
        spin=2,
        n_flavors=2,
        hamiltonian=_hamiltonian(),
        sector="default",
        spectral_group=SpectralGroupIdentity(status=COMPLETE_MULTIPLET, multiplicity=2, twice_T=1),
        path=None,
        flavor_component=None,
        normalization=None,
    )
    defaults.update(overrides)
    return ScientificIdentity(**defaults)


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_load_schema())


# ---------------------------------------------------------------------------
# jsonschema / Draft 2020-12
# ---------------------------------------------------------------------------


def test_jsonschema_is_installed_and_supports_draft202012() -> None:
    assert version("jsonschema")
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_v1_is_untouched_and_kept_as_historical() -> None:
    v1_path = Path(__file__).resolve().parents[2] / "schemas" / "level1" / "correlators-v1.schema.json"
    with v1_path.open() as handle:
        v1 = json.load(handle)
    assert v1["$id"].endswith("level1-correlators-v1.schema.json")


# ---------------------------------------------------------------------------
# Root / nested additionalProperties: false
# ---------------------------------------------------------------------------


def test_root_rejects_unknown_property() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    document["unexpected_field"] = True
    errors = list(_validator().iter_errors(document))
    assert errors


def test_identity_rejects_unknown_property() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    document["identity"]["unexpected"] = 1
    errors = list(_validator().iter_errors(document))
    assert errors


def test_payload_rejects_unknown_property() -> None:
    record = build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", HermitianRestrictedDiagnostics(
        status=COMPLETE_MULTIPLET, trace=4.0, eigenvalues=(1.0, 3.0), minimum=1.0, maximum=3.0,
        spectral_range=2.0, frobenius_norm=10.0**0.5, hermiticity_defect=0.0,
    ))
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    document["payload"]["extra"] = 1
    errors = list(_validator().iter_errors(document))
    assert errors


# ---------------------------------------------------------------------------
# Complex numbers, matrices, arrays
# ---------------------------------------------------------------------------


def test_raw_observable_complex_shape() -> None:
    record = build_result_record(_identity(), "raw_observable", "O_ij_raw", 1.5 - 2.5j)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"] == {"real": 1.5, "imag": -2.5}
    assert not list(_validator().iter_errors(document))


def test_flavor_matrix_is_exactly_2x2() -> None:
    matrix = FlavorCorrelatorMatrix(matrix=np.array([[1 + 1j, 2 + 0j], [0 + 0j, 3 - 1j]]), status=COMPLETE_MULTIPLET)
    record = build_result_record(_identity(), "flavor_diagnostic", "raw_G", matrix)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert len(document["payload"]["matrix"]) == 2
    assert all(len(row) == 2 for row in document["payload"]["matrix"])
    assert not list(_validator().iter_errors(document))


def test_flavor_matrix_wrong_shape_fails_schema_validation() -> None:
    document = serialize_result_record(
        build_result_record(_identity(), "flavor_diagnostic", "raw_G",
                     FlavorCorrelatorMatrix(matrix=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)),
        repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1",
    )
    document["payload"]["matrix"] = document["payload"]["matrix"][:1]  # only 1 row now
    errors = list(_validator().iter_errors(document))
    assert errors


def test_eigenvalues_array_round_trips() -> None:
    diag = HermitianRestrictedDiagnostics(status=COMPLETE_MULTIPLET, trace=4.0, eigenvalues=(1.0, 3.0), minimum=1.0, maximum=3.0, spectral_range=2.0, frobenius_norm=10.0**0.5, hermiticity_defect=0.0)
    record = build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", diag)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["eigenvalues"] == [1.0, 3.0]


def test_singular_values_array_round_trips() -> None:
    diag = NonHermitianRestrictedDiagnostics(status=COMPLETE_MULTIPLET, trace=1 + 1j, singular_values=(3.0, 1.0), frobenius_norm=10.0**0.5)
    record = build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", diag)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["singular_values"] == [3.0, 1.0]


# ---------------------------------------------------------------------------
# value / null_reason exclusion, closed reasons per source
# ---------------------------------------------------------------------------


def test_normalized_moment_value_and_null_reason_are_mutually_exclusive_in_schema() -> None:
    record = build_result_record(_identity(), "normalized_observable", "rho_QQ", NormalizedMoment(value=0.3, null_reason=None))
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    document["payload"]["null_reason"] = "zero_local_charge_variance"  # forge both present
    errors = list(_validator().iter_errors(document))
    assert errors


def test_rho_qq_only_accepts_zero_local_charge_variance() -> None:
    record = build_result_record(_identity(), "normalized_observable", "rho_QQ", NormalizedMoment(value=None, null_reason="zero_local_charge_variance"))
    serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")  # OK


def test_rho_qq_rejects_a_reason_belonging_to_a_different_source() -> None:
    record = build_result_record(_identity(), "normalized_observable", "rho_QQ", NormalizedMoment(value=None, null_reason="normalization_denominator_below_floor"))
    with pytest.raises(ValueError, match="not among the reasons"):
        serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")


def test_gamma_o_only_accepts_normalization_denominator_below_floor() -> None:
    record = build_result_record(_identity(), "normalized_observable", "gamma_O", NormalizedMoment(value=None, null_reason="normalization_denominator_below_floor"))
    serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")


def test_gamma_o_rejects_zero_local_charge_variance() -> None:
    record = build_result_record(_identity(), "normalized_observable", "gamma_O", NormalizedMoment(value=None, null_reason="zero_local_charge_variance"))
    with pytest.raises(ValueError, match="not among the reasons"):
        serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")


# ---------------------------------------------------------------------------
# SymmetryLabel -- three states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "value"),
    [(NUMERIC, 1 + 2j), (NOT_APPLICABLE, None), (UNAVAILABLE, None)],
)
def test_symmetry_label_three_states_validate(kind: str, value) -> None:
    record = build_result_record(_identity(), "symmetry_label", "translation_character", SymmetryLabel(kind=kind, value=value))
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["kind"] == kind


def test_symmetry_label_unavailable_is_not_a_null_reason_anywhere() -> None:
    schema = _load_schema()
    null_reason_enum = schema["$defs"]["nullReason"]["enum"]
    assert "unavailable" not in null_reason_enum
    robustness_null_reason_enum = schema["$defs"]["robustnessResult"]["properties"]["null_reason"]["enum"]
    assert "unavailable" not in robustness_null_reason_enum


# ---------------------------------------------------------------------------
# Hermitian / non-Hermitian diagnostics
# ---------------------------------------------------------------------------


def test_hermitian_diagnostic_validates() -> None:
    diag = HermitianRestrictedDiagnostics(status=COMPLETE_MULTIPLET, trace=4.0, eigenvalues=(1.0, 3.0), minimum=1.0, maximum=3.0, spectral_range=2.0, frobenius_norm=10.0**0.5, hermiticity_defect=0.0)
    record = build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", diag)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["operator_kind"] == "hermitian"


def test_non_hermitian_diagnostic_validates_and_has_no_eigenvalue_field() -> None:
    diag = NonHermitianRestrictedDiagnostics(status=COMPLETE_MULTIPLET, trace=1 + 1j, singular_values=(3.0, 1.0), frobenius_norm=10.0**0.5)
    record = build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", diag)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert "eigenvalues" not in document["payload"]
    assert "eigenvectors" not in document["payload"]
    assert "schur" not in document["payload"]


def test_non_hermitian_diagnostic_schema_forbids_eigenvalues_field() -> None:
    schema = _load_schema()
    non_hermitian_properties = schema["$defs"]["nonHermitianDiagnostic"]["properties"]
    assert "eigenvalues" not in non_hermitian_properties
    assert schema["$defs"]["nonHermitianDiagnostic"]["additionalProperties"] is False


# ---------------------------------------------------------------------------
# Orbit -- validated pipeline only
# ---------------------------------------------------------------------------


def test_orbit_statistic_from_validated_orbit_validates() -> None:
    key = OrbitComparabilityKey(orbit_family="fam", path_length=1, spectral_group_key="g0", status=COMPLETE_MULTIPLET, observable_kind="O_ij_raw", normalization="raw_G", flavor_component="alpha0_beta1", hamiltonian_identity="ref")
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j), OrbitElement(key, 1 + 1j)), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    identity = _identity(normalization="raw_G", flavor_component="alpha0_beta1")
    record = build_result_record(identity, "orbit_statistic", "O_ij_raw", payload)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["element_count"] == 2


# ---------------------------------------------------------------------------
# Matching -- exact and non-exact
# ---------------------------------------------------------------------------


def test_matching_exact_carries_matched_group() -> None:
    matched = SpectralGroupMatchKey(geometry="triangle", hamiltonian_identity_without_spin="ref", sector_identity="default", status=COMPLETE_MULTIPLET, multiplicity=2, twice_T=1, translation_label=SymmetryLabel(NUMERIC, 1 + 0j), reflection_label=SymmetryLabel(NOT_APPLICABLE, None))
    record = build_result_record(_identity(), "matching", "gamma_O", MatchOutcome(EXACT_LABEL_MATCH, matched))
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["matched_group"] is not None


def test_matching_non_exact_forbids_matched_group_in_schema() -> None:
    record = build_result_record(_identity(), "matching", "gamma_O", MatchOutcome(TARGET_GROUP_NOT_IN_WINDOW, None))
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["matched_group"] is None
    # forge a matched_group on a non-exact status -- schema must reject it
    document["payload"]["matched_group"] = {
        "status": "complete_multiplet", "multiplicity": 2, "twice_T": 1,
        "translation_label": {"kind": "not_applicable", "value": None},
        "reflection_label": {"kind": "not_applicable", "value": None},
    }
    errors = list(_validator().iter_errors(document))
    assert errors


# ---------------------------------------------------------------------------
# Robustness -- definitive and indeterminate
# ---------------------------------------------------------------------------


def test_robustness_definitive_validates() -> None:
    result = RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    record = build_result_record(_identity(), "robustness", "gamma_O", result)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["verdict"] == "robust"


def test_robustness_indeterminate_validates() -> None:
    result = RobustnessResult(verdict=INDETERMINATE, null_reason=TARGET_GROUP_NOT_IN_WINDOW, gamma_o=None, difference=None, amplitude=None)
    record = build_result_record(_identity(), "robustness", "gamma_O", result)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["payload"]["verdict"] == "indeterminate"


def test_robustness_definitive_verdict_with_null_reason_fails_schema() -> None:
    document = serialize_result_record(
        build_result_record(_identity(), "robustness", "gamma_O", RobustnessResult(ROBUST, None, NormalizedMoment(0.01, None), 0.01, 1.0)),
        repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1",
    )
    document["payload"]["null_reason"] = "target_group_not_in_window"
    errors = list(_validator().iter_errors(document))
    assert errors


def test_robustness_ambiguous_match_forbids_gamma_o_in_schema() -> None:
    document = serialize_result_record(
        build_result_record(_identity(), "robustness", "gamma_O", RobustnessResult(INDETERMINATE, TARGET_GROUP_NOT_IN_WINDOW, None, None, None)),
        repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1",
    )
    document["payload"]["gamma_o"] = {"value": 0.5, "null_reason": None}
    document["payload"]["difference"] = 0.5
    document["payload"]["amplitude"] = 1.0
    errors = list(_validator().iter_errors(document))
    assert errors


# ---------------------------------------------------------------------------
# Non-finite rejection
# ---------------------------------------------------------------------------


def test_non_finite_payload_rejected_before_schema() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", float("nan"))
    with pytest.raises(ValueError, match="finite"):
        serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")


def test_non_finite_J_rejected_at_identity_construction() -> None:
    with pytest.raises(ValueError, match="finite"):
        _identity(hamiltonian=_hamiltonian(J=(float("inf"),)))


# ---------------------------------------------------------------------------
# repository_commit / metadata validation
# ---------------------------------------------------------------------------


def test_serialize_rejects_malformed_repository_commit() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    with pytest.raises(ValueError, match="repository_commit"):
        serialize_result_record(record, repository_commit="not-a-commit", manifest_fingerprint="fp", campaign_id="c1")


def test_serialize_rejects_empty_campaign_id() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    with pytest.raises(ValueError, match="campaign_id"):
        serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="")


def test_schema_version_constant_matches_document() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["schema_version"] == SCHEMA_VERSION == "level1-correlators-v2"


# ---------------------------------------------------------------------------
# Schema-level record_kind / observable_kind pairs -- not just the Python
# table: a manually forged document with a forbidden pair must be rejected
# by Draft202012Validator directly, covering all 8 record_kind categories.
# ---------------------------------------------------------------------------


def _valid_document_for(record_kind: str) -> dict:
    builders = {
        "raw_observable": lambda: build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5),
        "normalized_observable": lambda: build_result_record(_identity(), "normalized_observable", "rho_QQ", NormalizedMoment(0.1, None)),
        "restricted_diagnostic": lambda: build_result_record(
            _identity(), "restricted_diagnostic", "C_QQ_raw",
            HermitianRestrictedDiagnostics(status=COMPLETE_MULTIPLET, trace=4.0, eigenvalues=(1.0, 3.0), minimum=1.0, maximum=3.0, spectral_range=2.0, frobenius_norm=10.0**0.5, hermiticity_defect=0.0),
        ),
        "flavor_diagnostic": lambda: build_result_record(_identity(), "flavor_diagnostic", "flavor_singlet", 1 + 1j),
        "orbit_statistic": lambda: build_result_record(
            _identity(normalization="raw_G", flavor_component="alpha0_beta1"), "orbit_statistic", "O_ij_raw",
            build_orbit_result_payload(ValidatedOrbit(
                key=(key := OrbitComparabilityKey(orbit_family="fam", path_length=1, spectral_group_key="g0", status=COMPLETE_MULTIPLET, observable_kind="O_ij_raw", normalization="raw_G", flavor_component="alpha0_beta1", hamiltonian_identity="ref")),
                elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN,
            )),
        ),
        "symmetry_label": lambda: build_result_record(_identity(), "symmetry_label", "translation_character", SymmetryLabel(NOT_APPLICABLE, None)),
        "matching": lambda: build_result_record(_identity(), "matching", "gamma_O", MatchOutcome(TARGET_GROUP_NOT_IN_WINDOW, None)),
        "robustness": lambda: build_result_record(_identity(), "robustness", "gamma_O", RobustnessResult(ROBUST, None, NormalizedMoment(0.01, None), 0.01, 1.0)),
    }
    record = builders[record_kind]()
    return serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")


@pytest.mark.parametrize(
    ("record_kind", "forbidden_observable_kind"),
    [
        ("raw_observable", "flavor_singlet"),
        ("normalized_observable", "raw_G"),
        ("restricted_diagnostic", "translation_character"),
        ("flavor_diagnostic", "rho_QQ"),
        ("orbit_statistic", "translation_character"),
        ("symmetry_label", "raw_G"),
        ("matching", "not_a_real_observable_kind"),
        ("robustness", "not_a_real_observable_kind"),
    ],
)
def test_schema_rejects_forbidden_record_kind_observable_kind_pair(record_kind: str, forbidden_observable_kind: str) -> None:
    document = _valid_document_for(record_kind)
    document["observable_kind"] = forbidden_observable_kind
    errors = list(_validator().iter_errors(document))
    assert errors, f"expected {record_kind!r}/{forbidden_observable_kind!r} to be rejected by the schema"


def test_schema_covers_all_eight_record_kinds_for_the_pair_test() -> None:
    tested = {"raw_observable", "normalized_observable", "restricted_diagnostic", "flavor_diagnostic", "orbit_statistic", "symmetry_label", "matching", "robustness"}
    from cosmobox.level1.results import RECORD_KINDS

    assert tested == set(RECORD_KINDS)


# ---------------------------------------------------------------------------
# _json_safe_hashable -- non-finite floats rejected explicitly
# ---------------------------------------------------------------------------


def test_json_safe_hashable_rejects_nan_in_spectral_group_key() -> None:
    from cosmobox.level1.serialization import _json_safe_hashable

    with pytest.raises(ValueError, match="finite"):
        _json_safe_hashable(float("nan"))


def test_json_safe_hashable_rejects_inf_in_spectral_group_key() -> None:
    from cosmobox.level1.serialization import _json_safe_hashable

    with pytest.raises(ValueError, match="finite"):
        _json_safe_hashable(float("inf"))


def test_json_safe_hashable_rejects_nan_nested_in_tuple() -> None:
    from cosmobox.level1.serialization import _json_safe_hashable

    with pytest.raises(ValueError, match="finite"):
        _json_safe_hashable((0, float("nan"), 2))


def test_orbit_comparability_key_with_non_finite_hashable_is_rejected_end_to_end() -> None:
    key = OrbitComparabilityKey(orbit_family="fam", path_length=1, spectral_group_key=(0, float("nan")), status=COMPLETE_MULTIPLET, observable_kind="O_ij_raw", normalization="raw_G", flavor_component="alpha0_beta1", hamiltonian_identity="ref")
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    identity = _identity(normalization="raw_G", flavor_component="alpha0_beta1")
    record = build_result_record(identity, "orbit_statistic", "O_ij_raw", payload)
    with pytest.raises(ValueError, match="finite"):
        serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")


# ---------------------------------------------------------------------------
# ROBUSTNESS_OBSERVABLE_KINDS -- schema enforces the SAME closed list,
# tested via manually-constructed JSON documents (no ResultRecord at all).
# path_phase_coherence stays frozen by D013 as a secondary robustness
# observable, but is absent from this enum until a module computes it.
# ---------------------------------------------------------------------------


def _manual_robustness_document(observable_kind: str) -> dict:
    return {
        "schema_version": "level1-correlators-v2",
        "repository_commit": REPO_COMMIT,
        "manifest_fingerprint": "fp",
        "campaign_id": "c1",
        "identity": {
            "geometry": "triangle",
            "spin": 2,
            "n_flavors": 2,
            "hamiltonian": {"J": [1.0], "h_is_zero": True, "t": 1.0, "g_E": 1.0, "K": 1.0},
            "sector": "default",
            "spectral_group": {"status": "complete_multiplet", "multiplicity": 2, "twice_T": 1},
            "path": None,
            "flavor_component": None,
            "normalization": None,
        },
        "provenance": {
            "spectral_status": "complete_multiplet",
            "source_type": "RobustnessResult",
            "source_module": "cosmobox.level1.robustness",
            "match_status": None,
            "covariance_validated": None,
            "scientific_seed": 1001,
            "solver_seed": 2002,
            "validation_rotation_seed": None,
        },
        "record_kind": "robustness",
        "observable_kind": observable_kind,
        "payload": {
            "verdict": "robust",
            "null_reason": None,
            "gamma_o": {"value": 0.01, "null_reason": None},
            "difference": 0.01,
            "amplitude": 1.0,
        },
    }


@pytest.mark.parametrize("observable_kind", ["gamma_O", "G_occ", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio"])
def test_schema_accepts_manually_built_robustness_document_for_each_allowed_pair(observable_kind: str) -> None:
    document = _manual_robustness_document(observable_kind)
    errors = list(_validator().iter_errors(document))
    assert errors == [], f"expected robustness/{observable_kind!r} to validate, got {errors}"


@pytest.mark.parametrize(
    "observable_kind",
    [
        "C_QQ_raw",
        "C_QQ_conn",
        "C_TT_raw",
        "O_ij_raw",
        "raw_G",
        "flavor_singular_values",
        "flavor_casimir_label",
        "translation_character",
    ],
)
def test_schema_rejects_manually_built_robustness_document_for_each_forbidden_pair(observable_kind: str) -> None:
    document = _manual_robustness_document(observable_kind)
    errors = list(_validator().iter_errors(document))
    assert errors, f"expected robustness/{observable_kind!r} to be rejected by the schema"


def test_schema_robustness_enum_excludes_path_phase_coherence() -> None:
    schema = _load_schema()
    for entry in schema["allOf"]:
        if entry["if"]["properties"]["record_kind"]["const"] == "robustness" and "observable_kind" in entry["then"]["properties"]:
            enum = entry["then"]["properties"]["observable_kind"]["enum"]
            assert "path_phase_coherence" not in enum
            assert set(enum) == {"gamma_O", "G_occ", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio"}
            return
    pytest.fail("no robustness observable_kind enum block found in the schema")


# ---------------------------------------------------------------------------
# provenance.scientific_seed / solver_seed / validation_rotation_seed
# (Level1B lot 1B-8) -- required at the schema level too, not just Python.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_key", ["scientific_seed", "solver_seed", "validation_rotation_seed"])
def test_schema_rejects_provenance_missing_seed_key(missing_key: str) -> None:
    document = _manual_robustness_document("gamma_O")
    del document["provenance"][missing_key]
    errors = list(_validator().iter_errors(document))
    assert errors, f"expected a missing provenance.{missing_key} to be rejected by the schema"


@pytest.mark.parametrize("key,bad_value", [("scientific_seed", -1), ("solver_seed", -1), ("validation_rotation_seed", -1)])
def test_schema_rejects_provenance_negative_seed(key: str, bad_value: int) -> None:
    document = _manual_robustness_document("gamma_O")
    document["provenance"][key] = bad_value
    errors = list(_validator().iter_errors(document))
    assert errors, f"expected provenance.{key}={bad_value} to be rejected by the schema"


def test_schema_accepts_provenance_with_non_null_validation_rotation_seed() -> None:
    document = _manual_robustness_document("gamma_O")
    document["provenance"]["validation_rotation_seed"] = 7
    errors = list(_validator().iter_errors(document))
    assert errors == []


def test_schema_rejects_provenance_missing_scientific_or_solver_seed_but_null_is_rejected_too() -> None:
    document = _manual_robustness_document("gamma_O")
    document["provenance"]["scientific_seed"] = None
    errors = list(_validator().iter_errors(document))
    assert errors, "scientific_seed must be an integer, never null"


def test_serialize_result_record_includes_seed_fields() -> None:
    record = build_result_record(
        _identity(), "raw_observable", "C_QQ_raw", 0.5, scientific_seed=5, solver_seed=6, validation_rotation_seed=7
    )
    document = serialize_result_record(record, repository_commit=REPO_COMMIT, manifest_fingerprint="fp", campaign_id="c1")
    assert document["provenance"]["scientific_seed"] == 5
    assert document["provenance"]["solver_seed"] == 6
    assert document["provenance"]["validation_rotation_seed"] == 7
    errors = list(_validator().iter_errors(document))
    assert errors == []
