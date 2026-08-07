"""Single-case execution for the Level1B campaign. Level1B lot 1B-8
(docs/governance/current-task.md).

run_single_case executes exactly ONE CampaignCaseSpec (already planned by
experiments.level1.planning.build_campaign_plan) against the Manifest it
was planned from: diagonalizes it via Level0, selects every target group
via experiments.level1.target_selection (unchanged), and produces every
single-case quantity the manifest requires -- D020's multiplet
correlators, raw_G and its four derivatives, restricted diagnostics,
symmetry labels, O_ij_raw per minimal path, and covariance-validated
orbit statistics -- as schema-v2-validated, deterministically assembled
documents held in memory. Every spectral group identity is built via
results.build_spectral_group_identity (D022), never a bare 3-field
reconstruction, using the group's real position in the case's full,
unfiltered spectral-window sequence.

It never computes gamma_O, any inter-S MatchOutcome, or any robustness
verdict; it never writes to disk, loops over multiple cases, or resumes
anything -- those are a separate, later lot (see
docs/governance/current-task.md for the exact authorized scope).
"""

from __future__ import annotations

from dataclasses import dataclass

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import Lattice, build_lattice
from cosmobox.level0.reports import build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.assembly import AssemblyReport, assemble_execution
from cosmobox.level1.automorphisms import (
    UnitaryAutomorphism,
    generate_closed_unitary_subgroup,
    reflection_unitary_automorphism,
    symmetry_subgroup,
    translation_unitary_automorphism,
)
from cosmobox.level1.diagnostics import (
    build_hermitian_restricted_diagnostics,
    build_non_hermitian_restricted_diagnostics,
)
from cosmobox.level1.flavor import (
    build_flavor_correlator_matrix,
    flavor_frobenius_squared,
    flavor_singlet,
    flavor_singular_value_ratio,
    flavor_singular_values,
)
from cosmobox.level1.local_observables import (
    build_local_charge_operator,
    build_local_flavor_generators,
    charge_correlator_connected_group,
    charge_correlator_raw_group,
    flavor_correlator_connected_group,
    flavor_correlator_raw_group,
    normalized_charge_correlator,
)
from cosmobox.level1.matching import NUMERIC, SYMMETRY_TOLERANCE, UNAVAILABLE, SymmetryLabel, compute_restricted_symmetry_label, compute_twice_T
from cosmobox.level1.matter import build_dressed_matter_matrix
from cosmobox.level1.orbits import OrbitComparabilityKey, flavor_component_label, validate_orbit_covariance
from cosmobox.level1.paths import OrientedPath, minimal_paths
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    SpectralGroupState,
    build_restricted_operator,
    canonical_multiplet_expectation,
    exploratory_partial_subspace_mean,
    extract_group_state,
)
from cosmobox.level1.results import (
    HamiltonianIdentity,
    ResultRecord,
    ScientificIdentity,
    SpectralGroupIdentity,
    build_orbit_result_payload,
    build_result_record,
    build_spectral_group_identity,
)
from cosmobox.level1.serialization import serialize_result_record

from experiments.level1.manifest import Manifest
from experiments.level1.planning import CampaignCaseSpec, derive_case_seed
from experiments.level1.target_selection import SELECTED, TargetSelectionOutcome, select_target_group

N_FLAVORS = 2
"""D006, frozen everywhere in level1 -- CampaignCaseSpec carries no
separate n_flavors field because the whole codebase already hardcodes
this invariant (local_observables.py, matter.py, ...)."""

RAW_G_NORMALIZATION = "raw_G"
"""The single normalization-level tag ever produced by this runner: every
quantity here is the unnormalized ("raw") level of D018's three-level
raw_G/G_occ/gamma_O hierarchy -- G_occ and gamma_O are inter-S/unproduced
and out of scope for this runner."""

_FLAVOR_COMPONENT_PAIRS = ((0, 0), (0, 1), (1, 0), (1, 1))


