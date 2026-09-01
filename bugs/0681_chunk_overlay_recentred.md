# 0681 — "3D object relocated, everything haywired" (flag_20260901_124838_106)

## Symptom
First successful in-app 3D view of the armA `om05a_folded.py` (the chunk-cache crash
fixed by 0679 had blocked earlier views): the prism-assembly housing rendered SUNK —
centred about y=0, wrapped around the device plate, with the wedge rows and mirror
poking out of it. Read as "everything haywired".

## What was actually wrong (one thing)
Every OPTICAL row rendered at its correct CAD pose (verified from the flag's
`row_actor_bounds`: A train, B train, mirrors, lens leg all exact). The relocated
object was the `optical_step_path` DECORATION (prism_assembly_chunk_armA.step):

- File authored bounds: y[−5.3, 60.8] (housing wrapping the trains + the mirror-1
  mount), z[−106.8, 49.0].
- Rendered: y[−33, 33] — the overlay placement CENTRES the transverse (x, y) on the
  optical axis (`_transformed…step_mesh` seat: `transverse_center = body_mid`,
  `axis_offset_xy` SUBTRACTED after centring). Correct for lens barrels; it strips an
  asymmetric decoration's authored y-centre (+27.77) → drawn 27.8 mm low.
- The 0677 wiring restored only the z identity (`placement_offset_z = authored
  z-min`); the tunnel chunk was y-symmetric so the y-centring was invisible there.
  The armA chunk is not.

## Fix (data, not code)
- Scene: `optical_step_axis_offset_xy = [-0.05, -27.7665]` = −(authored transverse
  centre) → the drawn seat equals the authored pose. Verified drawn bounds
  y[−5.2, 60.8] via `_transformed_imported_step_mesh_for_label("optical")`.
- `bugs/0677_chunk_and_device.py` `wire_armA()` now bakes the axis offset from the
  chunk's measured bounds, so a rebuild reproduces the seat.
- Guard: 0672 validator A6 pins the drawn chunk centre (y≈27.8, z≈−28.9); phase 505.

Full overlay identity recipe for an authored-in-world decoration:
`placement_offset_z = authored z-min` AND `axis_offset_xy = -(authored x/y centre)`.

## Non-bugs checked and left alone
- The wide red fan diving past mirror 1 = CHAIN fields vignetting (pre-0680,
  byte-identical trace, 0605 "missed rays must visibly miss"). Not faceB: its census
  is 73 die at the lens stop (the known lens-seat asymmetry), 4 B-train, 4 reach.
- Lens/camera overlays: seats verified unchanged and correct.
