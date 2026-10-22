import type { RiskKey } from "../api/types";

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

export function riskKeyFromScore(score: number): RiskKey {
  return RISK_LEVELS[Math.max(0, Math.min(4, Math.round(score)))] ?? "low";
}
