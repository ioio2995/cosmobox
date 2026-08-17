"""Level3 generic-spin execution layer (lot L3-B-GENERIC-EXECUTION-LAYER).

Reuses the accepted, already-generic-in-spin Level0 primitives
(build_lattice, build_basis, build_hamiltonian_terms, build_key_index,
build_level0_report_with_eigenvectors) directly, and reuses the Level2
primitives that are already generic in content -- never their public,
S=2/S=3-branded contract -- (adapter.build_case_operators,
adapter.build_case_multiplet_profile, orchestration.analyze_case_metric,
orchestration.compare_primary_metric_inter_s,
orchestration.compare_control_metric_inter_s). No Level2 file is imported
for its normative contract (execution.CaseSpec/GeometryComparison/
compare_geometry, serialization.py, experiments/level2/manifest.py,
schemas/level2/*, scripts/level2_campaign/*) and none of them is modified
by this module. Only REFERENCE_N_FLAVORS/REFERENCE_EXTERNAL_CHARGES/
build_reference_hamiltonian_parameters are imported unchanged from
cosmobox.level2.execution, so Level3 uses exactly the same reference
Hamiltonian as Level2 (n_flavors=2, J_i=1, h=0, t=1, g_E=1, K=1,
external_charges=0) rather than a second, independently maintained copy
that could silently drift from it.

CaseSpec is generic in spin: geometry is validated against Level0's own
lattice registry (cosmobox.level0.lattice.GEOMETRIES -- every geometry
build_lattice actually supports, not a Level2-specific subset of three),
and spin is validated by Level0's own generic validator
(cosmobox.level0.encoding.validate_spin: any integer >= 1). No whitelist
of specific spin values (no (2,3), no (2,3,4), ...) is reintroduced at
this layer.

compare_spin_pair reuses orchestration.compare_primary_metric_inter_s/
compare_control_metric_inter_s for their actual computation (same math,
same profile-comparison primitives, same taxonomy vocabulary,
multiplet-by-multiplet inter-S matching still FORBIDDEN), but re-exposes
the primary-metric result under spin-neutral field names
(SpinPairPrimaryComparison) instead of orchestration.
PrimaryInterSComparison's own S2/S3-branded fields (delta_hl_s2/s3,
c_x_23/d_x_23, direction_s2/s3) -- per the L3-B mandate's "descripteurs de
forme" clause (option A: encapsulate the reused Level2 result behind a
Level3-neutral structure). The reused taxonomy strings
(SAME_INTER_S_DIRECTION, OPPOSITE_INTER_S_DIRECTION,
NO_RESOLVED_SPECTRAL_CONTRAST, NOT_EVALUABLE) are the accepted Level2
vocabulary, carried here for technical continuity only -- this module does
not define, and must not be read as defining, a Level3 scientific
convergence protocol (S -> infinity convergence remains NOT_ESTABLISHED
and out of scope for this lot).

No new Hamiltonian term, no new metric, no new numerical tolerance, and no
multiplet-by-multiplet inter-S matching is introduced anywhere in this
module. No real S>=4 case is ever executed by this module's own tests;
run_case itself is production code intended for a future, separately
authorized execution (real S>=4 diagonalization requires its own
scientific pre-registration, not opened by this lot).

Full-spectrum execution policy (lot L3-B-D-E-CORRECTIVE /
L3-E-FULL-SPECTRUM-EXECUTION-POLICY): Level0's own dispatcher
(cosmobox.level0.reports._compute_spectrum) picks dense vs sparse purely
from SpectrumOptions.max_dense_dimension against the case's dimension --
it is never modified here. The sparse path (scipy.sparse.linalg.eigsh)
caps at k = dimension - 1 by construction and can therefore never return
a genuinely complete eigensystem; Level3's contract is full spectrum or
an explicit failure, never a silent partial result. run_case therefore
(a) builds full_spectrum_options(dimension) itself, forcing
max_dense_dimension (and, to keep SpectrumOptions' own invariant, if
needed max_sparse_dimension) up to at least `dimension` so Level0's
dispatcher can only choose the dense path; (b) checks
LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT *before* building the Hamiltonian,
refusing outright (FullSpectrumCapabilityExceeded) rather than ever
falling back to a partial sparse result; and (c) re-verifies, after
build_level0_report_with_eigenvectors returns, that the eigensystem
actually is complete (IncompleteSpectrumRejected otherwise) before any
D2/D3 primitive is ever called -- no observable is computed from an
incomplete spectrum under any circumstance.
"""

