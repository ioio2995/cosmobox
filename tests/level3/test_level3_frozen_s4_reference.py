"""Unit tests for cosmobox.level3.frozen_s4_reference (lot L3-P).

Exercises the real, versioned results/level3/level3-s4-truncation-extension-v1/
artifacts (frozen by lot L3-L) for the positive paths, and tmp_path
copies with deliberately corrupted bytes/provenance for the negative
paths -- the real versioned artifacts are never modified by any test
here. No cosmobox.level0/level2/level3 physics primitive (build_lattice,
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
from cosmobox.level3.frozen_s4_reference import (
    LEVEL3_S4_REFERENCE_DIMENSIONS,
    FrozenS4ReferenceIntegrityError,
    frozen_metric_comparison,
    frozen_s4_reference_root,
    load_campaign_summary,
    load_case_result,
    reconstruct_case_execution_result,
    verify_frozen_s4_reference,
    verify_sha256sums,
)

REAL_ROOT = frozen_s4_reference_root()


@pytest.fixture()
def tampered_root(tmp_path: Path) -> Path:
    """A full copy of the real, versioned frozen S4 reference directory,
    so tests can corrupt bytes/provenance without ever touching the real
    tracked artifacts."""
    copy_root = tmp_path / "level3-s4-truncation-extension-v1"
    shutil.copytree(REAL_ROOT, copy_root)
    return copy_root


# ---------------------------------------------------------------------------
# Positive paths: the real, versioned artifacts
# ---------------------------------------------------------------------------


def test_verify_sha256sums_passes_on_real_versioned_artifacts():
    verify_sha256sums()  # must not raise


def test_verify_frozen_s4_reference_passes_on_real_versioned_artifacts():
    verify_frozen_s4_reference()  # must not raise


def test_load_campaign_summary_matches_pinned_identity():
    document = load_campaign_summary()
    assert document["campaign_id"] == "level3-s4-truncation-extension-v1"
    assert document["campaign_status"] == "COMPLETE"
    assert {entry["geometry"] for entry in document["geometries"]} == {"triangle", "ring4", "ring5"}


@pytest.mark.parametrize("geometry", sorted(LEVEL3_S4_REFERENCE_DIMENSIONS))
def test_load_case_result_matches_frozen_dimensions_and_invariants(geometry: str):
    document = load_case_result(geometry)
    assert document["dimension"] == LEVEL3_S4_REFERENCE_DIMENSIONS[geometry]
    assert document["geometry"] == geometry
    assert document["spin"] == 4
    assert document["full_spectrum"] is True
    assert document["solver_method"] == "dense"
    assert document["window_truncated"] is False
    assert document["partial_subspace_count"] == 0


# ---------------------------------------------------------------------------
# Reconstruction: frozen S4 case-result JSON -> CaseExecutionResult, never run_case
# ---------------------------------------------------------------------------


def test_reconstruct_case_execution_result_from_real_triangle_s4():
    result = reconstruct_case_execution_result("triangle")
    assert isinstance(result, CaseExecutionResult)
    assert result.spec.geometry == "triangle"
    assert result.spec.spin == 4
    assert result.dimension == 168


def test_reconstruct_case_execution_result_never_calls_run_case(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("reconstruct_case_execution_result must never call run_case")

    monkeypatch.setattr(level3_execution, "run_case", forbidden)
    result = reconstruct_case_execution_result("triangle")
    assert result.dimension == 168


def test_reconstruct_case_execution_result_leaves_raw_observables_unreconstructed():
    result = reconstruct_case_execution_result("ring4")
    for entry in result.entries:
        assert entry.c_tt_conn is None
        assert entry.rho_qq is None


def test_reconstructed_s4_feeds_compare_spin_pair_without_modification():
    # Synthetic S5 side, matching the pattern already established for
    # frozen-S3-vs-real-S4 comparisons in tests/level3/test_level3_serialization.py.
    from cosmobox.level2 import metrics, orchestration
    from cosmobox.level2.adapter import MultipletProfileEntry
    from cosmobox.level3.execution import CaseSpec

    result_s4 = reconstruct_case_execution_result("triangle")

    n = 5
    boundaries = [i / n for i in range(n + 1)]
    entries = tuple(
        MultipletProfileEntry(
            energy=0.0, multiplicity=1, epsilon=0.0,
            q_start=boundaries[i], q_end=boundaries[i + 1], q_midpoint=(boundaries[i] + boundaries[i + 1]) / 2,
            m_tt=float(i + 1) * 0.01, r_eff=metrics.Available(0.1 * (i + 1), None),
            a_qq=0.5, m_qq=metrics.Available(0.2, None),
        )
        for i in range(n)
    )
    analyses = {m: orchestration.analyze_case_metric(entries, m) for m in orchestration.ALL_METRICS}
    result_s5 = CaseExecutionResult(
        spec=CaseSpec(geometry="triangle", spin=5), dimension=n, group_count=n, entries=entries,
        m_tt_analysis=analyses["M_TT"], r_eff_analysis=analyses["R_eff"],
        a_qq_analysis=analyses["A_QQ"], m_qq_analysis=analyses["M_QQ"],
    )

    comparison = compare_spin_pair(result_s4, result_s5)
    assert comparison.geometry == "triangle"
    assert comparison.m_tt.taxonomy in {
        "NOT_EVALUABLE",
        "NO_RESOLVED_SPECTRAL_CONTRAST",
        "OPPOSITE_INTER_S_DIRECTION",
        "SAME_INTER_S_DIRECTION",
    }


# ---------------------------------------------------------------------------
# Already-aggregated S3<->S4 values -- read directly, never recomputed
# ---------------------------------------------------------------------------


def test_frozen_metric_comparison_carries_s2_s3_s4_data():
    entry = frozen_metric_comparison("triangle", "M_TT")
    assert {"delta_hl_s2", "delta_hl_s3", "delta_hl_s4", "direction_s2", "direction_s3", "direction_s4",
            "t_x_23", "t_x_34", "c_x_23", "d_x_23", "c_x_34", "d_x_34"}.issubset(entry)
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
    with pytest.raises(FrozenS4ReferenceIntegrityError):
        verify_sha256sums(root=tampered_root)


def test_verify_sha256sums_rejects_tampered_file(tampered_root):
    case_path = tampered_root / "cases" / "triangle-S4.json"
    document = json.loads(case_path.read_text())
    document["dimension"] = 999999
    case_path.write_text(json.dumps(document))

    with pytest.raises(FrozenS4ReferenceIntegrityError):
        verify_sha256sums(root=tampered_root)


def test_verify_sha256sums_rejects_missing_listed_artifact(tampered_root):
    (tampered_root / "cases" / "ring5-S4.json").unlink()
    with pytest.raises(FrozenS4ReferenceIntegrityError):
        verify_sha256sums(root=tampered_root)


def test_load_case_result_rejects_wrong_provenance(tampered_root):
    case_path = tampered_root / "cases" / "triangle-S4.json"
    document = json.loads(case_path.read_text())
    document["campaign_id"] = "a-different-campaign"
    case_path.write_text(json.dumps(document))

    with pytest.raises(FrozenS4ReferenceIntegrityError):
        load_case_result("triangle", root=tampered_root)


def test_load_case_result_rejects_wrong_dimension(tampered_root):
    case_path = tampered_root / "cases" / "triangle-S4.json"
    document = json.loads(case_path.read_text())
    document["dimension"] = 169
    case_path.write_text(json.dumps(document))

    with pytest.raises(FrozenS4ReferenceIntegrityError):
        load_case_result("triangle", root=tampered_root)


def test_load_case_result_rejects_unknown_geometry():
    with pytest.raises(ValueError):
        load_case_result("hexagon")


def test_load_campaign_summary_rejects_wrong_repository_commit(tampered_root):
    summary_path = tampered_root / "campaign-summary.json"
    document = json.loads(summary_path.read_text())
    document["repository_commit"] = "f" * 40
    summary_path.write_text(json.dumps(document))

    with pytest.raises(FrozenS4ReferenceIntegrityError):
        load_campaign_summary(root=tampered_root)
