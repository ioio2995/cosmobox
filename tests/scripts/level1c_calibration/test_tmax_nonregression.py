"""Unit tests for the target-id-free non-regression calibration tool
(1C-7c2c).

Entirely synthetic/unit -- no real diagonalization of any holdout case,
no `--confirm-run-calibration` invocation, no dependency on the real
historical artifact directory (which lives outside this repository and
is not guaranteed present in every environment). `run_calibration` is
exercised end to end in one wiring test only, after monkeypatching
`build_case_context`/`compute_current_group_result` (the only two real-
diagonalization entry points) with controlled synthetic substitutes --
everything else (manifest/plan loading, historical JSONL parsing via the
already-accepted scripts.level1b_analysis loader/indexer, structural
comparison, aggregation, tolerance derivation, provenance plumbing with
git calls themselves monkeypatched) runs for real.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from cosmobox.level1.assembly import assemble_execution
from cosmobox.level0.lattice import build_lattice
from cosmobox.level1.matching import NOT_APPLICABLE, NUMERIC, UNAVAILABLE, SpectralGroupMatchKey, SymmetryLabel
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from cosmobox.level1.results import SpectralGroupIdentity
from experiments.level1.manifest import load_manifest
from experiments.level1.planning import build_campaign_plan, build_ordered_pairs
from scripts.level1b_analysis.indexing import IndexedSpectralGroup
from scripts.level1c_calibration import tmax_nonregression as m

REAL_MANIFEST = load_manifest()
REAL_PLAN = build_campaign_plan(REAL_MANIFEST)
REAL_PLAN_BY_KEY = {(c.geometry, c.spin, c.hamiltonian_case_id): c for c in REAL_PLAN}

TRIANGLE_S1 = REAL_PLAN_BY_KEY[("triangle", 1, "reference")]
RING4_S1 = REAL_PLAN_BY_KEY[("ring4", 1, "reference")]
RING5_S1 = REAL_PLAN_BY_KEY[("ring5", 1, "reference")]


def _freeze(value):
    if isinstance(value, dict):
        from types import MappingProxyType

        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _ctt_doc(i: int, j: int, value: float) -> dict:
    return {"identity": {"path": [i, j]}, "record_kind": "raw_observable", "observable_kind": "C_TT_conn", "payload": value}


def _rho_doc(i: int, j: int, value: float | None, null_reason: str | None = None) -> dict:
    return {
        "identity": {"path": [i, j]},
        "record_kind": "normalized_observable",
        "observable_kind": "rho_QQ",
        "payload": {"value": value, "null_reason": null_reason},
    }


def _build_group(
    case,
    *,
    group_index: int,
    twice_T: int | None,
    multiplicity: int,
    status: str = COMPLETE_MULTIPLET,
    translation: SymmetryLabel = SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)),
    reflection: SymmetryLabel = SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)),
    documents: tuple[dict, ...] = (),
) -> IndexedSpectralGroup:
    identity = SpectralGroupIdentity(
        status=status, multiplicity=multiplicity, twice_T=twice_T, spectral_window_group_index=group_index, representative_energy=1.23
    )
    match_key = SpectralGroupMatchKey(
        geometry=case.geometry,
        hamiltonian_identity_without_spin=(case.geometry, case.hamiltonian_case_id),
        sector_identity=case.sector_id,
        status=status,
        multiplicity=multiplicity,
        twice_T=twice_T if twice_T is not None else 0,
        translation_label=translation,
        reflection_label=reflection,
    )
    frozen_docs = tuple(_freeze(d) for d in documents) if documents else (_freeze({"placeholder": True}),)
    return IndexedSpectralGroup(
        case_id=case.case_id, case=case, spectral_group_identity=identity, spectral_window_group_index=group_index, match_key=match_key, documents=frozen_docs
    )


def _full_pairs(case, value_ctt: float = 0.5, value_rho: float | None = 0.25, null_reason: str | None = None) -> tuple[dict, ...]:
    n_nodes = len(build_lattice(case.geometry).nodes)
    docs = []
    for i, j in build_ordered_pairs(n_nodes):
        docs.append(_ctt_doc(i, j, value_ctt))
        docs.append(_rho_doc(i, j, value_rho, null_reason))
    return tuple(docs)


def _current_result(*, multiplicity, twice_T, translation=None, reflection=None, ctt=None, rho=None):
    return m.CurrentGroupResult(
        multiplicity=multiplicity,
        twice_T=twice_T,
        translation_label=translation or SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)),
        reflection_label=reflection or SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)),
        ctt=ctt or {},
        rho=rho or {},
    )


# ---------------------------------------------------------------------------
# derive_absolute_tolerance / CEIL_DECADE_POLICY (corrected, 1C-7c2c)
# ---------------------------------------------------------------------------


class TestDeriveAbsoluteTolerance:
    def test_exact_power_of_ten(self):
        assert m.derive_absolute_tolerance(1e-12) == pytest.approx(1e-12)

    def test_nextafter_above_power_of_ten_promotes_decade(self):
        e = np.nextafter(1e-12, np.inf)
        tol = m.derive_absolute_tolerance(e)
        assert tol == pytest.approx(1e-11)
        assert tol >= e

    def test_slightly_above_power_of_ten_promotes_decade(self):
        e = 1e-12 * (1 + 1e-10)
        tol = m.derive_absolute_tolerance(e)
        assert tol == pytest.approx(1e-11)
        assert tol >= e

    def test_nextafter_above_1e_minus_10(self):
        e = np.nextafter(1e-10, np.inf)
        tol = m.derive_absolute_tolerance(e)
        assert tol == pytest.approx(1e-9)
        assert tol >= e

    def test_generic_value_rounds_up(self):
        assert m.derive_absolute_tolerance(2.3e-13) == pytest.approx(1e-12)

    def test_zero_uses_float64_epsilon_reference(self):
        assert m.derive_absolute_tolerance(0.0) == pytest.approx(1e-15)

    def test_invariant_tol_greater_or_equal_e_across_many_values(self):
        rng = np.random.default_rng(12345)
        for _ in range(500):
            exponent = rng.uniform(-16, 2)
            mantissa = rng.uniform(1.0, 10.0)
            e = mantissa * (10.0**exponent)
            assert m.derive_absolute_tolerance(e) >= e

    def test_invariant_holds_across_several_decades_boundaries(self):
        for exponent in range(-16, 3):
            base = 10.0**exponent
            for candidate in (base, np.nextafter(base, np.inf), base * (1 + 1e-9), np.nextafter(base, -np.inf)):
                if candidate <= 0:
                    continue
                assert m.derive_absolute_tolerance(candidate) >= candidate

    def test_negative_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(-1e-10)

    def test_nan_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(float("nan"))

    def test_infinity_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(float("inf"))

    def test_bool_is_rejected(self):
        with pytest.raises(ValueError):
            m.derive_absolute_tolerance(True)

    def test_no_rounding_of_log10_in_source(self):
        import inspect

        source = inspect.getsource(m.derive_absolute_tolerance)
        assert "round(" not in source


# ---------------------------------------------------------------------------
# Canonical JSON
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_same_semantic_payload_produces_identical_bytes(self):
        a = {"b": 1, "a": 2}
        b = {"a": 2, "b": 1}
        assert m.canonical_json_bytes(a) == m.canonical_json_bytes(b)

    def test_nan_is_refused(self):
        with pytest.raises(ValueError):
            m.canonical_json_bytes({"value": float("nan")})

    def test_infinity_is_refused(self):
        with pytest.raises(ValueError):
            m.canonical_json_bytes({"value": float("inf")})

    def test_single_trailing_newline(self):
        data = m.canonical_json_bytes({"a": 1})
        assert data.endswith(b"\n") and not data.endswith(b"\n\n")


# ---------------------------------------------------------------------------
# Environment fingerprint + completeness (hardened, 1C-7c2c)
# ---------------------------------------------------------------------------


class TestEnvironmentFingerprint:
    def test_deterministic_serialization(self):
        assert m.build_environment_fingerprint() == m.build_environment_fingerprint()

    def test_real_fingerprint_is_complete(self):
        assert m.environment_fingerprint_is_complete(m.build_environment_fingerprint()) is True

    def test_missing_python_version_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["python_version"] = ""
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_unavailable_numpy_version_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["numpy_version"] = m._ENVIRONMENT_FINGERPRINT_UNAVAILABLE
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_missing_scipy_version_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["scipy_version"] = None
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_blas_unavailable_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["blas_lapack"] = {**fp["blas_lapack"], "blas_name": m._ENVIRONMENT_FINGERPRINT_UNAVAILABLE}
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_lapack_version_unavailable_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["blas_lapack"] = {**fp["blas_lapack"], "lapack_version": m._ENVIRONMENT_FINGERPRINT_UNAVAILABLE}
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_empty_platform_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["platform"] = ""
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_empty_architecture_is_incomplete(self):
        fp = dict(m.build_environment_fingerprint())
        fp["architecture"] = ""
        assert m.environment_fingerprint_is_complete(fp) is False

    def test_equality_exact_field_by_field(self):
        fp = m.build_environment_fingerprint()
        other = dict(fp)
        other["platform"] = "different"
        assert m.environments_are_equal(fp, fp) is True
        assert m.environments_are_equal(fp, other) is False

    def test_blas_lapack_identity_unavailable_fallback(self, monkeypatch):
        monkeypatch.setattr(m.np, "show_config", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
        identity = m._blas_lapack_identity()
        assert identity["blas_name"] == m._ENVIRONMENT_FINGERPRINT_UNAVAILABLE


# ---------------------------------------------------------------------------
# select_required_cases -- exactly the five holdout cases, no fallback.
# ---------------------------------------------------------------------------


class TestSelectRequiredCases:
    def test_real_manifest_resolves_exactly_five_cases(self):
        cases = m.select_required_cases(REAL_MANIFEST)
        assert set(cases) == m.REQUIRED_CASE_KEYS
        assert len(cases) == 5

    def test_case_ids_match_manifest_derived_ids(self):
        cases = m.select_required_cases(REAL_MANIFEST)
        assert cases[("triangle", 1, "reference")].case_id == TRIANGLE_S1.case_id
        assert cases[("ring5", 1, "reference")].case_id == RING5_S1.case_id

    def test_j_break_never_in_required_keys(self):
        assert all(key[2] != "j_break" for key in m.REQUIRED_CASE_KEYS)

    def test_triangle_ring5_s2_s3_never_in_required_keys(self):
        for geometry in ("triangle", "ring5"):
            for spin in (2, 3):
                assert (geometry, spin, "reference") not in m.REQUIRED_CASE_KEYS

    def test_missing_required_case_raises_config_error(self, monkeypatch):
        incomplete_plan = tuple(case for case in REAL_PLAN if not (case.geometry == "triangle" and case.spin == 1))
        monkeypatch.setattr(m, "build_campaign_plan", lambda manifest: incomplete_plan)
        with pytest.raises(m.CalibrationConfigError, match="triangle"):
            m.select_required_cases(REAL_MANIFEST)

    def test_missing_ring4_s2_raises_config_error(self, monkeypatch):
        incomplete_plan = tuple(case for case in REAL_PLAN if not (case.geometry == "ring4" and case.spin == 2))
        monkeypatch.setattr(m, "build_campaign_plan", lambda manifest: incomplete_plan)
        with pytest.raises(m.CalibrationConfigError, match="ring4"):
            m.select_required_cases(REAL_MANIFEST)

    def test_extra_cases_in_plan_are_ignored(self):
        # The real plan has 11 cases (5 required + 6 not required); only
        # the 5 required ones are ever returned.
        cases = m.select_required_cases(REAL_MANIFEST)
        assert len(REAL_PLAN) == 11
        assert len(cases) == 5


# ---------------------------------------------------------------------------
# is_group_eligible -- CALIBRATION_GROUP_FILTER, purely structural.
# ---------------------------------------------------------------------------


class TestIsGroupEligible:
    def _n_nodes(self, case):
        return len(build_lattice(case.geometry).nodes)

    def test_complete_resolved_numeric_full_pairs_is_eligible(self):
        group = _build_group(TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, documents=_full_pairs(TRIANGLE_S1))
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is True

    def test_partial_subspace_excluded(self):
        group = _build_group(TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, status=PARTIAL_SUBSPACE, documents=_full_pairs(TRIANGLE_S1))
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is False

    def test_unresolved_twice_t_excluded(self):
        group = _build_group(TRIANGLE_S1, group_index=0, twice_T=None, multiplicity=2, documents=_full_pairs(TRIANGLE_S1))
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is False

    def test_translation_not_applicable_excluded(self):
        group = _build_group(
            TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, translation=SymmetryLabel(kind=NOT_APPLICABLE, value=None), documents=_full_pairs(TRIANGLE_S1)
        )
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is False

    def test_reflection_unavailable_excluded(self):
        group = _build_group(
            TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, reflection=SymmetryLabel(kind=UNAVAILABLE, value=None), documents=_full_pairs(TRIANGLE_S1)
        )
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is False

    def test_missing_one_ctt_pair_excluded(self):
        docs = list(_full_pairs(TRIANGLE_S1))
        docs = [d for d in docs if not (d["observable_kind"] == "C_TT_conn" and tuple(d["identity"]["path"]) == (0, 1))]
        group = _build_group(TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, documents=tuple(docs))
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is False

    def test_missing_one_rho_pair_excluded(self):
        docs = list(_full_pairs(TRIANGLE_S1))
        docs = [d for d in docs if not (d["observable_kind"] == "rho_QQ" and tuple(d["identity"]["path"]) == (0, 1))]
        group = _build_group(TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, documents=tuple(docs))
        assert m.is_group_eligible(group, n_nodes=self._n_nodes(TRIANGLE_S1)) is False

    def test_eligible_group_count_per_case_when_one_incomplete_one_eligible(self):
        eligible = _build_group(TRIANGLE_S1, group_index=0, twice_T=1, multiplicity=2, documents=_full_pairs(TRIANGLE_S1))
        docs = list(_full_pairs(TRIANGLE_S1))[:-1]
        incomplete = _build_group(TRIANGLE_S1, group_index=1, twice_T=3, multiplicity=4, documents=tuple(docs))
        n_nodes = self._n_nodes(TRIANGLE_S1)
        assert m.is_group_eligible(eligible, n_nodes=n_nodes) is True
        assert m.is_group_eligible(incomplete, n_nodes=n_nodes) is False


# ---------------------------------------------------------------------------
# compare_group -- CURRENT_MATCH, pair-set equality, nullity, non-finite.
# ---------------------------------------------------------------------------


class TestCompareGroup:
    def _historical(self, **kwargs):
        defaults = dict(group_index=0, twice_T=1, multiplicity=2, documents=_full_pairs(TRIANGLE_S1))
        defaults.update(kwargs)
        return _build_group(TRIANGLE_S1, **defaults)

    def test_missing_current_index(self):
        result = m.compare_group(self._historical(), None)
        assert result.status == m.GROUP_MATCH_MISSING_CURRENT_INDEX
        assert not result.ok

    def test_all_match(self):
        historical = self._historical()
        current = _current_result(
            multiplicity=2, twice_T=1, ctt={(0, 1): 0.5, (1, 0): 0.5, (0, 2): 0.5, (2, 0): 0.5, (1, 2): 0.5, (2, 1): 0.5}, rho={(0, 1): (0.25, None), (1, 0): (0.25, None), (0, 2): (0.25, None), (2, 0): (0.25, None), (1, 2): (0.25, None), (2, 1): (0.25, None)}
        )
        result = m.compare_group(historical, current)
        assert result.ok
        assert len(result.ctt_records) == 6
        assert len(result.rho_records) == 6

    def test_multiplicity_mismatch(self):
        current = _current_result(multiplicity=99, twice_T=1)
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_MULTIPLICITY_MISMATCH

    def test_twice_t_mismatch(self):
        current = _current_result(multiplicity=2, twice_T=99)
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_TWICE_T_MISMATCH

    def test_translation_mismatch(self):
        current = _current_result(multiplicity=2, twice_T=1, translation=SymmetryLabel(kind=NOT_APPLICABLE, value=None))
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_TRANSLATION_MISMATCH

    def test_reflection_mismatch(self):
        current = _current_result(multiplicity=2, twice_T=1, reflection=SymmetryLabel(kind=UNAVAILABLE, value=None))
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_REFLECTION_MISMATCH

    def test_energy_difference_alone_never_fails(self):
        # representative_energy is not part of CurrentGroupResult / the
        # comparison at all -- this test documents that fact structurally.
        assert not hasattr(m.CurrentGroupResult, "representative_energy")

    def _full_current(self, ctt_value=0.5, rho_value=0.25):
        pairs = build_ordered_pairs(len(build_lattice(TRIANGLE_S1.geometry).nodes))
        return _current_result(
            multiplicity=2, twice_T=1, ctt={pair: ctt_value for pair in pairs}, rho={pair: (rho_value, None) for pair in pairs}
        )

    def test_historical_missing_one_ctt_pair_fails(self):
        docs = [d for d in _full_pairs(TRIANGLE_S1) if not (d["observable_kind"] == "C_TT_conn" and tuple(d["identity"]["path"]) == (0, 1))]
        historical = self._historical(documents=tuple(docs))
        result = m.compare_group(historical, self._full_current())
        assert result.status == m.GROUP_MATCH_CTT_PAIR_SET_MISMATCH

    def test_current_missing_one_ctt_pair_fails(self):
        current = self._full_current()
        pairs = dict(current.ctt)
        del pairs[(0, 1)]
        current = _current_result(multiplicity=2, twice_T=1, ctt=pairs, rho=current.rho)
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_CTT_PAIR_SET_MISMATCH

    def test_historical_missing_one_rho_pair_fails(self):
        docs = [d for d in _full_pairs(TRIANGLE_S1) if not (d["observable_kind"] == "rho_QQ" and tuple(d["identity"]["path"]) == (0, 1))]
        historical = self._historical(documents=tuple(docs))
        result = m.compare_group(historical, self._full_current())
        assert result.status == m.GROUP_MATCH_RHO_PAIR_SET_MISMATCH

    def test_current_missing_one_rho_pair_fails(self):
        current = self._full_current()
        pairs = dict(current.rho)
        del pairs[(0, 1)]
        current = _current_result(multiplicity=2, twice_T=1, ctt=current.ctt, rho=pairs)
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_RHO_PAIR_SET_MISMATCH

    def test_rho_null_vs_nonnull_fails(self):
        docs = _full_pairs(TRIANGLE_S1)
        historical = self._historical(documents=docs)
        current = self._full_current()
        current.rho[(0, 1)] = (None, "zero_local_charge_variance")
        result = m.compare_group(historical, current)
        assert result.status == m.GROUP_MATCH_RHO_NULLITY_MISMATCH

    def test_rho_both_null_same_reason_included_as_categorical(self):
        docs = tuple(d if d["observable_kind"] != "rho_QQ" else _rho_doc(*d["identity"]["path"], None, "zero_local_charge_variance") for d in _full_pairs(TRIANGLE_S1))
        historical = self._historical(documents=docs)
        current = self._full_current()
        for pair in list(current.rho):
            current.rho[pair] = (None, "zero_local_charge_variance")
        result = m.compare_group(historical, current)
        assert result.ok
        assert all(record.both_null for record in result.rho_records)

    def test_rho_both_null_different_reason_fails(self):
        docs = tuple(d if d["observable_kind"] != "rho_QQ" else _rho_doc(*d["identity"]["path"], None, "reason_a") for d in _full_pairs(TRIANGLE_S1))
        historical = self._historical(documents=docs)
        current = self._full_current()
        for pair in list(current.rho):
            current.rho[pair] = (None, "reason_b")
        result = m.compare_group(historical, current)
        assert result.status == m.GROUP_MATCH_RHO_NULL_REASON_MISMATCH

    def test_nan_ctt_current_fails(self):
        current = self._full_current()
        current.ctt[(0, 1)] = float("nan")
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_NON_FINITE_VALUE

    def test_inf_ctt_historical_fails(self):
        docs = tuple(d if not (d["observable_kind"] == "C_TT_conn" and tuple(d["identity"]["path"]) == (0, 1)) else _ctt_doc(0, 1, float("inf")) for d in _full_pairs(TRIANGLE_S1))
        historical = self._historical(documents=docs)
        result = m.compare_group(historical, self._full_current())
        assert result.status == m.GROUP_MATCH_NON_FINITE_VALUE

    def test_nan_rho_current_fails(self):
        current = self._full_current()
        current.rho[(0, 1)] = (float("nan"), None)
        result = m.compare_group(self._historical(), current)
        assert result.status == m.GROUP_MATCH_NON_FINITE_VALUE


# ---------------------------------------------------------------------------
# aggregate_metrics -- MAX_ABS.
# ---------------------------------------------------------------------------


class TestAggregateMetrics:
    def test_max_abs_over_multiple_comparisons(self):
        c1 = m.GroupComparison(m.GROUP_MATCH_OK, (m.CttPairRecord(1e-10), m.CttPairRecord(5e-8)), ())
        c2 = m.GroupComparison(m.GROUP_MATCH_OK, (m.CttPairRecord(3e-9),), ())
        metrics = m.aggregate_metrics([c1, c2])
        assert metrics.e_ctt == pytest.approx(5e-8)

    def test_no_ctt_records_gives_none(self):
        metrics = m.aggregate_metrics([])
        assert metrics.e_ctt is None
        assert metrics.e_rho is None

    def test_rho_all_both_null_gives_no_numeric_status(self):
        c = m.GroupComparison(m.GROUP_MATCH_OK, (), (m.RhoPairRecord(None, True),))
        metrics = m.aggregate_metrics([c])
        assert metrics.e_rho is None
        assert metrics.rho_numeric_status == m.RHO_NUMERIC_UNAVAILABLE

    def test_rho_mixed_numeric_and_null(self):
        c = m.GroupComparison(m.GROUP_MATCH_OK, (), (m.RhoPairRecord(None, True), m.RhoPairRecord(3e-9, False)))
        metrics = m.aggregate_metrics([c])
        assert metrics.e_rho == pytest.approx(3e-9)
        assert metrics.rho_numeric_status is None


# ---------------------------------------------------------------------------
# CLI safety, no group selector surface (1C-7c2c hardening).
# ---------------------------------------------------------------------------


class TestCliSafety:
    def test_help_never_computes(self, monkeypatch):
        monkeypatch.setattr(m, "run_calibration", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must never run")))
        with pytest.raises(SystemExit) as excinfo:
            m.main(["--help"])
        assert excinfo.value.code == 0

    def test_default_never_computes(self, monkeypatch):
        monkeypatch.setattr(m, "run_calibration", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must never run")))
        assert m.main([]) == 0

    def test_confirm_requires_historical_output_dir(self):
        with pytest.raises(SystemExit):
            m.main(["--confirm-run-calibration"])

    def test_no_group_selector_flags_exist(self):
        parser = m._build_arg_parser()
        forbidden = {"--group-index", "--twice-T", "--target-id", "--historical-manifest"}
        actual = {action.option_strings[0] for action in parser._actions if action.option_strings}
        assert forbidden.isdisjoint(actual)

    def test_confirm_flag_invokes_run_calibration(self, monkeypatch, capsys):
        artifact = m.CalibrationArtifact(
            status=m.CALIBRATION_SUCCESS,
            calibration_contract_version=m.CALIBRATION_CONTRACT_VERSION,
            schema_version=m.CALIBRATION_ARTIFACT_SCHEMA_VERSION,
            code_commit="a" * 40,
            historical_campaign_id="level1b-reference-v1",
            historical_manifest_fingerprint="f" * 64,
            historical_repository_commit=m.EXPECTED_HISTORICAL_REPOSITORY_COMMIT,
            historical_cases=(),
            environment_fingerprint={},
            e_ctt=1e-12,
            e_rho=1e-13,
            non_regression_ctt_abs_tol=1e-12,
            non_regression_rho_abs_tol=1e-12,
            failure_reasons=(),
        )
        called = {}

        def _fake_run_calibration(*a, **k):
            called["invoked"] = True
            return artifact

        monkeypatch.setattr(m, "run_calibration", _fake_run_calibration)
        exit_code = m.main(["--confirm-run-calibration", "--historical-output-dir", "/some/path"])
        assert called.get("invoked") is True
        assert exit_code == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed["status"] == m.CALIBRATION_SUCCESS


# ---------------------------------------------------------------------------
# No HistoricalGroupSelector / target_id / select_target_group surface.
# ---------------------------------------------------------------------------


class TestNoTargetIdSurface:
    def test_historical_group_selector_does_not_exist(self):
        assert not hasattr(m, "HistoricalGroupSelector")

    def test_historical_calibration_manifest_does_not_exist(self):
        assert not hasattr(m, "HistoricalCalibrationManifest")

    def test_no_target_id_field_anywhere_in_module_dataclasses(self):
        import dataclasses as dc

        for name in ("CurrentGroupResult", "GroupComparison", "CalibrationArtifact", "HistoricalCaseSummary"):
            obj = getattr(m, name)
            field_names = {f.name for f in dc.fields(obj)}
            assert "target_id" not in field_names
            assert "target_twice_T" not in field_names

    def test_module_does_not_import_select_target_group(self):
        # The module docstring explains, by name, why select_target_group
        # is deliberately not used -- so the raw source text legitimately
        # mentions it. What must never exist is a functional import or a
        # module-level binding of it.
        assert not hasattr(m, "select_target_group")
        assert "select_target_group" not in vars(m)
        import inspect

        for _name, function in inspect.getmembers(m, inspect.isfunction):
            if function.__module__ != m.__name__:
                continue
            closure_names = function.__code__.co_names
            assert "select_target_group" not in closure_names


# ---------------------------------------------------------------------------
# Git provenance.
# ---------------------------------------------------------------------------


class TestGitProvenance:
    def test_dirty_worktree_refusal(self, monkeypatch):
        monkeypatch.setattr(m, "_require_clean_git_worktree", lambda repo_root=None: (_ for _ in ()).throw(m._GitProvenanceFailure()))
        with pytest.raises(m.CalibrationInternalFailure):
            m.require_clean_worktree()

    def test_invalid_commit_sha_refusal(self, monkeypatch):
        monkeypatch.setattr(m, "_resolve_git_head_sha", lambda repo_root=None: (_ for _ in ()).throw(m._GitProvenanceFailure()))
        with pytest.raises(m.CalibrationInternalFailure):
            m.resolve_calibration_code_commit()

    def test_missing_required_case_refused_before_any_git_call(self, monkeypatch):
        calls = {"clean": 0, "sha": 0}
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: calls.__setitem__("clean", calls["clean"] + 1))
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: calls.__setitem__("sha", calls["sha"] + 1) or "a" * 40)
        incomplete_plan = tuple(case for case in REAL_PLAN if not (case.geometry == "triangle" and case.spin == 1))
        monkeypatch.setattr(m, "build_campaign_plan", lambda manifest: incomplete_plan)
        with pytest.raises(m.CalibrationConfigError):
            m.run_calibration("/nonexistent", manifest=REAL_MANIFEST)
        assert calls["clean"] == 0
        assert calls["sha"] == 0


# ---------------------------------------------------------------------------
# Firewall.
# ---------------------------------------------------------------------------


class TestFirewall:
    SECRET = "SECRET_INTERNAL_VALUE=123.456789"

    def test_internal_exception_in_case_loop_sanitized(self, monkeypatch, tmp_path):
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "a" * 40)

        fake_index = SimpleNamespace(groups=(), campaign_id="level1b-reference-v1", manifest_fingerprint="f" * 64, repository_commit=m.EXPECTED_HISTORICAL_REPOSITORY_COMMIT)
        monkeypatch.setattr(m, "load_historical_index", lambda *a, **k: fake_index)

        def _raise_with_secret(*a, **k):
            raise ValueError(self.SECRET)

        monkeypatch.setattr(m, "eligible_groups_for_case", _raise_with_secret)

        with pytest.raises(m.CalibrationInternalFailure) as excinfo:
            m.run_calibration(tmp_path, manifest=REAL_MANIFEST)

        assert self.SECRET not in str(excinfo.value)
        assert excinfo.value.__cause__ is None

        import traceback

        rendered = "".join(traceback.format_exception(type(excinfo.value), excinfo.value, excinfo.value.__traceback__))
        assert self.SECRET not in rendered

    def test_memory_error_still_becomes_internal_failure(self, monkeypatch, tmp_path):
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "a" * 40)
        fake_index = SimpleNamespace(groups=(), campaign_id="level1b-reference-v1", manifest_fingerprint="f" * 64, repository_commit=m.EXPECTED_HISTORICAL_REPOSITORY_COMMIT)
        monkeypatch.setattr(m, "load_historical_index", lambda *a, **k: fake_index)
        monkeypatch.setattr(m, "eligible_groups_for_case", lambda *a, **k: (_ for _ in ()).throw(MemoryError()))
        with pytest.raises(m.CalibrationInternalFailure):
            m.run_calibration(tmp_path, manifest=REAL_MANIFEST)


# ---------------------------------------------------------------------------
# run_calibration wiring -- build_case_context/compute_current_group_result
# (the only real-diagonalization entry points) are monkeypatched;
# everything else runs for real against a fully synthetic 11-case
# historical directory (all cases build_campaign_plan(REAL_MANIFEST)
# actually requires -- scripts.level1b_analysis.loader/indexing validate
# the full plan, all-or-nothing).
# ---------------------------------------------------------------------------


def _write_case_artifacts(base_dir: Path, case, *, eligible: bool, ctt_offset: float = 0.0, rho_offset: float = 0.0):
    case_dir = base_dir / "runs" / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    n_nodes = len(build_lattice(case.geometry).nodes)

    def _base(group_index):
        return {
            "schema_version": REAL_MANIFEST.schema_version,
            "repository_commit": m.EXPECTED_HISTORICAL_REPOSITORY_COMMIT,
            "manifest_fingerprint": REAL_MANIFEST.fingerprint,
            "campaign_id": REAL_MANIFEST.campaign_id,
            "identity": {
                "geometry": case.geometry,
                "spin": case.spin,
                "n_flavors": 2,
                "hamiltonian": {
                    "J": list(case.hamiltonian_parameters.J),
                    "h_is_zero": True,
                    "t": case.hamiltonian_parameters.t,
                    "g_E": case.hamiltonian_parameters.g_E,
                    "K": case.hamiltonian_parameters.K,
                },
                "sector": case.sector_id,
                "spectral_group": {
                    "status": COMPLETE_MULTIPLET,
                    "multiplicity": 1,
                    "twice_T": 0,
                    "spectral_window_group_index": group_index,
                    "representative_energy": 1.0 + group_index,
                },
                "path": None,
                "flavor_component": None,
                "normalization": None,
            },
            "provenance": {
                "spectral_status": COMPLETE_MULTIPLET,
                "source_type": "float",
                "source_module": "builtins",
                "match_status": None,
                "covariance_validated": None,
                "scientific_seed": case.scientific_seed,
                "solver_seed": case.solver_seed,
                "validation_rotation_seed": case.validation_rotation_seed,
            },
        }

    documents = []
    group_index = 0
    doc = _base(group_index)
    documents.append({**doc, "record_kind": "symmetry_label", "observable_kind": "flavor_casimir_label", "payload": {"kind": "numeric", "value": {"real": 0.0, "imag": 0.0}}})
    documents.append({**doc, "record_kind": "symmetry_label", "observable_kind": "translation_character", "payload": {"kind": "numeric", "value": {"real": 1.0, "imag": 0.0}}})
    documents.append({**doc, "record_kind": "symmetry_label", "observable_kind": "reflection_character", "payload": {"kind": "numeric", "value": {"real": -1.0, "imag": 0.0}}})
    if eligible:
        for i, j in build_ordered_pairs(n_nodes):
            pair_doc = _base(group_index)
            pair_doc["identity"] = {**pair_doc["identity"], "path": [i, j]}
            documents.append({**pair_doc, "record_kind": "raw_observable", "observable_kind": "C_TT_conn", "payload": 0.5 + ctt_offset})
            documents.append({**pair_doc, "record_kind": "normalized_observable", "observable_kind": "rho_QQ", "payload": {"value": 0.25 + rho_offset, "null_reason": None}})

    ordered_documents, _report = assemble_execution(documents)
    records_path = case_dir / "records.jsonl"
    text = "\n".join(json.dumps(d) for d in ordered_documents) + "\n"
    records_path.write_text(text, encoding="utf-8")
    records_sha256 = m.compute_file_sha256(records_path)

    run_json = {
        "case_id": case.case_id,
        "campaign_id": REAL_MANIFEST.campaign_id,
        "manifest_fingerprint": REAL_MANIFEST.fingerprint,
        "repository_commit": m.EXPECTED_HISTORICAL_REPOSITORY_COMMIT,
        "run_status": "success",
        "record_count": len(ordered_documents),
        "records_sha256": records_sha256,
        "errors": [],
    }
    (case_dir / "run.json").write_text(json.dumps(run_json), encoding="utf-8")


def _build_full_historical_directory(tmp_path: Path, *, ctt_offset: float = 0.0, rho_offset: float = 0.0) -> Path:
    base_dir = tmp_path / "historical"
    for case in REAL_PLAN:
        _write_case_artifacts(base_dir, case, eligible=(case.geometry, case.spin, case.hamiltonian_case_id) in m.REQUIRED_CASE_KEYS, ctt_offset=ctt_offset, rho_offset=rho_offset)
    return base_dir


class TestRunCalibrationWiring:
    def test_full_success(self, tmp_path, monkeypatch):
        historical_dir = _build_full_historical_directory(tmp_path, ctt_offset=0.0, rho_offset=0.0)

        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)

        def _fake_build_case_context(case):
            return SimpleNamespace(case_id=case.case_id)

        known_diffs = {}

        def _fake_current(context, group_index):
            n_nodes_by_case = {case.case_id: len(build_lattice(case.geometry).nodes) for case in REAL_PLAN}
            n_nodes = n_nodes_by_case[context.case_id]
            pairs = build_ordered_pairs(n_nodes)
            offset_ctt = known_diffs.get((context.case_id, "ctt"), 2.3e-13)
            offset_rho = known_diffs.get((context.case_id, "rho"), 1e-14)
            return m.CurrentGroupResult(
                multiplicity=1,
                twice_T=0,
                translation_label=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)),
                reflection_label=SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)),
                ctt={pair: 0.5 + offset_ctt for pair in pairs},
                rho={pair: (0.25 + offset_rho, None) for pair in pairs},
            )

        monkeypatch.setattr(m, "build_case_context", _fake_build_case_context)
        monkeypatch.setattr(m, "compute_current_group_result", _fake_current)

        artifact = m.run_calibration(historical_dir, manifest=REAL_MANIFEST)

        assert artifact.status == m.CALIBRATION_SUCCESS
        assert artifact.failure_reasons == ()
        assert artifact.e_ctt == pytest.approx(2.3e-13)
        assert artifact.non_regression_ctt_abs_tol == pytest.approx(1e-12)
        assert artifact.e_rho == pytest.approx(1e-14)
        assert artifact.non_regression_rho_abs_tol == pytest.approx(1e-13)
        assert artifact.historical_campaign_id == "level1b-reference-v1"
        assert artifact.historical_repository_commit == m.EXPECTED_HISTORICAL_REPOSITORY_COMMIT
        assert len(artifact.historical_cases) == 5
        assert all(case.eligible_group_count == 1 for case in artifact.historical_cases)

        rendered = json.dumps(m._artifact_to_json(artifact))
        assert str(tmp_path) not in rendered

    def test_no_eligible_group_in_one_case_fails(self, tmp_path, monkeypatch):
        base_dir = tmp_path / "historical"
        for case in REAL_PLAN:
            required = (case.geometry, case.spin, case.hamiltonian_case_id) in m.REQUIRED_CASE_KEYS
            eligible = required and not (case.geometry == "ring5" and case.spin == 1)
            _write_case_artifacts(base_dir, case, eligible=eligible)

        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)
        monkeypatch.setattr(m, "build_case_context", lambda case: SimpleNamespace(case_id=case.case_id))
        monkeypatch.setattr(
            m,
            "compute_current_group_result",
            lambda context, group_index: m.CurrentGroupResult(
                multiplicity=1, twice_T=0, translation_label=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)), reflection_label=SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)), ctt={}, rho={}
            ),
        )

        artifact = m.run_calibration(base_dir, manifest=REAL_MANIFEST)
        assert artifact.status == m.CALIBRATION_FAIL
        assert any("no eligible calibration group" in reason for reason in artifact.failure_reasons)

    def test_structural_mismatch_fails_whole_calibration(self, tmp_path, monkeypatch):
        historical_dir = _build_full_historical_directory(tmp_path)
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)
        monkeypatch.setattr(m, "build_case_context", lambda case: SimpleNamespace(case_id=case.case_id))
        monkeypatch.setattr(
            m,
            "compute_current_group_result",
            lambda context, group_index: m.CurrentGroupResult(
                multiplicity=999, twice_T=0, translation_label=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)), reflection_label=SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)), ctt={}, rho={}
            ),
        )
        artifact = m.run_calibration(historical_dir, manifest=REAL_MANIFEST)
        assert artifact.status == m.CALIBRATION_FAIL
        assert artifact.non_regression_ctt_abs_tol is None
        assert artifact.non_regression_rho_abs_tol is None

    def test_fail_status_clears_both_tolerances_even_with_diagnostic_metrics(self, tmp_path, monkeypatch):
        base_dir = tmp_path / "historical"
        for case in REAL_PLAN:
            required = (case.geometry, case.spin, case.hamiltonian_case_id) in m.REQUIRED_CASE_KEYS
            eligible = required and not (case.geometry == "triangle" and case.spin == 1)
            _write_case_artifacts(base_dir, case, eligible=eligible)

        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)
        monkeypatch.setattr(m, "build_case_context", lambda case: SimpleNamespace(case_id=case.case_id))

        def _fake_current(context, group_index):
            n_nodes_by_case = {case.case_id: len(build_lattice(case.geometry).nodes) for case in REAL_PLAN}
            pairs = build_ordered_pairs(n_nodes_by_case[context.case_id])
            return m.CurrentGroupResult(
                multiplicity=1, twice_T=0, translation_label=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)), reflection_label=SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)), ctt={pair: 0.5 for pair in pairs}, rho={pair: (0.25, None) for pair in pairs}
            )

        monkeypatch.setattr(m, "compute_current_group_result", _fake_current)
        artifact = m.run_calibration(base_dir, manifest=REAL_MANIFEST)

        assert artifact.status == m.CALIBRATION_FAIL
        assert any("triangle" in reason and "eligible" in reason for reason in artifact.failure_reasons)
        # the other 4 cases DID produce numeric E_CTT/E_RHO diagnostically
        assert artifact.e_ctt is not None
        assert artifact.non_regression_ctt_abs_tol is None
        assert artifact.non_regression_rho_abs_tol is None

    def test_environment_incomplete_fails(self, tmp_path, monkeypatch):
        historical_dir = _build_full_historical_directory(tmp_path)
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)
        monkeypatch.setattr(m, "build_environment_fingerprint", lambda: {"python_version": "", "numpy_version": "1", "scipy_version": "1", "blas_lapack": {"blas_name": "x", "blas_version": "x", "lapack_name": "x", "lapack_version": "x"}, "platform": "p", "architecture": "a"})
        monkeypatch.setattr(m, "build_case_context", lambda case: SimpleNamespace(case_id=case.case_id))
        monkeypatch.setattr(
            m,
            "compute_current_group_result",
            lambda context, group_index: m.CurrentGroupResult(multiplicity=1, twice_T=0, translation_label=SymmetryLabel(kind=NUMERIC, value=complex(1.0, 0.0)), reflection_label=SymmetryLabel(kind=NUMERIC, value=complex(-1.0, 0.0)), ctt={}, rho={}),
        )
        artifact = m.run_calibration(historical_dir, manifest=REAL_MANIFEST)
        assert artifact.status == m.CALIBRATION_FAIL
        assert any("environment" in reason for reason in artifact.failure_reasons)

    def test_repository_commit_mismatch_raises_config_error(self, tmp_path, monkeypatch):
        base_dir = tmp_path / "historical"
        for case in REAL_PLAN:
            _write_case_artifacts(base_dir, case, eligible=False)
        # Corrupt one run.json's repository_commit to simulate provenance drift.
        run_json_path = base_dir / "runs" / TRIANGLE_S1.case_id / "run.json"
        payload = json.loads(run_json_path.read_text())
        payload["repository_commit"] = "1" * 40
        run_json_path.write_text(json.dumps(payload))
        # Recompute is not needed: records_sha256 unaffected, but the
        # cross-check inside load_validated_cases reads run.json's own
        # repository_commit against the parameter passed to it.
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)
        with pytest.raises(m.CalibrationConfigError):
            m.run_calibration(base_dir, manifest=REAL_MANIFEST)

    def test_missing_case_directory_raises_config_error(self, tmp_path, monkeypatch):
        base_dir = tmp_path / "historical"
        for case in REAL_PLAN:
            if case.case_id == RING5_S1.case_id:
                continue
            _write_case_artifacts(base_dir, case, eligible=False)
        monkeypatch.setattr(m, "require_clean_worktree", lambda repo_root=None: None)
        monkeypatch.setattr(m, "resolve_calibration_code_commit", lambda repo_root=None: "b" * 40)
        with pytest.raises(m.CalibrationConfigError):
            m.run_calibration(base_dir, manifest=REAL_MANIFEST)