@dataclass(frozen=True, slots=True)
class CaseExecutionResult:
    """The in-memory result of executing exactly one CampaignCaseSpec.
    `documents` are already schema-v2-validated and deterministically
    assembled (assembly.assemble_execution) -- nothing is written to
    disk. `target_outcomes` records every target's selection outcome,
    including ambiguous/not_in_window/structurally_not_applicable ones,
    which never contribute any document: an absent or ambiguous target
    is recorded explicitly here, never silently replaced by another
    group."""

    case_id: str
    target_outcomes: tuple[TargetSelectionOutcome, ...]
    documents: tuple[dict, ...]
    assembly_report: AssemblyReport


def _verify_case_belongs_to_manifest(case: CampaignCaseSpec, manifest: Manifest) -> None:
    """The case must actually have been planned from THIS manifest, not
    merely one that happens to share its shape: two manifests with
    identical grid/target content but different scientific_seed would
    plan cases with the same case_id but different per-case seeds, so
    re-deriving the expected seeds from manifest.scientific_seed and
    case.case_id (planning.derive_case_seed, unchanged) is a real,
    meaningful check -- not a formality."""
    if case.geometry not in manifest.target_groups:
        raise ValueError(f"case.geometry {case.geometry!r} is not a geometry in this manifest's target_groups")
    if case.target_groups != manifest.target_groups[case.geometry]:
        raise ValueError(
            f"case.target_groups for geometry {case.geometry!r} does not match this manifest's own "
            "target_groups -- the case was not planned from this manifest"
        )
    expected_scientific_seed = derive_case_seed(manifest.scientific_seed, case.case_id, "scientific")
    if case.scientific_seed != expected_scientific_seed:
        raise ValueError(
            f"case.scientific_seed ({case.scientific_seed}) does not match the seed derived from this "
            f"manifest's scientific_seed and the case's own case_id ({expected_scientific_seed}) -- the case "
            "was not planned from this manifest"
        )
    expected_solver_seed = derive_case_seed(manifest.scientific_seed, case.case_id, "solver")
    if case.solver_seed != expected_solver_seed:
        raise ValueError(
            f"case.solver_seed ({case.solver_seed}) does not match the seed derived from this manifest's "
            f"scientific_seed and the case's own case_id ({expected_solver_seed}) -- the case was not planned "
            "from this manifest"
        )


def _dispatch_expectation(operator, group_state: SpectralGroupState, *, hermitian: bool):
    """canonical_multiplet_expectation for a complete_multiplet group,
    exploratory_partial_subspace_mean for a partial_subspace one --
    dispatched on group_state.status, the same pattern D020's own
    _group_expectation uses in local_observables.py (not reused directly
    since it is private to that module)."""
    if group_state.status == COMPLETE_MULTIPLET:
        return canonical_multiplet_expectation(operator, group_state, hermitian=hermitian)
    return exploratory_partial_subspace_mean(operator, group_state, hermitian=hermitian)


def _hamiltonian_identity(case: CampaignCaseSpec) -> HamiltonianIdentity:
    return HamiltonianIdentity(
        J=case.hamiltonian_parameters.J,
        h_is_zero=True,
        t=case.hamiltonian_parameters.t,
        g_E=case.hamiltonian_parameters.g_E,
        K=case.hamiltonian_parameters.K,
    )


def _hamiltonian_identity_hashable(hamiltonian_identity: HamiltonianIdentity) -> tuple:
    """A JSON-safe (str/int/float/bool/None/tuple only, recursively --
    serialization._json_safe_hashable's own contract) tuple encoding of
    HamiltonianIdentity, for OrbitComparabilityKey.hamiltonian_identity
    (a caller-supplied Hashable with no canonical format shared with the
    structured HamiltonianIdentity type -- results.py's own docstring
    says this cross-check is deliberately not performed, so passing the
    dataclass instance itself would fail JSON serialization, not a
    results.py contract)."""
    return (hamiltonian_identity.J, hamiltonian_identity.h_is_zero, hamiltonian_identity.t, hamiltonian_identity.g_E, hamiltonian_identity.K)


