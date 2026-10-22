import type { Feature, FeatureCollection, LineString, Point, Polygon } from "geojson";
import type { Coordinate, Heatmap, Place, Route, TripPlan } from "../../api/types";

export type Bounds = [[number, number], [number, number]];

export function routeLine(route: Route): Coordinate[] {
  return route.segments.flatMap((segment, i) =>
    i === 0 ? segment.coordinates : segment.coordinates.slice(1),
  );
}

/** Keep every n-th point (and the last) so a line has at most `maxPoints` points. */
export function thinLine(coordinates: Coordinate[], maxPoints: number): Coordinate[] {
  if (coordinates.length <= maxPoints) return coordinates;
  const step = Math.ceil(coordinates.length / (maxPoints - 1));
  const thinned = coordinates.filter((_, i) => i % step === 0);
  const last = coordinates[coordinates.length - 1];
  if (last && thinned[thinned.length - 1] !== last) thinned.push(last);
  return thinned;
}

export function routeLinesCollection(plan: TripPlan): FeatureCollection<LineString> {
  return {
    type: "FeatureCollection",
    features: plan.routes.map((route) => ({
      type: "Feature",
      id: route.id,
      properties: { routeId: route.id, recommended: route.id === plan.recommendation.route_id },
      geometry: { type: "LineString", coordinates: routeLine(route) },
    })),
  };
}

export function riskSegmentsCollection(route: Route): FeatureCollection<LineString> {
  return {
    type: "FeatureCollection",
    features: route.segments.map((segment, i) => ({
      type: "Feature",
      id: i,
      properties: { level: segment.level },
      geometry: { type: "LineString", coordinates: segment.coordinates },
    })),
  };
}

export function checkpointsCollection(route: Route): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: route.checkpoints.map((checkpoint) => ({
      type: "Feature",
      id: checkpoint.index,
      properties: { index: checkpoint.index, level: checkpoint.risk.level },
      geometry: { type: "Point", coordinates: checkpoint.coordinate },
    })),
  };
}

export function endpointsCollection(origin: Place, destination: Place): FeatureCollection<Point> {
  const point = (place: Place, role: string): Feature<Point> => ({
    type: "Feature",
    properties: { role, label: place.label },
    geometry: { type: "Point", coordinates: [place.lon, place.lat] },
  });
  return { type: "FeatureCollection", features: [point(origin, "origin"), point(destination, "destination")] };
}

/**
 * One square per corridor cell carrying every hour's risk as h0…hN, so the slider only has to
 * swap the layer's colour expression — the geometry is uploaded to the GPU once.
 */
export function heatmapCellsCollection(heatmap: Heatmap): FeatureCollection<Polygon> {
  const half = heatmap.cell_size_deg / 2;
  return {
    type: "FeatureCollection",
    features: heatmap.cells.map(([lon, lat], i) => {
      const properties: Record<string, number> = {};
      heatmap.risk[i]?.forEach((score, hour) => {
        properties[`h${hour}`] = score;
      });
      return {
        type: "Feature",
        id: i,
        properties,
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [lon - half, lat - half],
              [lon + half, lat - half],
              [lon + half, lat + half],
              [lon - half, lat + half],
              [lon - half, lat - half],
            ],
          ],
        },
      };
    }),
  };
}

export function boundsOf(coordinates: Iterable<Coordinate>): Bounds | null {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of coordinates) {
    minLon = Math.min(minLon, lon);
    minLat = Math.min(minLat, lat);
    maxLon = Math.max(maxLon, lon);
    maxLat = Math.max(maxLat, lat);
  }
  return Number.isFinite(minLon) ? [[minLon, minLat], [maxLon, maxLat]] : null;
}
