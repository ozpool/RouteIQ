import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import type { Place } from "../../api/types";
import { geocode } from "../../api/trips";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";

interface PlaceInputProps {
  label: string;
  value: Place | null;
  onChange: (place: Place | null) => void;
  placeholder: string;
}

export function PlaceInput({ label, value, onChange, placeholder }: PlaceInputProps) {
  const id = useId();
  const listId = `${id}-options`;
  const [text, setText] = useState(value?.label ?? "");
  const [isOpen, setIsOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const query = useDebouncedValue(text.trim(), 300);
  const isSearching = isOpen && query.length >= 2 && query !== value?.label;

  const { data: options = [], isFetching, isError } = useQuery({
    queryKey: ["geocode", query],
    queryFn: ({ signal }) => geocode(query, signal),
    enabled: isSearching,
    staleTime: 10 * 60_000,
  });

  const choose = (place: Place) => {
    onChange(place);
    setText(place.label);
    setIsOpen(false);
  };

  return (
    <div className="field place-input">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={isOpen && options.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder={placeholder}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setHighlight(0);
          setIsOpen(true);
          if (value) onChange(null);
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => window.setTimeout(() => setIsOpen(false), 120)}
        onKeyDown={(event) => {
          const isStale = query !== text.trim() || isFetching;
          if (event.key === "Enter" && !value && text.trim()) {
            // Never submit the form with an unresolved place, nor pick from an older query.
            event.preventDefault();
            if (isStale) return;
          }
          if (!isOpen || options.length === 0) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setHighlight((h) => (h + 1) % options.length);
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setHighlight((h) => (h - 1 + options.length) % options.length);
          } else if (event.key === "Enter") {
            const option = options[highlight];
            if (option) {
              event.preventDefault();
              choose(option);
            }
          } else if (event.key === "Escape") {
            setIsOpen(false);
          }
        }}
      />
      {isSearching && (
        <ul id={listId} role="listbox" className="place-input__options">
          {isFetching && options.length === 0 && <li className="muted">Searching…</li>}
          {isError && <li className="muted">Place search is unavailable.</li>}
          {!isFetching && !isError && options.length === 0 && <li className="muted">No matches</li>}
          {options.map((option, i) => (
            <li
              key={`${option.label}-${option.lat}-${option.lon}`}
              role="option"
              aria-selected={i === highlight}
              className={i === highlight ? "is-highlighted" : undefined}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(option);
              }}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
