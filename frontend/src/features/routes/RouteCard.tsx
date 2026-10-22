import type { Route } from "../../api/types";
import { formatClock, formatDuration, formatMiles } from "../../domain/format";
import { CheckpointList } from "./CheckpointList";
import { RiskBadge } from "./RiskBadge";
import { RiskBar } from "./RiskBar";

interface RouteCardProps {
  route: Route;
  rank: number;
  isRecommended: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  activeCheckpoint: number | null;
  onSelectCheckpoint: (index: number) => void;
}

export function RouteCard({
  route,
  rank,
  isRecommended,
  isSelected,
  isExpanded,
  onToggle,
  activeCheckpoint,
  onSelectCheckpoint,
}: RouteCardProps) {
  const miles = route.risk.miles_by_level;
  return (
    <article className={`route-card${isSelected ? " is-selected" : ""}${isExpanded ? " is-expanded" : ""}`}>
      <button
        type="button"
        className="route-card__summary"
        onClick={onToggle}
        aria-expanded={isExpanded}
        title={isExpanded ? "Hide checkpoints" : "Show checkpoints and highlight on map"}
      >
        <div className="route-card__title">
          <span className="route-card__rank">#{rank}</span>
          <h3>{route.label}</h3>
          {isRecommended && <span className="pill pill--recommended">Recommended</span>}
          {isSelected && <span className="pill pill--map">On map</span>}
          <span className="route-card__max">
            <RiskBadge level={route.risk.max_level} />
            <span className="route-card__chevron" aria-hidden="true">
              {isExpanded ? "▾" : "▸"}
            </span>
          </span>
        </div>
        {route.summary && <p className="route-card__via">via {route.summary}</p>}
        <dl className="route-card__stats">
          <div>
            <dt>Distance</dt>
            <dd>{formatMiles(route.distance_mi)}</dd>
          </div>
          <div>
            <dt>Drive time</dt>
            <dd>{formatDuration(route.duration_s)}</dd>
          </div>
          <div>
            <dt>Arrive</dt>
            <dd>{formatClock(route.arrival)}</dd>
          </div>
          <div>
            <dt>Avg risk</dt>
            <dd>{route.risk.average.toFixed(2)} / 4</dd>
          </div>
        </dl>
        <RiskBar route={route} />
        <p className="route-card__miles">
          {miles.no_travel > 0 && <span className="danger">{formatMiles(miles.no_travel)} No Travel · </span>}
          <span>{formatMiles(miles.severe)} Severe</span> · <span>{formatMiles(miles.high)} High</span>
        </p>
      </button>
      {isExpanded && (
        <CheckpointList
          checkpoints={route.checkpoints}
          activeIndex={activeCheckpoint}
          onSelect={onSelectCheckpoint}
        />
      )}
    </article>
  );
}