from __future__ import annotations

from dataclasses import dataclass

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import validate_spin
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import GEOMETRIES, build_lattice
from cosmobox.level0.reports import Level0Report, SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level2 import adapter, orchestration
from cosmobox.level2.adapter import MultipletProfileEntry
from cosmobox.level2.execution import (
    REFERENCE_EXTERNAL_CHARGES,
    REFERENCE_N_FLAVORS,
    build_reference_hamiltonian_parameters,
)
from cosmobox.level2.metrics import Available
from cosmobox.level2.orchestration import CaseMetricAnalysis

# ---------------------------------------------------------------------------
# 0. Full-spectrum execution policy: dense-path guarantee, operational
# capacity guard, post-diagonalization completeness assertion
# ---------------------------------------------------------------------------

LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT = 2008
"""Operational capacity limit for Level3's dense full-spectrum execution
path -- NOT a physical threshold, NOT a maximum spin, NOT a convergence
criterion, NOT a property of the model. It records what the L3-D synthetic
capability preflight actually demonstrated (SYNTHETIC_D2008_FULL_EIGENSYSTEM
= COMPLETE: a D=2008 dense Hermitian eigh completed in ~8.18s wall time at
~480 MiB peak RSS in the tested environment, with no OOM and no LAPACK
failure). It happens to equal the ring5 S=4 basis dimension found by the
L3-C capability preflight, but that is a coincidence of what was tested,
not a rule keyed to any particular (geometry, spin) pair -- nothing in this
module branches on 2008, 4, or any specific dimension/spin value. Raising
this limit requires a new, separately-run and separately-authorized
capability preflight, never an edit to this constant based on assumption
or extrapolation."""


class FullSpectrumCapabilityExceeded(RuntimeError):
    """Raised by run_case, before any Hamiltonian is built, when a case's
    Hilbert-space dimension exceeds LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT.

    This is deliberately NOT a statement that the case or the underlying
    model is invalid: it means the dense full-spectrum capability has not
    yet been validated at this dimension by a capability preflight. No
    sparse fallback is ever attempted to work around it -- Level3's
    contract is full spectrum or explicit failure, never a silently
    partial result."""


class IncompleteSpectrumRejected(RuntimeError):
    """Raised by run_case if, after calling
    build_level0_report_with_eigenvectors with full_spectrum_options, the
    returned report/eigenvectors do not actually constitute a complete
    eigensystem (status != "computed", computed_eigenvalues != dimension,
    eigenvectors missing, or eigenvectors of the wrong shape). No D2/D3
    primitive -- no observable of any kind -- is ever reached from this
    branch."""


def full_spectrum_options(dimension: int) -> SpectrumOptions:
    """SpectrumOptions guaranteed to make Level0's own dispatcher
    (reports._compute_spectrum: `dimension <= max_dense_dimension` ->
    dense) select the dense path and request exactly `dimension`
    eigenvalues -- the only way to obtain a genuinely complete
    eigensystem, since the sparse path caps at k = dimension - 1 by
    construction and can never satisfy a full-spectrum contract.
    max_sparse_dimension is raised alongside max_dense_dimension only when
    needed to keep SpectrumOptions' own frozen invariant
    (max_dense_dimension <= max_sparse_dimension) satisfied; it never
    otherwise changes reports.py's default sparse-path behavior, since the
    dense branch is always chosen first whenever it applies. Does not
    modify cosmobox.level0.reports in any way: it only chooses values for
    the SpectrumOptions dataclass reports.py already exposes."""
    if dimension < 1:
        raise ValueError(f"dimension must be >= 1, got {dimension}")
    default_max_sparse_dimension = SpectrumOptions().max_sparse_dimension
    return SpectrumOptions(
        n_eigenvalues=dimension,
        max_dense_dimension=dimension,
        max_sparse_dimension=max(dimension, default_max_sparse_dimension),
    )


