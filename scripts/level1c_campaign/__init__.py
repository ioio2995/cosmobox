"""Level1C Phase-P (NORMATIVE_PRODUCTION) execution and persistence.
Lot 1C-8c.

Mirrors the scripts/level1b_campaign/ split (runner.py executes one
case in memory, outputs.py persists it atomically) for the Level1C J0
x S response campaign -- reusing every applicable cosmobox.level1/
cosmobox.level0 scientific primitive verbatim, never duplicating them.

This package implements PHASE_P only: no baseline non-regression gate,
no inter-J0 tracking, no response phase, no campaign-level aggregation
of the 20 cases, and no real normative campaign execution. See
docs/governance/current-task.md for the exact authorized scope of each
lot.
"""
