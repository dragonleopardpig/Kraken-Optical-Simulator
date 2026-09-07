# 0744 -- om05a cannot focus at the fields being asked for, and the tool never says so

Flags `20260907_18xxxx` / `20260907_192856_304`:

> "I doubt we have any device that won't put the image plane in front of the sensor. Seems 50mm,
> 30mm and 20mm device size all fail!"
> "I changed to 30x30mm device size, still can't solved. Now I seriously doubt no device size can
> solve!"

The user is right for every size they tried, and the reason is geometric, not a solver defect.

## Measured

The object->sensor track is **433.360 mm** and fixed. The only gap in front of the vendor chain is
the device gap, **5.350 mm**. The FOV solve sets magnification by sliding the lens; with the object
AND the sensor both fixed, the conjugate closes only at particular magnifications, so every other
request lands the image in front of the sensor:

| device | delivered \|m\| | focus residual | lens move |
|---|---|---|---|
| 14 mm | 1.5673 | -82.73 mm | -135.2 |
| 18 mm | 1.2190 | -96.40 mm | -120.2 |
| 22 mm | 0.9974 | **-99.65 mm** (worst) | -105.1 |
| 30 mm | 0.7314 | -91.52 mm | -75.1 |
| 42 mm | 0.5224 | -63.68 mm | -30.0 |
| 50 mm | 0.4389 | (no-op; measured -20.94 mm) | -- |
| 58 mm | 0.3783 | -15.48 mm | +30.0 |
| 60 mm | 0.3657 | **-9.01 mm** | +37.5 |
| 61 mm | -- | REFUSED | +41.3 needed |

The residual shrinks monotonically as the field grows, and would reach zero at roughly a **62 mm**
field. It never gets there: at 61 mm the solve refuses because

    that field needs the lens +41.3 mm along its leg, but only 40.15 mm of physical room is left
    before its body reaches RA mirror 2 (40 mm) -- short by 1.155 mm

**The build is ~1.2 mm of lens travel short of a focused configuration.** Everything at or below a
60 mm field is 9-100 mm out of focus by construction; nothing the FOV solve can do changes that,
because the solve is only allowed to move the lens.

## Why the solve cannot fix it

For a fixed effective focal length, a target magnification fixes BOTH conjugates -- object-to-lens
and lens-to-sensor. The sensor is vendor hardware and immutable
([[feedback_vendor_hardware_immutable]]), and the device gap offers 5.350 mm, so the track cannot
absorb the 9-100 mm it needs. The solve therefore delivers the FOV and reports a residual, which is
honest but leaves the user with "it never focuses" and no way to see why.

## What the tool should say (not yet built)

A residual should come with the geometry that explains it:

* this track focuses at a ~62 mm field (\|m\| ~ 0.35); you are asking for one that cannot;
* the lens is blocked 1.155 mm short of it by RA mirror 2;
* closing it needs a bench change -- the camera moved ~9 mm, the device stage moved, or a shorter
  EFL -- none of which the tool may do on its own.

Today the user has to solve a ladder of device sizes by hand to discover this.

## Not a defect in

The solve, the ghost (bugs/0740), the delivered-field readout (bugs/0741) or the image-plane
placement (bugs/0742). Those were all verified correct while measuring this.

## Addendum -- the PRODUCTION scene is the one that focuses

