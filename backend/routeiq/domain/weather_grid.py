"""The lookup grid shared by checkpoint weather and the corridor heatmap.

The free Open-Meteo tier counts every location in a request (about 600 per minute, 5,000 per
hour). Snapping lookups to one shared grid bounds the cost of a trip and lets the heatmap reuse
the cells the checkpoints already fetched. Each checkpoint still reads its own ETA hour; only
the lookup position moves, by at most half a cell.
"""

import math
from collections.abc import Sequence

from routeiq.domain.geo import LatLon

# 0.2° (~12 mi) is close to the global forecast models' resolution; coarser sizes are used only
# when a trip would otherwise exceed its lookup budget.
GRID_SIZES_DEG = (0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5)


def cell_of(point: LatLon, size: float) -> tuple[int, int]:
    return math.floor(point.lat / size), math.floor(point.lon / size)


def cell_center(cell: tuple[int, int], size: float) -> LatLon:
    i, j = cell
    return LatLon(round((i + 0.5) * size, 4), round((j + 0.5) * size, 4))


def snap_to_grid(points: Sequence[LatLon], max_cells: int) -> tuple[float, list[LatLon]]:
    """Each point's cell center on the finest grid where all points fit in `max_cells` cells."""
    for size in GRID_SIZES_DEG:
        cells = [cell_of(point, size) for point in points]
        if len(set(cells)) <= max_cells:
            break
    return size, [cell_center(cell, size) for cell in cells]
