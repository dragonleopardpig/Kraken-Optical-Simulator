# 0084 — Open 3D: promoting a beam-splitter cube as the first element flung the downstream chain off-axis

## Symptom (user)

> [flag_20260617_105037_052] after promoting, all placement seems go haywire.

A 50 mm beam-splitter cube (`prisms/Beam_Splitter/32704`) was promoted as **row 1**
(the first optical element) with the 45° face coated "Partial Reflecting /
Transmitting". After the promote, the cube sat on the global axis at y=0 but the
whole downstream lens chain (rows 2,3,4) jumped to **y≈−120**, disconnected from
the cube, and the rays escaped to **z = ±millions** (optical-axis span −3.1M…+1.2M).

Principle invoked by the user: *an element placed anywhere must still trace
correct physics* — see [[feedback_random_element_ray_trace]] and the North Star
[[feedback_trace_mode_north_star]].

## Root cause

The "output-port follower" (`build_optical_solid_output_port_pose_overrides`)
repositions the rows downstream of an optical solid onto that solid's **exit
face**. To choose the exit it calls `select_optical_solid_output_face`, which
ranks candidates with `_output_face_sort_key`:

```
side_priority = {"Down": 6.0, "Up": 5.0, "Right": 4.0, "Back": 3.0, "Front": 2.0, "Left": 1.0}
```

A promoted beam-splitter **cube** has *all six* outer faces inferred as
Transmit/Output (only the 45° diagonal is the Beam Splitter). So the selector
picked **`Down` (−Y)** — highest side priority — as the "exit", even though the
real straight-through transmit exit is **`Right` (+Z)**. The override builder then
built a folding frame from that −Y face and dragged every follower row onto it
(→ y≈−120); the misplaced surfaces no longer intercepted the beam, so the chief
rays escaped and were extended with the long synthetic terminal tail (→ z=±M).

The 0017/0022 guard ("an *inferred* exit that does not fold the beam must not
reposition downstream rows") was already present — but it never fired, because
the selector handed it the folding −Y face instead of the non-folding +Z face.

## Fix (this commit)

In `select_optical_solid_output_face`, when choosing among **inferred** outputs,
prefer a face whose **world normal runs along the incoming +Z optical axis**
(`normal_world · +Z ≥ cos 15°`) — the genuine straight-through exit — before
falling back to the `Down>Up>Right` side priority. For a beam-splitter / plate
cube this selects the +Z `Right` face, which trips the existing non-folding guard
so the downstream chain is left on-axis. A genuine fold prism (penta, right-angle)
has **no** +Z-aligned transmit exit (its output is a side face, its +Z face is a
mirror/TIR), so it still falls back to side priority — unchanged. The preference
applies only to the *inferred* pool; explicit user-authored output ports are
untouched, and callers without world normals keep their old behavior.

## Regression gate (display-free)

`validate_open3d_beam_splitter_transmit_and_second_axis.py` gains two checks:
- `select_optical_solid_output_face` on a full 6-face cube picks the **+Z
  `Right`** exit (it picked `Down` before the fix).
- `build_optical_solid_output_port_pose_overrides([Object, cube, Lens, Image])`
  with the cube first produces **no** downstream override (the chain stays put).
Facet A still asserts a *genuinely folded* inferred exit DOES reposition, so the
fix is surgical, not a blanket disable.

## Note for the user

This is the genuine bug fixed — a beam-splitter cube placed anywhere now leaves
the rest of the system on its authored axis and traces straight through (the
reflected branch remains a separate non-sequential branch). Restart the app to
pick it up. (For the plane-parallel-plate focus experiment you can also just
leave the diagonal uncoated, but that is no longer required to avoid the haywire.)

## Status: FIXED
