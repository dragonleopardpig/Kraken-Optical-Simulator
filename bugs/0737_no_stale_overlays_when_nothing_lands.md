# 0737 — when nothing lands, say so; never draw a stale measurement

Flag `flag_20260907_111321_904`, build 08f0acb9. Three observations in one state whose
terminations were `{"stopped_at_surface_10": 1439, "missed_image": 561}` — **no "image" entry at
all**, so not one ray reached the sensor:

1. *"So there is no best focus image plane?"* — correct, and silent. Nothing landed, so there was
   nothing to measure; the viewer drew nothing and explained nothing.
2. *"the clipped overlays is not ON, why showing the gray clipped rays?"* — bugs/0022 deliberately
   kept EVERY ray when the filter would hide them all ("don't blank the trace"). With every ray
   clipped, that override fired and the switch looked broken.
3. *"no rays hit the sensor, but the green strips overlayed on the sensor, not reasonable"* — the
   split-field strips were the ones measured by an EARLIER trace, drawn as if current.

All three are the same principle: **the scene must not present a measurement that this trace did
not make, and it must say why when it cannot make one.**

## Fix

* `measure_split_field_image_strips`: a band with fewer than `min_rays` landing rays keeps its
  numbers for reference but is marked `stale=True, measured=False, ray_count=0`; the coverage
  overlay skips a stale strip.
* the 3D ray collection honours `Clipped` even when every ray is clipped, and records
  `_ray_display_suppressed_note` — *"No ray reaches the sensor: N clipped rays hidden
  (Overlays → Clipped to show them)"* — re-stated on every draw so it can never go stale itself.
* `_measure_focused_image_plane` records `_focused_image_plane_unmeasured` when no ray reaches the
  detector, counting the terminations: *"FOCUS: no ray reaches the sensor, so the image plane
  cannot be measured (1439 stopped at surface 10, 561 missed image)"*.
* both notes ride the existing amber banner via `format_focus_summary_lines(..., notes=...)`.

## Guard

`validate_open3d_0737_no_stale_overlays_when_nothing_lands` = penta phase 535: A the stale/fresh
marking; B the overlay skips a stale strip and there is only one drawing path; C the Clipped toggle
is honoured with a stated reason; D the notes reach the banner and the measurement records why.

## Measured alongside — a REAL asymmetry to chase (not fixed here)

The user also asked why the rays look focused on one side of the sensor and defocused on the
other. The two beam AXES are provably symmetric — identical leg lengths, **428.371 mm total each**,
landing at ∓8.78 mm about the sensor centre. But tracing a clean solve to the 20 × 1 mm face and
measuring each face's own bundle at the sensor:

| face | landing rays | waist offset | spot at the waist | spot ON the sensor |
|---|---|---|---|---|
| A (front) | 4 | −72.67 mm | 0.9 µm | 1.68 mm |
| B (back) | 7 | −79.47 mm | 0.15 µm | 1.95 mm |

Each face focuses sharply, but **6.8 mm apart along the beam** — so one can be sharper on the
sensor than the other. Equal geometric path with different conjugates points at unequal GLASS in
the two arms (a ~20 mm glass difference would give ~6.8 mm of focus shift). Worth chasing with a
proper ray count; the sample here is small (4 and 7 rays).
