import { type CSSProperties, memo } from "react";
import type { Checkpoint, Heatmap, Route } from "../../api/types";
import { formatClock, localZoneName } from "../../domain/format";
import { hoursBetween } from "../../domain/playback";
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from "../../domain/risk";
import type { TruckState } from "../../domain/truckPosition";
import { HEATMAP_OPACITY } from "../map/layers";
import { type Playback, SLIDER_STEP_HOURS } from "./usePlayback";

interface HeatmapControlProps {
  heatmap: Heatmap | undefined;
  route: Route | undefined;
  isLoading: boolean;
  error: string | null;
  playback: Playback;
  isVisible: boolean;
  onVisibleChange: (visible: boolean) => void;
}

function formatOffset(hours: number): string {
  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return m ? `+${h}h ${String(m).padStart(2, "0")}m` : `+${h}h`;
}

function truckLabel(truck: TruckState | null): string {
  if (!truck) return "";
  if (truck.status === "waiting") return "Truck not departed yet";
  if (truck.status === "arrived") return "Truck has arrived";
  return `Truck at mile ${truck.mile.toFixed(0)}`;
}

function stepTitle(direction: "Previous" | "Next", checkpoint: Checkpoint | null): string {
  if (!checkpoint) return direction === "Previous" ? "At the first checkpoint" : "No later checkpoint in the window";
  return `${direction} checkpoint: mile ${checkpoint.mile.toFixed(0)}, ${formatClock(checkpoint.eta)}`;
}

function hexAlpha(hex: string, opacity: number): string {
  return `${hex}${Math.round(opacity * 255)
    .toString(16)
    .padStart(2, "0")}`;
}

/** One tick per checkpoint, coloured by its risk, so the steps between checkpoints are visible. */
const CheckpointTicks = memo(function CheckpointTicks({
  route,
  startMs,
  maxOffsetHours,
}: {
  route: Route;
  startMs: number;
  maxOffsetHours: number;
}) {
  const last = route.checkpoints.length - 1;
  return (
    <div className="slider-ticks" aria-hidden="true">
      {route.checkpoints.map((checkpoint, i) => {
        const hours = hoursBetween(new Date(startMs), new Date(checkpoint.eta));
        if (hours < 0 || hours > maxOffsetHours) return null;
        const style = {
          "--at": hours / maxOffsetHours,
          background: RISK_COLOR[checkpoint.risk.level],
        } as CSSProperties;
        return (
          <span key={checkpoint.index} className={i === last ? "slider-ticks__arrival" : undefined} style={style} />
        );
      })}
    </div>
  );
});

export function HeatmapControl({
  heatmap,
  route,
  isLoading,
  error,
  playback,
  isVisible,
  onVisibleChange,
}: HeatmapControlProps) {
  const { startMs, offsetHours, maxOffsetHours, previous, next, isPlaying } = playback;
  const canStep = Boolean(route && heatmap);
  const clock = startMs !== null ? formatClock(new Date(startMs + offsetHours * 3_600_000)) : "";
  const zone = localZoneName();

  return (
    <section className="heatmap-control" aria-label="Corridor weather forecast">
      <div className="heatmap-control__row">
        <label className="toggle">
          <input type="checkbox" checked={isVisible} onChange={(event) => onVisibleChange(event.target.checked)} />
          Corridor heatmap
        </label>
        {playback.canTripOnly && (
          <label className="toggle toggle--quiet" title="End the slider at the selected route's arrival">
            <input
              type="checkbox"
              checked={playback.isTripOnly}
              onChange={(event) => playback.setTripOnly(event.target.checked)}
            />
            Trip only
          </label>
        )}
        <span className="heatmap-control__time">
          {heatmap ? (
            <>
              <strong>{formatOffset(offsetHours)}</strong> · {clock} {zone}
            </>
          ) : isLoading ? (
            "Loading forecast…"
          ) : (
            (error ?? "Plan a trip to see the forecast")
          )}
        </span>
      </div>
      <div className="heatmap-control__row">
        <div className="heatmap-control__buttons" role="group" aria-label="Trip playback">
          <button
            type="button"
            className="button button--icon button--quiet"
            onClick={() => previous && playback.goToCheckpoint(previous.index)}
            disabled={!canStep || !previous}
            aria-label="Previous checkpoint"
            title={stepTitle("Previous", previous)}
          >
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path fill="currentColor" d="M3 2h2v12H3zM14 2v12L6 8z" />
            </svg>
          </button>
          <button
            type="button"
            className="button button--icon"
            onClick={playback.togglePlay}
            disabled={!canStep}
            aria-label={isPlaying ? "Pause trip playback" : "Play trip checkpoint by checkpoint"}
            title={isPlaying ? "Pause" : "Drive the selected route checkpoint by checkpoint"}
          >
            {isPlaying ? "❚❚" : "▶"}
          </button>
          <button
            type="button"
            className="button button--icon button--quiet"
            onClick={() => next && playback.goToCheckpoint(next.index)}
            disabled={!canStep || !next}
            aria-label="Next checkpoint"
            title={stepTitle("Next", next)}
          >
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path fill="currentColor" d="M11 2h2v12h-2zM2 2v12l8-6z" />
            </svg>
          </button>
        </div>
        <div className="heatmap-control__track">
          <input
            type="range"
            className="heatmap-control__slider"
            min={0}
            max={maxOffsetHours}
            step={SLIDER_STEP_HOURS}
            value={offsetHours}
            disabled={!heatmap}
            onChange={(event) => playback.scrub(Number(event.target.value))}
            aria-label="Forecast time after departure hour"
            aria-valuetext={heatmap ? `${formatOffset(offsetHours)}, ${clock} ${zone}` : undefined}
          />
          {route && startMs !== null && (
            <CheckpointTicks route={route} startMs={startMs} maxOffsetHours={maxOffsetHours} />
          )}
        </div>
      </div>
      <div className="heatmap-control__row heatmap-control__foot">
        <ul className="legend" aria-label="Heatmap risk levels">
          {RISK_LEVELS.map((level, i) => (
            <li key={level}>
              <span
                style={{
                  background: hexAlpha(RISK_COLOR[level], HEATMAP_OPACITY[i] ?? 1),
                  borderColor: RISK_COLOR[level],
                }}
              />
              {RISK_LABEL[level]}
            </li>
          ))}
        </ul>
        <span className="muted">{playback.note ?? truckLabel(playback.truck)}</span>
      </div>
    </section>
  );
}
