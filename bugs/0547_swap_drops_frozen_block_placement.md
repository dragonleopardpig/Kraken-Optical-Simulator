# 0547 — a lens swap drops the frozen block's world placement

**Flag:** `attachment/recorded_bug_repros/flag_20260804_212159_302` (build `f0a4df6a`, dirty)
**Scene:** `attachment/machine_vision_AZ85_RA_Mirror_BS.py`, swapping ELS-85 → `0703-005-000-40-EXC`
**Reported:** *"swapped the lens: physical lens is reversed, surrogate is snap to another axis,
lens STEP seems not snap and not centered at the fold axis."*

Found immediately after bugs/0546 unblocked the swap on this scene — the swap had never actually
run on a 0433-frozen assembly before, so this was latent, not a regression from 0546.

## Root cause

On a **0433-frozen / axis-snapped** scene a row's `desp` + `tilt` *is* its final world placement
(`row_placement.WORLD`) — the fold is already baked in. The replacement block, though, comes from
a **fresh single-lens surrogate**, whose rows are straight-axis (`desp 0`, `tilt 0`). The splice
copies those rows in verbatim, so the whole lens jumps onto the global +Z axis:

| | before | after (broken) |
|---|---|---|
| Front datum pose | `(118.586, 0, 53.803)` | `(0, 0, 155.520)` — **118.6 mm off the leg** |
| Block tilt | `(0, −90, −180)` | `(0, 0, 0)` — flattened |
| BS cube / RA mirror | on the leg | unchanged (0546 holds) |

Everything else in the scene keeps its baked placement, so the surrogate ends up alone on the
vertical axis while the lens STEP overlay — whose pose bugs/0381 deliberately *preserves* — stays
behind on the leg. Hence all three reported symptoms at once, and a trace that sprays past the
RA prism instead of focusing (detector misses 63, worst 10.43 mm).

The fold transform cannot supply the missing frame: `_optical_axis_fold_world_transform_for_row`
is **None on every frozen scene**. That is the durable "frozen fold-transform gate", and this is
its **4th** consumer after 0517 (camera frame), 0519 (solve gate) and 0525 (cone crease).

## Fix

Measure the leg from the scene itself and re-bake the replacement onto it.

* `_swap_frozen_block_frame(front, rear)` — returns `None` unless some block row is
  `row_placement.is_world_placed`, so a plain sequential scene is untouched. Otherwise it
  reports `origin` (the front datum's world pose), `axis` (unit **front datum → rear datum**, the
  leg as the scene itself states it), `tilt` (the baked block tilt) and the `ScenePlacement`
  freeze breadcrumb. A zero-length block falls back to the baked tilt's own +Z — never the
  global axis.
* `_swap_apply_frozen_block_frame(frame, front, rear)` — each new row keeps the surrogate's own
  axial spacing (its station offset from the front datum) and is placed at
  `origin + axis * offset`, carrying the baked tilt, `axis_move = 0`, and the freeze breadcrumb
  (without it the table round-trip flattens an Aperture's tilts — bugs/0441). `desp_z` absorbs
  the station the way every world-placed row does.

It runs **after** the bugs/0383 rear-datum gap write, with `_swap_reseat_preserved_rows`: a pose
is `station + desp_z`, so `desp_z` can only be derived once the stations are final.

Measured on the user's own scene after the fix:

```
front datum  (118.586, 0, 53.803) -> (118.586, 0, 53.803)   drift 0 mm
block        z = 53.803 throughout, x 118.586 -> 168.590 (the 0703's 50.0 mm span)
tilt         (0, -90, -180) carried
promoted     BS drift 0.0 mm, RA mirror drift 5.7e-14 mm
detector misses 63 -> 59 (worst 10.43 -> 8.50 mm)
```

## Guard

`KrakenOS/UI/validate_open3d_0547_swap_keeps_frozen_leg.py` (penta phase 434) rebuilds the
flagged scene's baked numbers and drives the **real** swap. It asserts the front datum's pose is
held, every block row's perpendicular distance from the old leg line is ~0, the tilt and freeze
breadcrumb are carried, and — separately — that an **unfrozen** scene yields no frame and gets no
baked desp. Non-vacuity: neutering the capture or the apply reproduces the exact 118.6 mm drift;
forcing the frame on always trips the sequential guard.

## Still open (not this bug)

* **"physical lens is reversed"** — bugs/0381 deliberately preserves `lens_step_reverse_direction`
  across a swap ("a swap changes the lens, not where the user put it"), so the 0703 inherits the
  ELS-85's flip state. Two vendor STEPs can be authored with opposite native orientations, so
  carrying the flag is a coin flip. Auto-orient was explicitly **dropped** for this case (the 0703
  surrogate is aperture-symmetric, front == rear CA == 13.1 mm, so no heuristic detects a
  reversal) — manual **"Flip lens facing"** remains the truth. Worth revisiting whether the flip
  should reset rather than carry.
* **lens STEP centring** — the overlay's persisted `placement_offset_xyz` is calibrated against
  the *old* datum span (ELS-85 mid 146.086); the 0703's mid is 143.588, so the body is ~2.5 mm off
  after the swap. The offset should be re-derived from the new span, not carried raw.
