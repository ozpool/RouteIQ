from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.cache import BaseCache

from routeiq.domain.forecast import HourlyForecast, ceil_hour, floor_hour
from routeiq.domain.geo import LatLon
from routeiq.domain.models import Weather
from routeiq.ports import WeatherProvider

_KEY_VERSION = "v2"
# 0.1° (~7 mi) is about the forecast model's own grid beyond its first day. Snapping to it lets
# nearby checkpoints and overlapping routes share one upstream lookup, which keeps long trips
# under Open-Meteo's per-minute location quota.
_PRECISION = 1

_Row = tuple[float, float | None, float, float]


def _to_row(w: Weather) -> _Row:
    return (w.wind_mph, w.gust_mph, w.rain_in_hr, w.snow_in_hr)


def _from_row(row: _Row) -> Weather:
    return Weather(wind_mph=row[0], gust_mph=row[1], rain_in_hr=row[2], snow_in_hr=row[3])


class CachedWeatherProvider:
    """Caches one 24-hour UTC day per rounded point and only fetches what is missing."""

    def __init__(self, inner: WeatherProvider, cache: BaseCache, ttl_seconds: int):
        self._inner = inner
        self._cache = cache
        self._ttl = ttl_seconds

    @staticmethod
    def _key(point: LatLon, day: date) -> str:
        return f"wx:{_KEY_VERSION}:{point.lat:.{_PRECISION}f}:{point.lon:.{_PRECISION}f}:{day}"

    def hourly_forecast(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        start, end = floor_hour(start), ceil_hour(end)
        days = [
            start.date() + timedelta(days=i) for i in range((end.date() - start.date()).days + 1)
        ]
        rounded = [p.rounded(_PRECISION) for p in points]
        unique = list(dict.fromkeys(rounded))

        keys = {(p, d): self._key(p, d) for p in unique for d in days}
        found: dict[str, Any] = self._cache.get_many(keys.values())
        missing = [p for p in unique if any(keys[p, d] not in found for d in days)]

        if missing:
            first_hour = datetime.combine(days[0], time(0), tzinfo=start.tzinfo)
            last_hour = datetime.combine(days[-1], time(23), tzinfo=start.tzinfo)
            fetched = self._inner.hourly_forecast(missing, first_hour, last_hour)
            fresh: dict[str, list[_Row]] = {}
            for point, series in zip(missing, fetched, strict=True):
                rows = [_to_row(w) for w in series.hours]
                for i, day in enumerate(days):
                    fresh[keys[point, day]] = rows[i * 24 : (i + 1) * 24]
            self._cache.set_many(fresh, timeout=self._ttl)
            found.update(fresh)

        offset = int(
            (start - datetime.combine(days[0], time(0), tzinfo=start.tzinfo)).total_seconds()
            // 3600
        )
        length = int((end - start).total_seconds() // 3600) + 1
        by_point = {}
        for point in unique:
            rows = [row for day in days for row in found[keys[point, day]]]
            hours = tuple(_from_row(row) for row in rows[offset : offset + length])
            by_point[point] = HourlyForecast(start=start, hours=hours)
        return [by_point[p] for p in rounded]