def _scientific_identity(
    case: CampaignCaseSpec,
    hamiltonian_identity: HamiltonianIdentity,
    spectral_group_identity: SpectralGroupIdentity,
    *,
    path: tuple[int, ...] | None = None,
    flavor_component: str | None = None,
    normalization: str | None = None,
) -> ScientificIdentity:
    return ScientificIdentity(
        geometry=case.geometry,
        spin=case.spin,
        n_flavors=N_FLAVORS,
        hamiltonian=hamiltonian_identity,
        sector=case.sector_id,
        spectral_group=spectral_group_identity,
        path=path,
        flavor_component=flavor_component,
        normalization=normalization,
    )


def _group_twice_T(flavor_casimir, group_state: SpectralGroupState) -> int | None:
    """The group's own twice_T label, computed once per selected group
    regardless of which selection_kind found it (fundamental/
    first_excited groups get a real label here too, not just
    flavor_label ones) -- reuses matching.compute_twice_T directly, no
    second definition."""
    casimir_expectation = _dispatch_expectation(flavor_casimir, group_state, hermitian=True)
    return compute_twice_T(casimir_expectation)


def _flavor_casimir_label(twice_T: int | None) -> SymmetryLabel:
    """Represents matching.compute_twice_T's already-computed integer
    label as a SymmetryLabel (results.py's SYMMETRY_LABEL_KINDS names
    "flavor_casimir_label" as a symmetry_label observable, sharing
    SymmetryLabel as its payload type with translation/reflection
    characters -- no separate type is defined for it). This is a
    representation choice, not a new computation: NUMERIC with
    value=complex(twice_T) when the label resolved, UNAVAILABLE
    otherwise. Unlike translation/reflection, there is no "not_applicable"
    case here -- the flavor Casimir is always defined on the same Hilbert
    space regardless of the Hamiltonian's own symmetry."""
    if twice_T is None:
        return SymmetryLabel(kind=UNAVAILABLE, value=None)
    return SymmetryLabel(kind=NUMERIC, value=complex(twice_T))


def _translation_and_reflection_automorphisms(
    lattice: Lattice, spin: int, keys, key_index: dict[int, int]
) -> tuple[UnitaryAutomorphism, UnitaryAutomorphism]:
    translation = translation_unitary_automorphism(lattice, N_FLAVORS, spin, keys, key_index, external_charges=None)
    reflection = reflection_unitary_automorphism(lattice, N_FLAVORS, spin, keys, key_index, external_charges=None)
    return translation, reflection


def _symmetry_subgroup(lattice: Lattice, spin: int, keys, key_index: dict[int, int], hamiltonian) -> tuple[UnitaryAutomorphism, ...]:
    """The empirically-commuting closed subgroup (V07), used only for
    orbit covariance validation below -- translation/reflection
    CHARACTERS are computed directly against the single generator each
    (compute_restricted_symmetry_label already checks commutation itself
    per generator, no subgroup needed for that)."""
    translation, reflection = _translation_and_reflection_automorphisms(lattice, spin, keys, key_index)
    closed = generate_closed_unitary_subgroup([translation, reflection])
    return symmetry_subgroup(closed, hamiltonian, tolerance=SYMMETRY_TOLERANCE)


def _group_level_records(
    case: CampaignCaseSpec,
    hamiltonian_identity: HamiltonianIdentity,
    hamiltonian,
    spectral_group_identity: SpectralGroupIdentity,
    group_state: SpectralGroupState,
    flavor_casimir,
    lattice: Lattice,
    keys,
    key_index: dict[int, int],
) -> list[ResultRecord]:
    """Symmetry labels: properties of the selected group itself, produced
    once per group, never per pair or path."""
    identity = _scientific_identity(case, hamiltonian_identity, spectral_group_identity)

    flavor_label = _flavor_casimir_label(spectral_group_identity.twice_T)
    translation, reflection = _translation_and_reflection_automorphisms(lattice, case.spin, keys, key_index)
    translation_label = compute_restricted_symmetry_label(hamiltonian, translation, group_state)
    reflection_label = compute_restricted_symmetry_label(hamiltonian, reflection, group_state)

    seeds = dict(
        scientific_seed=case.scientific_seed,
        solver_seed=case.solver_seed,
        validation_rotation_seed=case.validation_rotation_seed,
    )
    return [
        build_result_record(identity, "symmetry_label", "flavor_casimir_label", flavor_label, **seeds),
        build_result_record(identity, "symmetry_label", "translation_character", translation_label, **seeds),
        build_result_record(identity, "symmetry_label", "reflection_character", reflection_label, **seeds),
    ]


