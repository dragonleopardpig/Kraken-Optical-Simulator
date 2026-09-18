# 0820 -- a lens surface is an ELEMENT, not one face of it

User, reading bugs/0819's conclusion that the ELS-85's glass could not be measured: "do you mean the
vendor STEP should have some element but it is missing? If yes, you may add it as long as the outer
dimension not changed."

Nothing is missing, and nothing had to be added. The measurement was wrong.

## What the STEP actually holds

`ELS-85-4.5V16K.STEP`, its four spherical faces:

```
face#61  extents=[2.657, 28.058, 14.158]  centre=[-23.28, -2.42, 47.05]  sphere centre [17.006, -2.417, 54.0]
face#62  extents=[2.657, 28.058, 14.158]  centre=[-23.28, -2.42, 60.95]  sphere centre [17.006, -2.417, 54.0]
face#63  extents=[2.657, 28.058, 14.158]  centre=[ 29.32, -2.42, 47.05]  sphere centre [-10.958, -2.417, 54.0]
face#64  extents=[2.657, 28.058, 14.158]  centre=[ 29.32, -2.42, 60.95]  sphere centre [-10.958, -2.417, 54.0]
```

Two pairs. Each pair shares a sphere centre and sits either side of z = 54.0: they are the two
**halves of one element**, at the front (8.6% along the body) and the rear (97.4%). Each half's bbox
is 28.058 mm across the split and 14.158 mm along it.

`_step_glass_aperture` read a FACE, taking the middle of its three extents -- correct for a whole
cap, and for half a cap it is the half-width. So an element 28.058 mm across measured 14.158 mm, on
an 85 mm f/4.5 lens whose pupil alone is 18.889 mm. **That is what gave the fragment away**: a front
element is never narrower than the pupil it passes, which is exactly the refusal bugs/0819 had to
add, and the reason the AZ85 sweep could not proceed.

The same split runs through the other two bodies that looked wrong:

| body | faces per element | was | is |
|---|---|---|---|
| ELS-85 | 2 halves | 14.158 | **28.058** |
| 15056 (150 mm) | 4 patches | 18.596 | **26.624** |
| 67304 (0.75X telecentric) | 2 halves | 14.893 | **29.643** |

## Fix

`_step_glass_aperture` groups spherical faces by the sphere they lie on -- centre and radius, rounded
to a micron -- and measures each ELEMENT on the union of its faces' boxes. A face carrying no sphere
parameters is still its own element, and the area gate (a group's summed area against the largest
group's) still drops a small protective cap.

Measured across all 22 vendor lens STEPs in `attachment/Lens`, exactly those three change. The PYRITE
bodies, whose elements are one face each, are untouched (5.6/120 stays 30.391), and so is
`ball_lens/step_63227.stp` at 9.617 mm -- a ball lens IS a hemisphere and that reading was always
right.

## What it changes downstream

* **New imports** of those folders now size their discs from the real element rather than the
  1.4 x stop fallback: the ELS-85 lands on 28.058 mm where bugs/0819 recorded 26.44 mm -- within
  1.6 mm of the hand-authored 29.0, which is the number the old layouts had guessed.
* **The bugs/0819 refit** can now run on those scenes. Its sub-pupil refusal still stands, and still
  fires for any body whose glass genuinely cannot be found.
* **The 67304 element reads 29.643 mm against a 29.5 mm barrel measure.** The two disagree by 0.14 mm
  because the barrel reader takes the largest coaxial CYLINDER, and this lens's element fills its
  housing; the import clamps with `min(lens_aperture, housing)` off this same number, so nothing is
  drawn inconsistently. Recorded rather than papered over.
* The **shipped layouts are not touched by this**; the reader feeds imports and the refit verb. The
  bugs/0819 sweep decisions stand, including leaving `machine_vision_AZ85_RA_Mirror` (95 guards) and
  the two vignetting fixtures alone.

## Guard

`validate_open3d_0820_a_lens_surface_is_an_element` (penta phase 599), display-free:

* A: two half-caps on one sphere read as one 28.06 mm element; a single half still reads 14.158 (the
  grouping invents nothing); two separate elements stay two and the widest wins, never their span; a
  face with no sphere centre is measured on its own; the area gate still drops a small cap.
* B: the three split bodies read their element and the two unsplit ones are unchanged, the ball lens
  included.
* C: the ELS-85's element is wider than the 18.889 mm pupil its own scene passes -- the physical test
  the fragment failed.

`validate_machine_vision_pyrite_85_surrogate`, `..._pyrite_120_surrogate` and
`..._azure_85_surrogate` fail before and after this change, with identical failure lists (checked by
restoring the file from git): they are about glass-vertex Z offsets and predate this work.
