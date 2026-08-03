# 0520 — lens drag = "Solve for FOV" (drag pins the section, focus + FOV follow)

## Request

flag_20260803_140823 + the user's general principle (same day): "when I drag the lens, the
corresponding FOV should change and the image should focus at the sensor" — generalized:
dragging any component should behave like **"Solve for FOV"** with the drag as that
section's thickness constraint. This is how the production instrument is used: FOV is
changed by physically sliding components and refocusing.

## Implementation (lens first)

`_finish_step_carry_drag` (open3d_inspector): when the committed carry drag's label is
`lens` and it moved, run `editor.snap_detector_to_image_plane()` — the 0490/0515
traced-focus snap (collision resolver + frozen-aware writer + adaptive convergence) — then
force a retrace refresh and update the Quick Estimation readout, so the FOV numbers follow
the new geometry. The status line appends "Refocused at the sensor (Solve for FOV)."

Other labels (LED/station/mirror/optical) keep the 0433 stay-put contract — those drags are
layout gestures, not conjugate edits; extending the principle to more components is the
follow-up (per-label opt-in as flags arrive). Headless drags via `translate_step_overlay`
are unaffected (the hook fires only on the interactive carry commit), so every existing
drag guard stays byte-identical.

## Guard

`validate_open3d_0520_lens_drag_refocuses.py` (penta phase 419): slide the lens assembly
off focus, invoke the finish hook with a lens carry state, assert the QE state returns
`in_focus=True` and the status carries the refocus note.
