from __future__ import annotations

import json
import math
from fractions import Fraction

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.experiments import (
    Level0Experiment,
    Level0ExperimentResult,
    compute_config_fingerprint,
    dump_level0_experiment_result_json,
    level0_experiment_result_to_json_dict,
    run_level0_experiment,
)
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import Level0Report, SpectrumOptions, SpectrumReport, TermStatistics, build_level0_report


def _hermitian_matrix(diag0: float, diag1: float, off: complex) -> np.ndarray:
    return np.array([[diag0, off], [np.conj(off), diag1]], dtype=np.complex128)


def _params(n_nodes: int, *, t: float = 0.7, g_E: float = 0.6, K: float = 0.5) -> HamiltonianParameters:
    J = tuple(0.3 - 0.2 * i for i in range(n_nodes))
    h = tuple(_hermitian_matrix(0.2 * i, -0.2 * i, 0.15 + 0.1j) for i in range(n_nodes))
    return HamiltonianParameters(J=J, h=h, t=t, g_E=g_E, K=K)


def _config(geometry: str = "triangle", *, external_charges=None, spectrum_options=None) -> Level0Experiment:
    lattice = build_lattice(geometry)
    return Level0Experiment(
        geometry=geometry,
        n_flavors=2,
        spin=1,
        external_charges=external_charges,
        parameters=_params(len(lattice.nodes)),
        spectrum_options=spectrum_options if spectrum_options is not None else SpectrumOptions(),
    )


# ---------------------------------------------------------------------------
# Level0Experiment construction / normalization
# ---------------------------------------------------------------------------


def test_config_rejects_unknown_geometry() -> None:
    with pytest.raises(ValueError):
        _config("not-a-real-geometry")


def test_config_normalizes_none_external_charges_to_zero_fractions() -> None:
    config = _config(external_charges=None)
    assert config.external_charges == (Fraction(0), Fraction(0), Fraction(0))


def test_config_rejects_wrong_length_external_charges() -> None:
    with pytest.raises(ValueError):
        _config(external_charges=(0, 0))


def test_config_rejects_wrong_length_j() -> None:
    lattice = build_lattice("triangle")
    bad_params = HamiltonianParameters(
        J=(0.1, 0.2), h=(_hermitian_matrix(0, 0, 0),) * 3, t=0.0, g_E=0.0, K=0.0
    )
    with pytest.raises(ValueError):
        Level0Experiment(
            geometry="triangle",
            n_flavors=2,
            spin=1,
            external_charges=None,
            parameters=bad_params,
            spectrum_options=SpectrumOptions(),
        )


def test_config_rejects_wrong_length_h() -> None:
    bad_params = HamiltonianParameters(
        J=(0.1, 0.2, 0.3), h=(_hermitian_matrix(0, 0, 0),) * 2, t=0.0, g_E=0.0, K=0.0
    )
    with pytest.raises(ValueError):
        Level0Experiment(
            geometry="triangle",
            n_flavors=2,
            spin=1,
            external_charges=None,
            parameters=bad_params,
            spectrum_options=SpectrumOptions(),
        )


def test_config_canonicalizes_geometry_to_lattice_name() -> None:
    config = _config("triangle")
    assert config.geometry == build_lattice("triangle").name


# ---------------------------------------------------------------------------
# run_level0_experiment matches a manual pipeline call on every scientific
# field (never on timings, which are inherently run-specific)
# ---------------------------------------------------------------------------


def test_run_level0_experiment_matches_manual_pipeline() -> None:
    config = _config("triangle")
    result = run_level0_experiment(config)

    lattice = build_lattice(config.geometry)
    basis = build_basis(lattice, config.n_flavors, config.spin, external_charges=config.external_charges)
    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(
        lattice, config.n_flavors, config.spin, basis.keys, key_index, config.parameters
    )
    expected_report = build_level0_report(
        lattice,
        config.n_flavors,
        config.spin,
        basis,
        terms,
        config.parameters,
        external_charges=config.external_charges,
        spectrum_options=config.spectrum_options,
    )

    assert result.report.dimension == expected_report.dimension
    assert result.report.sector_count == expected_report.sector_count
    assert result.report.spectrum.status == expected_report.spectrum.status
    manual_eigs = [ep.eigenvalue for ep in expected_report.spectrum.eigenpairs]
    result_eigs = [ep.eigenvalue for ep in result.report.spectrum.eigenpairs]
    assert result_eigs == pytest.approx(manual_eigs)


def test_run_level0_experiment_timings_are_finite_and_nonnegative() -> None:
    result = run_level0_experiment(_config("triangle"))
    assert math.isfinite(result.basis_build_seconds) and result.basis_build_seconds >= 0
    assert math.isfinite(result.hamiltonian_build_seconds) and result.hamiltonian_build_seconds >= 0
    assert math.isfinite(result.report_build_seconds) and result.report_build_seconds >= 0


