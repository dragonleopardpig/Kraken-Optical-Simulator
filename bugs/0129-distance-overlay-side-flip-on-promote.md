# 0129 — "distance overlay changes to another side after promote" — NOT REPRODUCIBLE on current code (suspected stale app)

## Symptom

`flag_20260624_084550_405`:

> "After dragging the BS to the LED, promoted, the distance overlay change to
> another side although the same ISO view."

The screenshot shows the amber **"Object → LED"** arrow sitting *above* the optical
axis while the blue **"S{n} Thickness"** arrows sit *below* it, in an ISO view the
user says they did not change.

## Investigation — why current code cannot produce this

The side a dimension is pushed to is `offset_direction(segment, view_normal, screen_up)`
(`open3d_thickness_dimensions.py`). Two facts make the reported flip impossible under
the code on this branch:

1. **`offset_direction` is sign-stable.** It computes `side = cross(view, segment)`
   then forces `dot(side, screen_up) <= 0` (always the screen-down side). Feeding it
   `+z` vs `-z` returns the *same* vector. Verified numerically with the recorded
   camera (`pos`/`focal`/`up` from the flag's `state.json`):

   ```
   seg (0,0, 1) -> side [-0.501 -0.865 0]  dot(side,up) = -0.946
   seg (0,0,-1) -> side [-0.501 -0.865 0]  dot(side,up) = -0.946
   ```

   So for a fixed camera, the side is fully determined by the segment *axis*, never
   its sign — and `dot = -0.946` is nowhere near the `0` threshold, so a small camera
   nudge can't flip it either.

2. **Every dimension in this scene is axial (`+z`).** The promoted BS solid has
   `tilt = [0,0,0]`, `desp = [0,0,27.5]` (on-axis). The promoted-solid own-thickness
   span (`_optical_solid_span_points`, `+z`), the "gap to solid" arrow
   (`p0 -> entry`, `+z`), and the amber `_emit_led_object_edge_dimension`
   (`axis = [0,0,1]`) all build `+z` segments and all call the *same* `offset_direction`
   with the *same* camera. They therefore land on the *same* (screen-down) side.

In particular the amber "Object → LED" overlay and the blue thickness arrows share one
code path for the side (`offset_direction(+z, view_normal, screen_up)`), so they cannot
render on opposite sides of the axis the way the screenshot shows.

## Conclusion

The opposite-side split in the screenshot is **not** current-branch behaviour. The
amber object→LED overlay is brand-new code (bugs/0123 commit `cc08e1a`, bugs/0125
commit `d451477`); a running app that had not been restarted onto that exact revision
(or was mid-way through it) would render the amber arrow on the old geometric side
while the thickness arrows used the unified screen-down side — exactly the split seen.

Per the project's stale-app rule (memory: *"if a recording won't reproduce on current
code after a thorough dig, suspect a stale running app; ask the user to restart +
re-record before deep-diving"*), no code change is made and no validator phase is
added. **Action owed: restart the app on the current branch and re-record if the side
still flips.** If it does, the re-recording should capture the camera before *and*
after the promote so we can tell whether the promote moved the view.
