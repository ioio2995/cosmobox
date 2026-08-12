"""In-memory execution layer connecting an explicitly specified Level2 case
to the already-accepted D1-D3 chain, and grouping a geometry's S=2/S=3
results into an inter-S comparison.

Lot L2-D4-EXECUTION. No manifest, schema, runner, or result serialization
is introduced here -- CaseExecutionResult and GeometryComparison are plain,
transient in-memory structures. repository_commit/campaign_id/
manifest_fingerprint/schema_version belong to a future, separate
persistence layer and are deliberately absent from every type in this
module. No real Level2 case is ever executed by this module's own tests;
run_case itself is production code intended for a future, separately
authorized execution.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level2 import adapter, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.orchestration import CaseMetricAnalysis, ControlMetricAnalysis, PrimaryInterSComparison

GEOMETRIES: tuple[str, ...] = ("triangle", "ring4", "ring5")
SPINS: tuple[int, ...] = (2, 3)

REFERENCE_N_FLAVORS = 2
REFERENCE_EXTERNAL_CHARGES = None
"""The frozen Level2 contract's n_flavors and external_charges
(spectral-regime-design.md SS3: "n_flavors: 2", "charges ext: 0" --
None is normalize_external_charges's own all-zero default, never a
richer, separately-invented all-zero tuple). These are never caller-
supplied degrees of freedom: CaseSpec carries only (geometry, spin), and
run_case uses these two constants directly."""

L2_A1_PREFLIGHT_REFERENCE: dict[tuple[str, int], tuple[int, int]] = {
    ("triangle", 2): (88, 22),
    ("triangle", 3): (128, 32),
    ("ring4", 2): (292, 106),
    ("ring4", 3): (432, 158),
    ("ring5", 2): (1000, 226),
    ("ring5", 3): (1504, 342),
}
"""(dimension, complete_group_count) already recorded by the L2-A1
preflight (docs/governance/current-task.md, "Resultat L2-A1 -- preflight
plein spectre"). Reference data only: nothing in this module consumes it.
Comparing a real run_case(...) result against these values is a separate,
explicitly authorized future jalon (L2-D4 mandate SS7) -- this module
performs no real Level2 diagonalization, so nothing here is validated
against them yet."""


# ---------------------------------------------------------------------------
# 1. CaseSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseSpec:
    """One Level2 case: geometry and spin alone. This is deliberately the
    ENTIRE surface of a Level2 case at this layer: n_flavors, the
    Hamiltonian parameters, and external_charges are never caller-
    supplied degrees of freedom here -- they are exactly the frozen
    Level2 contract (spectral-regime-design.md SS3: reference
    Hamiltonian, J_i=1, h=0, t=1, g_E=1, K=1, n_flavors=2,
    external_charges=0), derived internally by run_case via
    REFERENCE_N_FLAVORS/REFERENCE_EXTERNAL_CHARGES/
    build_reference_hamiltonian_parameters. No physical variant is
    representable by this type."""

    geometry: str
    spin: int

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        if self.spin not in SPINS:
            raise ValueError(f"spin must be one of {SPINS}, got {self.spin!r}")


def build_reference_hamiltonian_parameters(n_nodes: int) -> HamiltonianParameters:
    """J_i=1, h=0, t=1, g_E=1, K=1 for every node -- exactly the
    "reference" Hamiltonian frozen by spectral-regime-design.md SS3. No
    other value is ever produced here."""
    if n_nodes < 1:
        raise ValueError(f"n_nodes must be >= 1, got {n_nodes}")
    return HamiltonianParameters(
        J=tuple(1.0 for _ in range(n_nodes)),
        h=tuple(np.zeros((2, 2), dtype=complex) for _ in range(n_nodes)),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )


def build_all_reference_case_specs() -> tuple[CaseSpec, ...]:
    """The six frozen Level2 cases, geometry-major then spin-minor order."""
    return tuple(CaseSpec(geometry=geometry, spin=spin) for geometry in GEOMETRIES for spin in SPINS)


# ---------------------------------------------------------------------------
# 2-5. run_case: Level0 construction, full spectrum, D2 adapter, D3
# analysis, assembled into an in-memory CaseExecutionResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseExecutionResult:
    """One case's execution result, entirely in memory. Carries no
    repository_commit/campaign_id/manifest_fingerprint/schema_version --
    those belong to a future persistence layer, not to this type."""

    spec: CaseSpec
    dimension: int
    group_count: int
    entries: tuple[MultipletProfileEntry, ...]
    m_tt_analysis: CaseMetricAnalysis
    r_eff_analysis: CaseMetricAnalysis
    a_qq_analysis: CaseMetricAnalysis
    m_qq_analysis: CaseMetricAnalysis

    def __post_init__(self) -> None:
        if not isinstance(self.spec, CaseSpec):
            raise ValueError(f"spec must be a CaseSpec, got {type(self.spec)}")
        if self.dimension < 1:
            raise ValueError(f"dimension must be >= 1, got {self.dimension}")
        if self.group_count < 1:
            raise ValueError(f"group_count must be >= 1, got {self.group_count}")
        if not self.entries:
            raise ValueError("entries must not be empty")
        if len(self.entries) != self.group_count:
            raise ValueError(
                f"len(entries) ({len(self.entries)}) does not match group_count ({self.group_count})"
            )
        total_multiplicity = sum(entry.multiplicity for entry in self.entries)
        if total_multiplicity != self.dimension:
            raise ValueError(
                f"entries' multiplicities sum to {total_multiplicity}, expected exactly "
                f"dimension={self.dimension}"
            )
        for metric, analysis in (
            ("M_TT", self.m_tt_analysis),
            ("R_eff", self.r_eff_analysis),
            ("A_QQ", self.a_qq_analysis),
            ("M_QQ", self.m_qq_analysis),
        ):
            if analysis.metric != metric:
                raise ValueError(f"{metric}_analysis.metric must be {metric!r}, got {analysis.metric!r}")

    def analysis_for(self, metric: str) -> CaseMetricAnalysis:
        by_metric = {
            "M_TT": self.m_tt_analysis,
            "R_eff": self.r_eff_analysis,
            "A_QQ": self.a_qq_analysis,
            "M_QQ": self.m_qq_analysis,
        }
        if metric not in by_metric:
            raise ValueError(f"metric must be one of {tuple(by_metric)}, got {metric!r}")
        return by_metric[metric]


def run_case(spec: CaseSpec) -> CaseExecutionResult:
    """Build `spec`'s Level0 case (full spectrum, n_eigenvalues always
    exactly the Hilbert-space dimension -- never a partial window), route
    it through the D2 adapter (which rejects the whole case, via its own
    PartialSubspaceCaseRejected, if any spectral group is
    partial_subspace -- never bypassed or caught here), then produce the
    four D3 metric analyses.

    n_flavors, the Hamiltonian parameters, and external_charges are never
    read from `spec` (it does not carry them): they are always exactly
    REFERENCE_N_FLAVORS, build_reference_hamiltonian_parameters(len(lattice.nodes)),
    and REFERENCE_EXTERNAL_CHARGES -- the frozen contract, with no
    caller-reachable degree of freedom to diverge from it."""
    lattice = build_lattice(spec.geometry)
    hamiltonian_params = build_reference_hamiltonian_parameters(len(lattice.nodes))

    basis = build_basis(lattice, REFERENCE_N_FLAVORS, spec.spin)
    dimension = len(basis.keys)
    key_index = build_key_index(basis.keys)

    terms = build_hamiltonian_terms(lattice, REFERENCE_N_FLAVORS, spec.spin, basis.keys, key_index, hamiltonian_params)
    report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice,
        REFERENCE_N_FLAVORS,
        spec.spin,
        basis,
        terms,
        hamiltonian_params,
        external_charges=REFERENCE_EXTERNAL_CHARGES,
        spectrum_options=SpectrumOptions(n_eigenvalues=dimension),
    )

    charge_operators, flavor_generators = adapter.build_case_operators(
        lattice, REFERENCE_N_FLAVORS, spec.spin, basis.keys, key_index
    )
    entries = adapter.build_case_multiplet_profile(report, eigenvectors, charge_operators, flavor_generators)

    return CaseExecutionResult(
        spec=spec,
        dimension=dimension,
        group_count=len(entries),
        entries=entries,
        m_tt_analysis=orchestration.analyze_case_metric(entries, "M_TT"),
        r_eff_analysis=orchestration.analyze_case_metric(entries, "R_eff"),
        a_qq_analysis=orchestration.analyze_case_metric(entries, "A_QQ"),
        m_qq_analysis=orchestration.analyze_case_metric(entries, "M_QQ"),
    )


# ---------------------------------------------------------------------------
# 6. compare_geometry: S=2/S=3 inter-S comparison for one geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeometryComparison:
    """One geometry's inter-S comparison: taxonomy + shape descriptors for
    the two primary metrics, descriptive-only analysis for the two control
    metrics. Carries no repository_commit/campaign_id/manifest_fingerprint/
    schema_version."""

    geometry: str
    result_s2: CaseExecutionResult
    result_s3: CaseExecutionResult
    m_tt: PrimaryInterSComparison
    r_eff: PrimaryInterSComparison
    a_qq: ControlMetricAnalysis
    m_qq: ControlMetricAnalysis

    def __post_init__(self) -> None:
        if self.result_s2.spec.geometry != self.geometry or self.result_s3.spec.geometry != self.geometry:
            raise ValueError(
                f"result_s2/result_s3 must both describe geometry={self.geometry!r}, got "
                f"{self.result_s2.spec.geometry!r} and {self.result_s3.spec.geometry!r}"
            )
        if self.result_s2.spec.spin != 2:
            raise ValueError(f"result_s2 must have spin == 2, got {self.result_s2.spec.spin!r}")
        if self.result_s3.spec.spin != 3:
            raise ValueError(f"result_s3 must have spin == 3, got {self.result_s3.spec.spin!r}")
        if self.m_tt.metric != "M_TT":
            raise ValueError(f"m_tt.metric must be 'M_TT', got {self.m_tt.metric!r}")
        if self.r_eff.metric != "R_eff":
            raise ValueError(f"r_eff.metric must be 'R_eff', got {self.r_eff.metric!r}")
        if self.a_qq.metric != "A_QQ":
            raise ValueError(f"a_qq.metric must be 'A_QQ', got {self.a_qq.metric!r}")
        if self.m_qq.metric != "M_QQ":
            raise ValueError(f"m_qq.metric must be 'M_QQ', got {self.m_qq.metric!r}")


def compare_geometry(result_s2: CaseExecutionResult, result_s3: CaseExecutionResult) -> GeometryComparison:
    """S=2 vs S=3 inter-S comparison for one geometry. M_TT/R_eff go
    through orchestration.compare_primary_metric_inter_s (taxonomy +
    C_X_23/D_X_23, L2-C1 guard reachable only via classify_inter_s on
    Delta_HL); A_QQ/M_QQ go through orchestration.
    compare_control_metric_inter_s (descriptive only). No multiplet-by-
    multiplet matching is performed anywhere: result_s2/result_s3 may
    (and normally do) come from different-dimension cases with
    independently partitioned q-profiles."""
    if result_s2.spec.geometry != result_s3.spec.geometry:
        raise ValueError(
            f"result_s2 and result_s3 must describe the same geometry, got "
            f"{result_s2.spec.geometry!r} and {result_s3.spec.geometry!r}"
        )
    if result_s2.spec.spin != 2:
        raise ValueError(f"result_s2 must have spin == 2, got {result_s2.spec.spin!r}")
    if result_s3.spec.spin != 3:
        raise ValueError(f"result_s3 must have spin == 3, got {result_s3.spec.spin!r}")

    return GeometryComparison(
        geometry=result_s2.spec.geometry,
        result_s2=result_s2,
        result_s3=result_s3,
        m_tt=orchestration.compare_primary_metric_inter_s(
            result_s2.analysis_for("M_TT"), result_s3.analysis_for("M_TT"), metric="M_TT"
        ),
        r_eff=orchestration.compare_primary_metric_inter_s(
            result_s2.analysis_for("R_eff"), result_s3.analysis_for("R_eff"), metric="R_eff"
        ),
        a_qq=orchestration.compare_control_metric_inter_s(
            result_s2.analysis_for("A_QQ"), result_s3.analysis_for("A_QQ"), metric="A_QQ"
        ),
        m_qq=orchestration.compare_control_metric_inter_s(
            result_s2.analysis_for("M_QQ"), result_s3.analysis_for("M_QQ"), metric="M_QQ"
        ),
    )
