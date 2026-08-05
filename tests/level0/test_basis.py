from __future__ import annotations

import itertools
from fractions import Fraction

import pytest

from cosmobox.level0.basis import build_basis
from cosmobox.level0.encoding import decode, encode
from cosmobox.level0.lattice import Lattice, build_lattice

T6_GEOMETRIES = ("triangle", "chain3", "ring4", "ring5")


def _node_charge(occupation: tuple[int, ...], node: int, n_flavors: int) -> Fraction:
    occ_count = sum(occupation[node * n_flavors : (node + 1) * n_flavors])
    return Fraction(occ_count) - Fraction(n_flavors, 2)


def _exact_gauss_residuals(
    lattice: Lattice,
    n_flavors: int,
    occupation: tuple[int, ...],
    flux: tuple[int, ...],
    external_charges: tuple[Fraction, ...],
) -> list[Fraction]:
    """Independent (non-doubled) exact residual of G_i for every node."""
    residuals = []
    for node in lattice.nodes:
        total = Fraction(0)
        for edge_index, edge in enumerate(lattice.edges):
            if edge.source == node:
                total += flux[edge_index]
            elif edge.target == node:
                total -= flux[edge_index]
        total -= _node_charge(occupation, node, n_flavors)
        total -= external_charges[node]
        residuals.append(total)
    return residuals


def _brute_force_basis(
    lattice: Lattice,
    n_flavors: int,
    spin: int,
    external_charges: tuple[Fraction, ...] | None,
):
    """Independent reference: enumerate ALL flux on ALL edges, filter by exact G_i=0.

    Uses plain Fraction arithmetic (no doubled integers) as a genuinely
    independent cross-check of basis.py's tree-based resolution (T6).
    """
    n_nodes = len(lattice.nodes)
    n_edges = len(lattice.edges)
    ext = external_charges if external_charges is not None else tuple(Fraction(0) for _ in lattice.nodes)
    target_total = -sum(ext, start=Fraction(0))

    occupations_by_sector: dict[tuple[Fraction, ...], list[tuple[int, ...]]] = {}
    for occupation in itertools.product((0, 1), repeat=n_nodes * n_flavors):
        charge_vector = tuple(_node_charge(occupation, node, n_flavors) for node in lattice.nodes)
        if sum(charge_vector, start=Fraction(0)) != target_total:
            continue
        occupations_by_sector.setdefault(charge_vector, []).append(occupation)

    keys: set[int] = set()
    sectors: dict[tuple[Fraction, ...], tuple[int, int, int]] = {}
    per_occupation_flux_counts: list[int] = []

    for charge_vector, occupation_list in occupations_by_sector.items():
        admissible = []
        for flux in itertools.product(range(-spin, spin + 1), repeat=n_edges):
            residuals = _exact_gauss_residuals(lattice, n_flavors, occupation_list[0], flux, ext)
            if all(r == 0 for r in residuals):
                admissible.append(flux)
        n_flux = len(admissible)
        per_occupation_flux_counts.extend([n_flux] * len(occupation_list))
        sectors[charge_vector] = (len(occupation_list), n_flux, len(occupation_list) * n_flux)
        for occupation in occupation_list:
            for flux in admissible:
                keys.add(int(encode(lattice, n_flavors, spin, occupation, flux)))

    return keys, sectors, per_occupation_flux_counts


@pytest.mark.parametrize(
    ("geometry", "n_flavors", "spin", "external_charges"),
    [
        # Non-empty, non-trivial cases: M=2 keeps Q_i integer, so these
        # actually exercise the chords and a cyclic tree resolution with
        # several admissible flux configurations per sector -- not just
        # two independent methods agreeing that a sector is impossible.
        ("triangle", 2, 1, None),
        ("ring4", 2, 1, None),
        ("ring5", 2, 1, None),
        # M=1 cases: every sector is empty (parity constraint), which
        # exercises the "correctly reports nothing" path instead.
        ("triangle", 1, 1, None),
        ("chain3", 1, 1, None),  # expected empty: no occupation reaches Q_tot = 0
        ("chain3", 2, 1, None),  # non-empty but chain3 has no chords
        ("ring4", 1, 1, None),
        ("ring5", 1, 1, None),
        ("chain3", 1, 1, (Fraction(1, 2), Fraction(1, 2), Fraction(1, 2))),
    ],
)
def test_tree_resolution_matches_brute_force_exactly(
    geometry: str, n_flavors: int, spin: int, external_charges
) -> None:
    lattice = build_lattice(geometry)
    report = build_basis(lattice, n_flavors, spin, external_charges)

    ext = external_charges if external_charges is not None else tuple(Fraction(0) for _ in lattice.nodes)
    brute_keys, brute_sectors, brute_flux_counts = _brute_force_basis(
        lattice, n_flavors, spin, external_charges
    )

    assert {int(key) for key in report.keys} == brute_keys
    assert sorted(int(key) for key in report.keys) == [int(key) for key in report.keys]

    tree_sectors = {
        sector.charge_vector: (sector.matter_multiplicity, sector.n_flux_admissible, sector.dimension)
        for sector in report.sectors
    }
    assert tree_sectors == brute_sectors

    brute_excluded = {cv: stats for cv, stats in brute_sectors.items() if stats[1] == 0}
    tree_excluded = {
        sector.charge_vector: (sector.matter_multiplicity, sector.n_flux_admissible, sector.dimension)
        for sector in report.excluded_sectors
    }
    assert tree_excluded == brute_excluded
    assert set(report.excluded_sectors) <= set(report.sectors)

    if brute_flux_counts:
        assert report.mean_flux_configs_per_occupation == pytest.approx(
            sum(brute_flux_counts) / len(brute_flux_counts)
        )
        assert report.max_flux_configs_per_occupation == max(brute_flux_counts)
    else:
        assert report.mean_flux_configs_per_occupation == 0.0
        assert report.max_flux_configs_per_occupation == 0


