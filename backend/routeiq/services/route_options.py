import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from routeiq.domain.geo import LatLon, bearing_degrees, destination_point, haversine_miles
from routeiq.domain.models import RouteCandidate
from routeiq.domain.similarity import overlap, route_cells
from routeiq.ports import NoRouteFound, ProviderError, RoutingProvider

logger = logging.getLogger(__name__)

TARGET_ROUTES = 3
DUPLICATE_OVERLAP = 0.8
MAX_DETOUR_RATIO = 1.75
# Perpendicular via-point offsets at the midpoint, as a share of the straight-line distance.
DETOUR_FRACTIONS = (0.15, -0.15, 0.3, -0.3)
MIN_DETOUR_OFFSET_MI = 10.0
MAX_DETOUR_OFFSET_MI = 120.0


@dataclass(frozen=True, slots=True)
class RouteOptions:
    candidates: tuple[RouteCandidate, ...]
    notes: tuple[str, ...]


def detour_via_points(origin: LatLon, destination: LatLon) -> list[LatLon]:
    distance = haversine_miles(origin, destination)
    heading = bearing_degrees(origin, destination)
    midpoint = destination_point(origin, heading, distance / 2)
    vias = []
    for fraction in DETOUR_FRACTIONS:
        offset = min(max(abs(fraction) * distance, MIN_DETOUR_OFFSET_MI), MAX_DETOUR_OFFSET_MI)
        side = 90 if fraction > 0 else -90
        vias.append(destination_point(midpoint, heading + side, offset))
    return vias


class RouteOptionsService:
    """Finds up to three distinct routes, adding via-point detours when the router offers fewer."""

    def __init__(self, routing: RoutingProvider, max_workers: int = 4):
        self._routing = routing
        self._max_workers = max_workers

    def find(self, origin: LatLon, destination: LatLon) -> RouteOptions:
        primary = self._routing.route([origin, destination], alternatives=TARGET_ROUTES)
        if not primary:
            raise NoRouteFound("routing", "no drivable route between these points")
        fastest_s = min(route.duration_s for route in primary)

        accepted: list[RouteCandidate] = []
        accepted_cells: list[frozenset[tuple[int, int]]] = []

        def consider(candidates: Sequence[RouteCandidate]) -> None:
            for candidate in candidates:
                if len(accepted) == TARGET_ROUTES:
                    return
                if accepted and candidate.duration_s > fastest_s * MAX_DETOUR_RATIO:
                    continue
                cells = route_cells(candidate.points)
                if any(overlap(cells, other) >= DUPLICATE_OVERLAP for other in accepted_cells):
                    continue
                accepted.append(candidate)
                accepted_cells.append(cells)

        consider(sorted(primary, key=lambda route: route.duration_s))
        if len(accepted) < TARGET_ROUTES:
            consider(self._detours(origin, destination))

        notes = ()
        if len(accepted) < TARGET_ROUTES:
            notes = (
                f"Only {len(accepted)} distinct route(s) exist between these points "
                "without a large detour.",
            )
        return RouteOptions(candidates=tuple(accepted), notes=notes)

    def _detours(self, origin: LatLon, destination: LatLon) -> list[RouteCandidate]:
        def fetch(via: LatLon) -> list[RouteCandidate]:
            try:
                return self._routing.route([origin, via, destination], alternatives=1)
            except ProviderError as exc:
                logger.warning("Detour via %s skipped: %s", via, exc)
                return []

        vias = detour_via_points(origin, destination)
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            return [route for routes in pool.map(fetch, vias) for route in routes]
