import type { Checkpoint } from "../../api/types";
import { formatClock } from "../../domain/format";
import { RiskBadge } from "../routes/RiskBadge";

export function CheckpointPopup({ checkpoint }: { checkpoint: Checkpoint }) {
  const { weather, risk } = checkpoint;
  return (
    <div className="popup">
      <div className="popup__head">
        <strong>Mile {checkpoint.mile.toFixed(0)}</strong>
        <RiskBadge level={risk.level} />
      </div>
      <div className="popup__eta">ETA {formatClock(checkpoint.eta)}</div>
      <dl className="popup__grid">
        <dt>Wind</dt>
        <dd>
          {weather.wind_mph.toFixed(0)} mph
          {weather.gust_mph !== null && <span className="muted"> · gusts {weather.gust_mph.toFixed(0)}</span>}
        </dd>
        <dt>Rain</dt>
        <dd>{weather.rain_in_hr.toFixed(2)} in/hr</dd>
        <dt>Snow</dt>
        <dd>{weather.snow_in_hr.toFixed(2)} in/hr</dd>
      </dl>
      {risk.reasons.length > 0 && (
        <ul className="popup__reasons">
          {risk.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
