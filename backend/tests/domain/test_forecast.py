from datetime import timedelta

import pytest

from routeiq.domain.forecast import ForecastOutOfRange, HourlyForecast, ceil_hour, floor_hour
from routeiq.domain.models import Weather
from tests.factories import DEPARTURE


def forecast() -> HourlyForecast:
    return HourlyForecast(
        start=DEPARTURE,
        hours=(
            Weather(wind_mph=10, gust_mph=15, rain_in_hr=0.0, snow_in_hr=0.0),
            Weather(wind_mph=30, gust_mph=40, rain_in_hr=0.4, snow_in_hr=0.1),
            Weather(wind_mph=20, gust_mph=None, rain_in_hr=0.0, snow_in_hr=0.0),
        ),
    )


def test_wind_is_interpolated_and_precipitation_uses_the_hour_ending_after() -> None:
    weather = forecast().weather_at(DEPARTURE + timedelta(minutes=15))
    assert weather.wind_mph == pytest.approx(15)
    assert weather.gust_mph == pytest.approx(21.25)
    assert weather.rain_in_hr == 0.4
    assert weather.snow_in_hr == 0.1


def test_exact_hour_uses_that_hour() -> None:
    weather = forecast().weather_at(DEPARTURE + timedelta(hours=1))
    assert (weather.wind_mph, weather.rain_in_hr) == (30, 0.4)


def test_missing_gust_stays_missing() -> None:
    assert forecast().weather_at(DEPARTURE + timedelta(minutes=90)).gust_mph is None


@pytest.mark.parametrize("offset", [timedelta(minutes=-1), timedelta(hours=2, minutes=1)])
def test_out_of_range_raises(offset: timedelta) -> None:
    with pytest.raises(ForecastOutOfRange):
        forecast().weather_at(DEPARTURE + offset)


def test_hour_rounding() -> None:
    t = DEPARTURE + timedelta(minutes=10)
    assert floor_hour(t) == DEPARTURE
    assert ceil_hour(t) == DEPARTURE + timedelta(hours=1)
    assert ceil_hour(DEPARTURE) == DEPARTURE
