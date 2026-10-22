import itertools
from collections.abc import Sequence
from typing import Any

import httpx

from routeiq.adapters import polyline
from routeiq.adapters.http import get_json
from routeiq.domain.geo import METERS_PER_MILE, LatLon, haversine_miles
from routeiq.domain.models import RouteCandidate
from routeiq.ports import NoRouteFound, ProviderError

PROVIDER = "osrm"
_NO_ROUTE_CODES = frozenset({"NoRoute", "NoSegment"})


class OsrmRoutingProvider:
    def __init__(self, client: httpx.Client, base_url: str):
        self._client = client
        self._base_url = base_url.rstrip("/")

    def route(self, waypoints: Sequence[LatLon], alternatives: int) -> list[RouteCandidate]:
        coordinates = ";".join(f"{p.lon:.6f},{p.lat:.6f}" for p in waypoints)
        # OSRM only computes alternatives between exactly two waypoints.
        wants_alternatives = len(waypoints) == 2 and alternatives > 1
        data = get_json(
            self._client,
            PROVIDER,
            f"{self._base_url}/route/v1/driving/{coordinates}",
            {
                "alternatives": alternatives if wants_alternatives else "false",
                "overview": "full",
                # polyline6 + duration-only is ~3x smaller than GeoJSON with both annotations.
                "geometries": "polyline6",
                "annotations": "duration",
                # Leg summaries ("I 55, I 70") are only filled in when steps are requested.
                "steps": "true",
            },
            json_error_statuses=frozenset({400}),
        )
        return parse_routes(data)


def parse_routes(data: Any) -> list[RouteCandidate]:
    code = data.get("code") if isinstance(data, dict) else None
    if code in _NO_ROUTE_CODES:
        raise NoRouteFound(PROVIDER, data.get("message") or "no drivable route between points")
    if code != "Ok":
        raise ProviderError(PROVIDER, f"unexpected response code {code!r}")
    try:
        return [_parse_route(route) for route in data["routes"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError(PROVIDER, f"malformed route payload ({exc})") from exc


def _parse_route(route: dict[str, Any]) -> RouteCandidate:
    points = tuple(polyline.decode(route["geometry"], precision=6))
    durations = [d for leg in route["legs"] for d in leg["annotation"]["duration"]]
    if len(durations) != len(points) - 1:
        raise ValueError("annotation count does not match geometry")
    distances = [haversine_miles(a, b) * METERS_PER_MILE for a, b in itertools.pairwise(points)]
    # Detour routes have two legs that often repeat the same road names.
    roads = [
        road.strip() for leg in route["legs"] for road in (leg.get("summary") or "").split(",")
    ]
    summary = ", ".join(dict.fromkeys(road for road in roads if road))
    return RouteCandidate(
        points=points,
        segment_distances_m=tuple(float(d) for d in distances),
        segment_durations_s=tuple(float(d) for d in durations),
        summary=summary,
    )
