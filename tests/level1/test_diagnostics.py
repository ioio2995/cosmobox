from __future__ import annotations

import ast
import dataclasses
import inspect
import math

import numpy as np
import pytest
import scipy.sparse as sp

from cosmobox.level0.basis import build_basis
from cosmobox.level0.hamiltonian import build_hamiltonian_terms, build_key_index
from cosmobox.level0.lattice import build_lattice
from cosmobox.level0.params import HamiltonianParameters
from cosmobox.level0.reports import SpectrumOptions, build_level0_report_with_eigenvectors
from cosmobox.level1 import diagnostics as diagnostics_module
from cosmobox.level1.diagnostics import (
    HermitianRestrictedDiagnostics,
    NonHermitianRestrictedDiagnostics,
    build_hermitian_restricted_diagnostics,
    build_non_hermitian_restricted_diagnostics,
)
from cosmobox.level1.restricted import (
    COMPLETE_MULTIPLET,
    HERMITICITY_TOLERANCE,
    PARTIAL_SUBSPACE,
    SpectralGroupState,
    build_restricted_operator,
    extract_group_state,
)

N_FLAVORS = 2
SPIN = 1


def _deterministic_unitary(dimension: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    q, r = np.linalg.qr(raw)
    phase = np.diag(r) / np.abs(np.diag(r))
    return q * phase


def _diagonalize(geometry: str, spin: int, n_eigenvalues: int):
    lattice = build_lattice(geometry)
    n_nodes = len(lattice.nodes)
    report = build_basis(lattice, N_FLAVORS, spin)
    key_index = build_key_index(report.keys)
    params = HamiltonianParameters(
        J=tuple(1.0 for _ in range(n_nodes)),
        h=tuple(np.zeros((2, 2), dtype=np.complex128) for _ in range(n_nodes)),
        t=1.0,
        g_E=1.0,
        K=1.0,
    )
    terms = build_hamiltonian_terms(lattice, N_FLAVORS, spin, report.keys, key_index, params)
    options = SpectrumOptions(n_eigenvalues=n_eigenvalues)
    level0_report, eigenvectors = build_level0_report_with_eigenvectors(
        lattice, N_FLAVORS, spin, report, terms, params, spectrum_options=options
    )
    return lattice, report, key_index, level0_report, eigenvectors


# ---------------------------------------------------------------------------
# Shared O_rest validation (exercised through the public builders)
# ---------------------------------------------------------------------------


def test_build_hermitian_diagnostics_rejects_1d_o_rest() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="2-D"):
        build_hermitian_restricted_diagnostics(np.zeros(4), state)


def test_build_hermitian_diagnostics_rejects_non_square_o_rest() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="square"):
        build_hermitian_restricted_diagnostics(np.zeros((2, 3)), state)


def test_build_hermitian_diagnostics_rejects_shape_mismatch_with_multiplicity() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    with pytest.raises(ValueError, match="multiplicity"):
        build_hermitian_restricted_diagnostics(np.eye(3, dtype=np.complex128), state)


def test_build_hermitian_diagnostics_rejects_non_finite_o_rest() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    o_rest = np.eye(2, dtype=np.complex128)
    o_rest[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        build_hermitian_restricted_diagnostics(o_rest, state)


# ---------------------------------------------------------------------------
# Hermitian diagnostics -- hand-verified
# ---------------------------------------------------------------------------


def test_build_hermitian_restricted_diagnostics_hand_verified() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    o_rest = np.diag([1.0, 3.0]).astype(np.complex128)
    diag = build_hermitian_restricted_diagnostics(o_rest, state)

    assert diag.status == COMPLETE_MULTIPLET
    assert diag.eigenvalues == pytest.approx((1.0, 3.0))
    assert diag.minimum == pytest.approx(1.0)
    assert diag.maximum == pytest.approx(3.0)
    assert diag.spectral_range == pytest.approx(2.0)
    assert diag.trace == pytest.approx(4.0)
    assert diag.frobenius_norm == pytest.approx(math.sqrt(1.0**2 + 3.0**2))
    assert diag.hermiticity_defect == pytest.approx(0.0, abs=1e-12)


def test_build_hermitian_restricted_diagnostics_rejects_non_hermitian_o_rest() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    o_rest = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)
    with pytest.raises(ValueError, match="not Hermitian"):
        build_hermitian_restricted_diagnostics(o_rest, state)


