"""Immutable intra-case spectral-group index over already-loaded Level1B
campaign documents. Level1B lot 1B-9b (docs/governance/current-task.md).

build_campaign_artifact_index groups every case's documents by
identity.spectral_group.spectral_window_group_index (D022's own exact,
intra-case discriminant -- never energy rank, never target_id, which is
never reconstructed anywhere in this module) and reconstructs exactly
one cosmobox.level1.matching.SpectralGroupMatchKey per group, from
already-serialized fields alone -- never a physical recomputation.
spectral_window_group_index and representative_energy are carried on
the index purely as intra-case identity/audit metadata (D022) and are
never placed inside a SpectralGroupMatchKey.

This module performs no inter-S comparison: it never calls
match_spectral_group, evaluate_robustness, or compute_gamma_o, and never
imports them. matching.py and robustness.py are reused only for the
frozen dataclass types they already define (SpectralGroupMatchKey,
SymmetryLabel) -- never modified, never re-implemented.

A group whose identity.spectral_group.twice_T is null (an unresolved
flavor label) is never given a SpectralGroupMatchKey and never produces
any matching.py outcome (not even ambiguous_cross_truncation_match,
which belongs exclusively to matching.py's own vocabulary for a
different situation) -- it raises UnresolvedFlavorLabelError instead,
blocking the whole index build. Per D018, an unresolved flavor label
makes exact inter-S matching impossible for that group; this lot treats
that as a precondition failure of index construction itself, not
something for a later matching step to silently work around.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmobox.level1.matching import SpectralGroupMatchKey, SymmetryLabel
from cosmobox.level1.results import SpectralGroupIdentity
from experiments.level1.manifest import Manifest
from experiments.level1.planning import CampaignCaseSpec

from .loader import FrozenDocument, LoadedCase, _is_deeply_frozen, load_validated_cases

_EXPECTED_N_FLAVORS = 2
"""D006, frozen everywhere in level1 -- ScientificIdentity.__post_init__
itself already enforces this; restated here as an independent
cross-check on the deserialized JSON, never imported from runner.py."""


class SpectralGroupIndexError(RuntimeError):
    """Raised for any provenance or structural inconsistency discovered
    while indexing a case's documents into spectral groups -- a document
    disagreeing with its own case, a group whose documents disagree on
    identity.spectral_group, a missing/duplicated group-level symmetry
    label, or a flavor_casimir_label disagreeing with its own group's
    twice_T. Always raised before any index is returned."""


class UnresolvedFlavorLabelError(SpectralGroupIndexError):
    """Raised specifically when identity.spectral_group.twice_T is null
    for some group -- see the module docstring. A dedicated subclass so
    callers can distinguish this specific, D018-grounded precondition
    from an ordinary provenance/structural error."""


@dataclass(frozen=True, slots=True)
class IndexedSpectralGroup:
    """One physical spectral group of one case, deduplicated by
    identity.spectral_group.spectral_window_group_index (D022's exact
    intra-case discriminant), together with every document that belongs
    to it and the SpectralGroupMatchKey reconstructed for it. Never
    carries a target_id -- D022: identity belongs to the group, never to
    the selection rule that found it."""

    case_id: str
    case: CampaignCaseSpec
    spectral_group_identity: SpectralGroupIdentity
    spectral_window_group_index: int
    match_key: SpectralGroupMatchKey
    documents: tuple[FrozenDocument, ...]

    def __post_init__(self) -> None:
        if self.case_id != self.case.case_id:
            raise ValueError(f"case_id ({self.case_id!r}) does not match case.case_id ({self.case.case_id!r})")
        if self.spectral_window_group_index != self.spectral_group_identity.spectral_window_group_index:
            raise ValueError(
                f"spectral_window_group_index ({self.spectral_window_group_index}) does not match "
                f"spectral_group_identity.spectral_window_group_index "
                f"({self.spectral_group_identity.spectral_window_group_index})"
            )
        if not self.documents:
            raise ValueError(f"documents must be non-empty for case {self.case_id!r} group {self.spectral_window_group_index}")
        for index, document in enumerate(self.documents):
            if not _is_deeply_frozen(document):
                raise ValueError(
                    f"documents[{index}] for case {self.case_id!r} group {self.spectral_window_group_index} is "
                    "not deeply frozen (a types.MappingProxyType root is not enough -- every nested dict/list "
                    "must also be frozen, and every mapping key must be a str) -- construct IndexedSpectralGroup "
                    "only via build_campaign_artifact_index, never with a partially frozen or forged document"
                )


@dataclass(frozen=True, slots=True)
class CampaignArtifactIndex:
    """The full, immutable index of a normative campaign's already-
    validated artifacts. `cases` preserves build_campaign_plan(manifest)'s
    own order; `groups` preserves case order, then
    spectral_window_group_index order within each case -- never
    filesystem/glob order."""

    manifest_fingerprint: str
    campaign_id: str
    repository_commit: str
    cases: tuple[LoadedCase, ...]
    groups: tuple[IndexedSpectralGroup, ...]

    def __post_init__(self) -> None:
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.repository_commit:
            raise ValueError("repository_commit must be non-empty")
        case_ids = [loaded_case.case.case_id for loaded_case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError(f"cases contains duplicate case_id(s): {sorted({c for c in case_ids if case_ids.count(c) > 1})}")
        group_keys = [(group.case_id, group.spectral_window_group_index) for group in self.groups]
        if len(group_keys) != len(set(group_keys)):
            raise ValueError("groups contains duplicate (case_id, spectral_window_group_index) pair(s)")


def _case_hamiltonian_identity_tuple(case: CampaignCaseSpec) -> tuple:
    """The same canonical shape as a document's own identity.hamiltonian
    once deserialized (_document_hamiltonian_identity_tuple below) --
    derived directly from the case's own HamiltonianParameters, h_is_zero
    computed from case.hamiltonian_parameters.h itself (never assumed
    True), never imported from runner.py's own private helper."""
    parameters = case.hamiltonian_parameters
    h_is_zero = all(bool(np.all(matrix == 0)) for matrix in parameters.h)
    return (
        tuple(float(value) for value in parameters.J),
        h_is_zero,
        float(parameters.t),
        float(parameters.g_E),
        float(parameters.K),
    )


