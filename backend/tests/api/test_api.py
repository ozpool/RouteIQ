from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from routeiq.container import Container
from routeiq.domain.geo import LatLon
from routeiq.domain.models import Place
from routeiq.ports import NoRouteFound, ProviderError, ProviderRateLimited
from routeiq.services.heatmap import CorridorHeatmapService
from routeiq.services.route_options import RouteOptionsService
from routeiq.services.trip_planner import TripPlanner
from tests.factories import straight_candidate
from tests.fakes import FakeRouting, FakeWeather


class FakeGeocoder:
    def search(self, query: str, limit: int) -> list[Place]:
        return [Place(label=f"{query}, Texas", point=LatLon(32.78, -96.8))][:limit]


def container_with(routing) -> Container:
    weather = FakeWeather()
    return Container(
        geocoder=FakeGeocoder(),
        trip_planner=TripPlanner(RouteOptionsService(routing), weather, truck_max_speed_mph=65),
        heatmap=CorridorHeatmapService(weather),
    )


@pytest.fixture
def api(monkeypatch) -> APIClient:
    cache.clear()
    routing = FakeRouting(
        primary=[straight_candidate(130, 60, lat=40)],
        detour=lambda via: [straight_candidate(140, 60, lat=round(via.lat, 1))],
    )
    monkeypatch.setattr("routeiq.api.views.get_container", lambda: container_with(routing))
    return APIClient()


def plan_body(**overrides):
    body = {
        "origin": {"lat": 40.0, "lon": -100.0, "label": "A"},
        "destination": {"lat": 40.0, "lon": -97.5, "label": "B"},
        "departure_time": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_weight_lb": 42000,
        "checkpoint_interval_mi": 25,
    }
    body.update(overrides)
    return body


def test_health(api: APIClient) -> None:
    assert api.get("/api/health").json() == {"status": "ok"}


def test_plan_returns_routes_checkpoints_and_recommendation(api: APIClient) -> None:
    response = api.post("/api/trips/plan", plan_body(), format="json")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) == 3
    route = data["routes"][0]
    assert route["checkpoints"][0]["risk"]["level"] == "low"
    assert route["checkpoints"][0]["coordinate"] == [-100.0, 40.0]
    assert route["segments"][0]["coordinates"][0] == [-100.0, 40.0]
    assert set(route["risk"]["miles_by_level"]) == {
        "low",
        "moderate",
        "high",
        "severe",
        "no_travel",
    }
    assert data["recommendation"]["route_id"] in {r["id"] for r in data["routes"]}
    assert route["departure"].endswith("Z")


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"checkpoint_interval_mi": 15}, "checkpoint_interval_mi"),
        ({"load_weight_lb": 0}, "load_weight_lb"),
        ({"load_weight_lb": 90_000}, "load_weight_lb"),
        ({"departure_time": "2020-01-01T00:00:00Z"}, "departure_time"),
        ({"origin": {"lat": 95, "lon": 0}}, "origin"),
        ({"destination": {"lat": 40.0, "lon": -100.0}}, "destination"),
    ],
)
def test_plan_validation(api: APIClient, overrides, field: str) -> None:
    response = api.post("/api/trips/plan", plan_body(**overrides), format="json")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert field in error["details"]


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (ProviderError("osrm", "HTTP 503"), 502, "provider_unavailable"),
        (NoRouteFound("osrm", "no route"), 422, "no_route"),
        (ProviderRateLimited("open-meteo", "HTTP 429"), 503, "provider_rate_limited"),
    ],
)
def test_provider_failures_map_to_clear_errors(monkeypatch, exc, status, code) -> None:
    class Broken:
        def route(self, waypoints, alternatives):
            raise exc

    cache.clear()
    monkeypatch.setattr("routeiq.api.views.get_container", lambda: container_with(Broken()))
    response = APIClient().post("/api/trips/plan", plan_body(), format="json")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_heatmap(api: APIClient) -> None:
    body = {
        "lines": [[[-100.0, 40.0], [-97.5, 40.0]]],
        "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
        "load_weight_lb": 30000,
    }
    response = api.post("/api/trips/heatmap", body, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["hours"] == 49
    assert len(data["cells"]) == len(data["risk"]) > 0
    assert all(len(row) == 49 for row in data["risk"])


def test_heatmap_rejects_bad_coordinates(api: APIClient) -> None:
    body = {
        "lines": [[[-200.0, 40.0], [-97.5, 40.0]]],
        "departure_time": timezone.now().isoformat(),
        "load_weight_lb": 30000,
    }
    assert api.post("/api/trips/heatmap", body, format="json").status_code == 400


def test_geocode(api: APIClient) -> None:
    assert api.get("/api/geocode", {"q": "Dallas"}).json()["results"][0]["label"] == (
        "Dallas, Texas"
    )
    assert api.get("/api/geocode", {"q": "D"}).status_code == 400
