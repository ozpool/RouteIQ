from dataclasses import dataclass
from datetime import datetime, timedelta
from string import ascii_uppercase

from routeiq.domain.checkpoints import place_checkpoints
from routeiq.domain.eta import EtaProfile
from routeiq.domain.geo import LatLon
from routeiq.domain.models import Checkpoint, RouteAssessment, TripPlan
from routeiq.domain.recommendation import recommend
from routeiq.domain.risk import assess
from routeiq.domain.scoring import summarize
from routeiq.ports import WeatherProvider
from routeiq.services.route_options import RouteOptionsService


@dataclass(frozen=True, slots=True)
class TripRequest:
    origin: LatLon
    destination: LatLon
    departure: datetime
    load_weight_lb: float
    checkpoint_interval_mi: int


class TripPlanner:
    def __init__(
        self,
        route_options: RouteOptionsService,
        weather: WeatherProvider,
        truck_max_speed_mph: float,
    ):
        self._route_options = route_options
        self._weather = weather
        self._truck_max_speed_mph = truck_max_speed_mph

    def plan(self, request: TripRequest) -> TripPlan:
        options = self._route_options.find(request.origin, request.destination)
        profiles = [EtaProfile(c, self._truck_max_speed_mph) for c in options.candidates]
        placements = [
            place_checkpoints(profile, request.checkpoint_interval_mi, request.departure)
            for profile in profiles
        ]

        # One batched forecast call for every checkpoint of every route.
        flat = [placement for route in placements for placement in route]
        latest_eta = max(placement.eta for placement in flat)
        forecasts = iter(
            self._weather.hourly_forecast([p.point for p in flat], request.departure, latest_eta)
        )

        routes = []
        for index, (candidate, profile, route_placements) in enumerate(
            zip(options.candidates, profiles, placements, strict=True)
        ):
            checkpoints = []
            for placement in route_placements:
                weather = next(forecasts).weather_at(placement.eta)
                checkpoints.append(
                    Checkpoint(
                        placement=placement,
                        weather=weather,
                        risk=assess(weather, request.load_weight_lb),
                    )
                )
            letter = ascii_uppercase[index]
            routes.append(
                RouteAssessment(
                    id=letter.lower(),
                    label=f"Route {letter}",
                    summary=candidate.summary,
                    distance_mi=profile.total_miles,
                    duration_s=profile.total_seconds,
                    departure=request.departure,
                    arrival=request.departure + timedelta(seconds=profile.total_seconds),
                    checkpoints=tuple(checkpoints),
                    risk=summarize(checkpoints, profile),
                )
            )

        return TripPlan(
            routes=tuple(routes),
            recommendation=recommend(routes),
            notes=options.notes,
        )
