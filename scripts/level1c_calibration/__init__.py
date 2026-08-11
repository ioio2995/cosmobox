"""Non-regression calibration tooling for Level 1C (1C-7c2).

tmax_nonregression.py implements the T_max baseline non-regression
calibration tool frozen documentarily in docs/levels/level1c/
identifiability-preregistration.md section 20.22: it compares a
historical Level 1B T_max record against a freshly recomputed Level 1C
J0=1 T_max record and derives NON_REGRESSION_CTT_ABS_TOL/
NON_REGRESSION_RHO_ABS_TOL via the frozen CEIL_DECADE_POLICY. This
package produces no J0!=1 response, no Delta_C_TT, no inter-J0 tracking,
and no geometry inference -- it is a calibration tool, never a campaign
runner.
"""
