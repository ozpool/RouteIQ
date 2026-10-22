# RouteIQ — weather-aware truck routing

RouteIQ helps a truck driver pick the safest route. Enter origin, destination, departure time and
load weight. RouteIQ finds three route options, checks the forecast at every checkpoint **for the
time the truck will be there**, scores the risk with the wind / rain / snow and load rules, and
recommends a route with a one-line reason. A corridor heatmap with a 0–48 hour slider shows how
conditions move along the trip.

React + TypeScript (Vite, MapLibre GL) · Django + DRF · OSRM · Open-Meteo · Photon. No API keys
needed.

## Features

- **3 route options**: router alternatives, plus via-point detours when the router returns
  fewer. Near-duplicates are removed.
- **Checkpoints every 10 / 25 / 50 mi**, each with an ETA from the route's own segment timings,
  capped at a truck speed (65 mph by default).
- **Forecast at ETA**: wind is interpolated between hours; rain and snow use the hour bucket the
  truck is driving through.
- **Risk engine**: the brief's thresholds plus the load rules, with a plain reason for every
  level that is above Low ("Load 42,000 lb raises wind risk High → Severe").
- **Recommendation**: fewest No Travel → Severe → High miles → lowest average risk → shortest
  time, with the deciding criterion shown.
- **Every route, not just the winner**: a comparison table shows each route's miles per risk
  level, average risk, drive time, number of forecast checkpoints and worst condition. Each route
  card opens its own checkpoint weather table; click an open card to close it, so several routes
  can be compared side by side.
- **Map**: the selected route is coloured by risk segment; checkpoints link to the table; other
  routes are dashed and clickable.
- **Corridor heatmap** with a 0–48 h slider (15-minute steps) and a truck marker showing where the
  selected route puts the truck at that time.
- **Trip playback**: ▶ drives the selected route checkpoint by checkpoint in ETA order, opening
  each checkpoint's weather, moving the heatmap to that hour, and stopping when the truck
  arrives.

## Quick start

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20+ with
[pnpm](https://pnpm.io/).

```bash
make setup        # creates .env from .env.example, installs backend + frontend deps
make dev-api      # terminal 1 — Django on 127.0.0.1:8000
make dev-web      # terminal 2 — Vite on http://localhost:5173 (proxies /api)
```

Without make:

```bash
cp .env.example .env
cd backend && uv sync && uv run python manage.py runserver 127.0.0.1:8000
cd frontend && pnpm install && pnpm dev
```

Production-like run (one container serving API + SPA, with Redis):

```bash
cp .env.example .env    # set SECRET_KEY
docker compose up --build    # http://localhost:8080
```

## Configuration

There is one `.env` at the repo root, documented line by line in [`.env.example`](.env.example).

- The backend reads it through a typed `pydantic-settings` class
  ([`backend/config/env.py`](backend/config/env.py)). It is the only code that reads the
  environment. Values are validated at startup, and `APP_ENV=production` refuses to start with a
  missing `SECRET_KEY`, `DEBUG=true`, or `ALLOWED_HOSTS=*`.
- Vite reads the same file (`envDir: ".."`) but only exposes `VITE_*` keys to the browser.
- In production, set real environment variables on the host; `.env` is git-ignored.

## Architecture

```
frontend (React SPA) ──/api──▶ api (DRF views: validate → service → present)
                                   │
                                services: RouteOptions · TripPlanner · CorridorHeatmap
                                   │
                    domain (pure)  │  ports (Protocols)  ◀── adapters: OSRM · Open-Meteo · Photon
                    risk, eta,     │                         + CachedWeatherProvider (Django cache)
                    checkpoints, scoring, recommendation, corridor
```

- [docs/HLD.md](docs/HLD.md): context, flows, key decisions, deployment.
- [docs/LLD.md](docs/LLD.md): modules, types, exact rule tables, API contract.
- [docs/adr/](docs/adr): providers, recommendation order, heatmap rendering.

## How the rules are read

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 – < 35 | 35 – < 45 | 45 – < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 – < 0.25 | 0.25 – < 0.50 | 0.50 – 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 – < 1.0 | 1.0 – < 2.0 | 2.0 – 3.0 | > 3.0 |

Load rules only raise the wind level: 45–54 mph with > 30,000 lb → No Travel; 35–44 mph with
> 40,000 lb → Severe. A checkpoint's level is the worst of wind, rain and snow. Every boundary is
covered by a test in `backend/tests/domain/test_risk.py`.

Assumptions, each one in code and docs:
- Wind = sustained 10 m wind. Gusts are shown but not scored.
- Rain = Open-Meteo `rain + showers`; snow = `snowfall`, both inches over the hour.
- A stretch between two checkpoints takes the worse of their two levels.
- No Travel miles rank before Severe miles (the brief's list starts at Severe).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/geocode?q=` | place autocomplete |
| POST | `/api/trips/plan` | routes, checkpoints, risk, recommendation |
| POST | `/api/trips/heatmap` | corridor cells × 49 hourly risk scores |

Request and response shapes are in [docs/LLD.md §10](docs/LLD.md#10-http-api) and
[`frontend/src/api/types.ts`](frontend/src/api/types.ts). Errors always look like
`{"error": {"code", "message", "details"?}}`.

## Tests and checks

```bash
make test    # 113 backend tests (pytest) + 12 frontend tests (vitest)
make lint    # ruff + TypeScript strict typecheck
```

- Domain: every threshold boundary, load rules, ETA and speed cap, forecast lookup, scoring,
  ranking and tie-breaks.
- Adapters: parsing against **recorded real responses** from OSRM, Open-Meteo and Photon
  (`backend/tests/adapters/fixtures`), plus request-parameter checks.
- Services and API: fake ports (our own interfaces), validation and error mapping.

CI (`.github/workflows/ci.yml`) runs lint, tests, the frontend build and the Docker build.

## Deployment

The `Dockerfile` is multi-stage: pnpm builds the SPA, then a slim Python image runs gunicorn,
and WhiteNoise serves the SPA from the same origin (hashed assets cached as immutable, API
responses gzipped). `render.yaml` is a one-click Render blueprint; any Docker host works.

## Known limits

- OSRM's public car profile ignores truck restrictions (weight, height, hazmat). Durations are
  capped at a truck speed, but routing is not truck-legal routing.
- Forecasts come from public models; skill drops after ~48 h. Departure is limited to the next
  7 days.
- Hours-of-service breaks are not modelled; ETAs assume continuous driving.
- The free Open-Meteo tier limits lookups per minute. Very long trips at 10-mile spacing can hit
  it; the API then returns a clear `provider_rate_limited` error.
