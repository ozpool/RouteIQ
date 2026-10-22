"""Adapter parsing against real recorded provider responses (see fixtures/)."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from django.core.cache.backends.locmem import LocMemCache

from routeiq.adapters import polyline
from routeiq.adapters.cached_weather import CachedWeatherProvider
from routeiq.adapters.open_meteo import OpenMeteoWeatherProvider, parse_forecasts
from routeiq.adapters.osrm import OsrmRoutingProvider, parse_routes
from routeiq.adapters.photon import parse_places
from routeiq.domain.forecast import HourlyForecast
from routeiq.domain.geo import METERS_PER_MILE, LatLon
from routeiq.ports import NoRouteFound, ProviderError, ProviderRateLimited
from tests.factories import CALM

FIXTURES = Path(__file__).parent / "fixtures"
DALLAS = LatLon(32.7767, -96.797)
FORT_WORTH = LatLon(32.7555, -97.3308)


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def client_returning(payload, status: int = 200, seen: list | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


class TestOsrm:
    def test_parses_alternatives_with_consistent_annotations(self) -> None:
        routes = parse_routes(load("osrm_dallas_fortworth.json"))
        assert len(routes) == 2
        first = routes[0]
        assert len(first.segment_distances_m) == len(first.points) - 1
        assert first.distance_m / METERS_PER_MILE == pytest.approx(32.1, abs=0.5)
        assert first.summary == "Tom Landry Freeway, Martin Luther King Jr Freeway"

    def test_requests_alternatives_only_between_two_waypoints(self) -> None:
        seen: list[httpx.Request] = []
        provider = OsrmRoutingProvider(
            client_returning(load("osrm_dallas_fortworth.json"), seen=seen), "https://osrm.test/"
        )
        provider.route([DALLAS, FORT_WORTH], alternatives=3)
        provider.route([DALLAS, LatLon(33, -97), FORT_WORTH], alternatives=3)
        assert seen[0].url.params["alternatives"] == "3"
        assert seen[1].url.params["alternatives"] == "false"
        assert seen[0].url.path.startswith("/route/v1/driving/-96.797000,32.776700;")

    def test_summary_drops_repeated_road_names_across_legs(self) -> None:
        data = load("osrm_dallas_fortworth.json")
        route = data["routes"][0]
        route["legs"] = [dict(route["legs"][0]), dict(route["legs"][0])]
        route["legs"][1]["annotation"] = {"duration": []}
        route["legs"][0]["summary"] = "I 70, US 40"
        route["legs"][1]["summary"] = "I 70, I 55"
        assert parse_routes(data)[0].summary == "I 70, US 40, I 55"

    def test_no_route_is_a_distinct_error(self) -> None:
        provider = OsrmRoutingProvider(
            client_returning({"code": "NoRoute", "message": "Impossible route"}, status=400),
            "https://osrm.test",
        )
        with pytest.raises(NoRouteFound):
            provider.route([DALLAS, FORT_WORTH], alternatives=3)

    def test_rate_limit_is_a_distinct_error(self, monkeypatch) -> None:
        monkeypatch.setattr("routeiq.adapters.http._BACKOFF_SECONDS", 0)
        provider = OsrmRoutingProvider(
            client_returning({"reason": "Too many requests"}, status=429), "https://osrm.test"
        )
        with pytest.raises(ProviderRateLimited):
            provider.route([DALLAS, FORT_WORTH], alternatives=3)

    def test_server_error_is_provider_error(self) -> None:
        provider = OsrmRoutingProvider(client_returning({}, status=500), "https://osrm.test")
        with pytest.raises(ProviderError):
            provider.route([DALLAS, FORT_WORTH], alternatives=3)


class TestOpenMeteo:
    START = datetime(2026, 10, 22, 18, tzinfo=UTC)
    END = datetime(2026, 10, 22, 21, tzinfo=UTC)

    def test_parses_multi_location_payload(self) -> None:
        series = parse_forecasts(
            load("open_meteo_two_points.json"), expected_points=2, start=self.START, end=self.END
        )
        assert len(series) == 2
        assert all(len(s.hours) == 4 and s.start == self.START for s in series)
        assert series[0].hours[0].wind_mph >= 0

    def test_rain_includes_showers(self) -> None:
        payload = load("open_meteo_two_points.json")[0]
        payload["hourly"]["rain"] = [0.1, 0, 0, 0]
        payload["hourly"]["showers"] = [0.2, 0, 0, 0]
        [series] = parse_forecasts(payload, expected_points=1, start=self.START, end=self.END)
        assert series.hours[0].rain_in_hr == pytest.approx(0.3)

    def test_rejects_wrong_time_axis_and_missing_values(self) -> None:
        payload = load("open_meteo_two_points.json")
        with pytest.raises(ProviderError):
            parse_forecasts(
                payload, 2, start=self.START + timedelta(hours=1), end=self.END + timedelta(hours=1)
            )
        payload[0]["hourly"]["snowfall"][1] = None
        with pytest.raises(ProviderError):
            parse_forecasts(payload, 2, start=self.START, end=self.END)

    def test_sends_imperial_units_and_utc_window(self) -> None:
        seen: list[httpx.Request] = []
        provider = OpenMeteoWeatherProvider(
            client_returning(load("open_meteo_two_points.json"), seen=seen), "https://om.test"
        )
        provider.hourly_forecast(
            [DALLAS, FORT_WORTH],
            self.START + timedelta(minutes=20),
            self.END - timedelta(minutes=30),
        )
        params = seen[0].url.params
        assert params["wind_speed_unit"] == "mph"
        assert params["precipitation_unit"] == "inch"
        assert (params["start_hour"], params["end_hour"]) == (
            "2026-10-22T18:00",
            "2026-10-22T21:00",
        )


class CountingWeather:
    def __init__(self) -> None:
        self.requested: list[list[LatLon]] = []

    def hourly_forecast(self, points, start, end):
        self.requested.append(list(points))
        hours = int((end - start).total_seconds() // 3600) + 1
        return [HourlyForecast(start=start, hours=(CALM,) * hours) for _ in points]


class TestCachedWeather:
    def make(self) -> tuple[CachedWeatherProvider, CountingWeather]:
        inner = CountingWeather()
        cache = LocMemCache("test-weather", {})
        cache.clear()
        return CachedWeatherProvider(inner, cache, ttl_seconds=60), inner

    def test_second_call_is_served_from_cache(self) -> None:
        provider, inner = self.make()
        start = datetime(2026, 10, 22, 22, 30, tzinfo=UTC)
        end = start + timedelta(hours=5)
        first = provider.hourly_forecast([DALLAS, FORT_WORTH], start, end)
        second = provider.hourly_forecast([FORT_WORTH], start, end)
        assert len(inner.requested) == 1
        assert first[0].start == datetime(2026, 10, 22, 22, tzinfo=UTC)
        assert len(first[0].hours) == 7  # 22:00 .. 04:00 across midnight
        assert second[0] == first[1]

    def test_only_missing_points_are_fetched_and_order_is_kept(self) -> None:
        provider, inner = self.make()
        start = datetime(2026, 10, 22, 6, tzinfo=UTC)
        provider.hourly_forecast([DALLAS], start, start)
        result = provider.hourly_forecast([FORT_WORTH, DALLAS, FORT_WORTH], start, start)
        assert inner.requested[1] == [FORT_WORTH.rounded(1)]
        assert len(result) == 3


def test_photon_labels() -> None:
    places = parse_places(load("photon_dallas.json"))
    assert places[0].label == "Dallas, Texas, United States"
    assert places[0].point.lat == pytest.approx(32.78, abs=0.1)


def test_polyline_decodes_reference_example() -> None:
    points = polyline.decode("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision=5)
    assert points == [LatLon(38.5, -120.2), LatLon(40.7, -120.95), LatLon(43.252, -126.453)]


def test_osrm_haversine_distance_matches_reported_distance() -> None:
    data = load("osrm_dallas_fortworth.json")
    for parsed, raw in zip(parse_routes(data), data["routes"], strict=True):
        assert parsed.distance_m == pytest.approx(raw["distance"], rel=0.005)


def test_photon_keeps_first_place_per_label() -> None:
    data = load("photon_dallas.json")
    data["features"].append(data["features"][0])
    labels = [place.label for place in parse_places(data)]
    assert len(labels) == len(set(labels))
