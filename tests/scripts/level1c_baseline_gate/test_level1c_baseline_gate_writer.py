from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.level1c_baseline_gate.gate import (
    BASELINE_CASE_SPECS,
    GATE_ARTIFACT_FILENAME,
    _finalize_artifact,
    build_case_comparison_result,
    validate_gate_artifact_document,
    write_gate_artifact,
)

REPO_COMMIT = "9" * 40


def _minimal_fail_artifact(level1c_manifest):
    """A schema-valid FAIL artifact built entirely from public helpers,
    with no real historical/Level1C data on disk -- write_gate_artifact
    itself never recomputes the gate, so its own tests only need SOME
    valid artifact, never a scientifically meaningful one."""
    results = tuple(
        build_case_comparison_result(geometry, spin, None, None, (), (f"TEST_REASON_{geometry}_{spin}",))
        for geometry, spin in BASELINE_CASE_SPECS
    )
    return _finalize_artifact(level1c_manifest, REPO_COMMIT, results, 1e-15, 1e-15)


def test_write_gate_artifact_creates_the_file(tmp_path: Path, level1c_manifest) -> None:
    artifact = _minimal_fail_artifact(level1c_manifest)
    write_gate_artifact(tmp_path, artifact)
    assert (tmp_path / GATE_ARTIFACT_FILENAME).exists()


def test_write_gate_artifact_filename_is_exactly_baseline_nonregression_json() -> None:
    assert GATE_ARTIFACT_FILENAME == "baseline-nonregression.json"


def test_write_gate_artifact_document_validates_against_schema(tmp_path: Path, level1c_manifest) -> None:
    artifact = _minimal_fail_artifact(level1c_manifest)
    write_gate_artifact(tmp_path, artifact)
    document = json.loads((tmp_path / GATE_ARTIFACT_FILENAME).read_text())
    validate_gate_artifact_document(document)
    assert document["gate_status"] == "FAIL"


def test_write_gate_artifact_is_deterministic_across_repeated_writes(tmp_path: Path, level1c_manifest) -> None:
    artifact = _minimal_fail_artifact(level1c_manifest)
    output_dir_a = tmp_path / "a"
    output_dir_b = tmp_path / "b"
    write_gate_artifact(output_dir_a, artifact)
    write_gate_artifact(output_dir_b, artifact)
    bytes_a = (output_dir_a / GATE_ARTIFACT_FILENAME).read_bytes()
    bytes_b = (output_dir_b / GATE_ARTIFACT_FILENAME).read_bytes()
    assert bytes_a == bytes_b


def test_write_gate_artifact_overwrites_a_previous_write(tmp_path: Path, level1c_manifest) -> None:
    artifact = _minimal_fail_artifact(level1c_manifest)
    write_gate_artifact(tmp_path, artifact)
    first_bytes = (tmp_path / GATE_ARTIFACT_FILENAME).read_bytes()
    write_gate_artifact(tmp_path, artifact)
    second_bytes = (tmp_path / GATE_ARTIFACT_FILENAME).read_bytes()
    assert first_bytes == second_bytes


def test_write_gate_artifact_never_recomputes_the_gate(tmp_path: Path, level1c_manifest) -> None:
    """write_gate_artifact takes an already-computed artifact object --
    it never calls run_baseline_nonregression_gate itself."""
    import inspect

    from scripts.level1c_baseline_gate import gate as gate_module

    source = inspect.getsource(gate_module.write_gate_artifact)
    assert "run_baseline_nonregression_gate(" not in source