def test_run_level0_experiment_reports_real_software_versions() -> None:
    import numpy as _np
    import scipy as _sp

    result = run_level0_experiment(_config("triangle"))
    assert result.numpy_version == _np.__version__
    assert result.scipy_version == _sp.__version__
    assert result.python_version  # non-empty


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_is_64_lowercase_hex_chars() -> None:
    fingerprint = compute_config_fingerprint(_config("triangle"))
    assert len(fingerprint) == 64
    assert fingerprint == fingerprint.lower()
    assert all(c in "0123456789abcdef" for c in fingerprint)


def test_fingerprint_is_deterministic() -> None:
    config = _config("triangle")
    assert compute_config_fingerprint(config) == compute_config_fingerprint(config)


def test_fingerprint_identical_for_int_and_fraction_external_charges() -> None:
    config_int = _config("triangle", external_charges=(0, 0, 0))
    config_fraction = _config("triangle", external_charges=(Fraction(0), Fraction(0), Fraction(0)))
    assert compute_config_fingerprint(config_int) == compute_config_fingerprint(config_fraction)


def test_fingerprint_changes_when_a_spectrum_option_changes() -> None:
    config_a = _config("triangle", spectrum_options=SpectrumOptions(n_eigenvalues=4))
    config_b = _config("triangle", spectrum_options=SpectrumOptions(n_eigenvalues=5))
    assert compute_config_fingerprint(config_a) != compute_config_fingerprint(config_b)


def test_fingerprint_independent_of_timings_and_versions() -> None:
    config = _config("triangle")
    result_a = run_level0_experiment(config)
    result_b = run_level0_experiment(config)
    # timings will generally differ between the two runs; the fingerprint must not.
    assert result_a.config_fingerprint == result_b.config_fingerprint == compute_config_fingerprint(config)


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


def test_json_export_is_valid_json_with_expected_top_level_keys() -> None:
    result = run_level0_experiment(_config("triangle"))
    text = dump_level0_experiment_result_json(result)
    parsed = json.loads(text)
    assert set(parsed) == {"schema_version", "config_fingerprint", "config", "environment", "timings", "report"}
    assert parsed["config_fingerprint"] == result.config_fingerprint


def test_json_export_contains_no_heavy_objects() -> None:
    result = run_level0_experiment(_config("ring4"))
    text = dump_level0_experiment_result_json(result)
    for forbidden in ("csr_matrix", "indptr", "indices", "eigenvector"):
        assert forbidden not in text


