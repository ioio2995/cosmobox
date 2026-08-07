"""Cross-S spectral group matching over an already-built, immutable
CampaignArtifactIndex (1B-9b, docs/governance/current-task.md). Level1B
lot 1B-9c.

build_inter_s_matching_report answers exactly one question: which
S_high spectral groups correspond exactly to which S_low spectral
groups? It reuses cosmobox.level1.matching.match_spectral_group,
unmodified, as the sole source of matching logic -- this module never
recodes any scientific comparison, never filters candidates by its own
rules before calling it, and never computes gamma_O, a robustness
verdict, or any other inter-S observable. Only the correspondence
itself is produced here.

Couple construction: two CampaignCaseSpec objects form an admissible
(high, low) couple only if they share the same geometry, the same
hamiltonian_identity_without_spin (indexing._case_hamiltonian_identity_
tuple -- the exact same helper build_campaign_artifact_index already
uses to build every group's own SpectralGroupMatchKey, reused here
rather than duplicated, so the two notions of "same Hamiltonian
identity" can never drift apart), and the same sector_id -- then the
two largest spin values among cases sharing that identity are taken as
(S_high, S_low). A physical identity with fewer than two available
spins produces no couple; this is not an error. In the current campaign
this naturally and correctly separates every "reference" triple
(S1/S2/S3) from its "j_break" counterpart (a single point at S2, alone
under its own, distinct hamiltonian_identity_without_spin, since
j_break changes a J value) without any name-based (case_id/
hamiltonian_case_id string) filtering.

structurally_applicable is passed as True for every couple this module
ever constructs: the pairing above is only ever formed between two
cases proven to share geometry, hamiltonian_identity_without_spin, and
sector_id, so the structural comparability match_spectral_group's
structurally_applicable parameter guards against is already established
by construction, not by an independent heuristic. No other value of
this parameter is produced by this module.

low_window_truncated is reconstructed once per low case, directly from
that case's own CampaignCaseSpec: (case.spectral_window <
case.physical_dimension). This is rigorously equivalent to the accepted
Level0 contract (cosmobox.level0.degeneracy.DegeneracyReport.
window_truncated = (n < dimension), where dimension is the case's
physical_dimension) because reports.py's dense/sparse spectrum paths
always request exactly k = min(options.n_eigenvalues, dimension)
eigenvalues with n_eigenvalues == case.spectral_window (experiments.
level1.planning.build_campaign_plan), so n < dimension holds if and
only if spectral_window < physical_dimension. No new field is added to
any artifact; ResultRecord v2 and serialization.py are untouched.

MatchOutcome.matched_group only carries a SpectralGroupMatchKey, not a
concrete IndexedSpectralGroup -- for an exact_label_match this module
resolves the one concrete low-side IndexedSpectralGroup whose own
match_key equals outcome.matched_group by ordinary dataclass equality.
Exactly one such group must exist; zero or more than one is a
structural inconsistency of the analysis pipeline itself (never a
matching.py concern) and raises InterSMatchingError. This resolution
never uses energy, spectral_window_group_index, disk order, or
proximity -- match_key equality is the only criterion, matching
matching.py's own already-accepted rule that identity belongs to the
group, never to energy rank (D022).

This module never calls evaluate_robustness, compute_gamma_o,
run_single_case, run_campaign, or launch_normative_campaign; it performs
no diagonalization and reconstructs no eigenvectors. It never uses or
reconstructs target_id anywhere in its API -- the scientific unit
remains IndexedSpectralGroup + SpectralGroupMatchKey, per 1B-9a/1B-9b.
"""

from __future__ import annotations

from dataclasses import dataclass

from cosmobox.level1.matching import EXACT_LABEL_MATCH, MatchOutcome, match_spectral_group
from experiments.level1.planning import CampaignCaseSpec

from .indexing import CampaignArtifactIndex, IndexedSpectralGroup, _case_hamiltonian_identity_tuple
from .loader import LoadedCase


class InterSMatchingError(RuntimeError):
    """Raised for a structural inconsistency discovered while resolving
    MatchOutcome.matched_group back to a concrete low-side
    IndexedSpectralGroup -- never for a matching.py outcome itself,
    which is always accepted as-is."""


@dataclass(frozen=True, slots=True)
class InterSGroupMatch:
    """One S_high spectral group compared against every S_low candidate
    of the same (high_case_id, low_case_id) couple, via a single
    match_spectral_group call. low_group is the concrete resolved group
    for an exact_label_match, and None for every other MatchOutcome
    status -- the match_key itself is never duplicated here since
    high_group/low_group already carry it."""

    high_case_id: str
    low_case_id: str
    high_spin: int
    low_spin: int
    high_group: IndexedSpectralGroup
    low_group: IndexedSpectralGroup | None
    outcome: MatchOutcome

    def __post_init__(self) -> None:
        if self.high_spin <= self.low_spin:
            raise ValueError(f"high_spin ({self.high_spin}) must be > low_spin ({self.low_spin})")
        if self.high_group.case_id != self.high_case_id:
            raise ValueError(f"high_group.case_id ({self.high_group.case_id!r}) != high_case_id ({self.high_case_id!r})")
        if (self.outcome.status == EXACT_LABEL_MATCH) != (self.low_group is not None):
            raise ValueError("low_group must be set if and only if outcome.status == 'exact_label_match'")
        if self.low_group is not None:
            if self.low_group.case_id != self.low_case_id:
                raise ValueError(f"low_group.case_id ({self.low_group.case_id!r}) != low_case_id ({self.low_case_id!r})")
            if self.low_group.match_key != self.outcome.matched_group:
                raise ValueError("low_group.match_key does not match outcome.matched_group")


