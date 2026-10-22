import pytest

from routeiq.domain.models import RiskLevel, Weather
from routeiq.domain.risk import (
    apply_load_rules,
    assess,
    classify_rain,
    classify_snow,
    classify_wind,
)

L, M, H, S, NT = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


def calm(**overrides: float) -> Weather:
    values = {"wind_mph": 5.0, "gust_mph": 8.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0}
    values.update(overrides)
    return Weather(**values)


@pytest.mark.parametrize(
    ("wind", "expected"),
    [(0, L), (24.9, L), (25, M), (34.9, M), (35, H), (44.9, H), (45, S), (54.9, S), (55, NT)],
)
def test_wind_thresholds(wind: float, expected: RiskLevel) -> None:
    assert classify_wind(wind) == expected


@pytest.mark.parametrize(
    ("rain", "expected"),
    [
        (0.0, L),
        (0.09, L),
        (0.10, M),
        (0.24, M),
        (0.25, H),
        (0.49, H),
        (0.50, S),
        (1.00, S),
        (1.01, NT),
    ],
)
def test_rain_thresholds(rain: float, expected: RiskLevel) -> None:
    assert classify_rain(rain) == expected


@pytest.mark.parametrize(
    ("snow", "expected"),
    [(0.0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, NT)],
)
def test_snow_thresholds(snow: float, expected: RiskLevel) -> None:
    assert classify_snow(snow) == expected


@pytest.mark.parametrize(
    ("wind_level", "load", "expected"),
    [
        (S, 30_000, S),
        (S, 30_001, NT),
        (H, 40_000, H),
        (H, 40_001, S),
        (M, 80_000, M),
        (NT, 1_000, NT),
    ],
)
def test_load_rules(wind_level: RiskLevel, load: int, expected: RiskLevel) -> None:
    assert apply_load_rules(wind_level, load) == expected


def test_any_load_at_55_mph_is_no_travel() -> None:
    assert assess(calm(wind_mph=55), load_weight_lb=1_000).level == NT


def test_heavy_load_in_high_wind_becomes_severe_with_reason() -> None:
    result = assess(calm(wind_mph=38), load_weight_lb=42_000)
    assert result.level == S
    assert result.wind == S
    assert any("Load 42,000 lb" in reason for reason in result.reasons)


def test_worst_condition_wins() -> None:
    result = assess(calm(wind_mph=30, rain_in_hr=0.6, snow_in_hr=0.7), load_weight_lb=10_000)
    assert (result.wind, result.rain, result.snow) == (M, S, M)
    assert result.level == S


def test_calm_weather_has_no_reasons() -> None:
    result = assess(calm(), load_weight_lb=45_000)
    assert result.level == L
    assert result.reasons == ()
