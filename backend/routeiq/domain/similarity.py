import math
from collections.abc import Sequence

from routeiq.domain.geo import LatLon, densify

_CELL_DEG = 0.02
_SAMPLE_STEP_MI = 0.5


def route_cells(points: Sequence[LatLon]) -> frozenset[tuple[int, int]]:
    return frozenset(
        (math.floor(p.lat / _CELL_DEG), math.floor(p.lon / _CELL_DEG))
        for p in densify(points, _SAMPLE_STEP_MI)
    )


def overlap(a: frozenset[tuple[int, int]], b: frozenset[tuple[int, int]]) -> float:
    """Jaccard overlap of the grid cells two routes pass through (1.0 = same road)."""
    union = len(a | b)
    return len(a & b) / union if union else 1.0
