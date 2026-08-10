"""Level1C normative campaign manifest/schema/planning tooling. Lot
1C-8b (docs/governance/current-task.md).

Machine-readable manifest loading/validation/fingerprint, deterministic
campaign planning (20 J0 x S cases), baseline/tracking-edge derivation,
and target-selection persistence for the frozen J0 x S response
campaign (docs/levels/level1c/identifiability-preregistration.md
sections 15-20). Built on top of the public cosmobox.level1 API and the
existing experiments.level1 primitives, never modifying them.

This package contains no scientific runner: it never diagonalizes,
never computes an observable, never tracks a spectral group across J0,
and never derives a physical response. Those belong to later, distinct
lots (see docs/governance/current-task.md for the exact authorized
scope of each).
"""
