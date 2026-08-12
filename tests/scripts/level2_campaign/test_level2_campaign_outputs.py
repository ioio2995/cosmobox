"""Unit tests for scripts.level2_campaign.outputs (lot
L2-E-CAMPAIGN-INFRASTRUCTURE). Filesystem-only, no scientific content.
"""

from __future__ import annotations

import json

import pytest

from scripts.level2_campaign.outputs import (
    atomic_write_json,
    campaign_output_dir,
    campaign_summary_path,
    canonical_json_bytes,
    write_campaign_summary,
)


def test_canonical_json_bytes_is_sorted_deterministic_and_newline_terminated():
    payload_a = canonical_json_bytes({"b": 1, "a": 2})
    payload_b = canonical_json_bytes({"a": 2, "b": 1})
    assert payload_a == payload_b
    assert payload_a.endswith(b"\n")
    assert json.loads(payload_a) == {"a": 2, "b": 1}


def test_atomic_write_json_creates_parent_directories_and_content(tmp_path):
    path = tmp_path / "nested" / "dir" / "document.json"
    atomic_write_json(path, {"hello": "world"})
    assert path.exists()
    assert json.loads(path.read_text()) == {"hello": "world"}


def test_atomic_write_json_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "document.json"
    atomic_write_json(path, {"a": 1})
    remaining = list(tmp_path.iterdir())
    assert remaining == [path]


def test_atomic_write_json_does_not_leave_a_partial_temp_file_on_failure(tmp_path, monkeypatch):
    path = tmp_path / "document.json"

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("os.replace", _boom)
    with pytest.raises(RuntimeError):
        atomic_write_json(path, {"a": 1})
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_campaign_output_dir_and_summary_path_layout(tmp_path):
    output_dir = campaign_output_dir(tmp_path, "level2-energy-regime-v1")
    assert output_dir == tmp_path / "level2-energy-regime-v1"
    summary_path = campaign_summary_path(tmp_path, "level2-energy-regime-v1")
    assert summary_path == output_dir / "campaign-summary.json"


def test_write_campaign_summary_is_atomic_and_readable(tmp_path):
    document = {"schema_version": "level2-campaign-summary-v1", "campaign_status": "COMPLETE"}
    path = write_campaign_summary(tmp_path, "level2-energy-regime-v1", document)
    assert path == campaign_summary_path(tmp_path, "level2-energy-regime-v1")
    assert json.loads(path.read_text()) == document
