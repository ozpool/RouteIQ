import { describe, expect, it } from "vitest";
import type { Route } from "../api/types";
import { nextCheckpoint, previousCheckpoint, sliderMaxHours } from "./playback";

const etas = ["2026-01-10T08:00:00Z", "2026-01-10T08:20:00Z", "2026-01-10T08:40:00Z"];
const route = {
  checkpoints: etas.map((eta, index) => ({ index, eta })),
} as unknown as Route;
const farFuture = new Date("2030-01-01T00:00:00Z");

describe("nextCheckpoint", () => {
  it("visits every checkpoint in order without skipping", () => {
    const visited: number[] = [];
    let time = new Date("2026-01-10T07:00:00Z");
    for (let next = nextCheckpoint(route, time, farFuture); next; next = nextCheckpoint(route, time, farFuture)) {
      visited.push(next.index);
      time = new Date(next.eta);
    }
    expect(visited).toEqual([0, 1, 2]);
  });

  it("stops once the truck has arrived", () => {
    expect(nextCheckpoint(route, new Date("2026-01-10T08:40:00Z"), farFuture)).toBeNull();
  });

  it("stops at the end of the forecast window", () => {
    const windowEnd = new Date("2026-01-10T08:30:00Z");
    expect(nextCheckpoint(route, new Date("2026-01-10T08:20:00Z"), windowEnd)).toBeNull();
  });
});

describe("previousCheckpoint", () => {
  it("steps back through every checkpoint in order", () => {
    const visited: number[] = [];
    let time = new Date("2026-01-10T09:00:00Z");
    for (let prev = previousCheckpoint(route, time); prev; prev = previousCheckpoint(route, time)) {
      visited.push(prev.index);
      time = new Date(prev.eta);
    }
    expect(visited).toEqual([2, 1, 0]);
  });

  it("is null at or before the first checkpoint", () => {
    expect(previousCheckpoint(route, new Date("2026-01-10T08:00:00Z"))).toBeNull();
  });

  it("goes back to the checkpoint just passed, not the one before it", () => {
    expect(previousCheckpoint(route, new Date("2026-01-10T08:30:00Z"))?.index).toBe(1);
  });
});

describe("sliderMaxHours", () => {
  it("covers the full forecast window by default and without a route", () => {
    expect(sliderMaxHours(48, 9.6, false, 0.25)).toBe(48);
    expect(sliderMaxHours(48, null, true, 0.25)).toBe(48);
  });

  it("ends at arrival, rounded up to the next step, when trip-only", () => {
    expect(sliderMaxHours(48, 9.6, true, 0.25)).toBe(9.75);
  });

  it("never goes past the forecast window", () => {
    expect(sliderMaxHours(48, 61, true, 0.25)).toBe(48);
  });
});
