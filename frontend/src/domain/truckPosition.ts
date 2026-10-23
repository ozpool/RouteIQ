import type { Coordinate, Route } from "../api/types";

const EARTH_RADIUS_MI = 3958.76;

export function distanceMiles([lon1, lat1]: Coordinate, [lon2, lat2]: Coordinate): number {
  const toRad = Math.PI / 180;
  const dLat = (lat2 - lat1) * toRad;
  const dLon = (lon2 - lon1) * toRad;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_MI * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** The point `fraction` (0–1) of the way along a polyline, measured by distance. */
export function pointAlong(coordinates: Coordinate[], fraction: number): Coordinate {
  const first = coordinates[0];
  if (!first) throw new Error("pointAlong needs at least one coordinate");
  const lengths = coordinates.slice(1).map((c, i) => distanceMiles(coordinates[i] ?? first, c));
  const target = lengths.reduce((a, b) => a + b, 0) * Math.min(1, Math.max(0, fraction));
  let walked = 0;
  for (let i = 0; i < lengths.length; i++) {
    const length = lengths[i] ?? 0;
    const start = coordinates[i] ?? first;
    const end = coordinates[i + 1] ?? start;
    if (walked + length >= target) {
      const t = length > 0 ? (target - walked) / length : 0;
      return [start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t];
    }
    walked += length;
  }
  return coordinates[coordinates.length - 1] ?? first;
}

export type TruckState =
  | { status: "waiting"; coordinate: Coordinate }
  | { status: "driving"; coordinate: Coordinate; mile: number }
  | { status: "arrived"; coordinate: Coordinate };

/** Where the truck is at `time`, following the route's checkpoint ETAs and road geometry. */
export function truckStateAt(route: Route, time: Date): TruckState | null {
  const { checkpoints, segments } = route;
  const first = checkpoints[0];
  const last = checkpoints[checkpoints.length - 1];
  if (!first || !last) return null;

  const t = time.getTime();
  if (t <= Date.parse(first.eta)) return { status: "waiting", coordinate: first.coordinate };
  if (t >= Date.parse(last.eta)) return { status: "arrived", coordinate: last.coordinate };

  for (let i = 0; i < checkpoints.length - 1; i++) {
    const a = checkpoints[i];
    const b = checkpoints[i + 1];
    if (!a || !b) continue;
    const start = Date.parse(a.eta);
    const end = Date.parse(b.eta);
    if (t <= end) {
      const fraction = end > start ? (t - start) / (end - start) : 0;
      const mile = a.mile + (b.mile - a.mile) * fraction;
      // Risk segments split at the midpoints between checkpoints, so find the one by mile.
      const segment = segments.find((s) => mile <= s.end_mile) ?? segments[segments.length - 1];
      if (!segment) return null;
      const span = segment.end_mile - segment.start_mile;
      const along = span > 0 ? (mile - segment.start_mile) / span : 0;
      return { status: "driving", coordinate: pointAlong(segment.coordinates, along), mile };
    }
  }
  return { status: "arrived", coordinate: last.coordinate };
}
