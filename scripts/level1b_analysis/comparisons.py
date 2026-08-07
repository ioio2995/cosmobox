"""Inter-S observable extraction and comparison over an already-built
InterSMatchingReport (1B-9c, docs/governance/current-task.md). Level1B
lot 1B-9d.

build_inter_s_observable_comparison_report answers "which high/low
values are actually comparable for each already-matched spectral group,
and what is gamma_O for O_ij_raw?" -- for exactly the closed observable
list this lot covers: O_ij_raw, rho_QQ, C_TT_conn,
flavor_singular_value_ratio. It never calls evaluate_robustness, never
produces a robust/non_robust/indeterminate verdict, and never recodes
any threshold logic (max(0.05, 0.15 * amplitude)) -- that belongs
entirely to the next lot, which decides how to apply
cosmobox.level1.robustness.evaluate_robustness to the comparisons built
here. gamma_O itself is computed exclusively via the existing
cosmobox.level1.robustness.compute_gamma_o, unmodified, never
reimplemented (|high - low| / max(|high|, |low|) is never recoded here).

Native record_kind disambiguation: an observable_kind alone is NOT a
unique key into a spectral group's documents. In the real campaign,
observable_kind == "O_ij_raw" is legitimately produced under THREE
different record_kinds sharing the exact same identity.path/
flavor_component/normalization: "raw_observable" (a bare per-path
complex reading -- what this lot compares), "orbit_statistic" (an
orbit-averaged OrbitResultPayload), and "restricted_diagnostic" (a
NonHermitianRestrictedDiagnostics). This module therefore always pins
BOTH observable_kind AND record_kind before selecting candidate
documents, deriving the one native record_kind of each of this lot's 4
target observable_kinds from cosmobox.level1.results' own closed
RAW_OBSERVABLE_KINDS/NORMALIZED_OBSERVABLE_KINDS/FLAVOR_DIAGNOSTIC_KINDS
tables (never a private, independently-maintained table): O_ij_raw and
C_TT_conn -> "raw_observable" (payload a bare complex/float,
respectively); rho_QQ -> "normalized_observable"; flavor_singular_value_
ratio -> "flavor_diagnostic" (both the latter two carrying a
NormalizedMoment-shaped {"value": ..., "null_reason": ...} payload).
C_TT_conn's payload is a bare, always-present, never-null float --
unlike rho_QQ/flavor_singular_value_ratio, it structurally has no
null_reason concept at all in this campaign's already-accepted schema
(results.py's own _expected_payload_types: raw_observable payloads are
always exactly `float`, non-optional).

Comparability axes (1B-9a, frozen): two documents (one high, one low,
already restricted to the same already-matched spectral group pair and
the same observable_kind/native record_kind) are comparable if and only
if identity.path, identity.flavor_component, and identity.normalization
are ALL exactly equal -- path compared as the complete, ordered tuple
serialized on disk, never reduced to (path[0], path[-1]) or a bare
(i, j): flavor_singular_value_ratio in particular is path-dependent, so
two documents sharing only the same endpoints but a different internal
path are NOT comparable. spectral_window_group_index, representative_
energy, target_id, and spin are never part of this key -- the group
pairing itself (InterSGroupMatch) already fixes those.

Cardinality: for each already-matched (high_group, low_group) and each
of the 4 target observable_kinds, the low side is indexed once by its
own comparability key; a genuine duplicate low key (two low documents
sharing path/flavor_component/normalization within the same group and
observable_kind) raises InterSObservableComparisonError immediately,
never resolved by picking the first one. Every eligible high document is
then required to find EXACTLY one low counterpart; a high document with
no matching low key also raises InterSObservableComparisonError -- this
first normative lot treats the corpus as fully analyzable, so an
unpaired high value is a structural problem to report loudly, never a
silently-dropped comparison. A low document with no high counterpart is
not an error: it is simply never visited (this module only ever walks
high_group.documents to decide what to compare).

Only exact_label_match couples are ever compared: for any other
MatchOutcome status (InterSGroupMatch.low_group is already None per
1B-9c's own invariant), no comparison is attempted and no value is
fabricated -- those matches are silently excluded from `comparisons`,
never turned into a placeholder or a verdict. In the current campaign
all 7 matches are exact_label_match.

Null handling: value is None if and only if null_reason is set, exactly
mirroring NormalizedMoment's own invariant, tracked independently for
the high and low side. A null value is never replaced by 0 or by the
normalization floor -- both sides are always reported as they were
actually serialized, structurally comparable or not.

This module performs no diagonalization, no scientific computation
beyond the single permitted compute_gamma_o(O_high, O_low) call for
O_ij_raw, and writes nothing to disk. matching.py/robustness.py/
results.py/serialization.py are only ever imported for their already-
accepted public names, never modified.
"""