def test_build_hermitian_restricted_diagnostics_never_returns_eigenvectors() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    diag = build_hermitian_restricted_diagnostics(np.diag([2.0, 5.0]).astype(np.complex128), state)
    field_names = {f.name for f in dataclasses.fields(diag)}
    assert "eigenvectors" not in field_names


def test_build_hermitian_restricted_diagnostics_accepts_partial_group() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=PARTIAL_SUBSPACE)
    diag = build_hermitian_restricted_diagnostics(np.diag([1.0, 3.0]).astype(np.complex128), state)
    assert diag.status == PARTIAL_SUBSPACE


# ---------------------------------------------------------------------------
# Non-Hermitian diagnostics -- hand-verified
# ---------------------------------------------------------------------------


def test_build_non_hermitian_restricted_diagnostics_hand_verified() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    o_rest = np.array([[1.0 + 1.0j, 2.0], [0.0, 3.0 - 1.0j]], dtype=np.complex128)
    diag = build_non_hermitian_restricted_diagnostics(o_rest, state)

    assert diag.status == COMPLETE_MULTIPLET
    assert diag.trace == pytest.approx((1.0 + 1.0j) + (3.0 - 1.0j))
    reference_singular_values = np.linalg.svd(o_rest, compute_uv=False)
    assert diag.singular_values == pytest.approx(tuple(reference_singular_values))
    assert diag.singular_values[0] >= diag.singular_values[1] >= 0.0
    assert diag.frobenius_norm == pytest.approx(np.linalg.norm(o_rest, "fro"))


def test_build_non_hermitian_restricted_diagnostics_accepts_a_genuinely_hermitian_o_rest_too() -> None:
    # Nothing prevents calling the non-Hermitian builder on a Hermitian
    # matrix -- it simply reports trace/singular values/Frobenius norm
    # without any Hermiticity assumption or check.
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    o_rest = np.diag([2.0, 5.0]).astype(np.complex128)
    diag = build_non_hermitian_restricted_diagnostics(o_rest, state)
    assert diag.singular_values == pytest.approx((5.0, 2.0))


def test_build_non_hermitian_restricted_diagnostics_never_computes_eigenvalues() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=COMPLETE_MULTIPLET)
    o_rest = np.array([[0.0, 1.0], [-1.0, 0.0]], dtype=np.complex128)  # eigenvalues +-i, purely non-normal example
    diag = build_non_hermitian_restricted_diagnostics(o_rest, state)
    field_names = {f.name for f in dataclasses.fields(diag)}
    assert field_names.isdisjoint({"eigenvalues", "eigenvectors", "schur"})


def test_build_non_hermitian_restricted_diagnostics_accepts_partial_group() -> None:
    state = SpectralGroupState(psi=np.eye(2, dtype=np.complex128), status=PARTIAL_SUBSPACE)
    diag = build_non_hermitian_restricted_diagnostics(np.eye(2, dtype=np.complex128), state)
    assert diag.status == PARTIAL_SUBSPACE


# ---------------------------------------------------------------------------
# Invariance under O_rest -> V^dagger O_rest V
# ---------------------------------------------------------------------------


def test_hermitian_diagnostics_invariant_under_internal_rotation() -> None:
    dimension = 3
    rng = np.random.default_rng(7)
    raw = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    o_rest = raw + raw.conj().T  # Hermitian by construction
    state = SpectralGroupState(psi=np.eye(dimension, dtype=np.complex128), status=COMPLETE_MULTIPLET)

    rotation = _deterministic_unitary(dimension, seed=11)
    rotated_o_rest = rotation.conj().T @ o_rest @ rotation

    original = build_hermitian_restricted_diagnostics(o_rest, state)
    rotated = build_hermitian_restricted_diagnostics(rotated_o_rest, state)

    assert rotated.trace == pytest.approx(original.trace, abs=1e-8)
    assert rotated.eigenvalues == pytest.approx(original.eigenvalues, abs=1e-8)
    assert rotated.minimum == pytest.approx(original.minimum, abs=1e-8)
    assert rotated.maximum == pytest.approx(original.maximum, abs=1e-8)
    assert rotated.spectral_range == pytest.approx(original.spectral_range, abs=1e-8)
    assert rotated.frobenius_norm == pytest.approx(original.frobenius_norm, abs=1e-8)
    assert rotated.hermiticity_defect == pytest.approx(original.hermiticity_defect, abs=1e-8)


