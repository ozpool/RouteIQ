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
            # Over-fetch because duplicate labels are dropped.
            {"q": query, "limit": limit * 2, "lang": "en"},
        )
        places = parse_places(data)[:limit]
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
    """Places in provider order; a city, its county and its boundary often share one label,
    so only the first (most relevant) place per label is kept."""
    places: dict[str, Place] = {}
    try:
        for feature in data["features"]:
            label = _label(feature["properties"])
            if label in places:
                continue
            lon, lat = feature["geometry"]["coordinates"][:2]
            places[label] = Place(label=label, point=LatLon(lat=float(lat), lon=float(lon)))
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise ProviderError(PROVIDER, f"malformed geocoding payload ({exc})") from exc
    return list(places.values())
