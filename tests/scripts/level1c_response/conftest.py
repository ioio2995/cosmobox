from __future__ import annotations

import pytest

from experiments.level1c import manifest as level1c_manifest_module

# Only pytest fixtures live here (see level1c_response_helpers.py's own
# docstring for why: a plain `from conftest import ...` in a test module
# collides across sibling test directories that each have their own
# conftest.py).


@pytest.fixture(scope="session")
def level1c_manifest() -> level1c_manifest_module.Level1CManifest:
    return level1c_manifest_module.load_manifest()