def _check_dense_capability(dimension: int) -> None:
    """The operational capacity guard: refuses outright, before any
    Hamiltonian is built, if `dimension` exceeds the validated dense
    full-spectrum capability. Never a sparse fallback."""
    if dimension > LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT:
        raise FullSpectrumCapabilityExceeded(
            f"requested dimension={dimension} exceeds "
            f"LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT={LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT}, "
            "the dense full-spectrum capability established by the L3-D synthetic capability "
            "preflight. This is an operational capacity limit, not a physical or convergence "
            "judgement about the case itself -- a new capability preflight is required before "
            "Level3 can attempt a dense full-spectrum diagonalization at this dimension. No "
            "sparse fallback is attempted."
        )


def _assert_full_eigensystem(report: Level0Report, eigenvectors, dimension: int) -> None:
    """The post-diagonalization completeness assertion: no D2/D3
    primitive is ever reached unless the returned spectrum genuinely is
    the complete eigensystem for `dimension`."""
    if report.spectrum.status != "computed":
        raise IncompleteSpectrumRejected(
            f"spectrum status is {report.spectrum.status!r}, expected 'computed' -- refusing to "
            "build observables from an incomplete or failed spectrum"
        )
    if report.spectrum.computed_eigenvalues != dimension:
        raise IncompleteSpectrumRejected(
            f"computed_eigenvalues={report.spectrum.computed_eigenvalues} does not match the "
            f"full Hilbert-space dimension={dimension} -- Level3 requires a complete eigensystem, "
            "never a partial spectrum"
        )
    if eigenvectors is None:
        raise IncompleteSpectrumRejected("eigenvectors is None -- Level3 requires the full eigenvector set")
    if eigenvectors.shape != (dimension, dimension):
        raise IncompleteSpectrumRejected(
            f"eigenvectors.shape={eigenvectors.shape}, expected ({dimension}, {dimension})"
        )

# ---------------------------------------------------------------------------
# 1. CaseSpec: geometry + generic spin
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseSpec:
    """One Level3 case: geometry and spin alone, exactly like Level2's own
    CaseSpec -- n_flavors, the Hamiltonian parameters, and
    external_charges are never caller-supplied here either: they are
    exactly the same frozen reference Hamiltonian Level2 uses
    (REFERENCE_N_FLAVORS, REFERENCE_EXTERNAL_CHARGES,
    build_reference_hamiltonian_parameters, imported unchanged from
    cosmobox.level2.execution). No physical variant is representable by
    this type, and no new physical degree of freedom is exposed."""

    geometry: str
    spin: int

    def __post_init__(self) -> None:
        if self.geometry not in GEOMETRIES:
            raise ValueError(f"geometry must be one of {GEOMETRIES}, got {self.geometry!r}")
        validate_spin(self.spin)


