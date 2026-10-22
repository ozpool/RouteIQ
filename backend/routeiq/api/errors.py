import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from routeiq.ports import NoRouteFound, ProviderError, ProviderRateLimited

logger = logging.getLogger(__name__)


def _error(code: str, message: str, http_status: int, details: Any = None) -> Response:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return Response({"error": body}, status=http_status)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, NoRouteFound):
        return _error("no_route", "No drivable route was found between these points.", 422)
    if isinstance(exc, ProviderRateLimited):
        logger.warning("Upstream rate limit: %s", exc)
        return _error(
            "provider_rate_limited",
            f"The {exc.provider} service is rate limiting us. Wait a minute and retry, "
            "or use a wider checkpoint interval for very long trips.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if isinstance(exc, ProviderError):
        logger.warning("Upstream provider failed: %s", exc)
        return _error(
            "provider_unavailable",
            f"The {exc.provider} service is unavailable right now. Please retry shortly.",
            status.HTTP_502_BAD_GATEWAY,
        )
    if isinstance(exc, ValidationError):
        return _error("invalid_request", "Some fields are invalid.", 400, exc.detail)
    if isinstance(exc, APIException):
        response = drf_exception_handler(exc, context)
        if response is not None:
            return _error(exc.default_code, str(exc.detail), response.status_code)
    return None
