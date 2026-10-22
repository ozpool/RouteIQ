import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "./api/client";
import { fetchHeatmap, planTrip } from "./api/trips";
import type { Place, PlanTripRequest, TripPlan } from "./api/types";
import { hoursBetween, nextCheckpoint } from "./domain/playback";
import { truckStateAt } from "./domain/truckPosition";
import { HeatmapControl, heatmapStart } from "./features/heatmap/HeatmapControl";
import { routeLine, thinLine } from "./features/map/geojson";
import { TripMap } from "./features/map/TripMap";
import { RouteList } from "./features/routes/RouteList";
import { TripForm } from "./features/trip-form/TripForm";

// The heatmap endpoint accepts up to 5000 points per line; the corridor grid is far coarser.
const HEATMAP_LINE_POINTS = 1500;
// Long enough to read each checkpoint's popup as the truck reaches it.
const PLAYBACK_STEP_MS = 1100;

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
  const [expandedRouteIds, setExpandedRouteIds] = useState<ReadonlySet<string>>(new Set());
  const [activeCheckpoint, setActiveCheckpoint] = useState<number | null>(null);
  const [offsetHours, setOffsetHours] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const tripCounter = useRef(0);

  const planning = useMutation({
    mutationFn: (request: PlanTripRequest) => planTrip(request),
    onSuccess: (plan, request) => {
      setTrip({ id: ++tripCounter.current, request, plan });
      setSelectedRouteId(plan.recommendation.route_id);
      setExpandedRouteIds(new Set([plan.recommendation.route_id]));
      setActiveCheckpoint(null);
      setOffsetHours(0);
      setIsPlaying(false);
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

  const startMs = heatmap ? heatmapStart(heatmap).getTime() : null;
  const maxOffsetHours = heatmap ? heatmap.hours - 1 : 48;
  const heatmapHour = Math.min(maxOffsetHours, Math.floor(offsetHours + 1e-9));
  const timeAt = (hours: number) => new Date((startMs ?? 0) + hours * 3_600_000);

  const truck = useMemo(
    () =>
      selectedRoute && startMs !== null
        ? truckStateAt(selectedRoute, new Date(startMs + offsetHours * 3_600_000))
        : null,
    [selectedRoute, startMs, offsetHours],
  );

  const jumpToCheckpoint = useCallback(
    (index: number) => {
      const checkpoint = selectedRoute?.checkpoints[index];
      if (!checkpoint || startMs === null) return;
      const hours = hoursBetween(new Date(startMs), new Date(checkpoint.eta));
      setOffsetHours(Math.min(maxOffsetHours, hours));
      setActiveCheckpoint(index);
    },
    [selectedRoute, startMs, maxOffsetHours],
  );

  // Playback: advance to the next checkpoint, one at a time, and stop when the truck arrives.
  useEffect(() => {
    if (!isPlaying || !selectedRoute || startMs === null) return;
    const timer = window.setTimeout(() => {
      const now = new Date(startMs + offsetHours * 3_600_000);
      const windowEnd = new Date(startMs + maxOffsetHours * 3_600_000);
      const next = nextCheckpoint(selectedRoute, now, windowEnd);
      if (next) jumpToCheckpoint(next.index);
      else setIsPlaying(false);
    }, PLAYBACK_STEP_MS);
    return () => window.clearTimeout(timer);
  }, [isPlaying, selectedRoute, startMs, offsetHours, maxOffsetHours, jumpToCheckpoint]);

  const togglePlay = () => {
    if (isPlaying) return setIsPlaying(false);
    if (!selectedRoute || startMs === null) return;
    // Finished (or past the forecast window): replay from the first checkpoint.
    if (!nextCheckpoint(selectedRoute, timeAt(offsetHours), timeAt(maxOffsetHours))) {
      jumpToCheckpoint(0);
    }
    setIsPlaying(true);
  };

  const lastCheckpoint = selectedRoute?.checkpoints[selectedRoute.checkpoints.length - 1];
  const playbackNote =
    lastCheckpoint &&
    startMs !== null &&
    Date.parse(lastCheckpoint.eta) > timeAt(maxOffsetHours).getTime() &&
    truck?.status !== "waiting"
      ? "Trip runs past the 48 h forecast window"
      : null;

  const selectRoute = useCallback((routeId: string) => {
    setSelectedRouteId(routeId);
    setActiveCheckpoint(null);
    setIsPlaying(false);
  }, []);

  const toggleRoute = useCallback(
    (routeId: string) => {
      const isOpen = expandedRouteIds.has(routeId);
      setExpandedRouteIds((open) => {
        const next = new Set(open);
        if (isOpen) next.delete(routeId);
        else next.add(routeId);
        return next;
      });
      if (!isOpen) selectRoute(routeId);
    },
    [expandedRouteIds, selectRoute],
  );

  const selectCheckpoint = useCallback(
    (routeId: string, index: number) => {
      if (routeId !== selectedRouteId) selectRoute(routeId);
      setIsPlaying(false);
      setActiveCheckpoint(index);
    },
    [selectedRouteId, selectRoute],
  );

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
            expandedRouteIds={expandedRouteIds}
            onSelectRoute={selectRoute}
            onToggleRoute={toggleRoute}
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

      <main className="map-area">
        <TripMap
          plan={plan}
          origin={trip ? trip.request.origin : origin}
          destination={trip ? trip.request.destination : destination}
          selectedRouteId={selectedRouteId}
          onSelectRoute={selectRoute}
          activeCheckpoint={activeCheckpoint}
          onSelectCheckpoint={(index) => {
            setIsPlaying(false);
            setActiveCheckpoint(index);
          }}
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
          offsetHours={offsetHours}
          maxOffsetHours={maxOffsetHours}
          onOffsetChange={(hours) => {
            setIsPlaying(false);
            setOffsetHours(hours);
          }}
          isVisible={showHeatmap}
          onVisibleChange={setShowHeatmap}
          truck={truck}
          isPlaying={isPlaying}
          canPlay={Boolean(selectedRoute && heatmap)}
          onTogglePlay={togglePlay}
          playbackNote={playbackNote}
        />
      </main>
    </div>
  );
}
