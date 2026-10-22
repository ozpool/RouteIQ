"""Composition root: the only module that knows which concrete adapters are in use."""

from dataclasses import dataclass
from functools import lru_cache

from django.core.cache import cache

from config.env import AppSettings, get_settings
from routeiq.adapters.cached_weather import CachedWeatherProvider
from routeiq.adapters.http import build_client
from routeiq.adapters.open_meteo import OpenMeteoWeatherProvider
from routeiq.adapters.osrm import OsrmRoutingProvider
from routeiq.adapters.photon import PhotonGeocoder
from routeiq.ports import Geocoder
from routeiq.services.heatmap import CorridorHeatmapService
from routeiq.services.route_options import RouteOptionsService
from routeiq.services.trip_planner import TripPlanner


@dataclass(frozen=True)
class Container:
    geocoder: Geocoder
    trip_planner: TripPlanner
    heatmap: CorridorHeatmapService


def build_container(settings: AppSettings) -> Container:
    client = build_client(settings.http_timeout_seconds, settings.http_user_agent)
    weather = CachedWeatherProvider(
        OpenMeteoWeatherProvider(client, settings.open_meteo_base_url),
        cache,
        settings.weather_cache_ttl_seconds,
    )
    routing = OsrmRoutingProvider(client, settings.osrm_base_url)
    return Container(
        geocoder=PhotonGeocoder(
            client, settings.photon_base_url, cache, settings.geocode_cache_ttl_seconds
        ),
        trip_planner=TripPlanner(
            RouteOptionsService(routing),
            weather,
            settings.truck_max_speed_mph,
        ),
        heatmap=CorridorHeatmapService(weather),
    )


@lru_cache
def get_container() -> Container:
    return build_container(get_settings())
