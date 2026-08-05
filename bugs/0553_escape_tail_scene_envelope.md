# 0553 — "some rays stop half way before touching the RA mirror"

**Flags:** `flag_20260805_101116_253`, `flag_20260805_101430_352` (zoomed), plus
`flag_20260805_101805_195` (the same view with the clipped overlay ON, for comparison).
**Reported:** *"after swapping the lens, FOV 23x23, solve for thickness, some rays stop half way
before touching the RA mirror."* Clipped rays were **OFF** (confirmed by the user).

## This one was mine

bugs/0551 fixed *"unbounded rays"* by shortening the escaped-ray display tail from
`1.25 × scene_radius` to `0.40 ×`. On this scene that landed **below the 75 mm floor** — proven
by the 0551 render comparison itself, where `0.40 ×` and the `75 mm stub` produced *byte-identical*
drawn extents (233.586…), which is only possible if `radius × 0.40 ≤ 75`. So the tail went from
~234 mm to 75 mm, a 3× shortening, and strays that used to sail past the prism now ended in
mid-air short of it. One complaint traded for another.

## Root cause

A fixed fraction of the envelope radius has **no relationship to where the scene's geometry
is**, so it is wrong in both directions at once. The guard makes this concrete: on a
100 mm-radius scene, `1.25 ×` draws 125 mm — simultaneously *past* the scene for a stray leaving
the centre (the 0551 streak) and only 125 mm of the 200 mm a stray needs to *cross* the scene
(the 0553 stop). No value of the constant satisfies both.

## Fix

The tail now runs until the stray **leaves the scene envelope**: the forward exit of the sphere
(`center`, `scene_radius`) that `scene_display_center_radius` builds from the surface meshes,
curves and targets — never from the rays themselves, so there is no feedback. Floored at 75 mm
and capped at 600 mm; those clamps only handle the extremes (a stray already outside the
envelope or aimed away from it still shows its direction; a pathological envelope cannot
produce an endless line).

`_scene_exit_distance` solves `|origin + t·d − centre| = radius` forward. It is measured from
`pts[-2]`, the start of the terminal SEGMENT, because `max_terminal_length` is that segment's
whole length — measuring from `pts[-1]` landed the drawn end one traced-stub short of the
envelope (caught by the guard, off by exactly 1 mm).

Behaviour:

| situation | tail |
|---|---|
| stray at the near edge crossing the scene | the full diameter — it traverses and stops at the far side |
| stray leaving the centre | the radius — stops at the envelope, never past it |
| stray already outside / aimed away | 75 mm floor (direction cue only) |
| very large scene | 600 mm cap |
| draw-suppressed branch (bugs/0506) | its short stub, unchanged |

## Guard

`KrakenOS/UI/validate_open3d_0551_escape_tail_bounded.py` (penta phase 436) calls the pure
projector: traverse, envelope, floor, cap, scene-relativity (doubling the scene doubles the
reach — a fixed millimetre bound fails this), never-shorter-than-traced, and the suppressed-branch
stub.

**Non-vacuity is unusually strong here — the guard rejects every rule that has ever shipped:**

| rule | verdict |
|---|---|
| `1.25 × radius` (pre-0551) | FAIL |
| `0.40 × radius` (bugs/0551) | FAIL |
| flat 75 mm stub | FAIL |
| sphere exit (bugs/0553) | PASS |

So it pins both flags at once and cannot be satisfied by re-tuning a constant.

## Lesson

*A display bound must be derived from the geometry it is bounding, not tuned against one scene.*
Two flags and two shipped constants were spent discovering that the radius fraction was the
wrong **quantity**, not the wrong **value** — the second attempt was measured and rendered on
the flagged scene and still regressed a different one, because the check only asked "is the
picture better here?" rather than "does this quantity mean anything?".
