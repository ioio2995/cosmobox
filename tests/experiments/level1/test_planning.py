from __future__ import annotations

import ast
import inspect

import pytest

from experiments.level1 import manifest as m
from experiments.level1 import planning as p


def _manifest() -> m.Manifest:
    return m.load_manifest()


# ---------------------------------------------------------------------------
# Deterministic plan
# ---------------------------------------------------------------------------


def test_build_campaign_plan_is_deterministic() -> None:
    manifest = _manifest()
    plan_a = p.build_campaign_plan(manifest)
    plan_b = p.build_campaign_plan(manifest)
    assert [case.case_id for case in plan_a] == [case.case_id for case in plan_b]
    assert [case.scientific_seed for case in plan_a] == [case.scientific_seed for case in plan_b]
    assert [case.solver_seed for case in plan_a] == [case.solver_seed for case in plan_b]


def test_build_campaign_plan_no_longer_accepts_a_free_root_seed() -> None:
    manifest = _manifest()
    signature = inspect.signature(p.build_campaign_plan)
    assert "root_seed" not in signature.parameters
    with pytest.raises(TypeError):
        p.build_campaign_plan(manifest, root_seed=123)  # type: ignore[call-arg]


def test_build_campaign_plan_derives_seeds_from_manifest_scientific_seed() -> None:
    manifest = _manifest()
    plan = p.build_campaign_plan(manifest)
    expected_first_case_scientific_seed = p.derive_case_seed(
        manifest.scientific_seed, plan[0].case_id, "scientific"
    )
    assert plan[0].scientific_seed == expected_first_case_scientific_seed


def test_build_campaign_plan_case_ids_are_unique() -> None:
    plan = p.build_campaign_plan(_manifest())
    case_ids = [case.case_id for case in plan]
    assert len(case_ids) == len(set(case_ids))


def test_build_campaign_plan_case_id_is_stable_across_calls() -> None:
    manifest = _manifest()
    plan_a = p.build_campaign_plan(manifest)
    plan_b = p.build_campaign_plan(manifest)
    for case_a, case_b in zip(plan_a, plan_b):
        assert case_a.case_id == case_b.case_id


# ---------------------------------------------------------------------------
# Seed derivation
# ---------------------------------------------------------------------------


def test_derive_case_seed_is_stable() -> None:
    a = p.derive_case_seed(42, "some-case-id", "scientific")
    b = p.derive_case_seed(42, "some-case-id", "scientific")
    assert a == b


def test_derive_case_seed_differs_by_role() -> None:
    scientific = p.derive_case_seed(42, "some-case-id", "scientific")
    solver = p.derive_case_seed(42, "some-case-id", "solver")
    assert scientific != solver


def test_derive_case_seed_differs_by_root_seed() -> None:
    a = p.derive_case_seed(1, "some-case-id", "scientific")
    b = p.derive_case_seed(2, "some-case-id", "scientific")
    assert a != b


def test_derive_case_seed_differs_by_case_id() -> None:
    a = p.derive_case_seed(42, "case-a", "scientific")
    b = p.derive_case_seed(42, "case-b", "scientific")
    assert a != b


def test_derive_case_seed_rejects_negative_root_seed() -> None:
    with pytest.raises(ValueError, match="root_seed"):
        p.derive_case_seed(-1, "some-case-id", "scientific")


def test_planning_module_never_calls_python_builtin_hash() -> None:
    """derive_case_seed/compute_case_id must use SHA-256, never hash()
    (unstable across processes/PYTHONHASHSEED, unsuitable for
    reproducible provenance). Parses planning.py's own AST and asserts no
    Call node's function is the bare name `hash` -- immune to the
    docstrings/comments in this very module mentioning "hash()" as prose
    (a plain text/regex search would false-positive on those), and to
    `hashlib.sha256(...)`, whose Call's function is an Attribute, not a
    bare Name."""
    tree = ast.parse(inspect.getsource(p))
    offending = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash"
    ]
    assert offending == [], "planning.py must never call the builtin hash()"


# ---------------------------------------------------------------------------
# Ordered pairs
# ---------------------------------------------------------------------------


def test_build_ordered_pairs_contains_both_orderings_as_distinct_elements() -> None:
    pairs = p.build_ordered_pairs(3)
    assert (0, 1) in pairs
    assert (1, 0) in pairs
    assert (0, 1) != (1, 0)
    assert len(pairs) == len(set(pairs))


def test_build_ordered_pairs_excludes_i_equals_j() -> None:
    pairs = p.build_ordered_pairs(4)
    assert all(i != j for i, j in pairs)


def test_build_ordered_pairs_count_matches_n_times_n_minus_one() -> None:
    n = 5
    pairs = p.build_ordered_pairs(n)
    assert len(pairs) == n * (n - 1)


def test_build_ordered_pairs_rejects_negative_n_nodes() -> None:
    with pytest.raises(ValueError, match="n_nodes"):
        p.build_ordered_pairs(-1)


def test_campaign_case_spec_ordered_pairs_matches_its_own_node_count() -> None:
    plan = p.build_campaign_plan(_manifest())
    triangle_case = next(case for case in plan if case.geometry == "triangle")
    n_nodes = len(triangle_case.hamiltonian_parameters.J)
    assert triangle_case.ordered_pairs == p.build_ordered_pairs(n_nodes)
    assert len(triangle_case.ordered_pairs) == n_nodes * (n_nodes - 1)


def test_campaign_case_spec_rejects_a_wrong_ordered_pairs_plan() -> None:
    plan = p.build_campaign_plan(_manifest())
    triangle_case = plan[0]
    with pytest.raises(ValueError, match="ordered_pairs"):
        p.CampaignCaseSpec(
            geometry=triangle_case.geometry,
            spin=triangle_case.spin,
            hamiltonian_case_id=triangle_case.hamiltonian_case_id,
            hamiltonian_parameters=triangle_case.hamiltonian_parameters,
            sector_id=triangle_case.sector_id,
            spectral_window=triangle_case.spectral_window,
            physical_dimension=triangle_case.physical_dimension,
            spectrum_options=triangle_case.spectrum_options,
            target_groups=triangle_case.target_groups,
            ordered_pairs=((0, 1),),  # wrong: does not cover this case's own node count
            scientific_seed=triangle_case.scientific_seed,
            solver_seed=triangle_case.solver_seed,
            validation_rotation_seed=None,
            case_id=triangle_case.case_id,
        )
