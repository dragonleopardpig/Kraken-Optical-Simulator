# 0794 -- when the vendor ships no STEP, build the envelope from the drawing

User: *"while I am getting the STEP file from the vendor, can you built a STEP file out of the PDF
or DWG drawing so that the algorithm works as expected?"*

Yes -- from the DWG, and derived rather than modelled by eye.

## Why a body matters

Several things measure against the lens BODY: the camera-clearance clamp needs something to
clear, bugs/0656's working-distance placement needs a rim to measure object-to-rim against, and
the scene has nothing to draw. The SPO TCL4.0X-65DI-5M ships a `.dwg` and a `.pdf` and no STEP, so
all of them were blind -- one of the two reasons bugs/0793's object placement had to fall back to
the model.

## The drawing already states the barrel

Its dimension entities carry a value AND the two points it spans, at 1:1 mm. Read that way:

    axis        y = 184.5      (all three on-axis radial dimensions centre there)
    front rim   x = 181.816    rear x = 324.30     ->  142.482 mm

    0.000  ..  54.900   diameter 31      (the 31.000 callout stands at x 213.06)
    54.900 ..  66.500   diameter 34      (34.000 at x 247.82)
    66.500 .. 142.482   diameter 30      (30.000 at x 323.80)

    coaxial port  diameter 16, standing 20.5 proud, 45.561 mm from the rim

`54.900 + 11.600 + 75.982 = 142.482`. The bands close on the body length exactly, and that is the
CHECK -- a profile assembled from the wrong dimensions does not close.

## Two rules make the derivation trustworthy

* **Each on-axis radial dimension marks one band**, at its own station. That is what a diameter
  callout means, and it is why the bands cannot be invented.
* **The port's own dimensions must not cut the profile.** The drawing's parenthesised reference to
  the port centre (the `(45.6)`) sits between the 31 and 34 callouts; taken as a step it moved the
  first band from 54.900 to 45.561. The port is therefore identified FIRST and its endpoints are
  excluded from the boundary candidates.

Both were found by getting them wrong first, and both are pinned by the guard.

## Result

`bugs/build_step_from_dwg_profile.py <drawing.dwg>` revolves the bands about the axis, fuses the
port, and writes `<drawing>.envelope.step`. Measured on the produced solid:

| | |
|---|---|
| axial extent | **142.482 mm** -- the body length |
| transverse | **34.0 mm** -- the largest diameter |
| across the port | **54.5 mm** (17 + 20.5 + 17) |

`scan_lens_folder` then classifies it, and the import wires it: `step=...envelope.step`, with the
surrogate unchanged (effl 10.297, object_thickness 65.0, fixed_conjugate).

## What it is, and is not

It is the **mechanical envelope the drawing dimensions** -- enough for clearance, for the rim, and
for the scene to draw something honest. It is NOT the vendor's CAD: no threads, no glass, no
internal detail, and the STEP's product name says so. Replace it when the vendor's own STEP
arrives.

The generated file is left beside the drawing rather than committed, because that vendor folder is
not tracked; the BUILDER is committed, so it can be re-run for the next vendor who ships only a
drawing.

## Still open

With the envelope present the swap still reports *"focus limited to 19.5 mm so the camera body
clears the upstream element"* -- the same 2 mm that flag_20260916_105357 carried, worth ~160 um of
blur. A C-mount camera is MOUNTED against the lens (bugs/0656's own words: "MOUNTED, never solved
into the barrel"), so a clearance clamp demanding a gap at that interface is the next thing to
look at, not this body.

## Guard

`python -m KrakenOS.UI.validate_open3d_0794_a_body_from_the_drawing` -- display-free; pins the
axis, the body length, all three bands, that the bands CLOSE, that the port is found and did not
cut the profile, and that the built solid's extents are the drawing's. Penta phase 577.
