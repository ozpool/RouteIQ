import { describe, expect, it } from "vitest";
import type { Checkpoint, Route } from "../api/types";
import { pointAlong, truckStateAt } from "./truckPosition";

function checkpoint(index: number, mile: number, lon: number, eta: string): Checkpoint {
  return {
    index,
    mile,
    coordinate: [lon, 40],
    eta,
    weather: { wind_mph: 5, gust_mph: null, rain_in_hr: 0, snow_in_hr: 0 },
    risk: { level: "low", score: 0, wind: "low", rain: "low", snow: "low", reasons: [], load_raised: false },
  };
}

const route: Route = {
  id: "a",
  label: "Route A",
  summary: "",
  distance_mi: 100,
  duration_s: 7200,
  departure: "2026-01-10T08:00:00Z",
  arrival: "2026-01-10T10:00:00Z",
  risk: {
    miles_by_level: { low: 100, moderate: 0, high: 0, severe: 0, no_travel: 0 },
    average: 0,
    exposure: 0,
    max_level: "low",
  },
  checkpoints: [
    checkpoint(0, 0, -100, "2026-01-10T08:00:00Z"),
    checkpoint(1, 50, -99, "2026-01-10T09:00:00Z"),
    checkpoint(2, 100, -98, "2026-01-10T10:00:00Z"),
  ],
  // One segment per checkpoint, split at the midpoints between checkpoints (1° of lon = 50 mi).
  segments: [
    { start_mile: 0, end_mile: 25, level: "low", coordinates: [[-100, 40], [-99.5, 40]] },
    { start_mile: 25, end_mile: 75, level: "low", coordinates: [[-99.5, 40], [-99, 40], [-98.5, 40]] },
    { start_mile: 75, end_mile: 100, level: "low", coordinates: [[-98.5, 40], [-98, 40]] },
  ],
};

describe("pointAlong", () => {
  it("walks by distance, not by vertex count", () => {
    const [lon] = pointAlong([[0, 0], [1, 0], [3, 0]], 0.5);
    expect(lon).toBeCloseTo(1.5, 3);
  });

  it("clamps to the ends", () => {
    expect(pointAlong([[0, 0], [1, 0]], -1)).toEqual([0, 0]);
    expect(pointAlong([[0, 0], [1, 0]], 2)).toEqual([1, 0]);
  });
});

describe("truckStateAt", () => {
  it("is waiting before departure and arrived after arrival", () => {
    expect(truckStateAt(route, new Date("2026-01-10T07:00:00Z"))?.status).toBe("waiting");
    expect(truckStateAt(route, new Date("2026-01-10T11:00:00Z"))?.status).toBe("arrived");
  });

  it("interpolates mile and position between checkpoint ETAs", () => {
    const state = truckStateAt(route, new Date("2026-01-10T09:30:00Z"));
    expect(state?.status).toBe("driving");
    if (state?.status !== "driving") return;
    expect(state.mile).toBeCloseTo(75);
    expect(state.coordinate[0]).toBeCloseTo(-98.5, 2);
  });

  it("finds the segment by mile, not by checkpoint pair", () => {
    const state = truckStateAt(route, new Date("2026-01-10T09:12:00Z"));
    if (state?.status !== "driving") throw new Error("expected driving");
    expect(state.mile).toBeCloseTo(60);
    expect(state.coordinate[0]).toBeCloseTo(-98.8, 2);
  });
});
