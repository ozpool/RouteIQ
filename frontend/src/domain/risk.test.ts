import { describe, expect, it } from "vitest";
import type { Checkpoint, RiskKey, Route } from "../api/types";
import { elevatedMiles, loadEffect } from "./risk";

const none = { low: 0, moderate: 0, high: 0, severe: 0, no_travel: 0 };

describe("elevatedMiles", () => {
  it("leaves out zero-mile levels, so a Moderate-only route shows just Moderate", () => {
    expect(elevatedMiles({ ...none, low: 1657, moderate: 150 })).toEqual([{ level: "moderate", miles: 150 }]);
  });

  it("lists every non-zero elevated level worst first", () => {
    expect(elevatedMiles({ low: 900, moderate: 40, high: 25, severe: 0, no_travel: 5 })).toEqual([
      { level: "no_travel", miles: 5 },
      { level: "high", miles: 25 },
      { level: "moderate", miles: 40 },
    ]);
  });

  it("is empty when every mile is Low", () => {
    expect(elevatedMiles({ ...none, low: 456 })).toEqual([]);
  });
});

function checkpoint(wind_mph: number, wind: RiskKey, load_raised = false): Checkpoint {
  return {
    index: 0,
    mile: 0,
    coordinate: [0, 0],
    eta: "2026-10-23T12:00:00Z",
    weather: { wind_mph, gust_mph: null, rain_in_hr: 0, snow_in_hr: 0 },
    risk: { level: wind, score: 0, wind, rain: "low", snow: "low", reasons: [], load_raised },
  };
}

function routeWith(checkpoints: Checkpoint[]): Route {
  return { checkpoints } as unknown as Route;
}

describe("loadEffect", () => {
  it("counts the checkpoints the load raised", () => {
    const route = routeWith([checkpoint(38, "severe", true), checkpoint(39, "severe", true), checkpoint(10, "low")]);
    expect(loadEffect(route, 42_000)).toBe(
      'Load 42,000 lb raised wind risk at 2 checkpoints on this route (tagged "load" in its table).',
    );
  });

  it("explains calm wind", () => {
    expect(loadEffect(routeWith([checkpoint(24, "low"), checkpoint(30, "moderate")]), 80_000)).toBe(
      "Load 80,000 lb changed nothing: the strongest wind is 30 mph, below the 35 mph where load starts to count.",
    );
  });

  it("explains a load under the limit for the strongest wind", () => {
    expect(loadEffect(routeWith([checkpoint(38, "high")]), 35_000)).toBe(
      "Load 35,000 lb changed nothing: at the strongest wind (38 mph) only loads over 40,000 lb raise the risk.",
    );
    expect(loadEffect(routeWith([checkpoint(48, "severe")]), 20_000)).toBe(
      "Load 20,000 lb changed nothing: at the strongest wind (48 mph) only loads over 30,000 lb raise the risk.",
    );
  });

  it("explains wind that is No Travel for any load", () => {
    expect(loadEffect(routeWith([checkpoint(57, "no_travel")]), 10_000)).toBe(
      "Load 10,000 lb changed nothing: the strongest wind (57 mph) is No Travel for any load.",
    );
  });
});
