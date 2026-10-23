"""Risk rules from the brief. Ranges are half-open except the strict '>' No Travel bounds."""

import operator
from collections.abc import Callable

from routeiq.domain.models import RiskAssessment, RiskLevel, Weather

Comparator = Callable[[float, float], bool]

# (upper bound, comparator, level): the first rule whose `value <cmp> bound` holds wins.
_WIND_RULES: tuple[tuple[float, Comparator, RiskLevel], ...] = (
    (25, operator.lt, RiskLevel.LOW),
    (35, operator.lt, RiskLevel.MODERATE),
    (45, operator.lt, RiskLevel.HIGH),
    (55, operator.lt, RiskLevel.SEVERE),
)
_RAIN_RULES: tuple[tuple[float, Comparator, RiskLevel], ...] = (
    (0.10, operator.lt, RiskLevel.LOW),
    (0.25, operator.lt, RiskLevel.MODERATE),
    (0.50, operator.lt, RiskLevel.HIGH),
    (1.00, operator.le, RiskLevel.SEVERE),
)
_SNOW_RULES: tuple[tuple[float, Comparator, RiskLevel], ...] = (
    (0.5, operator.lt, RiskLevel.LOW),
    (1.0, operator.lt, RiskLevel.MODERATE),
    (2.0, operator.lt, RiskLevel.HIGH),
    (3.0, operator.le, RiskLevel.SEVERE),
)

HEAVY_LOAD_NO_TRAVEL_LB = 30_000
HEAVY_LOAD_SEVERE_LB = 40_000


def _classify(value: float, rules: tuple[tuple[float, Comparator, RiskLevel], ...]) -> RiskLevel:
    for bound, compare, level in rules:
        if compare(value, bound):
            return level
    return RiskLevel.NO_TRAVEL


def classify_wind(wind_mph: float) -> RiskLevel:
    return _classify(wind_mph, _WIND_RULES)


def classify_rain(rain_in_hr: float) -> RiskLevel:
    return _classify(rain_in_hr, _RAIN_RULES)


def classify_snow(snow_in_hr: float) -> RiskLevel:
    return _classify(snow_in_hr, _SNOW_RULES)


def apply_load_rules(wind_level: RiskLevel, load_weight_lb: float) -> RiskLevel:
    if wind_level == RiskLevel.SEVERE and load_weight_lb > HEAVY_LOAD_NO_TRAVEL_LB:
        return RiskLevel.NO_TRAVEL
    if wind_level == RiskLevel.HIGH and load_weight_lb > HEAVY_LOAD_SEVERE_LB:
        return RiskLevel.SEVERE
    return wind_level


def assess(weather: Weather, load_weight_lb: float) -> RiskAssessment:
    base_wind = classify_wind(weather.wind_mph)
    wind = apply_load_rules(base_wind, load_weight_lb)
    rain = classify_rain(weather.rain_in_hr)
    snow = classify_snow(weather.snow_in_hr)

    reasons: list[str] = []
    if base_wind > RiskLevel.LOW:
        reasons.append(f"Wind {weather.wind_mph:.1f} mph → {base_wind.label}")
    if wind != base_wind:
        reasons.append(
            f"Load {load_weight_lb:,.0f} lb raises wind risk {base_wind.label} → {wind.label}"
        )
    if rain > RiskLevel.LOW:
        reasons.append(f"Rain {weather.rain_in_hr:.2f} in/hr → {rain.label}")
    if snow > RiskLevel.LOW:
        reasons.append(f"Snow {weather.snow_in_hr:.2f} in/hr → {snow.label}")

    return RiskAssessment(
        level=max(wind, rain, snow),
        wind=wind,
        rain=rain,
        snow=snow,
        reasons=tuple(reasons),
        load_raised=wind != base_wind,
    )
