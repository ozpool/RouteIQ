import { describe, expect, it } from "vitest";
import type { Route } from "../api/types";
import { nextCheckpoint } from "./playback";

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
