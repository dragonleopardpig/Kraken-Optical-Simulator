# bugs/0346 — single-axis CA→optical-axis snap must auto-complete without a prior refresh

## The flag (build-stamped FRESH — a real regression, not a stale app)

`flag_20260717_160019_506`:

> sadly... right click snap to optical axis still not working, opticl axis no
> highlight, click on it no snap.

`state.json` carries the **0345 build stamp**: `{"git": "0815ab71", "branch":
"nonseq-display-refactor", "dirty": true}` — i.e. the app was launched from the
current post-0344 code. So this is **not** a stale app; the snap genuinely does not
finish. (This is the first flag to answer the "is this even on the new build?"
question the 0345 stamp was added for.)

The snapshot also shows a **single-axis** scene: `optical_axis_records` len = 1
(`axis:global`), `optical_axis_actor_count = 1`. By flag time
`interaction_mode = idle` and `step_overlay_poses.led.axis_anchor = null` — the armed
pick was already gone (the user's click-away trying to hit the buried axis cancelled
it).

## Root cause

`_optical_axis_pick_records` is the list the one-click auto-complete
(`_single_optical_axis_pick_info`, bugs/0337) reads. It is **(re)populated only by a
scene refresh** — `open3d_scene_refresh.py` clears it, then
`_add_optical_axis_pick_overlays` appends one record per axis (the same actors that
draw the dashed guides). Nothing else fills it.

The right-click **"Snap Clear Aperture → Optical Axis"** fires
`_snap_clear_aperture_to_optical_axis_from_context`, which arms the pick and then
immediately asks `_single_optical_axis_pick_info(center)` whether the scene has a
single axis it can finish on the spot. When the snap runs **before** a refresh has
repopulated the list (the common case — the menu action does not force a refresh
first), `_optical_axis_pick_records` is **empty**, so:

```
_single_optical_axis_pick_info:  if not records: return None
```

→ auto-complete is skipped → the snap falls back to the bugs/0337 **two-step "click
the dotted Optical Axis" pick**. That is exactly the unusable state 0337 was written
to eliminate: near the opening the axis runs *inside* the body (no hover highlight),
and its only visible stubs sit in the far screen corners, outside the 28 px hover /
40 px click tolerance. The user is stranded — "optical axis no highlight, click on it
no snap."

### Headless proof (`bugs/probe_0346_snap_autocomplete.py`)

On the user's single-axis scene `attachment/machine_vision_150mm_test.py`, under Xvfb:

```
[3]  _optical_axis_pick_records: n=0                       <- empty at snap time
[3b] _optical_axis_records_for_3d(None): n=1  ['axis:global']   <- source is fine
[4]  CA resolve: center=[~0, ~0, 261.3]  normal=[0,0,1]    <- 0344 resolves the opening
[5]  _single_optical_axis_pick_info -> None                <- empty list -> no payload
[6]  snap fired: pick_mode False -> True                   <- STUCK ARMED (bug repro)
```

The source method `_optical_axis_records_for_3d(None)` returns the single axis even
though the cached `_optical_axis_pick_records` is empty — the divergence is pure
refresh timing.

## Fix — decouple the auto-complete from refresh timing

`_single_optical_axis_pick_info` now falls back to `_optical_axis_records_for_3d(None)`
— the **same source** `_add_optical_axis_pick_overlays` derives the pick records from —
when `_optical_axis_pick_records` yields no usable records:

```python
records = _usable_axis_pick_records(getattr(self, "_optical_axis_pick_records", None))
if not records:                                   # bugs/0346
    try:
        source = self._optical_axis_records_for_3d(None)
    except Exception:
        source = None
    records = _usable_axis_pick_records(source)
if not records:
    return None
axis_ids = {str(rec.get("axis_id", "") or "") for rec, _pts in records}
...
```

`_usable_axis_pick_records` is a small module-level helper applying the identical
valid-Nx3-points gate `_add_optical_axis_pick_overlays` uses when it appends, so the
fallback reconstructs exactly what a refresh would have produced.

Behaviour by scene:
- **single axis** (straight scene) → source yields 1 axis → payload → **auto-completes
  on the menu click** (the fix).
- **multi axis** (folded RA-mirror scene, e.g. AZ85 → 3 axes) → source yields >1
  distinct `axis_id` → `None` → the explicit "click the intended axis" step is kept
  (correct: the machine must not guess which of several axes).
- **populated pick list** → used directly, the fallback source is never consulted (no
  behaviour change, no extra work).

### After-fix proof (same probe)

```
150mm_test (single axis): [5] -> PAYLOAD   [6] pick_mode False -> False   AUTO-COMPLETED
AZ85_RA_Mirror (3 axes):  [5] -> None      [6] pick_mode False -> True    STUCK ARMED (correct — disambiguate)
```

## Guard & regression

`KrakenOS/UI/validate_open3d_ca_snap_autocomplete_fallback.py` (penta **Phase 302**),
display-free:
- empty pick list + single-axis source → payload (the fix); + multi-axis source →
  None; + empty/raising source → None (never leaks);
- a populated pick list is used directly (the fallback source is not consulted);
- `_usable_axis_pick_records` keeps only valid Nx3 records;
- source contract: `_single_optical_axis_pick_info` consults
  `_optical_axis_records_for_3d` as the empty-list fallback.

The refactor of the record-parsing into the module-level `_usable_axis_pick_records`
keeps the existing 0337 guard (`validate_open3d_led_ca_axis_snap.py`, phase 296)
passing — it drives `_single_optical_axis_pick_info` with a bare stub, which the free
function (no `self`) still serves.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` — module-level
  `_usable_axis_pick_records()` helper + the `_optical_axis_records_for_3d(None)`
  empty-list fallback in `_single_optical_axis_pick_info`.
- `KrakenOS/UI/validate_open3d_ca_snap_autocomplete_fallback.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 302.
- `tools/penta_validator_baseline.json` — Phase 302 = pass.
- `bugs/probe_0346_snap_autocomplete.py` — headless repro (scene-parametric).

## Owed / follow-ups
- **In-app GLX eyeball**: confirm the single-axis right-click snap now centres+normals
  the opening in one click with no stranded two-step pick (cannot drive the GL canvas
  headless here).
- **Pre-existing, unrelated**: penta **Phase 293**
  (`validate_open3d_led_ca_persistent_select`) fails on HEAD too — its SimpleNamespace
  stub is missing a `_clear_selected_step_face` no-op (the method exists on the real
  inspector, open3d_inspector.py:19681). Stale-guard stub gap, not a code regression;
  flag separately.
