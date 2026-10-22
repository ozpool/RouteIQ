import itertools
from collections.abc import Sequence

from routeiq.domain.eta import EtaProfile
from routeiq.domain.geo import simplify
from routeiq.domain.models import Checkpoint, RiskLevel, RiskSegment, RiskSummary

# ~30 m: invisible at street zoom, cuts OSRM's full geometry by roughly 5x.
DISPLAY_TOLERANCE_DEG = 0.0003


def summarize(checkpoints: Sequence[Checkpoint], profile: EtaProfile) -> RiskSummary:
    segments = []
    for start, end in itertools.pairwise(checkpoints):
        a, b = start.placement, end.placement
        path = [a.point, *profile.points[a.path_index + 1 : b.path_index + 1], b.point]
        segments.append(
            RiskSegment(
                start_mile=a.mile,
                end_mile=b.mile,
                level=max(start.risk.level, end.risk.level),
                points=tuple(simplify(path, DISPLAY_TOLERANCE_DEG)),
            )
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
        segments=tuple(segments),
    )
