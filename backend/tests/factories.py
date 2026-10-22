"""Small builders for domain objects used across test modules."""

from datetime import UTC, datetime, timedelta

from routeiq.domain.forecast import HourlyForecast
from routeiq.domain.geo import METERS_PER_MILE, LatLon
from routeiq.domain.models import (
    Checkpoint,
    CheckpointPlacement,
    RiskLevel,
    RiskSummary,
    RouteAssessment,
    RouteCandidate,
    Weather,
)
from routeiq.domain.risk import assess

DEPARTURE = datetime(2026, 1, 10, 8, 0, tzinfo=UTC)
CALM = Weather(wind_mph=5.0, gust_mph=9.0, rain_in_hr=0.0, snow_in_hr=0.0)


def straight_candidate(
    miles: float, mph: float, segments: int = 10, lat: float = 40.0, summary: str = "I-80"
) -> RouteCandidate:
    """An east-west route of `segments` equal pieces at a constant provider speed."""
    degrees = miles / (69.172 * 0.766)  # ≈ miles per degree of longitude at 40° N
    points = tuple(LatLon(lat, -100 + degrees * i / segments) for i in range(segments + 1))
    seg_m = miles * METERS_PER_MILE / segments
    seg_s = miles / mph * 3600 / segments
    return RouteCandidate(
        points=points,
        segment_distances_m=(seg_m,) * segments,
        segment_durations_s=(seg_s,) * segments,
        summary=summary,
    )


def flat_forecast(weather: Weather = CALM, hours: int = 72, start: datetime = DEPARTURE):
    return HourlyForecast(start=start, hours=(weather,) * hours)


def checkpoint(index: int, mile: float, level_weather: Weather, path_index: int = 0) -> Checkpoint:
    return Checkpoint(
        placement=CheckpointPlacement(
            index=index,
            mile=mile,
            point=LatLon(40, -100 + mile / 53),
            eta=DEPARTURE + timedelta(hours=mile / 60),
            path_index=path_index,
        ),
        weather=level_weather,
        risk=assess(level_weather, load_weight_lb=20_000),
    )


def route(
    route_id: str,
    duration_h: float,
    *,
    no_travel: float = 0.0,
    severe: float = 0.0,
    high: float = 0.0,
    average: float = 0.0,
) -> RouteAssessment:
    miles = dict.fromkeys(RiskLevel, 0.0)
    miles[RiskLevel.NO_TRAVEL] = no_travel
    miles[RiskLevel.SEVERE] = severe
    miles[RiskLevel.HIGH] = high
    return RouteAssessment(
        id=route_id,
        label=f"Route {route_id.upper()}",
        summary="",
        distance_mi=100,
        duration_s=duration_h * 3600,
        departure=DEPARTURE,
        arrival=DEPARTURE + timedelta(hours=duration_h),
        checkpoints=(),
        risk=RiskSummary(
            miles_by_level=miles,
            average_risk=average,
            max_level=RiskLevel.LOW,
            segments=(),
        ),
    )