def _node_diagnostic_records(
    case: CampaignCaseSpec,
    hamiltonian_identity: HamiltonianIdentity,
    spectral_group_identity: SpectralGroupIdentity,
    group_state: SpectralGroupState,
    lattice: Lattice,
    keys,
    key_index: dict[int, int],
    node: int,
) -> list[ResultRecord]:
    """Hermitian restricted diagnostics of the single-site charge
    operator Q_i -- the only single-site Hermitian operator this runner
    diagnoses (T_i^a diagnostics are not part of the manifest's required
    production list)."""
    identity = _scientific_identity(case, hamiltonian_identity, spectral_group_identity, path=(node,))

    charge_operator = build_local_charge_operator(lattice, N_FLAVORS, case.spin, keys, key_index, node)
    o_rest = build_restricted_operator(charge_operator, group_state)
    diagnostic = build_hermitian_restricted_diagnostics(o_rest, group_state)

    return [
        build_result_record(
            identity,
            "restricted_diagnostic",
            "C_QQ_raw",
            diagnostic,
            scientific_seed=case.scientific_seed,
            solver_seed=case.solver_seed,
            validation_rotation_seed=case.validation_rotation_seed,
        )
    ]


def _pair_correlator_records(
    case: CampaignCaseSpec,
    hamiltonian_identity: HamiltonianIdentity,
    spectral_group_identity: SpectralGroupIdentity,
    group_state: SpectralGroupState,
    lattice: Lattice,
    keys,
    key_index: dict[int, int],
    i: int,
    j: int,
) -> list[ResultRecord]:
    """C_QQ_raw/rho_QQ/C_TT_raw/C_TT_conn (D020): local-operator
    quantities with no path/transporter dependence at all -- produced
    once per ordered pair, never multiplied by the pair's path count."""
    identity = _scientific_identity(case, hamiltonian_identity, spectral_group_identity, path=(i, j))

    charge_i = build_local_charge_operator(lattice, N_FLAVORS, case.spin, keys, key_index, i)
    charge_j = build_local_charge_operator(lattice, N_FLAVORS, case.spin, keys, key_index, j)
    generators_i = build_local_flavor_generators(lattice, N_FLAVORS, case.spin, keys, key_index, i)
    generators_j = build_local_flavor_generators(lattice, N_FLAVORS, case.spin, keys, key_index, j)

    raw_charge = charge_correlator_raw_group(charge_i, charge_j, group_state)
    connected_charge = charge_correlator_connected_group(charge_i, charge_j, group_state)
    raw_flavor = flavor_correlator_raw_group(generators_i, generators_j, group_state)
    connected_flavor = flavor_correlator_connected_group(generators_i, generators_j, group_state)

    variance_i = charge_correlator_connected_group(charge_i, charge_i, group_state)
    variance_j = charge_correlator_connected_group(charge_j, charge_j, group_state)
    if not (connected_charge.status == variance_i.status == variance_j.status):
        raise ValueError(
            "rho_QQ's connected value and both variances must come from the same group_state status "
            f"(got {connected_charge.status!r}, {variance_i.status!r}, {variance_j.status!r})"
        )
    rho_qq = normalized_charge_correlator(connected_charge.value, variance_i.value, variance_j.value)

    seeds = dict(
        scientific_seed=case.scientific_seed,
        solver_seed=case.solver_seed,
        validation_rotation_seed=case.validation_rotation_seed,
    )
    return [
        build_result_record(identity, "raw_observable", "C_QQ_raw", raw_charge.value, **seeds),
        build_result_record(identity, "raw_observable", "C_TT_raw", raw_flavor.value, **seeds),
        build_result_record(identity, "raw_observable", "C_TT_conn", connected_flavor.value, **seeds),
        build_result_record(identity, "normalized_observable", "rho_QQ", rho_qq, **seeds),
    ]


