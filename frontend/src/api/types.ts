/** Mirrors backend/routeiq/api/presenters.py. Coordinates are [lon, lat]. */

export type Coordinate = [number, number];

export type RiskKey = "low" | "moderate" | "high" | "severe" | "no_travel";

export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export interface CheckpointWeather {
  wind_mph: number;
  gust_mph: number | null;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface CheckpointRisk {
  level: RiskKey;
  score: number;
  wind: RiskKey;
  rain: RiskKey;
  snow: RiskKey;
  reasons: string[];
}

export interface Checkpoint {
  index: number;
  mile: number;
  coordinate: Coordinate;
  eta: string;
  weather: CheckpointWeather;
  risk: CheckpointRisk;
}

export interface RiskSegment {
  start_mile: number;
  end_mile: number;
  level: RiskKey;
  coordinates: Coordinate[];
}

export interface Route {
  id: string;
  label: string;
  summary: string;
  distance_mi: number;
  duration_s: number;
  departure: string;
  arrival: string;
  risk: {
    miles_by_level: Record<RiskKey, number>;
    average: number;
    max_level: RiskKey;
  };
  checkpoints: Checkpoint[];
  segments: RiskSegment[];
}

export interface Recommendation {
  route_id: string;
  ranking: string[];
  reason: string;
  warnings: string[];
}

export interface TripPlan {
  routes: Route[];
  recommendation: Recommendation;
  notes: string[];
}

export type CheckpointInterval = 10 | 25 | 50;

export interface PlanTripRequest {
  origin: Place;
  destination: Place;
  departure_time: string;
  load_weight_lb: number;
  checkpoint_interval_mi: CheckpointInterval;
}

export interface HeatmapRequest {
  lines: Coordinate[][];
  departure_time: string;
  load_weight_lb: number;
}

export interface Heatmap {
  start_time: string;
  hours: number;
  cell_size_deg: number;
  cells: Coordinate[];
  /** risk[cell][hour] as a 0–4 score. */
  risk: number[][];
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}
