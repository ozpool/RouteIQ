import itertools

import pytest

from routeiq.domain.corridor import corridor_cells
from routeiq.domain.geo import (
    LatLon,
    bearing_degrees,
    densify,
    destination_point,
    haversine_miles,
    simplify,
)
from routeiq.domain.similarity import overlap, route_cells

CHICAGO = LatLon(41.8781, -87.6298)
ST_LOUIS = LatLon(38.6270, -90.1994)


def test_haversine_known_distance() -> None:
    assert haversine_miles(CHICAGO, ST_LOUIS) == pytest.approx(262.3, abs=0.5)


def test_destination_point_round_trip() -> None:
    distance = haversine_miles(CHICAGO, ST_LOUIS)
    target = destination_point(CHICAGO, bearing_degrees(CHICAGO, ST_LOUIS), distance)
    assert haversine_miles(target, ST_LOUIS) < 0.01


def test_densify_bounds_step() -> None:
    dense = densify([CHICAGO, ST_LOUIS], max_step_mi=10)
    assert dense[0] == CHICAGO and dense[-1] == ST_LOUIS
    assert max(haversine_miles(a, b) for a, b in itertools.pairwise(dense)) <= 10.01


def test_simplify_drops_collinear_points_and_keeps_corners() -> None:
    line = [LatLon(0, x / 10) for x in range(11)] + [LatLon(1, 1)]
    assert simplify(line, 0.001) == [LatLon(0, 0), LatLon(0, 1), LatLon(1, 1)]


def test_overlap_same_and_disjoint() -> None:
    a = route_cells([CHICAGO, ST_LOUIS])
    b = route_cells([LatLon(30, -100), LatLon(31, -101)])
    assert overlap(a, a) == 1.0
    assert overlap(a, b) == 0.0


def test_corridor_covers_route_and_respects_cap() -> None:
    size, cells = corridor_cells([[CHICAGO, ST_LOUIS]], max_cells=400)
    assert size == 0.2
    assert 0 < len(cells) <= 400
    assert min(haversine_miles(c, CHICAGO) for c in cells) < 10
    assert len(set(cells)) == len(cells)


def test_corridor_coarsens_long_routes() -> None:
    size, cells = corridor_cells([[LatLon(34, -118), LatLon(40.7, -74)]], max_cells=150)
    assert size > 0.2
    assert len(cells) <= 150
