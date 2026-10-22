# RouteIQ — Low-Level Design

Companion to [HLD.md](HLD.md). This file describes modules, types, interfaces and the exact
rules the code implements.

## 1. Backend layout (ports and adapters)

```
backend/
├── config/                 Django project: typed env, settings, urls, wsgi
│   ├── env.py              AppSettings (pydantic-settings) — the only place env is read
│   └── settings.py
├── routeiq/
│   ├── domain/             Pure Python. No Django, no HTTP. Fully unit-tested.
│   │   ├── geo.py          LatLon, haversine, bearing, offset, Douglas-Peucker
│   │   ├── models.py       RiskLevel, Weather, RouteCandidate, Checkpoint, RouteAssessment …
│   │   ├── forecast.py     HourlyForecast.weather_at(t)
│   │   ├── risk.py         threshold tables + load rules → RiskAssessment
│   │   ├── eta.py          EtaProfile (truck speed cap, position/time at a mile)
│   │   ├── checkpoints.py  place checkpoints every N miles
│   │   ├── scoring.py      miles per level, average risk, risk segments
│   │   ├── recommendation.py  lexicographic ranking + human reason
│   │   ├── similarity.py   route overlap (dedupe alternatives)
│   │   └── corridor.py     grid cells within the corridor around the routes
│   ├── ports.py            RoutingProvider, WeatherProvider, Geocoder protocols + errors
│   ├── adapters/           osrm.py, open_meteo.py, photon.py, cached_weather.py, http.py
│   ├── services/           route_options.py, trip_planner.py, heatmap.py
│   ├── container.py        composition root: builds adapters + services from AppSettings
│   └── api/                serializers (input), presenters (output), views, urls, errors
└── tests/                  domain/, adapters/ (recorded fixtures), services/ (fake ports), api/
```

Dependency rule: `api → services → domain + ports ← adapters`. The domain imports nothing
from the other layers. Only `container.py` knows concrete adapters.

## 2. Domain types

```python
class RiskLevel(IntEnum):   LOW=0  MODERATE=1  HIGH=2  SEVERE=3  NO_TRAVEL=4

@dataclass(frozen=True) Weather:          wind_mph, gust_mph|None, rain_in_hr, snow_in_hr
@dataclass(frozen=True) RiskAssessment:   level, wind, rain, snow, reasons: tuple[str, ...]
@dataclass(frozen=True) RouteCandidate:   points, segment_distances_m, segment_durations_s, summary
@dataclass(frozen=True) CheckpointPlacement: index, mile, point, eta, path_index
@dataclass(frozen=True) Checkpoint:       placement, weather, risk
@dataclass(frozen=True) RiskSegment:      start_mile, end_mile, level, points
@dataclass(frozen=True) RouteAssessment:  id, label, summary, distance_mi, duration_s, departure,
                                          arrival, checkpoints, segments, miles_by_level,
                                          average_risk, max_level
@dataclass(frozen=True) Recommendation:   route_id, ranking: tuple[str, ...], reason, warnings
```

## 3. Risk rules (`domain/risk.py`)

Each table is a list of upper bounds checked in order. The brief's ranges are read as
half-open intervals, except where the brief uses a strict `>` for No Travel.

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | `< 25` | `< 35` | `< 45` | `< 55` | `>= 55` |
| Rain (in/hr) | `< 0.10` | `< 0.25` | `< 0.50` | `<= 1.00` | `> 1.00` |
| Snow (in/hr) | `< 0.5` | `< 1.0` | `< 2.0` | `<= 3.0` | `> 3.0` |

Load rules are applied to the wind level only, and only raise it:

| Wind | Load | Result |
|---|---|---|
| `>= 55` | any | No Travel |
| `45–54` | `> 30,000 lb` | No Travel |
| `35–44` | `> 40,000 lb` | Severe |

Checkpoint level = `max(wind_after_load, rain, snow)`. Every rule that fired is recorded in
`reasons`, so the UI can say *why* a checkpoint is Severe.

Inputs: sustained 10 m wind (gusts are shown, not scored); rain = Open-Meteo
`rain + showers`; snow = `snowfall` (both in inches over the hour).

## 4. ETA and checkpoints

- `EtaProfile` turns a `RouteCandidate` into cumulative miles and cumulative seconds per
  vertex. Each segment's duration is `max(provider_duration, distance / truck_max_speed)`, so
  a car-profile router never makes a truck faster than the cap.
- `position_at(mile)` binary-searches the vertex and interpolates position and time linearly
  inside the segment.
- Checkpoints sit at mile `0, N, 2N, …` plus the destination (`N ∈ {10, 25, 50}`).
  `eta = departure + seconds_at(mile)`.

## 5. Forecast lookup (`domain/forecast.py`)

Open-Meteo reports precipitation as the total of the *preceding* hour, and wind as an
instant value at the hour.

- Precipitation at time `t` → the bucket that ends at `ceil_hour(t)`.
- Wind at time `t` → linear interpolation between `floor_hour(t)` and `ceil_hour(t)`.
- A time outside the series raises `ForecastOutOfRange`; it is never silently clamped.

