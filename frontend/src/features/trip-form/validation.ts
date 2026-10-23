import type { Place } from "../../api/types";
import { distanceMiles } from "../../domain/truckPosition";

// Same limits the API enforces, so a form that passes here is never rejected for them.
export const MAX_LOAD_LB = 80_000;
export const MAX_DAYS_AHEAD = 7;
const MAX_HOURS_PAST = 1;
const MIN_TRIP_MI = 1;

export interface TripFormValues {
  origin: Place | null;
  destination: Place | null;
  departure: string;
  load: string;
}

export type TripFormErrors = Partial<Record<keyof TripFormValues, string>>;

export function loadError(load: string): string | undefined {
  if (load.trim() === "") return "Enter the load weight.";
  const pounds = Number(load);
  if (!Number.isFinite(pounds)) return "Enter a number of pounds.";
  if (pounds < 1 || pounds > MAX_LOAD_LB) return `Must be between 1 and ${MAX_LOAD_LB.toLocaleString()} lb.`;
  return undefined;
}

export function departureError(departure: string, now: Date): string | undefined {
  const time = new Date(departure).getTime();
  if (departure === "" || Number.isNaN(time)) return "Enter a date and time.";
  if (time < now.getTime() - MAX_HOURS_PAST * 3_600_000) return "Can't be more than 1 hour in the past.";
  if (time > now.getTime() + MAX_DAYS_AHEAD * 86_400_000) return `Must be within the next ${MAX_DAYS_AHEAD} days.`;
  return undefined;
}

/**
 * Field errors for the trip form. Typed values (load, departure, same place twice) are checked
 * as the user types; an unpicked place only counts once the user has tried to submit, because
 * a half-typed place name is normal while searching.
 */
export function validateTripForm(values: TripFormValues, now: Date, hasTriedSubmit: boolean): TripFormErrors {
  const errors: TripFormErrors = {};
  const load = loadError(values.load);
  if (load) errors.load = load;
  const departure = departureError(values.departure, now);
  if (departure) errors.departure = departure;

  const { origin, destination } = values;
  if (origin && destination) {
    const miles = distanceMiles([origin.lon, origin.lat], [destination.lon, destination.lat]);
    if (miles < MIN_TRIP_MI) errors.destination = "Must be at least 1 mile from the origin.";
  }
  if (hasTriedSubmit) {
    if (!origin) errors.origin = "Pick the origin from the list.";
    if (!destination) errors.destination = "Pick the destination from the list.";
  }
  return errors;
}
