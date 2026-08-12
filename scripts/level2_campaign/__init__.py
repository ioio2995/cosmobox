"""Level2 campaign infrastructure: provenance resolution, deterministic
planning, structural validation gates, and atomic persistence.

Lot L2-E-CAMPAIGN-INFRASTRUCTURE. Never reimplements metrics.py/
profiles.py/adapter.py/orchestration.py: it only calls
cosmobox.level2.execution.run_case/compare_geometry and validates/
persists their already-computed output.

CASE_RESULT_PERSISTENCE = NOT_IMPLEMENTED_IN_THIS_LOT: see
cosmobox.level2.serialization's module docstring for the exact D2/D4
boundary this defers to a separate, explicitly authorized lot.
"""
