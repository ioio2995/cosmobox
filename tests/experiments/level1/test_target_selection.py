from __future__ import annotations

import numpy as np
import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level0.symmetries import build_flavor_casimir
from cosmobox.level1.restricted import COMPLETE_MULTIPLET, PARTIAL_SUBSPACE, SpectralGroupState, extract_group_state

from experiments.level1 import manifest as m
from experiments.level1 import target_selection as ts

DEGENERACY_TOLERANCE = 1e-10


def _target(selection_kind: str, **overrides) -> m.TargetGroupSpec:
    defaults = dict(
        target_id="t",
        selection_kind=selection_kind,
        target_twice_T=None,
        selection_within_label=None,
        required_spectral_status="complete_multiplet" if selection_kind != "structurally_not_applicable" else None,
        requires_inter_s_exact_match=selection_kind == "first_excited",
    )
    if selection_kind == "flavor_label":
        defaults.update(target_twice_T=1, selection_within_label="lowest_representative_energy")
    defaults.update(overrides)
    return m.TargetGroupSpec(**defaults)


def _triangle_s1() -> tuple:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, 2, 1)
    key_index = build_key_index(report.keys)
    params = HamiltonianParameters(
        J=tuple(1.0 for _ in lattice.nodes),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in lattice.nodes),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, 2, 1, report, terms, params, spectrum_options=SpectrumOptions(n_eigenvalues=16)
    )
    groups = level0_report.spectrum.degeneracy.groups
    group_states = [extract_group_state(eigenvectors, group) for group in groups]
    flavor_casimir = build_flavor_casimir(lattice, 2, 1, report.keys, key_index)
    return lattice, report, key_index, groups, group_states, flavor_casimir


# ---------------------------------------------------------------------------
# fundamental / first_excited / structurally_not_applicable
# ---------------------------------------------------------------------------


def test_select_fundamental_picks_rank_zero_and_reports_status() -> None:
    _lattice, _report, _key_index, groups, group_states, _casimir = _triangle_s1()
    outcome = ts.select_target_group(_target("fundamental"), groups, group_states, degeneracy_tolerance=DEGENERACY_TOLERANCE)
    assert outcome.status == ts.SELECTED
    assert outcome.group_index == 0
    assert outcome.selected_group_status == COMPLETE_MULTIPLET
    assert outcome.meets_normative_requirements is True


def test_select_first_excited_not_in_window_when_only_one_group() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, 2, 1)
    key_index = build_key_index(report.keys)
    params = HamiltonianParameters(
        J=tuple(1.0 for _ in lattice.nodes),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in lattice.nodes),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )
    terms = build_hamiltonian_terms(lattice, 2, 1, report.keys, key_index, params)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, 2, 1, report, terms, params, spectrum_options=SpectrumOptions(n_eigenvalues=2)
    )
    groups = level0_report.spectrum.degeneracy.groups
    group_states = [extract_group_state(eigenvectors, group) for group in groups]
    assert len(groups) == 1  # window ends mid-multiplet

    outcome = ts.select_target_group(
        _target("first_excited"), groups, group_states, degeneracy_tolerance=DEGENERACY_TOLERANCE
    )
    assert outcome.status == ts.NOT_IN_WINDOW
    assert outcome.group_index is None
    assert outcome.selected_group_status is None
    assert outcome.meets_normative_requirements is None


def test_select_structurally_not_applicable_selects_nothing() -> None:
    _lattice, _report, _key_index, groups, group_states, _casimir = _triangle_s1()
    outcome = ts.select_target_group(
        _target("structurally_not_applicable"), groups, group_states, degeneracy_tolerance=DEGENERACY_TOLERANCE
    )
    assert outcome.status == ts.STRUCTURALLY_NOT_APPLICABLE
    assert outcome.group_index is None


# ---------------------------------------------------------------------------
# flavor_label
# ---------------------------------------------------------------------------


def test_select_flavor_label_finds_the_maximal_t_max_group_on_triangle_s1() -> None:
    _lattice, _report, _key_index, groups, group_states, casimir = _triangle_s1()
    target = _target("flavor_label", target_twice_T=3)  # T=3/2, triangle's T_max at S=1
    outcome = ts.select_target_group(
        target, groups, group_states, flavor_casimir=casimir, degeneracy_tolerance=DEGENERACY_TOLERANCE
    )
    assert outcome.status == ts.SELECTED
    assert outcome.twice_T == 3


