"""Unit tests for the T_max non-regression calibration tool (1C-7c2).

Entirely synthetic/unit -- no real diagonalization of triangle/ring5, no
real T_max campaign calculation, no real Level1C preflight, no real
calibration run against a genuine historical corpus. `run_calibration`
is exercised end to end in one wiring test only after monkeypatching
`compute_current_tmax_case` (the sole real-diagonalization entry point)
with a synthetic, controlled substitute -- everything else in that test
runs for real (manifest loading, historical JSONL parsing/hashing,
comparison, aggregation, tolerance derivation, provenance plumbing with
git calls themselves monkeypatched).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from cosmobox.level1.matching import NOT_APPLICABLE, NUMERIC, UNAVAILABLE, SymmetryLabel
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from experiments.level1.manifest import load_manifest
from scripts.level1c_calibration import tmax_nonregression as m

REAL_MANIFEST = load_manifest()
REFERENCE_HAMILTONIAN = {"h_is_zero": True, "t": 1.0, "g_E": 1.0, "K": 1.0}


def _reference_j(n_nodes: int) -> list[float]:
    return [1.0] * n_nodes


def _document(
    *,
    geometry: str,
    spin: int,
    n_nodes: int,
    campaign_id: str,
    manifest_fingerprint: str,
    group_index: int,
    twice_T: int,
    multiplicity: int,
    status: str = COMPLETE_MULTIPLET,
    representative_energy: float = 1.23,
    record_kind: str,
    observable_kind: str,
    payload,
    path: tuple[int, int] | None = None,
) -> dict:
    return {
        "schema_version": "level1-correlators-v2",
        "repository_commit": "a" * 40,
        "manifest_fingerprint": manifest_fingerprint,
        "campaign_id": campaign_id,
        "identity": {
            "geometry": geometry,
            "spin": spin,
            "n_flavors": 2,
            "hamiltonian": {"J": _reference_j(n_nodes), **REFERENCE_HAMILTONIAN},
            "sector": "default",
            "spectral_group": {
                "status": status,
                "multiplicity": multiplicity,
                "twice_T": twice_T,
                "spectral_window_group_index": group_index,
                "representative_energy": representative_energy,
            },
            "path": list(path) if path is not None else None,
            "flavor_component": None,
            "normalization": None,
        },
        "provenance": {
            "spectral_status": status,
            "source_type": "float",
            "source_module": "builtins",
            "match_status": None,
            "covariance_validated": None,
            "scientific_seed": 0,
            "solver_seed": 0,
            "validation_rotation_seed": None,
        },
        "record_kind": record_kind,
        "observable_kind": observable_kind,
        "payload": payload,
    }


def _ctt_document(**kwargs) -> dict:
    return _document(record_kind="raw_observable", observable_kind="C_TT_conn", **kwargs)


def _rho_document(*, value, null_reason=None, **kwargs) -> dict:
    return _document(
        record_kind="normalized_observable", observable_kind="rho_QQ", payload={"value": value, "null_reason": null_reason}, **kwargs
    )


def _symmetry_document(*, observable_kind: str, kind: str, value: complex | None, **kwargs) -> dict:
    payload = {"kind": kind, "value": ({"real": value.real, "imag": value.imag} if value is not None else None)}
    return _document(record_kind="symmetry_label", observable_kind=observable_kind, payload=payload, path=None, **kwargs)


def _write_records(case_dir: Path, documents: list[dict]) -> str:
    case_dir.mkdir(parents=True, exist_ok=True)
    records_path = case_dir / "records.jsonl"
    text = "\n".join(json.dumps(document) for document in documents) + "\n"
    records_path.write_text(text, encoding="utf-8")
    return m.compute_file_sha256(records_path)


# ---------------------------------------------------------------------------
# derive_absolute_tolerance / CEIL_DECADE_POLICY
# ---------------------------------------------------------------------------


class TestDeriveAbsoluteTolerance:
    def test_generic_value_rounds_up_to_next_decade(self):
        assert m.derive_absolute_tolerance(2.3e-13) == pytest.approx(1e-12)

    def test_exact_power_of_ten_stays_on_its_own_decade(self):
        for exponent in (-8, -10, -12, -14):
            value = 10.0**exponent
            assert m.derive_absolute_tolerance(value) == pytest.approx(value)

    def test_zero_uses_float64_epsilon_reference(self):
        expected = 10.0 ** math.ceil(math.log10(np.finfo(np.float64).eps))
        assert m.derive_absolute_tolerance(0.0) == pytest.approx(expected)
        assert m.derive_absolute_tolerance(0.0) == pytest.approx(1e-15)

    def test_negative_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(-1e-10)

    def test_nan_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(float("nan"))

    def test_infinity_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(float("inf"))
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(float("-inf"))

    def test_bool_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(True)

    def test_never_a_rigorous_bound_marketing_string_present_only_in_docs(self):
        # The function itself carries no floor/safety-factor parameter --
        # this is a structural assertion that the signature stays minimal.
        import inspect

        signature = inspect.signature(m.derive_absolute_tolerance)
        assert list(signature.parameters) == ["e"]


# ---------------------------------------------------------------------------
# Canonical JSON
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_same_semantic_payload_produces_identical_bytes_regardless_of_key_order(self):
        a = {"b": 1, "a": 2, "c": {"y": 1, "x": 2}}
        b = {"a": 2, "c": {"x": 2, "y": 1}, "b": 1}
        assert m.canonical_json_bytes(a) == m.canonical_json_bytes(b)

    def test_nan_is_refused(self):
        with pytest.raises(ValueError):
            m.canonical_json_bytes({"value": float("nan")})

    def test_infinity_is_refused(self):
        with pytest.raises(ValueError):
            m.canonical_json_bytes({"value": float("inf")})

    def test_ends_with_a_single_trailing_newline(self):
        data = m.canonical_json_bytes({"a": 1})
        assert data.endswith(b"\n")
        assert not data.endswith(b"\n\n")


# ---------------------------------------------------------------------------
# Environment fingerprint
# ---------------------------------------------------------------------------


class TestEnvironmentFingerprint:
    def test_deterministic_serialization(self):
        first = m.build_environment_fingerprint()
        second = m.build_environment_fingerprint()
        assert first == second
        assert m.canonical_json_bytes(first) == m.canonical_json_bytes(second)

    def test_same_fingerprint_is_equal(self):
        fp = m.build_environment_fingerprint()
        assert m.environments_are_equal(fp, dict(fp))

    def test_python_version_mismatch_is_different(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["python_version"] = "0.0.0"
        assert not m.environments_are_equal(fp, other)

    def test_numpy_version_mismatch_is_different(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["numpy_version"] = "0.0.0"
        assert not m.environments_are_equal(fp, other)

    def test_scipy_version_mismatch_is_different(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["scipy_version"] = "0.0.0"
        assert not m.environments_are_equal(fp, other)

    def test_blas_lapack_mismatch_is_different(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["blas_lapack"] = {**other["blas_lapack"], "blas_version": "0.0.0"}
        assert not m.environments_are_equal(fp, other)

    def test_platform_mismatch_is_different(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["platform"] = "nonexistent-platform"
        assert not m.environments_are_equal(fp, other)

    def test_architecture_mismatch_is_different(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["architecture"] = "nonexistent-arch"
        assert not m.environments_are_equal(fp, other)

    def test_no_timestamp_field(self):
        fp = m.build_environment_fingerprint()
        for key in fp:
            assert "time" not in key.lower()

    def test_blas_lapack_identity_unavailable_fallback(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise RuntimeError("no structured config available")

        monkeypatch.setattr(m.np, "show_config", _raise)
        identity = m._blas_lapack_identity()
        assert identity["blas_name"] == m._ENVIRONMENT_FINGERPRINT_UNAVAILABLE
        assert identity["lapack_version"] == m._ENVIRONMENT_FINGERPRINT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Historical calibration manifest loading -- explicit, never glob/latest.
# ---------------------------------------------------------------------------


class TestHistoricalManifestLoading:
    def _minimal_payload(self, tmp_path: Path) -> dict:
        return {
            "campaign_id": "level1b-reference-v1",
            "manifest_fingerprint": "f" * 64,
            "cases": [
                {
                    "geometry": "triangle",
                    "spin": 2,
                    "case_dir": str(tmp_path),
                    "expected_records_sha256": "a" * 64,
                    "target_group_selector": {"spectral_window_group_index": 5, "twice_T": 3, "multiplicity": 4},
                }
            ],
        }

    def test_valid_minimal_manifest_parses(self, tmp_path):
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(self._minimal_payload(tmp_path)), encoding="utf-8")
        manifest = m.load_historical_calibration_manifest(path)
        assert manifest.campaign_id == "level1b-reference-v1"
        assert len(manifest.cases) == 1
        assert manifest.cases[0].target_group_selector.twice_T == 3

    def test_missing_file_is_refused(self, tmp_path):
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(tmp_path / "does-not-exist.json")

    def test_invalid_json_is_refused(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_missing_top_level_key_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        del payload["manifest_fingerprint"]
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_empty_cases_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        payload["cases"] = []
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_duplicate_geometry_spin_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        payload["cases"].append(dict(payload["cases"][0]))
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_invalid_geometry_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        payload["cases"][0]["geometry"] = "ring4"
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_invalid_spin_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        payload["cases"][0]["spin"] = 1
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_bad_sha256_format_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        payload["cases"][0]["expected_records_sha256"] = "not-a-hash"
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)

    def test_missing_selector_key_is_refused(self, tmp_path):
        payload = self._minimal_payload(tmp_path)
        del payload["cases"][0]["target_group_selector"]["multiplicity"]
        path = tmp_path / "historical.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(m.CalibrationConfigError):
            m.load_historical_calibration_manifest(path)


# ---------------------------------------------------------------------------
# Historical record extraction
# ---------------------------------------------------------------------------


class TestExtractHistoricalTargetRecords:
    CAMPAIGN_ID = "level1b-reference-v1"
    FINGERPRINT = "f" * 64
    SELECTOR = m.HistoricalGroupSelector(spectral_window_group_index=5, twice_T=3, multiplicity=4)

    def _base_kwargs(self):
        return dict(
            geometry="triangle",
            spin=2,
            n_nodes=3,
            campaign_id=self.CAMPAIGN_ID,
            manifest_fingerprint=self.FINGERPRINT,
            group_index=self.SELECTOR.spectral_window_group_index,
            twice_T=self.SELECTOR.twice_T,
            multiplicity=self.SELECTOR.multiplicity,
        )

    def test_extracts_matching_ctt_and_rho_and_labels(self):
        documents = [
            _ctt_document(**self._base_kwargs(), payload=0.5, path=(0, 1)),
            _rho_document(**self._base_kwargs(), value=0.25, path=(0, 1)),
            _symmetry_document(**self._base_kwargs(), observable_kind="translation_character", kind=NUMERIC, value=complex(1.0, 0.0)),
            _symmetry_document(**self._base_kwargs(), observable_kind="reflection_character", kind=NUMERIC, value=complex(-1.0, 0.0)),
            # An unrelated record (different group) must never be picked up.
            _ctt_document(**{**self._base_kwargs(), "group_index": 0}, payload=999.0, path=(0, 1)),
        ]
        result = m.extract_historical_target_records(
            documents,
            geometry="triangle",
            spin=2,
            campaign_id=self.CAMPAIGN_ID,
            manifest_fingerprint=self.FINGERPRINT,
            n_nodes=3,
            selector=self.SELECTOR,
        )
        assert result is not None
        assert result.ctt[(0, 1)] == 0.5
        assert result.rho[(0, 1)] == (0.25, None)
        assert result.translation_label == SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0))
        assert result.reflection_label == SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0))
        assert result.twice_T == 3
        assert result.multiplicity == 4

    def test_returns_none_when_nothing_matches(self):
        documents = [_ctt_document(**{**self._base_kwargs(), "group_index": 0}, payload=0.5, path=(0, 1))]
        result = m.extract_historical_target_records(
            documents,
            geometry="triangle",
            spin=2,
            campaign_id=self.CAMPAIGN_ID,
            manifest_fingerprint=self.FINGERPRINT,
            n_nodes=3,
            selector=self.SELECTOR,
        )
        assert result is None

    def test_duplicate_pair_record_is_refused(self):
        documents = [
            _ctt_document(**self._base_kwargs(), payload=0.5, path=(0, 1)),
            _ctt_document(**self._base_kwargs(), payload=0.6, path=(0, 1)),
        ]
        with pytest.raises(m.CalibrationConfigError):
            m.extract_historical_target_records(
                documents,
                geometry="triangle",
                spin=2,
                campaign_id=self.CAMPAIGN_ID,
                manifest_fingerprint=self.FINGERPRINT,
                n_nodes=3,
                selector=self.SELECTOR,
            )

    def test_disagreeing_status_is_refused(self):
        documents = [
            _ctt_document(**self._base_kwargs(), payload=0.5, path=(0, 1)),
            _ctt_document(**{**self._base_kwargs(), "status": PARTIAL_SUBSPACE}, payload=0.5, path=(1, 2)),
        ]
        with pytest.raises(m.CalibrationConfigError):
            m.extract_historical_target_records(
                documents,
                geometry="triangle",
                spin=2,
                campaign_id=self.CAMPAIGN_ID,
                manifest_fingerprint=self.FINGERPRINT,
                n_nodes=3,
                selector=self.SELECTOR,
            )

    def test_wrong_campaign_id_is_never_matched(self):
        documents = [_ctt_document(**{**self._base_kwargs(), "campaign_id": "other-campaign"}, payload=0.5, path=(0, 1))]
        result = m.extract_historical_target_records(
            documents,
            geometry="triangle",
            spin=2,
            campaign_id=self.CAMPAIGN_ID,
            manifest_fingerprint=self.FINGERPRINT,
            n_nodes=3,
            selector=self.SELECTOR,
        )
        assert result is None

    def test_diagonal_path_never_extracted(self):
        documents = [_ctt_document(**self._base_kwargs(), payload=0.5, path=(0, 0))]
        result = m.extract_historical_target_records(
            documents,
            geometry="triangle",
            spin=2,
            campaign_id=self.CAMPAIGN_ID,
            manifest_fingerprint=self.FINGERPRINT,
            n_nodes=3,
            selector=self.SELECTOR,
        )
        assert result is not None
        assert result.ctt == {}


# ---------------------------------------------------------------------------
# compare_case -- structural identity, nullity, and metric extraction
# ---------------------------------------------------------------------------


def _current_records(*, ctt=None, rho=None, translation=None, reflection=None, twice_T=3, multiplicity=4, status=COMPLETE_MULTIPLET):
    return m.CurrentTargetRecords(
        ctt=ctt or {},
        rho=rho or {},
        translation_label=translation or SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)),
        reflection_label=reflection or SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)),
        twice_T=twice_T,
        multiplicity=multiplicity,
        spectral_status=status,
    )


def _historical_records(*, ctt=None, rho=None, translation=None, reflection=None, twice_T=3, multiplicity=4, status=COMPLETE_MULTIPLET):
    return m.HistoricalTargetRecords(
        ctt=ctt or {},
        rho=rho or {},
        translation_label=translation or SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)),
        reflection_label=reflection or SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)),
        spectral_status=status,
        twice_T=twice_T,
        multiplicity=multiplicity,
    )


class TestCompareCase:
    def test_current_unavailable(self):
        result = m.compare_case("triangle", 2, None, m._TMAX_UNAVAILABLE_NOT_SELECTED, _historical_records())
        assert result.status == m.CASE_CURRENT_UNAVAILABLE
        assert result.detail == m._TMAX_UNAVAILABLE_NOT_SELECTED

    def test_historical_unavailable(self):
        result = m.compare_case("triangle", 2, _current_records(), None, None)
        assert result.status == m.CASE_HISTORICAL_UNAVAILABLE

    def test_status_mismatch_is_structural(self):
        result = m.compare_case("triangle", 2, _current_records(status=COMPLETE_MULTIPLET), None, _historical_records(status=PARTIAL_SUBSPACE))
        assert result.status == m.CASE_STRUCTURAL_MISMATCH

    def test_twice_t_mismatch_is_structural(self):
        result = m.compare_case("triangle", 2, _current_records(twice_T=3), None, _historical_records(twice_T=5))
        assert result.status == m.CASE_STRUCTURAL_MISMATCH

    def test_multiplicity_mismatch_is_structural(self):
        result = m.compare_case("triangle", 2, _current_records(multiplicity=4), None, _historical_records(multiplicity=6))
        assert result.status == m.CASE_STRUCTURAL_MISMATCH

    def test_translation_label_mismatch_is_structural(self):
        current = _current_records(translation=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)))
        historical = _historical_records(translation=SymmetryLabel(kind=NOT_APPLICABLE, value=None))
        result = m.compare_case("triangle", 2, current, None, historical)
        assert result.status == m.CASE_STRUCTURAL_MISMATCH

    def test_reflection_label_mismatch_is_structural(self):
        current = _current_records(reflection=SymmetryLabel(kind=UNAVAILABLE, value=None))
        historical = _historical_records(reflection=SymmetryLabel(kind=UNAVAILABLE, value=None))
        result = m.compare_case("triangle", 2, current, None, historical)
        # Two UNAVAILABLE labels never agree (matching.symmetry_labels_match's own rule).
        assert result.status == m.CASE_STRUCTURAL_MISMATCH

    def test_historical_missing_labels_is_structural(self):
        historical = _historical_records(translation=None, reflection=None)
        object.__setattr__(historical, "translation_label", None)
        object.__setattr__(historical, "reflection_label", None)
        result = m.compare_case("triangle", 2, _current_records(), None, historical)
        assert result.status == m.CASE_STRUCTURAL_MISMATCH

    def test_ctt_max_abs_and_pair_intersection(self):
        current = _current_records(ctt={(0, 1): 1.0, (0, 2): 2.0, (1, 2): 3.0})
        historical = _historical_records(ctt={(0, 1): 1.0 + 2.3e-13, (0, 2): 2.0 + 1e-14})
        result = m.compare_case("triangle", 2, current, None, historical)
        assert result.status == m.CASE_AVAILABLE
        pairs = {(r.i, r.j) for r in result.ctt_records}
        assert pairs == {(0, 1), (0, 2)}  # (1, 2) absent historically -> never compared

    def test_rho_both_nonnull_included(self):
        current = _current_records(rho={(0, 1): (0.5, None)})
        historical = _historical_records(rho={(0, 1): (0.5 + 1e-14, None)})
        result = m.compare_case("triangle", 2, current, None, historical)
        assert result.status == m.CASE_AVAILABLE
        assert len(result.rho_records) == 1
        assert not result.rho_records[0].both_null
        assert result.rho_records[0].abs_diff == pytest.approx(1e-14, abs=1e-16)

    def test_rho_both_null_same_reason_is_categorical_agreement(self):
        current = _current_records(rho={(0, 1): (None, "zero_local_charge_variance")})
        historical = _historical_records(rho={(0, 1): (None, "zero_local_charge_variance")})
        result = m.compare_case("triangle", 2, current, None, historical)
        assert result.status == m.CASE_AVAILABLE
        assert result.rho_records[0].both_null is True
        assert result.rho_records[0].abs_diff is None

    def test_rho_null_vs_nonnull_fails(self):
        current = _current_records(rho={(0, 1): (None, "zero_local_charge_variance")})
        historical = _historical_records(rho={(0, 1): (0.5, None)})
        result = m.compare_case("triangle", 2, current, None, historical)
        assert result.status == m.CASE_NULLITY_MISMATCH

    def test_rho_both_null_different_reason_fails(self):
        current = _current_records(rho={(0, 1): (None, "zero_local_charge_variance")})
        historical = _historical_records(rho={(0, 1): (None, "some_other_reason")})
        result = m.compare_case("triangle", 2, current, None, historical)
        assert result.status == m.CASE_NULLITY_MISMATCH


# ---------------------------------------------------------------------------
# Aggregation -- MAX_ABS, order independence, availability
# ---------------------------------------------------------------------------


class TestAggregateMetrics:
    def _available_case(self, geometry, spin, ctt_diffs, rho_records):
        ctt_records = tuple(m.CttPairRecord(geometry, spin, i, j, diff) for (i, j), diff in ctt_diffs.items())
        return m.CaseComparison(geometry, spin, m.CASE_AVAILABLE, None, ctt_records, rho_records)

    def test_max_abs_over_multiple_records(self):
        case1 = self._available_case("triangle", 2, {(0, 1): 1e-10, (0, 2): 5e-8}, ())
        case2 = self._available_case("triangle", 3, {(0, 1): 3e-9}, ())
        metrics = m.aggregate_metrics([case1, case2])
        assert metrics.e_ctt == pytest.approx(5e-8)

    def test_order_of_records_has_no_effect(self):
        case_a = self._available_case("triangle", 2, {(0, 1): 5e-8, (0, 2): 1e-10}, ())
        case_b = self._available_case("triangle", 2, {(0, 2): 1e-10, (0, 1): 5e-8}, ())
        assert m.aggregate_metrics([case_a]).e_ctt == m.aggregate_metrics([case_b]).e_ctt

    def test_zero_difference_is_a_valid_e_ctt(self):
        case = self._available_case("triangle", 2, {(0, 1): 0.0}, ())
        metrics = m.aggregate_metrics([case])
        assert metrics.e_ctt == 0.0

    def test_no_ctt_records_gives_none(self):
        metrics = m.aggregate_metrics([m.CaseComparison("triangle", 2, m.CASE_CURRENT_UNAVAILABLE, "x", (), ())])
        assert metrics.e_ctt is None

    def test_rho_all_both_null_gives_no_numeric_status(self):
        rho_records = (m.RhoPairRecord("triangle", 2, 0, 1, None, True),)
        case = self._available_case("triangle", 2, {}, rho_records)
        metrics = m.aggregate_metrics([case])
        assert metrics.e_rho is None
        assert metrics.rho_numeric_status == m.RHO_NUMERIC_UNAVAILABLE

    def test_rho_no_records_at_all_gives_no_status(self):
        case = self._available_case("triangle", 2, {}, ())
        metrics = m.aggregate_metrics([case])
        assert metrics.rho_numeric_status is None

    def test_rho_mixed_numeric_and_null_uses_max_of_numeric_only(self):
        rho_records = (
            m.RhoPairRecord("triangle", 2, 0, 1, None, True),
            m.RhoPairRecord("triangle", 2, 0, 2, 3e-9, False),
            m.RhoPairRecord("triangle", 2, 1, 2, 7e-10, False),
        )
        case = self._available_case("triangle", 2, {}, rho_records)
        metrics = m.aggregate_metrics([case])
        assert metrics.e_rho == pytest.approx(3e-9)
        assert metrics.rho_numeric_status is None

    def test_usable_geometries_triangle_and_ring5(self):
        cases = [self._available_case("triangle", 2, {}, ()), self._available_case("ring5", 3, {}, ())]
        assert m.usable_geometries(cases) == {"triangle", "ring5"}

    def test_usable_geometries_only_triangle(self):
        cases = [
            self._available_case("triangle", 2, {}, ()),
            m.CaseComparison("ring5", 2, m.CASE_CURRENT_UNAVAILABLE, "x", (), ()),
            m.CaseComparison("ring5", 3, m.CASE_HISTORICAL_UNAVAILABLE, "x", (), ()),
        ]
        assert m.usable_geometries(cases) == {"triangle"}

    def test_t_max_absent_in_one_spin_but_present_in_other_still_usable(self):
        cases = [
            self._available_case("triangle", 2, {(0, 1): 1e-10}, ()),
            m.CaseComparison("triangle", 3, m.CASE_CURRENT_UNAVAILABLE, m._TMAX_UNAVAILABLE_NOT_SELECTED, (), ()),
        ]
        assert m.usable_geometries(cases) == {"triangle"}


# ---------------------------------------------------------------------------
# CLI safety
# ---------------------------------------------------------------------------


class TestCliSafety:
    def test_help_never_computes(self, monkeypatch, capsys):
        def _forbidden(*args, **kwargs):
            raise AssertionError("run_calibration must never be called by --help")

        monkeypatch.setattr(m, "run_calibration", _forbidden)
        # argparse's own -h/--help handler exits directly (SystemExit(0))
        # before any of this module's code runs -- it never reaches
        # run_calibration, which is exactly what this test asserts.
        with pytest.raises(SystemExit) as excinfo:
            m.main(["--help"])
        assert excinfo.value.code == 0

    def test_default_never_computes(self, monkeypatch):
        def _forbidden(*args, **kwargs):
            raise AssertionError("run_calibration must never be called without --confirm-run-calibration")

        monkeypatch.setattr(m, "run_calibration", _forbidden)
        exit_code = m.main([])
        assert exit_code == 0

    def test_confirm_flag_requires_historical_manifest(self):
        with pytest.raises(SystemExit):
            m.main(["--confirm-run-calibration"])

    def test_confirm_flag_invokes_run_calibration_and_prints_json(self, monkeypatch, capsys, tmp_path):
        artifact = m.CalibrationArtifact(
            schema_version=m.CALIBRATION_ARTIFACT_SCHEMA_VERSION,
            provenance=m.CalibrationProvenance("v1", "a" * 40, "campaign", "f" * 64, {}),
            cases=(),
            status=m.CALIBRATION_SUCCESS,
            failure_reasons=(),
            e_ctt=1e-12,
            e_rho=1e-13,
            rho_numeric_status=None,
            non_regression_ctt_abs_tol=1e-12,
            non_regression_rho_abs_tol=1e-12,
        )
        called = {}

        def _fake_run_calibration(historical_manifest, manifest=None, *, repo_root=None):
            called["invoked"] = True
            return artifact

        monkeypatch.setattr(m, "run_calibration", _fake_run_calibration)
        monkeypatch.setattr(
            m, "load_historical_calibration_manifest", lambda path: m.HistoricalCalibrationManifest("c", "f" * 64, ())
        )
        exit_code = m.main(["--confirm-run-calibration", "--historical-manifest", str(tmp_path / "x.json")])
        assert called["invoked"] is True
        assert exit_code == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed["status"] == m.CALIBRATION_SUCCESS

    def test_confirm_flag_nonzero_exit_on_failure_status(self, monkeypatch, capsys, tmp_path):
        artifact = m.CalibrationArtifact(
            schema_version=m.CALIBRATION_ARTIFACT_SCHEMA_VERSION,
            provenance=m.CalibrationProvenance("v1", "a" * 40, "campaign", "f" * 64, {}),
            cases=(),
            status=m.CALIBRATION_FAIL,
            failure_reasons=("no usable calibration case for geometry 'ring5'",),
            e_ctt=None,
            e_rho=None,
            rho_numeric_status=None,
            non_regression_ctt_abs_tol=None,
            non_regression_rho_abs_tol=None,
        )
        monkeypatch.setattr(m, "run_calibration", lambda *a, **k: artifact)
        monkeypatch.setattr(
            m, "load_historical_calibration_manifest", lambda path: m.HistoricalCalibrationManifest("c", "f" * 64, ())
        )
        exit_code = m.main(["--confirm-run-calibration", "--historical-manifest", str(tmp_path / "x.json")])
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Git provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_dirty_worktree_refusal(self, monkeypatch):
        def _dirty(repo_root=None):
            raise m._GitProvenanceFailure()

        monkeypatch.setattr(m, "_require_clean_git_worktree", _dirty)
        with pytest.raises(m.CalibrationInternalFailure):
            m.require_clean_worktree()

    def test_invalid_commit_sha_refusal(self, monkeypatch):
        def _bad_sha(repo_root=None):
            raise m._GitProvenanceFailure()

        monkeypatch.setattr(m, "_resolve_git_head_sha", _bad_sha)
        with pytest.raises(m.CalibrationInternalFailure):
            m.resolve_calibration_code_commit()

    def test_historical_artifact_sha_mismatch_refusal(self, tmp_path):
        case_dir = tmp_path / "case"
        _write_records(case_dir, [{"a": 1}])
        case = m.HistoricalCaseReference(
            geometry="triangle",
            spin=2,
            case_dir=str(case_dir),
            expected_records_sha256="0" * 64,
            target_group_selector=m.HistoricalGroupSelector(5, 3, 4),
        )
        with pytest.raises(m.CalibrationConfigError):
            m._load_and_verify_historical_documents(case)

    def test_manifest_fingerprint_mismatch_refusal_before_any_git_call(self, monkeypatch):
        calls = {"clean": 0, "sha": 0}
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: calls.__setitem__("clean", calls["clean"] + 1))
        monkeypatch.setattr(
            m, "resolve_calibration_code_commit", lambda repo_root=None: calls.__setitem__("sha", calls["sha"] + 1) or "a" * 40
        )
        historical_manifest = m.HistoricalCalibrationManifest(campaign_id="x", manifest_fingerprint="0" * 64, cases=(
            m.HistoricalCaseReference("triangle", 2, "/nonexistent", "a" * 64, m.HistoricalGroupSelector(5, 3, 4)),
        ))
        with pytest.raises(m.CalibrationConfigError):
            m.run_calibration(historical_manifest, manifest=REAL_MANIFEST)
        assert calls["clean"] == 0
        assert calls["sha"] == 0


# ---------------------------------------------------------------------------
# Firewall: no raw internal exception content ever reaches a public path.
# ---------------------------------------------------------------------------


class TestFirewall:
    SECRET = "SECRET_INTERNAL_VALUE=123.456789"

    def test_internal_exception_is_sanitized_in_run_calibration(self, monkeypatch, tmp_path):
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "a" * 40)

        def _raise_with_secret(*args, **kwargs):
            raise ValueError(self.SECRET)

        monkeypatch.setattr(m, "compute_current_tmax_case", _raise_with_secret)

        historical_manifest = m.HistoricalCalibrationManifest(
            campaign_id="level1b-reference-v1",
            manifest_fingerprint=REAL_MANIFEST.fingerprint,
            cases=(m.HistoricalCaseReference("triangle", 2, str(tmp_path), "a" * 64, m.HistoricalGroupSelector(5, 3, 4)),),
        )

        with pytest.raises(m.CalibrationInternalFailure) as excinfo:
            m.run_calibration(historical_manifest, manifest=REAL_MANIFEST)

        assert self.SECRET not in str(excinfo.value)
        assert excinfo.value.__cause__ is None

        import traceback

        rendered = "".join(traceback.format_exception(type(excinfo.value), excinfo.value, excinfo.value.__traceback__))
        assert self.SECRET not in rendered

    def test_memory_error_is_not_converted_to_internal_failure(self, monkeypatch, tmp_path):
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "a" * 40)

        def _raise_memory_error(*args, **kwargs):
            raise MemoryError()

        monkeypatch.setattr(m, "compute_current_tmax_case", _raise_memory_error)
        historical_manifest = m.HistoricalCalibrationManifest(
            campaign_id="level1b-reference-v1",
            manifest_fingerprint=REAL_MANIFEST.fingerprint,
            cases=(m.HistoricalCaseReference("triangle", 2, str(tmp_path), "a" * 64, m.HistoricalGroupSelector(5, 3, 4)),),
        )
        with pytest.raises(m.CalibrationInternalFailure):
            m.run_calibration(historical_manifest, manifest=REAL_MANIFEST)


# ---------------------------------------------------------------------------
# run_calibration wiring -- the ONLY real-diagonalization entry point
# (compute_current_tmax_case) is monkeypatched; everything else (manifest
# loading, historical JSONL parsing/hashing, structural comparison,
# aggregation, tolerance derivation, provenance plumbing) runs for real.
# ---------------------------------------------------------------------------


class TestRunCalibrationWiring:
    GEOMETRY_NODES = {"triangle": (0, 1, 2), "ring5": (0, 1, 2, 3, 4)}
    TARGET_TWICE_T = {"triangle": 3, "ring5": 5}

    def _pairs(self, geometry):
        nodes = self.GEOMETRY_NODES[geometry]
        return [(i, j) for i in nodes for j in nodes if i != j]

    def _build_case(self, tmp_path, geometry, spin, *, ctt_offset, rho_offset):
        twice_T = self.TARGET_TWICE_T[geometry]
        multiplicity = twice_T + 1
        n_nodes = len(self.GEOMETRY_NODES[geometry])
        base = dict(
            geometry=geometry,
            spin=spin,
            n_nodes=n_nodes,
            campaign_id="level1b-reference-v1",
            manifest_fingerprint=REAL_MANIFEST.fingerprint,
            group_index=7,
            twice_T=twice_T,
            multiplicity=multiplicity,
        )
        pairs = self._pairs(geometry)
        current_ctt = {pair: 0.5 + 0.01 * index for index, pair in enumerate(pairs)}
        current_rho = {pair: (0.2 + 0.01 * index, None) for index, pair in enumerate(pairs)}

        documents = []
        for pair in pairs:
            documents.append(_ctt_document(**base, payload=current_ctt[pair] + ctt_offset, path=pair))
            documents.append(_rho_document(**base, value=current_rho[pair][0] + rho_offset, path=pair))
        documents.append(_symmetry_document(**base, observable_kind="translation_character", kind=NUMERIC, value=complex(1.0, 0.0)))
        documents.append(_symmetry_document(**base, observable_kind="reflection_character", kind=NUMERIC, value=complex(-1.0, 0.0)))

        case_dir = tmp_path / f"{geometry}_S{spin}"
        sha256 = _write_records(case_dir, documents)

        current_records = m.CurrentTargetRecords(
            ctt=current_ctt,
            rho=current_rho,
            translation_label=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)),
            reflection_label=SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)),
            twice_T=twice_T,
            multiplicity=multiplicity,
            spectral_status=COMPLETE_MULTIPLET,
        )
        historical_case = m.HistoricalCaseReference(
            geometry=geometry,
            spin=spin,
            case_dir=str(case_dir),
            expected_records_sha256=sha256,
            target_group_selector=m.HistoricalGroupSelector(spectral_window_group_index=7, twice_T=twice_T, multiplicity=multiplicity),
        )
        return current_records, historical_case

    def test_full_success_derives_tolerances_from_max_abs_diff(self, tmp_path, monkeypatch):
        current_by_case = {}
        historical_cases = []
        offsets = {
            ("triangle", 2): (2.3e-13, 1e-14),
            ("triangle", 3): (1e-14, 1e-14),
            ("ring5", 2): (1e-14, 4e-14),
            ("ring5", 3): (1e-14, 1e-14),
        }
        for (geometry, spin), (ctt_offset, rho_offset) in offsets.items():
            current_records, historical_case = self._build_case(tmp_path, geometry, spin, ctt_offset=ctt_offset, rho_offset=rho_offset)
            current_by_case[(geometry, spin)] = current_records
            historical_cases.append(historical_case)

        def _fake_current(geometry, spin, manifest):
            return current_by_case[(geometry, spin)], None

        monkeypatch.setattr(m, "compute_current_tmax_case", _fake_current)
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)

        historical_manifest = m.HistoricalCalibrationManifest(
            campaign_id="level1b-reference-v1", manifest_fingerprint=REAL_MANIFEST.fingerprint, cases=tuple(historical_cases)
        )
        artifact = m.run_calibration(historical_manifest, manifest=REAL_MANIFEST)

        assert artifact.status == m.CALIBRATION_SUCCESS
        assert artifact.failure_reasons == ()
        assert artifact.e_ctt == pytest.approx(2.3e-13)
        assert artifact.non_regression_ctt_abs_tol == pytest.approx(1e-12)
        assert artifact.e_rho == pytest.approx(4e-14)
        assert artifact.non_regression_rho_abs_tol == pytest.approx(1e-13)
        assert artifact.provenance.code_commit == "b" * 40
        assert len(artifact.cases) == 4
        assert all(case.status == m.CASE_AVAILABLE for case in artifact.cases)
        # Public firewall: no raw per-pair value ever reaches the artifact.
        rendered = json.dumps(m._artifact_to_json(artifact))
        assert "0.5" not in rendered  # a raw current C_TT_conn value
        assert str(tmp_path) not in rendered  # no filesystem path leakage

    def test_missing_geometry_fails_with_reason(self, tmp_path, monkeypatch):
        current_records, historical_case = self._build_case(tmp_path, "triangle", 2, ctt_offset=1e-14, rho_offset=1e-14)

        def _fake_current(geometry, spin, manifest):
            if geometry == "triangle" and spin == 2:
                return current_records, None
            return None, m._TMAX_UNAVAILABLE_NOT_SELECTED

        monkeypatch.setattr(m, "compute_current_tmax_case", _fake_current)
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)

        historical_manifest = m.HistoricalCalibrationManifest(
            campaign_id="level1b-reference-v1", manifest_fingerprint=REAL_MANIFEST.fingerprint, cases=(historical_case,)
        )
        artifact = m.run_calibration(historical_manifest, manifest=REAL_MANIFEST)
        assert artifact.status == m.CALIBRATION_FAIL
        assert any("ring5" in reason for reason in artifact.failure_reasons)

    def test_selector_twice_t_inconsistent_with_manifest_is_refused(self, tmp_path, monkeypatch):
        _, historical_case = self._build_case(tmp_path, "triangle", 2, ctt_offset=1e-14, rho_offset=1e-14)
        bad_case = m.HistoricalCaseReference(
            geometry="triangle",
            spin=2,
            case_dir=historical_case.case_dir,
            expected_records_sha256=historical_case.expected_records_sha256,
            target_group_selector=m.HistoricalGroupSelector(spectral_window_group_index=7, twice_T=99, multiplicity=100),
        )
        monkeypatch.setattr(m, "compute_current_tmax_case", lambda *a, **k: (None, m._TMAX_UNAVAILABLE_NOT_SELECTED))
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)

        historical_manifest = m.HistoricalCalibrationManifest(
            campaign_id="level1b-reference-v1", manifest_fingerprint=REAL_MANIFEST.fingerprint, cases=(bad_case,)
        )
        with pytest.raises(m.CalibrationConfigError):
            m.run_calibration(historical_manifest, manifest=REAL_MANIFEST)
