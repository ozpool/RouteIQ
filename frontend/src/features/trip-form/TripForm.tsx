import { type FormEvent, memo, useState } from "react";
import type { CheckpointInterval, Place, PlanTripRequest } from "../../api/types";
import { localZoneName, nextQuarterHour, toLocalInputValue } from "../../domain/format";
import { FieldError, invalidProps } from "./FieldError";
import { PlaceInput } from "./PlaceInput";
import { MAX_DAYS_AHEAD, MAX_LOAD_LB, type TripFormErrors, validateTripForm } from "./validation";

const INTERVALS: CheckpointInterval[] = [10, 25, 50];
const FIELD_IDS: Record<keyof TripFormErrors, string> = {
  origin: "origin",
  destination: "destination",
  departure: "departure",
  load: "load",
};

interface TripFormProps {
  isSubmitting: boolean;
  onSubmit: (request: PlanTripRequest) => void;
  origin: Place | null;
  destination: Place | null;
  onOriginChange: (place: Place | null) => void;
  onDestinationChange: (place: Place | null) => void;
}

export const TripForm = memo(function TripForm({
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
  const [hasTriedSubmit, setHasTriedSubmit] = useState(false);

  const now = new Date();
  const errors = validateTripForm({ origin, destination, departure, load }, now, hasTriedSubmit);
  const minDeparture = toLocalInputValue(new Date(now.getTime() - 60 * 60_000));
  const maxDeparture = toLocalInputValue(new Date(now.getTime() + MAX_DAYS_AHEAD * 86_400_000));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setHasTriedSubmit(true);
    const finalErrors = validateTripForm({ origin, destination, departure, load }, new Date(), true);
    const firstInvalid = (Object.keys(FIELD_IDS) as (keyof TripFormErrors)[]).find((key) => finalErrors[key]);
    if (firstInvalid || !origin || !destination) {
      if (firstInvalid) document.getElementById(FIELD_IDS[firstInvalid])?.focus();
      return;
    }
    onSubmit({
      origin,
      destination,
      departure_time: new Date(departure).toISOString(),
      load_weight_lb: Number(load),
      checkpoint_interval_mi: interval,
    });
  };

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceInput
        id={FIELD_IDS.origin}
        label="Origin"
        value={origin}
        onChange={onOriginChange}
        placeholder="e.g. Chicago, IL"
        error={errors.origin}
      />
      <PlaceInput
        id={FIELD_IDS.destination}
        label="Destination"
        value={destination}
        onChange={onDestinationChange}
        placeholder="e.g. St. Louis, MO"
        error={errors.destination}
      />
      <div className="field-row">
        <div className="field">
          <label htmlFor={FIELD_IDS.departure}>Departure ({localZoneName()})</label>
          <input
            id={FIELD_IDS.departure}
            type="datetime-local"
            value={departure}
            min={minDeparture}
            max={maxDeparture}
            onChange={(event) => setDeparture(event.target.value)}
            required
            {...invalidProps(FIELD_IDS.departure, errors.departure)}
          />
          <FieldError id={FIELD_IDS.departure} message={errors.departure} />
        </div>
        <div className="field">
          <label htmlFor={FIELD_IDS.load}>Load weight (lb)</label>
          <input
            id={FIELD_IDS.load}
            type="number"
            inputMode="numeric"
            min={1}
            max={MAX_LOAD_LB}
            step={500}
            value={load}
            onChange={(event) => setLoad(event.target.value)}
            required
            {...invalidProps(FIELD_IDS.load, errors.load)}
          />
          <FieldError id={FIELD_IDS.load} message={errors.load} />
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
      <button type="submit" className="button button--primary" disabled={isSubmitting}>
        {isSubmitting ? "Checking routes and forecast…" : "Find safest route"}
      </button>
    </form>
  );
});
