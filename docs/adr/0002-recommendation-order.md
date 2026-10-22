# 2. Lexicographic recommendation, No Travel first

Date: 2026-10-22 · Status: accepted

## Context
The brief lists route preferences in order: fewest Severe miles, fewest High miles, lowest
average risk, shortest time. It does not say where No Travel miles go, and it asks to balance
risk and time.

## Decision
Sort by `(No Travel mi, Severe mi, High mi, average risk, duration)`, comparing miles at 0.1 mi
and average risk at 0.01 so float noise never decides. The UI shows the first criterion that
separated the winner from the runner-up.

A segment between two checkpoints takes the worse of the two levels (conservative).

## Consequences
- Fully explainable: every recommendation comes with a one-line reason.
- A route can win while being hours slower. That follows the brief's order on purpose; the
  reason text makes the trade visible.
- If even the best route crosses No Travel or Severe conditions, a warning is shown.
