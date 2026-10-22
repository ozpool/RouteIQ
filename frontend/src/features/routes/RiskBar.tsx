import type { Route } from "../../api/types";
import { formatMiles } from "../../domain/format";
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from "../../domain/risk";

/** Share of the route's miles at each risk level, worst levels listed in the tooltip. */
export function RiskBar({ route }: { route: Route }) {
  const miles = route.risk.miles_by_level;
  const total = RISK_LEVELS.reduce((sum, level) => sum + miles[level], 0) || 1;
  const title = RISK_LEVELS.filter((level) => miles[level] > 0)
    .map((level) => `${RISK_LABEL[level]}: ${formatMiles(miles[level])}`)
    .join(" · ");
  return (
    <div className="risk-bar" role="img" aria-label={title} title={title}>
      {RISK_LEVELS.map((level) =>
        miles[level] > 0 ? (
          <span
            key={level}
            style={{ width: `${(miles[level] / total) * 100}%`, background: RISK_COLOR[level] }}
          />
        ) : null,
      )}
    </div>
  );
}
