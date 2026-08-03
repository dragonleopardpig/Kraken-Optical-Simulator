# 0528 — the gizmo-arrow lens drag never refocused (Solve for FOV hole)

## Flag

`flag_20260803_203614`: "the FOV changed after lens dragged, but the rays are defocus, I
think FOV not changed fully enough." AZ85 RA-mirror+BS frozen scene, lens dragged
+50.54 mm along the split leg toward the prism.

## Diagnosis (what the recorded state proved)

- The lens placement offset moved exactly `[+50.542, 0, −50.542]` — the 0527 anchor
  compensation ran for the WHOLE drag, so the 0526 conjugate composite wrote every
  millimetre (gaps 130.63→181.18 / 103.27→52.73). The write-through was NOT the problem.
- The prism row still carried its fresh 44.12 gap and the drawn sensor sat at the fresh
  z = −5.08: `snap_detector_to_image_plane` never ran. With the sensor ~18.5 mm past the
  new best focus, the drawn FOV (branch magnification at the STALE sensor) read 33.7 where
  the refocused equilibrium is 47.66 — "FOV not changed fully enough" was the readout
  honestly describing a defocused system.
- Replays of the 0520 CARRY path (both headless and with a live inspector, per-frame
  drags) converge cleanly — sensor to −23.53, "Refocused at the sensor". The user's
  gesture was the OTHER drag surface: the gizmo translate ARROW (the scene state shows the
  lens selected with its handle set).

## Root cause

0520 wired the Solve-for-FOV refocus into `_finish_step_carry_drag` (body-grab carry)
only. The gizmo-arrow commit — `_finish_step_translate_drag` — runs the same
`translate_step_overlay` composite but returned right after setting its status: conjugates
written, sensor abandoned. Same principle as the 0248/0296/0298/0503 lesson: guard the
invariant ("an interactive lens commit that wrote conjugates refocuses"), not the one
gesture it was first reported on.

## Fix

`_finish_step_translate_drag` gained the 0520 block after a successful lens commit, gated
on `editor._last_translate_row_shifts` being non-empty — the composite's own breadcrumbs,
so it fires exactly when conjugates were written. A perpendicular arrow drag leaves the
list empty and keeps the 0433 stay-put contract (no snap, no note). On refocus: forced
retrace + QE readout refresh + the same status note.

Excluded by design: "Center Surface → Optical Axis" (an alignment snap, not a drag
gesture) and row-level placement handles (table-domain edits) stay refocus-free.

## Guard

`validate_open3d_0528_gizmo_lens_drag_refocuses.py` (penta phase 423): the +50.54 mm
X-arrow drag writes its sections AND re-seats the sensor with the note; a perpendicular
arrow drag changes nothing and carries no note.
