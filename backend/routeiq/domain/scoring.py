import itertools
from collections.abc import Sequence

from routeiq.domain.eta import EtaProfile
from routeiq.domain.geo import simplify
from routeiq.domain.models import Checkpoint, RiskLevel, RiskSegment, RiskSummary

# ~30 m: invisible at street zoom, cuts OSRM's full geometry by roughly 5x.
DISPLAY_TOLERANCE_DEG = 0.0003


def _segment(
    profile: EtaProfile, start_mile: float, end_mile: float, level: RiskLevel
) -> RiskSegment:
    start, _, start_index = profile.locate(start_mile)
    end, _, end_index = profile.locate(end_mile)
    path = [start, *profile.points[start_index + 1 : end_index + 1], end]
    return RiskSegment(
        start_mile=start_mile,
        end_mile=end_mile,
        level=level,
        points=tuple(simplify(path, DISPLAY_TOLERANCE_DEG)),
    )


def summarize(checkpoints: Sequence[Checkpoint], profile: EtaProfile) -> RiskSummary:
    """Each checkpoint's level covers the road from halfway back to the previous checkpoint to
    halfway to the next. A storm's miles are then off by at most half an interval at each edge,
    so the 10, 25 and 50 mi intervals agree closely instead of one bad sample tainting both
    neighbouring stretches."""
    miles = [c.placement.mile for c in checkpoints]
    bounds = [miles[0], *((a + b) / 2 for a, b in itertools.pairwise(miles)), miles[-1]]
    segments = tuple(
        _segment(profile, start, end, checkpoint.risk.level)
        for checkpoint, (start, end) in zip(checkpoints, itertools.pairwise(bounds), strict=True)
    )

    miles_by_level = dict.fromkeys(RiskLevel, 0.0)
    for segment in segments:
        miles_by_level[segment.level] += segment.miles

    total = sum(segment.miles for segment in segments)
    weighted = sum(int(segment.level) * segment.miles for segment in segments)
    return RiskSummary(
        miles_by_level=miles_by_level,
        average_risk=weighted / total if total > 0 else 0.0,
        max_level=max(c.risk.level for c in checkpoints),
        segments=segments,
    )
