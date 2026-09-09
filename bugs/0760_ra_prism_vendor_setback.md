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