def _pair_path_records(
    case: CampaignCaseSpec,
    hamiltonian_identity: HamiltonianIdentity,
    spectral_group_identity: SpectralGroupIdentity,
    group_state: SpectralGroupState,
    lattice: Lattice,
    keys,
    key_index: dict[int, int],
    path: OrientedPath,
    subgroup: tuple[UnitaryAutomorphism, ...],
) -> list[ResultRecord]:
    """raw_G and its four derivatives, O_ij_raw and its restricted
    diagnostics, and covariance-validated orbit statistics -- all
    path-dependent (the dressed operator transports along `path`),
    produced once per (ordered pair, minimal path). path_selection ==
    all_minimal_paths (D021): every minimal path of a pair gets its own
    records, never collapsed to a single arbitrarily-chosen path."""
    seeds = dict(
        scientific_seed=case.scientific_seed,
        solver_seed=case.solver_seed,
        validation_rotation_seed=case.validation_rotation_seed,
    )

    records: list[ResultRecord] = []

    correlator_matrix = build_flavor_correlator_matrix(lattice, N_FLAVORS, case.spin, keys, key_index, group_state, path)
    matrix_identity = _scientific_identity(
        case, hamiltonian_identity, spectral_group_identity, path=path.nodes, normalization=RAW_G_NORMALIZATION
    )
    records.append(build_result_record(matrix_identity, "flavor_diagnostic", "raw_G", correlator_matrix, **seeds))
    records.append(
        build_result_record(matrix_identity, "flavor_diagnostic", "flavor_singlet", flavor_singlet(correlator_matrix), **seeds)
    )
    records.append(
        build_result_record(
            matrix_identity, "flavor_diagnostic", "flavor_frobenius_squared", flavor_frobenius_squared(correlator_matrix), **seeds
        )
    )
    records.append(
        build_result_record(
            matrix_identity, "flavor_diagnostic", "flavor_singular_values", flavor_singular_values(correlator_matrix), **seeds
        )
    )
    records.append(
        build_result_record(
            matrix_identity,
            "flavor_diagnostic",
            "flavor_singular_value_ratio",
            flavor_singular_value_ratio(correlator_matrix),
            **seeds,
        )
    )

    for alpha, beta in _FLAVOR_COMPONENT_PAIRS:
        operator = build_dressed_matter_matrix(lattice, N_FLAVORS, case.spin, keys, key_index, path, alpha, beta)
        component_label = flavor_component_label(alpha, beta)
        component_identity = _scientific_identity(
            case, hamiltonian_identity, spectral_group_identity, path=path.nodes, flavor_component=component_label
        )

        raw_value = _dispatch_expectation(operator, group_state, hermitian=False)
        records.append(build_result_record(component_identity, "raw_observable", "O_ij_raw", raw_value, **seeds))

        o_rest = build_restricted_operator(operator, group_state)
        diagnostic = build_non_hermitian_restricted_diagnostics(o_rest, group_state)
        records.append(build_result_record(component_identity, "restricted_diagnostic", "O_ij_raw", diagnostic, **seeds))

        key = OrbitComparabilityKey(
            orbit_family=f"{case.geometry}-translation_reflection",
            path_length=path.length,
            spectral_group_key=(spectral_group_identity.status, spectral_group_identity.multiplicity, spectral_group_identity.twice_T),
            status=spectral_group_identity.status,
            observable_kind="O_ij_raw",
            normalization=RAW_G_NORMALIZATION,
            flavor_component=component_label,
            hamiltonian_identity=_hamiltonian_identity_hashable(hamiltonian_identity),
        )
        validated_orbit = validate_orbit_covariance(
            lattice, N_FLAVORS, case.spin, keys, key_index, subgroup, group_state, path, alpha, beta, key
        )
        orbit_payload = build_orbit_result_payload(validated_orbit)
        orbit_identity = _scientific_identity(
            case, hamiltonian_identity, spectral_group_identity, path=path.nodes, flavor_component=component_label, normalization=RAW_G_NORMALIZATION
        )
        records.append(build_result_record(orbit_identity, "orbit_statistic", "O_ij_raw", orbit_payload, **seeds))

    return records


