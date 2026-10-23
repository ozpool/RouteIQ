from datetime import timedelta

import pytest
from django.core.cache import cache
from django.core.handlers.wsgi import WSGIHandler
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from routeiq.adapters import provider_status
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


def test_health_reports_every_service_without_calling_providers(api: APIClient) -> None:
    cache.clear()
    body = api.get("/api/health").json()
    assert body["status"] == "ok"
    assert set(body["services"]) == {"routing", "weather", "geocoding", "cache"}
    assert body["services"]["routing"]["provider"] == "OSRM"
    assert body["services"]["weather"]["status"] == "unknown"
    assert body["services"]["cache"] == {
        "backend": "in-memory",
        "used_for": "forecast and geocode responses, provider status",
        "status": "ok",
    }


def test_health_is_degraded_after_a_provider_fails(api: APIClient) -> None:
    cache.clear()
    provider_status.record_success("osrm")
    provider_status.record_failure(
        "open-meteo", "HTTP 429: Hourly API request limit exceeded", rate_limited=True
    )
    body = api.get("/api/health")
    assert body.status_code == 200
    services = body.json()["services"]
    assert body.json()["status"] == "degraded"
    assert services["routing"]["status"] == "ok"
    assert services["routing"]["last_success"] is not None
    assert services["weather"]["status"] == "rate_limited"
    assert services["weather"]["last_error"]["message"].startswith("HTTP 429")
    provider_status.record_success("open-meteo")
    assert api.get("/api/health").json()["status"] == "ok"


def test_health_answers_head_with_the_get_response_minus_the_body(api: APIClient) -> None:
    assert api.head("/api/health").status_code == 200
    # Through the real middleware chain: Django's test client strips HEAD bodies itself and
    # would hide one, so call the WSGI handler directly.
    handler = WSGIHandler()
    environ = APIRequestFactory().head("/api/health").environ
    captured: dict = {}
    body = b"".join(
        handler(
            environ, lambda status, headers: captured.update(status=status, headers=dict(headers))
        )
    )
    assert captured["status"].startswith("200")
    assert body == b""
    assert captured["headers"]["Content-Type"] == "application/json"


def test_plan_returns_routes_checkpoints_and_recommendation(api: APIClient) -> None:
    response = api.post("/api/trips/plan", plan_body(), format="json")
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) == 3
    route = data["routes"][0]
    assert route["checkpoints"][0]["risk"]["level"] == "low"
    assert route["checkpoints"][0]["risk"]["load_raised"] is False
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
        (
            ProviderRateLimited("open-meteo", "HTTP 429: Hourly limit."),
            503,
            "provider_rate_limited",
        ),
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


def test_rate_limit_message_passes_provider_reason(monkeypatch) -> None:
    class Limited:
        def route(self, waypoints, alternatives):
            raise ProviderRateLimited("open-meteo", "HTTP 429: Hourly API request limit exceeded.")

    cache.clear()
    monkeypatch.setattr("routeiq.api.views.get_container", lambda: container_with(Limited()))
    message = (
        APIClient().post("/api/trips/plan", plan_body(), format="json").json()["error"]["message"]
    )
    assert "Hourly API request limit exceeded." in message