def _document_hamiltonian_identity_tuple(hamiltonian: FrozenDocument) -> tuple:
    return (
        tuple(float(value) for value in hamiltonian["J"]),
        hamiltonian["h_is_zero"],
        float(hamiltonian["t"]),
        float(hamiltonian["g_E"]),
        float(hamiltonian["K"]),
    )


def _require_document_matches_case(document: FrozenDocument, case: CampaignCaseSpec, expected_hamiltonian: tuple) -> None:
    identity = document["identity"]
    provenance = document["provenance"]

    if identity["geometry"] != case.geometry:
        raise SpectralGroupIndexError(
            f"case {case.case_id!r}: document identity.geometry ({identity['geometry']!r}) != case.geometry "
            f"({case.geometry!r})"
        )
    if identity["spin"] != case.spin:
        raise SpectralGroupIndexError(f"case {case.case_id!r}: document identity.spin ({identity['spin']!r}) != case.spin ({case.spin!r})")
    if identity["sector"] != case.sector_id:
        raise SpectralGroupIndexError(
            f"case {case.case_id!r}: document identity.sector ({identity['sector']!r}) != case.sector_id ({case.sector_id!r})"
        )
    if identity["n_flavors"] != _EXPECTED_N_FLAVORS:
        raise SpectralGroupIndexError(
            f"case {case.case_id!r}: document identity.n_flavors ({identity['n_flavors']!r}) != {_EXPECTED_N_FLAVORS} (D006)"
        )
    if _document_hamiltonian_identity_tuple(identity["hamiltonian"]) != expected_hamiltonian:
        raise SpectralGroupIndexError(
            f"case {case.case_id!r}: document identity.hamiltonian ({identity['hamiltonian']!r}) does not match "
            f"the case's own hamiltonian_parameters"
        )

    seeds = (provenance["scientific_seed"], provenance["solver_seed"], provenance["validation_rotation_seed"])
    expected_seeds = (case.scientific_seed, case.solver_seed, case.validation_rotation_seed)
    if seeds != expected_seeds:
        raise SpectralGroupIndexError(
            f"case {case.case_id!r}: document provenance seeds {seeds} do not match the case's own "
            f"(scientific_seed, solver_seed, validation_rotation_seed) {expected_seeds}"
        )

    if provenance["spectral_status"] != identity["spectral_group"]["status"]:
        raise SpectralGroupIndexError(
            f"case {case.case_id!r}: document provenance.spectral_status ({provenance['spectral_status']!r}) "
            f"!= identity.spectral_group.status ({identity['spectral_group']['status']!r})"
        )


def _exactly_one_group_level_record(documents: tuple[FrozenDocument, ...], observable_kind: str, case_id: str, group_index: int) -> FrozenDocument:
    matches = [
        document
        for document in documents
        if document["record_kind"] == "symmetry_label"
        and document["observable_kind"] == observable_kind
        and document["identity"]["path"] is None
    ]
    if len(matches) != 1:
        raise SpectralGroupIndexError(
            f"case {case_id!r} group index {group_index}: expected exactly 1 group-level {observable_kind!r} "
            f"record, found {len(matches)}"
        )
    return matches[0]


