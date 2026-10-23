import type { RiskKey, Route } from "../api/types";

export const RISK_LEVELS: readonly RiskKey[] = ["low", "moderate", "high", "severe", "no_travel"];

export const RISK_LABEL: Record<RiskKey, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  severe: "Severe",
  no_travel: "No Travel",
};

/** Ordered by score 0–4; also used as MapLibre match-expression outputs. */
export const RISK_COLOR: Record<RiskKey, string> = {
  low: "#2f9e62",
  moderate: "#e2b822",
  high: "#ee8131",
  severe: "#d7383b",
  no_travel: "#7a2fbf",
};

const ELEVATED_WORST_FIRST: readonly RiskKey[] = ["no_travel", "severe", "high", "moderate"];

/** The elevated levels a route actually has, worst first; zero-mile levels are left out. */
export function elevatedMiles(miles: Record<RiskKey, number>): { level: RiskKey; miles: number }[] {
  return ELEVATED_WORST_FIRST.filter((level) => miles[level] > 0).map((level) => ({ level, miles: miles[level] }));
}

// Mirrors backend/routeiq/domain/risk.py: the load can only raise the wind level.
export const LOAD_SEVERE_LB = 40_000; // above this, 35–44 mph wind is Severe instead of High
export const LOAD_NO_TRAVEL_LB = 30_000; // above this, 45–54 mph wind is No Travel instead of Severe

/** One line on what the load did to a route's risk, including why it changed nothing. */
export function loadEffect(route: Route, loadLb: number): string {
  const load = `Load ${loadLb.toLocaleString()} lb`;
  const raised = route.checkpoints.filter((checkpoint) => checkpoint.risk.load_raised).length;
  if (raised > 0) {
    return `${load} raised wind risk at ${raised} checkpoint${raised === 1 ? "" : "s"} on this route (tagged "load" in its table).`;
  }
  const strongest = Math.max(0, ...route.checkpoints.map((checkpoint) => checkpoint.weather.wind_mph));
  const windLevel = route.checkpoints.reduce<RiskKey>(
    (worst, checkpoint) =>
      RISK_LEVELS.indexOf(checkpoint.risk.wind) > RISK_LEVELS.indexOf(worst) ? checkpoint.risk.wind : worst,
    "low",
  );
  const mph = `${strongest.toFixed(0)} mph`;
  if (windLevel === "low" || windLevel === "moderate") {
    return `${load} changed nothing: the strongest wind is ${mph}, below the 35 mph where load starts to count.`;
  }
  if (windLevel === "no_travel") {
    return `${load} changed nothing: the strongest wind (${mph}) is No Travel for any load.`;
  }
  const limit = windLevel === "high" ? LOAD_SEVERE_LB : LOAD_NO_TRAVEL_LB;
  return `${load} changed nothing: at the strongest wind (${mph}) only loads over ${limit.toLocaleString()} lb raise the risk.`;
}