@dataclass(frozen=True, slots=True)
class InterSMatchingReport:
    """The full, immutable inter-S matching result of one campaign
    artifact index. Provenance is that of the SOURCE campaign
    (campaign_id/manifest_fingerprint/repository_commit, copied
    unchanged from the CampaignArtifactIndex that produced `matches`) --
    never the commit the analysis code itself happens to run at.
    matches is ordered by couple (plan/index order), then by
    spectral_window_group_index within each couple's high case -- never
    filesystem order."""

    campaign_id: str
    manifest_fingerprint: str
    repository_commit: str
    matches: tuple[InterSGroupMatch, ...]

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not self.repository_commit:
            raise ValueError("repository_commit must be non-empty")


def _low_window_truncated(case: CampaignCaseSpec) -> bool:
    return case.spectral_window < case.physical_dimension


def _build_case_pairs(index: CampaignArtifactIndex) -> tuple[tuple[LoadedCase, LoadedCase], ...]:
    """Groups index.cases (already in build_campaign_plan order) by
    (geometry, hamiltonian_identity_without_spin, sector_id), preserving
    first-appearance order of each key -- so the returned pairs are
    already in deterministic, plan-derived order. Within a key sharing
    at least two cases, only the two largest spins are paired; fewer
    than two cases under a key produces no pair for it, never an error.
    """
    grouped: dict[tuple, list[LoadedCase]] = {}
    for loaded_case in index.cases:
        case = loaded_case.case
        key = (case.geometry, _case_hamiltonian_identity_tuple(case), case.sector_id)
        grouped.setdefault(key, []).append(loaded_case)

    pairs: list[tuple[LoadedCase, LoadedCase]] = []
    for cases in grouped.values():
        if len(cases) < 2:
            continue
        ordered = sorted(cases, key=lambda loaded_case: loaded_case.case.spin, reverse=True)
        pairs.append((ordered[0], ordered[1]))
    return tuple(pairs)


def _resolve_low_group(
    outcome: MatchOutcome,
    low_groups: tuple[IndexedSpectralGroup, ...],
    *,
    high_case_id: str,
    high_group_index: int,
) -> IndexedSpectralGroup | None:
    if outcome.status != EXACT_LABEL_MATCH:
        return None
    concrete = [group for group in low_groups if group.match_key == outcome.matched_group]
    if len(concrete) != 1:
        raise InterSMatchingError(
            f"high case {high_case_id!r} group index {high_group_index}: expected exactly 1 concrete low "
            f"IndexedSpectralGroup with match_key == outcome.matched_group, found {len(concrete)}"
        )
    return concrete[0]


def build_inter_s_matching_report(index: CampaignArtifactIndex) -> InterSMatchingReport:
    """Builds every admissible (S_high, S_low) couple from index.cases,
    then for every S_high group calls match_spectral_group(target=
    high_group.match_key, candidates=[low group match_keys],
    structurally_applicable=True, low_window_truncated=...) exactly
    once, unfiltered -- match_spectral_group remains the sole source of
    truth for the outcome. Performs no diagonalization, no eigenvector
    reconstruction, and no write of any kind.
    """
    groups_by_case_id: dict[str, list[IndexedSpectralGroup]] = {}
    for group in index.groups:
        groups_by_case_id.setdefault(group.case_id, []).append(group)

    matches: list[InterSGroupMatch] = []
    for high_loaded, low_loaded in _build_case_pairs(index):
        high_case = high_loaded.case
        low_case = low_loaded.case
        low_groups = tuple(groups_by_case_id.get(low_case.case_id, ()))
        low_candidates = tuple(group.match_key for group in low_groups)
        low_truncated = _low_window_truncated(low_case)

        for high_group in groups_by_case_id.get(high_case.case_id, ()):
            outcome = match_spectral_group(
                high_group.match_key,
                low_candidates,
                structurally_applicable=True,
                low_window_truncated=low_truncated,
            )
            low_group = _resolve_low_group(
                outcome, low_groups, high_case_id=high_case.case_id, high_group_index=high_group.spectral_window_group_index
            )
            matches.append(
                InterSGroupMatch(
                    high_case_id=high_case.case_id,
                    low_case_id=low_case.case_id,
                    high_spin=high_case.spin,
                    low_spin=low_case.spin,
                    high_group=high_group,
                    low_group=low_group,
                    outcome=outcome,
                )
            )

    return InterSMatchingReport(
        campaign_id=index.campaign_id,
        manifest_fingerprint=index.manifest_fingerprint,
        repository_commit=index.repository_commit,
        matches=tuple(matches),
    )
