from __future__ import annotations

import pytest

from cosmobox.level1.local_observables import NormalizedMoment
from cosmobox.level1.matching import NOT_APPLICABLE, NUMERIC, EXACT_LABEL_MATCH, MatchOutcome, SpectralGroupMatchKey, SymmetryLabel
from cosmobox.level1.orbits import OrbitComparabilityKey, OrbitElement, OrbitStatistics, ValidatedOrbit
from cosmobox.level1.orbits import _VALIDATION_TOKEN
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE
from cosmobox.level1.results import (
    HamiltonianIdentity,
    OrbitResultPayload,
    Provenance,
    ResultRecord,
    ScientificIdentity,
    SpectralGroupIdentity,
    build_orbit_result_payload,
)
from cosmobox.level1.robustness import INDETERMINATE, ROBUST, RobustnessResult


def _hamiltonian(**overrides) -> HamiltonianIdentity:
    defaults = dict(J=(1.0, 1.0, 1.0), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)
    defaults.update(overrides)
    return HamiltonianIdentity(**defaults)


def _group(**overrides) -> SpectralGroupIdentity:
    defaults = dict(status=COMPLETE_MULTIPLET, multiplicity=2, twice_T=1)
    defaults.update(overrides)
    return SpectralGroupIdentity(**defaults)


def _identity(**overrides) -> ScientificIdentity:
    defaults = dict(
        geometry="triangle",
        spin=2,
        n_flavors=2,
        hamiltonian=_hamiltonian(),
        sector="default",
        spectral_group=_group(),
        path=None,
        flavor_component=None,
        normalization=None,
    )
    defaults.update(overrides)
    return ScientificIdentity(**defaults)


def _provenance(**overrides) -> Provenance:
    defaults = dict(
        spectral_status=COMPLETE_MULTIPLET,
        source_type="X",
        source_module="cosmobox.level1.local_observables",
        match_status=None,
        covariance_validated=None,
    )
    defaults.update(overrides)
    return Provenance(**defaults)


# ---------------------------------------------------------------------------
# HamiltonianIdentity / SpectralGroupIdentity / ScientificIdentity / Provenance
# ---------------------------------------------------------------------------


def test_hamiltonian_identity_rejects_empty_J() -> None:
    with pytest.raises(ValueError, match="J"):
        HamiltonianIdentity(J=(), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)


def test_hamiltonian_identity_rejects_non_finite_J() -> None:
    with pytest.raises(ValueError, match="finite"):
        HamiltonianIdentity(J=(float("nan"),), h_is_zero=True, t=1.0, g_E=1.0, K=1.0)


def test_spectral_group_identity_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        SpectralGroupIdentity(status="degenerate", multiplicity=1, twice_T=0)


def test_spectral_group_identity_rejects_nonpositive_multiplicity() -> None:
    with pytest.raises(ValueError, match="multiplicity"):
        SpectralGroupIdentity(status=COMPLETE_MULTIPLET, multiplicity=0, twice_T=0)


def test_spectral_group_identity_accepts_none_twice_t() -> None:
    group = SpectralGroupIdentity(status=COMPLETE_MULTIPLET, multiplicity=1, twice_T=None)
    assert group.twice_T is None


def test_scientific_identity_rejects_wrong_n_flavors() -> None:
    with pytest.raises(ValueError, match="n_flavors"):
        _identity(n_flavors=3)


def test_scientific_identity_rejects_empty_path() -> None:
    with pytest.raises(ValueError, match="path"):
        _identity(path=())


def test_provenance_rejects_invalid_spectral_status() -> None:
    with pytest.raises(ValueError, match="spectral_status"):
        _provenance(spectral_status="degenerate")


def test_provenance_rejects_empty_source_type() -> None:
    with pytest.raises(ValueError, match="source_type"):
        _provenance(source_type="")


# ---------------------------------------------------------------------------
# ResultRecord -- record_kind / observable_kind / payload-type coherence
# ---------------------------------------------------------------------------


def test_result_record_raw_observable_accepts_float() -> None:
    record = ResultRecord(_identity(), _provenance(), "raw_observable", "C_QQ_raw", 0.5)
    assert record.payload == 0.5


def test_result_record_raw_observable_O_ij_raw_requires_complex() -> None:
    with pytest.raises(ValueError, match="payload"):
        ResultRecord(_identity(), _provenance(), "raw_observable", "O_ij_raw", 0.5)
    record = ResultRecord(_identity(), _provenance(), "raw_observable", "O_ij_raw", 0.5 + 0j)
    assert record.payload == 0.5 + 0j


def test_result_record_rejects_unknown_record_kind() -> None:
    with pytest.raises(ValueError, match="record_kind"):
        ResultRecord(_identity(), _provenance(), "bogus_kind", "C_QQ_raw", 0.5)


