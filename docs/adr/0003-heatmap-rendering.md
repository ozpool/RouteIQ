# 3. Heatmap as a GPU grid with all hours preloaded

Date: 2026-10-22 · Status: accepted

## Context
The heatmap needs a smooth 0–48 h slider along the trip corridor. Density heatmaps (Leaflet.heat,
MapLibre `heatmap` layers) add up overlapping points, so two Moderate cells next to each other
would look Severe. That would misstate risk.

## Decision
- The API returns corridor cells (finest grid from 0.2° up that fits 400 cells) and the risk
  score for each of 49 hours in one compact response.
- The SPA turns cells into fill polygons once, with `h0…h48` as feature properties.
- The slider changes only the layer's `fill-color` match expression. No data is re-sent to the
  GPU and no request is made.

## Consequences
- Colours show the real level of each cell; no false hot spots.
- Slider and play animation are a paint-property swap, which redraws in one frame.
- Cells look blocky at high zoom; that is honest about the forecast resolution.
