import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { ApiError } from "./api/client";
import { fetchHeatmap, planTrip } from "./api/trips";
import type { Place, PlanTripRequest, TripPlan } from "./api/types";
import { HeatmapControl } from "./features/heatmap/HeatmapControl";
import { usePlayback } from "./features/heatmap/usePlayback";
import { routeLine, thinLine } from "./features/map/geojson";
import { TripMap } from "./features/map/TripMap";
import { RouteList } from "./features/routes/RouteList";
import { TripForm } from "./features/trip-form/TripForm";
import { useResizablePanel } from "./hooks/useResizablePanel";

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
  // Whether the selected route's card shows its checkpoint table; only that card can be open.
  const [isRouteOpen, setRouteOpen] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const tripCounter = useRef(0);
  const panel = useResizablePanel();

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
  // Reaching a checkpoint (map click, ⏮ / ⏭, playback) reopens the card so its row is visible.
  const showCheckpoint = useCallback((index: number) => {
    setActiveCheckpoint(index);
    setRouteOpen(true);
  }, []);
  const playback = usePlayback(selectedRoute, heatmap, showCheckpoint);
  const { pause, reset } = playback;

  const planning = useMutation({
    mutationFn: (request: PlanTripRequest) => planTrip(request),
    onSuccess: (plan, request) => {
      setTrip({ id: ++tripCounter.current, request, plan });
      setSelectedRouteId(plan.recommendation.route_id);
      setActiveCheckpoint(null);
      setRouteOpen(true);
      reset();
    },
  });

  const selectRoute = useCallback(
    (routeId: string) => {
      setSelectedRouteId(routeId);
      setActiveCheckpoint(null);
      setRouteOpen(true);
      pause();
    },
    [pause],
  );

  // A card click: another route is selected and opened; the selected route's card opens or closes.
  const toggleRouteCard = useCallback(
    (routeId: string) => {
      if (routeId === selectedRouteId) setRouteOpen((open) => !open);
      else selectRoute(routeId);
    },
    [selectedRouteId, selectRoute],
  );

  const selectCheckpoint = useCallback(
    (routeId: string, index: number) => {
      if (routeId !== selectedRouteId) selectRoute(routeId);
      pause();
      setActiveCheckpoint(index);
    },
    [selectedRouteId, selectRoute, pause],
  );

  const selectMapCheckpoint = useCallback(
    (index: number | null) => {
      pause();
      if (index === null) setActiveCheckpoint(null);
      else showCheckpoint(index);
    },
    [pause, showCheckpoint],
  );

  return (
    <div
      ref={panel.containerRef}
      className={`app${panel.isResizing ? " is-resizing" : ""}`}
      style={panel.containerStyle}
    >
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
          onSubmit={planning.mutate}
          origin={origin}
          destination={destination}
          onOriginChange={setOrigin}
          onDestinationChange={setDestination}
        />

        {planning.isPending && (
          <p className="status" role="status">
            Finding three routes and checking the forecast at every checkpoint. Long trips can take
            up to 20 seconds.
          </p>
        )}

        {planning.isError && (
          <p className="alert alert--error" role="alert">
            {errorMessage(planning.error)}
            {plan && " The routes below are from your previous search."}
          </p>
        )}

        {trip ? (
          <RouteList
            key={trip.id}
            plan={trip.plan}
            loadWeightLb={trip.request.load_weight_lb}
            selectedRouteId={selectedRouteId}
            onSelectRoute={selectRoute}
            isSelectedOpen={isRouteOpen}
            onToggleRoute={toggleRouteCard}
            activeCheckpoint={activeCheckpoint}
            onSelectCheckpoint={selectCheckpoint}
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

      <div className="panel-resizer" {...panel.handleProps} />

      <main className="map-area">
        <TripMap
          plan={plan}
          origin={trip ? trip.request.origin : origin}
          destination={trip ? trip.request.destination : destination}
          selectedRouteId={selectedRouteId}
          onSelectRoute={selectRoute}
          activeCheckpoint={activeCheckpoint}
          onSelectCheckpoint={selectMapCheckpoint}
          heatmap={heatmap}
          heatmapHour={playback.heatmapHour}
          showHeatmap={showHeatmap}
          truck={playback.truck}
        />
        {planning.isPending && <div className="map-area__loading" aria-hidden="true" />}
        <HeatmapControl
          heatmap={heatmap}
          route={selectedRoute}
          isLoading={heatmapQuery.isFetching}
          error={heatmapQuery.isError ? errorMessage(heatmapQuery.error) : null}
          playback={playback}
          isVisible={showHeatmap}
          onVisibleChange={setShowHeatmap}
        />
      </main>
    </div>
  );
}
