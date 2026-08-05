from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosmobox.level0 import compute_config_fingerprint
from cosmobox.level0.degeneracy import DegeneracyReport, SpectralLevelGroup
from cosmobox.level0.symmetries import OperatorKind, SymmetrySectorDiagnostic
from scripts.level0_symmetry_campaign.analysis import (
    SYMMETRY_JSON_SCHEMA_VERSION,
    SYMMETRY_OPERATOR_NAMES,
    SymmetryExperimentResult,
    _check_commutator_restriction_consistency,
    run_symmetry_experiment,
    symmetry_experiment_result_to_json_dict,
)
from scripts.level0_symmetry_campaign.grid import (
    J_BREAK_GEOMETRIES,
    J_BROKEN_NODE0,
    J_REFERENCE,
    MAIN_GEOMETRIES,
    N_EIGENVALUES,
    SPIN_REFERENCE,
    SYMMETRY_CAMPAIGN_EXPECTED_RUNS,
    SYMMETRY_CAMPAIGN_THRESHOLDS,
    build_symmetry_campaign_specs,
    spec_to_experiment,
    validate_unique_fingerprints,
)
from scripts.level0_symmetry_campaign.outputs import (
    SUMMARY_CSV_FIELDS,
    _summary_row,
    validate_existing_run,
    write_manifest,
)
from scripts.level0_symmetry_campaign.runner import run_campaign

# ---------------------------------------------------------------------------
# grid.py
# ---------------------------------------------------------------------------


def test_grid_has_exactly_8_specs() -> None:
    assert len(build_symmetry_campaign_specs()) == SYMMETRY_CAMPAIGN_EXPECTED_RUNS


def test_grid_experiment_ids_are_unique() -> None:
    specs = build_symmetry_campaign_specs()
    ids = [spec.experiment_id for spec in specs]
    assert len(set(ids)) == len(ids)


def test_grid_fingerprints_are_unique() -> None:
    fingerprints = validate_unique_fingerprints(build_symmetry_campaign_specs())
    assert len(set(fingerprints.values())) == SYMMETRY_CAMPAIGN_EXPECTED_RUNS


def test_grid_is_deterministic_across_calls() -> None:
    a = build_symmetry_campaign_specs()
    b = build_symmetry_campaign_specs()
    assert a == b


def test_grid_uses_spin_2_flavor_2_eigenvalues_16_and_zero_external_charges() -> None:
    for spec in build_symmetry_campaign_specs():
        assert spec.spin == SPIN_REFERENCE == 2
        config = spec_to_experiment(spec)
        assert config.n_flavors == 2
        assert config.spectrum_options.n_eigenvalues == N_EIGENVALUES == 16
        assert all(q == 0 for q in config.external_charges)


def test_grid_reference_points_cover_triangle_ring4_ring5() -> None:
    specs = build_symmetry_campaign_specs()
    reference_geometries = {spec.geometry for spec in specs if "reference" in spec.roles}
    assert reference_geometries == set(MAIN_GEOMETRIES) == {"triangle", "ring4", "ring5"}


def test_grid_h_eta_sweep_is_ring5_only() -> None:
    specs = build_symmetry_campaign_specs()
    h_eta_specs = [spec for spec in specs if "h_sensitivity" in spec.roles]
    assert len(h_eta_specs) == 3
    assert all(spec.geometry == "ring5" for spec in h_eta_specs)
    assert sorted(spec.h_eta for spec in h_eta_specs) == [0.1, 0.25, 0.5]


def test_grid_j_break_is_triangle_and_ring5_only() -> None:
    specs = build_symmetry_campaign_specs()
    j_break_specs = [spec for spec in specs if "j_break" in spec.roles]
    assert {spec.geometry for spec in j_break_specs} == set(J_BREAK_GEOMETRIES) == {"triangle", "ring5"}
    assert all(spec.j_pattern == "broken_node0" for spec in j_break_specs)


def test_j_broken_node0_pattern_is_exactly_j0_1_5_others_1() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/j_break")
    config = spec_to_experiment(spec)
    assert config.parameters.J[0] == pytest.approx(J_BROKEN_NODE0) == pytest.approx(1.5)
    assert all(J == pytest.approx(J_REFERENCE) == pytest.approx(1.0) for J in config.parameters.J[1:])


def test_uniform_j_pattern_is_all_ones() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "ring4/reference")
    config = spec_to_experiment(spec)
    assert all(J == pytest.approx(J_REFERENCE) for J in config.parameters.J)


# ---------------------------------------------------------------------------
# analysis.py -- run_symmetry_experiment / JSON export
# ---------------------------------------------------------------------------


