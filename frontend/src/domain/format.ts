const timeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  hour: "numeric",
  minute: "2-digit",
});

const zoneFormat = new Intl.DateTimeFormat(undefined, { timeZoneName: "short" });

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? `${hours}h ${String(minutes).padStart(2, "0")}m` : `${minutes}m`;
}

export function formatMiles(miles: number): string {
  return `${miles.toLocaleString(undefined, { maximumFractionDigits: miles < 100 ? 1 : 0 })} mi`;
}

export function formatClock(iso: string | Date): string {
  return timeFormat.format(typeof iso === "string" ? new Date(iso) : iso);
}

export function localZoneName(): string {
  return zoneFormat.formatToParts(new Date()).find((p) => p.type === "timeZoneName")?.value ?? "";
}

/** `YYYY-MM-DDTHH:mm` in local time, the format <input type="datetime-local"> expects. */
export function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

export function nextQuarterHour(from = new Date()): Date {
  const date = new Date(from);
  date.setSeconds(0, 0);
  date.setMinutes(Math.ceil((date.getMinutes() + 1) / 15) * 15);
  return date;
}
