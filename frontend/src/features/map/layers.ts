import type {
  CircleLayerSpecification,
  ExpressionSpecification,
  FillLayerSpecification,
  LineLayerSpecification,
} from "maplibre-gl";
import { RISK_COLOR, RISK_LEVELS } from "../../domain/risk";

type Layer<T> = Omit<T, "source">;

const levelColor: ExpressionSpecification = [
  "match",
  ["get", "level"],
  ...RISK_LEVELS.flatMap((level) => [level, RISK_COLOR[level]]),
  RISK_COLOR.low,
] as unknown as ExpressionSpecification;

export const LAYER_IDS = {
  heatmap: "heatmap-cells",
  routeHit: "route-hit",
  otherRoutes: "route-others",
  selectedCasing: "route-selected-casing",
  selectedRisk: "route-selected-risk",
  checkpoints: "checkpoints",
  endpoints: "endpoints",
} as const;

export function heatmapFillLayer(hour: number): Layer<FillLayerSpecification> {
  const score: ExpressionSpecification = ["get", `h${hour}`];
  return {
    id: LAYER_IDS.heatmap,
    type: "fill",
    paint: {
      "fill-color": [
        "match",
        score,
        ...RISK_LEVELS.flatMap((level, i) => [i, RISK_COLOR[level]]),
        RISK_COLOR.low,
      ] as unknown as ExpressionSpecification,
      // Low cells stay faint so the corridor reads as context, not as a warning.
      "fill-opacity": ["match", score, 0, 0.1, 1, 0.32, 0.45] as unknown as ExpressionSpecification,
      "fill-antialias": false,
    },
  };
}

export function otherRoutesLayer(selectedId: string): Layer<LineLayerSpecification> {
  return {
    id: LAYER_IDS.otherRoutes,
    type: "line",
    filter: ["!=", ["get", "routeId"], selectedId],
    layout: { "line-join": "round", "line-cap": "round" },
    paint: {
      "line-color": "#5b6b78",
      "line-opacity": 0.55,
      "line-width": ["interpolate", ["linear"], ["zoom"], 4, 2.5, 10, 5],
      "line-dasharray": [1.5, 1.2],
    },
  };
}

export const routeHitLayer: Layer<LineLayerSpecification> = {
  id: LAYER_IDS.routeHit,
  type: "line",
  paint: { "line-color": "#000", "line-opacity": 0, "line-width": 18 },
};

export const selectedCasingLayer: Layer<LineLayerSpecification> = {
  id: LAYER_IDS.selectedCasing,
  type: "line",
  layout: { "line-join": "round", "line-cap": "round" },
  paint: {
    "line-color": "#0f2f3a",
    "line-width": ["interpolate", ["linear"], ["zoom"], 4, 6, 10, 11],
  },
};

export const selectedRiskLayer: Layer<LineLayerSpecification> = {
  id: LAYER_IDS.selectedRisk,
  type: "line",
  layout: { "line-join": "round", "line-cap": "round" },
  paint: {
    "line-color": levelColor,
    "line-width": ["interpolate", ["linear"], ["zoom"], 4, 3.5, 10, 7],
  },
};

export const checkpointsLayer: Layer<CircleLayerSpecification> = {
  id: LAYER_IDS.checkpoints,
  type: "circle",
  paint: {
    "circle-color": levelColor,
    // MapLibre only allows ["zoom"] as the input of a top-level interpolate.
    "circle-radius": [
      "interpolate",
      ["linear"],
      ["zoom"],
      4,
      ["case", ["boolean", ["feature-state", "active"], false], 8, 4],
      10,
      ["case", ["boolean", ["feature-state", "active"], false], 11, 7],
    ],
    "circle-stroke-color": "#ffffff",
    "circle-stroke-width": ["case", ["boolean", ["feature-state", "active"], false], 3, 1.5],
  },
};

export const endpointsLayer: Layer<CircleLayerSpecification> = {
  id: LAYER_IDS.endpoints,
  type: "circle",
  paint: {
    "circle-color": ["match", ["get", "role"], "origin", "#ffffff", "#0f2f3a"],
    "circle-radius": 7,
    "circle-stroke-color": ["match", ["get", "role"], "origin", "#0f2f3a", "#ffffff"],
    "circle-stroke-width": 3,
  },
};
