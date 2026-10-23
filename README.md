# RouteIQ

Weather-aware truck routing. RouteIQ compares three route options for a trip, reads the forecast
at each checkpoint for the time the truck will reach it, scores the risk from wind, rain, snow
and load weight, and recommends the safest route with a one-line reason. A corridor heatmap with
a 0–48 hour slider shows how conditions change along the way.

- Live app: https://routeiq-fzde.onrender.com (the planner itself is at `/app/`)
- Health check: https://routeiq-fzde.onrender.com/api/health
- Status page: https://stats.uptimerobot.com/T4N5L51NHB

Long trips such as Dallas, TX → Chicago, IL or Seattle, WA → Minneapolis, MN return three
distinct routes; short trips often have only two real options, and the app says so rather than
inventing a third.

## Walkthrough

A short video walkthrough of the app and the main design decisions:

Video link: _to be added_

## Features

- Three route options, each checked against the forecast at every checkpoint's ETA (every 10,
  25 or 50 miles) and scored with the brief's risk and load rules.
- A recommended route with the criterion that decided it and a note on what the load changed.
- A map and sidebar kept in sync: all routes, checkpoint risk and ETAs, one selected route at a
  time.
- A corridor heatmap with a 0–48 hour slider, checkpoint stepping and playback.
- Live form validation and a health endpoint for uptime monitoring.

## Tech stack

- Frontend: React 18, TypeScript, Vite, MapLibre GL, TanStack Query
- Backend: Python 3.12, Django 5, Django REST Framework, httpx, pydantic-settings
- Providers: OSRM (routing), Open-Meteo (weather), Photon (geocoding). No API keys are required.
- Deployment: Docker, gunicorn, WhiteNoise, Render