def test_select_flavor_label_not_in_window_when_no_candidate_matches() -> None:
    _lattice, _report, _key_index, groups, group_states, casimir = _triangle_s1()
    target = _target("flavor_label", target_twice_T=99)  # no group has this label
    outcome = ts.select_target_group(
        target, groups, group_states, flavor_casimir=casimir, degeneracy_tolerance=DEGENERACY_TOLERANCE
    )
    assert outcome.status == ts.NOT_IN_WINDOW


def test_select_flavor_label_requires_flavor_casimir() -> None:
    _lattice, _report, _key_index, groups, group_states, _casimir = _triangle_s1()
    with pytest.raises(ValueError, match="flavor_casimir"):
        ts.select_target_group(
            _target("flavor_label", target_twice_T=3), groups, group_states, degeneracy_tolerance=DEGENERACY_TOLERANCE
        )


# ---------------------------------------------------------------------------
# Synthetic group_states with hand-controlled statuses, to exercise the
# pooling rule without depending on which real triangle groups happen to
# be complete/partial. Uses a fixed flavor_casimir designed so every group
# in `group_states` has EXACTLY the same computed twice_T (a diagonal
# operator with a single eigenvalue matching T(T+1) for twice_T=2, i.e.
# T=1, casimir eigenvalue 2.0), so the ONLY thing distinguishing
# candidates is representative_energy and complete/partial status.
# ---------------------------------------------------------------------------


def _uniform_casimir_group_state(dim: int, status: str, seed: int):
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))
    q, _ = np.linalg.qr(raw)
    return SpectralGroupState(psi=q[:, : max(1, dim // 2)], status=status)


class _FakeGroup:
    def __init__(self, representative_energy: float) -> None:
        self.representative_energy = representative_energy


def test_flavor_label_never_skips_a_lower_partial_for_a_higher_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact scenario the corrective mission requires: a lower-energy
    partial candidate and a higher-energy complete candidate share the
    same target_twice_T -- the lower partial candidate must be selected,
    with its status reported as partial_subspace (never promoted)."""
    target = _target("flavor_label", target_twice_T=2)

    group_states = [
        _uniform_casimir_group_state(6, PARTIAL_SUBSPACE, seed=1),  # lower energy, index 0
        _uniform_casimir_group_state(6, COMPLETE_MULTIPLET, seed=2),  # higher energy, index 1
    ]
    groups = [_FakeGroup(representative_energy=-5.0), _FakeGroup(representative_energy=-1.0)]

    monkeypatch.setattr(ts, "_group_twice_T", lambda casimir, group_state, *, flavor_label_tolerance: 2)

    outcome = ts.select_target_group(
        target, groups, group_states, flavor_casimir="unused", degeneracy_tolerance=DEGENERACY_TOLERANCE
    )
    assert outcome.status == ts.SELECTED
    assert outcome.group_index == 0
    assert outcome.selected_group_status == PARTIAL_SUBSPACE
    assert outcome.meets_normative_requirements is False  # complete_multiplet was required, partial was selected


def test_flavor_label_tie_between_complete_and_partial_is_ambiguous(monkeypatch: pytest.MonkeyPatch) -> None:
    target = _target("flavor_label", target_twice_T=2)

    group_states = [
        _uniform_casimir_group_state(6, PARTIAL_SUBSPACE, seed=3),
        _uniform_casimir_group_state(6, COMPLETE_MULTIPLET, seed=4),
    ]
    tied_energy = -3.0
    groups = [_FakeGroup(representative_energy=tied_energy), _FakeGroup(representative_energy=tied_energy)]

    monkeypatch.setattr(ts, "_group_twice_T", lambda casimir, group_state, *, flavor_label_tolerance: 2)

    outcome = ts.select_target_group(
        target, groups, group_states, flavor_casimir="unused", degeneracy_tolerance=DEGENERACY_TOLERANCE
    )
    assert outcome.status == ts.AMBIGUOUS
    assert outcome.group_index is None
