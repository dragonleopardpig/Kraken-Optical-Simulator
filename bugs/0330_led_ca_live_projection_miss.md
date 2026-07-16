# 0330 — LED clear-aperture square resolves the whole panel LIVE (a live-only projection miss) — DIAGNOSIS + INSTRUMENTATION

## RESOLUTION (2026-07-16, `flag_20260716_170326_798` read with the new instrumentation) — NOT A PICK BUG
The instrumented flag settled it, and it was **not** a projection/size/DPI miss and **not** a pick-logic
miss. All three sizes AGREE (`render_window == renderer_viewport == widget_logical == [1163,904]`), which
kills the size/DPI theory from the diagnosis below. The decisive anomaly: the opening pick's stash ran at
`cursor_xy=[1019,402]` with `chosen_face_index=null`, while the user's flag cursor was `vtk_xy=[432,652]`
(on the square F053) — **590 px apart.**

Two display-free / real-inspector probes resolve the fork projection-bug vs cursor-plumbing:
- `bugs/diag_0330b_flag798.py` (offscreen VTK, no Xvfb): at the flag camera+size the square F053 projects to
  bbox `x[430,636] y[450,659]` — exactly where the screenshot draws it — and `nearest_opening_loop([432,652])`
  → **SQUARE**, `nearest_opening_loop([1019,402])` → **None**. So the projection is correct.
- `bugs/diag_0330c_flag798_live.py` (REAL `Kraken3DInspector` under Xvfb, analytic pick): at `[432,652]`
  **every** path returns **F053** — `_step_feature_pick_for_display_xy` (raw, actor=None), stash
  `cursor=[432,652] chosen=53`, `_step_feature_pick_any_for_display_xy(all)` = `led/F053`, and
  `(labels=("led",))` = `led/F053`. At `[1019,402]` all return None (correctly — empty panel → F005 fallback).

**Conclusion:** the pick code is correct; the flagged frame is a **stale-hover capture**. The last processed
passive-hover `<Motion>` was at `[1019,402]` (panel → F005); the mouse then moved to `[432,652]`; and
`flag_bug()`'s `render_window.Render()` (open3d_inspector.py:8463) re-painted that STALE F005 highlight plus a
crosshair at the flag cursor — the hover was never re-run at the final position. (The 142 px gap between the
live-stash square centroid `[674.9,545.4]` and the offscreen `[533.1,554.6]` is the same story: the stash was
written under the earlier `[1019,402]` hover's camera, before the user rotated to the flag camera —
`_world_to_display_2d` is byte-identical to raw `WorldToDisplay`, so it is not a projection-function bug.)

**Square opening (F053) geometry:** 45.0 mm × 45.0 mm (four ~41 mm straight edges + ~2 mm rounded corners,
perimeter 176.6 mm), plane x=51.43, centroid `[51.43, 20.91, 70.89]`; ~206×209 px on screen at the flag camera
— a large, easy target, so the miss is not about opening size.

**Owed / next (proposed, not yet built):** make the hover/flag **re-pick at the flag cursor** so the recorded
highlight + stash always match the crosshair — this removes the stale-hover ambiguity and the next "CA not
highlighted" flag will either show the square correctly highlighted (no bug) or capture a genuine miss with the
RIGHT cursor. No penta phase / baseline regen this turn (no behavior change to the pick path).

---
### (original diagnosis below — the size/DPI theory it explores is now SUPERSEDED by the resolution above)

## Flag / redirect
After 0329 shipped (the interior-hit containment fallback), the user re-tested on a **fresh** app
(they quit Kitty and restart for every single test) and recorded `flag_20260716_162559_978`:

> still the same, CA not highlighted.

state.json: cursor `vtk_xy=[432,428]`, `hover_step_cell_key="('step','led','F005')"` — the LIVE hover
resolved the **whole front panel** (F005), not the central emitting square (F053). The screenshot's
green crosshair sits **inside** the drawn square. The app started 16:18, after the 0329 fix hit disk
15:28 — so the fix WAS loaded. This is a real, still-open miss, not a stale app.

## What I proved — and the contradiction it exposes
`bugs/diag_0330_flag978.py` drives the **real** `Kraken3DInspector` headless under Xvfb with the flag's
**exact** camera and the **independent** live cursor `[432,428]`, at the flag screenshot's true render
size **1163×904**:

```
render-window size = (1163, 904)
square proj-centroid = (529.6, 502.0)   cursor->nearest square-rim distance = 1.86 px
nearest_opening_loop([432,428]) = F053(perim=177)
live cell_id=4343  FULL_pick face_id='F053'      <-- the SQUARE, correct
```

So at the flag's own camera **and** render size, the full live pick path returns **F053** (the square).
Yet the LIVE app returned **F005**. Same code, same camera, same nominal size → **different result.**

The recorded cursor was captured at flag time via `GetEventPosition()` (flipped against the render
window height): `png_xy=[432,476]`, `vtk_xy=[432,428]`, `428+476=904` — self-consistent with a
1163×904 frame. The user does not resize between hovering the CA and pressing the flag key, so
hover-time size ≈ flag-time size. If both are 1163×904, the headless path picks F053 — but live picked
F005. **The miss can therefore only be a projection / render-size / DPI difference at the LIVE pick
instant that a single before-flag screenshot cannot carry.**

