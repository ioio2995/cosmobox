from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

from cosmobox.level0 import compute_config_fingerprint
from scripts.level0_reference_campaign import runner as runner_module
from scripts.level0_reference_campaign.grid import (
    REFERENCE_CAMPAIGN_EXPECTED_RUNS,
    ADDITIONAL_SWEEP_VALUES,
    build_reference_campaign_specs,
    spec_to_experiment,
    validate_unique_fingerprints,
)
from scripts.level0_reference_campaign.outputs import SUMMARY_CSV_FIELDS, _summary_row, validate_existing_run
from scripts.level0_reference_campaign.runner import run_campaign

# ---------------------------------------------------------------------------
# Grid generation
# ---------------------------------------------------------------------------


def test_grid_has_exactly_72_specs() -> None:
    specs = build_reference_campaign_specs()
    assert len(specs) == REFERENCE_CAMPAIGN_EXPECTED_RUNS == 72


def test_grid_experiment_ids_are_unique() -> None:
    specs = build_reference_campaign_specs()
    ids = [spec.experiment_id for spec in specs]
    assert len(set(ids)) == len(ids)


def test_grid_fingerprints_are_unique() -> None:
    specs = build_reference_campaign_specs()
    fingerprints = validate_unique_fingerprints(specs)
    assert len(set(fingerprints.values())) == len(specs) == 72


def test_grid_is_deterministic_across_calls() -> None:
    first = build_reference_campaign_specs()
    second = build_reference_campaign_specs()
    assert first == second


def test_grid_composition_is_15_48_3_6() -> None:
    specs = build_reference_campaign_specs()
    controls = [s for s in specs if "control" in s.roles]
    additional_sweeps = [
        s for s in specs if s.roles and s.roles[0].startswith("sweep_") and "control" not in s.roles
    ]
    truncation = [s for s in specs if "spin_truncation" in s.roles]
    h_sensitivity = [s for s in specs if "h_sensitivity" in s.roles]

    assert len(controls) == 15
    assert len(additional_sweeps) == 48
    assert len(truncation) == 3
    assert len(h_sensitivity) == 6
    assert len(controls) + len(additional_sweeps) + len(truncation) + len(h_sensitivity) == 72


def test_reference_point_has_all_six_roles() -> None:
    specs = build_reference_campaign_specs()
    for geometry in ("triangle", "ring4", "ring5"):
        reference = next(s for s in specs if s.experiment_id == f"{geometry}/reference")
        assert set(reference.roles) == {"control", "reference", "sweep_J", "sweep_t", "sweep_g_E", "sweep_K"}


def test_no_additional_sweep_spec_has_x_equal_one() -> None:
    assert 1.0 not in ADDITIONAL_SWEEP_VALUES
    specs = build_reference_campaign_specs()
    for spec in specs:
        if spec.roles and spec.roles[0].startswith("sweep_") and "reference" not in spec.roles:
            assert "=1.0" not in spec.experiment_id


def test_local_only_control_has_zero_intersite_couplings() -> None:
    specs = build_reference_campaign_specs()
    local_only = next(s for s in specs if s.experiment_id == "triangle/local_only")
    assert local_only.t == 0.0
    assert local_only.g_E == 0.0
    assert local_only.K == 0.0
    assert local_only.J == 1.0
    assert local_only.h_eta == 0.0


def test_h_sensitivity_specs_only_on_triangle_and_ring4() -> None:
    specs = build_reference_campaign_specs()
    h_sensitivity = [s for s in specs if "h_sensitivity" in s.roles]
    assert {s.geometry for s in h_sensitivity} == {"triangle", "ring4"}
    assert {s.h_eta for s in h_sensitivity} == {0.1, 0.25, 0.5}


def test_spin_truncation_specs_match_the_frozen_points() -> None:
    specs = build_reference_campaign_specs()
    truncation = {(s.geometry, s.spin) for s in specs if "spin_truncation" in s.roles}
    assert truncation == {("triangle", 2), ("triangle", 3), ("ring4", 2)}


