"""Level2 campaign infrastructure: provenance resolution, deterministic
planning, structural validation gates, atomic persistence, and (lot
L2-E2-CASE-RESULT-AND-END-TO-END-RUNNER) the end-to-end campaign runner
(runner.run_campaign).

Never reimplements metrics.py/profiles.py/adapter.py/orchestration.py:
it only calls cosmobox.level2.execution.run_case/compare_geometry and
validates/persists their already-computed output.
"""
