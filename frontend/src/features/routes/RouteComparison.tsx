import type { Checkpoint, Route, TripPlan } from "../../api/types";
import { formatDuration } from "../../domain/format";
import { RISK_COLOR, RISK_LABEL } from "../../domain/risk";

function worstCheckpoint(route: Route): Checkpoint | undefined {
  return route.checkpoints.reduce<Checkpoint | undefined>(
    (worst, checkpoint) => (!worst || checkpoint.risk.score > worst.risk.score ? checkpoint : worst),
    undefined,
  );
}

function worstConditions(route: Route): string {
  const worst = worstCheckpoint(route);
  if (!worst || worst.risk.score === 0) return "No elevated conditions";
  const reason = worst.risk.reasons[worst.risk.reasons.length - 1] ?? RISK_LABEL[worst.risk.level];
  return `${reason} at mi ${worst.mile.toFixed(0)}`;
}

interface RouteComparisonProps {
  plan: TripPlan;
  selectedRouteId: string | null;
  onSelectRoute: (routeId: string) => void;
}

/** Every fetched route side by side, with the exact numbers the ranking compares. */
export function RouteComparison({ plan, selectedRouteId, onSelectRoute }: RouteComparisonProps) {
  const rankOf = new Map(plan.recommendation.ranking.map((id, i) => [id, i + 1]));
  const routes = [...plan.routes].sort((a, b) => (rankOf.get(a.id) ?? 0) - (rankOf.get(b.id) ?? 0));

  return (
    <div className="comparison">
      <p className="comparison__title">
        All {routes.length} routes, scored on {routes.reduce((n, r) => n + r.checkpoints.length, 0)}{" "}
        forecast checkpoints
      </p>
      <div className="comparison__scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Route</th>
              <th scope="col" title="Miles in No Travel conditions">No Trav.</th>
              <th scope="col">Severe</th>
              <th scope="col">High</th>
              <th scope="col">Mod.</th>
              <th scope="col" title="Risk-miles: each mile times its level, Moderate 1 to No Travel 4">Exp.</th>
              <th scope="col">Time</th>
              <th scope="col" title="Weather samples">Pts</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((route) => {
              const miles = route.risk.miles_by_level;
              return (
                <tr
                  key={route.id}
                  className={route.id === selectedRouteId ? "is-active" : undefined}
                  onClick={() => onSelectRoute(route.id)}
                  title={worstConditions(route)}
                >
                  <td>#{rankOf.get(route.id)}</td>
                  <td>
                    <span
                      className="comparison__dot"
                      style={{ background: RISK_COLOR[route.risk.max_level] }}
                      title={`Worst checkpoint: ${RISK_LABEL[route.risk.max_level]}`}
                    />
                    <span className="comparison__route">{route.label.replace("Route ", "")}</span>
                  </td>
                  <td className={miles.no_travel > 0 ? "danger" : undefined}>{miles.no_travel.toFixed(0)}</td>
                  <td>{miles.severe.toFixed(0)}</td>
                  <td>{miles.high.toFixed(0)}</td>
                  <td>{miles.moderate.toFixed(0)}</td>
                  <td title={`Average ${route.risk.average.toFixed(2)} / 4 per mile`}>
                    {route.risk.exposure.toFixed(0)}
                  </td>
                  <td>{formatDuration(route.duration_s)}</td>
                  <td>{route.checkpoints.length}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ul className="comparison__worst">
        {routes.map((route) => (
          <li key={route.id}>
            <strong>{route.label}:</strong> {worstConditions(route)}
          </li>
        ))}
      </ul>
      <p className="comparison__rule">
        Ranked by fewest No Travel → Severe → High miles, then least weather exposure (risk-miles,
        so a detour cannot dilute the same bad miles), then shortest time. Miles are in mi.
      </p>
    </div>
  );
}
