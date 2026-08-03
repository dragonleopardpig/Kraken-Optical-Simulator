# 0521 — DESIGN: pick cycling for the Object/FOV plane buried in the LED STEP

## Request

User (2026-08-03): "the FOV plane is very near the LED STEP, I have to every time zoom in
enough for me to correctly pick and click the Object plane, otherwise, the LED STEP has
high probability get selected. Any better way?"

## Design (not yet implemented)

CAD-standard **click-through cycling**: clicking the SAME screen spot again picks the next
candidate under the cursor. First click → the LED STEP body (today's behaviour, unchanged);
second click at the same spot → the Object/FOV plane behind it; third → next candidate;
wraps around. No new modifier (Shift is multi-select, Alt is the edge-pick contract,
bugs/0323/0324).

Implementation sketch: remember the last pick (screen point ± ~6 px, picked prop). On a
repeat click within tolerance, temporarily `PickableOff()` the previously picked actor(s),
re-run the pick, restore pickability — cycles through overlapping candidates without any
geometric heuristics (the 0323 lesson: don't guess which actor the user "meant"). Status
line names what was picked each time so the cycle is legible. Guard: a probe that fires two
synthetic picks at one screen point over the LED/FOV overlap and asserts the second pick
lands the Object plane row.

Interim workaround (already shipped behaviour): right-click → Scene Components lists every
row/plane for direct selection without zooming (bugs/0403 consolidation).
