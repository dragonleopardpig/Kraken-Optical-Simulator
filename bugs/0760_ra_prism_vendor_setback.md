# 0760 -- the big inverted RA prism was seated 3.563 mm too close to the housing

User, with two annotated screenshots (`attachment/original.jpg`, `attachment/converted.jpg`):

> Have you add the little gap between the big inverted RA mirror and the prism assembly?

Cropping both red boxes settles it: the vendor view shows the housing plate, then white space,
then the prism apex lower down. The scene render has the prism touching the plate underside.

## Correcting myself first

Much earlier in this arc I reported the gap as "present, measured three ways -- vendor 7.60 /
optical rows 7.88 / displayed chunk 7.53 mm" and asked the user to point at what looked wrong.
The 7.60 mm was right about the VENDOR. The claim that the scene had it was wrong, and it stalled
this item for a long time.

## The vendor number

`om05a_26_1_r03_2s_lr_asm.stp`, 12 solids. Exactly one matches a 50 mm RA-mirror envelope:

```
solid 5   size [49.9, 49.9, 50.0]
          x[-114.300, -64.400]  y[83.200, 133.100]  z[-23.500, 26.500]
nearest part above it:  +y gap  7.596 mm
```

The scene, measured the same way (clearance gated on overlap in the other two axes):

```
attachment/om05a_folded_80mm.py    gap 4.033 mm
attachment/om05a_folded.py         gap 4.033 mm
```

Shortfall **3.563 mm**, identical in both files.

## Why the wedge stays

The scene's prism is an analytic 6-vertex wedge
(`cad_cache/promoted_step_overlays/optical_analytic_*.stl`, local bounds +-25 mm). The vendor part
`mirror1_50.step` measures 49.900 x 49.900 x 50.000 -- so the surrogate's DIMENSION is already
right and only the seating was wrong. Per the user's call, the wedge stays (swapping in the vendor
body would risk changing the fold the trace runs on) and the seat is corrected.

## Fix

`row 7 'RA mirror 1 (50 mm)'  desp_y  +52.8000 -> +56.3630`, in BOTH scenes.

The move is perpendicular to the beam, so the optics is untouched:

| | gap | \|m\| | field | residual | rays |
|---|---|---|---|---|---|
| before | 4.033 mm | 0.42595319 | 54.0905 | -0.0535 / -0.0537 | 322 |
| after | **7.596 mm** | 0.42595311 | 54.0905 | -0.0535 / -0.0537 | 322 |

|m| agrees to seven significant figures and the residual is identical. bugs/0750 audit: exactly
one row moved off its authored placement -- row 7, +3.5630 mm, which is the intended edit.

## Consequence worth knowing

The sensor's world position shifts `[272.633, -2.609, -25.0] -> [269.070, 0.954, -25.0]`: moving
the fold prism translates the folded beam and the downstream chain follows it. RA mirror 2 does
NOT move (it is absolutely seated). The conjugate is preserved exactly, so this is benign
optically. If the camera's absolute position is believed correct as it was, the alternative is to
move the HOUSING 3.563 mm the other way and leave the prism and camera put -- same gap, nothing
optical moves at all.

Backups: `om05a_folded_80mm.py.pre-gap.bak`, `om05a_folded.py.pre-gap.bak`.

---

## Follow-up: the whole downstream group must travel, and the frames are mirrored

User: *"the gap introduced, then all the following lens+filter+RA mirror+camera should shift down
together."* Correct -- and the first cut did not do it. Measured deltas after the prism move:

```
RA mirror 1 (50 mm)            [0.0, 3.563, 0.0]
RA mirror 2 (40 mm)            [0.0, 0.0, 0.0]      <- LEFT BEHIND
Filter 48-926                  [-3.563, 3.563, 0.0]
Front/Rear Optical Vertex      [-3.563, 3.563, 0.0]
SENSOR                         [-3.563, 3.563, 0.0]
```

RA mirror 2 is absolutely seated, so it does not ride the chain and has to be moved explicitly.
The 5.039 mm diagonal is 3.563 x sqrt(2) -- the correct displacement of a beam folded by a 45 deg
mirror moved 3.563 mm.

**And the two scenes are mirrored in x.** `om05a_folded.py` carries RA mirror 2 at
`desp_x -272.70` against `+272.68` in the 80 mm file. Applying the 80 mm delta to it verbatim put
the mirror the wrong way and left the sensor 3x displaced:

```
RA mirror 2   [-3.563, 3.563, 0.0]   <- wrong sign for this frame
Filter, lens  [+3.563, 3.563, 0.0]
SENSOR        [-3.563, 10.689, 0.0]  <- broken
```

Corrected to `+3.563` there (net `desp_x +7.126`). Both scenes are now coherent:

| scene | prism | group | gap | arms | \|m\| | field | residual |
|---|---|---|---|---|---|---|---|
| `om05a_folded_80mm.py` | [0, +3.563, 0] | [-3.563, +3.563, 0] | 7.596 | 322 / 322 | 0.425953 | 54.090 | -0.0535 / -0.0537 |
| `om05a_folded.py` | [0, +3.563, 0] | [+3.563, +3.563, 0] | 7.596 | 644 / 644 | 0.412444 | 55.862 | -0.4565 / -0.4564 |

The production file traced **arm B = 0 rays** before this work and now traces 644 on both arms
with matching |m|.

## Process note

Two self-inflicted errors here, both caught only by measuring components individually:

* the first fix moved the chain but not the absolutely-seated mirror, and the trace still passed
  -- the conjugate happened to be preserved, so a residual check alone could not see it;
* the verification script hardcoded the 80 mm scene path and ignored its argument, so "both
  scenes verified" was one scene verified twice. The production sign error survived that check.

A per-component delta table is the check that catches both. A residual is not enough.
