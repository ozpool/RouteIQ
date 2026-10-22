"""HTTP handlers: validate, call one service, present. No business logic here."""

from rest_framework.decorators import api_view, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from routeiq.api.presenters import present_heatmap, present_places, present_trip_plan
from routeiq.api.serializers import GeocodeQuerySerializer, HeatmapSerializer, PlanTripSerializer
from routeiq.container import get_container
from routeiq.services.trip_planner import TripRequest


class GeocodeThrottle(AnonRateThrottle):
    rate = "60/min"


class PlanningThrottle(AnonRateThrottle):
    rate = "20/min"


@api_view(["GET"])
def health(request: Request) -> Response:
    return Response({"status": "ok"})


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
@throttle_classes([PlanningThrottle])
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
@throttle_classes([PlanningThrottle])
def corridor_heatmap(request: Request) -> Response:
    body = HeatmapSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    data = body.validated_data
    heatmap = get_container().heatmap.build(
        data["lines"], data["departure_time"], data["load_weight_lb"]
    )
    return Response(present_heatmap(heatmap))
