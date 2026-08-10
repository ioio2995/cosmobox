from __future__ import annotations

from pathlib import Path

import pytest
from level1c_launcher_helpers import _FakeGateArtifact, empty_success_phase_p_report, failed_phase_p_report

from scripts import run_level1c_campaign as cli_module
from scripts.level1c_launcher.launch import (
    COMPLETED,
    STOP_BEFORE_GATE,
    STOP_NORMATIVE_PIPELINE_BEFORE_T,
    Level1CNormativeLaunchReport,
    NormativeLaunchError,
)


def _report(pipeline_status: str, *, gate_status: str | None = None) -> Level1CNormativeLaunchReport:
    if pipeline_status == STOP_BEFORE_GATE:
        return Level1CNormativeLaunchReport(
            phase_p_report=failed_phase_p_report(), gate_artifact=None, tracking_records=None,
            response_records=None, pipeline_status=STOP_BEFORE_GATE,
        )
    if pipeline_status == STOP_NORMATIVE_PIPELINE_BEFORE_T:
        return Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(), gate_artifact=_FakeGateArtifact(gate_status="FAIL"),
            tracking_records=None, response_records=None, pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
        )
    return Level1CNormativeLaunchReport(
        phase_p_report=empty_success_phase_p_report(), gate_artifact=_FakeGateArtifact(gate_status="PASS"),
        tracking_records=("t",), response_records=("r",), pipeline_status=COMPLETED,
    )


def test_cli_parser_has_no_scientific_override() -> None:
    parser = cli_module._build_parser()
    dests = {action.dest for action in parser._actions}
    assert dests == {"help", "output_dir", "historical_output_dir", "repo_root"}


def test_cli_output_dir_is_required(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main(["--historical-output-dir", str(tmp_path), "--repo-root", str(tmp_path)])
    assert excinfo.value.code == 2


def test_cli_historical_output_dir_is_required(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main(["--output-dir", str(tmp_path / "out"), "--repo-root", str(tmp_path)])
    assert excinfo.value.code == 2


def test_cli_completed_yields_exit_code_0(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cli_module, "launch_normative_campaign",
        lambda repo_root, *, output_dir, historical_output_dir: _report(COMPLETED),
    )
    exit_code = cli_module.main(
        ["--output-dir", str(tmp_path / "out"), "--historical-output-dir", str(tmp_path), "--repo-root", str(tmp_path)]
    )
    assert exit_code == 0


def test_cli_stop_before_gate_yields_exit_code_1(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cli_module, "launch_normative_campaign",
        lambda repo_root, *, output_dir, historical_output_dir: _report(STOP_BEFORE_GATE),
    )
    exit_code = cli_module.main(
        ["--output-dir", str(tmp_path / "out"), "--historical-output-dir", str(tmp_path), "--repo-root", str(tmp_path)]
    )
    assert exit_code == 1


def test_cli_stop_normative_pipeline_before_t_yields_exit_code_1(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        cli_module, "launch_normative_campaign",
        lambda repo_root, *, output_dir, historical_output_dir: _report(STOP_NORMATIVE_PIPELINE_BEFORE_T),
    )
    exit_code = cli_module.main(
        ["--output-dir", str(tmp_path / "out"), "--historical-output-dir", str(tmp_path), "--repo-root", str(tmp_path)]
    )
    assert exit_code == 1


def test_cli_normative_launch_error_yields_exit_code_2(monkeypatch, tmp_path: Path) -> None:
    def raise_error(repo_root, *, output_dir, historical_output_dir):
        raise NormativeLaunchError("boom")

    monkeypatch.setattr(cli_module, "launch_normative_campaign", raise_error)
    exit_code = cli_module.main(
        ["--output-dir", str(tmp_path / "out"), "--historical-output-dir", str(tmp_path), "--repo-root", str(tmp_path)]
    )
    assert exit_code == 2


def test_cli_does_not_catch_non_launch_exceptions(monkeypatch, tmp_path: Path) -> None:
    def raising_launch(repo_root, *, output_dir, historical_output_dir):
        raise RuntimeError("phase internal failure")

    monkeypatch.setattr(cli_module, "launch_normative_campaign", raising_launch)
    with pytest.raises(RuntimeError):
        cli_module.main(
            ["--output-dir", str(tmp_path / "out"), "--historical-output-dir", str(tmp_path), "--repo-root", str(tmp_path)]
        )


def test_cli_default_repo_root_is_derived_from_script_location() -> None:
    assert cli_module._DEFAULT_REPO_ROOT == Path(cli_module.__file__).resolve().parents[1]
