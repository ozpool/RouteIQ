from datetime import timedelta

import pytest

from routeiq.domain.geo import LatLon
from routeiq.domain.models import RiskLevel, Weather
from routeiq.ports import NoRouteFound, ProviderError
from routeiq.services.heatmap import HEATMAP_HOURS, CorridorHeatmapService
from routeiq.services.route_options import RouteOptionsService, detour_via_points
from routeiq.services.trip_planner import TripPlanner, TripRequest
from tests.factories import CALM, DEPARTURE, straight_candidate
from tests.fakes import FakeRouting, FakeWeather

ORIGIN, DESTINATION = LatLon(40, -100), LatLon(40, -97.5)
STORM = Weather(wind_mph=40, gust_mph=55, rain_in_hr=0.0, snow_in_hr=0.0)


def test_detour_vias_sit_on_both_sides_of_the_line() -> None:
    vias = detour_via_points(ORIGIN, DESTINATION)
    assert len(vias) == 4
    assert (vias[0].lat - 40) * (vias[1].lat - 40) < 0
    assert abs(vias[2].lat - 40) > abs(vias[0].lat - 40)


class TestRouteOptions:
    def test_adds_distinct_detours_until_three(self) -> None:
        routing = FakeRouting(
            primary=[straight_candidate(130, 60, lat=40)],
            detour=lambda via: [straight_candidate(140, 60, lat=round(via.lat, 1))],
        )
        options = RouteOptionsService(routing).find(ORIGIN, DESTINATION)
        assert len(options.candidates) == 3
        assert options.notes == ()

    def test_drops_duplicates_and_slow_detours_and_says_so(self) -> None:
        routing = FakeRouting(
            primary=[straight_candidate(130, 60, lat=40), straight_candidate(130, 60, lat=40)],
            detour=lambda via: [straight_candidate(400, 60, lat=round(via.lat, 1))],
        )
        options = RouteOptionsService(routing).find(ORIGIN, DESTINATION)
        assert len(options.candidates) == 1
        assert "Only 1 distinct route" in options.notes[0]

    def test_failed_detour_is_skipped_not_fatal(self) -> None:
        def flaky(via: LatLon):
            if via.lat > 40:
                raise ProviderError("osrm", "HTTP 503")
            return [straight_candidate(140, 60, lat=round(via.lat, 1))]

        routing = FakeRouting(primary=[straight_candidate(130, 60)], detour=flaky)
        assert len(RouteOptionsService(routing).find(ORIGIN, DESTINATION).candidates) == 3

    def test_no_primary_route_raises(self) -> None:
        with pytest.raises(NoRouteFound):
            RouteOptionsService(FakeRouting(primary=[])).find(ORIGIN, DESTINATION)


class TestTripPlanner:
    def plan(self, weather: FakeWeather, load: float = 20_000):
        fast_stormy = straight_candidate(130, 65, lat=40.0, summary="I-80")
        slow_calm = straight_candidate(140, 55, lat=41.0, summary="US-30")
        routing = FakeRouting(primary=[fast_stormy, slow_calm])
        planner = TripPlanner(RouteOptionsService(routing), weather, truck_max_speed_mph=65)
        return planner.plan(
            TripRequest(
                origin=ORIGIN,
                destination=DESTINATION,
                departure=DEPARTURE + timedelta(minutes=20),
                load_weight_lb=load,
                checkpoint_interval_mi=25,
            )
        )

    def test_avoids_the_route_through_the_storm(self) -> None:
        weather = FakeWeather(lambda p, t: STORM if p.lat < 40.5 else CALM)
        plan = self.plan(weather, load=45_000)

        stormy, calm = plan.routes
        assert stormy.risk.miles_by_level[RiskLevel.SEVERE] == pytest.approx(130, abs=0.5)
        assert calm.risk.max_level == RiskLevel.LOW
        assert plan.recommendation.route_id == calm.id
        assert plan.recommendation.reason.startswith("Fewest Severe miles")
        assert weather.calls == 1

    def test_lighter_load_keeps_wind_at_high(self) -> None:
        weather = FakeWeather(lambda p, t: STORM if p.lat < 40.5 else CALM)
        stormy = self.plan(weather, load=20_000).routes[0]
        assert stormy.risk.max_level == RiskLevel.HIGH

    def test_checkpoints_use_eta_weather(self) -> None:
        # Storm arrives two hours after departure everywhere.
        weather = FakeWeather(lambda p, t: STORM if t >= DEPARTURE + timedelta(hours=2) else CALM)
        route = self.plan(weather).routes[0]
        first, last = route.checkpoints[0], route.checkpoints[-1]
        assert first.risk.level == RiskLevel.LOW
        assert last.placement.eta == route.arrival
        assert last.risk.level == RiskLevel.HIGH
        assert [c.placement.mile for c in route.checkpoints] == pytest.approx(
            [0, 25, 50, 75, 100, 125, 130], abs=0.01
        )


def test_heatmap_has_one_row_per_cell_and_49_hours() -> None:
    weather = FakeWeather(lambda p, t: STORM if t >= DEPARTURE + timedelta(hours=24) else CALM)
    heatmap = CorridorHeatmapService(weather).build(
        [[ORIGIN, DESTINATION]], DEPARTURE + timedelta(minutes=40), load_weight_lb=45_000
    )
    assert heatmap.start_time == DEPARTURE
    assert heatmap.hours == HEATMAP_HOURS + 1
    assert len(heatmap.risk) == len(heatmap.cells) > 0
    row = heatmap.risk[0]
    assert row[0] == RiskLevel.LOW and row[24] == RiskLevel.SEVERE
