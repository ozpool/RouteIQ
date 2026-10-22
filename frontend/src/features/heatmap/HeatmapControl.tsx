import { useEffect, useState } from "react";
import type { Heatmap } from "../../api/types";
import { formatClock } from "../../domain/format";
import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from "../../domain/risk";
import type { TruckState } from "../../domain/truckPosition";

const PLAY_STEP_MS = 450;

interface HeatmapControlProps {
  heatmap: Heatmap | undefined;
  isLoading: boolean;
  error: string | null;
  hour: number;
  onHourChange: (hour: number) => void;
  isVisible: boolean;
  onVisibleChange: (visible: boolean) => void;
  truck: TruckState | null;
}

export function heatmapHourTime(heatmap: Heatmap, hour: number): Date {
  return new Date(Date.parse(heatmap.start_time) + hour * 3_600_000);
}

function truckLabel(truck: TruckState | null): string {
  if (!truck) return "";
  if (truck.status === "waiting") return "Truck not departed yet";
  if (truck.status === "arrived") return "Truck has arrived";
  return `Truck near mile ${truck.mile.toFixed(0)}`;
}

export function HeatmapControl({
  heatmap,
  isLoading,
  error,
  hour,
  onHourChange,
  isVisible,
  onVisibleChange,
  truck,
}: HeatmapControlProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const lastHour = heatmap ? heatmap.hours - 1 : 48;

  useEffect(() => {
    if (!isPlaying) return;
    const timer = window.setInterval(() => {
      onHourChange(hour >= lastHour ? 0 : hour + 1);
    }, PLAY_STEP_MS);
    return () => window.clearInterval(timer);
  }, [isPlaying, hour, lastHour, onHourChange]);

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
              <strong>+{hour}h</strong> · {formatClock(heatmapHourTime(heatmap, hour))}
            </>
          ) : isLoading ? (
            "Loading forecast…"
          ) : (
            error ?? "Plan a trip to see the forecast"
          )}
        </span>
      </div>
      <div className="heatmap-control__row">
        <button
          type="button"
          className="button button--icon"
          onClick={() => setIsPlaying((playing) => !playing)}
          disabled={!heatmap}
          aria-label={isPlaying ? "Pause forecast animation" : "Play forecast animation"}
        >
          {isPlaying ? "❚❚" : "▶"}
        </button>
        <input
          type="range"
          className="heatmap-control__slider"
          min={0}
          max={lastHour}
          step={1}
          value={hour}
          disabled={!heatmap}
          onChange={(event) => onHourChange(Number(event.target.value))}
          aria-label="Forecast hour after departure"
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
        <span className="muted">{truckLabel(truck)}</span>
      </div>
    </section>
  );
}
