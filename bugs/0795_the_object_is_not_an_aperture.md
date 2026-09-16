# 0795 -- the object is not an aperture

`flag_20260916_113737_764`, on the scene holding the SPO TCL4.0X-65DI-5M:
*"why the rays look so wierd, sudden bend on last two surrogate and single pencils rays reaching
the sensor, not the focusing rays type."*

Both halves of that sentence are right, and only one of them is a bug.

## Measured, from the scene's own launch

Ray-bundle radius at each vertex, axial field, as saved:

| | object | front datum | group 1 | stop | group 2 | rear datum | sensor |
|---|---|---|---|---|---|---|---|
| **as flagged** | 0.000 | **0.330** | 0.355 | 0.239 | 0.029 | 0.022 | 0.000 |
| **fixed** | 0.000 | **8.320** | 8.960 | 6.030 | 0.721 | 0.561 | 0.000 |

0.330 mm of beam through a lens with a 26.076 mm front aperture and a 15.076 mm stop is the
"single pencil". The stop was passing **4%** of its own diameter.

## Root cause: two clamps that measure the wrong thing

`_resolved_preview_pupil_radius` sizes the launch, and both of its inputs were category errors.

**1. `_entrance_radius` clamps to the OBJECT's semi-diameter.**

    object_radius = max(float(self.rows[0].diameter) / 2.0, 0.5)
    ...
    return min(radius, object_radius)

The object semi-diameter says how WIDE the object is. It never says what ANGLE the lens accepts.
Until now nothing noticed, because at 1x and below the object is the LARGER of the two and the
clamp never bound:

| | object semi-dia | front clear semi-dia | clamp used |
|---|---|---|---|
| WWK10-110CP-111V3 @ 1x | 8.758 | 7.003 | 7.003 -- the aperture, correct |
| SPO TCL4.0X @ 4x | **1.375** | 13.038 | **1.375** -- the object, the pencil |

A 4x lens is the first scene in the corpus whose object is SMALLER than its own cone: 2.75 mm of
object, 26 mm of front glass. The clamp took the object.

**2. `PupilCalc` cannot solve an object-space telecentric, and the fallback is half the stop.**

    PupilCalc RAISED: IndexError: index 1 is out of bounds for axis 0 with size 1
    PupilTool.py:591: RuntimeWarning: divide by zero encountered in scalar divide

`PupilCalc` finds the entrance pupil by Newton-solving the object height whose chief ray hits the
stop centre. In an object-space telecentric the chief ray is PARALLEL to the axis for every
object height, so that derivative is identically zero -- the solve divides by zero, the probe
rays never register, and `RadPupInp` never arrives. The silent `except Exception: pass` then
leaves `aperture_radius = aperture_value * 0.5` = **7.538 mm**, which is a radius AT THE STOP
PLANE being used as an aim radius at the FIRST SURFACE, 132 mm and two groups away.

## Fix: measure the cone that fills the stop

Neither clamp needs to be guessed. Aim one probe ray from the axial object point, read its height
at the stop row with apertures ignored (exactly as `PupilCalc` does), and scale -- the pupil is a
paraxial construction, so one probe fixes the whole cone:

| probe aim | height at the stop | stop-filling aim radius | object NA |
|---|---|---|---|
| 0.250 | 0.18120 | 10.4000 | 0.16000 |
| 1.000 | 0.72481 | 10.4000 | 0.16000 |
| 4.000 | 2.89924 | 10.4000 | 0.16000 |

Linear to five decimals, and 0.16000 is `m/(2*N_working)` = 4/(2*12.5) for this lens -- the
datasheet's own working f-number, recovered from the geometry rather than assumed.

`_stop_filling_launch_radius` is that measurement. It only ever RAISES the historical clamp, and
never past the physical front clear radius, so a scene whose object is already the wider of the
two keeps its launch to the byte. For an `Infinity` object it returns None: there is no aim plane
to scale against, the launch grid IS the pupil.

The same measurement replaces `aperture_value * 0.5` when the declared type is `STOP`, because
that is precisely what a `STOP` declaration means -- a diameter at the stop, translated to the
plane the bundles actually aim at.