The finding above is about `om05a_folded_80mm.py`, which the user built as an experiment (big RA
mirror flipped for internal reflection, lens 85 -> 80 mm). The production build,
`attachment/om05a_folded.py` (PYRITE 4.5/85, 0.5-2.0x), was still carrying the bugs/0722 defect --
first RA mirror normals `(0, 0.703508, -0.710687)` = **44.7092 deg**, so the fold was 89.42 deg, not
90 -- because 0722 deliberately left it alone ("the older 50 mm scene still references the previous
cached meshes and was left as is").

Squared and re-seated with the existing tool (backup `om05a_folded.py.pre-0722-prod.bak`):

    bugs/0722_square_first_ra_mirrors.py --apply attachment/om05a_folded.py
    bugs/0722_square_first_ra_mirrors.py --seat  attachment/om05a_folded.py

`--apply` took both first RA mirrors 44.71 -> 45.00 deg; `--seat` moved the front-datum frame-desp
(-6.0798, 0, -0.3885) -> (-8.78, 0, -0.3885), landing the datum and the sensor on z = -25.000.

Verified: every fold **90.0000 deg**; strips **A +3.6011..+3.6483 / B -3.6483..-3.6011**, pair
midpoint -0.00000 mm (symmetry error **0.00000 mm**); 1288 rays reach the image.

FOV long side 20 -> 54 mm, all ten sizes solve with no refusal, and this build DOES reach focus:

| long side | \|m\| | delivered FOV | residual |
|---|---|---|---|
| 20 | 1.0971 | 21.00 x 21.00 | -72.15 mm |
| 32 | 0.6857 | 33.60 x 33.60 | -60.62 mm |
| 44 | 0.4987 | 46.20 x 46.20 | -29.99 mm |
| 51 | 0.4303 | 53.55 x 53.55 | -8.66 mm |
| 53.7 | -- | -- | **-0.455 mm** (traced; 19 um spot on the sensor, 1288 rays) |
| 54 | 0.4063 | 56.70 x 56.70 | +0.95 mm |

Focus crosses zero at about **53.8 mm**.

## Open, found while measuring

* The vendor assembly puts **7.60 mm** between the Big RA mirror (vol 62499.5 = 50^3/2) and the
  nearest prism (centre mirror); the scene's optical rows have **7.880 mm** -- 0.28 mm wide.
* The DISPLAYED `prism_assembly_chunk_armA.step` overlay spans y -5.23..60.77 and overlaps RA
  mirror 1's solid (y 27.80..77.80) by **32.967 mm**, so the 3D view shows no gap where the optics
  have one. A display-overlay placement problem, not the optics.
* Both scenes carry `camera_step_rotation_x/y = 0.5817 / 359.4183 deg` -- numerically the same
  0.58 deg dip 0722 removed from the chain. Unverified whether it is a stale compensation.

## CORRECTION -- the 80 mm variant DOES focus; the residual I swept is wrong by a constant

The user asked whether the focus shift from the Big RA mirror glass (and then the BS cube and the
Edmund filter) had been taken into account. It had not, and checking it overturned the conclusion
above.

The sweep used `image_delta_mm`, the FIRST-ORDER residual. The traced waist (real rays through the
real solids) disagrees with it by a CONSTANT:

| device | paraxial | traced | difference |
|---|---|---|---|
| 30 mm | -91.522 | -71.983 | +19.539 |
| 50 mm | (no-op) | -20.941 | -- |
| 56 mm | -21.877 | -2.281 | +19.596 |
| 58 mm | -15.481 | +4.116 | +19.597 |

**+19.55 +- 0.03 mm, flat** -- the signature of a fixed slab missing from the first order. By the
TRACED waist the 80 mm variant crosses focus at about **56.7 mm**, comfortably reachable. The
"structurally cannot focus" claim was an artefact of quoting the paraxial number.

## What glass the model actually carries

| element | modelled | shift |
|---|---|---|
| BS cube A (row 3) | BK7 15 mm | +5.122 mm nominal; the axis ray crosses 19.27 mm -> +6.58 mm |
| Filter 48-926 (row 13) | N-BK7 1 mm | +0.341 mm |
| **RA mirror 1 (50 mm)** | **glass = AIR** | **0 -- an internal-reflection prism would give +17.07 mm** |
| First RA mirror A/B, Centre A/B, RA mirror 2 | glass = AIR | 0 |

Every RA mirror is a front-surface mirror in the model. Total shift carried: **+5.463 mm**. If the
build uses internal-reflection prisms (the user flipped the Big RA mirror for exactly that), their
glass is absent everywhere.

Note the 19.55 mm paraxial gap is NOT the glass: the model carries 5.46 mm and the trace sees
6.58 mm. It is a separate first-order defect in the folded conjugate.

## Consequence for the reported numbers

Every "focus residual" line the banner shows comes from the first order, so it is ~19.5 mm
pessimistic on this scene. The detached image plane (bugs/0728) is measured from the TRACE and is
correct -- the two readouts in the same scene disagree by that amount.

## Prism glass modelled (user spec) -- and a row-model trap

User: "Only the big RA mirror is internal reflection because I rotate it from external reflection.
The rest of the RA mirror is external. So in summary, for internal reflection: BS cube, big inverted
RA mirror and Edmund Filter."

So the PRODUCTION scene needs no change -- its big RA mirror is external, and `glass=AIR` is right.
Only `om05a_folded_80mm.py` (the flipped variant) was missing glass. Row 7 set to BK7
(backup `om05a_folded_80mm.py.pre-prismglass.bak`; N-BK7 differs by <0.01 mm here).

The TRACE now does the right thing -- the axis ray's glass path goes 19.27 -> 85.880 mm, the new
legs being `RA mirror 1: 16.61 + 25.00 + 25.00` = 66.61 mm of internal path:

| device | traced waist before | traced waist after |
|---|---|---|
| 30 mm | -71.983 | -32.845 |
| 42 mm | -- | +1.713 |
| 46 mm | -- | +14.235 |

Traced focus now crosses at about **41.4 mm**, and the scene solves 20-46 mm (48 refuses: the lens
needs +46.47 mm of leg against 40.15 mm before RA mirror 2).

**The trap:** the FIRST ORDER reads a row's glass as filling that row's THICKNESS, and row 7's
thickness is the 158.07 mm gap AFTER the prism, not the prism. The paraxial residual moved
-91.522 -> -37.546 = **+53.976 mm**, and 158.07 x (1 - 1/1.5185) = **53.97 mm** -- an exact match.
So the first order now believes 158 mm of BK7 where the prism is 50 mm (66.61 mm of path).

The trace is geometry-driven and correct; the paraxial readout is not. That is why the
paraxial-vs-traced gap is +4.7 to +12.7 mm and grows with field.

**Proper fix (not done -- needs a scene-structure decision):** the prism wants its own glass row
carrying the prism's thickness, with the following gap left in AIR. Restructuring rows touches the
follower walk and the 0722 seat, so it should not be done casually.

**Meanwhile: judge focus by the traced waist, never by the banner residual.**

## Row split done -- the prism's glass now fills the PRISM, not the gap

`om05a_folded_80mm.py` row 7 was carrying BK7 across its 158.07 mm thickness (the gap AFTER the
prism). Split, keeping the station sum exact (backup `om05a_folded_80mm.py.pre-rowsplit.bak`):

* row 7 `RA mirror 1 (50 mm)`  -- BK7, thickness **50.0 mm** (the prism)
* row 8 `prism exit gap (air)` -- AIR, thickness **108.0696 mm**, undrawn scaffolding

50.0 + 108.0696 = 158.0696. **Worst downstream station shift: 0.000000000 mm** -- nothing moved.
Verified after: folds still **90.0000 deg**, and the front datum / filter / sensor still on
centre z = -25.000, so the bugs/0722 seat survives. 25 rows now; the FOV solve's leg gap becomes
row 8 (the air gap), which is the physically right thing to adjust.

Corrected behaviour, and the delivered FOV tracks the request again (the 158 mm bug had it
returning 26.60 for a 21.00 request):

| long side | \|m\| | delivered FOV | paraxial | traced waist |
|---|---|---|---|---|
| 20 | 1.0971 | 21.00 x 21.00 | -81.86 | -- |
| 30 | 0.7314 | 31.50 x 31.50 | -74.45 | -54.898 |
| 50 | 0.4389 | 52.50 x 52.50 | -23.46 | **-3.826** |
| 52 | -- | -- | -17.34 | **+2.292** |
| 56 | 0.3918 | 58.80 x 58.80 | -4.80 | -- |
| 60 | -- | -- | REFUSED (needs +54.62 mm of leg) | -- |

**Traced focus crossing ~51.3 mm; solves 20-56 mm.**

## The +19.55 mm first-order defect is NOT the glass -- still open

| prism glass state | paraxial - traced |
|---|---|
| none | +19.539 |
| 158 mm (the row bug) | +4.70 (coincidentally masked) |
| **50 mm (correct)** | **+19.551 / +19.633 / +19.632** |

Flat at **+19.55 mm** whether the prism glass is modelled or not, so it is an independent defect in
the folded first order -- and it is what the solve banner reports. The traced waist (bugs/0728's
detached image plane) is the trustworthy readout. Two numbers in the same scene disagree by 19.55 mm.
