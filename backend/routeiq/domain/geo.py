import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

EARTH_RADIUS_MI = 3958.7613
METERS_PER_MILE = 1609.344


@dataclass(frozen=True, slots=True)
class LatLon:
    lat: float
    lon: float

    def rounded(self, places: int) -> "LatLon":
        return LatLon(round(self.lat, places), round(self.lon, places))


def haversine_miles(a: LatLon, b: LatLon) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def interpolate(a: LatLon, b: LatLon, fraction: float) -> LatLon:
    return LatLon(a.lat + (b.lat - a.lat) * fraction, a.lon + (b.lon - a.lon) * fraction)


def bearing_degrees(a: LatLon, b: LatLon) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlon = math.radians(b.lon - a.lon)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def destination_point(origin: LatLon, bearing_deg: float, distance_mi: float) -> LatLon:
    angular = distance_mi / EARTH_RADIUS_MI
    theta = math.radians(bearing_deg)
    lat1, lon1 = math.radians(origin.lat), math.radians(origin.lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular) + math.cos(lat1) * math.sin(angular) * math.cos(theta)
    )
    lon2 = lon1 + math.atan2(
        math.sin(theta) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )
    return LatLon(math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180)


def densify(points: Sequence[LatLon], max_step_mi: float) -> list[LatLon]:
    """Insert points so no two consecutive points are more than `max_step_mi` apart."""
    if not points:
        return []
    dense = [points[0]]
    for a, b in itertools.pairwise(points):
        steps = math.ceil(haversine_miles(a, b) / max_step_mi)
        dense.extend(interpolate(a, b, i / steps) for i in range(1, steps))
        dense.append(b)
    return dense


def _perpendicular_distance(p: LatLon, start: LatLon, end: LatLon) -> float:
    dx, dy = end.lon - start.lon, end.lat - start.lat
    if dx == 0 and dy == 0:
        return math.hypot(p.lon - start.lon, p.lat - start.lat)
    t = ((p.lon - start.lon) * dx + (p.lat - start.lat) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(p.lon - (start.lon + t * dx), p.lat - (start.lat + t * dy))


def simplify(points: Sequence[LatLon], tolerance_deg: float) -> list[LatLon]:
    """Douglas-Peucker in degree space; iterative so long routes cannot hit the recursion limit."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        max_distance, index = 0.0, first
        for i in range(first + 1, last):
            distance = _perpendicular_distance(points[i], points[first], points[last])
            if distance > max_distance:
                max_distance, index = distance, i
        if max_distance > tolerance_deg:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [p for p, kept in zip(points, keep, strict=True) if kept]
