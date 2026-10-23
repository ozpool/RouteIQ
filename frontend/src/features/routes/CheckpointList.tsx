import { useEffect, useRef } from "react";
import type { Checkpoint } from "../../api/types";
import { formatClock, localZoneName } from "../../domain/format";
import { RiskBadge } from "./RiskBadge";

interface CheckpointListProps {
  checkpoints: Checkpoint[];
  activeIndex: number | null;
  onSelect: (index: number) => void;
}

export function CheckpointList({ checkpoints, activeIndex, onSelect }: CheckpointListProps) {
  const activeRow = useRef<HTMLTableRowElement>(null);

  // A checkpoint picked on the map (or reached by playback) scrolls its row into view.
  useEffect(() => {
    activeRow.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeIndex]);

  return (
    <table className="checkpoints">
      <thead>
        <tr>
          <th scope="col">Mile</th>
          <th scope="col">ETA ({localZoneName()})</th>
          <th scope="col">Wind</th>
          <th scope="col">Rain / Snow</th>
          <th scope="col">Risk</th>
        </tr>
      </thead>
      <tbody>
        {checkpoints.map((checkpoint) => (
          <tr
            key={checkpoint.index}
            ref={checkpoint.index === activeIndex ? activeRow : undefined}
            className={checkpoint.index === activeIndex ? "is-active" : undefined}
            onClick={() => onSelect(checkpoint.index)}
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") onSelect(checkpoint.index);
            }}
            title={checkpoint.risk.reasons.join("\n") || "No elevated conditions"}
          >
            <td>{checkpoint.mile.toFixed(0)}</td>
            <td>{formatClock(checkpoint.eta)}</td>
            <td>{checkpoint.weather.wind_mph.toFixed(0)} mph</td>
            <td>
              {checkpoint.weather.rain_in_hr.toFixed(2)} / {checkpoint.weather.snow_in_hr.toFixed(2)}
            </td>
            <td>
              <RiskBadge level={checkpoint.risk.level} />
              {checkpoint.risk.load_raised && (
                <span className="load-tag" title="The load raised this checkpoint's wind risk">
                  load
                </span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