from __future__ import annotations

from dataclasses import dataclass

from cosmobox.level1.local_observables import NormalizedMoment
from cosmobox.level1.matching import EXACT_LABEL_MATCH
from cosmobox.level1.results import FLAVOR_DIAGNOSTIC_KINDS, NORMALIZED_OBSERVABLE_KINDS, RAW_OBSERVABLE_KINDS
from cosmobox.level1.robustness import compute_gamma_o

from .indexing import IndexedSpectralGroup
from .inter_s import InterSGroupMatch, InterSMatchingReport
from .loader import FrozenDocument

GAMMA_O_OBSERVABLE_KIND = "O_ij_raw"
SCALAR_OBSERVABLE_KINDS = ("rho_QQ", "C_TT_conn", "flavor_singular_value_ratio")
TARGET_OBSERVABLE_KINDS = (GAMMA_O_OBSERVABLE_KIND,) + SCALAR_OBSERVABLE_KINDS
"""The closed list of observable_kinds this lot compares. Deliberately
excludes G_occ, path_phase_coherence, flavor_singlet, raw_G,
flavor_singular_values, symmetry labels, and orbit statistics -- none of
those are in scope for 1B-9d."""


class InterSObservableComparisonError(RuntimeError):
    """Raised for a structural inconsistency discovered while pairing an
    already-matched high/low spectral group's documents -- a duplicate
    low comparability key, or a high document with no exactly-one low
    counterpart. Never raised for a genuinely null value on either side
    (that is expected, ordinary data, not an error)."""


def _native_record_kind(observable_kind: str) -> str:
    """The one record_kind each of this lot's 4 target observable_kinds
    is natively produced under, derived from results.py's own closed
    tables -- see the module docstring for why O_ij_raw specifically
    needs this disambiguation against orbit_statistic/restricted_
    diagnostic records sharing the same observable_kind name."""
    if observable_kind in RAW_OBSERVABLE_KINDS:
        return "raw_observable"
    if observable_kind in NORMALIZED_OBSERVABLE_KINDS:
        return "normalized_observable"
    if observable_kind in FLAVOR_DIAGNOSTIC_KINDS:
        return "flavor_diagnostic"
    raise InterSObservableComparisonError(f"observable_kind {observable_kind!r} has no known native record_kind")


def _comparability_key(document: FrozenDocument) -> tuple:
    identity = document["identity"]
    return (identity["path"], identity["flavor_component"], identity["normalization"])


def _candidate_documents(group: IndexedSpectralGroup, observable_kind: str, record_kind: str) -> list[FrozenDocument]:
    return [
        document
        for document in group.documents
        if document["observable_kind"] == observable_kind and document["record_kind"] == record_kind
    ]


def _index_low_documents(
    low_group: IndexedSpectralGroup, observable_kind: str, record_kind: str, *, high_case_id: str, low_case_id: str
) -> dict[tuple, FrozenDocument]:
    index: dict[tuple, FrozenDocument] = {}
    for document in _candidate_documents(low_group, observable_kind, record_kind):
        key = _comparability_key(document)
        if key in index:
            raise InterSObservableComparisonError(
                f"low case {low_case_id!r} group index {low_group.spectral_window_group_index}: duplicate low "
                f"document for observable_kind={observable_kind!r} at comparability key (path, flavor_component, "
                f"normalization)={key!r} (comparing against high case {high_case_id!r})"
            )
        index[key] = document
    return index


def _reconstruct_complex(payload: FrozenDocument) -> complex:
    return complex(payload["real"], payload["imag"])


def _reconstruct_scalar(observable_kind: str, payload: object) -> tuple[float | None, str | None]:
    """C_TT_conn's payload is a bare, always-present float (no null_reason
    concept exists for it in this campaign's schema) -- rho_QQ and
    flavor_singular_value_ratio are NormalizedMoment-shaped
    {"value": ..., "null_reason": ...} mappings."""
    if observable_kind == "C_TT_conn":
        return float(payload), None
    return payload["value"], payload["null_reason"]


