# 0849 -- scene labels draw above the housings; the HUD and banner above the labels

flag_20260921_172317 (the 20 x 20 solve): inside the camera body the scene printed

    Face A field                    Sensor 23.0x23.0          <- on top of each other
    Face A field: Focused image 0.1155 mm in front of the sensor (spot 0.489 um here vs 3.06 um on the sensor)
    Face B field: Focused image 0.1155 mm in front of the sensor (spot 0.489 um here vs 3.06 um on the sensor)

dimmed, and cross-hatched by the camera's own edges.

## Why

**Occlusion, not colour.** The label actor asks for a white background at 82% opacity -- yet the
camera's lines showed straight through. With a camera STEP glued the sensor is *inside* the
housing, and so is every image-plane label (sensor size, field strips, focus planes). In the
main renderer each translucent wall between the eye and the label is blended over it.

**Repetition.** The focus-plane label carried the full measurement -- distance, side, both spot
sizes -- which the banner's FOCUS / per-face rows already give, with the Landed / not-defocus
verdict those numbers feed. On a split field the scene printed it twice, over the rays.

## Fix

- The coverage labels go on the **always-on-top layer** the gizmos already use (bugs/0112),
  **never pickable** -- that layer is picked first, and a label must not take a click meant for
  the body behind it.
- That alone put a label **over the banner** in a real-inspector capture (a "Face B field" label
  across the banner's left column). So the HUD and the banner moved to the **same layer**: VTK
  renders a layer's 2-D actors in its overlay pass, after its 3-D props, so they always cover the
  labels. One set of helpers (`_attach_annotation_prop` / `_detach_annotation_prop` /
  `_annotation_layer_renderer`) serves all three; with no top layer everything stays on the main
  renderer.
- The focus-plane label says which field, how far, which side. The spot sizes stay in the banner.
- Label **positions are unchanged** -- they carry the user's own tuning (bugs/0241, "just beside
  the orange square", "too far").

Checked with the REAL inspector on om05a (`bugs/diag_0849_label_layers.py`, private Xvfb): all 9
labels, the HUD and the banner on the top layer; the labels readable over the housing; the
banner drawn over the label that used to cover it.

The sensor-isolation band filter already walked the top layer, and it only ever filtered
`vtkActor`s -- billboards were never in it, before or after.

## Still open

"Face A field" and "Sensor 23.0x23.0" still collide in the user's oblique view: anchored ~16 mm
apart in 3-D, projected onto the same spot. A general fix is screen-space label de-cluttering;
not done here, because the anchors are hand-tuned and moving them is the user's call.

## Guard

`validate_open3d_0849_labels_readable_above_housings.py`, display-free, penta phase 628.

- **A** the helpers on a fake with two REAL vtkRenderers: attach -> top layer only (and off the
  main renderer), idempotent; detach -> neither; no top layer -> main renderer
- **L** the REAL label builder: through the helper, not pickable; a legacy inspector still gets
  its label
- **F** focus labels name field, distance, side -- no spot sizes
- **W** the HUD and banner updaters attach / detach through the helper (executable lines; the
  diagnostic is the rendered check)

Existing guards: 20 of 23 label / banner / HUD / gizmo / isolation guards pass. Of the other
three, `gizmo_overlay_on_top` and `step_reselect_single_gizmo` fail identically on the unpatched
code (pre-existing). The third, **0762 D1-D3 (penta phase 550), was repaired here**: it pinned
the banner placement's IMPLEMENTATION (`hud.GetSize(renderer, size)`, `size = [0, 0]`,
`x_norm > 0.72`), which bugs/0838 deliberately replaced with text-derived widths -- stale since,
unnoticed because no gate subset included 550. It now asserts what 0762 claimed, on the pure
`solve_banner_anchor`: beside the HUD by the HUD's width when the banner fits, stacked when it
would run off the edge, and that the live placement decides through it.
