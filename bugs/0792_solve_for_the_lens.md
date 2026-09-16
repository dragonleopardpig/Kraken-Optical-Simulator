# 0792 -- a catalogue states the conjugates, so solve for the LENS

User: *"non of the vendor will release those information unless you are their number one
customer."* That is the constraint this change accepts. bugs/0790 established that the SPO
TCL4.0X-65DI-5M is fully legible and still un-importable, because

    f (2 + m + 1/m) + HH' = track

is one equation in two unknowns and no machine-vision catalogue states the second. bugs/0653
closed it by assuming coincident principal planes. That is right near 1x and false above it.

## The assumption, measured

| lens | m | WD | housing | track | f (HH'=0) | object -> H | H vs rim | |
|---|---|---|---|---|---|---|---|---|
| Edmund 67-304 | 0.75 | 110 | 155 | 282.53 | 69.19 | 161.44 | +51.44 | OK |
| COOLENS WWK10 | 1.00 | 110 | 152.6 | 280.13 | 70.03 | 140.06 | +30.06 | OK |
| **Edmund 62-793** | 4.00 | 65 | 110 | 192.53 | 30.80 | 38.51 | **-26.49** | refused |
| **SPO TCL4.0X** | 4.00 | 65 | 142.5 | 225.03 | 36.00 | 45.01 | **-19.99** | refused |

A 4x lens at 65 mm working distance needs a **325 mm** track for coincident principal planes;
real ones are 192-225 mm. It is not one vendor being terse -- **Edmund's own 4x/65 mm lens fails
the same test, harder.** And no thick lens can rescue it: for the 62-793, H inside the housing
needs f >= 52 mm while H' inside needs f <= 25.5 mm. The windows do not overlap, because a 4x
telecentric in a 110 mm barrel is a compound, telephoto-like design whose EQUIVALENT principal
planes genuinely lie outside its own envelope.

## Fix -- stop solving for a focal length; solve for the lens

The catalogue does pin the conjugates. Fix the two groups where the hardware puts them -- just
inside each end of the housing -- and their powers follow exactly::

    a  = WD + margin            object -> group 1
    b  = flange + margin        group 2 -> image
    d  = housing - 2 margin     separation
    v1 = m a d / (m a - b)      intermediate image, from group 1
    f1 = a v1 / (a + v1)
    f2 = b (v1 - d) / (v1 - d - b)

Above 1x, `v1 > d` always, so the intermediate image falls BEHIND group 2, which therefore sees a
virtual object and comes out **negative** -- the telephoto pair the geometry demanded all along.

Two consequences worth stating:

* **The stop is the cone, not `effl / f#`.** A catalogue f-number for a fixed-conjugate lens is
  the WORKING one, so `NA_object = m / (2 N)`, and the marginal ray reaches the stop at
  `a NA (1 - f1/v1)`. For the Edmund 62-793 that is **6.50 mm**, where `effl / f#` would have
  given **0.32 mm** -- a cone wrong by a factor of twenty.
* **The stop goes at group 1's back focal plane**, which is what makes the entrance pupil infinite
  and the chief rays parallel off the object. The default half-way split leaves a surrogate merely
  finite-conjugate; for these it now sits at `f1`, which the solve guarantees lies between the
  groups.

Applied ONLY where the old route fails: `telecentric_conjugate_cardinals` and the DWG builder now
mark the case `conjugate_constrained` instead of refusing, and the builder solves for the lens.
Everything that already worked is untouched -- PYRITE 56/80 still `asymmetric` at effl 82.39,
WWK10 still `efl-span-symmetric` at 70.0315.

## Measured -- the SPO TCL4.0X-65DI-5M now imports

    Object                      thick  65.0000      <- the stated working distance
    Front Optical Vertex Datum  thick   5.0000
    Blackbox Group 1            thick  47.1127  rc  47.112667
    Aperture Stop               thick  85.3873      <- f1 behind group 1: telecentric
    Blackbox Group 2            thick   5.0000  rc -23.882528
    Rear Optical Vertex Datum   thick  17.5260      <- the C-mount flange
    Image / Sensor                           diam  11.000

Traced paraxially through those emitted groups: **m = -4.0000**, and a 2.2 mm object images to
**8.800 mm** -- the 2/3" sensor width the datasheet's own F.O.V row quotes. Stop 15.076 mm, which
traces back to exactly f/12.5.

## What this does and does not claim

It reproduces the vendor's contract -- magnification at the stated working distance with the image
at the mount flange, the stated image circle, the stated working f-number -- which is what a
layout and a ray trace need. It does **not** claim to be the vendor's design: the catalogue leaves
one free parameter, and this picks the member whose groups sit in the barrel. A lens meant to be
refocused to a different magnification still wants a real prescription.

## Guard

`python -m KrakenOS.UI.validate_open3d_0792_solve_for_the_lens` -- display-free and offline;
for the Edmund 62-793, the SPO TCL4.0X and a synthetic 2x it pins the delivered magnification,
the object at the working distance, the image at the flange, both groups inside the housing, the
telephoto sign above 1x, a stop that traces back to the catalogue f-number, and the telecentric
stop position -- plus refusal of geometry it cannot honour. Penta phase 575.
