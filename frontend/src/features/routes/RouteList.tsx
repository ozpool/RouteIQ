import type { TripPlan } from "../../api/types";
import { RouteCard } from "./RouteCard";

interface RouteListProps {
  plan: TripPlan;
  selectedRouteId: string | null;
  onSelectRoute: (routeId: string) => void;
  activeCheckpoint: number | null;
  onSelectCheckpoint: (index: number) => void;
}

export function RouteList({
  plan,
  selectedRouteId,
  onSelectRoute,
  activeCheckpoint,
  onSelectCheckpoint,
}: RouteListProps) {
  const { recommendation } = plan;
  const byId = new Map(plan.routes.map((route) => [route.id, route]));
  const ranked = recommendation.ranking.flatMap((id) => byId.get(id) ?? []);
  const best = byId.get(recommendation.route_id);

  return (
    <section className="results" aria-label="Route options">
      <div className="recommendation">
        <p className="recommendation__eyebrow">Recommended</p>
        <p className="recommendation__title">{best?.label}</p>
        <p className="recommendation__reason">{recommendation.reason}</p>
        {recommendation.warnings.map((warning) => (
          <p key={warning} className="alert alert--warning">
            {warning}
          </p>
        ))}
        {plan.notes.map((note) => (
          <p key={note} className="alert alert--info">
            {note}
          </p>
        ))}
      </div>
      {ranked.map((route, i) => (
        <RouteCard
          key={route.id}
          route={route}
          rank={i + 1}
          isRecommended={route.id === recommendation.route_id}
          isSelected={route.id === selectedRouteId}
          onSelect={() => onSelectRoute(route.id)}
          activeCheckpoint={route.id === selectedRouteId ? activeCheckpoint : null}
          onSelectCheckpoint={onSelectCheckpoint}
        />
      ))}
    </section>
  );
}
