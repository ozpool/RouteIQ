import math
from collections.abc import Sequence

from routeiq.domain.geo import LatLon, densify, haversine_miles

CORRIDOR_RADIUS_MI = 30.0
MAX_CELLS = 400
# Coarsen the grid until the corridor fits MAX_CELLS; 0.2° is close to the forecast model grid.
CELL_SIZES_DEG = (0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5)
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
                    center = LatLon((i + 0.5) * size, (j + 0.5) * size)
                    if haversine_miles(center, sample) <= radius_mi:
                        cells.add((i, j))
    return cells


def corridor_cells(
    lines: Sequence[Sequence[LatLon]],
    radius_mi: float = CORRIDOR_RADIUS_MI,
    max_cells: int = MAX_CELLS,
) -> tuple[float, tuple[LatLon, ...]]:
    """Grid cell centers within `radius_mi` of any line, on the finest grid that fits."""
    for size in CELL_SIZES_DEG:
        cells = _cells_for(lines, size, radius_mi)
        if len(cells) <= max_cells:
            break
    centers = tuple(
        LatLon(round((i + 0.5) * size, 4), round((j + 0.5) * size, 4)) for i, j in sorted(cells)
    )
    return size, centers
