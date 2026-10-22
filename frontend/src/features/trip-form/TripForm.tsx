import { type FormEvent, useState } from "react";
import type { CheckpointInterval, Place, PlanTripRequest } from "../../api/types";
import { localZoneName, nextQuarterHour, toLocalInputValue } from "../../domain/format";
import { PlaceInput } from "./PlaceInput";

const INTERVALS: CheckpointInterval[] = [10, 25, 50];
const MAX_LOAD_LB = 80_000;
const MAX_DAYS_AHEAD = 7;

interface TripFormProps {
  isSubmitting: boolean;
  onSubmit: (request: PlanTripRequest) => void;
  origin: Place | null;
  destination: Place | null;
  onOriginChange: (place: Place | null) => void;
  onDestinationChange: (place: Place | null) => void;
}

export function TripForm({
  isSubmitting,
  onSubmit,
  origin,
  destination,
  onOriginChange,
  onDestinationChange,
}: TripFormProps) {
  const [departure, setDeparture] = useState(() => toLocalInputValue(nextQuarterHour()));
  const [load, setLoad] = useState("42000");
  const [interval, setCheckpointInterval] = useState<CheckpointInterval>(25);
  const [error, setError] = useState<string | null>(null);

  const minDeparture = toLocalInputValue(new Date(Date.now() - 60 * 60_000));
  const maxDeparture = toLocalInputValue(new Date(Date.now() + MAX_DAYS_AHEAD * 86_400_000));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const loadLb = Number(load);
    const departureDate = new Date(departure);
    if (!origin || !destination) return setError("Pick an origin and a destination from the list.");
    if (!Number.isFinite(loadLb) || loadLb < 1 || loadLb > MAX_LOAD_LB)
      return setError(`Load must be between 1 and ${MAX_LOAD_LB.toLocaleString()} lb.`);
    if (Number.isNaN(departureDate.getTime())) return setError("Enter a departure date and time.");
    setError(null);
    onSubmit({
      origin,
      destination,
      departure_time: departureDate.toISOString(),
      load_weight_lb: loadLb,
      checkpoint_interval_mi: interval,
    });
  };

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceInput label="Origin" value={origin} onChange={onOriginChange} placeholder="e.g. Chicago, IL" />
      <PlaceInput
        label="Destination"
        value={destination}
        onChange={onDestinationChange}
        placeholder="e.g. St. Louis, MO"
      />
      <div className="field-row">
        <div className="field">
          <label htmlFor="departure">Departure ({localZoneName()})</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            min={minDeparture}
            max={maxDeparture}
            onChange={(event) => setDeparture(event.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={1}
            max={MAX_LOAD_LB}
            step={500}
            value={load}
            onChange={(event) => setLoad(event.target.value)}
            required
          />
        </div>
      </div>
      <fieldset className="field segmented">
        <legend>Check weather every</legend>
        {INTERVALS.map((value) => (
          <label key={value} className={interval === value ? "is-checked" : undefined}>
            <input
              type="radio"
              name="interval"
              value={value}
              checked={interval === value}
              onChange={() => setCheckpointInterval(value)}
            />
            {value} mi
          </label>
        ))}
      </fieldset>
      {error && (
        <p className="alert alert--error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="button button--primary" disabled={isSubmitting}>
        {isSubmitting ? "Checking routes and forecast…" : "Find safest route"}
      </button>
    </form>
  );
}
