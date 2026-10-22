# 1. Free, keyless providers behind ports

Date: 2026-10-22 · Status: accepted

## Context
The app needs routing with alternatives, hourly forecasts up to ~3 days out, and geocoding.
Reviewers must be able to run it without signing up for anything.

## Decision
- Routing: OSRM (public demo server, car profile).
- Weather: Open-Meteo forecast API (imperial units, UTC, multi-location requests).
- Geocoding: Photon (OSM data, autocomplete-friendly).

Each is an adapter behind `RoutingProvider`, `WeatherProvider` or `Geocoder` in
`routeiq/ports.py`. Base URLs come from the environment.

## Consequences
- Zero keys to run. A self-hosted OSRM or a paid provider is a config change or a new adapter.
- OSRM's car profile is not truck-aware (no weight or height limits) and is faster than a loaded
  truck. We cap segment speeds at `TRUCK_MAX_SPEED_MPH`. OpenRouteService `driving-hgv` would be
  the next adapter if truck restrictions matter, but its public API only returns alternatives for
  short trips.
- Public OSRM often returns only 1–2 alternatives, so `RouteOptionsService` adds via-point
  detours to reach three distinct routes.
- Open-Meteo's free tier caps location lookups per minute. We batch, cache and snap to 0.1°,
  and report a 429 as a distinct `provider_rate_limited` error.