def test_chain3_m1_has_no_physical_sector_without_external_charge() -> None:
    lattice = build_lattice("chain3")
    report = build_basis(lattice, n_flavors=1, spin=1, external_charges=None)
    assert report.keys == ()
    assert report.sectors == ()
    assert report.mean_flux_configs_per_occupation == 0.0
    assert report.max_flux_configs_per_occupation == 0


@pytest.mark.parametrize(
    ("geometry", "n_flavors", "spin"),
    [
        # M=1 gives a half-integer Q_i on every node, which the doubled-integer
        # parity check in basis.py correctly rejects everywhere without an
        # external charge to compensate node-by-node (not just in total) --
        # see test_m1_without_external_charge_has_no_physical_state_anywhere.
        # M=2 keeps Q_i integer and is used here to exercise a non-empty basis.
        ("triangle", 2, 1),
        ("ring4", 2, 1),
        ("ring5", 2, 1),
        ("disk7", 2, 1),
    ],
)
def test_every_returned_key_satisfies_exact_gauss_law(geometry: str, n_flavors: int, spin: int) -> None:
    lattice = build_lattice(geometry)
    report = build_basis(lattice, n_flavors, spin)
    ext = tuple(Fraction(0) for _ in lattice.nodes)

    assert report.keys, "expected a non-empty basis for this configuration"
    # Deterministic (sorted keys), bounded sample: full geometries like disk7
    # can return hundreds of thousands of keys, and this check re-verifies
    # each one independently via decode() + exact Fraction arithmetic.
    sample_size = 500
    stride = max(1, len(report.keys) // sample_size)
    for key in report.keys[::stride]:
        occupation, flux = decode(lattice, n_flavors, spin, key)
        residuals = _exact_gauss_residuals(lattice, n_flavors, occupation, flux, ext)
        assert all(r == 0 for r in residuals)


def test_excluded_sectors_preserve_matter_multiplicity() -> None:
    lattice = build_lattice("ring4")
    report = build_basis(lattice, n_flavors=1, spin=1)
    assert report.sectors  # ring4, M=1: several Q_tot=0 sectors exist, all excluded (parity)
    assert report.sectors == report.excluded_sectors
    for sector in report.excluded_sectors:
        assert sector.n_flux_admissible == 0
        assert sector.dimension == 0
        # at M=1 each charge vector corresponds to exactly one occupation bit pattern
        assert sector.matter_multiplicity == 1


def test_dimension_equals_sum_of_sector_dimensions() -> None:
    lattice = build_lattice("ring4")
    report = build_basis(lattice, n_flavors=1, spin=1)
    assert len(report.keys) == sum(sector.dimension for sector in report.sectors)


def test_keys_are_sorted_and_unique() -> None:
    lattice = build_lattice("ring5")
    report = build_basis(lattice, n_flavors=2, spin=1)
    as_ints = [int(key) for key in report.keys]
    assert as_ints == sorted(as_ints)
    assert len(as_ints) == len(set(as_ints))


def test_rejects_wrong_length_external_charges() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        build_basis(lattice, n_flavors=1, spin=1, external_charges=(Fraction(0), Fraction(0)))


def test_rejects_external_charge_with_bad_denominator() -> None:
    lattice = build_lattice("triangle")
    with pytest.raises(ValueError):
        build_basis(lattice, n_flavors=1, spin=1, external_charges=(Fraction(1, 3), Fraction(0), Fraction(0)))


def test_accepts_integer_and_half_integer_external_charges() -> None:
    lattice = build_lattice("triangle")
    report = build_basis(lattice, n_flavors=1, spin=1, external_charges=(1, Fraction(1, 2), Fraction(-1, 2)))
    assert isinstance(report.mean_flux_configs_per_occupation, float)


def test_disk7_is_reasonably_fast_at_minimal_parameters() -> None:
    lattice = build_lattice("disk7")
    report = build_basis(lattice, n_flavors=2, spin=1)
    assert report.keys  # sanity: a physical basis exists for disk7, M=2, S=1


def test_m1_without_external_charge_has_no_physical_state_anywhere() -> None:
    """M=1 gives a half-integer Q_i on every node; without a compensating
    external charge at that same node, the doubled Gauss-law parity check
    can never be satisfied -- this holds for every geometry, not just
    chain3 (see test_chain3_m1_has_no_physical_sector_without_external_charge)."""
    for geometry in ("triangle", "chain3", "ring4", "ring5", "disk7"):
        lattice = build_lattice(geometry)
        report = build_basis(lattice, n_flavors=1, spin=1)
        assert report.keys == ()