## Getting started

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 20+ with
[pnpm](https://pnpm.io/).

```bash
make setup      # create .env from .env.example and install dependencies
make dev-api    # Django on http://127.0.0.1:8000
make dev-web    # Vite on http://localhost:5173 (planner at /app/), proxying /api to Django
```

Without make:

```bash
cp .env.example .env
cd backend && uv sync && uv run python manage.py runserver 127.0.0.1:8000
cd frontend && pnpm install && pnpm dev
```

To run the production image locally with Redis:

```bash
cp .env.example .env          # then set SECRET_KEY
docker compose up --build     # http://localhost:8080
```

## Configuration

All settings live in one `.env` file at the repository root and are documented in
[`.env.example`](.env.example); no key is needed for local development. In production, set
`APP_ENV=production` and a `SECRET_KEY`. The app refuses to start with `DEBUG` on or with
`ALLOWED_HOSTS=*`.

## How it works

1. Routes. OSRM returns up to three alternatives. If fewer than three distinct routes come back,
   the API adds detours through points to either side of the midpoint. Routes that overlap an
   accepted one by 80% or more, or are over 1.75 times the fastest, are dropped.
2. Truck ETA. Each road segment takes the longer of the router's time and its distance at the
   truck speed cap.
3. Checkpoints. Placed at mile 0, then every 10, 25 or 50 miles, plus the destination.
4. Weather. One batched Open-Meteo request covers every checkpoint of every route. Rain and snow
   come from the hour the truck is driving through; wind is interpolated between hours. Lookups
   share a grid of about 12 miles and are cached.
5. Risk. Each checkpoint gets a level from the rules below. Its level covers the road from
   halfway back to the previous checkpoint to halfway to the next.
6. Recommendation. Routes are ranked as described below.
7. Heatmap. After the plan returns, the browser requests risk for a band of grid cells around
   the routes for each of the next 49 hours. The slider then only repaints the map; it never
   calls the server.

## Risk rules

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 to < 35 | 35 to < 45 | 45 to < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 to < 0.25 | 0.25 to < 0.50 | 0.50 to 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 to < 1.0 | 1.0 to < 2.0 | 2.0 to 3.0 | > 3.0 |

The brief's ranges share their edges, so each range includes its lower bound; the No Travel
limits keep the brief's strict "greater than".

Load rules apply to wind only and can only raise its level:

| Wind | Load | Result |
|---|---|---|
| ≥ 55 mph | any | No Travel |
| 45 to 54 mph | over 30,000 lb | No Travel |
| 35 to 44 mph | over 40,000 lb | Severe |

A checkpoint's level is the worst of wind (after the load rules), rain and snow. Wind is the
sustained 10 m wind; gusts are shown but not scored. Rain is Open-Meteo's rain plus showers, and
snow is its snowfall, both in inches per hour.

## Route recommendation

Routes are compared on the following, in order, and the first difference decides:

1. Fewest No Travel miles
2. Fewest Severe miles
3. Fewest High miles
4. Least weather exposure, in risk-miles (each mile multiplied by its level, from Moderate = 1 to
   No Travel = 4)
5. Shortest drive time

The response names the deciding criterion, for example "Fewest Severe miles: 0.0 mi vs 37.5 mi
on Route B", and adds a warning when even the best route crosses Severe or No Travel conditions.

Two choices go beyond the brief's wording. No Travel miles are ranked before Severe miles,
because a No Travel stretch is strictly worse. The fourth step compares total risk-miles rather
than a per-mile average, because an average lets a longer detour dilute the same bad miles with
extra Low miles and win despite being hours slower. Average risk is still reported for each route.

## API

| Method | Path | Description | Rate limit per IP |
|---|---|---|---|
| GET, HEAD | `/api/health` | Liveness and status of each integrated service | 120/min |
| GET | `/api/geocode?q=&limit=` | Place search (`q` 2–120 characters, `limit` up to 8) | 60/min |
| POST | `/api/trips/plan` | Routes, checkpoints, risk and recommendation | 20/min |
| POST | `/api/trips/heatmap` | Corridor cells with 49 hourly risk scores | 20/min |

Request and response types are defined in
[`frontend/src/api/types.ts`](frontend/src/api/types.ts).

### Plan a trip

```bash
curl -X POST https://routeiq-fzde.onrender.com/api/trips/plan \
  -H 'Content-Type: application/json' \
  -d '{
    "origin": {"lat": 32.7767, "lon": -96.7970, "label": "Dallas, TX"},
    "destination": {"lat": 41.8781, "lon": -87.6298, "label": "Chicago, IL"},
    "departure_time": "2026-10-24T14:00:00Z",
    "load_weight_lb": 42000,
    "checkpoint_interval_mi": 25
  }'
```

`departure_time` must include a UTC offset and fall between one hour ago and seven days ahead.
`load_weight_lb` must be between 1 and 80,000, `checkpoint_interval_mi` must be 10, 25 or 50,
and the origin and destination must be at least one mile apart.

An excerpt of the response:

```json
{
  "routes": [{
    "id": "a",
    "distance_mi": 966.5,
    "duration_s": 61560,
    "risk": {"exposure": 25.0, "max_level": "moderate"},
    "checkpoints": [{"mile": 25, "eta": "2026-10-24T14:27:00Z", "risk": {"level": "moderate", "load_raised": false}}]
  }],
  "recommendation": {"route_id": "a", "reason": "Least weather exposure: 25.0 risk-mi vs 50.0 risk-mi on Route C."}
}
```

The heatmap endpoint takes the route lines, departure time and load, and returns grid cells with
49 hourly risk scores each. Errors share one shape, `{"error": {"code", "message", "details"}}`:
400 for invalid input, 422 when no route exists, 429 when rate-limited, and 502 or 503 when a
provider is down or out of quota.

## Health check

- `GET or HEAD /api/health` returns the status of each integrated service (OSRM, Open-Meteo, Photon and
the cache). 

## Architecture diagram

[`docs/architecture.png`](docs/architecture.png) shows the request path, how the browser, the
API, the cache and the providers fit together, what one trip does inside the server, the risk
and load rules, how routes are ranked (with a live example), the planner screen, and known
limits. The editable source is
[`docs/architecture.excalidraw`](docs/architecture.excalidraw); open it at
[excalidraw.com](https://excalidraw.com) with File → Open.

## Project structure

```
docs/              architecture diagram (PNG and editable Excalidraw file)
backend/
  config/          settings and typed environment
  routeiq/
    domain/        risk rules, ETA, checkpoints, forecast lookup, scoring, ranking (pure Python)
    ports.py       interfaces for routing, weather and geocoding providers
    adapters/      OSRM, Open-Meteo, Photon, caching, HTTP client, provider status
    services/      route options, trip planner, corridor heatmap
    api/           request validation, response presenters, views, health, error handling
  tests/
frontend/
  index.html       landing page
  app/index.html   planner page
frontend/src/
  api/             HTTP client and API types
  config/          typed environment
  domain/          formatting, risk helpers, playback and truck position
  features/        trip form, route list, map, heatmap control
  hooks/           debounced input, resizable sidebar
  styles/          application stylesheet
```

The backend follows a ports-and-adapters layout: the domain has no Django or HTTP dependencies,
and `backend/routeiq/container.py` is the only place that wires concrete providers.
