from __future__ import annotations

import pytest

from experiments.level1c import manifest as m
from experiments.level1c import planning as p
from scripts.level1c_campaign.runner import run_level1c_case

REPO_COMMIT = "5159c2d68a060858cfd751e9b76365eecb2aba3e"


@pytest.fixture(scope="session")
def manifest() -> m.Level1CManifest:
    return m.load_manifest()


@pytest.fixture(scope="session")
def cases(manifest: m.Level1CManifest) -> tuple:
    return p.build_level1c_campaign_plan(manifest)


def _case(cases: tuple, *, geometry: str, spin: int, hamiltonian_case_id: str):
    return next(
        case
        for case in cases
        if case.geometry == geometry and case.spin == spin and case.hamiltonian_case_id == hamiltonian_case_id
    )


@pytest.fixture(scope="session")
def triangle_j0_1_00_case(cases: tuple):
    """Baseline: window=9, both REQUIRED targets on distinct complete
    groups (0, 1), T_max also resolving to group 1."""
    return _case(cases, geometry="triangle", spin=2, hamiltonian_case_id="j0-1.00")


@pytest.fixture(scope="session")
def triangle_j0_1_00_result(manifest: m.Level1CManifest, triangle_j0_1_00_case):
    return run_level1c_case(manifest, triangle_j0_1_00_case, repository_commit=REPO_COMMIT)


@pytest.fixture(scope="session")
def triangle_j0_0_50_case(cases: tuple):
    """Perturbed: window=5, T_max naturally selected on a partial_subspace
    group (real, unmocked exercise of the CALIBRATION_ONLY/
    non-conformant-but-never-blocking path)."""
    return _case(cases, geometry="triangle", spin=2, hamiltonian_case_id="j0-0.50")


@pytest.fixture(scope="session")
def triangle_j0_0_50_result(manifest: m.Level1CManifest, triangle_j0_0_50_case):
    return run_level1c_case(manifest, triangle_j0_0_50_case, repository_commit=REPO_COMMIT)


@pytest.fixture(scope="session")
def ring5_j0_1_00_case(cases: tuple):
    """Baseline: window=15, all three REQUIRED targets found on distinct
    complete groups, T_max naturally not_in_window."""
    return _case(cases, geometry="ring5", spin=2, hamiltonian_case_id="j0-1.00")


@pytest.fixture(scope="session")
def ring5_j0_1_00_result(manifest: m.Level1CManifest, ring5_j0_1_00_case):
    return run_level1c_case(manifest, ring5_j0_1_00_case, repository_commit=REPO_COMMIT)
