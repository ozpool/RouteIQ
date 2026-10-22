import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from routeiq.domain.models import Weather


class ForecastOutOfRange(LookupError):
    pass


def floor_hour(t: datetime) -> datetime:
    return t.replace(minute=0, second=0, microsecond=0)


def ceil_hour(t: datetime) -> datetime:
    floored = floor_hour(t)
    return floored if floored == t else floored + timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    """`hours[i]` is the forecast for `start + i hours` (UTC, hour aligned).

    Precipitation values are totals for the hour *ending* at that time; wind is instantaneous.
    """

    start: datetime
    hours: tuple[Weather, ...]

    @property
    def end(self) -> datetime:
        return self.start + timedelta(hours=len(self.hours) - 1)

    def _index(self, t: datetime) -> float:
        return (t - self.start).total_seconds() / 3600

    def at_hour(self, t: datetime) -> Weather:
        index = self._index(t)
        if index != int(index) or not 0 <= index < len(self.hours):
            raise ForecastOutOfRange(f"No hourly forecast for {t.isoformat()}")
        return self.hours[int(index)]

    def weather_at(self, t: datetime) -> Weather:
        index = self._index(t)
        lower, upper = math.floor(index), math.ceil(index)
        if lower < 0 or upper >= len(self.hours):
            raise ForecastOutOfRange(
                f"{t.isoformat()} is outside {self.start.isoformat()}..{self.end.isoformat()}"
            )
        before, after = self.hours[lower], self.hours[upper]
        fraction = index - lower

        def blend(a: float, b: float) -> float:
            return a + (b - a) * fraction

        gust = (
            blend(before.gust_mph, after.gust_mph)
            if before.gust_mph is not None and after.gust_mph is not None
            else None
        )
        return Weather(
            wind_mph=blend(before.wind_mph, after.wind_mph),
            gust_mph=gust,
            rain_in_hr=after.rain_in_hr,
            snow_in_hr=after.snow_in_hr,
        )
