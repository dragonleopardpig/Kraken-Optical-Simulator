# 0885 -- the scene-source edit popup, and what a census does not tell you

bugs/0363's "general 3D source element" popup: right-click a source in the Scene Components
browser -> Edit Source... and set its name, origin, emit direction, emitting size, cone
half-angle, ray count and power. Apply writes through `update_scene_source_spec` -- the same path
the seat-on-face glue uses -- so the glyph, the illumination volume and the trace all follow.
`panels/open3d_source_edit_dialog.py` 185 -> 59 lines.

## The model decides what the dialog *contains*

A coaxial illuminator gets two more fields (bugs/0401): the illumination-edge profile and its
width. The Tk popup tested `spec[COAXIAL_ILLUMINATOR_KEY]` and drew two extra widgets. In the
framework that is the **builder** reading the spec and adding the fields or not -- so both
toolkits get it from one place, and neither view needs to know what a coaxial illuminator is.

## One option the renderer grew

`render_row_form(..., modal=True)`. The inspector's popups **grab**: a click in the 3D viewport
behind must not retrace under a half-filled form. Only this dialog asks for it.

## What the census got wrong about the Inspection Part dialog

I had listed `services/inspection_part.py:298` (197 lines) as a phase-3 row form. Reading it:
bugs/0828 replaced its explanatory paragraph with **a `tk.Canvas` picture of the part at true
proportions**, redrawn as the dimensions change, with the two inspected faces lit and a
derivation chain beside it. Its fields and verbs are a row form, but that picture is not a
`FormField`.

The drawing is already model data -- `face_polygons()` and `chain_text()` return polygons and
lines -- so the seam exists. What is missing is a **view hook**: something like
`RowForm.preview`, which both renderers draw. That is a new family property for one dialog, so it
wants its own decision rather than being smuggled into a port. **Left for its own bug.**

## Guard

`KrakenOS/UI/validate_open3d_0885_scene_source_edit_form.py` (penta phase 673):

- **B** -- 12 fields; an unknown source refuses, and so does no source at all
- **V** -- "Direction must be a non-zero vector.", "Width and height must be positive.",
  "Enter numeric values (direction may be any non-zero vector)."
- **A** -- apply **halves** the entered size into `radius_x`/`radius_y` (12 x 8 -> 6, 4) through
  `update_scene_source_spec`
- **C** -- a coaxial spec adds exactly `coaxial_edge_profile` and `coaxial_edge_width`; a plain
  one does not
- **T** -- the REAL Tk popup drew 12 entries and **grabbed**
- **Q** -- the Qt dialog showed the same 12 fields and applied 14 x 6 mm as radii 7 and 3
