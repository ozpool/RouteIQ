"""In-memory implementations of the ports. They are our own interfaces, so faking them is safe;
the real adapters are covered against recorded payloads in tests/adapters."""

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

from routeiq.domain.forecast import HourlyForecast, ceil_hour, floor_hour
from routeiq.domain.geo import LatLon
from routeiq.domain.models import RouteCandidate, Weather
from tests.factories import CALM


class FakeRouting:
    def __init__(
        self,
        primary: list[RouteCandidate],
        detour: Callable[[LatLon], list[RouteCandidate]] = lambda via: [],
    ):
        self.primary = primary
        self.detour = detour
        self.calls: list[list[LatLon]] = []

    def route(self, waypoints: Sequence[LatLon], alternatives: int) -> list[RouteCandidate]:
        self.calls.append(list(waypoints))
        if len(waypoints) == 2:
            return self.primary
        return self.detour(waypoints[1])


class FakeWeather:
    """Weather chosen per point and time by a function; defaults to calm everywhere."""

    def __init__(self, weather_for: Callable[[LatLon, datetime], Weather] = lambda p, t: CALM):
        self.weather_for = weather_for
        self.calls = 0

    def hourly_forecast(self, points, start, end):
        self.calls += 1
        start, end = floor_hour(start), ceil_hour(end)
        hours = int((end - start).total_seconds() // 3600) + 1
        return [
            HourlyForecast(
                start=start,
                hours=tuple(
                    self.weather_for(point, start + timedelta(hours=h)) for h in range(hours)
                ),
            )
            for point in points
        ]
