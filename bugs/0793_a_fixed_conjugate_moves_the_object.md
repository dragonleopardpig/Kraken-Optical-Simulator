# 0793 -- a fixed-conjugate lens brings its object distance with it

`flag_20260916_105357_603`, on a scene holding the Hikrobot MV-CS050 and the SPO TCL4.0X-65DI-5M:
*"rays seems like not focusing to sensor."*

The banner:

    FOCUS: the image forms 40.96 mm in front of the sensor -- spot 6.62e-12 um there vs 957 um
    Magnification: 0.924x (sensor/FOV)

A spot of 6.6e-12 um at best focus says the optics are ideal. The CONJUGATE was wrong.

## Measured, from the saved rows

The scene held a **110 mm** object leg and a **19.526 mm** rear gap. Tracing its own emitted
groups (f1 47.112667, f2 -23.882528, d 132.5):

| object leg | rear gap | magnification | where the image lands |
|---|---|---|---|
| **110.0** (as saved) | 19.526 | **-0.2164** | a VIRTUAL image 16.4 mm BEFORE the rear group -- **40.960 mm** in front of the sensor |
| **65.0** (the lens's own) | 17.526 | **-4.0000** | on the sensor, **0.000 mm** defocus |

40.960 reproduces the banner's 40.96 exactly. 110 mm is the WORKING DISTANCE OF THE OUTGOING
LENS -- the 1x WWK10-110CP-111V3.

## Root cause

A swap preserves the object leg by design (bugs/0378: "Object ... are preserved") and moves the
IMAGE to the new lens's best focus (bugs/0388). For a lens whose object distance is free that is
right. For a FIXED-CONJUGATE lens it is not: it operates at one point, and 45 mm outside it this
one forms no real image at all -- so the refocus had nothing to find.

bugs/0656 already knows this and places the object at the vendor working distance on a swap. It
is gated on `_lens_datasheet_wd_registration()`, which could not run here for two independent
reasons, both measured:

* it needs a **lens STEP mesh** to measure object-to-rim, and the SPO folder ships none
  (`.dwg` + `.pdf` only); and
* it applies `0 < f(1+1/m) - WD < f` -- the coincident-principal-plane law that bugs/0792
  established is unreachable above about 1x. Here it evaluates to **-19.995**, so the
  registration returns None before the mesh is even consulted.

So the one lens that most needs its object placed was the one lens the placement could not serve.

## Fix

A conjugate-constrained surrogate (bugs/0792) already knows its object distance: it was BUILT
with the object at the vendor working distance, and its front datum IS the housing rim, so
`object_thickness` is that distance with nothing to measure. The model now says so
(`fixed_conjugate`), and the swap applies it when the measured route cannot -- after bugs/0656,
so a lens that CAN be measured still gets the measured answer, and before the refocus, because
otherwise there is no best focus to snap to.

The flag is deliberately narrow: **only** the conjugate-constrained build sets it. On the EFL
route the object gap is DERIVED (the 1x WWK10's is 70.846 mm against a stated 110 mm working
distance, the difference being exactly what bugs/0647's registration refit exists to correct), so
claiming it as a contract there would move the object to a number no datasheet states.

## The user's scene

`attachment/MV-CS050-60UM_V5_TCL4.0X-65DI-5M` still holds 110.0 / 19.526. It is the user's file
and predates this fix, so it is left alone: set the object leg to **65** and the rear gap to
**17.526**, or re-do the swap.

## Noticed while reading it, not fixed here

That scene saved as `MV-CS050-60UM_V5_TCL4.0X-65DI-5M` -- with no `.py` -- and its settings
sidecar as `MV-CS050-60UM_V5_TCL4.open3d.json`, both truncated at the first dot of "TCL4.0X".
A layout name containing a dot is being run through a stem/suffix split. Worth its own bug.

## Guard

`python -m KrakenOS.UI.validate_open3d_0793_a_fixed_conjugate_moves_the_object` -- display-free
and offline; it reproduces the flag's 40.96 mm from the saved numbers, shows the same groups
focus at 65 mm, pins that only the conjugate-constrained build claims the contract (the 1x
telecentric and an ordinary lens must not), and pins the ORDER in the swap: measured route first,
model fallback second, both before the refocus. Penta phase 576.
