from __future__ import annotations

import pytest

from cosmobox.level1.local_observables import NormalizedMoment
from cosmobox.level1.matching import (
    EXACT_LABEL_MATCH,
    NOT_APPLICABLE,
    NUMERIC,
    MatchOutcome,
    SpectralGroupMatchKey,
    SymmetryLabel,
)
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
    build_result_record,
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


def _matching_orbit_identity(**overrides) -> ScientificIdentity:
    defaults = dict(flavor_component="alpha0_beta1", normalization="raw_G")
    defaults.update(overrides)
    return _identity(**defaults)


def _derived_provenance(payload: object, *, spectral_status: str = COMPLETE_MULTIPLET, **overrides) -> Provenance:
    """A correctly-derived Provenance for `payload` -- mirrors what
    build_result_record computes internally, for tests that need to
    construct ResultRecord directly (not via the factory)."""
    defaults = dict(
        spectral_status=spectral_status,
        source_type=type(payload).__name__,
        source_module=type(payload).__module__,
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
        Provenance(spectral_status="degenerate", source_type="float", source_module="builtins", match_status=None, covariance_validated=None)


def test_provenance_rejects_empty_source_type() -> None:
    with pytest.raises(ValueError, match="source_type"):
        Provenance(spectral_status=COMPLETE_MULTIPLET, source_type="", source_module="builtins", match_status=None, covariance_validated=None)


# ---------------------------------------------------------------------------
# build_result_record -- the recommended construction path
# ---------------------------------------------------------------------------


def test_build_result_record_derives_source_type_and_module() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    assert record.provenance.source_type == "float"
    assert record.provenance.source_module == "builtins"


def test_build_result_record_derives_spectral_status_from_identity() -> None:
    partial_identity = _identity(spectral_group=_group(status=PARTIAL_SUBSPACE))
    result = RobustnessResult(verdict=INDETERMINATE, null_reason="truncated_spectral_group", gamma_o=None, difference=None, amplitude=None)
    record = build_result_record(partial_identity, "robustness", "gamma_O", result)
    assert record.provenance.spectral_status == PARTIAL_SUBSPACE


def test_build_result_record_keeps_match_status_and_covariance_validated_as_external_arguments() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5, match_status="exact_label_match", covariance_validated=True)
    assert record.provenance.match_status == "exact_label_match"
    assert record.provenance.covariance_validated is True


# ---------------------------------------------------------------------------
# Provenance cannot lie about payload origin (direct ResultRecord path)
# ---------------------------------------------------------------------------


def test_result_record_rejects_provenance_source_type_mismatch() -> None:
    provenance = _derived_provenance(0.5, source_type="NormalizedMoment")
    with pytest.raises(ValueError, match="source_type"):
        ResultRecord(_identity(), provenance, "raw_observable", "C_QQ_raw", 0.5)


def test_result_record_rejects_provenance_source_module_mismatch() -> None:
    provenance = _derived_provenance(0.5, source_module="cosmobox.level1.local_observables")
    with pytest.raises(ValueError, match="source_module"):
        ResultRecord(_identity(), provenance, "raw_observable", "C_QQ_raw", 0.5)


def test_result_record_rejects_provenance_spectral_status_mismatch() -> None:
    provenance = _derived_provenance(0.5, spectral_status=PARTIAL_SUBSPACE)  # identity below is complete_multiplet
    with pytest.raises(ValueError, match="spectral_status"):
        ResultRecord(_identity(), provenance, "raw_observable", "C_QQ_raw", 0.5)


def test_result_record_accepts_correctly_derived_provenance() -> None:
    record = ResultRecord(_identity(), _derived_provenance(0.5), "raw_observable", "C_QQ_raw", 0.5)
    assert record.payload == 0.5


# ---------------------------------------------------------------------------
# ResultRecord -- record_kind / observable_kind / payload-type coherence
# ---------------------------------------------------------------------------


def test_result_record_raw_observable_accepts_float() -> None:
    record = build_result_record(_identity(), "raw_observable", "C_QQ_raw", 0.5)
    assert record.payload == 0.5


def test_result_record_raw_observable_O_ij_raw_requires_complex() -> None:
    with pytest.raises(ValueError, match="payload"):
        build_result_record(_identity(), "raw_observable", "O_ij_raw", 0.5)
    record = build_result_record(_identity(), "raw_observable", "O_ij_raw", 0.5 + 0j)
    assert record.payload == 0.5 + 0j


def test_result_record_rejects_unknown_record_kind() -> None:
    with pytest.raises(ValueError, match="record_kind"):
        build_result_record(_identity(), "bogus_kind", "C_QQ_raw", 0.5)


