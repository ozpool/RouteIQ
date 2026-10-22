from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from routeiq.adapters.http import get_json
from routeiq.domain.forecast import HourlyForecast, ceil_hour, floor_hour
from routeiq.domain.geo import LatLon
from routeiq.domain.models import Weather
from routeiq.ports import ProviderError

PROVIDER = "open-meteo"
HOURLY_VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")
_REQUIRED = ("wind_speed_10m", "rain", "showers", "snowfall")
_HOUR_FORMAT = "%Y-%m-%dT%H:%M"


class OpenMeteoWeatherProvider:
    def __init__(
        self, client: httpx.Client, base_url: str, batch_size: int = 100, max_workers: int = 4
    ):
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._batch_size = batch_size
        self._max_workers = max_workers

    def hourly_forecast(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        start, end = floor_hour(start), ceil_hour(end)
        batches = [
            points[i : i + self._batch_size] for i in range(0, len(points), self._batch_size)
        ]
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            results = pool.map(lambda batch: self._fetch(batch, start, end), batches)
            return [series for batch_result in results for series in batch_result]

    def _fetch(
        self, points: Sequence[LatLon], start: datetime, end: datetime
    ) -> list[HourlyForecast]:
        data = get_json(
            self._client,
            PROVIDER,
            f"{self._base_url}/v1/forecast",
            {
                "latitude": ",".join(f"{p.lat:.4f}" for p in points),
                "longitude": ",".join(f"{p.lon:.4f}" for p in points),
                "hourly": ",".join(HOURLY_VARIABLES),
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "UTC",
                "start_hour": start.strftime(_HOUR_FORMAT),
                "end_hour": end.strftime(_HOUR_FORMAT),
            },
        )
        return parse_forecasts(data, expected_points=len(points), start=start, end=end)


def parse_forecasts(
    data: Any, expected_points: int, start: datetime, end: datetime
) -> list[HourlyForecast]:
    locations = data if isinstance(data, list) else [data]
    if len(locations) != expected_points:
        raise ProviderError(PROVIDER, f"expected {expected_points} locations, got {len(locations)}")
    expected_hours = int((end - start) / timedelta(hours=1)) + 1
    try:
        return [_parse_location(location, start, expected_hours) for location in locations]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError(PROVIDER, f"malformed forecast payload ({exc})") from exc


def _parse_location(location: dict[str, Any], start: datetime, expected_hours: int):
    hourly = location["hourly"]
    times = hourly["time"]
    first = datetime.strptime(times[0], _HOUR_FORMAT).replace(tzinfo=UTC)
    if first != start or len(times) != expected_hours:
        raise ValueError(f"time axis {times[0]} x{len(times)} does not match request")
    for name in _REQUIRED:
        if any(value is None for value in hourly[name]):
            raise ValueError(f"missing {name} values")
    gusts = hourly["wind_gusts_10m"]
    hours = tuple(
        Weather(
            wind_mph=float(hourly["wind_speed_10m"][i]),
            gust_mph=None if gusts[i] is None else float(gusts[i]),
            rain_in_hr=float(hourly["rain"][i]) + float(hourly["showers"][i]),
            snow_in_hr=float(hourly["snowfall"][i]),
        )
        for i in range(len(times))
    )
    return HourlyForecast(start=start, hours=hours)
