"""Unit tests for cosmobox.level3.frozen_reference (lot L3-I).

Exercises the real, versioned results/level2/level2-energy-regime-v1/
artifacts (frozen by lot L3-H) for the positive paths, and tmp_path
copies with deliberately corrupted bytes/provenance for the negative
paths -- the real versioned artifacts are never modified by any test
here. No cosmobox.level0/level2 physics primitive (build_lattice,
build_basis, build_hamiltonian_terms, run_case) is ever called: every
reconstruction goes through already-persisted JSON only.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from cosmobox.level3 import execution as level3_execution
from cosmobox.level3.execution import CaseExecutionResult, compare_spin_pair
from cosmobox.level3.frozen_reference import (
    LEVEL2_REFERENCE_DIMENSIONS,
    FrozenReferenceIntegrityError,
    frozen_metric_comparison,
    frozen_reference_root,
    load_campaign_summary,
    load_case_result,
    reconstruct_case_execution_result,
    verify_frozen_reference,
    verify_sha256sums,
)

REAL_ROOT = frozen_reference_root()


@pytest.fixture()
def tampered_root(tmp_path: Path) -> Path:
    """A full copy of the real, versioned frozen reference directory, so
    tests can corrupt bytes/provenance without ever touching the real
    tracked artifacts."""
    copy_root = tmp_path / "level2-energy-regime-v1"
    shutil.copytree(REAL_ROOT, copy_root)
    return copy_root


# ---------------------------------------------------------------------------
# Positive paths: the real, versioned artifacts
# ---------------------------------------------------------------------------


def test_verify_sha256sums_passes_on_real_versioned_artifacts():
    verify_sha256sums()  # must not raise


def test_verify_frozen_reference_passes_on_real_versioned_artifacts():
    verify_frozen_reference()  # must not raise


def test_load_campaign_summary_matches_pinned_identity():
    document = load_campaign_summary()
    assert document["campaign_id"] == "level2-energy-regime-v1"
    assert document["campaign_status"] == "COMPLETE"
    assert {entry["geometry"] for entry in document["geometries"]} == {"triangle", "ring4", "ring5"}


@pytest.mark.parametrize(("geometry", "spin"), sorted(LEVEL2_REFERENCE_DIMENSIONS))
def test_load_case_result_matches_frozen_dimensions(geometry: str, spin: int):
    document = load_case_result(geometry, spin)
    assert document["dimension"] == LEVEL2_REFERENCE_DIMENSIONS[(geometry, spin)]
    assert document["geometry"] == geometry
    assert document["spin"] == spin


# ---------------------------------------------------------------------------
# Reconstruction: frozen case-result JSON -> CaseExecutionResult, never run_case
# ---------------------------------------------------------------------------


def test_reconstruct_case_execution_result_from_real_triangle_s3():
    result = reconstruct_case_execution_result("triangle", 3)
    assert isinstance(result, CaseExecutionResult)
    assert result.spec.geometry == "triangle"
    assert result.spec.spin == 3
    assert result.dimension == 128
    assert result.group_count == 32


def test_reconstruct_case_execution_result_never_calls_run_case(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("reconstruct_case_execution_result must never call run_case")

    monkeypatch.setattr(level3_execution, "run_case", forbidden)
    result = reconstruct_case_execution_result("triangle", 3)
    assert result.dimension == 128


def test_reconstruct_case_execution_result_leaves_raw_observables_unreconstructed():
    result = reconstruct_case_execution_result("triangle", 2)
    for entry in result.entries:
        assert entry.c_tt_conn is None
        assert entry.rho_qq is None


def test_reconstructed_s2_s3_feed_compare_spin_pair_without_modification():
    result_s2 = reconstruct_case_execution_result("triangle", 2)
    result_s3 = reconstruct_case_execution_result("triangle", 3)
    comparison = compare_spin_pair(result_s2, result_s3)
    assert comparison.geometry == "triangle"
    assert comparison.m_tt.taxonomy in {
        "NOT_EVALUABLE",
        "NO_RESOLVED_SPECTRAL_CONTRAST",
        "OPPOSITE_INTER_S_DIRECTION",
        "SAME_INTER_S_DIRECTION",
    }


# ---------------------------------------------------------------------------
# Already-aggregated Level2 values -- read directly, never recomputed
# ---------------------------------------------------------------------------


def test_frozen_metric_comparison_delta_hl_and_cx23_come_from_campaign_summary():
    entry = frozen_metric_comparison("triangle", "M_TT")
    assert set(entry) == {
        "metric", "delta_hl_s2", "delta_hl_s3", "taxonomy", "direction_s2", "direction_s3", "c_x_23", "d_x_23",
    }
    assert entry["metric"] == "M_TT"


def test_frozen_metric_comparison_rejects_unknown_metric():
    with pytest.raises(ValueError):
        frozen_metric_comparison("triangle", "not-a-metric")


def test_frozen_metric_comparison_rejects_unknown_geometry():
    with pytest.raises(ValueError):
        frozen_metric_comparison("hexagon", "M_TT")


# ---------------------------------------------------------------------------
# Integrity failures: missing file, bad hash, bad provenance -- all on a
# tmp_path COPY, never on the real versioned artifacts.
# ---------------------------------------------------------------------------


def test_verify_sha256sums_rejects_missing_sums_file(tampered_root):
    (tampered_root / "SHA256SUMS").unlink()
    with pytest.raises(FrozenReferenceIntegrityError):
        verify_sha256sums(root=tampered_root)


def test_verify_sha256sums_rejects_tampered_file(tampered_root):
    case_path = tampered_root / "cases" / "triangle-S3.json"
    document = json.loads(case_path.read_text())
    document["dimension"] = 999999
    case_path.write_text(json.dumps(document))

    with pytest.raises(FrozenReferenceIntegrityError):
        verify_sha256sums(root=tampered_root)


def test_verify_sha256sums_rejects_missing_listed_artifact(tampered_root):
    (tampered_root / "cases" / "ring5-S3.json").unlink()
    with pytest.raises(FrozenReferenceIntegrityError):
        verify_sha256sums(root=tampered_root)


def test_load_case_result_rejects_wrong_provenance(tampered_root):
    case_path = tampered_root / "cases" / "triangle-S3.json"
    document = json.loads(case_path.read_text())
    document["campaign_id"] = "a-different-campaign"
    case_path.write_text(json.dumps(document))

    with pytest.raises(FrozenReferenceIntegrityError):
        load_case_result("triangle", 3, root=tampered_root)


def test_load_case_result_rejects_wrong_dimension(tampered_root):
    case_path = tampered_root / "cases" / "triangle-S3.json"
    document = json.loads(case_path.read_text())
    document["dimension"] = 129
    document["group_count"] = 33
    case_path.write_text(json.dumps(document))

    with pytest.raises(FrozenReferenceIntegrityError):
        load_case_result("triangle", 3, root=tampered_root)


def test_load_case_result_rejects_unknown_geometry_spin_pair():
    with pytest.raises(ValueError):
        load_case_result("triangle", 4)


def test_load_campaign_summary_rejects_wrong_repository_commit(tampered_root):
    summary_path = tampered_root / "campaign-summary.json"
    document = json.loads(summary_path.read_text())
    document["repository_commit"] = "f" * 40
    summary_path.write_text(json.dumps(document))

    with pytest.raises(FrozenReferenceIntegrityError):
        load_campaign_summary(root=tampered_root)
