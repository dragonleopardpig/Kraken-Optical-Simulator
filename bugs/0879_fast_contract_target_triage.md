# 0879 -- the fast-contract targets: six triaged, five gated

`validate_fast_contracts` is itself a meta-runner over ungated validators, so gating it covers
many at once -- but it was reporting six failing targets. Same verdict as 0878: **rot, fixtures
and validator bugs. No optics regression.**

| target | verdict |
|---|---|
| `open3d-live` | the STEP verbs moved out of the left Live Controls into the right Scene Components panel (the same move 0877 found for Promote) |
| `open3d-lens-step-face-pick` | two stale source pins -- see below |
| `cad-scene-cache` | a forbidden-token proxy that no longer matches the structure |
| `step-analytic-import` | the fixture pointed at a **display-only** overlay label |
| `launch-origin-within-object-aperture` | a contract **superseded by bugs/0523**, on the user's own flag |
| `five-penta-with-lens-layout` | a fixture that is not in the repo -- now a SKIP |
| `ui-modular-maintainability` | **left failing on purpose**: an aspirational line budget |

## The drag sign, measured -- and I got it backwards first

`validate_open3d_lens_step_face_pick` pinned `camera.Azimuth(-dx_f * degrees_per_pixel)`, the
pre-0206 call that the rigid Rodrigues orbit replaced. Measuring it instead (as 0877 did for the
fixed-drag checks) means stating the convention explicitly:

> camera on +Z looking at the origin, view-up +Y, so screen-right is +X. "Grab the scene" puts
> the CAMERA on the opposite side: drag right (+dx) swings it to −X so the scene moves right, and
> drag **up** (Tk `dy < 0`, because Tk's y grows downward) swings it to **−Y** so the scene tilts
> up toward the cursor.

My first version asserted the camera went to **+Y** on an upward drag and produced a false
failure (`camera went to y=-17.3648`). The code was right; the assertion was not. The corrected
check says why, so the next reader does not repeat it.

`_display_feature_edges_mesh` was the other one: a module-level import **alias**, so it was never
in the class source at all. The drawing goes through `cached_display_feature_edges`.

## The passive-hover token list

`validate_cad_scene_cache` forbade `_actor_step_map.get(actor_key)` anywhere in the hover branch.
But mapping the pick *result* to a label is an O(1) dict read -- the cost the contract cares about
is **which actors the picker considers**. `_passive_hover_pick_rotation_handle` builds its pick
list from the handle maps only and runs on `_prop_picker`, so that is what the check asserts now.

## A display-only label cannot have analytic optical faces

`validate_step_analytic_import` asked `app._step_overlay_face_metadata("lens")` for grouped
analytic faces and got 160 plane-clustered facets with no grouping. `"lens"` is one of
`_DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC = {"camera", "led", "lens"}` -- a vendor lens/camera/LED
body is **decoration**, and skipping the analytic path for it is the design. Analytic optical
faces belong to the `"optical"` label, the one Import Optical STEP → Promote to Optical Element
uses. Pointed there, the check reports 6 faces with the split asphere correctly grouped as
`S002/F001+S002/F005`.

## Two launch contracts, not one

`validate_launch_origin_within_object_aperture` reported
`launch bundle 0 origin (10.05, 10.05) radius 14.21 exceeds launch maximum 10.05`. Its
radial-inscribed contract was **superseded by bugs/0523**, on the user's flag: *"all the outer 3
rays should relocate to the 4 corner and 4 edges, simulating rays launching from maximum FOV"*. A
camera sees a **rectangle**, not a disc, so when the object-FOV rectangle is known the grid spans
it. Scenes with no rectangle keep the radial layout. The validator now checks both, on the same
scene, by hiding the rectangle for the radial cases.

**Measured and reported, not asserted.** On MV150:

```
FOV half extents (10.0462, 10.0462) mm, inscribed 10.0462 mm, diagonal 14.2074 mm;
object aperture radius 12.5 mm -> corner overhang 1.70744 mm
```

The FOV's **inscribed** circle fits inside the object's clear aperture, and that is asserted. The
four **corners** sit 1.71 mm outside it. Whether the object aperture should cover the FOV diagonal
is a prescription question -- the sensor really does see those corners, and a ray starting outside
the object row's clear aperture may be handled differently downstream (a ray outside the stop
skips finite lens surfaces). It is printed on every run rather than silently asserted either way.

## Gated

`run_checks()` added, registered as **penta phases 664-668**; gate green over 656-668.
`validate_fast_contracts` now reports only `ui-modular-maintainability`.