# ---------------------------------------------------------------------------
# 2. run_case: identical conceptual chain to Level2's own run_case, generic
# in spin
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseExecutionResult:
    """One case's execution result, entirely in memory -- same shape as
    Level2's own CaseExecutionResult. Carries no repository_commit/
    campaign_id/manifest_fingerprint/schema_version: persistence is a
    future, separately authorized Level3 layer, not opened by this lot."""

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
    """Build `spec`'s Level0 case with a genuinely complete eigensystem --
    never a partial window, never a silent sparse-path truncation -- route
    it through the same D2 adapter (which rejects the whole case, via its
    own PartialSubspaceCaseRejected, if any spectral group is
    partial_subspace -- never bypassed or caught here) and the same D3
    metric analyses Level2 uses. Conceptually identical to
    cosmobox.level2.execution.run_case's own wiring, generic in
    spec.spin.

    Order of operations (L3-E mandate): basis -> dimension -> dense
    capability guard (_check_dense_capability, raising
    FullSpectrumCapabilityExceeded before any Hamiltonian is built if
    `dimension` exceeds LEVEL3_VALIDATED_DENSE_DIMENSION_LIMIT) ->
    Hamiltonian -> dense full eigensystem (full_spectrum_options(dimension)
    forces Level0's own dispatcher onto the dense path, never sparse) ->
    completeness assertion (_assert_full_eigensystem, raising
    IncompleteSpectrumRejected if the returned spectrum is not actually
    complete) -> only then D2/D3 observables.

    n_flavors, the Hamiltonian parameters, and external_charges are never
    read from `spec` (it does not carry them): they are always exactly
    REFERENCE_N_FLAVORS, build_reference_hamiltonian_parameters(len(lattice.nodes)),
    and REFERENCE_EXTERNAL_CHARGES -- the same frozen contract Level2 uses,
    imported unchanged, with no caller-reachable degree of freedom to
    diverge from it."""
    lattice = build_lattice(spec.geometry)

    basis = build_basis(lattice, REFERENCE_N_FLAVORS, spec.spin)
    dimension = len(basis.keys)
    _check_dense_capability(dimension)

    hamiltonian_params = build_reference_hamiltonian_parameters(len(lattice.nodes))
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
        spectrum_options=full_spectrum_options(dimension),
    )
    _assert_full_eigensystem(report, eigenvectors, dimension)

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
# 3. SpinPairComparison: explicit S_a <-> S_b comparison, spin-neutral names
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SpinPairPrimaryComparison:
    """Spin-neutral view of one primary metric's (M_TT or R_eff)
    inter-spin comparison. Computed via
    orchestration.compare_primary_metric_inter_s (same math, same L2-C1
    numerical guard reachable only through classify_contrast on
    delta_hl, same profile-comparison primitives) -- only the field names
    are remapped away from orchestration.PrimaryInterSComparison's own
    S2/S3-branded surface (delta_hl_s2/s3, c_x_23/d_x_23,
    direction_s2/s3). taxonomy/direction_lower/direction_higher reuse the
    accepted Level2 taxonomy vocabulary (SAME_INTER_S_DIRECTION,
    OPPOSITE_INTER_S_DIRECTION, NO_RESOLVED_SPECTRAL_CONTRAST,
    NOT_EVALUABLE) for technical continuity only -- this is NOT a Level3
    scientific convergence protocol, which remains a separate,
    not-yet-authorized future lot."""

    metric: str
    delta_hl_lower: Available
    delta_hl_higher: Available
    taxonomy: str
    direction_lower: str | None
    direction_higher: str | None
    cross_profile_correlation: Available
    cross_profile_distance: Available

    def __post_init__(self) -> None:
        if self.metric not in orchestration.PRIMARY_METRICS:
            raise ValueError(f"metric must be one of {orchestration.PRIMARY_METRICS}, got {self.metric!r}")


@dataclass(frozen=True, slots=True)
class SpinPairControlComparison:
    """Spin-neutral view of one control metric's (A_QQ or M_QQ) inter-spin
    companion: both spins' already-computed descriptive
    CaseMetricAnalysis, side by side. No taxonomy, no shape descriptor, no
    L2-C1 guard -- identical scope to orchestration.ControlMetricAnalysis,
    only the field names (analysis_a/analysis_b instead of
    analysis_s2/analysis_s3) are spin-neutral."""

    metric: str
    analysis_a: CaseMetricAnalysis
    analysis_b: CaseMetricAnalysis

    def __post_init__(self) -> None:
        if self.metric not in orchestration.CONTROL_METRICS:
            raise ValueError(f"metric must be one of {orchestration.CONTROL_METRICS}, got {self.metric!r}")


def _primary_comparison(
    analysis_a: CaseMetricAnalysis, analysis_b: CaseMetricAnalysis, *, metric: str
) -> SpinPairPrimaryComparison:
    raw = orchestration.compare_primary_metric_inter_s(analysis_a, analysis_b, metric=metric)
    return SpinPairPrimaryComparison(
        metric=metric,
        delta_hl_lower=raw.delta_hl_s2,
        delta_hl_higher=raw.delta_hl_s3,
        taxonomy=raw.classification.taxonomy,
        direction_lower=raw.classification.direction_s2,
        direction_higher=raw.classification.direction_s3,
        cross_profile_correlation=raw.c_x_23,
        cross_profile_distance=raw.d_x_23,
    )


def _control_comparison(
    analysis_a: CaseMetricAnalysis, analysis_b: CaseMetricAnalysis, *, metric: str
) -> SpinPairControlComparison:
    raw = orchestration.compare_control_metric_inter_s(analysis_a, analysis_b, metric=metric)
    return SpinPairControlComparison(metric=metric, analysis_a=raw.analysis_s2, analysis_b=raw.analysis_s3)