## 6. Scoring (`domain/scoring.py`)

- Segment `i` runs from checkpoint `i` to `i+1`; its level is the worse of the two.
- `miles_by_level[level]` = sum of segment lengths at that level.
- `average_risk` = distance-weighted mean of segment levels (0.0 – 4.0).

## 7. Recommendation (`domain/recommendation.py`)

Routes are sorted by this tuple (smaller wins), with rounding so float noise never decides:

1. No Travel miles (rounded to 0.1 mi) — extension, see HLD §5
2. Severe miles (0.1 mi)
3. High miles (0.1 mi)
4. Average risk (0.01)
5. Duration (seconds)

The reason names the first key where the winner beats the runner-up, e.g.
*"Fewest Severe miles: 0.0 mi vs 37.5 mi on Route B."* A warning is added when even the
winner crosses No Travel or Severe conditions.

## 8. Services

**RouteOptionsService.find(origin, destination) → list[RouteCandidate]**
1. Ask the provider for up to 3 alternatives.
2. While fewer than 3 distinct routes: route through a via-point offset perpendicular to the
   origin→destination line at the midpoint (±15%, then ±30% of the straight distance,
   clamped 10–120 mi). Detour attempts run in parallel.
3. A candidate is a duplicate when its grid-cell overlap (Jaccard on 0.02° cells) with an
   accepted route is ≥ 0.8. Candidates longer than 1.75 × the fastest route are dropped.
4. If geography allows fewer than 3, return what exists and add a note; never fabricate.

**TripPlanner.plan(request) → TripPlan**
routes → EtaProfiles → checkpoints → one `WeatherProvider.hourly_forecast` call for all
checkpoint points → `assess` → `summarize` → `recommend`.

**CorridorHeatmapService.build(lines, departure, load) → Heatmap**
`corridor.cells(lines)` → one forecast call for hours `departure … departure + 48h` →
`risk[cell][hour]`.

## 9. Ports

```python
class RoutingProvider(Protocol):
    def route(self, waypoints: Sequence[LatLon], alternatives: int) -> list[RouteCandidate]: ...

class WeatherProvider(Protocol):
    def hourly_forecast(self, points: Sequence[LatLon], start: datetime, end: datetime
                        ) -> list[HourlyForecast]: ...   # same order as points

class Geocoder(Protocol):
    def search(self, query: str, limit: int) -> list[Place]: ...
```

Errors: `ProviderError` (upstream down / bad payload → HTTP 502), `NoRouteFound` (→ 422).

`CachedWeatherProvider` decorates any `WeatherProvider`: it rounds points to 0.01°, stores one
series per point and UTC day in the Django cache (`WEATHER_CACHE_TTL_SECONDS`), and only sends
the missing points upstream. `OpenMeteoWeatherProvider` batches 100 points per call and runs
batches in parallel.

## 10. HTTP API

| Method | Path | Body / query | Response |
|---|---|---|---|
| GET | `/api/health` | — | `{status}` |
| GET | `/api/geocode` | `q` (2–120 chars), `limit` ≤ 8 | `{results: [{label, lat, lon}]}` |
| POST | `/api/trips/plan` | origin, destination `{lat, lon, label}`, `departure_time` (ISO 8601 with offset, now−1h … now+7d), `load_weight_lb` (1 – 80,000), `checkpoint_interval_mi` ∈ {10, 25, 50} | `{routes[], recommendation, notes[]}` |
| POST | `/api/trips/heatmap` | `lines` (1–3 × ≤ 5000 `[lon, lat]`), `departure_time`, `load_weight_lb` | `{start_time, hours, cell_size_deg, cells[[lon,lat]], risk[[int×49]]}` |

Errors share one shape: `{"error": {"code", "message", "details"?}}`.

## 11. Frontend layout

```
frontend/src/
├── config/env.ts            typed import.meta.env
├── api/                     client (fetch + ApiError), types, trips (plan, heatmap, geocode)
├── domain/                  risk colours/labels, formatters, truck position along a route
├── features/
│   ├── trip-form/           TripForm, PlaceInput (debounced geocode autocomplete)
│   ├── routes/              RouteList, RouteCard, CheckpointList
│   ├── map/                 TripMap, layer specs, GeoJSON builders, CheckpointPopup
│   └── heatmap/             HeatmapControl (slider + play), grid GeoJSON builder
├── hooks/useDebouncedValue.ts
└── App.tsx                  page state: plan result, selected route, heatmap hour
```

Rendering rules for smoothness:
- Every GeoJSON collection is built once per API response (`useMemo`), never per slider tick.
- Heatmap cells are fill polygons carrying `h0 … h48`; the slider only changes the layer's
  `fill-color` expression (`['match', ['get', 'h<hour>'], …]`).
- Checkpoints are a GL circle layer, not DOM markers; one popup is shown on click.
- The selected route is drawn per risk segment; other routes are dimmed.
