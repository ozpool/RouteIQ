from routeiq.domain.corridor import corridor_cells
from routeiq.domain.geo import LatLon, densify
from routeiq.domain.weather_grid import GRID_SIZES_DEG, snap_to_grid

CHICAGO = LatLon(41.8781, -87.6298)
ST_LOUIS = LatLon(38.6270, -90.1994)
LOS_ANGELES = LatLon(34.05, -118.24)
NEW_YORK = LatLon(40.71, -74.0)


def test_short_trip_uses_finest_grid_and_keeps_order() -> None:
    points = densify([CHICAGO, ST_LOUIS], max_step_mi=10)
    size, snapped = snap_to_grid(points, max_cells=250)
    assert size == GRID_SIZES_DEG[0]
    assert len(snapped) == len(points)
    assert abs(snapped[0].lat - CHICAGO.lat) <= size / 2
    assert abs(snapped[-1].lon - ST_LOUIS.lon) <= size / 2


def test_long_trip_is_coarsened_to_fit_the_budget() -> None:
    # Three separate coast-to-coast routes, like a real long trip.
    points = [
        point
        for shift in (0.0, 1.0, 2.0)
        for point in densify(
            [LatLon(LOS_ANGELES.lat + shift, LOS_ANGELES.lon), LatLon(NEW_YORK.lat, NEW_YORK.lon)],
            max_step_mi=10,
        )
    ]
    size, snapped = snap_to_grid(points, max_cells=250)
    assert size > GRID_SIZES_DEG[0]
    assert len(set(snapped)) <= 250


def test_checkpoint_lookups_reuse_heatmap_cells() -> None:
    line = densify([CHICAGO, ST_LOUIS], max_step_mi=10)
    _, snapped = snap_to_grid(line, max_cells=250)
    _, cells = corridor_cells([line], max_cells=10_000)
    assert set(snapped) <= set(cells)