def test_non_hermitian_diagnostics_invariant_under_internal_rotation() -> None:
    dimension = 3
    rng = np.random.default_rng(13)
    o_rest = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(size=(dimension, dimension))
    state = SpectralGroupState(psi=np.eye(dimension, dtype=np.complex128), status=COMPLETE_MULTIPLET)

    rotation = _deterministic_unitary(dimension, seed=17)
    rotated_o_rest = rotation.conj().T @ o_rest @ rotation

    original = build_non_hermitian_restricted_diagnostics(o_rest, state)
    rotated = build_non_hermitian_restricted_diagnostics(rotated_o_rest, state)

    assert rotated.trace == pytest.approx(original.trace, abs=1e-8)
    assert rotated.singular_values == pytest.approx(original.singular_values, abs=1e-8)
    assert rotated.frobenius_norm == pytest.approx(original.frobenius_norm, abs=1e-8)


# ---------------------------------------------------------------------------
# Integration: real O_rest built via restricted.build_restricted_operator,
# on both a complete and a partial spectral group.
# ---------------------------------------------------------------------------


def test_hermitian_diagnostics_on_real_complete_and_partial_groups() -> None:
    lattice, report, key_index, level0_report, eigenvectors = _diagonalize("triangle", SPIN, n_eigenvalues=8)
    groups = level0_report.spectrum.degeneracy.groups
    complete_group = next(g for g in groups if not g.lower_bound_only)
    partial_group = next(g for g in groups if g.lower_bound_only)

    identity_operator = sp.identity(eigenvectors.shape[0], format="csr", dtype=np.complex128)

    complete_state = extract_group_state(eigenvectors, complete_group)
    complete_o_rest = build_restricted_operator(identity_operator, complete_state)
    complete_diag = build_hermitian_restricted_diagnostics(complete_o_rest, complete_state)
    assert complete_diag.status == COMPLETE_MULTIPLET
    assert complete_diag.trace == pytest.approx(complete_state.multiplicity, abs=1e-8)

    partial_state = extract_group_state(eigenvectors, partial_group)
    partial_o_rest = build_restricted_operator(identity_operator, partial_state)
    partial_diag = build_hermitian_restricted_diagnostics(partial_o_rest, partial_state)
    assert partial_diag.status == PARTIAL_SUBSPACE
    assert partial_diag.trace == pytest.approx(partial_state.multiplicity, abs=1e-8)


# ---------------------------------------------------------------------------
# HermitianRestrictedDiagnostics.__post_init__ -- direct construction
# ---------------------------------------------------------------------------


def _hermitian_kwargs(**overrides) -> dict:
    defaults = dict(
        status=COMPLETE_MULTIPLET,
        trace=4.0,
        eigenvalues=(1.0, 3.0),
        minimum=1.0,
        maximum=3.0,
        spectral_range=2.0,
        frobenius_norm=math.sqrt(10.0),
        hermiticity_defect=0.0,
    )
    defaults.update(overrides)
    return defaults


def test_hermitian_restricted_diagnostics_accepts_valid_construction() -> None:
    diag = HermitianRestrictedDiagnostics(**_hermitian_kwargs())
    assert diag.eigenvalues == (1.0, 3.0)


def test_hermitian_restricted_diagnostics_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(status="degenerate"))


def test_hermitian_restricted_diagnostics_rejects_non_finite_scalar() -> None:
    with pytest.raises(ValueError, match="finite"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(trace=float("nan")))


def test_hermitian_restricted_diagnostics_rejects_unsorted_eigenvalues() -> None:
    with pytest.raises(ValueError, match="sorted ascending"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(eigenvalues=(3.0, 1.0), minimum=3.0, maximum=1.0))


def test_hermitian_restricted_diagnostics_rejects_minimum_mismatch() -> None:
    with pytest.raises(ValueError, match="minimum"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(minimum=0.0))


def test_hermitian_restricted_diagnostics_rejects_maximum_mismatch() -> None:
    with pytest.raises(ValueError, match="maximum"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(maximum=99.0))


def test_hermitian_restricted_diagnostics_rejects_spectral_range_mismatch() -> None:
    with pytest.raises(ValueError, match="spectral_range"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(spectral_range=99.0))


def test_hermitian_restricted_diagnostics_rejects_negative_hermiticity_defect() -> None:
    with pytest.raises(ValueError, match="hermiticity_defect"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(hermiticity_defect=-1.0))


