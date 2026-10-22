import math
from collections.abc import Sequence

from routeiq.domain.geo import LatLon, densify, haversine_miles
from routeiq.domain.weather_grid import GRID_SIZES_DEG, cell_center

CORRIDOR_RADIUS_MI = 25.0
# Lookup budget for one heatmap: with the checkpoint budget this keeps a whole trip well under
# the weather provider's per-minute quota.
MAX_CELLS = 150
_SAMPLE_STEP_MI = 10.0
_MILES_PER_DEG_LAT = 69.0


def _cells_for(
    lines: Sequence[Sequence[LatLon]], size: float, radius_mi: float
) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    dlat = radius_mi / _MILES_PER_DEG_LAT
    for line in lines:
        for sample in densify(line, _SAMPLE_STEP_MI):
            dlon = dlat / max(math.cos(math.radians(sample.lat)), 0.1)
            for i in range(
                math.floor((sample.lat - dlat) / size), math.floor((sample.lat + dlat) / size) + 1
            ):
                for j in range(
                    math.floor((sample.lon - dlon) / size),
                    math.floor((sample.lon + dlon) / size) + 1,
                ):
                    if haversine_miles(cell_center((i, j), size), sample) <= radius_mi:
                        cells.add((i, j))
    return cells


def corridor_cells(
    lines: Sequence[Sequence[LatLon]],
    radius_mi: float = CORRIDOR_RADIUS_MI,
    max_cells: int = MAX_CELLS,
) -> tuple[float, tuple[LatLon, ...]]:
    """Grid cell centers within `radius_mi` of any line, on the finest grid that fits."""
    for size in GRID_SIZES_DEG:
        cells = _cells_for(lines, size, radius_mi)
        if len(cells) <= max_cells:
            break
    return size, tuple(cell_center(cell, size) for cell in sorted(cells))
