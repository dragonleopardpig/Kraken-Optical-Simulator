# 0741 / 0742 -- report the field the optics deliver, and centre the image plane on the beam

Flag `20260907_143739_657`, "50x50mm device size", asked simply: *is everything correct?* Then,
looking at the render: *"I notice the image plane is shifted to the side from the Center of the
Sensor, you can see the pink color line slanted as well."*

Two defects, both in the READOUT rather than the optics. The trace itself was healthy --
`{"stopped_at_surface_10": 1416, "image": 584}`, 584 rays reaching the sensor on the repaired
scene, the lens moved +136.5 mm cleanly with no collision.

## 0741 -- the banner reported the REQUEST as the delivered field

The scene's device is `width 50, height 1, depth 50`, and the front face spans width x height, so
the request was 50 x 1 mm (+5% -> 52.5 x 1.05). The banner said:

    SOLVE: delivering 52.5 x 1.05 mm (|m| 0.4389)

but at |m| 0.4389 a 23.04 x 23.04 mm sensor images **52.5 x 52.5 mm** of object. The success path
stashed the delivered field as the request:

```python
summary = {
    "requested_fov_wh": (float(obj_w), float(obj_h)),
    "delivered_fov_wh": (float(obj_w), float(obj_h)),   # <- the request, not the delivery
}
```

while the NO-OP path right above it computed it properly (`sensor / |m|`, via
`_fov_already_delivered`) and said "Already delivering 52.5 x 52.5 mm". The two paths disagreed
about the same scene, and the banner understated the imaged height by 50x.

Now both compute it from the achieved magnification. Measured after the fix: requested
`(52.5, 1.05)`, delivered `(52.5, 52.5)`, |m| 0.4389.

**Not a bug, but worth stating:** the inspected face is `width x height`. A "50 x 50 device" needs
`height_mm = 50`; setting `depth_mm = 50` sets the separation between the front and back faces, not
the face itself.

## 0742 -- the drawn image plane sat 11.6 mm to the side of the beam

bugs/0729 places the focused image plane by walking the winning field's rays back along their REAL
traced path (a folded tail is shorter than the waist distance, so a straight extrapolation lands
past the fold mirror). Correct for the fold -- but the *winning field* is one field among many, and
its bundle lands wherever that field point images, off-axis. Walking it back put the drawn plane
beside the beam:

| | measured |
|---|---|
| sensor centre | `[272.633, -1.759, -25.000]`, normal `[0, -1, 0]` |
| focus centre (before) | `[283.599, 19.182, -28.852]` |
| along the sensor normal | -20.941 mm (the reported defocus -- correct) |
| **lateral from the centre** | **11.623 mm** |
| angle between normals | 0.0000 deg |
| landing rays | 644, centroid on the sensor centre to **0.000 mm** |

So the rays landed dead centre while the plane was drawn 11.6 mm off. The "slant" is perspective on
an off-centre rectangle -- bugs/0733 still holds, the plane is parallel to the sensor to 0.0000 deg.

Two steps to fix it, because the first was only approximate:

1. Anchor the walk on the ray that lands nearest the **beam centre** rather than on the winning
   field -- same real-path walk, so bugs/0729's fold handling is untouched. That fixed x exactly
   and left 3.851 mm in z: om05a's split-field beams arrive ~10.4 deg off normal, so walking any
   single ray back 20.94 mm displaces it sideways by `20.94 * tan(10.4 deg)`.
2. When the walk crosses **no fold** -- the transported normal comes back equal to the sensor's --
   the waist is on the same straight leg as the sensor, so the rectangle belongs on the sensor's
   own axis. Keep the along-axis distance from the walk and drop the lateral wander, which is an
   arrival ANGLE, not a sideways shift of the image.

   When a fold WAS crossed, the walked point is kept untouched: the waist really is around the
   corner, which is what bugs/0729 was for. Penta 528 (the folded case) still passes.

After: focus centre `[272.633, 19.182, -25.000]` -- **lateral 0.000 mm**, angle 0.0000 deg, defocus
-20.941 mm.

## Still open (reported, not fixed)

`offset_spread_mm` is **118.63 mm** on this scene: the per-field waists disagree by 118 mm, so a
single "image plane" with a 0.226 um spot describes the winning field, not the system. The banner
presents it without that caveat. Worth either quoting the spread or drawing a per-field range.

## Guard

`KrakenOS/UI/validate_open3d_0741_delivered_field_and_plane_centre.py` (penta phase 538).