## The other half: declare the STOP, not an f-number

The generated layout carried `aperture_type: FNO, aperture_value: 12.5`, which `FNO` resolves
against the system EFL -- 0.824 mm of entrance pupil. bugs/0792 established that a
conjugate-constrained build's EFL is an EQUIVALENT number with no infinite-conjugate meaning, so
an f-number taken against it means nothing either. 0792 fixed the stop ROW diameter and left the
system aperture to be re-derived from that EFL. The importer now declares `STOP` with the solved
stop diameter, which is the aperture this lens actually has.

## The bend is real

`f2 = -23.883` -- above 1x the conjugate solve returns a TELEPHOTO pair (bugs/0792), and a
diverging rear group is the only arrangement that reaches 4x in this track. Group 1 forms its
image **144.0 mm** downstream, 11.5 mm PAST group 2, which takes that converging beam as a
virtual object and pushes it out to the sensor 22.5 mm away:

    1 / (1/(-23.883) + 1/11.5) = 22.18 mm   vs   5.000 + 17.526 = 22.526 mm of real gap

So the beam very nearly crosses at group 2 and is bent back out. That IS a sudden bend, and it is
the lens. It only looked pathological because it was drawn on a pencil instead of a cone -- with
the cone filled, group 2 receives 0.721 mm of beam and hands the sensor a focus.

## Blast radius, measured

Every one of the 157 layouts was checked by recomputing the pre-0795 resolution from the same
inputs and comparing. **5 move**, and all 5 for the same reason -- a declared EPD that the object
semi-diameter had been silently clipping:

| layout | before | after | source_model |
|---|---|---|---|
| `point_cone_source_example` | 2.000 | 9.000 | Random point cone |
| `random_source_illumination_example` | 4.000 | 9.000 | Random circle source |
| `weighted_sourcernd_example` | 4.000 | 9.000 | Random circle source |
| `line_source_illumination_example` | 5.000 | 9.000 | Random line source |
| `machine_vision_150mm_coaxial_led` | 37.000 | 39.000 | Random rectangle source (+3 scene sources) |

All five carry a `source_model`, so `_build_random_source_bundle` (or, for the LED scene,
`_build_scene_source_bundles`) returns first and the preview never reaches the code that consumes
the radius -- the only other reader is bugs/0695's additive mirrored-arm rebuild, which none of
them uses. No validator references any of the four source examples, and the penta MV-150 phases
use `machine_vision_150mm_coaxial_led_FOLDED`, which is not affected. The other 152 layouts are
byte-identical.

Of the 25 lens folders under `attachment/` that build a surrogate, exactly one -- the SPO
TCL4.0X-65DI-5M -- now declares `STOP`; every other keeps its `FNO`/`EPD` to the byte, because
only a conjugate-constrained build takes that branch.

The reference build is shared: `_resolved_preview_pupil_radius` builds the first-order reference
once and hands it to both the probe and `PupilCalc`, so bugs/0166's cost is unchanged.

## The user's saved scene

`machine_vision_spo_tcl4_0x_65di_5m_*.py` on disk still carries `FNO 12.5`, and under an
f-number the fix cannot help it: `min(clamp, EFL/f#/2)` is 0.412 mm whatever the clamp says. Both
halves are needed -- **re-import or re-swap the lens** so the layout carries `STOP 15.0761`.

## Guard

`python -m KrakenOS.UI.validate_open3d_0795_the_object_is_not_an_aperture` -- display-free, on
synthetic layouts in a temp dir with no repo writes and no vendor CAD for the physics. It pins
that the object clamp is what bound (1.375 against a 13.038 mm aperture), that the measured cone
is 10.4000 mm = object NA 0.16000 = m/(2 N_working), that the resolution lands on it and never
past the front clear radius nor on half the stop diameter, that `PupilCalc` genuinely raises on
an object-space telecentric, that the traced axial bundle is 8.320 mm at the front datum and
fills 80% of the stop where it passed 4%, that the conjugate is untouched, that a wider object
resolves identically before and after, that an `Infinity` object measures nothing, and that a
conjugate-constrained import declares `STOP`. Penta phase 578.
