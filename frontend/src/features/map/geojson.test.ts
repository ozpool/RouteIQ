import { describe, expect, it } from "vitest";
import type { Coordinate, Heatmap } from "../../api/types";
import { boundsOf, heatmapCellsCollection, thinLine } from "./geojson";

describe("heatmapCellsCollection", () => {
  const heatmap: Heatmap = {
    start_time: "2026-01-10T08:00:00Z",
    hours: 3,
    cell_size_deg: 0.2,
    cells: [[-100.1, 40.1]],
    risk: [[0, 2, 4]],
  };

  it("builds one square per cell with every hour as a property", () => {
    const [feature] = heatmapCellsCollection(heatmap).features;
    expect(feature?.properties).toEqual({ h0: 0, h1: 2, h2: 4 });
    const ring = feature?.geometry.coordinates[0];
    expect(ring?.[0]?.[0]).toBeCloseTo(-100.2);
    expect(ring?.[2]?.[1]).toBeCloseTo(40.2);
  });
});

describe("thinLine", () => {
  const line: Coordinate[] = Array.from({ length: 1001 }, (_, i) => [i, 0]);

  it("keeps short lines unchanged", () => {
    expect(thinLine(line, 2000)).toBe(line);
  });

  it("caps the point count and keeps both ends", () => {
    const thinned = thinLine(line, 100);
    expect(thinned.length).toBeLessThanOrEqual(100);
    expect(thinned[0]).toEqual([0, 0]);
    expect(thinned[thinned.length - 1]).toEqual([1000, 0]);
  });
});

describe("boundsOf", () => {
  it("returns null for no points", () => {
    expect(boundsOf([])).toBeNull();
  });

  it("spans all points", () => {
    expect(boundsOf([[1, 5], [-3, 2], [4, -1]])).toEqual([[-3, -1], [4, 5]]);
  });
});
