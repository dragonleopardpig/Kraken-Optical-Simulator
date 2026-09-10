# 0774 -- a field that overflows the sensor must be said, not silently clipped

> "I noticed the two image strips going outward from the center of the sensor, reaching the
> boundary at 21mm device size. Do you take this into account?"

No. I had spent the whole 21 mm investigation measuring waists along the optical axis and never
once checked where the strips sat relative to the sensor bounds. A ray that reaches the detector
PLANE but lands beyond its active area counted as landing, and the banner reported focus residual
and spot size as usual.

## Two laws

Fitted and then verified to +-0.005 mm across two device sizes and five magnifications:

```
LAW 1  strip POSITION   |u|outer = 9.278 * |m|         the fixed arm offset, magnified
LAW 2  strip LENGTH     |v|half  = device * |m| / 2
```

| device | FOV | \|m\| | u_outer | 9.278\|m\| | v_half | device·\|m\|/2 |
|---|---|---|---|---|---|---|
| 24.0 | 25.20 | 0.9143 | 8.483 | 8.483 | 10.975 | 10.971 |
| 22.0 | 23.10 | 0.9974 | 9.254 | 9.254 | 10.975 | 10.971 |
| 21.5 | 22.57 | 1.0208 | 9.469 | 9.471 | 10.975 | 10.974 |
| 25.0 | 26.25 | 0.8777 | 8.144 | 8.144 | 10.975 | 10.971 |
| 30.0 | 34.00 | 0.6776 | 6.287 | 6.287 | 10.167 | 10.165 |
| 30.0 | 28.00 | 0.8229 | 7.635 | 7.635 | clipped | 12.343 |
| 30.0 | 24.00 | 0.9600 | 8.907 | 8.907 | clipped | 14.400 |

Consequences worth knowing:

- With the **default +5% field the strips always sit at 95.2%** of the sensor half, whatever the
  device size. That permanent 4.8% margin is why it always looks close to the edge.
- The field overflows the ENDS whenever the requested **FOV is smaller than the device**. A 30 mm
  device at FOV 24 images only **80%** of the part.
- The position boundary is reached at **|m| = 1.2416 -> FOV 18.56 mm -> device 17.67 mm**.

## Counting landings is not enough

A ray heading well past the sensor never reaches it, so a landing census sees only the sliver AT
the boundary: the 30 mm / FOV 24 case registers **44 rays 0.005 mm out** while LAW 2 says
**2.88 mm per side** is lost. So the check predicts the extent from the device and the delivered
magnification, and reports the captured fraction; the ray count is kept as corroboration for the
edge case where nothing is predictable.

Verified against the measurement: predicted field half 10.165 vs measured v 10.167 (device 30,
FOV 34) and 10.971 vs 10.975 (device 21) -- the two non-overflowing cases agree to 0.004 mm.

## What this does NOT explain

Device 21 at its default field has **zero** overflow (captured 100%), so the strips reaching the
boundary is not the cause of the 21 mm asymmetry. That remains open, with five hypotheses now
eliminated: edge-of-machine, stray rays, lens jammed against the prism, lens-move capped
(measured: requested -129.1350, applied -129.1350 in full), and field off the sensor.

What the laws DO give is an exact, independent check on the delivered magnification straight from
the traced strip position -- and by it, device 21 violates LAW 1 by 1.393 mm while every other
size obeys it to 0.002 mm. That is the sharpest statement of the bug so far.

## Guard

`KrakenOS/UI/validate_open3d_0774_field_overflowing_the_sensor_is_said.py`, penta phase **558**:
an overflowing field is reported with the overflow, both sizes, the captured fraction and the
remedy (A); a field inside the sensor says nothing (B); the captured fraction is LAW 2, checked
against all three measured cases (C); the banner prefers the prediction over the under-reporting
ray count, and the annotation is guarded so a readout cannot break the measurement (D).
