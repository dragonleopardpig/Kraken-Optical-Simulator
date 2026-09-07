# 0733 — "image location tilted": the focus plane must be square to the AXIS, not to a ray

Flag `flag_20260907_102153_232` ("image location tilted"), build ce8c82d3, unfolded top view of
`om05a_folded_80mm.py`.

## What was wrong

bugs/0729 put the focused-image plane in the right PLACE (walked back along the traced path) but
oriented it by the winning field's local ray direction. In this design the beams enter the lens
**off-axis by design** (±8.8 mm through the inverted prism), so no chief ray is parallel to the
lens axis — the drawn plane came out **3.6° tilted** against a sensor that is square to the axis.

Two wrong turns on the way to the fix, both measured and discarded:

| attempt | result |
|---|---|
| average the local direction over all contributing fields | tilt 3.6° → **1.0°** — better, but it mixes the two arms |
| use the "axial" field's chief ray (launch nearest the object centre) | tilt **4.3°** — worse: when the whole beam rides off-axis, the axial FIELD's chief ray is not the axis either |

## The fix

The axis is not any ray. It is the **sensor normal transported back through the same folds the
ray took**. Inside `focus_point_along_paths`, while walking back:

* at a turn greater than 30° the ray reflected about `m = normalise(d_before − d_after)` — which
  is exactly parallel to the real mirror normal for any incidence — so the running axis is
  reflected about that same `m`;
* a smaller turn is a refraction and does not re-orient the leg;
* with no fold at all the sensor normal is returned unchanged.

Measured on om05a: the plane normal is now **(1.0, −2.9e-8, 2.1e-8) — 0.000° from the lens axis**,
with the placement unchanged at (248.64, 52.80, −14.88), still at the Filter.

The editor needed no change: `focus_point_along_paths` already supplies the plane normal, so it
now supplies the axis instead of a ray direction.

## Guard

`validate_open3d_0733_focus_plane_square_to_the_axis` = penta phase 532: A a 90° fold transports
the sensor normal onto the leg axis exactly and the placement is unchanged; B an off-axis ray on
the SAME physical mirror yields the same plane normal (the ray runs 2.97° off the axis, the plane
does not); C an unfolded path keeps the sensor normal; D a refraction-sized turn does not
re-orient it.

Note for future work on this file: a synthetic reflection test must reflect about a real mirror
normal (`d_after = d − 2(d·m)m`). An arbitrary "incoming tilted, outgoing exactly −y" pair is not
a reflection any mirror can produce, and it fails the guard for the wrong reason.
