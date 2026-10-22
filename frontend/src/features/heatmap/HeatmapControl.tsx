import type { Heatmap } from "../../api/types";
import { formatClock } from "../../domain/format";
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from "../../domain/risk";
import type { TruckState } from "../../domain/truckPosition";

/** The slider moves in 15-minute steps so the truck marker moves smoothly between checkpoints. */
export const SLIDER_STEP_HOURS = 0.25;

interface HeatmapControlProps {
  heatmap: Heatmap | undefined;
  isLoading: boolean;
  error: string | null;
  offsetHours: number;
  maxOffsetHours: number;
  onOffsetChange: (hours: number) => void;
  isVisible: boolean;
  onVisibleChange: (visible: boolean) => void;
  truck: TruckState | null;
  isPlaying: boolean;
  canPlay: boolean;
  onTogglePlay: () => void;
  playbackNote: string | null;
}

export function heatmapStart(heatmap: Heatmap): Date {
  return new Date(heatmap.start_time);
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

export function HeatmapControl({
  heatmap,
  isLoading,
  error,
  offsetHours,
  maxOffsetHours,
  onOffsetChange,
  isVisible,
  onVisibleChange,
  truck,
  isPlaying,
  canPlay,
  onTogglePlay,
  playbackNote,
}: HeatmapControlProps) {
  return (
    <section className="heatmap-control" aria-label="Corridor weather forecast">
      <div className="heatmap-control__row">
        <label className="toggle">
          <input
            type="checkbox"
            checked={isVisible}
            onChange={(event) => onVisibleChange(event.target.checked)}
          />
          Corridor heatmap
        </label>
        <span className="heatmap-control__time" aria-live="polite">
          {heatmap ? (
            <>
              <strong>{formatOffset(offsetHours)}</strong> ·{" "}
              {formatClock(new Date(heatmapStart(heatmap).getTime() + offsetHours * 3_600_000))}
            </>
          ) : isLoading ? (
            "Loading forecast…"
          ) : (
            (error ?? "Plan a trip to see the forecast")
          )}
        </span>
      </div>
      <div className="heatmap-control__row">
        <button
          type="button"
          className="button button--icon"
          onClick={onTogglePlay}
          disabled={!canPlay}
          aria-label={isPlaying ? "Pause trip playback" : "Play trip checkpoint by checkpoint"}
          title={isPlaying ? "Pause" : "Drive the selected route checkpoint by checkpoint"}
        >
          {isPlaying ? "❚❚" : "▶"}
        </button>
        <input
          type="range"
          className="heatmap-control__slider"
          min={0}
          max={maxOffsetHours}
          step={SLIDER_STEP_HOURS}
          value={offsetHours}
          disabled={!heatmap}
          onChange={(event) => onOffsetChange(Number(event.target.value))}
          aria-label="Forecast time after departure hour"
        />
      </div>
      <div className="heatmap-control__row heatmap-control__foot">
        <ul className="legend">
          {RISK_LEVELS.map((level) => (
            <li key={level}>
              <span style={{ background: RISK_COLOR[level] }} />
              {RISK_LABEL[level]}
            </li>
          ))}
        </ul>
        <span className="muted">{playbackNote ?? truckLabel(truck)}</span>
      </div>
    </section>
  );
}
