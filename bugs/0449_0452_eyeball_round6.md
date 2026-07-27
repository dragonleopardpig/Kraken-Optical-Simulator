# 0449–0452 — Eyeball round 6 ("too many bugs"): one cascade, not four failures

Recording `recording_20260726_191552.json` + 4 flags on build `aa978f49`. The user
stopped testing: *"Unable to test further, too many bugs."* The forensics show a
**cascade from two defects**, not four independent ones — worth stating plainly because
it changes what had to be fixed.

| flag | what it really was |
|---|---|
| "original with ray on" | **healthy baseline** — the pristine folded scene traces a dense, coherent bundle into the sensor |
| "after RA mirror deletion" | the freeze worked (chain, barrel, camera all stayed); the straight beam is physically right. Only a synthesized detector drew a phantom "Sensor 23×23 / Image circle" ring inside the LED, with pale ray styling → **0451** |
| "adding BS not showing up… add another… Undo, Undo. Surrogate get separated" | **0450 → 0449 cascade**: the add was invisible (rays ON), so the user added a second one; then Undo restored a mid-command intermediate |
| "rubberband snap" | snapping the torn scene scattered the block — garbage-in. The snap should have **refused** → **0452** |

## 0449 — one user action must be ONE undo step (the root)

`add_beam_splitter_to_led` fires a CHAIN of service-level `_begin/_commit_history_capture`
pairs (import overlay → centre CA → orient → seat → glue → promote → coating flag →
station-neutralize). Each pushed its own snapshot, so the first Undo restored a
**mid-command intermediate the user never saw**: rows at the un-neutralized stations
(z=115.5, i.e. *before* 0435's neutralization) with the lens barrel still seated at
z=53. The snapshot CONTENT was never the problem — `_capture_editor_state` already
carries rows + layout settings together — the COUNT was.

Fix: `_history_atomic`, a `functools.wraps` decorator opening one `history_transaction()`
around a public command; inner pairs no-op while it is open and ONE snapshot is pushed at
the outermost exit. Reentrant and restore-safe; plain table edits unchanged. The decorator
form is deliberate: three guards assert on `inspect.getsource(add_beam_splitter_to_led)`,
and `getsource` unwraps `__wrapped__`, so they keep reading the real body.

**Second defect found by its own guard**: the settings SERVICE cannot write the editor's
`_`-prefixed state (its `__setattr__` routes those onto itself — the delegation trap of
bugs/0306 + 0312), so `self._optical_led_glued = …` inside `_apply_layout_settings` was
dead for the editor. Undo restored the persisted glue value while the LIVE flag stayed
stale. Re-asserted editor-side, where the write lands.

## 0450 — a model change with rays ON must paint immediately

`refresh_from_editor`'s async branch (bugs/0223) kicked the background worker and returned
having painted **nothing**, so with Show Rays ON the new BS existed only in the rows until
the long folded trace applied. Rays OFF took the 0400 sync bodies-only path and appeared
at once — hence "add another one, ray off, BS shows up". The async kick now paints a
BODIES-ONLY scene synchronously (new `bodies_only` flag on `build_inspector_refresh`;
geometry is cheap, only the trace is slow) and the worker's rays replace it on arrival.
Preview failures are swallowed — the worker's own refresh still lands.

## 0452 — a snap must refuse a torn selection

With the front datum bent off the block, the first→last fit ran corner-to-corner **through
the bend** (48.7°). The transform stayed rigid, so the preserved internal bend *read* as
scatter. Rigid-from-garbage is still garbage: reference members' perpendicular deviation
from the fit line is measured and a non-collinear selection is REFUSED, naming the
offending rows and moving nothing. Tolerance `max(2 mm, 2 % of span)` — sub-mm intentional
decenters pass, the flag's 28 mm tear is unmistakably rejected. The 0439 translate-only
path and sane folded snaps are untouched.

## 0451 — still open

Phantom straight-arm coverage ring + pale ray styling after the mirror delete. Its fork
had completed the anatomy (the ring is a synthesized detector for a terminal
**non-reaching** arm — distinct from 0448's vignette-dominated *reaching* leaf) but was
killed before the draw-gate landed. The rule to implement: gate the DRAW for an arm that
carries no image while keeping its ray HARD-STOP (the 0182 lesson — dropping the target
un-bounds rays into a starburst).

## Verification

Probes `bugs/probe_0449_undo_atomicity.py` (replays the flag's add,add,undo,undo plus
redo round-trips, asserting the barrel stays attached at every stop),
`probe_0450_bs_add_rays_on.py`, `probe_0452_snap_collinearity.py` (replays the torn
geometry and asserts refusal with zero mutations). Penta phases 365-367.
