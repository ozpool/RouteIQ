import {
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

export const DEFAULT_PANEL_WIDTH = 440;
const MIN_PANEL_WIDTH = 360;
const MAX_PANEL_WIDTH = 760;
// The map stays usable next to a wide sidebar.
const MIN_MAP_WIDTH = 360;
const KEYBOARD_STEP = 24;
const STORAGE_KEY = "routeiq.panelWidth";

function maxPanelWidth(): number {
  return Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, window.innerWidth - MIN_MAP_WIDTH));
}

function clampWidth(width: number): number {
  return Math.round(Math.min(maxPanelWidth(), Math.max(MIN_PANEL_WIDTH, width)));
}

function readStoredWidth(): number {
  try {
    const stored = Number(window.localStorage.getItem(STORAGE_KEY));
    return stored > 0 ? stored : DEFAULT_PANEL_WIDTH;
  } catch {
    // Storage can be blocked (private mode, site data off); the default width is fine then.
    return DEFAULT_PANEL_WIDTH;
  }
}

function storeWidth(width: number): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(width));
  } catch {
    // Blocked storage only means the width is not remembered next visit.
  }
}

/**
 * Sidebar width set by dragging a separator. While dragging, the width is written straight to the
 * container's `--panel-width` so the app does not re-render on every pointer move; it is committed
 * to state (and remembered) when the drag ends.
 */
export function useResizablePanel() {
  const containerRef = useRef<HTMLDivElement>(null);
  const draftWidth = useRef(0);
  const [width, setWidth] = useState(() => clampWidth(readStoredWidth()));
  const [isResizing, setIsResizing] = useState(false);

  const preview = useCallback((next: number) => {
    containerRef.current?.style.setProperty("--panel-width", `${next}px`);
  }, []);

  const commit = useCallback(
    (next: number) => {
      const clamped = clampWidth(next);
      preview(clamped);
      setWidth(clamped);
      storeWidth(clamped);
    },
    [preview],
  );

  useEffect(() => {
    const keepInBounds = () => setWidth((current) => clampWidth(current));
    window.addEventListener("resize", keepInBounds);
    return () => window.removeEventListener("resize", keepInBounds);
  }, []);

  const widthAt = (clientX: number) =>
    clampWidth(clientX - (containerRef.current?.getBoundingClientRect().left ?? 0));

  const handleProps = {
    role: "separator",
    tabIndex: 0,
    "aria-orientation": "vertical" as const,
    "aria-label": "Resize sidebar",
    "aria-valuenow": width,
    "aria-valuemin": MIN_PANEL_WIDTH,
    "aria-valuemax": maxPanelWidth(),
    title: "Drag to resize · double-click to reset",
    onPointerDown: (event: PointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) return;
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      draftWidth.current = width;
      setIsResizing(true);
    },
    onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
      if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
      draftWidth.current = widthAt(event.clientX);
      preview(draftWidth.current);
    },
    onLostPointerCapture: () => {
      setIsResizing(false);
      commit(draftWidth.current);
    },
    onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => {
      const next = {
        ArrowLeft: width - KEYBOARD_STEP,
        ArrowRight: width + KEYBOARD_STEP,
        Home: MIN_PANEL_WIDTH,
        End: maxPanelWidth(),
      }[event.key];
      if (next === undefined) return;
      event.preventDefault();
      commit(next);
    },
    onDoubleClick: () => commit(DEFAULT_PANEL_WIDTH),
  };

  return {
    containerRef,
    containerStyle: { "--panel-width": `${width}px` } as CSSProperties,
    isResizing,
    handleProps,
  };
}
