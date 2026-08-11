from __future__ import annotations

import pytest

from experiments.level1c import manifest as manifest_module

# Only pytest fixtures live here -- see level1c_launcher_helpers.py's own
# docstring for why non-fixture helpers live in a uniquely-named module
# instead.


@pytest.fixture(scope="module")
def real_manifest() -> manifest_module.Level1CManifest:
    return manifest_module.load_manifest()