@dataclass(frozen=True, slots=True)
class SpinPairComparison:
    """One geometry's explicit S_a <-> S_b comparison: taxonomy + shape
    descriptors for the two primary metrics (spin-neutral names),
    side-by-side descriptive analysis for the two control metrics.
    result_a/result_b are ordered strictly by spin
    (result_a.spec.spin < result_b.spec.spin) -- not necessarily
    consecutive: 2<->3, 2<->4, 3<->4, 4<->6, etc. are all representable.
    Carries no repository_commit/campaign_id/manifest_fingerprint/
    schema_version."""

    geometry: str
    result_a: CaseExecutionResult
    result_b: CaseExecutionResult
    m_tt: SpinPairPrimaryComparison
    r_eff: SpinPairPrimaryComparison
    a_qq: SpinPairControlComparison
    m_qq: SpinPairControlComparison

    def __post_init__(self) -> None:
        if self.result_a.spec.geometry != self.geometry or self.result_b.spec.geometry != self.geometry:
            raise ValueError(
                f"result_a/result_b must both describe geometry={self.geometry!r}, got "
                f"{self.result_a.spec.geometry!r} and {self.result_b.spec.geometry!r}"
            )
        if self.result_a.spec.spin >= self.result_b.spec.spin:
            raise ValueError(
                "result_a.spec.spin must be strictly less than result_b.spec.spin, got "
                f"{self.result_a.spec.spin!r} and {self.result_b.spec.spin!r}"
            )
        if self.m_tt.metric != "M_TT":
            raise ValueError(f"m_tt.metric must be 'M_TT', got {self.m_tt.metric!r}")
        if self.r_eff.metric != "R_eff":
            raise ValueError(f"r_eff.metric must be 'R_eff', got {self.r_eff.metric!r}")
        if self.a_qq.metric != "A_QQ":
            raise ValueError(f"a_qq.metric must be 'A_QQ', got {self.a_qq.metric!r}")
        if self.m_qq.metric != "M_QQ":
            raise ValueError(f"m_qq.metric must be 'M_QQ', got {self.m_qq.metric!r}")


def compare_spin_pair(result_a: CaseExecutionResult, result_b: CaseExecutionResult) -> SpinPairComparison:
    """Explicit S_a <-> S_b inter-spin comparison for one geometry, for
    any two distinct spins -- not limited to S=2/S=3, not required to be
    consecutive. result_a must carry the strictly lower spin
    (result_a.spec.spin < result_b.spec.spin); reorder the call site if
    needed. Reuses orchestration.compare_primary_metric_inter_s/
    compare_control_metric_inter_s for the actual computation (same math,
    same profile primitives): no multiplet-by-multiplet matching is
    performed anywhere, result_a/result_b may (and normally do) come from
    different-dimension cases with independently partitioned q-profiles."""
    if result_a.spec.geometry != result_b.spec.geometry:
        raise ValueError(
            f"result_a and result_b must describe the same geometry, got "
            f"{result_a.spec.geometry!r} and {result_b.spec.geometry!r}"
        )
    if result_a.spec.spin >= result_b.spec.spin:
        raise ValueError(
            "result_a.spec.spin must be strictly less than result_b.spec.spin, got "
            f"{result_a.spec.spin!r} and {result_b.spec.spin!r}"
        )

    return SpinPairComparison(
        geometry=result_a.spec.geometry,
        result_a=result_a,
        result_b=result_b,
        m_tt=_primary_comparison(result_a.analysis_for("M_TT"), result_b.analysis_for("M_TT"), metric="M_TT"),
        r_eff=_primary_comparison(result_a.analysis_for("R_eff"), result_b.analysis_for("R_eff"), metric="R_eff"),
        a_qq=_control_comparison(result_a.analysis_for("A_QQ"), result_b.analysis_for("A_QQ"), metric="A_QQ"),
        m_qq=_control_comparison(result_a.analysis_for("M_QQ"), result_b.analysis_for("M_QQ"), metric="M_QQ"),
    )
