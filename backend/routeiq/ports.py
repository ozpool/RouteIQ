"""Interfaces the services depend on. Adapters in routeiq.adapters implement them."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from routeiq.domain.forecast import HourlyForecast
from routeiq.domain.geo import LatLon
from routeiq.domain.models import Place, RouteCandidate


class ProviderError(Exception):
    """An upstream provider failed or returned something we cannot trust."""

    def __init__(self, provider: str, message: str):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.message = message


class NoRouteFound(ProviderError):
    pass


class ProviderRateLimited(ProviderError):
    pass


class RoutingProvider(Protocol):
    def route(self, waypoints: Sequence[LatLon], alternatives: int) -> list[RouteCandidate]:
        """Routes through `waypoints` in order; up to `alternatives` routes when there are two."""
        ...


class WeatherProvider(Protocol):
    def hourly_forecast(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        """One hourly series per point, in input order, covering at least `start`..`end`."""
        ...


class Geocoder(Protocol):
    def search(self, query: str, limit: int) -> list[Place]: ...
