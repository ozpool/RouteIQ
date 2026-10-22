from typing import Any

import httpx
from django.core.cache import BaseCache

from routeiq.adapters.http import get_json
from routeiq.domain.geo import LatLon
from routeiq.domain.models import Place
from routeiq.ports import ProviderError

PROVIDER = "photon"
_LABEL_FIELDS = ("name", "city", "state", "country")


class PhotonGeocoder:
    def __init__(self, client: httpx.Client, base_url: str, cache: BaseCache, ttl_seconds: int):
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._cache = cache
        self._ttl = ttl_seconds

    def search(self, query: str, limit: int) -> list[Place]:
        key = f"geo:v1:{limit}:{query.strip().lower()}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = get_json(
            self._client,
            PROVIDER,
            f"{self._base_url}/api/",
            {"q": query, "limit": limit, "lang": "en"},
        )
        places = parse_places(data)
        self._cache.set(key, places, timeout=self._ttl)
        return places


def _label(properties: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in _LABEL_FIELDS:
        value = properties.get(field)
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts)


def parse_places(data: Any) -> list[Place]:
    try:
        return [
            Place(
                label=_label(feature["properties"]),
                point=LatLon(
                    lat=float(feature["geometry"]["coordinates"][1]),
                    lon=float(feature["geometry"]["coordinates"][0]),
                ),
            )
            for feature in data["features"]
        ]
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise ProviderError(PROVIDER, f"malformed geocoding payload ({exc})") from exc