def test_result_record_rejects_observable_kind_not_valid_for_record_kind() -> None:
    with pytest.raises(ValueError, match="observable_kind"):
        build_result_record(_identity(), "raw_observable", "flavor_singlet", 0.5)


def test_result_record_rejects_wrong_payload_type_for_normalized_observable() -> None:
    with pytest.raises(ValueError, match="payload"):
        build_result_record(_identity(), "normalized_observable", "rho_QQ", 0.5)


def test_result_record_normalized_observable_accepts_normalized_moment() -> None:
    moment = NormalizedMoment(value=0.1, null_reason=None)
    record = build_result_record(_identity(), "normalized_observable", "rho_QQ", moment)
    assert record.payload is moment


def test_result_record_symmetry_label_restricts_observable_kind() -> None:
    label = SymmetryLabel(kind=NOT_APPLICABLE, value=None)
    with pytest.raises(ValueError, match="observable_kind"):
        build_result_record(_identity(), "symmetry_label", "C_QQ_raw", label)
    record = build_result_record(_identity(), "symmetry_label", "translation_character", label)
    assert record.payload is label


# ---------------------------------------------------------------------------
# Cross-object guard: no definitive verdict for a partial_subspace identity
# ---------------------------------------------------------------------------


def test_result_record_rejects_definitive_verdict_on_partial_subspace_identity() -> None:
    partial_identity = _identity(spectral_group=_group(status=PARTIAL_SUBSPACE))
    result = RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    with pytest.raises(ValueError, match="partial_subspace"):
        build_result_record(partial_identity, "robustness", "gamma_O", result)


def test_result_record_accepts_indeterminate_verdict_on_partial_subspace_identity() -> None:
    partial_identity = _identity(spectral_group=_group(status=PARTIAL_SUBSPACE))
    result = RobustnessResult(verdict=INDETERMINATE, null_reason="truncated_spectral_group", gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    record = build_result_record(partial_identity, "robustness", "gamma_O", result)
    assert record.payload is result


def test_result_record_accepts_definitive_verdict_on_complete_multiplet_identity() -> None:
    result = RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)
    record = build_result_record(_identity(), "robustness", "gamma_O", result)
    assert record.payload is result


# ---------------------------------------------------------------------------
# Payload-embedded spectral status must match identity.spectral_group.status
# ---------------------------------------------------------------------------


def test_result_record_rejects_flavor_matrix_status_mismatch() -> None:
    import numpy as np
    from cosmobox.level1.flavor import FlavorCorrelatorMatrix

    matrix = FlavorCorrelatorMatrix(matrix=np.eye(2, dtype=np.complex128), status=PARTIAL_SUBSPACE)
    with pytest.raises(ValueError, match="spectral status"):
        build_result_record(_identity(), "flavor_diagnostic", "raw_G", matrix)


def test_result_record_rejects_hermitian_diagnostic_status_mismatch() -> None:
    from cosmobox.level1.diagnostics import HermitianRestrictedDiagnostics

    diag = HermitianRestrictedDiagnostics(status=PARTIAL_SUBSPACE, trace=4.0, eigenvalues=(1.0, 3.0), minimum=1.0, maximum=3.0, spectral_range=2.0, frobenius_norm=10.0**0.5, hermiticity_defect=0.0)
    with pytest.raises(ValueError, match="spectral status"):
        build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", diag)


def test_result_record_rejects_non_hermitian_diagnostic_status_mismatch() -> None:
    from cosmobox.level1.diagnostics import NonHermitianRestrictedDiagnostics

    diag = NonHermitianRestrictedDiagnostics(status=PARTIAL_SUBSPACE, trace=1 + 1j, singular_values=(3.0, 1.0), frobenius_norm=10.0**0.5)
    with pytest.raises(ValueError, match="spectral status"):
        build_result_record(_identity(), "restricted_diagnostic", "C_QQ_raw", diag)


def test_result_record_rejects_orbit_comparability_key_status_mismatch() -> None:
    key = OrbitComparabilityKey(orbit_family="fam", path_length=1, spectral_group_key="g0", status=PARTIAL_SUBSPACE, observable_kind="O_ij_raw", normalization="raw_G", flavor_component="alpha0_beta1", hamiltonian_identity="ref")
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    with pytest.raises(ValueError, match="spectral status"):
        build_result_record(_matching_orbit_identity(), "orbit_statistic", "O_ij_raw", payload)


def test_result_record_rejects_matched_group_status_mismatch() -> None:
    # matched.status diverges from identity.spectral_group.status (complete
    # in identity, partial in the matched group) -- caught by the generic
    # payload-embedded-status cross-check before the matching-specific one.
    matched = SpectralGroupMatchKey(geometry="triangle", hamiltonian_identity_without_spin="ref", sector_identity="default", status=PARTIAL_SUBSPACE, multiplicity=2, twice_T=1, translation_label=SymmetryLabel(NUMERIC, 1 + 0j), reflection_label=SymmetryLabel(NOT_APPLICABLE, None))
    outcome = MatchOutcome(EXACT_LABEL_MATCH, matched)
    with pytest.raises(ValueError, match="spectral status"):
        build_result_record(_identity(), "matching", "gamma_O", outcome)


