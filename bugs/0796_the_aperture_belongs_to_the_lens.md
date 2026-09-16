# 0796 -- the aperture belongs to the lens, not to the scene

`flag_20260916_125457_269`, build `c771d3e7` (so bugs/0795 was already in): *"I swapped the lens,
seems the rays look the same."*

They did. bugs/0795 removed the pencil from the CLAMP. It was still coming from the DECLARATION.

## Measured, through the real swap callback

The user's scene, then `swap_imaging_lens_from_folder(SPO TCL4.0X)` driven headlessly:

| | aperture | axial bundle radius: object / front datum / group 1 / stop / group 2 / rear / sensor |
|---|---|---|
| as flagged | `FNO` -> EPD 0.8238 | 0.000 / **0.330** / 0.355 / 0.239 / 0.029 / 0.022 / 0.000 |
| after the swap, before this fix | `FNO` -> EPD 0.8238 | 0.000 / **0.330** / 0.355 / 0.239 / 0.029 / 0.022 / 0.003 |
| after the swap, fixed | `STOP 15.0761` | 0.000 / **8.320** / 8.960 / 6.030 / 0.721 / 0.561 / 0.064 |

The swap was working: the rows changed, the object sat at the 4x lens's own 65 mm, the banner
read 4.16x. The imported model even declared `STOP 15.0761`. The SCENE stayed on `FNO 12.5`.

## Root cause

`_apply_swapped_lens_step_settings` takes exactly two things from the incoming layout -- the STEP
path and the largest-component flag -- and its docstring is explicit that everything else,
including "source/field/pupil settings", is left untouched. That is right for all of them but
one.

Pose, object, camera, field and source describe the **scene**, and the user chose them; bugs/0378
and bugs/0381 exist because resetting them threw away the user's work. An aperture describes the
**lens**:

* `FNO` resolves against the system EFL, and after a swap that EFL is a different lens's;
* `EPD` is a pupil diameter in millimetres, which is a statement about the glass that just left.

Neither survives the departure with any meaning. Here `FNO 12.5` against the conjugate-constrained
build's EQUIVALENT EFL of 10.297 (bugs/0792: that EFL has no infinite-conjugate meaning) resolves
to a **0.824 mm** entrance pupil on a lens whose stop is **15.076 mm** -- 18x under, and exactly
the pencil the user photographed twice.

## Fix

`_apply_swapped_lens_aperture` adopts the incoming lens's declaration, and returns a note so the
swap SAYS so instead of silently restating the user's aperture in another lens's terms:

    Aperture set to this lens's own (STOP 15.0761, was FNO 12.5): an f-number or a pupil
    diameter only means anything against the lens it came from.

It runs where the other incoming settings land, before the auto-refocus, so best focus is found
on the cone the lens actually passes. A declaration that says nothing -- absent, unrecognised,
zero, unparseable -- is ignored and the scene's aperture is left alone, and re-adopting an
identical declaration is silent.

## Noticed while measuring, not fixed here

The sensor row now reads **0.064 mm** of bundle radius where a focused cone reads 0. That is the
2 mm camera-clearance clamp: the swap's refocus set the rear gap to 19.526 mm where the lens
images at 17.526. Against the MV-CS050's 3.45 um pixel that is a 128 um blur disc -- about **37
pixels** -- and it was invisible while the launch was a pencil, because a 0.022 mm beam has
almost no cone to defocus. A C-mount interface should SEAT, not clear. Own bug, already on the
backlog, and now with a measured cost.

## Guard

`python -m KrakenOS.UI.validate_open3d_0796_the_aperture_belongs_to_the_lens` -- display-free, a
synthetic scene in a temp dir plus the real swap callback. It pins that the swap adopts the
declaration and does so before the refocus and reports it in its message; that the flagged state
launches a 0.330 mm pencil under `FNO 12.5`; that adopting returns a note and sets the vars, that
re-adopting the same is silent and that junk is ignored; and end to end, that a scene declaring
the outgoing lens's f-number comes out of a real swap declaring `STOP 15.0761` and launching
8.320 mm where the flag traced 0.330. Penta phase 579.