Why the screenshot always looks correct (masking the miss): `flag_bug()` calls
`render_window.Render()` (open3d_inspector.py:8463) **before** the `vtkWindowToImageFilter` capture,
re-syncing the render-window size. So the drawn frame + the crosshair the recorder paints from
`vtk_xy` always land the cursor on the CA — even when the earlier **hover** projection used a different
size and missed.

Ruled out as the concrete cause:
- **`<Configure>` shadowing.** `_bind_trace_tk_configure` (19082) binds with `add="+"`, so it does NOT
  replace `vtkTkRenderWindowInteractor`'s built-in size sync. The trace observers (19047-19072) only log.
- **Two cursors / two projections within one event.** The passive hover feeds the SAME `(x,y)` to both
  VTK's `_picker.Pick` (7885) and the analytic opening projection (7917); both reference the same render
  window, so they cannot diverge *within* one hover — the divergence must be **temporal or DPI**, not
  intra-event.

## Why I did NOT blind-fix the resize/pick path this turn
- This box has **no GLX** for the Tk-embedded inspector (Xvfb llvmpipe segfaults on the marathon;
  NVIDIA/EGL doesn't drop into the Tk widget), so I cannot verify a live behavior change.
- The Tk/VTK resize path is delicate (memory: the auto-logout footgun, the resize/coating bugs).
- The exact trigger — render-window-size lag vs **HiDPI / Tk-scaling** pixel mismatch (`GetEventPosition`
  in one scale, `WorldToDisplay` in another) vs render-window/GL-drawable divergence — is **not
  confirmable from one recording**. A wrong DPI-scale "fix" could regress non-HiDPI users.

Per the 0329 lesson I logged (a headless-pass/live-fail means the **harness diverged from the failing
gesture** — get the decisive live datum, don't guess): I instrumented the live pick so the **next** flag
carries the exact numbers, then fix with data.

## Instrumentation shipped (no behavior change)
`KrakenOS/UI/services/open3d_round_lens_pick.py` — new `_stash_opening_hover_debug`, called inside
`_opening_loop_hover_pick` right after the snap. At every opening hover it records onto
`inspector._last_opening_hover_debug`:
- `render_window_size` (the render window's pixel size — what `WorldToDisplay` uses),
- `renderer_viewport_size` (`renderer.GetSize()`),
- `widget_logical_size` (`winfo_width/height` — the Tk logical pixels the cursor event is expressed in),
- `cursor_xy`,
- `n_loops`, `chosen_face_index`, and per-loop `{face_index, perimeter, centroid_px, centroid_dist_px}`
  — where **every** mined opening projected and how far it landed from the cursor.

`KrakenOS/UI/services/open3d_event_recorder.py` — `SceneSnapshot` gains `render_window_size` +
`opening_hover_debug`, populated in `capture_scene_snapshot`, so `flag_bug` persists them into
`state.json` under `scene_state`.

### What the next "CA not highlighted" flag will decide
- If `render_window_size ≠ widget_logical_size` (or the square's `centroid_dist_px` is large at the
  recorded cursor) → a **projection / size / DPI** miss — and I'll have the exact sizes to reconcile the
  cursor coordinate with the render-window pixels at pick time.
- If all three sizes agree **and** the square projects onto the cursor yet `chosen_face_index` is
  `null`/F005 → a **snap-logic** miss (a different fix, in `nearest_opening_loop`).

## Verified
- **`bugs/diag_0330_hover_debug_guard.py`** (display-free) — **PASS**. (A) `_stash_opening_hover_debug`
  records the three sizes + cursor + per-loop projected centroid/distance + chosen face; a loop
  projecting ONTO the cursor gets ~0 px, a far loop a large distance. (B) end-to-end through
  `_opening_loop_hover_pick` (loop miner + snap patched) the stash lands on the inspector — so a real
  `flag_bug` will find it.
- **No regression:** `bugs/diag_0329_interior.py` (offscreen) still resolves the square interior/rim and
  off-body→None; `KrakenOS/UI/validate_open3d_led_opening_loop_hover.py` still **PASS**.
- **End-to-end under Xvfb** (`bugs/diag_0330_flag978.py`): the real inspector populates
  `opening_hover_debug` — `render_window_size=[1163,904]`, `widget_logical_size=[992,850]` (the gap here
  is an artifact of the harness forcing the render size to the flag screenshot, but it proves the
  instrumentation **captures** a render-window-vs-widget size mismatch — exactly the datum the live flag
  needs).

## Notes / remaining
- **No penta phase yet.** This turn is diagnosis + instrumentation, not a behavior fix, so a penta phase
  + baseline regen is deferred until the actual 0330 fix (the guard lives in `bugs/` meanwhile).
- **Owed:** one more in-app flag of the CA miss to read the live `opening_hover_debug`, then implement +
  verify the real fix (candidate: reconcile the hover cursor with the render-window pixel size before the
  opening projection, or test opening containment in world space via the picker ray — "display follows
  physics").
- Still paused (untouched): the phantom whole-face fill (bugs/0325) and the Alt-live gremlin (bugs/0324).

## Files
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — `_stash_opening_hover_debug` + call in
  `_opening_loop_hover_pick`.
- `KrakenOS/UI/services/open3d_event_recorder.py` — `SceneSnapshot.render_window_size` +
  `.opening_hover_debug`; populated in `capture_scene_snapshot`.
- `bugs/diag_0330_flag978.py` — real-inspector-under-Xvfb flag repro; now also prints the live stash.
- `bugs/diag_0330_hover_debug_guard.py` — display-free guard for the instrumentation contract.