def test_result_record_rejects_exact_match_with_partial_group_even_when_identity_agrees() -> None:
    # Both identity.spectral_group.status AND matched.status are
    # partial_subspace (so the generic cross-check passes), but
    # exact_label_match must still never be paired with a partial group --
    # this exercises the matching-specific guard on its own.
    partial_identity = _identity(spectral_group=_group(status=PARTIAL_SUBSPACE))
    matched = SpectralGroupMatchKey(geometry="triangle", hamiltonian_identity_without_spin="ref", sector_identity="default", status=PARTIAL_SUBSPACE, multiplicity=2, twice_T=1, translation_label=SymmetryLabel(NUMERIC, 1 + 0j), reflection_label=SymmetryLabel(NOT_APPLICABLE, None))
    outcome = MatchOutcome(EXACT_LABEL_MATCH, matched)
    with pytest.raises(ValueError, match="matched_group.status"):
        build_result_record(partial_identity, "matching", "gamma_O", outcome)


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
    record = build_result_record(_identity(), "matching", "gamma_O", outcome)
    assert record.payload is outcome


def test_result_record_matching_rejects_wrong_payload_type() -> None:
    with pytest.raises(ValueError, match="payload"):
        build_result_record(_identity(), "matching", "gamma_O", "exact_label_match")


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


def test_result_record_orbit_statistic_full_coherence_succeeds() -> None:
    key = _orbit_key()
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    record = build_result_record(_matching_orbit_identity(), "orbit_statistic", "O_ij_raw", payload)
    assert record.payload is payload


def test_result_record_orbit_statistic_rejects_observable_kind_mismatch() -> None:
    key = _orbit_key(observable_kind="O_ij_raw")
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    with pytest.raises(ValueError, match="observable_kind"):
        build_result_record(_matching_orbit_identity(), "orbit_statistic", "flavor_singlet", payload)


def test_result_record_orbit_statistic_rejects_normalization_mismatch() -> None:
    key = _orbit_key(normalization="raw_G")
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    identity = _matching_orbit_identity(normalization="G_occ")
    with pytest.raises(ValueError, match="normalization"):
        build_result_record(identity, "orbit_statistic", "O_ij_raw", payload)


def test_result_record_orbit_statistic_rejects_flavor_component_mismatch() -> None:
    key = _orbit_key(flavor_component="alpha0_beta1")
    orbit = ValidatedOrbit(key=key, elements=(OrbitElement(key, 1 + 1j),), _token=_VALIDATION_TOKEN)
    payload = build_orbit_result_payload(orbit)
    identity = _matching_orbit_identity(flavor_component="alpha1_beta0")
    with pytest.raises(ValueError, match="flavor_component"):
        build_result_record(identity, "orbit_statistic", "O_ij_raw", payload)


# ---------------------------------------------------------------------------
# ROBUSTNESS_OBSERVABLE_KINDS -- D013/D018's closed robustness-verdict list
# ---------------------------------------------------------------------------


def _robustness_payload() -> RobustnessResult:
    return RobustnessResult(verdict=ROBUST, null_reason=None, gamma_o=NormalizedMoment(0.01, None), difference=0.01, amplitude=1.0)


@pytest.mark.parametrize("observable_kind", ["gamma_O", "G_occ", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio"])
def test_robustness_accepts_every_closed_list_observable_kind(observable_kind: str) -> None:
    record = build_result_record(_identity(), "robustness", observable_kind, _robustness_payload())
    assert record.observable_kind == observable_kind


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
def test_robustness_rejects_observable_kind_outside_the_closed_list(observable_kind: str) -> None:
    with pytest.raises(ValueError, match="observable_kind"):
        build_result_record(_identity(), "robustness", observable_kind, _robustness_payload())


def test_robustness_observable_kinds_constant_excludes_path_phase_coherence() -> None:
    # path_phase_coherence is frozen by D013 as a secondary robustness
    # observable, but no level1 module computes it yet -- it must stay
    # absent from the effective enum until one does.
    from cosmobox.level1.results import ROBUSTNESS_OBSERVABLE_KINDS

    assert "path_phase_coherence" not in ROBUSTNESS_OBSERVABLE_KINDS
    assert set(ROBUSTNESS_OBSERVABLE_KINDS) == {"gamma_O", "G_occ", "rho_QQ", "C_TT_conn", "flavor_singular_value_ratio"}
