"""Input validation at the HTTP boundary. Everything past here trusts its arguments."""

from datetime import UTC, timedelta

from django.utils import timezone
from rest_framework import serializers

from routeiq.domain.checkpoints import ALLOWED_INTERVALS_MI
from routeiq.domain.geo import LatLon, haversine_miles

MAX_LOAD_LB = 80_000
MAX_PAST_DEPARTURE = timedelta(hours=1)
MAX_FUTURE_DEPARTURE = timedelta(days=7)
MIN_TRIP_MI = 1.0
MAX_LINES = 3
MAX_LINE_POINTS = 5000


class PointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        return LatLon(lat=values["lat"], lon=values["lon"])


class _DepartureAndLoad(serializers.Serializer):
    # Inputs without an offset are read as UTC; the SPA always sends one.
    departure_time = serializers.DateTimeField(default_timezone=UTC)
    load_weight_lb = serializers.FloatField(min_value=1, max_value=MAX_LOAD_LB)

    def validate_departure_time(self, value):
        now = timezone.now()
        if value < now - MAX_PAST_DEPARTURE:
            raise serializers.ValidationError("Departure cannot be more than 1 hour in the past.")
        if value > now + MAX_FUTURE_DEPARTURE:
            raise serializers.ValidationError("Departure must be within the next 7 days.")
        return value.astimezone(UTC)


class PlanTripSerializer(_DepartureAndLoad):
    origin = PointSerializer()
    destination = PointSerializer()
    checkpoint_interval_mi = serializers.ChoiceField(choices=ALLOWED_INTERVALS_MI)

    def validate(self, attrs):
        if haversine_miles(attrs["origin"], attrs["destination"]) < MIN_TRIP_MI:
            raise serializers.ValidationError(
                {"destination": "Destination must be at least 1 mile from the origin."}
            )
        return attrs


class _Coordinate(serializers.Field):
    """A GeoJSON-style [lon, lat] pair."""

    def to_internal_value(self, data):
        if (
            not isinstance(data, list)
            or len(data) != 2
            or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in data)
        ):
            raise serializers.ValidationError("Expected a [lon, lat] pair of numbers.")
        lon, lat = (float(v) for v in data)
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise serializers.ValidationError("Coordinate out of range.")
        return LatLon(lat=lat, lon=lon)


class HeatmapSerializer(_DepartureAndLoad):
    lines = serializers.ListField(
        child=serializers.ListField(child=_Coordinate(), min_length=2, max_length=MAX_LINE_POINTS),
        min_length=1,
        max_length=MAX_LINES,
    )


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=120, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=8, default=5)
