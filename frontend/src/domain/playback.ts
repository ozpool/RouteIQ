import type { Checkpoint, Route } from "../api/types";

// Within a second of a checkpoint counts as being at it, so stepping never lands on the same one.
const SAME_MOMENT_MS = 1000;

/**
 * The checkpoint the truck reaches next after `time`, or null once it has passed the last one
 * (or the next one is after `until`, the end of the forecast window). Playback steps through
 * these one by one, so the truck stops at every checkpoint in ETA order and never skips one.
 */
export function nextCheckpoint(route: Route, time: Date, until: Date): Checkpoint | null {
  const now = time.getTime();
  const next = route.checkpoints.find((checkpoint) => Date.parse(checkpoint.eta) > now + SAME_MOMENT_MS);
  if (!next || Date.parse(next.eta) > until.getTime()) return null;
  return next;
}

/** The last checkpoint the truck passed before `time`, or null before the first one. */
export function previousCheckpoint(route: Route, time: Date): Checkpoint | null {
  const now = time.getTime();
  for (let i = route.checkpoints.length - 1; i >= 0; i--) {
    const checkpoint = route.checkpoints[i];
    if (checkpoint && Date.parse(checkpoint.eta) < now - SAME_MOMENT_MS) return checkpoint;
  }
  return null;
}

export function hoursBetween(start: Date, end: Date): number {
  return (end.getTime() - start.getTime()) / 3_600_000;
}

/**
 * Slider end in hours: the whole forecast window, or with `tripOnly` the selected route's arrival
 * rounded up to a slider step.
 */
export function sliderMaxHours(
  windowHours: number,
  arrivalOffsetHours: number | null,
  tripOnly: boolean,
  stepHours: number,
): number {
  if (!tripOnly || arrivalOffsetHours === null) return windowHours;
  const tripEnd = Math.ceil(arrivalOffsetHours / stepHours - 1e-9) * stepHours;
  return Math.min(windowHours, Math.max(stepHours, tripEnd));
}