def test_run_symmetry_experiment_produces_diagnostics_for_every_operator_and_group() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/reference")
    config = spec_to_experiment(spec)
    result = run_symmetry_experiment(config)

    degeneracy = result.base.report.spectrum.degeneracy
    assert degeneracy is not None
    assert len(result.diagnostics) == len(SYMMETRY_OPERATOR_NAMES) * len(degeneracy.groups)
    names = {d.operator_name for d in result.diagnostics}
    assert names == set(SYMMETRY_OPERATOR_NAMES)


def test_json_export_has_required_symmetry_fields() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/reference")
    result = run_symmetry_experiment(spec_to_experiment(spec))
    payload = symmetry_experiment_result_to_json_dict(result)

    assert payload["schema_version"] == SYMMETRY_JSON_SCHEMA_VERSION
    symmetry = payload["symmetry"]
    assert symmetry["operators"] == list(SYMMETRY_OPERATOR_NAMES)
    for diagnostic in symmetry["diagnostics"]:
        assert "spectral_group_lower_bound_only" in diagnostic
        assert "spectral_group_multiplicity_observed" in diagnostic
        assert isinstance(diagnostic["restricted_eigenvalues"], list)
        for pair in diagnostic["restricted_eigenvalues"]:
            assert len(pair) == 2

    # solver method / dimension / published eigenvalue count / timings recorded
    assert symmetry["solver_method"] in ("dense", "sparse_eigsh")
    assert symmetry["dimension"] == payload["report"]["dimension"]
    assert symmetry["published_eigenvalues"] == payload["report"]["spectrum"]["computed_eigenvalues"]
    assert "symmetry_operators_build_seconds" in payload["timings"]
    assert "symmetry_diagnostics_seconds" in payload["timings"]


def test_json_export_is_json_serializable_with_no_nan() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "ring5/j_break")
    result = run_symmetry_experiment(spec_to_experiment(spec))
    payload = symmetry_experiment_result_to_json_dict(result)
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
    assert json.loads(text) == payload


def test_json_export_contains_no_automatic_physical_interpretation() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "ring5/j_break")
    result = run_symmetry_experiment(spec_to_experiment(spec))
    payload = symmetry_experiment_result_to_json_dict(result)
    text = json.dumps(payload).lower()
    for forbidden in ("is_symmetric", "symmetry_confirmed", "symmetry_broken", "conserved", "verdict"):
        assert forbidden not in text


# ---------------------------------------------------------------------------
# analysis._check_commutator_restriction_consistency
# ---------------------------------------------------------------------------


def _group(start: int, end: int, *, lower_bound_only: bool, energy: float = 0.0) -> SpectralLevelGroup:
    return SpectralLevelGroup(
        start_index=start,
        end_index_exclusive=end,
        representative_energy=energy,
        min_energy=energy,
        max_energy=energy,
        multiplicity_observed=end - start,
        lower_bound_only=lower_bound_only,
    )


def _degeneracy(groups: tuple[SpectralLevelGroup, ...]) -> DegeneracyReport:
    return DegeneracyReport(
        tolerance=1e-10,
        ground_multiplicity_observed=groups[0].multiplicity_observed,
        first_distinct_energy=None if len(groups) < 2 else groups[1].representative_energy,
        first_distinct_gap=(
            None if len(groups) < 2 else groups[1].representative_energy - groups[0].representative_energy
        ),
        groups=groups,
        window_truncated=any(g.lower_bound_only for g in groups),
    )


def _diagnostic(*, group_index: int, restriction_defect: float, commutator_defect: float | None) -> SymmetrySectorDiagnostic:
    return SymmetrySectorDiagnostic(
        operator_name="X",
        operator_kind=OperatorKind.HERMITIAN,
        spectral_group_index=group_index,
        restricted_eigenvalues=(1.0 + 0j,),
        restriction_defect=restriction_defect,
        restricted_hermiticity_defect=0.0,
        restricted_unitarity_defect=None,
        subspace_orthonormality_defect=0.0,
        commutator_defect=commutator_defect,
    )


def test_consistency_check_passes_when_small_commutator_matches_small_restriction() -> None:
    groups = (_group(0, 1, lower_bound_only=False),)
    diagnostics = (_diagnostic(group_index=0, restriction_defect=1e-12, commutator_defect=1e-12),)
    _check_commutator_restriction_consistency(diagnostics, _degeneracy(groups))  # must not raise


def test_consistency_check_passes_when_commutator_is_large_regardless_of_restriction() -> None:
    groups = (_group(0, 1, lower_bound_only=False),)
    diagnostics = (_diagnostic(group_index=0, restriction_defect=0.9, commutator_defect=5.0),)
    _check_commutator_restriction_consistency(diagnostics, _degeneracy(groups))  # must not raise


