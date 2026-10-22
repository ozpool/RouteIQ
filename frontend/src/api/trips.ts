import { requestJson } from "./client";
import type { Heatmap, HeatmapRequest, Place, PlanTripRequest, TripPlan } from "./types";

export function planTrip(request: PlanTripRequest, signal?: AbortSignal): Promise<TripPlan> {
  return requestJson<TripPlan>("/api/trips/plan", {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}

export function fetchHeatmap(request: HeatmapRequest, signal?: AbortSignal): Promise<Heatmap> {
  return requestJson<Heatmap>("/api/trips/heatmap", {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}

export async function geocode(query: string, signal?: AbortSignal): Promise<Place[]> {
  const params = new URLSearchParams({ q: query, limit: "6" });
  const { results } = await requestJson<{ results: Place[] }>(`/api/geocode?${params}`, { signal });
  return results;
}
