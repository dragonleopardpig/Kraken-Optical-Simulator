# bugs/0337 — "Right click center CA to optical axis not working": the second click can't land on the axis

**Flag 1 of `recording_20260717_130459.json`** (imported vendor LED): *"right click
center CA to optical axis not working."* Then, after retrying:
*"I tried again, right click edge to snap optical axis, but I can't select the
Optical Axis"*, *"I think it is a break rather than friction"*, and *"the optical
axis should get highlight first when mouse hover, but it didn't."*

This is the follow-through on bugs 0333/0335: the user pins a CA opening (0334),
right-clicks it, picks **"Snap Clear Aperture -> Optical Axis (center + normal)"**
(0335 opening menu) — and nothing happens.

## Not friction — a genuine break in the second click

`_snap_clear_aperture_to_optical_axis_from_context` only did **step one** of a
two-step pick: it *armed* `start_step_normal_axis_pick(anchor_mode="feature_center", …)`
(sets `_step_normal_axis_pick_mode`, stores the opening centre + normal) and then
asked the user to **click the dotted Optical Axis guide** as step two. The apply
(`_apply_step_normal_axis_pick` → `_apply_step_feature_center_axis_pick` →
`snap_step_feature_normal_to_optical_axis`) only runs on that second click.

That second click is unreachable for this scene. Projecting the recorded camera
(`state.json`: `camera_position [273.2,106.5,99.9]`, `focal [0,0,50]`,
`parallel_scale 101.15`, window `1163×904`) against the one axis record
(`axis:global`, polyline `[[0,0,-102.79],[0,0,244.57]]`):

- The optical axis **is** the world z-axis. It runs straight **through the LED
  body** (bounds x∈[−79,79], y∈[−68,68], z∈[0,141]). Near the opening the axis is
  *inside the solid* — occluded — so there is nothing to hover-highlight there.
  (That is exactly the user's *"the optical axis should get highlight first … but
  it didn't."*)
- Its only **visible** stubs project to the far screen corners (endpoint P1 ≈
  `(1221,661)` off the right edge; P2 ≈ `(-233,186)` off the left edge). Both are
  **off-screen**.

The hover-highlight-during-arm branch keys on a **28 px** screen proximity and the
click keys on **40 px** (`AXIS_PICK_TOLERANCE_PX`). Near the opening the axis is
occluded; where it is visible it is off-screen. There is no cursor position that
both hovers the opening *and* lands within tolerance of the axis. The two-step is
genuinely unusable here — a break, not friction.

## Fix — when there is exactly ONE optical axis, skip the second click

There is nothing to disambiguate in a single-axis scene, so the snap finishes in
one click. `_snap_clear_aperture_to_optical_axis_from_context`
(`open3d_face_assignment.py`) still **arms** as before (that path stores the
opening geometry and is the tested route), then:

```python
if not bool(getattr(self, "_step_normal_axis_pick_mode", False)):
    return                      # arm bailed (no opening geometry) — its status stands
axis_info = self._single_optical_axis_pick_info(center)
if axis_info is None:
    return                      # several axes — keep the explicit "click the axis" step
self._apply_step_normal_axis_pick(axis_info)
self.render()
```

`_single_optical_axis_pick_info(center)` synthesises the axis's pick payload from
`_optical_axis_pick_records` (the same per-refresh list the live click consults):
it keeps records with a valid Nx3 polyline, returns **None** when there are zero or
more than one **distinct** `axis_id` (multi-axis scenes still get the explicit
pick), and for the single axis returns `dict(record)` with
`picked_world = opening centre`. `_optical_axis_frame_from_pick` then projects that
centre onto the axis polyline (its **perpendicular foot**) — precisely the point
the manual click aims at, minus the aiming.

Because the apply is the **same** `_apply_step_normal_axis_pick` the manual click
would have called, the physics is identical (rotate the opening normal onto the
axis **and** translate its centre onto it, via
`snap_step_feature_normal_to_optical_axis`); only the unreachable click is removed.
The staleness clear that moves the pinned rim with the body (0334) still runs in
the apply tail.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_ca_axis_snap.py` (penta **Phase 292**),
display-free, **Section 4**:
- `_single_optical_axis_pick_info` returns a one-click payload for a single axis
  (carries the `axis_id`; `picked_world` == the opening centre), **None** for two
  distinct axes, **None** for no records;
- behavioural: with one axis the CA snap **arms then applies immediately** (apply
  count 1); with two axes it **arms only** (apply count 0 — the two-step stands);
- source contract: the handler one-clicks via `_single_optical_axis_pick_info` +
  `_apply_step_normal_axis_pick`.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` —
  `_snap_clear_aperture_to_optical_axis_from_context` one-clicks on a single axis;
  new `_single_optical_axis_pick_info` helper.
- `KrakenOS/UI/validate_open3d_led_ca_axis_snap.py` — new guard (Section 4).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 292 title
  + docstring extended to cover the one-click snap.
- `tools/penta_validator_baseline.json` — Phase 292 title updated (still pass).
