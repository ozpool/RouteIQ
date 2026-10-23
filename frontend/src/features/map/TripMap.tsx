import "maplibre-gl/dist/maplibre-gl.css";
import type { MapLayerMouseEvent } from "maplibre-gl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MapGL, {
  AttributionControl,
  Layer,
  type MapRef,
  Marker,
  NavigationControl,
  Popup,
  Source,
} from "react-map-gl/maplibre";
import type { Heatmap, Place, TripPlan } from "../../api/types";
import { env } from "../../config/env";
import type { TruckState } from "../../domain/truckPosition";
import { CheckpointPopup } from "./CheckpointPopup";
import {
  boundsOf,
  checkpointsCollection,
  endpointsCollection,
  heatmapCellsCollection,
  riskSegmentsCollection,
  routeLine,
  routeLinesCollection,
} from "./geojson";
import {
  LAYER_IDS,
  checkpointsLayer,
  endpointsLayer,
  heatmapFillLayer,
  otherRoutesLayer,
  recommendedRouteLayer,
  routeHitLayer,
  selectedCasingLayer,
  selectedRiskLayer,
} from "./layers";

const INITIAL_VIEW = { longitude: -96.5, latitude: 38.5, zoom: 3.6 };
const INTERACTIVE_LAYERS = [LAYER_IDS.checkpoints, LAYER_IDS.routeHit];
// Open-Meteo's free API is CC-BY 4.0: the forecast must be credited wherever it is shown.
const WEATHER_ATTRIBUTION =
  '<a href="https://open-meteo.com/" target="_blank" rel="noopener">Weather data by Open-Meteo.com</a>';

interface TripMapProps {
  plan: TripPlan | undefined;
  origin: Place | null;
  destination: Place | null;
  selectedRouteId: string | null;
  onSelectRoute: (routeId: string) => void;
  activeCheckpoint: number | null;
  onSelectCheckpoint: (index: number | null) => void;
  heatmap: Heatmap | undefined;
  heatmapHour: number;
  showHeatmap: boolean;
  truck: TruckState | null;
}

