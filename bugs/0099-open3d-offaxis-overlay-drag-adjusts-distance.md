# 0099 — off-axis STEP overlay drag adjusts the optical distance / ray path

**Flagged:** `flag_20260621_142611` … `flag_20260621_142758` (4 recordings).

## Symptom
A beam-splitter STEP imported into the **lens** overlay slot and placed *off the rays* (beside the
optical axis) still moved a thickness dimension and the ray path when dragged:

1. "the imported beam splitter STEP placed randomly"
2. "move the beam splitter, the ray path adjusted as well"
3. "distance adjusted"
4. "drag the beam splitter again, the distance adjusted as well"

State: `selected_step_rotation_active_label = 'lens'` — the cube was sitting in the lens overlay slot.

## Root cause
Regression from the item-1 (camera→detector) and item-4 (lens→object-gap) **"move together"** glue.
`translate_step_overlay` redirects an AXIAL (+Z) drag of the `lens`/`camera` overlay to an optical gap
(object-to-lens distance / image distance) so the genuine glued lens/camera drags the whole optical
unit. That redirect fired for **any** axial drag of the lens/camera overlay — including a foreign body
(a cube) the user dropped off the axis into the lens slot. So dragging the off-axis BS drove the
lens-front gap + retraced the rays.

## Fix
The axial↔distance glue only applies while the overlay is in its **glued, on-axis** pose. Both
redirects are gated on `overlay_on_axis` = the overlay's current lateral offset
(`_step_axis_offset_xy` + the lateral part of `_step_placement_offset_xyz`) is ~0. An overlay placed
off the axis is a free body: its axial drag just moves the body (placement offset), never the optical
distance / rays. The genuine on-axis glued lens/camera is unaffected (it stays at lateral offset 0
because the glue redirects the axial component into the gap, not the offset).

## Test
`bugs/repro_0099.py` (display-free): on MV measured, an on-axis lens axial drag still redirects
(front 268→278); an off-axis lens axial drag leaves the gap unchanged (268→268) and only moves the
body (offset `[0,30,10]`).

NOTE: a beam splitter belongs in its own (optical/BS) handling, not the lens slot — that's the
item-3 (BS↔LED) work. This fix makes the off-axis case harmless regardless of slot.
