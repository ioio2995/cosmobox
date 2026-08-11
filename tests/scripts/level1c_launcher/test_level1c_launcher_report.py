from __future__ import annotations

import pytest
from level1c_launcher_helpers import _FakeGateArtifact, empty_success_phase_p_report, failed_phase_p_report

from scripts.level1c_launcher.launch import (
    COMPLETED,
    STOP_BEFORE_GATE,
    STOP_NORMATIVE_PIPELINE_BEFORE_T,
    Level1CNormativeLaunchReport,
)


def test_stop_before_gate_valid() -> None:
    report = Level1CNormativeLaunchReport(
        phase_p_report=failed_phase_p_report(),
        gate_artifact=None,
        tracking_records=None,
        response_records=None,
        pipeline_status=STOP_BEFORE_GATE,
    )
    assert report.pipeline_status == STOP_BEFORE_GATE


def test_stop_before_gate_rejects_p_global_success_true() -> None:
    with pytest.raises(ValueError, match="global_success must be False"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=None,
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_BEFORE_GATE,
        )


def test_stop_before_gate_rejects_present_gate_artifact() -> None:
    with pytest.raises(ValueError, match="must all be None"):
        Level1CNormativeLaunchReport(
            phase_p_report=failed_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="PASS"),
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_BEFORE_GATE,
        )


def test_stop_normative_pipeline_before_t_valid() -> None:
    report = Level1CNormativeLaunchReport(
        phase_p_report=empty_success_phase_p_report(),
        gate_artifact=_FakeGateArtifact(gate_status="FAIL"),
        tracking_records=None,
        response_records=None,
        pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
    )
    assert report.pipeline_status == STOP_NORMATIVE_PIPELINE_BEFORE_T


def test_stop_normative_pipeline_before_t_rejects_p_global_success_false() -> None:
    with pytest.raises(ValueError, match="global_success must be True"):
        Level1CNormativeLaunchReport(
            phase_p_report=failed_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="FAIL"),
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
        )


def test_stop_normative_pipeline_before_t_requires_gate_artifact() -> None:
    with pytest.raises(ValueError, match="gate_artifact must be set"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=None,
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
        )


def test_stop_normative_pipeline_before_t_requires_fail_status() -> None:
    with pytest.raises(ValueError, match="gate_status"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="PASS"),
            tracking_records=None,
            response_records=None,
            pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
        )


def test_stop_normative_pipeline_before_t_rejects_tracking_present() -> None:
    with pytest.raises(ValueError, match="must both be None"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="FAIL"),
            tracking_records=("x",),
            response_records=None,
            pipeline_status=STOP_NORMATIVE_PIPELINE_BEFORE_T,
        )


def test_completed_valid() -> None:
    report = Level1CNormativeLaunchReport(
        phase_p_report=empty_success_phase_p_report(),
        gate_artifact=_FakeGateArtifact(gate_status="PASS"),
        tracking_records=("t",),
        response_records=("r",),
        pipeline_status=COMPLETED,
    )
    assert report.pipeline_status == COMPLETED


def test_completed_requires_p_global_success() -> None:
    with pytest.raises(ValueError, match="global_success"):
        Level1CNormativeLaunchReport(
            phase_p_report=failed_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="PASS"),
            tracking_records=("t",),
            response_records=("r",),
            pipeline_status=COMPLETED,
        )


def test_completed_requires_gate_pass() -> None:
    with pytest.raises(ValueError, match="gate_status"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="FAIL"),
            tracking_records=("t",),
            response_records=("r",),
            pipeline_status=COMPLETED,
        )


def test_completed_requires_tracking_and_response_present() -> None:
    with pytest.raises(ValueError, match="tracking_records and response_records"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=_FakeGateArtifact(gate_status="PASS"),
            tracking_records=None,
            response_records=("r",),
            pipeline_status=COMPLETED,
        )


def test_unknown_pipeline_status_rejected() -> None:
    with pytest.raises(ValueError, match="pipeline_status must be one of"):
        Level1CNormativeLaunchReport(
            phase_p_report=empty_success_phase_p_report(),
            gate_artifact=None,
            tracking_records=None,
            response_records=None,
            pipeline_status="BOGUS",
        )


def test_never_carries_a_normative_campaign_valid_field() -> None:
    report = Level1CNormativeLaunchReport(
        phase_p_report=empty_success_phase_p_report(),
        gate_artifact=_FakeGateArtifact(gate_status="PASS"),
        tracking_records=("t",),
        response_records=("r",),
        pipeline_status=COMPLETED,
    )
    assert not hasattr(report, "normative_campaign_valid")
    assert not hasattr(report, "physical_response")
