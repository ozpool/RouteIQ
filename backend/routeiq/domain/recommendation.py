"""Route ranking: the brief's priority order, applied lexicographically.

No Travel miles are ranked ahead of Severe miles: a No Travel stretch is strictly worse than
a Severe one, and the brief's list starts at Severe only because it lists route preferences.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from routeiq.domain.models import Recommendation, RiskLevel, RouteAssessment


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


@dataclass(frozen=True)
class _Criterion:
    win_phrase: str
    tie_phrase: str
    key: Callable[[RouteAssessment], float]
    render: Callable[[float], str]


def _miles_at(level: RiskLevel) -> Callable[[RouteAssessment], float]:
    return lambda route: round(route.risk.miles_by_level[level], 1)


def _miles(value: float) -> str:
    return f"{value:.1f} mi"


CRITERIA: tuple[_Criterion, ...] = (
    _Criterion("Fewest No Travel miles", "No Travel miles", _miles_at(RiskLevel.NO_TRAVEL), _miles),
    _Criterion("Fewest Severe miles", "Severe miles", _miles_at(RiskLevel.SEVERE), _miles),
    _Criterion("Fewest High miles", "High miles", _miles_at(RiskLevel.HIGH), _miles),
    _Criterion(
        "Lowest average risk",
        "average risk",
        lambda route: round(route.risk.average_risk, 2),
        lambda value: f"{value:.2f}",
    ),
    _Criterion(
        "Shortest travel time",
        "travel time",
        lambda route: round(route.duration_s),
        format_duration,
    ),
)


def rank_key(route: RouteAssessment) -> tuple[float, ...]:
    return tuple(criterion.key(route) for criterion in CRITERIA)


def _reason(best: RouteAssessment, runner_up: RouteAssessment) -> str:
    tied: list[str] = []
    for criterion in CRITERIA:
        mine, theirs = criterion.key(best), criterion.key(runner_up)
        if mine == theirs:
            if mine:
                tied.append(criterion.tie_phrase)
            continue
        reason = (
            f"{criterion.win_phrase}: {criterion.render(mine)} vs "
            f"{criterion.render(theirs)} on {runner_up.label}."
        )
        if tied:
            reason = f"Tied on {', '.join(tied)}. {reason}"
        return reason
    return f"All options score the same; {best.label} is listed first."


def _warnings(best: RouteAssessment) -> tuple[str, ...]:
    no_travel = best.risk.miles_by_level[RiskLevel.NO_TRAVEL]
    severe = best.risk.miles_by_level[RiskLevel.SEVERE]
    if no_travel > 0:
        return (
            f"Every option crosses No Travel conditions ({no_travel:.1f} mi on the best route). "
            "Delay departure or wait for conditions to clear.",
        )
    if severe > 0:
        return (f"The recommended route still has {severe:.1f} mi of Severe risk.",)
    return ()


def recommend(routes: Sequence[RouteAssessment]) -> Recommendation:
    ranked = sorted(routes, key=rank_key)
    best = ranked[0]
    reason = _reason(best, ranked[1]) if len(ranked) > 1 else "Only one route option is available."
    return Recommendation(
        route_id=best.id,
        ranking=tuple(route.id for route in ranked),
        reason=reason,
        warnings=_warnings(best),
    )
