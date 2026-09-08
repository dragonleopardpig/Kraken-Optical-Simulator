# 0752 -- a split field forms TWO images; measure one focus plane per image

User, on my claim that "at 30 mm the image forms ~7.5 mm off the sensor centre":

> everything is symmetry, A and B sides, I can't figure out how to make an Image Plane
> off-centered.

They were right, and the measurement proves it. The optics is symmetric to the last digit.
The off-centre plane was mine.

## The optics is exact

Traced bundle, `attachment/om05a_folded_80mm.py`, 644 landing rays classified by the band each
launched from:

| | rays | u centroid | v centroid | v range |
|---|---|---|---|---|
| Face A field | 322 | -0.0000 | **+5.3474** | +4.233 .. +5.935 |
| Face B field | 322 | -0.0000 | **-5.3474** | -5.935 .. -4.233 |

`v_A + v_B = -0.00000 mm`. `u_A - u_B = +0.0000 mm`. Combined centroid over both arms: exactly
the sensor centre. There is no asymmetry to find.

## Where the off-centre plane came from

`_measure_focused_image_plane` pooled **every** landing ray of **both** arms into one "beam
centre" and then picked the ray nearest it as the axial ray (bugs/0742). On a split field that
pooled centre is `v = 0.0000` -- the **dark ridge between the two strips**, which is precisely
where no ray lands:

```
pooled centre `every`: u -0.0000  v -0.0000   nearest ray anywhere: 4.5059 mm away
```

So the "axial" ray was an **edge** ray, 4.5 mm outside the light, 0.85 mm inside its own arm's
image centre. Worse, the choice between the two arms is an **exact tie** -- 4.5059 mm either way,
by symmetry -- broken by dict iteration order. The plane was then dragged 14.31 mm
(`plane_recentre_mm`) onto whichever arm won the coin flip.

In the loaded scene bugs/0742's straight-leg clause then projected the result back onto the
sensor's own axis, so the drawn plane landed at u=0, v=0 and the defect was **masked, not
absent**. When the walk crosses a fold that clause does not fire (bugs/0729 keeps the walked
point), the arm's edge-ray anchor survives into the drawing, and the plane is visibly off to one
side -- which is what the user kept reporting.

## Fix

A pooled centroid describes a single image. A split field forms **one image per arm**, so
measure one plane per image:

* `_focus_image_partitions(buckets, launches)` assigns each landing bundle to the field band its
  launch point is nearest -- the same rule `measure_split_field_image_strips` already classifies
  landings with, so the focus planes and the measured strips agree by construction. Fewer than
  two bands that actually receive rays -> **one** partition over every bucket, i.e. exactly the
  pooled behaviour every non-split scene had before.
* `_measure_one_focus_image(...)` measures one image: its own waist (bugs/0728), bugs/0729's
  fold-aware walk, bugs/0742's re-centring **on its own landing centre**, and bugs/0751's rule
  that the plane is only ever walked along a real traced ray, never translated.
* bugs/0742's straight-leg clause now projects onto the axis through **that image's** landing
  centre instead of the sensor centre. Collapsing a split-field image to the sensor centre would
  hide the split the user is looking at; for a single on-axis image the two anchors coincide, so
  nothing changes.
* The overlay draws one rectangle + connector per image, each sized to the light it actually
  lands (`half_along_u_mm` / `half_along_v_mm`) rather than the full sensor, each labelled with
  its band name. The banner names every image's offset.

## Result

| | before | after |
|---|---|---|
| axial ray's distance from the light it anchors | **4.5059 mm** (outside it) | **0.00027 mm** (inside it) |
| plane dragged (`plane_recentre_mm`) | 14.31 mm | -- |
| which arm anchors the plane | dict order (exact tie) | each arm anchors its own |
| drawn planes | 1 | 2 |

The two planes come back symmetric, as the user said they must be:

```
plane v:      +5.3474  and  -5.3474   sum -0.000000
plane u:      -0.0000  and  -0.0000   diff +0.000001
offset_mm:   -17.2812  and -17.2799   diff -0.001296
```

Banner:

```
FOCUS: the image forms 17.28 mm in front of the sensor -- spot 1.03 um there vs 606 um on the sensor
  Face A field: 17.28 mm in front of the sensor
  Face B field: 17.28 mm in front of the sensor
Move the device stage / camera focus to land it -- vendor hardware untouched
```

The 0.0013 mm agreement between the two arms is now *visible*, which is the thing that makes the
symmetry checkable at a glance instead of arguable.

## Correction to bugs/0751

0751's revert (never translate the plane onto the sensor) stands and is still right. Its
*interpretation* of the leftover 7.5 mm was wrong: I wrote "that 7.5 mm is REAL -- at this
conjugate the bundle genuinely lands off-centre". It was not real. It was this pooling artefact
-- an edge ray of one arm, picked because the pooled centre sat in the gap between the arms.

## Guard

`validate_open3d_0752_one_focus_plane_per_image.py` (penta phase 542), display-free:

* the partition splits two bands and collapses to one group without bands or with only one fed;
* per-image anchoring picks an axial ray INSIDE its own image, and mirrored inputs produce
  mirrored planes;
* the specs/labels fan out one per image, sized and named per image, with the connector starting
  at that image's landing centre;
* the banner names every image.
