# 0023 — Moving the beam splitter off the beam dragged the focus/detector off station

**Status:** Fixed (2026-06-06).
**Component:** optical-solid output-port follower —
`KrakenOS/UI/nonseq_output_ports.py`
(`build_optical_solid_output_port_pose_overrides` / `_exit_frame_is_non_folding`).
**Reported via:** in-app recorder, `attachment/recorded_bug_repros/flag_20260606_223248_453`
("removing the beam splitter, the rays should now focus at the sensor … something
is wrong fundamentally"), refined live by the user.

## Symptoms (user's words)

> removing the beam splitter, the ray is not traced correctly to physics, the
> rays should now focus at the sensor.
> still need to fix the beam splitter remove, wrong focus position.

Shifting the promoted beam-splitter cube sideways off the optical axis put the
beam's focus in the wrong place: the rays no longer reached the sensor.

## Root cause

The cube's output-port override repositions every downstream row onto the cube's
exit frame (`frame_origin = output_face_centroid + normal·thickness`). Bug 0017
added a guard to *skip* that for a straight-through **inferred** exit, but the
predicate `_exit_frame_is_on_axis_passthrough` required the exit to be **both**
codirectional with the incoming axis **and laterally centred on it**.

When the user shifted the cube −55 mm in X, the exit face moved off-axis but the
exit *direction* stayed straight ahead (`normal = [0,0,1]`, no fold). The
codirectional test still passed, but the **lateral-centred test failed**, so the
skip stopped applying and the override snapped the downstream Image/detector onto
the displaced exit face:

| | cube (row 6) world | Image (row 7) world |
|---|---|---|
| cube in place | `[0, 0, 212.5]` | `[0, 0, 665]` (the sensor station) |
| cube −55 mm X | `[-55, 0, 212.5]` | **`[-55, 0, 265]`** (dragged ~400 mm off station) |

The on-axis beam then missed the displaced detector entirely (every ray
`no_next_intersection`), so it could not focus on the sensor. The trace mode was
already correct (non-sequential `NsTraceLoop`); only the geometry override was
wrong. As the user put it: a ray doesn't care whether the sensor is there — the
lens sets the focus at a fixed point in space, and the beam propagates to it
whether or not the cube is in the path. **Only a fold relocates the beam.**

## Fix

The skip is now **direction-only**: `_exit_frame_is_non_folding` returns True
whenever the exit is codirectional with the incoming axis, regardless of the
solid's lateral position. A non-folding inferred exit never repositions
downstream rows — the beam keeps its direction, so the existing rows already lie
on its path. Folded inferred exits, explicit output ports, and physics-traced
exits still drive the follower-row workflow unchanged. (A genuine codirectional
beam *displacer* must be authored with an explicit output port, which is not
gated by this skip.)

With the fix, shifting the cube off-axis leaves the Image/detector at its real
`[0, 0, 665]` station; the beam propagates straight and focuses there:

| | rays after the cube is shifted −55 mm X |
|---|---|
| before | bundle 279, **all escaped**, 0 hit the detector (focus dragged to z=265) |
| after | bundle 279, **155 hit_detector + 124 missed_detector, 0 escaped** (beam focuses at the fixed sensor; the 124 misses are the physical defocus from losing the glass plate) |

This is the physics fix behind bugs/0022 (which only made the vanished rays
*visible* — a display safety net that is kept, since rays propagate independently
of any detector).

## Tests

`KrakenOS/UI/validate_open3d_moved_splitter_keeps_focus.py` — display-free:

* **A:** `_exit_frame_is_non_folding` is True for a codirectional exit and False
  for a 90° fold; the override builder uses it and no longer references the
  stale lateral-centred predicate.
* **B:** with the machine-vision rows and the cube shifted −55 mm in X, the
  override does **not** reposition the downstream Image row (it stays on its
  authored station); the cube-in-place case is unchanged. SKIPs without the
  prescription.

Verified fail-before / pass-after (the override dragged the Image 665→265 before,
665→665 after) and that the bug-0017/0018 beam-splitter transmit/reflect guards
still pass (the folded reflected branch still repositions correctly). Wired into
the comprehensive harness as `Phase 32`; gate baseline regenerated.
