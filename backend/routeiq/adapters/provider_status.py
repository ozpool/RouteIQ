"""Outcome of each provider's last real call, for the health endpoint.

Recorded from live traffic so a health check never calls a provider: no quota spent, and a
provider blip cannot make the platform's health check restart the app.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

_KEY = "provider-status:{}"
_TTL_SECONDS = 24 * 3600


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _update(provider: str, **fields: Any) -> None:
    key = _KEY.format(provider)
    try:
        status = cache.get(key) or {"last_success": None, "last_error": None}
        status.update(fields)
        cache.set(key, status, _TTL_SECONDS)
    except Exception:
        # Status is diagnostics only; a cache outage must not fail the user's request.
        logger.warning("could not record %s status", provider, exc_info=True)


def record_success(provider: str) -> None:
    _update(provider, ok=True, last_success=_now())


def record_failure(provider: str, message: str, *, rate_limited: bool) -> None:
    _update(
        provider,
        ok=False,
        rate_limited=rate_limited,
        last_error={"at": _now(), "message": message},
    )


def provider_status(provider: str) -> dict[str, Any]:
    """`status`: unknown (no call since the cache was emptied), ok, rate_limited or failing."""
    recorded = cache.get(_KEY.format(provider))
    if recorded is None:
        return {"status": "unknown", "last_success": None, "last_error": None}
    if recorded.get("ok"):
        status = "ok"
    else:
        status = "rate_limited" if recorded.get("rate_limited") else "failing"
    return {
        "status": status,
        "last_success": recorded["last_success"],
        "last_error": recorded["last_error"],
    }
