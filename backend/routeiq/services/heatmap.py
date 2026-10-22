from collections.abc import Sequence
from datetime import datetime, timedelta

from routeiq.domain.corridor import corridor_cells
from routeiq.domain.forecast import floor_hour
from routeiq.domain.geo import LatLon, simplify
from routeiq.domain.models import Heatmap
from routeiq.domain.risk import assess
from routeiq.ports import WeatherProvider

HEATMAP_HOURS = 48
# ~1 km; corridor cells are ≥ 0.2°, so route detail below this changes nothing.
_CORRIDOR_TOLERANCE_DEG = 0.01


class CorridorHeatmapService:
    def __init__(self, weather: WeatherProvider):
        self._weather = weather

    def build(
        self, lines: Sequence[Sequence[LatLon]], departure: datetime, load_weight_lb: float
    ) -> Heatmap:
        simplified = [simplify(line, _CORRIDOR_TOLERANCE_DEG) for line in lines]
        cell_size, cells = corridor_cells(simplified)
        start = floor_hour(departure)
        hours = [start + timedelta(hours=h) for h in range(HEATMAP_HOURS + 1)]
        forecasts = self._weather.hourly_forecast(cells, hours[0], hours[-1])
        risk = tuple(
            tuple(int(assess(forecast.at_hour(t), load_weight_lb).level) for t in hours)
            for forecast in forecasts
        )
        return Heatmap(
            start_time=start,
            hours=len(hours),
            cell_size_deg=cell_size,
            cells=cells,
            risk=risk,
        )