def test_json_export_keys_are_sorted() -> None:
    result = run_level0_experiment(_config("triangle"))
    text = dump_level0_experiment_result_json(result)
    parsed_raw = json.loads(text)
    # re-dump with the same sort_keys policy and compare byte-for-byte
    resorted = json.dumps(parsed_raw, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
    assert text == resorted


def test_json_export_round_trips_fraction_and_complex_fields() -> None:
    config = _config("triangle", external_charges=(Fraction(1, 2), Fraction(-1, 2), 0))
    result = run_level0_experiment(config)
    parsed = level0_experiment_result_to_json_dict(result)
    assert parsed["config"]["external_charges"] == ["1/2", "-1/2", "0/1"]
    first_h_entry = parsed["config"]["parameters"]["h"][0]
    assert first_h_entry[0][1] == [
        float(config.parameters.h[0][0, 1].real),
        float(config.parameters.h[0][0, 1].imag),
    ]


def test_json_dumps_rejects_non_finite_value_via_allow_nan_false() -> None:
    with pytest.raises(ValueError):
        json.dumps({"x": float("nan")}, allow_nan=False)


# ---------------------------------------------------------------------------
# Level0ExperimentResult.__post_init__ invariants
# ---------------------------------------------------------------------------


def _valid_result_kwargs() -> dict:
    result = run_level0_experiment(_config("triangle"))
    return {
        "config": result.config,
        "report": result.report,
        "basis_build_seconds": result.basis_build_seconds,
        "hamiltonian_build_seconds": result.hamiltonian_build_seconds,
        "report_build_seconds": result.report_build_seconds,
        "python_version": result.python_version,
        "numpy_version": result.numpy_version,
        "scipy_version": result.scipy_version,
        "cosmobox_version": result.cosmobox_version,
        "config_fingerprint": result.config_fingerprint,
    }


def _dummy_report(config: Level0Experiment, **overrides) -> Level0Report:
    """A minimal (dimension=0) Level0Report matching `config` except for
    whatever field is overridden -- avoids building a real basis/Hamiltonian
    just to test a single mismatch-detection branch of __post_init__."""
    empty_terms = tuple(
        TermStatistics(name=name, nnz=0, density=0.0, hermiticity_defect=0.0, frobenius_norm=0.0)
        for name in ("dot", "hopping", "electric", "magnetic", "total")
    )
    empty_spectrum = SpectrumReport(
        status="computed",
        method="direct",
        requested_eigenvalues=config.spectrum_options.n_eigenvalues,
        computed_eigenvalues=0,
        tolerance=None,
        reason=None,
        eigenpairs=(),
        spectral_gap=None,
    )
    fields = {
        "lattice_name": config.geometry,
        "n_flavors": config.n_flavors,
        "spin": config.spin,
        "external_charges": config.external_charges,
        "dimension": 0,
        "sector_count": 0,
        "excluded_sector_count": 0,
        "mean_flux_configs_per_occupation": 0.0,
        "max_flux_configs_per_occupation": 0,
        "terms": empty_terms,
        "spectrum": empty_spectrum,
        "spectrum_options": config.spectrum_options,
        "parameters": config.parameters,
    }
    fields.update(overrides)
    return Level0Report(**fields)


# ---------------------------------------------------------------------------
# Correction 1 -- lattice_name / n_flavors / spin consistency
# ---------------------------------------------------------------------------


def test_result_rejects_report_with_mismatched_lattice_name() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["report"] = _dummy_report(kwargs["config"], lattice_name="ring4")
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_rejects_report_with_mismatched_n_flavors() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["report"] = _dummy_report(kwargs["config"], n_flavors=3)
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_rejects_report_with_mismatched_spin() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["report"] = _dummy_report(kwargs["config"], spin=2)
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


# ---------------------------------------------------------------------------
# Correction 2 -- fingerprint must match compute_config_fingerprint(config),
# not just be well-formed
# ---------------------------------------------------------------------------


def test_result_rejects_well_formed_fingerprint_belonging_to_another_config() -> None:
    kwargs = _valid_result_kwargs()
    other_config = _config("ring4")
    kwargs["config_fingerprint"] = compute_config_fingerprint(other_config)
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


# ---------------------------------------------------------------------------
# Correction 3 -- semantic (canonical-payload) equality of parameters, not
# object identity: equivalent-but-distinct objects accepted, any numeric
# difference rejected.
# ---------------------------------------------------------------------------


def test_result_accepts_equivalent_but_distinct_parameters_objects() -> None:
    kwargs = _valid_result_kwargs()
    base = kwargs["config"].parameters
    equivalent_params = HamiltonianParameters(
        J=tuple(base.J),
        h=tuple(np.array(matrix, dtype=np.complex128, copy=True) for matrix in base.h),
        t=base.t,
        g_E=base.g_E,
        K=base.K,
    )
    assert equivalent_params is not base

    kwargs["report"] = _dummy_report(kwargs["config"], parameters=equivalent_params)
    Level0ExperimentResult(**kwargs)  # must not raise


@pytest.mark.parametrize("field", ["J", "h", "t", "g_E", "K"])
def test_result_rejects_report_with_one_differing_parameter_coefficient(field: str) -> None:
    kwargs = _valid_result_kwargs()
    base = kwargs["config"].parameters

    if field == "J":
        altered = HamiltonianParameters(J=(base.J[0] + 1.0,) + base.J[1:], h=base.h, t=base.t, g_E=base.g_E, K=base.K)
    elif field == "h":
        altered_h0 = np.array(base.h[0], dtype=np.complex128, copy=True)
        altered_h0[0, 0] += 1.0  # stays real -> stays Hermitian
        altered = HamiltonianParameters(J=base.J, h=(altered_h0,) + base.h[1:], t=base.t, g_E=base.g_E, K=base.K)
    elif field == "t":
        altered = HamiltonianParameters(J=base.J, h=base.h, t=base.t + 1.0, g_E=base.g_E, K=base.K)
    elif field == "g_E":
        altered = HamiltonianParameters(J=base.J, h=base.h, t=base.t, g_E=base.g_E + 1.0, K=base.K)
    else:
        altered = HamiltonianParameters(J=base.J, h=base.h, t=base.t, g_E=base.g_E, K=base.K + 1.0)

    kwargs["report"] = _dummy_report(kwargs["config"], parameters=altered)
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_rejects_negative_timing() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["basis_build_seconds"] = -0.1
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_rejects_non_finite_timing() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["hamiltonian_build_seconds"] = float("nan")
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_accepts_zero_timing() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["report_build_seconds"] = 0.0
    Level0ExperimentResult(**kwargs)  # must not raise


def test_result_rejects_malformed_fingerprint() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["config_fingerprint"] = "not-a-fingerprint"
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_rejects_uppercase_fingerprint() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["config_fingerprint"] = kwargs["config_fingerprint"].upper()
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_accepts_none_cosmobox_version() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["cosmobox_version"] = None
    Level0ExperimentResult(**kwargs)  # must not raise


def test_result_rejects_empty_python_version() -> None:
    kwargs = _valid_result_kwargs()
    kwargs["python_version"] = ""
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)


def test_result_rejects_report_with_different_spectrum_options() -> None:
    config = _config("triangle")
    lattice = build_lattice(config.geometry)
    basis = build_basis(lattice, config.n_flavors, config.spin, external_charges=config.external_charges)
    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(
        lattice, config.n_flavors, config.spin, basis.keys, key_index, config.parameters
    )
    mismatched_report = build_level0_report(
        lattice,
        config.n_flavors,
        config.spin,
        basis,
        terms,
        config.parameters,
        external_charges=config.external_charges,
        spectrum_options=SpectrumOptions(n_eigenvalues=1),  # deliberately different from config's
    )

    kwargs = _valid_result_kwargs()
    kwargs["report"] = mismatched_report
    with pytest.raises(ValueError):
        Level0ExperimentResult(**kwargs)
