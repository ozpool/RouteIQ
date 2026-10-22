interface PublicEnv {
  apiBaseUrl: string;
  mapStyleUrl: string;
}

const DEFAULT_MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

function readEnv(): PublicEnv {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  const mapStyleUrl = import.meta.env.VITE_MAP_STYLE_URL || DEFAULT_MAP_STYLE;
  return { apiBaseUrl, mapStyleUrl };
}

export const env = readEnv();
