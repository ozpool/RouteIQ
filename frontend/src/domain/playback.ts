import type { Checkpoint, Route } from "../api/types";

/**
 * The checkpoint the truck reaches next after `time`, or null once it has passed the last one
 * (or the next one is after `until`, the end of the forecast window). Playback steps through
 * these one by one, so the truck stops at every checkpoint in ETA order and never skips one.
 */
export function nextCheckpoint(route: Route, time: Date, until: Date): Checkpoint | null {
  const now = time.getTime();
  const next = route.checkpoints.find((checkpoint) => Date.parse(checkpoint.eta) > now + 1000);
  if (!next || Date.parse(next.eta) > until.getTime()) return null;
  return next;
}

export function hoursBetween(start: Date, end: Date): number {
  return (end.getTime() - start.getTime()) / 3_600_000;
}
