from __future__ import annotations

import pytest

from experiments.level1.manifest import Manifest, load_manifest
from experiments.level1.planning import build_campaign_plan
from experiments.level1c import manifest as level1c_manifest_module
from scripts.level1b_analysis.indexing import CampaignArtifactIndex, build_campaign_artifact_index
from scripts.level1c_baseline_gate.gate import HISTORICAL_REPOSITORY_COMMIT

from level1c_baseline_gate_helpers import REAL_HISTORICAL_OUTPUT_DIR, real_level1c_baseline_case_id

# Only pytest fixtures live here (see level1c_baseline_gate_helpers.py's
# own docstring for why: a plain `from conftest import ...` in a test
# module collides across sibling test directories that each have their
# own conftest.py, e.g. tests/scripts/level1c_campaign/conftest.py).


@pytest.fixture(scope="session")
def historical_manifest() -> Manifest:
    return load_manifest()


@pytest.fixture(scope="session")
def historical_index(historical_manifest: Manifest) -> CampaignArtifactIndex:
    """Real, read-only, already-accepted Level1B historical archive --
    no diagonalization (build_campaign_artifact_index only loads and
    validates already-persisted JSON)."""
    return build_campaign_artifact_index(historical_manifest, REAL_HISTORICAL_OUTPUT_DIR, repository_commit=HISTORICAL_REPOSITORY_COMMIT)


@pytest.fixture(scope="session")
def historical_case_ids(historical_manifest: Manifest) -> dict[tuple[str, int], str]:
    result = {}
    for case in build_campaign_plan(historical_manifest):
        if case.hamiltonian_case_id == "reference" and case.geometry in ("triangle", "ring5") and case.spin in (2, 3):
            result[(case.geometry, case.spin)] = case.case_id
    return result


@pytest.fixture(scope="session")
def level1c_manifest() -> level1c_manifest_module.Level1CManifest:
    return level1c_manifest_module.load_manifest()


@pytest.fixture(scope="session")
def level1c_case_ids(level1c_manifest) -> dict[tuple[str, int], str]:
    return {
        (geometry, spin): real_level1c_baseline_case_id(level1c_manifest, geometry, spin)
        for geometry in ("triangle", "ring5")
        for spin in (2, 3)
    }
