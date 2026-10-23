/** The message under a field. Always rendered so `aria-live` announces it when it appears. */
export function FieldError({ id, message }: { id: string; message: string | undefined }) {
  return (
    <p id={`${id}-error`} className="field__error" aria-live="polite">
      {message}
    </p>
  );
}

/** Marks an input invalid and points screen readers at its message, only while there is one. */
export function invalidProps(id: string, message: string | undefined) {
  return message ? { "aria-invalid": true, "aria-describedby": `${id}-error` } : {};
}
