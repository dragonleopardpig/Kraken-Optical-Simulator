# 0152 — thickness dimension offset side must re-derive for the live camera on orbit

> **Provenance:** re-applied from M90aPro-local commit `2c6331f` (originally numbered
> **0136**) after the cross-machine branch divergence — origin's 0136 is an unrelated
> "hiding a STEP element leaves its gizmo" bug, so this work was renumbered to 0152. The
> source fix (inspector + thickness_dimensions + scene_refresh) cherry-picked onto current
> HEAD cleanly and composes with origin's 0140 label-squaring work; only the penta phase +
> baseline were re-authored (phase **140**).

## Symptom

Two flags from `recording_20260624_203801.json`, narrating a before/after:

* `flag_20260624_203423_975` — "thickness overlays **changed to opposite side**."
* `flag_20260624_203516_116` — "thickness **changed back to correct side after glue BS to LED**."

The blue S-thickness dimension arrows + labels jumped to the wrong side of the optical axis,
and only snapped back to the correct side once the user glued the beam splitter to the LED.

## Root cause

A dimension's offset side is `offset_direction(segment, view_normal, screen_up)` —
`cross(view, segment)` flipped to sit on the screen-bottom (bugs/0007). It is **view-relative**
and is computed **once at draw time**, inside `add_overlays` (a scene refresh).

On a camera orbit, `_on_camera_interaction` → `_reorient_thickness_labels_for_camera`
re-derives only the **label billboard angle** for the live camera (bugs/0128). It never
re-derived the **side**. So after orbiting, the arrow + label stayed on the side that was
correct for the *pre-orbit* camera — the "opposite side" — until the next full scene refresh
re-ran `add_overlays` and recomputed the side. Gluing the BS to the LED calls
`_refresh_open_3d_views` → that refresh is what "changed it back to the correct side"; the
glue itself is incidental (any refresh would do it). The side never depends on the glue state
(verified: `offset_direction` takes only the view, the segment direction and screen-up — glue,
row order and BS position never enter it), so this was a *staleness* bug, the exact gap
bugs/0128 left when it fixed the label angle but not the side.

## Fix

Mirror the bugs/0128 cheap orbit-time re-derivation for the **side**:

* `_emit_span_dimension` registers each dimension's actors (arrow, two leaders, label) plus
  its UN-offset anchors and current offset via `_register_view_relative_dimension`.
* On `EndInteractionEvent` (orbit/zoom release — not per frame), `_on_camera_interaction`
  calls `_reposition_dimensions_for_camera`: for each dimension it re-derives the side for the
  live camera, `AddPosition`s the rigid arrow by `new_offset − old_offset`, `SetPosition`s the
  billboard label, and rebuilds the two short leaders (one end is pinned to the surface, so
  they can't be rigidly translated — they are cheap 2-point lines, re-created in place). No
  scene rebuild, no re-trace, so it keeps the CAD-smooth interaction the user expects.
* The group registry is cleared on every scene refresh (the refresh removes the actors and
  re-registers fresh ones). Repositioning is idempotent (a no-op when the side is unchanged)
  and leak-free (old leaders are dropped before new ones are added — the actor table holds at
  most the two live leaders per dimension).

`add_label_actor` now returns the label actor (was a bool; both callers use `if ...:`, so the
truthy/None return is compatible) so the group can re-place it.

## Guard

`KrakenOS/UI/validate_open3d_dimension_side_orbit.py` (display-free; binds the real
`_reposition_dimensions_for_camera` onto a fake inspector with stub actors/camera). Checks:
**A** orbiting side-view → tilted moves the arrow by exactly `new_offset − old_offset` (live
side); **B** the label is re-placed and both leaders rebuilt; **C** idempotent for the same
camera; **D** no actor leak across many orbits (exactly 2 leaders, bounded actor table);
**E** source contracts (orbit-end reposition, refresh clears the registry, emit registers the
group). Penta phase **140**; baseline regenerated. In-app eyeball owed — the cheap actor
re-place + leader rebuild on orbit can't be driven through the embedded VTK canvas headless
(orbit a tilted view and confirm the arrows track to screen-bottom without a refresh).