def test_hermitian_restricted_diagnostics_rejects_trace_mismatch() -> None:
    with pytest.raises(ValueError, match="sum\\(eigenvalues\\)"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(trace=999.0))


def test_hermitian_restricted_diagnostics_rejects_frobenius_identity_violation() -> None:
    with pytest.raises(ValueError, match="frobenius_norm"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(frobenius_norm=999.0))


def test_hermitian_restricted_diagnostics_rejects_empty_eigenvalues() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        HermitianRestrictedDiagnostics(**_hermitian_kwargs(eigenvalues=()))


# ---------------------------------------------------------------------------
# NonHermitianRestrictedDiagnostics.__post_init__ -- direct construction
# ---------------------------------------------------------------------------


def _non_hermitian_kwargs(**overrides) -> dict:
    defaults = dict(
        status=COMPLETE_MULTIPLET,
        trace=1 + 2j,
        singular_values=(3.0, 1.0),
        frobenius_norm=math.sqrt(10.0),
    )
    defaults.update(overrides)
    return defaults


def test_non_hermitian_restricted_diagnostics_accepts_valid_construction() -> None:
    diag = NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs())
    assert diag.singular_values == (3.0, 1.0)


def test_non_hermitian_restricted_diagnostics_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(status="degenerate"))


def test_non_hermitian_restricted_diagnostics_rejects_non_finite_trace() -> None:
    with pytest.raises(ValueError, match="not finite"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(trace=complex(float("nan"), 0.0)))


def test_non_hermitian_restricted_diagnostics_rejects_negative_singular_value() -> None:
    with pytest.raises(ValueError, match=">= 0"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(singular_values=(3.0, -1.0)))


def test_non_hermitian_restricted_diagnostics_rejects_non_finite_singular_value() -> None:
    with pytest.raises(ValueError, match="not finite"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(singular_values=(3.0, float("nan"))))


def test_non_hermitian_restricted_diagnostics_rejects_unsorted_singular_values() -> None:
    with pytest.raises(ValueError, match="sorted descending"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(singular_values=(1.0, 3.0)))


def test_non_hermitian_restricted_diagnostics_rejects_empty_singular_values() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(singular_values=()))


def test_non_hermitian_restricted_diagnostics_rejects_negative_frobenius_norm() -> None:
    with pytest.raises(ValueError, match="frobenius_norm"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(frobenius_norm=-1.0))


def test_non_hermitian_restricted_diagnostics_rejects_frobenius_identity_violation() -> None:
    with pytest.raises(ValueError, match="frobenius_norm"):
        NonHermitianRestrictedDiagnostics(**_non_hermitian_kwargs(frobenius_norm=999.0))


# ---------------------------------------------------------------------------
# V20 -- contract: no forbidden spectral API, no forbidden fields
# ---------------------------------------------------------------------------

_FORBIDDEN_SPECTRAL_ATTRS = {"eig", "eigh", "schur"}


def test_v20_diagnostics_module_never_calls_a_forbidden_spectral_api() -> None:
    source = inspect.getsource(diagnostics_module)
    tree = ast.parse(source)
    offending_calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _FORBIDDEN_SPECTRAL_ATTRS
    ]
    assert offending_calls == []


def test_v20_diagnostics_module_only_uses_eigvalsh_as_a_spectral_api() -> None:
    source = inspect.getsource(diagnostics_module)
    tree = ast.parse(source)
    spectral_calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"eigvalsh", "eig", "eigh", "eigvals", "schur", "eigs", "eigsh"}
    ]
    assert spectral_calls == ["eigvalsh"]


def test_v20_non_hermitian_diagnostics_has_no_forbidden_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(NonHermitianRestrictedDiagnostics)}
    assert field_names.isdisjoint({"eigenvalues", "eigenvectors", "schur"})


def test_v20_hermitian_diagnostics_has_no_eigenvector_field() -> None:
    field_names = {f.name for f in dataclasses.fields(HermitianRestrictedDiagnostics)}
    assert "eigenvectors" not in field_names


# ---------------------------------------------------------------------------
# Tolerance reuse
# ---------------------------------------------------------------------------


def test_diagnostics_module_reuses_restricted_hermiticity_tolerance() -> None:
    assert diagnostics_module.HERMITICITY_TOLERANCE == HERMITICITY_TOLERANCE
