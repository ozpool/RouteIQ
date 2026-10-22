import logging
import time
from typing import Any

import httpx

from routeiq.ports import ProviderError, ProviderRateLimited

logger = logging.getLogger(__name__)

_RETRY_STATUSES = frozenset({429, 502, 503, 504})
_ATTEMPTS = 3
_BACKOFF_SECONDS = 0.4


def build_client(timeout_seconds: float, user_agent: str) -> httpx.Client:
    return httpx.Client(
        timeout=timeout_seconds,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        transport=httpx.HTTPTransport(retries=2),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict):
        detail = body.get("reason") or body.get("message")
        if detail:
            return f"HTTP {response.status_code}: {detail}"
    return f"HTTP {response.status_code}"


def get_json(
    client: httpx.Client,
    provider: str,
    url: str,
    params: dict[str, Any],
    json_error_statuses: frozenset[int] = frozenset(),
) -> Any:
    """GET and decode JSON. Retries rate limits and gateway errors; raises ProviderError.

    Statuses in `json_error_statuses` return their body so the adapter can read the error code.
    """
    attempt = 0
    while True:
        attempt += 1
        started = time.perf_counter()
        try:
            response = client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise ProviderError(provider, f"request failed ({exc.__class__.__name__})") from exc
        logger.debug(
            "%s %s -> %s in %.0f ms",
            provider,
            url,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        if response.status_code in _RETRY_STATUSES and attempt < _ATTEMPTS:
            time.sleep(_BACKOFF_SECONDS * attempt)
            continue
        if response.status_code == 429:
            raise ProviderRateLimited(provider, _error_detail(response))
        if response.status_code >= 400 and response.status_code not in json_error_statuses:
            raise ProviderError(provider, _error_detail(response))
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(provider, "response was not valid JSON") from exc
