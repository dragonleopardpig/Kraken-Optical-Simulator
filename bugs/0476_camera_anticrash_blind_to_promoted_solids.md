# 0476 — the camera anti-crash was blind to promoted solids, and remove-defocus never asked it

Flag `flag_20260729_185536_867` on build `69426d5b`, scene
`attachment/machine_vision_AZ85_RA_Mirror_BS.py`:

> unhide the Camera STEP: the anti-crash algorithm not functioning. Camera crash to RA mirror.

Reported once before as `flag_20260729_154419_478` ("Camera crashes to RA mirror"), which
bugs/0471 answered with a warning that — as it turns out — could never fire on this scene.

## Measured

From `state.json`, a genuine axis-aligned overlap on all three axes:

    camera body    x [194.93, 264.93]   y [-35.0,  35.0]   z [ 6.49, 80.12]
    RA mirror row  x [193.65, 218.65]   y [-12.5,  12.5]   z [59.40, 84.40]
    overlap        x 23.7 mm            y 25.0 mm          z 20.7 mm

and, decisively:

    step overlay labels present : ['camera']
    promoted solid rows         : [3, 7]

The user had reached this state via "remove defocus", which took row 7's thickness from
18.86 to 80.9399 and carried the glued camera into the mirror.

## Two independent defects

### 1. The check could not see the obstacle

`camera_body_collisions` (`scene_placement_commands.py:2734`) promised, in its own docstring,
*"names of promoted solids whose bodies OVERLAP this STEP body"*. The implementation scanned
STEP **overlay** labels:

    for other in ("lens", "led", "optical"):
        other_mesh = self._transformed_imported_step_mesh_for_label(other)

Once a beam splitter or fold mirror is PROMOTED its overlay is gone — the same disappearance
bugs/0103 had to handle for the glue menu. On this scene the BS is row 3 and the RA mirror is
row 7, and there is no `optical` overlay at all, so the loop `continue`d past every candidate
and returned `[]` however deep the camera sat inside the mirror. Verified independently:
with the camera pushed into a real 3-axis overlap, `camera_body_collisions() -> []` while
`_swap_camera_body_clearance_deficit() -> 14.48 mm`.

Fixed by also scanning rows carrying `advanced['StepOverlayPromotion']`, through
`_promoted_solid_world_bounds` — the bugs/0393b helper that takes the SIZE from the promotion
metadata but re-reads the CENTRE from the live placement, because the metadata centre goes
stale the moment the solid is moved. Overlay scanning is kept; a scene can have both.

### 2. Remove-defocus never asked

`snap_detector_to_image_plane` writes `rows[-2].thickness += delta` with no floor, no clamp
and no post-move check, and its only wrapper
(`Kraken3DInspector._snap_detector_to_image_plane`, `open3d_inspector.py:20275`) called
`_apply_model_change()` and stopped. Every "remove defocus" menu entry routes there. It was
the only camera-moving action without a collision warning — the two seating paths have had
one since bugs/0471.

Fixed by running the check after the rebuild, exactly as `_seat_camera_on_sensor` does. After
the rebuild and never inside the move: the transformed STEP mesh is memoized (bugs/0331), so
an in-action check reads the pre-move body.

## Why the collision FLOOR did not save it either

`_image_gap_collision_floor` (`quick_estimation.py:902`) returns `far_min` from
`_folded_image_conjugate_split` — `0.5 * aperture` = **12.5 mm** here. That reserves the
mirror's half-aperture for the sensor **plane**. It knows nothing about the camera body's
11.48 mm front-to-sensor standoff, let alone the 73.63 mm body hanging upstream of the sensor.
A sensor-plane floor cannot keep a body out of the mirror. (bugs/0391-0395 solved exactly this
for the lens-swap path, with `_swap_camera_body_clearance_deficit` measuring real mesh
geometry along the folded leg; it was never back-ported to the focus paths.)

Deliberately NOT changed here: the floor still governs the sensor plane, and remove-defocus
still puts the sensor at best focus and WARNS. Silently adding clearance would defocus the
image the user just asked to focus — the same reasoning bugs/0471 used to make seating an
explicit action rather than an automatic correction. Making the body's standoff a real
constraint on the FOV solve is follow-on work, tracked with bugs/0475's sibling flags.

## Verified

`KrakenOS/UI/validate_open3d_0476_camera_body_collision_promoted.py`, display-free, driving a
stub over the REAL `ScenePlacementMixin` + `LayoutTableWorkbenchMixin` so the genuine
`_promoted_solid_world_bounds` runs, on the flagged AABBs verbatim. Penta phase **384**.

    PASS A0  the flagged camera/mirror AABBs really do overlap on all 3 axes
    PASS B1  a promoted solid overlapping the camera is reported
    PASS B2  the hit names the promoted row, not an overlay label
    PASS C1  a camera clear of the mirror reports nothing (no false alarm)
    PASS D1  a non-promoted row is skipped, not crashed
    PASS E1  an overlapping STEP OVERLAY is still reported (overlay scan not lost)
    PASS F1  the remove-defocus wrapper runs the camera collision check
    PASS F2  it checks AFTER the rebuild

Run against the pre-fix tree first: B1, B2, F1 and F2 all fail, with `B1` returning `[]` —
the reported symptom exactly.