@dataclass(frozen=True, slots=True)
class GammaOComparison:
    """One O_ij_raw high/low pair and the gamma_O computed for it via
    cosmobox.level1.robustness.compute_gamma_o, unmodified. high_value/
    low_value are always present (O_ij_raw's raw_observable payload is
    never null); gamma_o is always a real NormalizedMoment instance --
    never Python None here -- though its OWN value may be None with
    null_reason="normalization_denominator_below_floor" when compute_
    gamma_o's amplitude floor is not cleared."""

    high_case_id: str
    low_case_id: str
    high_group: IndexedSpectralGroup
    low_group: IndexedSpectralGroup
    path: tuple[int, ...] | None
    flavor_component: str | None
    normalization: str | None
    high_value: complex
    low_value: complex
    gamma_o: NormalizedMoment

    def __post_init__(self) -> None:
        if not isinstance(self.high_group, IndexedSpectralGroup):
            raise ValueError(f"high_group must be an IndexedSpectralGroup, got {type(self.high_group)}")
        if not isinstance(self.low_group, IndexedSpectralGroup):
            raise ValueError(f"low_group must be an IndexedSpectralGroup, got {type(self.low_group)}")
        if self.high_group.case_id != self.high_case_id:
            raise ValueError(f"high_group.case_id ({self.high_group.case_id!r}) != high_case_id ({self.high_case_id!r})")
        if self.low_group.case_id != self.low_case_id:
            raise ValueError(f"low_group.case_id ({self.low_group.case_id!r}) != low_case_id ({self.low_case_id!r})")
        if self.path is not None and not isinstance(self.path, tuple):
            raise ValueError(f"path must be a tuple or None, got {type(self.path)}")
        if type(self.high_value) is not complex:
            raise ValueError(f"high_value must be exactly complex, got {type(self.high_value)}")
        if type(self.low_value) is not complex:
            raise ValueError(f"low_value must be exactly complex, got {type(self.low_value)}")
        if not isinstance(self.gamma_o, NormalizedMoment):
            raise ValueError(f"gamma_o must be a NormalizedMoment, got {type(self.gamma_o)}")


@dataclass(frozen=True, slots=True)
class ScalarObservableComparison:
    """One rho_QQ/C_TT_conn/flavor_singular_value_ratio high/low pair --
    no gamma_o field at all: the type itself makes "gamma_o computed for
    a scalar observable in this lot" unrepresentable, rather than relying
    on a runtime None check. value is None if and only if the
    corresponding null_reason is set, independently for each side; a
    null value is carried exactly as serialized, never replaced by 0 or
    an epsilon."""

    high_case_id: str
    low_case_id: str
    high_group: IndexedSpectralGroup
    low_group: IndexedSpectralGroup
    observable_kind: str
    path: tuple[int, ...] | None
    flavor_component: str | None
    normalization: str | None
    high_value: float | None
    low_value: float | None
    high_null_reason: str | None
    low_null_reason: str | None

    def __post_init__(self) -> None:
        if self.observable_kind not in SCALAR_OBSERVABLE_KINDS:
            raise ValueError(f"observable_kind must be one of {SCALAR_OBSERVABLE_KINDS}, got {self.observable_kind!r}")
        if not isinstance(self.high_group, IndexedSpectralGroup):
            raise ValueError(f"high_group must be an IndexedSpectralGroup, got {type(self.high_group)}")
        if not isinstance(self.low_group, IndexedSpectralGroup):
            raise ValueError(f"low_group must be an IndexedSpectralGroup, got {type(self.low_group)}")
        if self.high_group.case_id != self.high_case_id:
            raise ValueError(f"high_group.case_id ({self.high_group.case_id!r}) != high_case_id ({self.high_case_id!r})")
        if self.low_group.case_id != self.low_case_id:
            raise ValueError(f"low_group.case_id ({self.low_group.case_id!r}) != low_case_id ({self.low_case_id!r})")
        if self.path is not None and not isinstance(self.path, tuple):
            raise ValueError(f"path must be a tuple or None, got {type(self.path)}")
        if (self.high_value is None) != (self.high_null_reason is not None):
            raise ValueError("high_value is None if and only if high_null_reason is set")
        if (self.low_value is None) != (self.low_null_reason is not None):
            raise ValueError("low_value is None if and only if low_null_reason is set")