# ---------------------------------------------------------------------------
# validate_existing_run
# ---------------------------------------------------------------------------


def test_validate_existing_run_missing_file(tmp_path: Path) -> None:
    specs = build_reference_campaign_specs()
    spec = specs[0]
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    is_valid, reason = validate_existing_run(tmp_path / "missing.json", spec, fingerprint)
    assert not is_valid
    assert reason


def test_validate_existing_run_rejects_correct_fingerprint_wrong_config_block(tmp_path: Path) -> None:
    specs = build_reference_campaign_specs()
    spec = specs[0]
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    path = tmp_path / f"{fingerprint}.json"
    path.write_text(
        json.dumps({"schema_version": 1, "config_fingerprint": fingerprint, "config": {"tampered": True}}),
        encoding="utf-8",
    )
    is_valid, reason = validate_existing_run(path, spec, fingerprint)
    assert not is_valid
    assert "run file is missing" in reason  # environment/timings/report also absent from this minimal fixture


def test_validate_existing_run_accepts_a_real_run(tmp_path: Path) -> None:
    specs = build_reference_campaign_specs()
    spec = next(s for s in specs if s.geometry == "triangle" and s.experiment_id == "triangle/local_only")
    output_dir = tmp_path / "campaign"
    run_campaign([spec], output_dir)
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    is_valid, reason = validate_existing_run(run_path, spec, fingerprint)
    assert is_valid
    assert reason is None


# ---------------------------------------------------------------------------
# validate_existing_run: structural hardening against a truncated/altered
# but well-fingerprinted file (bug found on review of 7b70968)
# ---------------------------------------------------------------------------


@pytest.fixture
def real_run_fixture(tmp_path: Path):
    """A genuine, fully valid 5A run JSON (parsed dict) plus its spec/path/fingerprint."""
    specs = build_reference_campaign_specs()
    spec = next(s for s in specs if s.experiment_id == "triangle/local_only")
    output_dir = tmp_path / "campaign"
    run_campaign([spec], output_dir)
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    return spec, fingerprint, payload, tmp_path


def _write_and_validate(spec, fingerprint, payload, tmp_dir: Path) -> tuple[bool, str | None]:
    path = tmp_dir / f"altered_{fingerprint}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return validate_existing_run(path, spec, fingerprint)


