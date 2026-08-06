"""Deterministic Level1B campaign planning. Level1B lot 1B-8.

planning.py turns an already-loaded, already-validated Manifest
(manifest.py) into a deterministic, pure sequence of CampaignCaseSpec
objects -- one per (grid point, Hamiltonian case, sector) combination
required by the manifest. It performs no diagonalization, no matching, no
observable computation, and launches nothing: it only builds frozen,
self-verifying case descriptions and derives their seeds. Execution lives
in scripts/level1b_campaign/.

Per-case seeds are derived from the manifest's own root seed
(manifest.scientific_seed -- part of the fingerprinted manifest, never a
free parameter supplied outside it), the case's own canonical case_id,
and a seed role, via SHA-256 -- never Python's built-in hash() (unstable
across processes/versions, unsuitable for reproducible provenance).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions

from .manifest import GridPointSpec, HamiltonianCaseSpec, Manifest, TargetGroupSpec

CASE_ID_HASH_LENGTH = 16
"""Hex characters (64 bits) of case-content hash appended to the readable
case_id prefix -- ample collision resistance for this campaign's grid
size, while keeping case_id short enough to use as a directory name."""

_SEED_BYTE_LENGTH = 8
"""8 bytes -> a non-negative int in [0, 2**64), accepted by both
SpectrumOptions.seed and numpy.random.default_rng."""


def _canonical_hermitian_matrix_payload(matrix: np.ndarray) -> list:
    return [
        [[float(matrix[row, col].real), float(matrix[row, col].imag)] for col in range(matrix.shape[1])]
        for row in range(matrix.shape[0])
    ]


def _canonical_hamiltonian_parameters_payload(parameters: HamiltonianParameters) -> dict:
    return {
        "J": [float(value) for value in parameters.J],
        "h": [_canonical_hermitian_matrix_payload(matrix) for matrix in parameters.h],
        "t": float(parameters.t),
        "g_E": float(parameters.g_E),
        "K": float(parameters.K),
    }


def build_ordered_pairs(n_nodes: int) -> tuple[tuple[int, int], ...]:
    """All ordered pairs (i, j) with i != j -- the campaign's
    pair_selection == "all_ordered_distinct_pairs" policy. (i, j) and
    (j, i) are always two distinct elements of this plan: the dressed
    matter operator O_ij[P] is generally not equal to O_ji[P] (a
    different creation/annihilation site pair, generally a different
    path), so collapsing them would silently drop half the requested
    identities. A caller MAY internally skip recomputing a value it can
    prove symmetric (e.g. a provably-symmetric raw moment), but that is
    an optimization on top of this plan, never a change to the plan
    itself -- this function always returns both orderings.

    Deterministic order: i ascending, then j ascending (i != j), so
    (0, 1) always precedes (1, 0)."""
    if isinstance(n_nodes, bool) or not isinstance(n_nodes, int) or n_nodes < 0:
        raise ValueError(f"n_nodes must be a non-negative int, got {n_nodes!r}")
    return tuple((i, j) for i in range(n_nodes) for j in range(n_nodes) if i != j)


@dataclass(frozen=True, slots=True)
class CampaignCaseSpec:
    """A single, frozen, self-verifying campaign case. case_id is
    re-derived from the case's own other fields in __post_init__ and
    checked against the supplied value -- the same self-verification
    pattern as Level0ExperimentResult.config_fingerprint and
    ResultRecord's derived provenance: a caller cannot construct a
    CampaignCaseSpec with a case_id that does not actually match its
    content."""

    geometry: str
    spin: int
    hamiltonian_case_id: str
    hamiltonian_parameters: HamiltonianParameters
    sector_id: str
    spectral_window: int
    physical_dimension: int
    spectrum_options: SpectrumOptions
    target_groups: tuple[TargetGroupSpec, ...]
    ordered_pairs: tuple[tuple[int, int], ...]
    scientific_seed: int
    solver_seed: int
    validation_rotation_seed: int | None
    case_id: str

    def __post_init__(self) -> None:
        expected_case_id = compute_case_id(
            geometry=self.geometry,
            spin=self.spin,
            hamiltonian_case_id=self.hamiltonian_case_id,
            hamiltonian_parameters=self.hamiltonian_parameters,
            sector_id=self.sector_id,
            spectral_window=self.spectral_window,
            target_groups=self.target_groups,
        )
        if self.case_id != expected_case_id:
            raise ValueError(
                f"case_id {self.case_id!r} does not match compute_case_id(...) ({expected_case_id!r}); "
                "a well-formed but wrong case_id is a provenance failure"
            )
        for name, value in (("scientific_seed", self.scientific_seed), ("solver_seed", self.solver_seed)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative int, got {value!r}")
        if self.validation_rotation_seed is not None and (
            isinstance(self.validation_rotation_seed, bool)
            or not isinstance(self.validation_rotation_seed, int)
            or self.validation_rotation_seed < 0
        ):
            raise ValueError(
                f"validation_rotation_seed must be None or a non-negative int, "
                f"got {self.validation_rotation_seed!r}"
            )
        n_nodes = len(self.hamiltonian_parameters.J)
        expected_pairs = build_ordered_pairs(n_nodes)
        if self.ordered_pairs != expected_pairs:
            raise ValueError(
                f"ordered_pairs does not match build_ordered_pairs({n_nodes}) for this case's own "
                "hamiltonian_parameters.J length -- a well-formed but wrong pair plan is a provenance failure"
            )


def compute_case_id(
    *,
    geometry: str,
    spin: int,
    hamiltonian_case_id: str,
    hamiltonian_parameters: HamiltonianParameters,
    sector_id: str,
    spectral_window: int,
    target_groups: tuple[TargetGroupSpec, ...],
) -> str:
    """A readable prefix (geometry/spin/Hamiltonian case name/sector)
    followed by a short hash of the case's full canonical content --
    including the resolved Hamiltonian parameter values, never just the
    ``reference``/``j_break`` name, so that a manifest bug reusing a name
    with different parameters cannot silently collide."""
    readable = f"{geometry}-S{spin}-{hamiltonian_case_id}-{sector_id}"
    payload = {
        "geometry": geometry,
        "spin": spin,
        "hamiltonian_case_id": hamiltonian_case_id,
        "hamiltonian_parameters": _canonical_hamiltonian_parameters_payload(hamiltonian_parameters),
        "sector_id": sector_id,
        "spectral_window": spectral_window,
        "target_groups": [
            {
                "target_id": group.target_id,
                "selection_kind": group.selection_kind,
                "target_twice_T": group.target_twice_T,
                "selection_within_label": group.selection_within_label,
            }
            for group in target_groups
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:CASE_ID_HASH_LENGTH]
    return f"{readable}-{digest}"


def derive_case_seed(root_seed: int, case_id: str, role: str) -> int:
    """Stable per-(root_seed, case_id, role) seed, derived via SHA-256 --
    never Python's hash(), which is randomized per-process for str/bytes
    (PYTHONHASHSEED) and therefore not reproducible provenance."""
    if isinstance(root_seed, bool) or not isinstance(root_seed, int) or root_seed < 0:
        raise ValueError(f"root_seed must be a non-negative int, got {root_seed!r}")
    if not case_id:
        raise ValueError("case_id must be non-empty")
    if not role:
        raise ValueError("role must be non-empty")
    payload = json.dumps(
        {"root_seed": root_seed, "case_id": case_id, "role": role},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:_SEED_BYTE_LENGTH], byteorder="big", signed=False)


def _build_hamiltonian_parameters(case: HamiltonianCaseSpec, n_nodes: int) -> HamiltonianParameters:
    if case.J_override is None:
        J = tuple(case.J_uniform for _ in range(n_nodes))
    else:
        override_node, override_value = case.J_override
        if not (0 <= override_node < n_nodes):
            raise ValueError(
                f"hamiltonian case {case.hamiltonian_case_id!r}: J_override node_index {override_node} "
                f"is out of range for {n_nodes} nodes"
            )
        J = tuple(override_value if node == override_node else case.J_uniform for node in range(n_nodes))
    if not case.h_is_zero:
        raise ValueError(
            f"hamiltonian case {case.hamiltonian_case_id!r}: h_is_zero=False is not representable "
            "yet -- the manifest schema currently only admits h_is_zero=true"
        )
    zero_h = tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes))
    return HamiltonianParameters(J=J, h=zero_h, t=case.t, g_E=case.g_E, K=case.K)


def _build_spectrum_options(manifest: Manifest, grid_point: GridPointSpec, solver_seed: int) -> SpectrumOptions:
    return SpectrumOptions(
        max_dense_dimension=manifest.resource_guardrails.max_dense_dimension,
        max_sparse_dimension=manifest.resource_guardrails.max_sparse_dimension,
        n_eigenvalues=grid_point.spectral_window,
        force=False,
        seed=solver_seed,
        degeneracy_tolerance=manifest.degeneracy_tolerance,
    )


def build_campaign_plan(manifest: Manifest) -> tuple[CampaignCaseSpec, ...]:
    """Deterministic, pure plan: one CampaignCaseSpec per (grid point,
    Hamiltonian case, sector), in the manifest's own grid/sectors order.
    Builds objects and derives seeds only -- never diagonalizes, matches,
    or computes an observable.

    The root seed for every derived per-case seed is manifest.
    scientific_seed -- part of the fingerprinted manifest itself, never a
    free parameter a caller could vary independently of the manifest."""
    root_seed = manifest.scientific_seed

    hamiltonian_cases_by_id = {case.hamiltonian_case_id: case for case in manifest.hamiltonian_cases}
    lattice_node_counts: dict[str, int] = {}

    cases: list[CampaignCaseSpec] = []
    for grid_point in manifest.grid:
        if grid_point.geometry not in lattice_node_counts:
            lattice_node_counts[grid_point.geometry] = len(build_lattice(grid_point.geometry).nodes)
        n_nodes = lattice_node_counts[grid_point.geometry]
        target_groups = manifest.target_groups[grid_point.geometry]

        for hamiltonian_case_id in grid_point.hamiltonian_case_ids:
            hamiltonian_case = hamiltonian_cases_by_id[hamiltonian_case_id]
            hamiltonian_parameters = _build_hamiltonian_parameters(hamiltonian_case, n_nodes)

            for sector_id in manifest.sectors:
                case_id = compute_case_id(
                    geometry=grid_point.geometry,
                    spin=grid_point.spin,
                    hamiltonian_case_id=hamiltonian_case_id,
                    hamiltonian_parameters=hamiltonian_parameters,
                    sector_id=sector_id,
                    spectral_window=grid_point.spectral_window,
                    target_groups=target_groups,
                )
                scientific_seed = derive_case_seed(root_seed, case_id, "scientific")
                solver_seed = derive_case_seed(root_seed, case_id, "solver")
                cases.append(
                    CampaignCaseSpec(
                        geometry=grid_point.geometry,
                        spin=grid_point.spin,
                        hamiltonian_case_id=hamiltonian_case_id,
                        hamiltonian_parameters=hamiltonian_parameters,
                        sector_id=sector_id,
                        spectral_window=grid_point.spectral_window,
                        physical_dimension=grid_point.physical_dimension,
                        spectrum_options=_build_spectrum_options(manifest, grid_point, solver_seed),
                        target_groups=target_groups,
                        ordered_pairs=build_ordered_pairs(n_nodes),
                        scientific_seed=scientific_seed,
                        solver_seed=solver_seed,
                        # No module in this codebase replays a randomized
                        # validation step yet, so there is nothing to seed:
                        # left null per the "null unless actually replayed"
                        # provenance rule, not computed-but-unused.
                        validation_rotation_seed=None,
                        case_id=case_id,
                    )
                )

    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
        raise ValueError(f"build_campaign_plan produced duplicate case_id(s): {duplicates}")

    return tuple(cases)