def test_consistency_check_raises_on_small_commutator_with_large_restriction_non_truncated() -> None:
    groups = (_group(0, 1, lower_bound_only=False),)
    diagnostics = (_diagnostic(group_index=0, restriction_defect=0.5, commutator_defect=1e-12),)
    with pytest.raises(RuntimeError, match="commutator_defect"):
        _check_commutator_restriction_consistency(diagnostics, _degeneracy(groups))


def test_consistency_check_does_not_raise_on_truncated_group_even_with_large_restriction() -> None:
    groups = (_group(0, 1, lower_bound_only=False, energy=0.0), _group(1, 2, lower_bound_only=True, energy=1.0))
    diagnostics = (
        _diagnostic(group_index=0, restriction_defect=1e-12, commutator_defect=1e-12),
        _diagnostic(group_index=1, restriction_defect=0.9, commutator_defect=1e-12),
    )
    _check_commutator_restriction_consistency(diagnostics, _degeneracy(groups))  # must not raise


def test_consistency_check_skips_none_commutator() -> None:
    groups = (_group(0, 1, lower_bound_only=False),)
    diagnostics = (_diagnostic(group_index=0, restriction_defect=0.9, commutator_defect=None),)
    _check_commutator_restriction_consistency(diagnostics, _degeneracy(groups))  # must not raise


# ---------------------------------------------------------------------------
# SymmetryExperimentResult.__post_init__
# ---------------------------------------------------------------------------


def test_symmetry_experiment_result_rejects_empty_diagnostics() -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/reference")
    result = run_symmetry_experiment(spec_to_experiment(spec))
    with pytest.raises(ValueError, match="diagnostics"):
        SymmetryExperimentResult(
            base=result.base,
            diagnostics=(),
            symmetry_operators_build_seconds=0.0,
            symmetry_diagnostics_seconds=0.0,
        )


@pytest.mark.parametrize("bad_value", [-1.0, float("nan"), float("inf")])
def test_symmetry_experiment_result_rejects_bad_timings(bad_value: float) -> None:
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/reference")
    result = run_symmetry_experiment(spec_to_experiment(spec))
    with pytest.raises(ValueError):
        SymmetryExperimentResult(
            base=result.base,
            diagnostics=result.diagnostics,
            symmetry_operators_build_seconds=bad_value,
            symmetry_diagnostics_seconds=0.0,
        )


# ---------------------------------------------------------------------------
# outputs.py -- validate_existing_run
# ---------------------------------------------------------------------------


def test_validate_existing_run_missing_file(tmp_path: Path) -> None:
    spec = build_symmetry_campaign_specs()[0]
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    is_valid, reason = validate_existing_run(tmp_path / "missing.json", spec, fingerprint)
    assert is_valid is False
    assert "no existing run file" in reason


@pytest.fixture
def real_run_fixture(tmp_path: Path):
    specs = build_symmetry_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/reference")
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))

    output_dir = tmp_path / "campaign"
    run_campaign([spec], output_dir)
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    return spec, fingerprint, payload, run_path


def test_validate_existing_run_accepts_the_untouched_fixture(real_run_fixture) -> None:
    spec, fingerprint, _payload, run_path = real_run_fixture
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is True
    assert reason is None


def test_validate_existing_run_rejects_wrong_schema_version(real_run_fixture) -> None:
    spec, fingerprint, payload, run_path = real_run_fixture
    payload["schema_version"] = 999
    run_path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is False
    assert "schema_version" in reason


def test_validate_existing_run_rejects_missing_symmetry_block(real_run_fixture) -> None:
    spec, fingerprint, payload, run_path = real_run_fixture
    del payload["symmetry"]
    run_path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is False
    assert "symmetry" in reason


def test_validate_existing_run_rejects_missing_degeneracy_block(real_run_fixture) -> None:
    spec, fingerprint, payload, run_path = real_run_fixture
    payload["report"]["spectrum"]["degeneracy"] = None
    run_path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is False


def test_validate_existing_run_rejects_diagnostics_not_covering_every_group(real_run_fixture) -> None:
    spec, fingerprint, payload, run_path = real_run_fixture
    payload["symmetry"]["diagnostics"] = [
        d for d in payload["symmetry"]["diagnostics"] if not (d["operator_name"] == "T" and d["spectral_group_index"] == 0)
    ]
    run_path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is False
    assert "cover every spectral group" in reason