export function TripMap({
  plan,
  origin,
  destination,
  selectedRouteId,
  onSelectRoute,
  activeCheckpoint,
  onSelectCheckpoint,
  heatmap,
  heatmapHour,
  showHeatmap,
  truck,
}: TripMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [labelLayerId, setLabelLayerId] = useState<string | undefined>();
  const [cursor, setCursor] = useState<string>("");

  const selectedRoute = plan?.routes.find((r) => r.id === selectedRouteId);

  const routeLines = useMemo(() => (plan ? routeLinesCollection(plan) : null), [plan]);
  const riskSegments = useMemo(
    () => (selectedRoute ? riskSegmentsCollection(selectedRoute) : null),
    [selectedRoute],
  );
  const checkpoints = useMemo(
    () => (selectedRoute ? checkpointsCollection(selectedRoute) : null),
    [selectedRoute],
  );
  const endpoints = useMemo(
    () => (origin && destination ? endpointsCollection(origin, destination) : null),
    [origin, destination],
  );
  const heatmapCells = useMemo(() => (heatmap ? heatmapCellsCollection(heatmap) : null), [heatmap]);
  const heatmapLayer = useMemo(() => heatmapFillLayer(heatmapHour), [heatmapHour]);
  const othersLayer = useMemo(() => otherRoutesLayer(selectedRouteId ?? ""), [selectedRouteId]);
  const recommendedLayer = useMemo(() => recommendedRouteLayer(selectedRouteId ?? ""), [selectedRouteId]);

  useEffect(() => {
    if (!plan) return;
    const bounds = boundsOf(plan.routes.flatMap(routeLine));
    if (bounds) {
      mapRef.current?.fitBounds(bounds, {
        padding: { top: 60, bottom: 190, left: 60, right: 60 },
        duration: 900,
      });
    }
  }, [plan]);

  // Feature-state highlight: no source re-upload when the active checkpoint changes.
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || activeCheckpoint === null || !map.getSource("checkpoints")) return;
    map.setFeatureState({ source: "checkpoints", id: activeCheckpoint }, { active: true });
    const point = selectedRoute?.checkpoints[activeCheckpoint]?.coordinate;
    if (point && !map.getBounds().contains(point)) map.easeTo({ center: point, duration: 600 });
    return () => {
      if (map.getSource("checkpoints")) {
        map.setFeatureState({ source: "checkpoints", id: activeCheckpoint }, { active: false });
      }
    };
  }, [activeCheckpoint, selectedRoute]);

  const handleLoad = useCallback(() => {
    const layers = mapRef.current?.getMap().getStyle().layers ?? [];
    setLabelLayerId(layers.find((layer) => layer.type === "symbol")?.id);
  }, []);

  const handleClick = useCallback(
    (event: MapLayerMouseEvent) => {
      const feature = event.features?.[0];
      if (!feature) {
        onSelectCheckpoint(null);
        return;
      }
      if (feature.layer.id === LAYER_IDS.checkpoints) {
        onSelectCheckpoint(Number(feature.properties.index));
      } else {
        onSelectRoute(String(feature.properties.routeId));
      }
    },
    [onSelectCheckpoint, onSelectRoute],
  );

  const popupCheckpoint = activeCheckpoint !== null ? selectedRoute?.checkpoints[activeCheckpoint] : undefined;

  return (
    <MapGL
      ref={mapRef}
      initialViewState={INITIAL_VIEW}
      mapStyle={env.mapStyleUrl}
      interactiveLayerIds={INTERACTIVE_LAYERS}
      onLoad={handleLoad}
      onClick={handleClick}
      onMouseEnter={() => setCursor("pointer")}
      onMouseLeave={() => setCursor("")}
      cursor={cursor}
      attributionControl={false}
      style={{ position: "absolute", inset: 0 }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      <AttributionControl
        compact
        position="top-left"
        customAttribution={WEATHER_ATTRIBUTION}
      />

      {heatmapCells && (
        <Source id="heatmap" type="geojson" data={heatmapCells}>
          <Layer
            {...heatmapLayer}
            beforeId={routeLines ? LAYER_IDS.otherRoutes : labelLayerId}
            layout={{ visibility: showHeatmap ? "visible" : "none" }}
          />
        </Source>
      )}

      {routeLines && (
        <Source id="routes" type="geojson" data={routeLines}>
          <Layer {...othersLayer} beforeId={labelLayerId} />
          <Layer {...recommendedLayer} beforeId={labelLayerId} />
          <Layer {...routeHitLayer} />
        </Source>
      )}

      {riskSegments && (
        <Source id="risk-segments" type="geojson" data={riskSegments}>
          <Layer {...selectedCasingLayer} />
          <Layer {...selectedRiskLayer} />
        </Source>
      )}

      {checkpoints && (
        <Source id="checkpoints" type="geojson" data={checkpoints}>
          <Layer {...checkpointsLayer} />
        </Source>
      )}

      {endpoints && (
        <Source id="endpoints" type="geojson" data={endpoints}>
          <Layer {...endpointsLayer} />
        </Source>
      )}

      {truck && (
        <Marker longitude={truck.coordinate[0]} latitude={truck.coordinate[1]} anchor="center">
          <div className={`truck truck--${truck.status}`} aria-label="Truck position at selected hour">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                fill="currentColor"
                d="M3 6h11v8h1.5V9h3.2L21 12.3V16h-1.2a2.3 2.3 0 0 1-4.6 0H9.3a2.3 2.3 0 0 1-4.6 0H3z"
              />
            </svg>
          </div>
        </Marker>
      )}

      {popupCheckpoint && (
        <Popup
          longitude={popupCheckpoint.coordinate[0]}
          latitude={popupCheckpoint.coordinate[1]}
          anchor="bottom"
          offset={12}
          closeOnClick={false}
          onClose={() => onSelectCheckpoint(null)}
          maxWidth="280px"
        >
          <CheckpointPopup checkpoint={popupCheckpoint} />
        </Popup>
      )}
    </MapGL>
  );
}
