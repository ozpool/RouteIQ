from collections.abc import Sequence
from typing import Any

import httpx

from routeiq.adapters.http import get_json
from routeiq.domain.geo import LatLon
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
                "geometries": "geojson",
                "annotations": "distance,duration",
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
    points = tuple(LatLon(lat=lat, lon=lon) for lon, lat in route["geometry"]["coordinates"])
    distances: list[float] = []
    durations: list[float] = []
    for leg in route["legs"]:
        distances.extend(leg["annotation"]["distance"])
        durations.extend(leg["annotation"]["duration"])
    if len(distances) != len(points) - 1 or len(durations) != len(distances):
        raise ValueError("annotation count does not match geometry")
    summary = ", ".join(leg["summary"] for leg in route["legs"] if leg.get("summary"))
    return RouteCandidate(
        points=points,
        segment_distances_m=tuple(float(d) for d in distances),
        segment_durations_s=tuple(float(d) for d in durations),
        summary=summary,
    )
