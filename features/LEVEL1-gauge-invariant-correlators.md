# Level 1 — Gauge-invariant relational correlators

Status: **feature definition — no implementation yet**

Branch: `research/level1-correlators`

Base: Level 0 closed by `experiments/LEVEL0-synthesis-and-closure.md`.

---

## 1. Purpose

Level 0 established an exact finite U(1) lattice-gauge substrate with:

- an explicitly constructed physical Hilbert space satisfying Gauss's law;
- complex fermionic matter with two flavors;
- finite-dimensional quantum links;
- exact sparse Hamiltonians;
- controlled spectral diagnostics;
- classified flavor and spatial symmetry sectors.

Level 1 introduces the first genuinely relational observables. Its purpose is to determine whether gauge-invariant correlations between matter degrees of freedom support a reproducible notion of relational separation across finite graphs and link truncations.

The objective is not to assume a geometry and recover it by construction. The objective is to measure gauge-invariant correlations on the exact physical states and determine whether a stable, interpretable spatial organization can be extracted from them.

---

## 2. Scope

This feature covers:

1. gauge-invariant two-point matter correlators joined by Wilson lines;
2. local gauge-invariant density observables;
3. flavor-resolved and flavor-summed correlators;
4. path selection and path dependence;
5. expectation values on non-degenerate states and degenerate spectral multiplets;
6. normalization conventions;
7. exact validation identities;
8. a small, pre-registered Level 1B campaign;
9. raw outputs suitable for later construction of an effective distance.

This feature does **not** yet define:

- an effective metric;
- a geodesic distance;
- curvature;
- causal structure;
- gravitational dynamics;
- continuum extrapolation;
- thermodynamic-limit claims.

Any distance-like quantity derived later from the correlators belongs to a subsequent feature and must not be silently folded into this one.

---

## 3. Frozen Level 0 conventions

Level 1 reuses without modification:

- the physical basis and encoding;
- Gauss-law projection;
- link orientation conventions;
- fermionic Jordan–Wigner ordering;
- Hamiltonian conventions;
- external-charge conventions;
- spectral degeneracy grouping;
- flavor-SU(2) generators and Casimir;
- translation and reflection operators;
- `S=2` as the scientific reference truncation, with `S=3` reserved for robustness controls where computationally feasible.

No Level 0 physical convention may be changed to simplify Level 1 observables.

---

## 4. Primary observables

### 4.1 Local occupation and charge

For node `i` and flavor `alpha`:

\[
 n_{i\alpha}=c^\dagger_{i\alpha}c_{i\alpha}.
\]

Flavor-summed occupation:

\[
 n_i=\sum_\alpha n_{i\alpha}.
\]

Dynamical charge, using the frozen Level 0 offset convention:

\[
 Q_i=n_i-1.
\]

Connected charge correlator:

\[
 C^{QQ}_{ij}
 =\langle Q_iQ_j\rangle
 -\langle Q_i\rangle\langle Q_j\rangle.
\]

This observable is local and gauge invariant. It provides a baseline against which Wilson-line-dressed matter correlators are compared.

### 4.2 Gauge-invariant dressed matter correlator

For an oriented path

\[
 P:i=v_0\to v_1\to\cdots\to v_\ell=j,
\]

define the path transporter:

\[
 W_P=\prod_{r=0}^{\ell-1} U_{e_r}^{s_r},
\]

where:

- `e_r` is the stored lattice edge corresponding to the step between `v_r` and `v_{r+1}`;
- `s_r=+1` when the path step follows the stored edge orientation;
- `s_r=-1` when it opposes it;
- `U_e^{-1}` means `U_e^\dagger` in the finite quantum-link representation.

The flavor-resolved dressed correlator is:

\[
 G^{\alpha\beta}_{ij}[P]
 =\left\langle
 c^\dagger_{i\alpha}
 W_P
 c_{j\beta}
 \right\rangle.
\]

The flavor trace is:

\[
 G_{ij}[P]
 =\sum_\alpha G^{\alpha\alpha}_{ij}[P].
\]

For the two-flavor model, the full 2×2 flavor matrix may also be retained:

\[
 \mathbf G_{ij}[P]
 =\left(G^{\alpha\beta}_{ij}[P]\right)_{\alpha,\beta=0,1}.
\]

### 4.3 Orientation reversal

For the reversed path `P^{-1}:j\to i`, the implementation must satisfy:

\[
 G^{\alpha\beta}_{ij}[P]
 =\left(G^{\beta\alpha}_{ji}[P^{-1}]\right)^*.
\]

This is a mandatory exact consistency identity, up to numerical precision in expectation values.

### 4.4 Zero-length path

For `i=j` and the empty path:

\[
 W_\varnothing=I,
\]

so that:

\[
 G^{\alpha\beta}_{ii}[\varnothing]
 =\langle c^\dagger_{i\alpha}c_{i\beta}\rangle.
\]

The diagonal element must reduce to the local occupation expectation.

---

## 5. Path conventions

Path dependence is physical in a gauge theory and must not be hidden.

### 5.1 Canonical path family

For every ordered node pair `(i,j)`, the campaign must enumerate all simple shortest paths in the underlying undirected graph.

The following quantities must be stored separately:

1. each individual path correlator `G_ij[P]`;
2. the number of shortest paths;
3. the arithmetic path average;
4. the maximum spread between shortest paths.

For a set of shortest paths `SP(i,j)`:

\[
 \overline G_{ij}
 =\frac{1}{|SP(i,j)|}
 \sum_{P\in SP(i,j)}G_{ij}[P].
\]

Path spread:

\[
 \Delta^{\mathrm{path}}_{ij}
 =\max_{P,Q\in SP(i,j)}|G_{ij}[P]-G_{ij}[Q]|.
\]

The path average is a reported derived observable, not a replacement for the individual paths.

### 5.2 Determinism

Path enumeration must be deterministic and independent of dictionary or set iteration order.

A path is serialized as an ordered node tuple, for example:

```json
{"nodes": [0, 1, 2]}
```

The corresponding oriented edge sequence must be derivable unambiguously from the lattice and is optionally included for auditability.

### 5.3 Non-shortest paths

Non-shortest simple paths are outside the initial Level 1B campaign. Their inclusion would mix correlation decay with Wilson-loop sensitivity and is deferred to a later feature.

---

## 6. Operator construction

### 6.1 Exact action on basis states

The dressed operator must be applied as an exact sequence on encoded basis states:

1. annihilate flavor `beta` at node `j`;
2. apply the ordered link transporters along `P`;
3. create flavor `alpha` at node `i`.

Elementary fermionic actions must reuse the existing Level 0 `annihilate` and `create` primitives.

Link raising or lowering must reuse the existing quantum-link conventions. A state that exceeds the allowed flux range is annihilated by the operator, as prescribed by the finite link representation.

The implementation must not infer gauge invariance by dropping states absent from the physical basis. Any nonzero transition whose resulting key is absent from the physical basis is an invariant violation and must raise.

### 6.2 Gauge-invariance validation

On the full unconstrained basis of a tractable small geometry, verify:

\[
 [G_k,\widehat G^{\alpha\beta}_{ij}[P]]=0
\]

for every Gauss generator `G_k`.

This test must cover:

- a path following stored orientations;
- a path containing at least one reversed edge;
- a zero-length path;
- at least one off-diagonal flavor component.

### 6.3 Hermitian combinations

The raw operator `c_i^\dagger W_P c_j` is generally non-Hermitian. For selected analyses, define:

\[
 X_{ij}[P]=\frac12\left(O_{ij}[P]+O_{ij}[P]^\dagger\right),
\]

\[
 Y_{ij}[P]=\frac{1}{2i}\left(O_{ij}[P]-O_{ij}[P]^\dagger\right).
\]

These combinations are diagnostic conveniences. The raw complex correlator remains the primary observable.

---

## 7. Degenerate spectral multiplets

Individual eigenvectors inside a degenerate eigenspace are basis-dependent. Level 1 must therefore distinguish state-specific values from multiplet-invariant quantities.

For a complete spectral group with orthonormal eigenvector matrix `Psi` and observable `O`, define the restricted matrix:

\[
 O_{\mathrm{rest}}=\Psi^\dagger O\Psi.
\]

### 7.1 Canonical multiplet average

The default scalar expectation for a complete multiplet of multiplicity `d` is the normalized trace:

\[
 \langle O\rangle_{\mathrm{mult}}
 =\frac{1}{d}\operatorname{Tr}(O_{\mathrm{rest}}).
\]

This is invariant under arbitrary unitary rotations within the degenerate eigenspace.

### 7.2 Multiplet spread

For Hermitian observables, report the eigenvalues of `O_rest` and their range.

For non-Hermitian observables, report:

- the normalized trace;
- singular values of `O_rest`;
- Frobenius norm;
- basis-invariance defect under test rotations.

The raw matrix may be retained in memory but must not be serialized unless explicitly approved in the campaign schema.

### 7.3 Symmetry-resolved refinement

Where a complete multiplet can be decomposed using commuting validated symmetry operators, the campaign may report symmetry-resolved subblocks. This is optional for the first implementation and must not replace the normalized full-multiplet trace.

### 7.4 Truncated spectral groups

A group marked `lower_bound_only=true` is not a complete multiplet.

For such a group:

- state-specific raw expectations may be reported as exploratory data;
- the normalized trace over the observed slice must be labelled `partial_subspace_trace`;
- it must not be described as a multiplet average;
- no invariance conclusion may depend on it.

---

## 8. Normalizations

Several normalizations are required because raw matter correlators mix occupation amplitudes with relational coherence.

### 8.1 Raw correlator

\[
 G_{ij}[P].
\]

Always retain the complex raw value.

### 8.2 Occupation-normalized coherence

For flavor-summed occupation:

\[
 \widetilde G_{ij}[P]
 =\frac{G_{ij}[P]}
 {\sqrt{\langle n_i\rangle\langle n_j\rangle}}.
\]

This is defined only when the denominator exceeds a frozen numerical floor.

Initial floor:

\[
 \epsilon_n=10^{-12}.
\]

When the denominator is below the floor, serialize `null` with an explicit reason rather than zero.

### 8.3 Connected density correlation coefficient

\[
 \rho^{QQ}_{ij}
 =\frac{C^{QQ}_{ij}}
 {\sqrt{C^{QQ}_{ii}C^{QQ}_{jj}}}.
\]

Apply the same `10^{-12}` denominator floor.

### 8.4 No distance transform in this feature

Expressions such as

\[
 -\log|\widetilde G_{ij}|
\]

or inverse-correlation distances are deliberately excluded. Their domain, regularization and triangle-inequality behavior require a separate pre-registered feature.

---

## 9. Numerical diagnostics

Every constructed observable must report or satisfy:

- matrix shape equal to the physical Hilbert-space dimension;
- finite sparse data;
- exact basis closure;
- gauge-commutator defect;
- adjoint-reversal identity defect;
- zero-path reduction defect;
- expectation-value finiteness;
- multiplet-subspace orthonormality defect;
- restriction defect where applicable.

Frozen engineering thresholds for the initial implementation:

```text
operator_identity_tolerance               = 1e-10
gauss_commutator_tolerance                = 1e-10
multiplet_orthonormality_tolerance         = 1e-8
complete_multiplet_invariance_tolerance    = 1e-8
occupation_normalization_floor             = 1e-12
```

These thresholds must be stored in the campaign manifest before execution and must not be adjusted after observing results.

---

## 10. Proposed public API

Names remain subject to implementation review, but the public contract should be no broader than necessary.

```python
@dataclass(frozen=True, slots=True)
class OrientedPath:
    nodes: tuple[int, ...]


def enumerate_shortest_paths(
    lattice: Lattice,
    source: int,
    target: int,
) -> tuple[OrientedPath, ...]: ...


def build_dressed_matter_operator(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    keys: Sequence[np.uint64],
    key_index: dict[int, int],
    source: int,
    target: int,
    source_flavor: int,
    target_flavor: int,
    path: OrientedPath,
) -> sp.csr_matrix: ...


def build_charge_operator(..., node: int) -> sp.csr_matrix: ...


def analyze_observable_in_subspaces(
    operator: sp.csr_matrix,
    operator_name: str,
    operator_kind: OperatorKind,
    eigenvectors: np.ndarray,
    degeneracy: DegeneracyReport,
) -> tuple[ObservableSectorDiagnostic, ...]: ...
```

The existing symmetry diagnostic API may be generalized only if the resulting abstraction remains clearer than maintaining a separate observable diagnostic type. This decision must be made during implementation review, not assumed here.

---

## 11. Level 1B reference campaign

### 11.1 Scientific reference

All primary runs use:

```text
n_flavors = 2
external_charges = 0
spin S = 2
J_i = 1
t = 1
g_E = 1
K = 1
h = 0
```

Geometries:

- triangle;
- ring4;
- ring5.

Spectral window:

- 16 lowest eigenvalues and retained eigenvectors;
- anchor-based degeneracy tolerance `1e-10`;
- complete and truncated groups treated separately.

### 11.2 Robustness controls

Subject to measured cost:

- triangle at `S=1,2,3`;
- ring4 at `S=1,2,3`;
- ring5 at `S=1,2`, with `S=3` only if tractable under the existing dimension guardrails.

No physical interpretation may rely on an observable that changes by more than the pre-registered truncation criterion between the two highest available `S` values.

The exact robustness threshold must be frozen before campaign execution. The Level 0 experience suggests that a universal 5% criterion may be too strict for all observables; Level 1 must pre-register observable-specific absolute and relative tolerances instead of tuning them after the fact.

### 11.3 State selection

Primary analysis targets:

1. the complete ground spectral group;
2. the first complete excited spectral group;
3. any complete `T=3/2` multiplet identified in Level 0;
4. no scientific conclusion from a window-truncated group.

### 11.4 Output per node pair

For every ordered node pair and every shortest path:

- raw flavor matrix `G^{alpha beta}`;
- flavor trace;
- normalized coherence when defined;
- charge connected correlator;
- normalized charge coefficient when defined;
- path-average values;
- path spread;
- multiplet averaging mode;
- truncation status;
- all numeric defects.

---

## 12. Validation tests

Minimum required tests before any real campaign:

### T1 — path validation

Reject:

- empty path with different endpoints;
- repeated nodes in a simple path;
- nonexistent edge steps;
- endpoint mismatch;
- out-of-range nodes.

### T2 — deterministic shortest paths

Verify exact path ordering on triangle, ring4 and ring5.

### T3 — physical-basis closure

Every nonzero dressed transition lands in the physical basis.

### T4 — full-space Gauss commutation

Verify exact commutation on a tractable unconstrained space.

### T5 — path reversal

Verify:

\[
 O_{ij}[P]^\dagger=O_{ji}[P^{-1}].
\]

### T6 — zero-path reduction

Verify equality with local one-body flavor operators.

### T7 — symmetry covariance

At spatially uniform parameters, verify translation and reflection covariance of the correlator family rather than requiring each fixed ordered pair operator to commute individually.

For an automorphism `A`:

\[
 U_A O_{ij}[P]U_A^\dagger
 =O_{A(i)A(j)}[A(P)].
\]

### T8 — multiplet basis invariance

Apply random unitary rotations inside a synthetic degenerate eigenspace and verify invariance of the normalized trace, singular values and Frobenius norm.

### T9 — truncated-group labelling

Ensure no partial subspace is serialized or described as a complete multiplet average.

### T10 — normalization floors

Verify `null` and explicit reason below the frozen denominator floor.

### T11 — exact small-model expectations

Use at least one hand-derived minimal basis case to validate signs, orientation and complex conjugation.

### T12 — campaign determinism and resume

Validate fingerprints, atomic outputs, manifest pre-registration and complete resume behavior.

---

## 13. Implementation lots

### 1A — path model and link transporter

- `OrientedPath` validation;
- deterministic shortest-path enumeration;
- exact link transporter action;
- tests T1–T2 and orientation tests.

### 1B — dressed matter and charge operators

- exact sparse operator construction;
- local charge operators;
- basis closure and Gauss tests;
- tests T3–T6 and T11.

### 1C — observable diagnostics on spectral groups

- normalized multiplet trace;
- Hermitian and non-Hermitian diagnostics;
- truncated-group contract;
- tests T8–T10.

### 1D — symmetry covariance

- translation/reflection covariance diagnostics for node-pair operator families;
- test T7.

### 1E — campaign tooling

- frozen Level 1B grid;
- thresholds and manifest;
- JSON/CSV output;
- resume and atomic writes;
- test T12;
- no real scientific execution yet.

### 1F — real campaign and analysis

- execute the pre-registered grid;
- preserve artefacts outside Git;
- report raw observations;
- classify robust and non-robust correlation structures;
- do not define an effective distance until a separate feature is approved.

Each lot requires independent review and validation before the next begins.

---

## 14. Acceptance criteria

Level 1B is complete when:

1. dressed matter correlators are proven gauge invariant under the exact finite conventions;
2. orientation and adjoint identities hold to the frozen tolerance;
3. multiplet averages are basis invariant;
4. truncated groups are never treated as complete multiplets;
5. raw and normalized correlators are available for all shortest paths and node pairs;
6. path dependence is explicitly quantified;
7. at least the reference `S=2` campaign succeeds for triangle, ring4 and ring5;
8. truncation robustness is measured on the approved controls;
9. no threshold or observable definition is changed after results are observed;
10. conclusions remain limited to relational correlation structure.

---

## 15. Authorized conclusions

If the acceptance criteria are met, Level 1B may establish:

- that gauge-invariant matter correlations are well-defined on the exact physical Hilbert space;
- whether they organize node pairs reproducibly across symmetry sectors;
- whether shortest-path correlators are path-independent, weakly path-dependent or strongly path-dependent on each graph;
- whether the observed organization is robust under link truncation;
- whether a later distance construction is scientifically justified.

Level 1B may not by itself establish an emergent metric or gravity.

---

## 16. Open decisions before implementation

The following decisions must be resolved and frozen before lot 1A begins:

1. whether the first campaign serializes the full flavor matrix or only the trace plus invariants;
2. the exact observable-specific truncation robustness thresholds;
3. whether ring5 at `S=3` is computationally admissible;
4. whether non-Hermitian restricted matrices require serialization of Schur data, or whether trace/singular values/Frobenius norm are sufficient;
5. the exact JSON schema and versioning boundary;
6. whether shared campaign I/O utilities should be factored out or remain campaign-local.

No code should be written until these decisions have been reviewed.