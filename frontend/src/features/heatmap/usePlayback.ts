import { useCallback, useEffect, useMemo, useState } from "react";
import type { Checkpoint, Heatmap, Route } from "../../api/types";
import { hoursBetween, nextCheckpoint, previousCheckpoint, sliderMaxHours } from "../../domain/playback";
import { type TruckState, truckStateAt } from "../../domain/truckPosition";

/** The slider moves in 15-minute steps so the truck marker moves smoothly between checkpoints. */
export const SLIDER_STEP_HOURS = 0.25;
// Long enough to read each checkpoint's popup as the truck reaches it.
const PLAYBACK_STEP_MS = 1100;

export interface Playback {
  /** Forecast start (epoch ms); slider offsets are hours after it. */
  startMs: number | null;
  offsetHours: number;
  maxOffsetHours: number;
  heatmapHour: number;
  /** Arrival of the selected route, in hours after the forecast start. */
  arrivalOffsetHours: number | null;
  isTripOnly: boolean;
  canTripOnly: boolean;
  setTripOnly: (tripOnly: boolean) => void;
  truck: TruckState | null;
  isPlaying: boolean;
  togglePlay: () => void;
  pause: () => void;
  previous: Checkpoint | null;
  next: Checkpoint | null;
  goToCheckpoint: (index: number) => void;
  scrub: (hours: number) => void;
  reset: () => void;
  note: string | null;
}

/**
 * Forecast time shared by the heatmap, the truck marker and the checkpoint popups: scrubbing,
 * stepping between checkpoints, and playback, which steps through every checkpoint in ETA order.
 */
export function usePlayback(
  route: Route | undefined,
  heatmap: Heatmap | undefined,
  onCheckpoint: (index: number) => void,
): Playback {
  const [requestedHours, setRequestedHours] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isTripOnly, setTripOnly] = useState(false);

  const startMs = heatmap ? Date.parse(heatmap.start_time) : null;
  const windowHours = heatmap ? heatmap.hours - 1 : 48;
  const arrivalOffsetHours =
    route && startMs !== null ? hoursBetween(new Date(startMs), new Date(route.arrival)) : null;
  const maxOffsetHours = sliderMaxHours(windowHours, arrivalOffsetHours, isTripOnly, SLIDER_STEP_HOURS);
  // Clamped at read time: switching to trip-only or a shorter route never leaves it past the end.
  const offsetHours = Math.min(requestedHours, maxOffsetHours);

  const now = startMs !== null ? new Date(startMs + offsetHours * 3_600_000) : null;
  const windowEnd = startMs !== null ? new Date(startMs + maxOffsetHours * 3_600_000) : null;
  const next = route && now && windowEnd ? nextCheckpoint(route, now, windowEnd) : null;
  const previous = route && now ? previousCheckpoint(route, now) : null;

  const truck = useMemo(
    () =>
      route && startMs !== null ? truckStateAt(route, new Date(startMs + offsetHours * 3_600_000)) : null,
    [route, startMs, offsetHours],
  );

  const goToCheckpoint = useCallback(
    (index: number) => {
      const checkpoint = route?.checkpoints[index];
      if (!checkpoint || startMs === null) return;
      setRequestedHours(hoursBetween(new Date(startMs), new Date(checkpoint.eta)));
      onCheckpoint(index);
    },
    [route, startMs, onCheckpoint],
  );

  useEffect(() => {
    if (!isPlaying) return;
    const timer = window.setTimeout(() => {
      if (next) goToCheckpoint(next.index);
      else setIsPlaying(false);
    }, PLAYBACK_STEP_MS);
    return () => window.clearTimeout(timer);
  }, [isPlaying, next, goToCheckpoint]);

  const togglePlay = () => {
    if (isPlaying) return setIsPlaying(false);
    if (!route || startMs === null) return;
    // Finished (or past the forecast window): replay from the first checkpoint.
    if (!next) goToCheckpoint(0);
    setIsPlaying(true);
  };

  const pause = useCallback(() => setIsPlaying(false), []);
  const scrub = useCallback((hours: number) => {
    setIsPlaying(false);
    setRequestedHours(hours);
  }, []);
  const reset = useCallback(() => {
    setIsPlaying(false);
    setRequestedHours(0);
  }, []);

  const last = route?.checkpoints[route.checkpoints.length - 1];
  const note =
    last && windowEnd && Date.parse(last.eta) > windowEnd.getTime() && truck?.status !== "waiting"
      ? "Trip runs past the 48 h forecast window"
      : null;

  return {
    startMs,
    offsetHours,
    maxOffsetHours,
    heatmapHour: Math.floor(offsetHours + 1e-9),
    arrivalOffsetHours,
    isTripOnly,
    canTripOnly: arrivalOffsetHours !== null && arrivalOffsetHours < windowHours,
    setTripOnly,
    truck,
    isPlaying,
    togglePlay,
    pause,
    previous,
    next,
    goToCheckpoint,
    scrub,
    reset,
    note,
  };
}
