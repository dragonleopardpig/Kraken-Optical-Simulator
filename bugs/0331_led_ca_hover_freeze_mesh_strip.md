# bugs/0331 — LED clear-aperture opening stops highlighting after an off-body hover

**Flags:** 978, 798, 718, 630, 408 (the "CA not highlighting / the next window gets
highlighted / no improvement at all" family, all on the vendor LED STEP).

## Symptom

Hovering the LED's central emitting square (its clear-aperture opening) highlights the
opening rim — until the cursor passes **off the body** once. After that the opening never
highlights again: the whole front panel lights up leaving the opening as a hole, or a
neighbouring window gets picked, no matter where the cursor goes. Every flag's persisted
`opening_hover_debug.cursor_xy` is frozen at an **off-body** position with
`chosen_face_index = None`, 300–590 px from where the user was actually pointing.

The pick *logic* is correct at the resting cursor — `bugs/diag_0330f_flag408_live.py`
proved the live pick resolves `[420,635] -> F164` on CO90. The opening simply never gets
picked there. Two independent defects conspire.

## Root cause 1 (the freeze) — the shared display mesh gets its face indices STRIPPED

The off-body / miss hover pick eventually runs
`ScenePlacementMixin._step_overlay_face_metadata_compute` (planar-face clustering for the
overlay). To silence PyVista's `InvalidMeshWarning` chorus it strips every cell-data array
off the mesh before `extract_surface()` / `triangulate()`:

```
KrakenOS/UI/services/scene_placement_commands.py
  4181  mesh = self._transformed_imported_step_mesh_for_label(label)   # SHARED, memoized
  ...
  4205  cell_data.clear()                                              # strips IN PLACE
```

But line 4181 returns the **shared, memoized display mesh** (for LED,
`_transformed_imported_led_step_mesh`, memoized by `_cached_transformed_step_overlay`), and
the strip ran **in place** on it. The `.copy(deep=True)` calls downstream (4237/4242) came
*after* the damage. So the live mesh lost its `kraken_step_selection_face_index` /
`kraken_step_face_index` arrays.

Consequences, all on the live mesh:
- `triangle_array_and_face_index(mesh)` → empty (no face indices to read).
- `opening_loops_for_mesh(mesh)` collapses **21 → 0** (`_compute_opening_loops` bails when
  `fidx.size` mismatches / no `fidx >= 0`).
- `_opening_loop_hover_pick` returns `None` **before** it stashes a result, so
  `opening_hover_debug` freezes at the off-body cursor — exactly the flag signature.

**Self-perpetuating:** the strip also bumps the mesh `MTime`. `opening_loops_for_mesh` and
`_surface_triangles_and_face_index` cache by `id(mesh)` + `_mesh_cache_token =
(n_points, n_cells, MTime)`. The bumped token forces a recompute — into the now-poisoned
(face-index-absent) state, which is then cached. The freeze persists until the mesh is
rebuilt from scratch (a signature change), which a plain hover never triggers.

### Diagnosis trail
- `diag_0331_faceindex_poison.py` — proved the arrays go **ABSENT** across the off-body
  hover while `id(mesh)` stays and `MTime` bumps (203052 → 380007).
- `diag_0331_bisect_poison.py` — isolated `step_feature_pick_for_display_xy(OFF)` as the
  stripper (`sel 60138 → 0`, keys 5 → `[]`).
- `diag_0331_bisect_inner.py` — function-wrapping **failed** to catch the leaf (callers hold
  their own import bindings, and the strip happens between wrapped calls).
- `diag_0331_trace_strip.py` — `sys.settrace` over the miss pick pinned the exact line:
  `scene_placement_commands.py:4205` in `_step_overlay_face_metadata_compute`.

### Fix 1

Deep-copy the fetched mesh **before** stripping, so the strip only ever touches a private
copy and the shared display mesh keeps its face indices:

```python
mesh = self._transformed_imported_step_mesh_for_label(label)
if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
    return normalize_optical_solid_face_metadata({})
try:
    mesh = mesh.copy(deep=True)   # bugs/0331: never strip the SHARED memoized mesh in place
except Exception:
    pass
```

After the fix the trace shows `strips=0`, `MTime` unchanged, `n_arrays=5` preserved; the
idempotency probe shows `n_loops` staying at 21 and `nearest_opening_loop([420,635]) = F164`
across an off-body hover, and hovering back on-body re-highlights `('step','led','F164')`.

## Root cause 2 (the lag) — the resting cursor never gets a hover pick

`_on_mouse_move`'s throttle (`_mouse_move_due`, 35 ms) drops moves that arrive inside one
interval. A mouse coming to **rest** fires its last reports inside a single throttle window
(HW reports ~125 Hz; X11 coalesces a fast flick into a couple of far-apart events), so the
**final resting position routinely never gets a pick** — the highlight freezes at the last
*processed* move, hundreds of px behind the cursor. This is the same family from the other
side: even with the mesh healthy, the pick never ran at the resting cursor.

### Fix 2

A debounced, one-shot **trailing re-pick**: each throttled (dropped) move schedules a timer
~one interval after motion stops; a processed move cancels it; on fire it re-runs the hover
at the resting cursor (skipped while a carry drag/follow owns the mouse). See
`_schedule_trailing_hover_repick` / `_cancel_trailing_hover_repick` /
`_on_trailing_hover_repick` in `open3d_inspector.py`, wired into `open3d_interaction.py`'s
throttle branch.

Fix 2 alone is **insufficient**: if the mesh is already poisoned by Fix-1's strip, re-picking
at rest still returns `None`. Both fixes are needed.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_hover_repick.py` (penta **Phase 291**), display-free:
- **Section 1 (mesh integrity):** runs the real `_step_overlay_face_metadata_compute` against
  the shared analytic mesh and asserts `opening_loops_for_mesh` stays 21 → 21 and the
  `kraken_step_*` arrays survive. Proven to have teeth: with the copy removed it fails with
  `keys 5 → []`, `loops 21 → 0`.
- **Section 2 (timer contract):** binds the real inspector methods onto a fake Tk widget and
  asserts schedule / debounce / fire-at-rest / not-during-carry / cancel / no-widget-no-op.

## Files touched
- `KrakenOS/UI/services/scene_placement_commands.py` — copy-before-strip (Fix 1).
- `KrakenOS/UI/open3d_inspector.py` — trailing re-pick timer (Fix 2).
- `KrakenOS/UI/services/open3d_interaction.py` — schedule/cancel wiring (Fix 2).
- `KrakenOS/UI/validate_open3d_led_hover_repick.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 291.
- `tools/penta_validator_baseline.json` — Phase 291 = pass.
