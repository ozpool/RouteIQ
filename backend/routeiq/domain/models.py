from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from routeiq.domain.geo import LatLon


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def key(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class Weather:
    wind_mph: float
    gust_mph: float | None
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    point: LatLon


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    """A route as the routing provider returned it; durations are not yet truck-adjusted."""

    points: tuple[LatLon, ...]
    segment_distances_m: tuple[float, ...]
    segment_durations_s: tuple[float, ...]
    summary: str

    @property
    def distance_m(self) -> float:
        return sum(self.segment_distances_m)

    @property
    def duration_s(self) -> float:
        return sum(self.segment_durations_s)


@dataclass(frozen=True, slots=True)
class CheckpointPlacement:
    index: int
    mile: float
    point: LatLon
    eta: datetime
    path_index: int


@dataclass(frozen=True, slots=True)
class Checkpoint:
    placement: CheckpointPlacement
    weather: Weather
    risk: RiskAssessment


@dataclass(frozen=True, slots=True)
class RiskSegment:
    start_mile: float
    end_mile: float
    level: RiskLevel
    points: tuple[LatLon, ...]

    @property
    def miles(self) -> float:
        return self.end_mile - self.start_mile


@dataclass(frozen=True, slots=True)
class RiskSummary:
    miles_by_level: dict[RiskLevel, float]
    average_risk: float
    max_level: RiskLevel
    segments: tuple[RiskSegment, ...]


@dataclass(frozen=True, slots=True)
class RouteAssessment:
    id: str
    label: str
    summary: str
    distance_mi: float
    duration_s: float
    departure: datetime
    arrival: datetime
    checkpoints: tuple[Checkpoint, ...]
    risk: RiskSummary


@dataclass(frozen=True, slots=True)
class Recommendation:
    route_id: str
    ranking: tuple[str, ...]
    reason: str
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TripPlan:
    routes: tuple[RouteAssessment, ...]
    recommendation: Recommendation
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Heatmap:
    start_time: datetime
    hours: int
    cell_size_deg: float
    cells: tuple[LatLon, ...]
    risk: tuple[tuple[int, ...], ...]