def test_validate_existing_run_accepts_the_untouched_fixture(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert (is_valid, reason) == (True, None)


def test_validate_existing_run_rejects_missing_report(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    del payload["report"]
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert not is_valid
    assert "report" in reason


def test_validate_existing_run_rejects_missing_timings(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    del payload["timings"]
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert not is_valid
    assert "timings" in reason


def test_validate_existing_run_rejects_report_from_another_geometry(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    payload["report"]["lattice_name"] = "ring4"
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert not is_valid
    assert "lattice_name" in reason


def test_validate_existing_run_rejects_report_parameters_differing_from_config(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    payload["report"]["parameters"]["t"] += 1.0
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert not is_valid
    assert "parameters" in reason


def test_validate_existing_run_rejects_terms_without_total_entry(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    payload["report"]["terms"] = [t for t in payload["report"]["terms"] if t["name"] != "total"]
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert not is_valid
    assert "total" in reason


def test_validate_existing_run_rejects_inconsistent_computed_eigenvalues(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    assert payload["report"]["spectrum"]["status"] == "computed"
    payload["report"]["spectrum"]["computed_eigenvalues"] += 1
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert not is_valid
    assert "computed_eigenvalues" in reason


def test_validate_existing_run_rejects_nan_timing(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    payload["timings"]["report_build_seconds"] = float("nan")
    path = tmp_dir / f"nan_timing_{fingerprint}.json"
    # json.dumps(allow_nan=True) default lets NaN through as invalid-JSON "NaN" literal,
    # which json.loads() (also permissive by default) will happily read back --
    # the point of this test is that *our* validator, not the JSON parser, must reject it.
    path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(path, spec, fingerprint)
    assert not is_valid
    assert "report_build_seconds" in reason


def test_validate_existing_run_rejects_nan_eigenvalue(real_run_fixture) -> None:
    spec, fingerprint, payload, tmp_dir = real_run_fixture
    assert payload["report"]["spectrum"]["eigenpairs"], "fixture must have at least one eigenpair"
    payload["report"]["spectrum"]["eigenpairs"][0]["eigenvalue"] = float("nan")
    path = tmp_dir / f"nan_eigenvalue_{fingerprint}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    is_valid, reason = validate_existing_run(path, spec, fingerprint)
    assert not is_valid
    assert "eigenvalue" in reason


def test_a_validated_file_can_be_summarized_without_exception(real_run_fixture) -> None:
    from scripts.level0_reference_campaign.outputs import CampaignRunRecord

    spec, fingerprint, payload, tmp_dir = real_run_fixture
    is_valid, reason = _write_and_validate(spec, fingerprint, payload, tmp_dir)
    assert (is_valid, reason) == (True, None)

    record = CampaignRunRecord(
        experiment_id=spec.experiment_id,
        roles=spec.roles,
        config_fingerprint=fingerprint,
        run_status="skipped",
        spectrum_status=payload["report"]["spectrum"]["status"],
        error_message=None,
    )
    row = _summary_row(spec, record, payload)  # must not raise
    assert row["spectrum_status"] == "computed"
    assert row["ground_energy"] != ""


# ---------------------------------------------------------------------------
# run_campaign: micro-campaign on 3 real (fast) triangle specs
# ---------------------------------------------------------------------------


@pytest.fixture
def micro_specs():
    specs = build_reference_campaign_specs()
    return [s for s in specs if s.geometry == "triangle"][:3]


def test_run_campaign_produces_one_run_file_per_spec(tmp_path: Path, micro_specs) -> None:
    output_dir = tmp_path / "campaign"
    records = run_campaign(micro_specs, output_dir)
    assert len(records) == 3
    assert all(r.run_status == "success" for r in records)
    run_files = list((output_dir / "runs").glob("*.json"))
    assert len(run_files) == 3


def test_run_campaign_resume_skips_already_valid_runs(tmp_path: Path, micro_specs, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "campaign"
    run_campaign(micro_specs, output_dir)

    calls = []
    original = runner_module.run_level0_experiment

    def _tracking(config):
        calls.append(config)
        return original(config)

    monkeypatch.setattr(runner_module, "run_level0_experiment", _tracking)

    records = run_campaign(micro_specs, output_dir)
    assert all(r.run_status == "skipped" for r in records)
    assert calls == []  # the runner was never invoked for an already-valid run


def test_run_campaign_manifest_and_csv_after_micro_campaign(tmp_path: Path, micro_specs) -> None:
    output_dir = tmp_path / "campaign"
    run_campaign(micro_specs, output_dir)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["expected_runs"] == 3
    assert len(manifest["runs"]) == 3
    assert {run["run_status"] for run in manifest["runs"]} == {"success"}

    with (output_dir / "summary.csv").open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == list(SUMMARY_CSV_FIELDS)
        rows = list(reader)
    assert len(rows) == 3
    for row in rows:
        assert row["spectrum_status"] == "computed"
        assert row["ground_energy"] != ""


def test_run_campaign_leaves_no_tmp_files(tmp_path: Path, micro_specs) -> None:
    output_dir = tmp_path / "campaign"
    run_campaign(micro_specs, output_dir)
    leftover = list(output_dir.rglob("*.tmp"))
    assert leftover == []


def test_run_campaign_spectrum_failed_is_still_run_status_success(tmp_path: Path, micro_specs, monkeypatch: pytest.MonkeyPatch) -> None:
    from cosmobox.level0.reports import EigenpairDiagnostic, SpectrumReport, TermExpectations
    import dataclasses

    output_dir = tmp_path / "campaign"
    spec = micro_specs[0]

    original = runner_module.run_level0_experiment

    def _force_failed(config):
        result = original(config)
        failed_spectrum = SpectrumReport(
            status="failed",
            method=result.report.spectrum.method,
            requested_eigenvalues=result.report.spectrum.requested_eigenvalues,
            computed_eigenvalues=0,
            tolerance=result.report.spectrum.tolerance,
            reason="synthetic failure for test purposes",
            eigenpairs=(),
            spectral_gap=None,
        )
        failed_report = dataclasses.replace(result.report, spectrum=failed_spectrum)
        return dataclasses.replace(result, report=failed_report)

    monkeypatch.setattr(runner_module, "run_level0_experiment", _force_failed)

    records = run_campaign([spec], output_dir)
    assert records[0].run_status == "success"
    assert records[0].spectrum_status == "failed"

    with (output_dir / "summary.csv").open(encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["spectrum_status"] == "failed"
    assert row["ground_energy"] == ""
    assert row["first_excited_energy"] == ""
    assert row["spectral_gap"] == ""


def test_run_campaign_unexpected_exception_becomes_error_and_campaign_continues(
    tmp_path: Path, micro_specs, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "campaign"
    failing_id = micro_specs[0].experiment_id

    original = runner_module.run_level0_experiment

    def _maybe_fail(config):
        # Fail only for the first spec's config (identified via fingerprint
        # at call time is awkward here, so just fail on the first call).
        if not _maybe_fail.called:
            _maybe_fail.called = True
            raise RuntimeError("synthetic unexpected failure")
        return original(config)

    _maybe_fail.called = False
    monkeypatch.setattr(runner_module, "run_level0_experiment", _maybe_fail)

    records = run_campaign(micro_specs, output_dir, stop_on_error=False)
    assert len(records) == 3  # campaign did not stop after the error
    statuses = {r.experiment_id: r.run_status for r in records}
    assert statuses[failing_id] == "error"
    assert sum(1 for s in statuses.values() if s == "success") == 2


def test_run_campaign_stop_on_error_halts_the_loop(tmp_path: Path, micro_specs, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "campaign"

    def _always_fail(config):
        raise RuntimeError("synthetic unexpected failure")

    monkeypatch.setattr(runner_module, "run_level0_experiment", _always_fail)

    records = run_campaign(micro_specs, output_dir, stop_on_error=True)
    assert len(records) == 1
    assert records[0].run_status == "error"


def test_run_campaign_invalid_existing_run_is_not_silently_overwritten(tmp_path: Path, micro_specs) -> None:
    output_dir = tmp_path / "campaign"
    spec = micro_specs[0]
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(
        json.dumps({"schema_version": 1, "config_fingerprint": fingerprint, "config": {"tampered": True}}),
        encoding="utf-8",
    )

    records = run_campaign([spec], output_dir)
    assert records[0].run_status == "error"
    assert "invalid" in records[0].error_message
    # not overwritten:
    assert json.loads(run_path.read_text(encoding="utf-8"))["config"] == {"tampered": True}


def test_run_campaign_overwrite_invalid_replaces_a_bad_run_file(tmp_path: Path, micro_specs) -> None:
    output_dir = tmp_path / "campaign"
    spec = micro_specs[0]
    fingerprint = compute_config_fingerprint(spec_to_experiment(spec))
    run_path = output_dir / "runs" / f"{fingerprint}.json"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(
        json.dumps({"schema_version": 1, "config_fingerprint": fingerprint, "config": {"tampered": True}}),
        encoding="utf-8",
    )

    records = run_campaign([spec], output_dir, overwrite_invalid=True)
    assert records[0].run_status == "success"
    assert json.loads(run_path.read_text(encoding="utf-8"))["config"]["geometry"] == "triangle"
