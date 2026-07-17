# bugs/0347 — folded-scene CA→optical-axis snap must auto-complete (fold segments are ONE axis)

## The flag (build-stamped 8834ecfa = the 0346 fix — so the fix was running)

`flag_20260717_164901_740`:

> right click snapping still not working.

`state.json` carries the **0346 build stamp**: `{"git": "8834ecfa", "branch":
"nonseq-display-refactor", "dirty": true}` — the app was launched from the code that
already contains the 0346 auto-complete-fallback fix. So 0346 did **not** fully fix the
user's experience.

Scene facts from the snapshot:
- **single displayed axis**: `optical_axis_records` len = 1 (`axis:global`,
  points `[0,0,-102.8] → [0,0,244.6]`), `optical_axis_actor_count = 1`.
- LED loaded, **nothing promoted** (`promoted_solid_rows: []`,
  `async_trace_decision.reason = "no_promoted_step_rows"`).
- the user **right-clicked the LED body** (`right_click_diagnostics.prior_hover_key =
  "('step','led','F053')"`, `override_fired = false` → the regular body menu, not the
  pinned-opening menu).
- the LED **did not move**: `step_overlay_poses.led.placement_offset_xyz = [0,0,0]`,
  `axis_offset_xy = [0,0]`.

The scene is `attachment/machine_vision_AZ85_RA_Mirror.py` (the only scene carrying the
ILS0202 LED), whose ILS0202 opening sits **~0.77 mm off the axis** in x — a real offset
the snap should remove.

## Why 0346's probe missed it

The 0346 probe verdict "AUTO-COMPLETED (good)" only checked that `pick_mode` cleared
(`False→False`). It never checked that the opening **moved**. On the coaxial
`machine_vision_150mm_test` scene the opening is already on-axis, so "success" moved
nothing — a false positive. The user's scene has a genuinely off-axis opening, and there
the snap silently did nothing.

## Root cause — the empty-list fallback over-counts a folded axis

The AZ85 scene is **folded**: `_folded_axis_incoming_fold_point_z()` resolves (Z≈53), so
`_optical_axis_records_for_3d(None)` returns **three** records — the ONE global axis split
into guide segments (bugs/0200/0216):

```
axis:global               (incoming +Z)
axis:global:reflected:1   (reflected middle leg)
axis:global:reflected     (reflected outgoing leg)
```

These are **segments of the same optical axis**, not three distinct axes.

At snap time `_optical_axis_pick_records` is **empty** (the 0346 pre-refresh condition —
reproduced headless: pick list n=0). So the 0346 fallback consults
`_optical_axis_records_for_3d(None)` and gets all three segments. Then:

```python
axis_ids = {str(rec.get("axis_id", "")) for rec, _pts in records}  # {global, reflected, reflected:1}
if len(axis_ids) != 1:        # 3 != 1
    return None               # -> "several axes, don't guess"
```

→ `_single_optical_axis_pick_info` returns `None` → the snap stays stuck in the bugs/0337
two-step arm (the axis is buried in the body, unpickable) → the off-axis opening never
moves. Exactly "right click snapping still not working."

The 0346 doc *called* the folded AZ85 case "multi axis → keep the explicit pick
(correct)". That was **wrong** from the user's point of view: a folded scene still shows
ONE optical axis, and the two-step pick is just as unusable there as on a straight scene.

### Headless proof (`bugs/probe_0347_menu_snap_natural.py`)

Load the AZ85 scene, resolve the CA, fire the real menu-path handler
(`_clear_aperture_opening_center_normal` → `_snap_clear_aperture_to_optical_axis_from_context`):

```
[fold] _folded_axis_incoming_fold_point_z = 53.0
[src ] _optical_axis_records_for_3d(None): n=3  ['axis:global','axis:global:reflected:1','axis:global:reflected']
[live] _optical_axis_pick_records:         n=0
BEFORE FIX (A) natural: pick_mode False->True   moved=0.0    (stuck armed, opening stays 0.77 mm off)
AFTER  FIX (A) natural: pick_mode False->False  moved=0.769  XY-off after=2.6e-14  (snapped onto axis)
```

## Fix — count optical axes by their BASE id

`_single_optical_axis_pick_info` now collapses each guide's fold suffix before counting
distinct axes, via a small module-level helper:

```python
def _base_optical_axis_id(axis_id) -> str:
    text = str(axis_id or "")
    marker = ":reflected"
    index = text.find(marker)
    return text[:index] if index != -1 else text

...
axis_ids = {_base_optical_axis_id(rec.get("axis_id", "")) for rec, _pts in records}
if len(axis_ids) != 1:
    return None
```

- **folded single axis** (`axis:global`, `axis:global:reflected*`) → all base `axis:global`
  → 1 → auto-completes. The existing nearest-segment logic (already present for
  `len(records) > 1`) then picks the segment closest to the opening — `axis:global` for an
  opening near the incoming +Z leg (0.77 mm away vs ~45 mm to the reflected legs) — and the
  snap projects the opening onto it.
- **genuinely distinct axes**: a traced beam branch carries `axis:ray:{i}:segment:{j}`
  (ray_display_geometry.py:386 — **no** `:reflected` marker), so it survives the collapse
  as a distinct base and still returns `None` → the explicit "click the intended axis"
  step is kept (a beam splitter / penta cascade must not be guessed).

## Guards & regression

New display-free guard `KrakenOS/UI/validate_open3d_ca_snap_folded_axis_autocomplete.py`
(penta **Phase 303**):
- `_base_optical_axis_id` collapses `:reflected[:N]`, leaves `axis:global` / `axis:ray:…`
  intact;
- folded source + EMPTY pick list → payload, picking the SEGMENT nearest the opening
  (`axis:global`), with `picked_world` = the opening centre;
- genuinely distinct axes (`axis:global` + `axis:ray:…`) → `None`;
- a folded pick list carried directly (no fallback) → auto-completes.

The 0346 guard (`validate_open3d_ca_snap_autocomplete_fallback.py`, Phase 302) had encoded
the old wrong assumption in its check #2 (`axis:global` + `axis:global:reflected` → `None`).
Updated: that folded pair now asserts a **payload**, and the "distinct axes → None" case
uses `axis:ray:0:segment:2`. Both Phase 302 and the 0337 guard (Phase 296) still pass — the
free `_base_optical_axis_id` / `_usable_axis_pick_records` helpers serve the bare stubs.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` — module-level `_base_optical_axis_id()`
  helper + base-id collapse in `_single_optical_axis_pick_info`.
- `KrakenOS/UI/validate_open3d_ca_snap_folded_axis_autocomplete.py` — new guard.
- `KrakenOS/UI/validate_open3d_ca_snap_autocomplete_fallback.py` — check #2 corrected.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 303.
- `tools/penta_validator_baseline.json` — Phase 303 = pass.
- `bugs/probe_0347_menu_snap_natural.py` — headless repro (natural + empty pick list).

## Owed / follow-ups
- **In-app GLX eyeball**: confirm the folded AZ85 right-click snap now centres+normals the
  LED opening in one click (cannot drive the GL canvas headless here).
- **Verify the recorder gap the false-positive exposed**: the flag snapshot reads the pose
  at FLAG time, not snap time; a "moved 0.0" is only visible because the user re-flagged.
  Consider capturing pre/post-snap pose in the recorder so a no-op snap is self-evident.
- **Pre-existing, unrelated**: penta Phase 293
  (`validate_open3d_led_ca_persistent_select`) still fails on HEAD (SimpleNamespace stub
  missing `_clear_selected_step_face`); stale-guard stub gap, flag separately.
