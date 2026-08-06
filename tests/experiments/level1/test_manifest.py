from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from experiments.level1 import manifest as m


def _raw() -> dict:
    return m.load_manifest_json()


# ---------------------------------------------------------------------------
# Schema validation / rejection
# ---------------------------------------------------------------------------


def test_manifest_json_validates_against_its_schema() -> None:
    raw = _raw()
    assert raw["schema_version"] == "level1-correlators-v2"


def test_manifest_schema_is_a_well_formed_draft202012_schema() -> None:
    Draft202012Validator.check_schema(m._load_schema())


def _assert_invalid(raw: dict) -> None:
    errors = list(m._validator().iter_errors(raw))
    assert errors, "expected the manifest to be rejected by its schema"


def test_manifest_rejects_unknown_top_level_property() -> None:
    raw = _raw()
    raw["unexpected_field"] = 1
    _assert_invalid(raw)


def test_manifest_rejects_unknown_property_in_target_group() -> None:
    raw = _raw()
    raw["target_groups"]["triangle"][0]["unexpected"] = True
    _assert_invalid(raw)


def test_manifest_rejects_unknown_property_in_productions() -> None:
    raw = _raw()
    raw["productions"]["unexpected"] = []
    _assert_invalid(raw)


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_is_stable_under_key_reordering() -> None:
    raw = _raw()
    reordered = json.loads(json.dumps(raw))  # dict order is already insertion order in Python
    shuffled = dict(reversed(list(reordered.items())))
    assert m.compute_manifest_fingerprint(raw) == m.compute_manifest_fingerprint(shuffled)


def test_fingerprint_changes_when_scientific_data_changes() -> None:
    raw = _raw()
    baseline = m.compute_manifest_fingerprint(raw)
    mutated = copy.deepcopy(raw)
    mutated["hamiltonian_cases"][0]["J_uniform"] = 999.0
    assert m.compute_manifest_fingerprint(mutated) != baseline


def test_fingerprint_includes_scientific_seed() -> None:
    raw = _raw()
    baseline = m.compute_manifest_fingerprint(raw)
    mutated = copy.deepcopy(raw)
    mutated["scientific_seed"] = raw["scientific_seed"] + 1
    assert m.compute_manifest_fingerprint(mutated) != baseline


def test_load_manifest_fingerprint_matches_compute_manifest_fingerprint() -> None:
    manifest = m.load_manifest()
    assert manifest.fingerprint == m.compute_manifest_fingerprint(manifest.raw)


# ---------------------------------------------------------------------------
# scientific_seed
# ---------------------------------------------------------------------------


def test_manifest_scientific_seed_is_a_non_negative_int() -> None:
    manifest = m.load_manifest()
    assert isinstance(manifest.scientific_seed, int)
    assert manifest.scientific_seed >= 0


def test_manifest_rejects_negative_scientific_seed() -> None:
    raw = _raw()
    raw["scientific_seed"] = -1
    _assert_invalid(raw)


# ---------------------------------------------------------------------------
# pair_selection
# ---------------------------------------------------------------------------


def test_pair_selection_is_all_ordered_distinct_pairs() -> None:
    manifest = m.load_manifest()
    assert manifest.pair_selection == "all_ordered_distinct_pairs"


def test_manifest_rejects_the_old_all_unordered_pairs_value() -> None:
    raw = _raw()
    raw["pair_selection"] = "all_unordered_pairs"
    _assert_invalid(raw)


# ---------------------------------------------------------------------------
# productions taxonomy
# ---------------------------------------------------------------------------


def test_productions_has_all_five_categories() -> None:
    productions = m.load_manifest().productions
    assert productions.single_case_observables
    assert productions.single_case_diagnostics
    assert productions.path_statistics
    assert set(productions.orbit_statistics) == {"orbit_mean", "orbit_max_pairwise_spread", "orbit_covariance_defect"}
    assert productions.inter_s_observables.primary == "gamma_O"


def test_gamma_o_is_only_in_inter_s_observables_not_single_case() -> None:
    productions = m.load_manifest().productions
    assert "gamma_O" not in productions.single_case_observables
    assert productions.inter_s_observables.primary == "gamma_O"


def test_g_occ_and_path_phase_coherence_are_marked_unproduced() -> None:
    inter_s = m.load_manifest().productions.inter_s_observables
    assert "G_occ" in inter_s.unproduced
    assert "path_phase_coherence" in inter_s.unproduced
    assert "path_phase_coherence" in inter_s.secondary  # pre-registered even though unproduced


def test_robustness_verdicts_are_flagged_as_part_of_the_inter_s_step() -> None:
    inter_s = m.load_manifest().productions.inter_s_observables
    assert inter_s.robustness_verdicts_included is True


# ---------------------------------------------------------------------------
# Target group normative fields
# ---------------------------------------------------------------------------


def test_first_excited_requires_complete_and_inter_s_exact_match() -> None:
    manifest = m.load_manifest()
    for geometry_targets in manifest.target_groups.values():
        for target in geometry_targets:
            if target.selection_kind == "first_excited":
                assert target.required_spectral_status == "complete_multiplet"
                assert target.requires_inter_s_exact_match is True


def test_fundamental_and_flavor_label_require_complete_but_not_exact_match() -> None:
    manifest = m.load_manifest()
    for geometry_targets in manifest.target_groups.values():
        for target in geometry_targets:
            if target.selection_kind in ("fundamental", "flavor_label"):
                assert target.required_spectral_status == "complete_multiplet"
                assert target.requires_inter_s_exact_match is False


def test_structurally_not_applicable_has_no_normative_status_requirement() -> None:
    manifest = m.load_manifest()
    found = False
    for geometry_targets in manifest.target_groups.values():
        for target in geometry_targets:
            if target.selection_kind == "structurally_not_applicable":
                found = True
                assert target.required_spectral_status is None
                assert target.requires_inter_s_exact_match is False
    assert found, "expected at least one structurally_not_applicable target (ring4's T_3_2)"


def test_target_group_spec_rejects_mismatched_required_spectral_status() -> None:
    with pytest.raises(ValueError, match="required_spectral_status"):
        m.TargetGroupSpec(
            target_id="x",
            selection_kind="fundamental",
            target_twice_T=None,
            selection_within_label=None,
            required_spectral_status=None,  # fundamental requires complete_multiplet
            requires_inter_s_exact_match=False,
        )


def test_target_group_spec_rejects_mismatched_inter_s_exact_match_flag() -> None:
    with pytest.raises(ValueError, match="requires_inter_s_exact_match"):
        m.TargetGroupSpec(
            target_id="x",
            selection_kind="fundamental",
            target_twice_T=None,
            selection_within_label=None,
            required_spectral_status="complete_multiplet",
            requires_inter_s_exact_match=True,  # only first_excited may require this
        )
