import type { RiskKey } from "../../api/types";
import { RISK_COLOR, RISK_LABEL } from "../../domain/risk";

export function RiskBadge({ level }: { level: RiskKey }) {
  return (
    <span className={`badge badge--${level}`} style={{ ["--risk" as string]: RISK_COLOR[level] }}>
      {RISK_LABEL[level]}
    </span>
  );
}
