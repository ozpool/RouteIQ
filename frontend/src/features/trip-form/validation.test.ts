import { describe, expect, it } from "vitest";
import type { Place } from "../../api/types";
import { departureError, loadError, validateTripForm } from "./validation";

const now = new Date("2026-10-23T12:00:00Z");
const dallas: Place = { label: "Dallas", lat: 32.7767, lon: -96.797 };
const chicago: Place = { label: "Chicago", lat: 41.8781, lon: -87.6298 };
const valid = { origin: dallas, destination: chicago, departure: "2026-10-23T14:00", load: "42000" };

describe("loadError", () => {
  it.each(["1", "42000", "80000"])("accepts %s lb", (load) => {
    expect(loadError(load)).toBeUndefined();
  });

  it.each(["0", "80001", "88000", "-5"])("rejects %s lb with the range", (load) => {
    expect(loadError(load)).toBe("Must be between 1 and 80,000 lb.");
  });

  it("asks for a value when empty and a number when not numeric", () => {
    expect(loadError("")).toBe("Enter the load weight.");
    expect(loadError("abc")).toBe("Enter a number of pounds.");
  });
});

describe("departureError", () => {
  it("allows up to 1 hour in the past and 7 days ahead", () => {
    expect(departureError("2026-10-23T11:30:00Z", now)).toBeUndefined();
    expect(departureError("2026-10-30T11:00:00Z", now)).toBeUndefined();
  });

  it("rejects older or later departures and empty input", () => {
    expect(departureError("2026-10-23T10:00:00Z", now)).toBe("Can't be more than 1 hour in the past.");
    expect(departureError("2026-10-31T12:00:00Z", now)).toBe("Must be within the next 7 days.");
    expect(departureError("", now)).toBe("Enter a date and time.");
  });
});

describe("validateTripForm", () => {
  it("has no errors for a valid trip", () => {
    expect(validateTripForm({ ...valid, departure: "2026-10-23T14:00:00Z" }, now, true)).toEqual({});
  });

  it("flags unpicked places only after a submit attempt", () => {
    const empty = { ...valid, origin: null, destination: null, departure: "2026-10-23T14:00:00Z" };
    expect(validateTripForm(empty, now, false)).toEqual({});
    expect(validateTripForm(empty, now, true)).toEqual({
      origin: "Pick the origin from the list.",
      destination: "Pick the destination from the list.",
    });
  });

  it("flags the same place twice while typing", () => {
    const same = { ...valid, destination: { ...dallas, label: "Dallas again" }, departure: "2026-10-23T14:00:00Z" };
    expect(validateTripForm(same, now, false).destination).toBe("Must be at least 1 mile from the origin.");
  });
});
