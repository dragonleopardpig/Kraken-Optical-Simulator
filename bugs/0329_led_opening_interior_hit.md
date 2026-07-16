# 0329 — highlight the clear-aperture opening when the cursor is INSIDE it (interior-hit "complement")

## Flag / redirect
After 0328 shipped (plain hover snaps to the nearest *closed opening loop*, so the central emitting
square became a first-class hover target) the user re-tested on a **fresh** app and recorded
`flag_20260716_150110_640`:

> still can't highlight it

then, when I suspected a stale app:

> restarted the app, still can't highlight it. Actually, I quit Kitty and restart for every single test.

and finally the observation that pointed straight at the fix:

> previously when I orbit I can get the Face highlight, but not every time … I noticed previous
> successful face highlighted, the face can highlight leaving the Clear Aperture Opening **not**
> highlighted. That means it is possible to highlight, **just complement it** I guess.

So the whole front-panel face (F005 in the tooltip) *does* highlight — with the opening left as a
see-through **hole**. The opening the user is pointing **into** never lights up. "Complement it" =
highlight the opening, not the panel around it.

## Root cause — 0328's rim proximity is a knife-edge on a WIDE opening
0328's `nearest_opening_loop` snaps by **rim proximity only** (`nearest_display_edge`, tolerance
~30 px). That is fine for a thin slot, whose whole interior is within 30 px of an edge. But the
central emitting square is a **wide** opening: it projects ~200 px across (bbox `x[781,983] y[400,612]`
on the recorded camera), so hovering its **middle** — the natural gesture — sits **~90–100 px** from
any rim, far outside the 30 px snap. The mined loop is right there, but the rim test returns None, and
hover falls through to the per-cell pick → the **whole front panel** (tooltip `('step','led','F005')`),
which highlights with the opening as a hole. Exactly the user's "the face highlights, the opening
doesn't."

Why every earlier harness passed at the *recorded* cursor: `vtk_xy = [886, 607]` happens to land on
the square's **top rim** (~3 px away), so rim proximity fired and both the offscreen and the real
inspector-under-Xvfb returned the square (F053). The recorded cursor was never the failing gesture —
the failing gesture is the **interior hover**, which rim-only always missed everywhere.

## Fix — a containment fallback (rim proximity stays first)
`KrakenOS/UI/services/open3d_opening_loops.py`, `nearest_opening_loop`:

1. **Rim proximity stays FIRST**, unchanged — so 0328 is preserved exactly (the recorded rim cursor
   still snaps to the square; a thin opening's edge still snaps from outside). Rim ties still break
   toward the **smaller** opening via the `(edge_distance, loop.area)` rank.
2. **Interior-hit fallback**: when *no* rim is within tolerance, project each in-gate loop's rim to a
   screen-space polygon (`_project_polygon`) and test whether the cursor is **inside** it
   (`_point_in_polygon`, even-odd ray cast). Snap to the containing opening whose projected **centroid
   is nearest** the cursor.
   - Nearest-centroid, **not smallest-area**: an early smallest-area tiebreak regressed the recorded
     cursor to a thin background slot (`perim≈365`) whose projected polygon also happened to contain
     the point. Nearest-centroid picks the aperture the user is actually pointing *into*.
3. Return `rim_best if rim_best is not None else inside_best` — rim wins whenever it fires; containment
   only covers the open middle.

No wiring change downstream: `_opening_loop_hover_pick` → `_step_opening_hover_pick` →
`step_feature_pick_for_display_xy` already route plain hover through `nearest_opening_loop`, and
`_opening_loop_hover_feature` returns the same line-rim overlay with `face_id = F%03d`.

## Verified (display-free + offscreen + real inspector under Xvfb)
- **`bugs/diag_0329_interior.py`** (offscreen VTK projector on the **real** ILS0202 LED, recorded
  camera; no Xvfb) — `square proj-centroid=(882,506)`, and `nearest_opening_loop`:
  **square-center (interior) → SQUARE**, **recorded cursor [886,607] → SQUARE**, **off-body → None** →
  `RESULT: PASS`. The interior center is exactly where the old rim-only snap returned None.
- **`bugs/diag_0329_realinspector.py`** (the **real** `Kraken3DInspector` headless under a private
  Xvfb, full live pick path incl. `_picker.Pick` + `_step_feature_pick_for_display_xy`) — both
  `recorded rim cursor (886,607)` and `square center (882,506)` resolve `FULL_pick=F053` (the square),
  not F005 (the panel). Proves the fix through the exact live entry point, not just a harness stand-in.
- **`KrakenOS/UI/validate_open3d_led_opening_loop_hover.py`** — **PASS**, checks reframed for 0329:
  **A** the square is mined (`F053`, 176.6 mm) and its face's outer silhouette dropped; **B** its hover
  feature is a LINE-loop overlay with a finite centroid/normal and an `F%03d` id; **C** a near-rim
  cursor (no `cell_id`) still snaps to it (0328 preserved); **D** *new* — the hole **CENTRE** (inside
  the projected polygon, far from every rim) now **snaps to the square** (the interior hit); **E** an
  off-body cursor stays selective (no snap).
- **`KrakenOS/UI/validate_open3d_led_ca_edge_hover.py`** (0326/0327/0328 guard) — still **PASS**; its
  selectivity check uses a far off-body cursor (1e5 px), which is neither near a rim nor inside any
  polygon, so the containment fallback correctly stays silent.
- Penta **phase 290** (`phase_290_led_opening_loop_hover`) delegates to the reframed guard; baseline
  stays `"290": "pass"` (the same phase, extended — no new phase number).

## Notes / remaining
- **In-app eyeball owed** (needs a GLX display this box lacks): import the LED, hover the **open
  middle** of the central emitting square from several orbit angles and confirm the opening rim
  highlights (and a click selects it) instead of the surrounding panel.
- The containment loop reuses the existing `gate_px = 260 px` centroid gate, so interior hits are only
  considered for openings whose centroid is reasonably near the cursor — cheap, and comfortably covers
  the square (max interior centroid distance ~145 px on the recorded camera).
- Generalises for free: an **LED-with-BS** has two clear-aperture openings (bugs/0319) — both are mined
  loops, so hovering the open middle of either now highlights that opening.
- **Memory correction logged**: I first dismissed this flag as a stale app (recording captured ~6 min
  after the 0328 commit). The user restarts for **every** test, so staleness is never the answer for
  them — a headless-passing/live-failing case means my **harness diverged from the failing gesture**,
  not that the app is stale. (feedback_stale_app_recording.md updated.)
- Still paused (not touched here): the phantom whole-face fill (bugs/0325) and the Alt-live gremlin
  (bugs/0324).

## Files
- `KrakenOS/UI/services/open3d_opening_loops.py` — `nearest_opening_loop` rim-first + **containment
  fallback**; new `_project_polygon` / `_point_in_polygon` helpers; docstring updated.
- `KrakenOS/UI/validate_open3d_led_opening_loop_hover.py` — guard reframed: D = interior hole-centre
  snaps to the square, E = off-body selective; PASS/name text mentions 0328 + 0329.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_290` docstring + name updated
  for the interior-hit check (delegates to the same guard).
- `tools/penta_validator_baseline.json` — phase-290 title reworded; `"290": "pass"` unchanged.
- `bugs/diag_0329_interior.py`, `bugs/diag_0329_realinspector.py` — end-to-end proofs (offscreen +
  real-inspector-under-Xvfb).
