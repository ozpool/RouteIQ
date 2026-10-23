import { useEffect, useRef } from "react";
import type { Route } from "../../api/types";
import { formatClock, formatDuration, formatMiles, localZoneName } from "../../domain/format";
import { RISK_LABEL, elevatedMiles } from "../../domain/risk";
import { CheckpointList } from "./CheckpointList";
import { RiskBadge } from "./RiskBadge";
import { RiskBar } from "./RiskBar";

interface RouteCardProps {
  route: Route;
  rank: number;
  isRecommended: boolean;
  isSelected: boolean;
  isOpen: boolean;
  onToggle: () => void;
  activeCheckpoint: number | null;
  onSelectCheckpoint: (index: number) => void;
}

export function RouteCard({
  route,
  rank,
  isRecommended,
  isSelected,
  isOpen,
  onToggle,
  activeCheckpoint,
  onSelectCheckpoint,
}: RouteCardProps) {
  const elevated = elevatedMiles(route.risk.miles_by_level);
  const cardRef = useRef<HTMLElement>(null);
  const wasSelected = useRef(isSelected);

  // Newly selected (from the map, the table or this card): bring it into view. A card that is
  // selected from its first render is left alone, so a new plan keeps the recommendation on top.
  useEffect(() => {
    if (isSelected && !wasSelected.current) cardRef.current?.scrollIntoView({ block: "start", behavior: "smooth" });
    wasSelected.current = isSelected;
  }, [isSelected]);

  return (
    <article ref={cardRef} className={`route-card${isSelected ? " is-selected" : ""}`}>
      <button
        type="button"
        className="route-card__summary"
        onClick={onToggle}
        aria-expanded={isOpen}
        title={isOpen ? "Hide checkpoints" : isSelected ? "Show checkpoints" : "Show this route on the map"}
      >
        <div className="route-card__title">
          <span className="route-card__rank">#{rank}</span>
          <h3>{route.label}</h3>
          {isRecommended && <span className="pill pill--recommended">Recommended</span>}
          {isSelected && <span className="pill pill--map">On map</span>}
          <span className="route-card__max">
            <RiskBadge level={route.risk.max_level} />
            <span className="route-card__chevron" aria-hidden="true">
              {isOpen ? "▾" : "▸"}
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
            <dt>Arrive ({localZoneName()})</dt>
            <dd>{formatClock(route.arrival)}</dd>
          </div>
          <div>
            <dt>Avg risk</dt>
            <dd>{route.risk.average.toFixed(2)} / 4</dd>
          </div>
        </dl>
        <RiskBar route={route} />
        <p className="route-card__miles">
          {elevated.length === 0
            ? `All ${formatMiles(route.distance_mi)} Low`
            : elevated.map(({ level, miles }, i) => (
                <span key={level} className={level === "no_travel" ? "danger" : undefined}>
                  {i > 0 && " · "}
                  {formatMiles(miles)} {RISK_LABEL[level]}
                </span>
              ))}
        </p>
      </button>
      {isOpen && (
        <CheckpointList
          checkpoints={route.checkpoints}
          activeIndex={activeCheckpoint}
          onSelect={onSelectCheckpoint}
        />
      )}
    </article>
  );
}
