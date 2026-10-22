import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, useState } from "react";
import { ApiError } from "./api/client";
import { fetchHeatmap, planTrip } from "./api/trips";
import type { Place, PlanTripRequest, TripPlan } from "./api/types";
import { truckStateAt } from "./domain/truckPosition";
import { HeatmapControl, heatmapHourTime } from "./features/heatmap/HeatmapControl";
import { routeLine, thinLine } from "./features/map/geojson";
import { TripMap } from "./features/map/TripMap";
import { RouteList } from "./features/routes/RouteList";
import { TripForm } from "./features/trip-form/TripForm";

// The heatmap endpoint accepts up to 5000 points per line; the corridor grid is far coarser.
const HEATMAP_LINE_POINTS = 1500;

interface PlannedTrip {
  id: number;
  request: PlanTripRequest;
  plan: TripPlan;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

export function App() {
  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [trip, setTrip] = useState<PlannedTrip | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [activeCheckpoint, setActiveCheckpoint] = useState<number | null>(null);
  const [heatmapHour, setHeatmapHour] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const tripCounter = useRef(0);

  const planning = useMutation({
    mutationFn: (request: PlanTripRequest) => planTrip(request),
    onSuccess: (plan, request) => {
      setTrip({ id: ++tripCounter.current, request, plan });
      setSelectedRouteId(plan.recommendation.route_id);
      setActiveCheckpoint(null);
      setHeatmapHour(0);
    },
  });

  const heatmapQuery = useQuery({
    queryKey: ["heatmap", trip?.id],
    enabled: trip !== null,
    staleTime: Infinity,
    queryFn: ({ signal }) => {
      if (!trip) throw new Error("heatmap requested without a trip");
      return fetchHeatmap(
        {
          lines: trip.plan.routes.map((route) => thinLine(routeLine(route), HEATMAP_LINE_POINTS)),
          departure_time: trip.request.departure_time,
          load_weight_lb: trip.request.load_weight_lb,
        },
        signal,
      );
    },
  });

  const plan = trip?.plan;
  const heatmap = heatmapQuery.data;
  const selectedRoute = plan?.routes.find((route) => route.id === selectedRouteId);

  const truck = useMemo(
    () => (selectedRoute && heatmap ? truckStateAt(selectedRoute, heatmapHourTime(heatmap, heatmapHour)) : null),
    [selectedRoute, heatmap, heatmapHour],
  );

  const selectRoute = useCallback((routeId: string) => {
    setSelectedRouteId(routeId);
    setActiveCheckpoint(null);
  }, []);

  return (
    <div className="app">
      <aside className="panel">
        <header className="panel__header">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <div>
            <h1>RouteIQ</h1>
            <p>Weather-aware truck routing</p>
          </div>
        </header>

        <TripForm
          isSubmitting={planning.isPending}
          onSubmit={(request) => planning.mutate(request)}
          origin={origin}
          destination={destination}
          onOriginChange={setOrigin}
          onDestinationChange={setDestination}
        />

        {planning.isError && (
          <p className="alert alert--error" role="alert">
            {errorMessage(planning.error)}
          </p>
        )}

        {plan ? (
          <RouteList
            plan={plan}
            selectedRouteId={selectedRouteId}
            onSelectRoute={selectRoute}
            activeCheckpoint={activeCheckpoint}
            onSelectCheckpoint={setActiveCheckpoint}
          />
        ) : (
          !planning.isPending && (
            <p className="empty-state">
              Enter a trip to compare three routes by the forecast the truck will actually drive
              into — sampled at each checkpoint's ETA and scored for your load.
            </p>
          )
        )}
      </aside>

      <main className="map-area">
        <TripMap
          plan={plan}
          origin={trip ? trip.request.origin : origin}
          destination={trip ? trip.request.destination : destination}
          selectedRouteId={selectedRouteId}
          onSelectRoute={selectRoute}
          activeCheckpoint={activeCheckpoint}
          onSelectCheckpoint={setActiveCheckpoint}
          heatmap={heatmap}
          heatmapHour={heatmapHour}
          showHeatmap={showHeatmap}
          truck={truck}
        />
        {planning.isPending && <div className="map-area__loading" aria-hidden="true" />}
        <HeatmapControl
          heatmap={heatmap}
          isLoading={heatmapQuery.isFetching}
          error={heatmapQuery.isError ? errorMessage(heatmapQuery.error) : null}
          hour={heatmapHour}
          onHourChange={setHeatmapHour}
          isVisible={showHeatmap}
          onVisibleChange={setShowHeatmap}
          truck={truck}
        />
      </main>
    </div>
  );
}
