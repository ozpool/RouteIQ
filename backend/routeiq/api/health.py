"""Body of GET /api/health: liveness plus the state of every service the app depends on.

The endpoint always answers 200 so the platform health check keeps the app up; monitors alert
on `"status": "degraded"` instead. No provider is called from here (see provider_status).
"""

import logging
from datetime import UTC, datetime
from typing import Any

from django.core.cache import cache

from config.env import AppSettings
from routeiq.adapters import open_meteo, osrm, photon, provider_status

logger = logging.getLogger(__name__)

_PROBLEM_STATES = frozenset({"failing", "rate_limited"})


def _provider(
    provider: str, name: str, used_for: str, base_url: str, **extra: Any
) -> dict[str, Any]:
    try:
        state = provider_status.provider_status(provider)
    except Exception:
        # The cache is down; the cache entry below already reports that.
        logger.warning("could not read %s status", provider, exc_info=True)
        state = {"status": "unknown", "last_success": None, "last_error": None}
    return {"provider": name, "used_for": used_for, "base_url": base_url, **extra, **state}


def _cache(settings: AppSettings) -> dict[str, Any]:
    try:
        cache.set("health:probe", "ok", 10)
        is_up = cache.get("health:probe") == "ok"
    except Exception:
        logger.warning("cache probe failed", exc_info=True)
        is_up = False
    return {
        "backend": "redis" if settings.cache_url else "in-memory",
        "used_for": "forecast and geocode responses, provider status",
        "status": "ok" if is_up else "down",
    }


def health_report(settings: AppSettings) -> dict[str, Any]:
    services = {
        "routing": _provider(
            osrm.PROVIDER, "OSRM", "route alternatives and segment timings", settings.osrm_base_url
        ),
        "weather": _provider(
            open_meteo.PROVIDER,
            "Open-Meteo",
            "hourly forecast at checkpoints and heatmap cells",
            settings.open_meteo_base_url,
            api_key_configured=bool(settings.open_meteo_api_key.get_secret_value()),
        ),
        "geocoding": _provider(
            photon.PROVIDER,
            "Photon",
            "place search for origin and destination",
            settings.photon_base_url,
        ),
        "cache": _cache(settings),
    }
    is_degraded = services["cache"]["status"] != "ok" or any(
        services[name]["status"] in _PROBLEM_STATES for name in ("routing", "weather", "geocoding")
    )
    return {
        "status": "degraded" if is_degraded else "ok",
        "time": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "environment": settings.app_env,
        "services": services,
    }
