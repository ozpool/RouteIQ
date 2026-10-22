from bisect import bisect_right
from itertools import accumulate

from routeiq.domain.geo import METERS_PER_MILE, LatLon, interpolate
from routeiq.domain.models import RouteCandidate


class EtaProfile:
    """Cumulative distance and truck travel time at every vertex of a route."""

    def __init__(self, candidate: RouteCandidate, max_speed_mph: float):
        segment_miles = [d / METERS_PER_MILE for d in candidate.segment_distances_m]
        segment_seconds = [
            max(provider_s, miles / max_speed_mph * 3600)
            for miles, provider_s in zip(segment_miles, candidate.segment_durations_s, strict=True)
        ]
        self.points = candidate.points
        self.cumulative_miles = [0.0, *accumulate(segment_miles)]
        self.cumulative_seconds = [0.0, *accumulate(segment_seconds)]

    @property
    def total_miles(self) -> float:
        return self.cumulative_miles[-1]

    @property
    def total_seconds(self) -> float:
        return self.cumulative_seconds[-1]

    def locate(self, mile: float) -> tuple[LatLon, float, int]:
        """Position, elapsed seconds and index of the segment start vertex at `mile`."""
        mile = min(max(mile, 0.0), self.total_miles)
        i = min(bisect_right(self.cumulative_miles, mile) - 1, len(self.points) - 2)
        start_mile, end_mile = self.cumulative_miles[i], self.cumulative_miles[i + 1]
        span = end_mile - start_mile
        fraction = (mile - start_mile) / span if span > 0 else 0.0
        point = interpolate(self.points[i], self.points[i + 1], fraction)
        seconds = self.cumulative_seconds[i] + fraction * (
            self.cumulative_seconds[i + 1] - self.cumulative_seconds[i]
        )
        return point, seconds, i
