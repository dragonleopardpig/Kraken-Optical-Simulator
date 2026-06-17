# 0093 — Open 3D: a promoted beam-splitter cube OVER-focuses the transmitted beam (focus lands before, not beyond, the bare-lens focus)

## Status: OPEN — investigation needed (not yet fixed)

Discovered 2026-06-18 from the user's physics reasoning while reviewing the
branch-detector positions (recordings `flag_20260618_001227_407` +
`_000848_194`). Documented here for a later session; **no fix committed yet.**

## Symptom (user)

> The old image location is the focus before the beam splitter was inserted.
> Since the beam splitter will always make the focusing further, the new detector
> position should be **after**, not **before**, the old image location.

The user only **inserted a beam splitter and promoted it while rays were on** (no
quick-estimation, no manual placement). The transmit-arm branch detector landed
*before* the original (bare-lens) focus — physically backwards.

## The data (recording flag_20260618_001227_407)

Scene: doublet (rows 1–3, z≈110–119) → promoted BK7 beam-splitter cube (row 4,
z=142–193, 50 mm, face `S001/F001` = "Partial Reflecting / Transmitting"), rays
on, `use_nonseq: True`. Cube diagonal (split point) at z≈167.

| | z (mm) | distance from diagonal |
|---|---|---|
| bare-lens focus = old Image (row 5) | 266 | 99 mm |
| traced transmit focus = branch detector (row 100001) | 233 | **66 mm** |
| traced reflect focus = branch detector (row 100000) | y=66 | **66 mm** |
| physically-expected with-cube focus (+t(1−1/n)≈17 mm) | ~283 | ~116 mm |

So the cube **over-converges** the beam: the transmit focus is ~50 mm too short
(66 mm vs ~116 mm expected) and lands *before* the bare-lens focus instead of
beyond it. Both arms converge at exactly 66 mm from the split (suspiciously
symmetric — the remaining convergence distance is the same for both, but it's the
*wrong* distance).

## Why this is a TRACE bug, not a detector-display bug

The branch detector (bugs/0088 B1 / 0090) sits at wherever the traced rays
actually converge — `_closest_approach_point` of the exit rays. So the detector
display is **correct relative to the trace**; the fault is upstream: the
non-sequential trace of the promoted beam-splitter cube is bending/over-converging
the transmitted beam.

Physics: a real beam-splitter cube is two same-glass prisms cemented at the coated
hypotenuse. The 45° interface has **no index step**, so it must only *split*
(partial reflection) and **never refract** the transmitted ray. The flat
front/back faces should contribute only the small plane-parallel-plate shift
(focus slightly **further**). Over-converging means the transmitted beam is being
refracted where it shouldn't be.

## Leading hypotheses (to check)

1. The internal 45° "Beam Splitter" face is being traced as a **refracting**
   interface (index step) instead of a coated, no-index-step split — bending the
   transmit beam.
2. The cube's front/back face refraction is applied **wrong-signed** (glass↔air
   swapped), converging instead of shifting.
3. The mesh-solid (STL-faceted) trace mishandles refraction for a converging beam
   at the flat faces.

## Investigation plan

- Reproduce headlessly: a converging beam (lens) → a flat BK7 cube (no coating) →
  confirm the focus shifts **further** by ~t(1−1/n); then add the 45° Beam
  Splitter face and check whether the transmit focus moves *closer* (the bug).
- Trace how the non-seq engine handles a promoted optical-solid's faces for the
  TRANSMIT branch (refraction vs straight-through at the Beam Splitter face);
  the 45° internal face must not apply refraction.
- North-Star: fix the non-sequential trace physics, do not dodge to sequential.
- This is separate from the detector-redesign display series (A/B1/0090/0091/0092),
  which is correct relative to the trace.

## Related

[[project-open3d-detector-redesign]] (B1 detectors follow this focus),
[[feedback_trace_mode_north_star]], [[feedback_random_element_ray_trace]].