def test_validate_existing_run_rejects_nan_timing(real_run_fixture) -> None:
    spec, fingerprint, payload, run_path = real_run_fixture
    text = json.dumps(payload).replace(
        f'"symmetry_diagnostics_seconds": {payload["timings"]["symmetry_diagnostics_seconds"]}',
        '"symmetry_diagnostics_seconds": NaN',
    )
    run_path.write_text(text, encoding="utf-8")
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is False


def test_validate_existing_run_rejects_status_not_computed(real_run_fixture) -> None:
    spec, fingerprint, payload, run_path = real_run_fixture
    payload["report"]["spectrum"]["status"] = "not_computed"
    run_path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid is False
    assert "computed" in reason


def test_a_validated_file_can_be_summarized_without_exception(real_run_fixture) -> None:
    spec, fingerprint, payload, _run_path = real_run_fixture

    class _Record:
        experiment_id = spec.experiment_id
        roles = spec.roles
        config_fingerprint = fingerprint

    row = _summary_row(spec, _Record(), payload)
    assert set(row) == set(SUMMARY_CSV_FIELDS)
    assert row["dimension"] == payload["report"]["dimension"]


# ---------------------------------------------------------------------------
# runner.py -- full campaign, resumability, pre-registered thresholds
# ---------------------------------------------------------------------------


def test_write_manifest_pre_registers_thresholds_with_empty_records(tmp_path: Path) -> None:
    write_manifest(
        tmp_path / "manifest.json",
        protocol_version=1,
        expected_runs=8,
        started_at="2026-01-01T00:00:00+00:00",
        thresholds=SYMMETRY_CAMPAIGN_THRESHOLDS,
        records=(),
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["thresholds"] == SYMMETRY_CAMPAIGN_THRESHOLDS
    assert manifest["expected_runs"] == 8
    assert manifest["runs"] == []


def test_run_campaign_full_grid_all_succeed_and_no_truncated_group_failure(tmp_path: Path) -> None:
    specs = build_symmetry_campaign_specs()
    output_dir = tmp_path / "campaign"
    records = run_campaign(specs, output_dir)

    assert len(records) == SYMMETRY_CAMPAIGN_EXPECTED_RUNS
    assert all(record.run_status == "success" for record in records)
    assert all(record.spectrum_status == "computed" for record in records)

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["thresholds"] == SYMMETRY_CAMPAIGN_THRESHOLDS
    assert len(manifest["runs"]) == SYMMETRY_CAMPAIGN_EXPECTED_RUNS

    # every run's last spectral group is window-truncated at n_eigenvalues=16
    # (measured fact for this grid), and none of them caused a failure.
    for run_file in (output_dir / "runs").glob("*.json"):
        payload = json.loads(run_file.read_text())
        groups = payload["report"]["spectrum"]["degeneracy"]["groups"]
        assert groups[-1]["lower_bound_only"] is True


def test_run_campaign_resume_skips_already_valid_runs(tmp_path: Path) -> None:
    specs = build_symmetry_campaign_specs()[:2]
    output_dir = tmp_path / "campaign"
    run_campaign(specs, output_dir)
    records = run_campaign(specs, output_dir)
    assert all(record.run_status == "skipped" for record in records)


def test_run_campaign_leaves_no_tmp_files(tmp_path: Path) -> None:
    specs = build_symmetry_campaign_specs()[:2]
    output_dir = tmp_path / "campaign"
    run_campaign(specs, output_dir)
    leftover = list(output_dir.rglob("*.tmp"))
    assert leftover == []


def test_run_campaign_invalid_existing_run_is_not_silently_overwritten(tmp_path: Path) -> None:
    specs = build_symmetry_campaign_specs()[:1]
    output_dir = tmp_path / "campaign"
    run_campaign(specs, output_dir)

    fingerprint = compute_config_fingerprint(spec_to_experiment(specs[0]))
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    payload = json.loads(run_path.read_text())
    del payload["symmetry"]
    run_path.write_text(json.dumps(payload), encoding="utf-8")

    records = run_campaign(specs, output_dir, overwrite_invalid=False)
    assert records[0].run_status == "error"
    assert "invalid" in records[0].error_message


def test_run_campaign_overwrite_invalid_replaces_a_bad_run_file(tmp_path: Path) -> None:
    specs = build_symmetry_campaign_specs()[:1]
    output_dir = tmp_path / "campaign"
    run_campaign(specs, output_dir)

    fingerprint = compute_config_fingerprint(spec_to_experiment(specs[0]))
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    payload = json.loads(run_path.read_text())
    del payload["symmetry"]
    run_path.write_text(json.dumps(payload), encoding="utf-8")

    records = run_campaign(specs, output_dir, overwrite_invalid=True)
    assert records[0].run_status == "success"
