"""Domain objects → JSON-ready dicts. Coordinates are [lon, lat] like GeoJSON."""

from datetime import datetime
from typing import Any

from routeiq.domain.geo import LatLon
from routeiq.domain.models import (
    Checkpoint,
    Heatmap,
    Place,
    RiskLevel,
    RouteAssessment,
    TripPlan,
)


def _coordinate(point: LatLon) -> list[float]:
    return [round(point.lon, 5), round(point.lat, 5)]


def _time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _checkpoint(checkpoint: Checkpoint) -> dict[str, Any]:
    weather, risk, placement = checkpoint.weather, checkpoint.risk, checkpoint.placement
    return {
        "index": placement.index,
        "mile": round(placement.mile, 1),
        "coordinate": _coordinate(placement.point),
        "eta": _time(placement.eta),
        "weather": {
            "wind_mph": round(weather.wind_mph, 1),
            "gust_mph": None if weather.gust_mph is None else round(weather.gust_mph, 1),
            "rain_in_hr": round(weather.rain_in_hr, 3),
            "snow_in_hr": round(weather.snow_in_hr, 3),
        },
        "risk": {
            "level": risk.level.key,
            "score": int(risk.level),
            "wind": risk.wind.key,
            "rain": risk.rain.key,
            "snow": risk.snow.key,
            "reasons": list(risk.reasons),
        },
    }


def _route(route: RouteAssessment) -> dict[str, Any]:
    return {
        "id": route.id,
        "label": route.label,
        "summary": route.summary,
        "distance_mi": round(route.distance_mi, 1),
        "duration_s": round(route.duration_s),
        "departure": _time(route.departure),
        "arrival": _time(route.arrival),
        "risk": {
            "miles_by_level": {
                level.key: round(route.risk.miles_by_level[level], 1) for level in RiskLevel
            },
            "average": round(route.risk.average_risk, 2),
            "exposure": round(route.risk.exposure, 1),
            "max_level": route.risk.max_level.key,
        },
        "checkpoints": [_checkpoint(c) for c in route.checkpoints],
        "segments": [
            {
                "start_mile": round(segment.start_mile, 1),
                "end_mile": round(segment.end_mile, 1),
                "level": segment.level.key,
                "coordinates": [_coordinate(p) for p in segment.points],
            }
            for segment in route.risk.segments
        ],
    }


def present_trip_plan(plan: TripPlan) -> dict[str, Any]:
    recommendation = plan.recommendation
    return {
        "routes": [_route(route) for route in plan.routes],
        "recommendation": {
            "route_id": recommendation.route_id,
            "ranking": list(recommendation.ranking),
            "reason": recommendation.reason,
            "warnings": list(recommendation.warnings),
        },
        "notes": list(plan.notes),
    }


def present_heatmap(heatmap: Heatmap) -> dict[str, Any]:
    return {
        "start_time": _time(heatmap.start_time),
        "hours": heatmap.hours,
        "cell_size_deg": heatmap.cell_size_deg,
        "cells": [_coordinate(cell) for cell in heatmap.cells],
        "risk": [list(row) for row in heatmap.risk],
    }


def present_places(places: list[Place]) -> dict[str, Any]:
    return {
        "results": [
            {"label": place.label, "lat": place.point.lat, "lon": place.point.lon}
            for place in places
        ]
    }