def _symmetry_label_from_payload(payload: FrozenDocument) -> SymmetryLabel:
    if payload["kind"] == "numeric":
        value = payload["value"]
        return SymmetryLabel(kind="numeric", value=complex(value["real"], value["imag"]))
    return SymmetryLabel(kind=payload["kind"], value=None)


def _require_flavor_casimir_matches_twice_t(flavor_casimir_record: FrozenDocument, twice_t: int, case_id: str, group_index: int) -> None:
    payload = flavor_casimir_record["payload"]
    if payload["kind"] != "numeric" or payload["value"]["real"] != float(twice_t) or payload["value"]["imag"] != 0.0:
        raise SpectralGroupIndexError(
            f"case {case_id!r} group index {group_index}: flavor_casimir_label payload {payload!r} does not "
            f"exactly match identity.spectral_group.twice_T ({twice_t!r})"
        )


def _build_indexed_group(case: CampaignCaseSpec, group_index: int, documents: tuple[FrozenDocument, ...]) -> IndexedSpectralGroup:
    reference_spectral_group = documents[0]["identity"]["spectral_group"]
    for document in documents[1:]:
        spectral_group = document["identity"]["spectral_group"]
        if spectral_group != reference_spectral_group:
            raise SpectralGroupIndexError(
                f"case {case.case_id!r} group index {group_index}: documents disagree on identity.spectral_group: "
                f"{reference_spectral_group!r} vs {spectral_group!r}"
            )

    spectral_group_identity = SpectralGroupIdentity(
        status=reference_spectral_group["status"],
        multiplicity=reference_spectral_group["multiplicity"],
        twice_T=reference_spectral_group["twice_T"],
        spectral_window_group_index=reference_spectral_group["spectral_window_group_index"],
        representative_energy=reference_spectral_group["representative_energy"],
    )

    flavor_casimir_record = _exactly_one_group_level_record(documents, "flavor_casimir_label", case.case_id, group_index)
    translation_record = _exactly_one_group_level_record(documents, "translation_character", case.case_id, group_index)
    reflection_record = _exactly_one_group_level_record(documents, "reflection_character", case.case_id, group_index)

    if spectral_group_identity.twice_T is None:
        raise UnresolvedFlavorLabelError(
            f"case {case.case_id!r} group index {group_index}: identity.spectral_group.twice_T is null "
            "(unresolved flavor label) -- per D018, exact inter-S matching is impossible for this group; "
            "no SpectralGroupMatchKey is built and no matching.py outcome is produced for it"
        )
    _require_flavor_casimir_matches_twice_t(flavor_casimir_record, spectral_group_identity.twice_T, case.case_id, group_index)

    match_key = SpectralGroupMatchKey(
        geometry=case.geometry,
        hamiltonian_identity_without_spin=_case_hamiltonian_identity_tuple(case),
        sector_identity=case.sector_id,
        status=spectral_group_identity.status,
        multiplicity=spectral_group_identity.multiplicity,
        twice_T=spectral_group_identity.twice_T,
        translation_label=_symmetry_label_from_payload(translation_record["payload"]),
        reflection_label=_symmetry_label_from_payload(reflection_record["payload"]),
    )

    return IndexedSpectralGroup(
        case_id=case.case_id,
        case=case,
        spectral_group_identity=spectral_group_identity,
        spectral_window_group_index=group_index,
        match_key=match_key,
        documents=documents,
    )


def _index_case(loaded_case: LoadedCase) -> tuple[IndexedSpectralGroup, ...]:
    case = loaded_case.case
    expected_hamiltonian = _case_hamiltonian_identity_tuple(case)

    documents_by_index: dict[int, list[FrozenDocument]] = {}
    for document in loaded_case.documents:
        _require_document_matches_case(document, case, expected_hamiltonian)
        group_index = document["identity"]["spectral_group"]["spectral_window_group_index"]
        documents_by_index.setdefault(group_index, []).append(document)

    return tuple(
        _build_indexed_group(case, group_index, tuple(documents_by_index[group_index]))
        for group_index in sorted(documents_by_index)
    )


def build_campaign_artifact_index(
    manifest: Manifest, campaign_output_dir: Path, *, repository_commit: str
) -> CampaignArtifactIndex:
    """load_validated_cases(...) once, then index every loaded case's
    documents into IndexedSpectralGroup objects -- case order preserved
    from the plan, groups sorted by spectral_window_group_index within
    each case. Performs no inter-S comparison whatsoever."""
    loaded_cases = load_validated_cases(manifest, campaign_output_dir, repository_commit=repository_commit)

    groups: list[IndexedSpectralGroup] = []
    for loaded_case in loaded_cases:
        groups.extend(_index_case(loaded_case))

    return CampaignArtifactIndex(
        manifest_fingerprint=manifest.fingerprint,
        campaign_id=manifest.campaign_id,
        repository_commit=repository_commit,
        cases=loaded_cases,
        groups=tuple(groups),
    )