@dataclass(frozen=True, slots=True)
class InterSObservableComparisonReport:
    """Provenance is that of the SOURCE campaign (campaign_id/
    manifest_fingerprint/repository_commit, copied unchanged from the
    InterSMatchingReport that produced `comparisons`) -- never the
    analysis code's own commit. comparisons preserves InterSMatchingReport
    .matches' own order, then -- within each matched couple -- the exact
    canonical order of high_group.documents (assembly.py's own sort
    order, never filesystem or numeric-value order); GammaOComparison and
    ScalarObservableComparison entries are interleaved exactly as their
    source high documents were ordered, never grouped by kind."""

    campaign_id: str
    manifest_fingerprint: str
    repository_commit: str
    comparisons: tuple[GammaOComparison | ScalarObservableComparison, ...]

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.manifest_fingerprint:
            raise ValueError("manifest_fingerprint must be non-empty")
        if not self.repository_commit:
            raise ValueError("repository_commit must be non-empty")


def _build_comparison(
    match: InterSGroupMatch, observable_kind: str, key: tuple, high_document: FrozenDocument, low_document: FrozenDocument
) -> GammaOComparison | ScalarObservableComparison:
    path, flavor_component, normalization = key
    if observable_kind == GAMMA_O_OBSERVABLE_KIND:
        high_value = _reconstruct_complex(high_document["payload"])
        low_value = _reconstruct_complex(low_document["payload"])
        return GammaOComparison(
            high_case_id=match.high_case_id,
            low_case_id=match.low_case_id,
            high_group=match.high_group,
            low_group=match.low_group,
            path=path,
            flavor_component=flavor_component,
            normalization=normalization,
            high_value=high_value,
            low_value=low_value,
            gamma_o=compute_gamma_o(high_value, low_value),
        )
    high_value, high_null_reason = _reconstruct_scalar(observable_kind, high_document["payload"])
    low_value, low_null_reason = _reconstruct_scalar(observable_kind, low_document["payload"])
    return ScalarObservableComparison(
        high_case_id=match.high_case_id,
        low_case_id=match.low_case_id,
        high_group=match.high_group,
        low_group=match.low_group,
        observable_kind=observable_kind,
        path=path,
        flavor_component=flavor_component,
        normalization=normalization,
        high_value=high_value,
        low_value=low_value,
        high_null_reason=high_null_reason,
        low_null_reason=low_null_reason,
    )


def _build_comparisons_for_match(match: InterSGroupMatch) -> list[GammaOComparison | ScalarObservableComparison]:
    low_indices = {
        observable_kind: _index_low_documents(
            match.low_group,
            observable_kind,
            _native_record_kind(observable_kind),
            high_case_id=match.high_case_id,
            low_case_id=match.low_case_id,
        )
        for observable_kind in TARGET_OBSERVABLE_KINDS
    }

    comparisons: list[GammaOComparison | ScalarObservableComparison] = []
    for high_document in match.high_group.documents:
        observable_kind = high_document["observable_kind"]
        if observable_kind not in TARGET_OBSERVABLE_KINDS:
            continue
        if high_document["record_kind"] != _native_record_kind(observable_kind):
            continue  # e.g. an O_ij_raw orbit_statistic/restricted_diagnostic record -- out of scope here
        key = _comparability_key(high_document)
        low_document = low_indices[observable_kind].get(key)
        if low_document is None:
            raise InterSObservableComparisonError(
                f"high case {match.high_case_id!r} group index {match.high_group.spectral_window_group_index}: no "
                f"low document for observable_kind={observable_kind!r} at comparability key (path, "
                f"flavor_component, normalization)={key!r} in low case {match.low_case_id!r} group index "
                f"{match.low_group.spectral_window_group_index}"
            )
        comparisons.append(_build_comparison(match, observable_kind, key, high_document, low_document))
    return comparisons


def build_inter_s_observable_comparison_report(matching_report: InterSMatchingReport) -> InterSObservableComparisonReport:
    """Walks matching_report.matches in order; a match whose outcome is
    not exact_label_match contributes no comparison at all (never a
    fabricated value, never a verdict). No evaluate_robustness call, no
    diagonalization, no write."""
    comparisons: list[GammaOComparison | ScalarObservableComparison] = []
    for match in matching_report.matches:
        if match.outcome.status != EXACT_LABEL_MATCH:
            continue
        comparisons.extend(_build_comparisons_for_match(match))

    return InterSObservableComparisonReport(
        campaign_id=matching_report.campaign_id,
        manifest_fingerprint=matching_report.manifest_fingerprint,
        repository_commit=matching_report.repository_commit,
        comparisons=tuple(comparisons),
    )