def run_single_case(manifest: Manifest, case: CampaignCaseSpec, *, repository_commit: str) -> CaseExecutionResult:
    """Execute exactly one CampaignCaseSpec against the Manifest it was
    planned from: verify ownership, diagonalize, select every target,
    produce every single-case quantity for every SELECTED target group,
    serialize (schema v2), and assemble deterministically. Never writes
    to disk. Never produces gamma_O, G_occ, path_phase_coherence, a
    MatchOutcome, or a robustness verdict -- see the module docstring and
    docs/governance/current-task.md.

    manifest_fingerprint and campaign_id come from `manifest` itself
    (never independently supplied, so they cannot silently diverge from
    it); repository_commit remains a separate parameter since it is a
    genuinely external fact (the git SHA of the code that ran), not part
    of the manifest.
    """
    _verify_case_belongs_to_manifest(case, manifest)

    lattice = build_lattice(case.geometry)
    basis = build_basis(lattice, N_FLAVORS, case.spin, external_charges=None)
    key_index = build_key_index(basis.keys)
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, case.spin, basis.keys, key_index, case.hamiltonian_parameters)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, case.spin, basis, terms, case.hamiltonian_parameters, spectrum_options=case.spectrum_options
    )

    # The FULL, unfiltered spectral-window sequence -- group_states is
    # built in the same order, before any target selection or filtering,
    # so index i of either sequence is unambiguously groups[i]'s own
    # spectral_window_group_index (D022).
    groups = level0_report.spectrum.degeneracy.groups
    group_states = tuple(extract_group_state(eigenvectors, group) for group in groups)

    flavor_casimir = build_flavor_casimir(lattice, N_FLAVORS, case.spin, basis.keys, key_index)
    hamiltonian_identity = _hamiltonian_identity(case)
    hamiltonian = terms.total

    outcomes = tuple(
        select_target_group(
            target,
            groups,
            group_states,
            flavor_casimir=flavor_casimir,
            degeneracy_tolerance=case.spectrum_options.degeneracy_tolerance,
        )
        for target in case.target_groups
    )

    subgroup = _symmetry_subgroup(lattice, case.spin, basis.keys, key_index, hamiltonian)

    records: list[ResultRecord] = []
    already_produced_group_indices: set[int] = set()
    for outcome in outcomes:
        if outcome.status != SELECTED:
            continue
        group_index = outcome.group_index
        if group_index in already_produced_group_indices:
            # Two different targets (e.g. first_excited and a flavor_label
            # target) may resolve to the SAME physical group -- its
            # SpectralGroupIdentity is built exactly once, right here, and
            # every one of its records is produced exactly once: two
            # targets sharing a group therefore always share the exact
            # same identity, never two artificially different ones.
            continue
        already_produced_group_indices.add(group_index)

        group = groups[group_index]
        group_state = group_states[group_index]
        twice_T = _group_twice_T(flavor_casimir, group_state)
        spectral_group_identity = build_spectral_group_identity(
            group, group_state, spectral_window_group_index=group_index, twice_T=twice_T
        )

        records.extend(
            _group_level_records(
                case, hamiltonian_identity, hamiltonian, spectral_group_identity, group_state, flavor_casimir, lattice, basis.keys, key_index
            )
        )

        for node in lattice.nodes:
            records.extend(
                _node_diagnostic_records(
                    case, hamiltonian_identity, spectral_group_identity, group_state, lattice, basis.keys, key_index, node
                )
            )

        for i, j in case.ordered_pairs:
            records.extend(
                _pair_correlator_records(
                    case, hamiltonian_identity, spectral_group_identity, group_state, lattice, basis.keys, key_index, i, j
                )
            )
            for path in minimal_paths(lattice, i, j):
                records.extend(
                    _pair_path_records(
                        case, hamiltonian_identity, spectral_group_identity, group_state, lattice, basis.keys, key_index, path, subgroup
                    )
                )

    documents = [
        serialize_result_record(
            record,
            repository_commit=repository_commit,
            manifest_fingerprint=manifest.fingerprint,
            campaign_id=manifest.campaign_id,
        )
        for record in records
    ]
    assembled_documents, assembly_report = assemble_execution(documents)

    return CaseExecutionResult(
        case_id=case.case_id,
        target_outcomes=outcomes,
        documents=assembled_documents,
        assembly_report=assembly_report,
    )
