# 0751 -- the focus plane follows the LIGHT, not the sensor centre (reverting 0747)

Flag `20260908_102928_871`: "30mm device size cannot be acheived. The Image Plane is still shifted
side way from the center." Third report of the same thing, and the third one was right about
something I had made worse.

## What bugs/0747 did, and why it was wrong

bugs/0742 anchored the drawn focus plane on the ray landing nearest the beam centroid, instead of
on the winning field's off-axis bundle. Good. bugs/0747 then went further and TRANSLATED that ray's
polyline so it landed exactly on the sensor centre, to make the rectangle look centred.

Measured on the same traced bundle, 30 mm device, offset -54.898 mm:

| anchoring | distance to the traced beam | lateral from the sensor centre |
|---|---|---|
| **0747 as shipped** (translate onto the sensor centre) | **7.4934 mm** | 0.7005 mm |
| **no translation** (walk the ray where it is) | **0.0000 mm** | 7.5251 mm |

The translation did not remove a 7.5 mm error, it MOVED one: off the sensor axis, onto the light,
and back again. Drawing the rectangle centred hid the shift behind a display-only nudge instead of
fixing it, which is exactly what
[[feedback_display_follows_physics]] forbids ("draw from the same transform the trace uses; never a
display-only nudge") and what bugs/0728 established ("a missed ray must visibly MISS").

## Fix

The translation is removed. bugs/0742's axial-ray choice stays -- the plane is still anchored on the
ray nearest the beam centroid rather than on one field's bundle -- so the plane now sits **0.0000 mm
from the traced beam**.

Verified: penta 527, 528, 532, 538, 540, 541 all pass.

## CORRECTED by bugs/0752 -- the 7.5 mm was NOT real

This section originally read: "the sideways offset it draws is information, not an artefact -- at a
30 mm device the image forms about 7.5 mm off the sensor centre. The overlay is reporting a real
property of the configuration."

That was wrong, and the user caught it: *"everything is symmetry, A and B sides, I can't figure out
how to make an Image Plane off-centered."* They were right. Measured, the two arms land at
v = +5.3474 and v = -5.3474 mm, summing to -0.00000 mm -- the optics is exactly symmetric.

The 7.5 mm came from anchoring on a centre POOLED over both arms, which on a split field falls in
the dark ridge between the two strips where no ray lands (nearest ray 4.5059 mm away). See
bugs/0752. The revert in this document stands; only its interpretation of the residual was wrong.

The remaining ~54 mm of apparent displacement is the FOLD: the waist is 54.9 mm back along the beam
and the last straight leg into the sensor is shorter than that, so it genuinely sits up the
incoming leg. That is bugs/0729's behaviour, which the user asked for ("I think it skip the fold.
It should be located somewhere near the Filter"). Whether a waist landing BEYOND a fold would read
better drawn unfolded on the sensor's own axis, with a note, is still an open presentation question
-- but it must be answered as a presentation choice, not by nudging the geometry.

## Process note

Three changes to this one overlay in one session (0742, 0747, 0751), two of which I made without
being able to measure the thing the user was actually pointing at. The measurement that settled it
-- "distance from the plane centre to the traced polyline" -- took one probe and should have been
the FIRST thing computed, not the third.