def test_result_record_rejects_observable_kind_not_valid_for_record_kind() -> None:
    with pytest.raises(ValueError, match="observable_kind"):
        ResultRecord(_identity(), _provenance(), "raw_observable", "flavor_singlet", 0.5)


def test_result_record_rejects_wrong_payload_type_for_normalized_observable() -> None:
    with pytest.raises(ValueError, match="payload"):
        ResultRecord(_identity(), _provenance(), "normalized_observable", "rho_QQ", 0.5)


def test_result_record_normalized_observable_accepts_normalized_moment() -> None:
    moment = NormalizedMoment(value=0.1, null_reason=None)
    record = ResultRecord(_identity(), _provenance(), "normalized_observable", "rho_QQ", moment)
    assert record.payload is moment


def test_result_record_symmetry_label_restricts_observable_kind() -> None:
    label = SymmetryLabel(kind=NOT_APPLICABLE, value=None)
    with pytest.raises(ValueError, match="observable_kind"):
        ResultRecord(_identity(), _provenance(), "symmetry_label", "C_QQ_raw", label)
    record = ResultRecord(_identity(), _provenance(), "symmetry_label", "translation_character", label)
    assert record.payload is label


# ---------------------------------------------------------------------------
# Cross-object guard: no definitive verdict for a partial_subspace identity
# ---------------------------------------------------------------------------


def test_result_record_rejects_definitive_verdict_on_partial_subspace_identity() -> None:
    partial_identity = _identity(spectral_group=_group(status=PARTIAL_SUBSPACE))
    result = RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    with pytest.raises(ValueError, match="partial_subspace"):
        ResultRecord(partial_identity, _provenance(), "robustness", "gamma_O", result)


def test_result_record_accepts_indeterminate_verdict_on_partial_subspace_identity() -> None:
    partial_identity = _identity(spectral_group=_group(status=PARTIAL_SUBSPACE))
    result = RobustnessResult(verdict=INDETERMINATE, null_reason="truncated_spectral_group", gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    record = ResultRecord(partial_identity, _provenance(), "robustness", "gamma_O", result)
    assert record.payload is result


def test_result_record_accepts_definitive_verdict_on_complete_multiplet_identity() -> None:
    result = RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    record = ResultRecord(_identity(), _provenance(), "robustness", "gamma_O", result)
    assert record.payload is result


# ---------------------------------------------------------------------------
# matching / robustness payloads
# ---------------------------------------------------------------------------


def test_result_record_matching_accepts_match_outcome() -> None:
    matched = SpectralGroupMatchKey(
        geometry="triangle", hamiltonian_identity_without_spin="ref", sector_identity="default",
        status=COMPLETE_MULTIPLET, multiplicity=2, twice_T=1,
        translation_label=SymmetryLabel(NUMERIC, 1 + 0j), reflection_label=SymmetryLabel(NOT_APPLICABLE, None),
    )
    outcome = MatchOutcome(EXACT_LABEL_MATCH, matched)
    record = ResultRecord(_identity(), _provenance(), "matching", "gamma_O", outcome)
    assert record.payload is outcome


def test_result_record_matching_rejects_wrong_payload_type() -> None:
    with pytest.raises(ValueError, match="payload"):
        ResultRecord(_identity(), _provenance(), "matching", "gamma_O", "exact_label_match")


# ---------------------------------------------------------------------------
# OrbitResultPayload -- constructible only from a real ValidatedOrbit
# ---------------------------------------------------------------------------


def _orbit_key(**overrides) -> OrbitComparabilityKey:
    defaults = dict(
        orbit_family="fam", path_length=1, spectral_group_key="g0", status=COMPLETE_MULTIPLET,
        observable_kind="O_ij_raw", normalization="raw_G", flavor_component="alpha0_beta1", hamiltonian_identity="ref",
    )
    defaults.update(overrides)
    return OrbitComparabilityKey(**defaults)


def test_build_orbit_result_payload_rejects_non_validated_orbit() -> None:
    with pytest.raises(ValueError, match="ValidatedOrbit"):
        build_orbit_result_payload("not an orbit")  # type: ignore[arg-type]


def test_build_orbit_result_payload_from_real_validated_orbit() -> None:
    key = _orbit_key()
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j), OrbitElement(key, 1 + 1j)), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    assert payload.element_count == 2
    assert payload.statistics.orbit_mean == pytest.approx(1 + 1j)
    assert payload.comparability_key == key


def test_orbit_result_payload_rejects_zero_element_count() -> None:
    key = _orbit_key()
    statistics = OrbitStatistics(orbit_mean=1 + 1j, orbit_max_pairwise_spread=0.0, orbit_covariance_defect=0.0)
    with pytest.raises(ValueError, match="element_count"):
        OrbitResultPayload(statistics=statistics, comparability_key=key, element_count=0)
