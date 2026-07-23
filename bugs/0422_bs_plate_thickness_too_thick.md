# 0422 — One-click BS "Plate" is ridiculously thick

**Flag `flag_20260723_115239_954`** (AZ85 scene):
> "Added a BS Plate. Few issue: Orientation is wrong, I am OK to do it manually and glue it to the LED
> STEP. But the thickness is ridiculously thick. Can we have a way to resize optical component by direct
> extrude a surface and/or input the numerical value to the particular dimension?"

## Fix (this bug) — thin the default plate

`add_beam_splitter_to_led("plate")` sized the plate thickness as **`side_mm * 0.12`** (12% of the LED
opening span), clamped to `[2, side_mm*0.5]`. On the AZ85 LED opening (clamped up to 90 mm) that's a
**~11 mm slab** — a thick block, not a beam-splitter plate.

A **plate beam splitter is a thin substrate** (~1–5 mm), independent of aperture. Changed the default to:

```python
thickness_mm = min(max(side_mm * 0.04, 1.0), 5.0)
```

Across LED openings 8–90 mm the plate is now 1.0–3.6 mm (was up to 10.8 mm). Width/height still span the
opening (the plate covers the aperture); only the thickness was wrong.

## Verification (`validate_open3d_bs_plate_thickness`, penta phase 340)

Display-free:

| check | asserts |
|---|---|
| THIN-FORMULA | `add_beam_splitter_to_led` uses the thin `min(max(side*0.04, 1), 5)` clamp, not the old `side_mm*0.12` slab |
| THIN-VALUES | the default thickness stays ≤ 5 mm across 8–90 mm openings and is always thinner than the face |

2/2 pass. Baseline phase 340 = pass.

## Not addressed here (tracked separately)

- **Orientation wrong** — the user said they're fine fixing it manually (glue to the LED STEP), so left as-is.
- **General "resize optical component by extrude a surface / input a numerical dimension"** — a real
  feature request, scoped separately. The parametric BS (cube side / plate w×h×t) is the tractable first
  target: a "Resize Beam Splitter…" numerical dialog that regenerates the parametric solid in place. A
  general drag-to-extrude on arbitrary STEP/promoted solids is a much larger CAD-editing project.
  See [[project_thickness_solve_roadmap]] / [[project_open3d_cad_manipulation_smoothness]].

## Files

- `KrakenOS/UI/services/scene_placement_commands.py` — thin plate-thickness default.
- `KrakenOS/UI/validate_open3d_bs_plate_thickness.py` — guard (phase 340).
