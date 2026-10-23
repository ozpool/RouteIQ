"""HTTP handlers: validate, call one service, present. No business logic here."""

from rest_framework.decorators import api_view, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from config.env import get_settings
from routeiq.api.health import health_report
from routeiq.api.presenters import present_heatmap, present_places, present_trip_plan
from routeiq.api.serializers import GeocodeQuerySerializer, HeatmapSerializer, PlanTripSerializer
from routeiq.container import get_container
from routeiq.services.trip_planner import TripRequest


# Each throttle needs its own scope: DRF keys the per-IP counter on the scope, and every
# AnonRateThrottle subclass would otherwise share "anon", so geocode typing used up the plan limit.
class GeocodeThrottle(AnonRateThrottle):
    scope = "geocode"
    rate = "60/min"


class PlanThrottle(AnonRateThrottle):
    scope = "plan"
    rate = "20/min"


class HeatmapThrottle(AnonRateThrottle):
    scope = "heatmap"
    rate = "20/min"


# GET and HEAD share one response; uptime monitors can use HEAD (body dropped by middleware).
@api_view(["GET", "HEAD"])
def health(request: Request) -> Response:
    return Response(health_report(get_settings()))


@api_view(["GET"])
@throttle_classes([GeocodeThrottle])
def geocode(request: Request) -> Response:
    query = GeocodeQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    places = get_container().geocoder.search(
        query.validated_data["q"], query.validated_data["limit"]
    )
    return Response(present_places(places))


@api_view(["POST"])
@throttle_classes([PlanThrottle])
def plan_trip(request: Request) -> Response:
    body = PlanTripSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    data = body.validated_data
    plan = get_container().trip_planner.plan(
        TripRequest(
            origin=data["origin"],
            destination=data["destination"],
            departure=data["departure_time"],
            load_weight_lb=data["load_weight_lb"],
            checkpoint_interval_mi=data["checkpoint_interval_mi"],
        )
    )
    return Response(present_trip_plan(plan))


@api_view(["POST"])
@throttle_classes([HeatmapThrottle])
def corridor_heatmap(request: Request) -> Response:
    body = HeatmapSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    data = body.validated_data
    heatmap = get_container().heatmap.build(
        data["lines"], data["departure_time"], data["load_weight_lb"]
    )
    return Response(present_heatmap(heatmap))
