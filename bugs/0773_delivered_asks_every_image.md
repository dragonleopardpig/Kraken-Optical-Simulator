# 0773 -- "already delivered" must ask every image; and the 21 mm arm asymmetry

Three flags on `35c49ea1`, all `om05a_folded_80mm`:

| device | user | measured (per arm) |
|---|---|---|
| 23 x 23 x 1 | "seems correct" | A -0.0807, B -0.0847 mm; spots 2.10 / 2.06 um |
| 22 x 22 x 1 | "seems correct... check everything else" | A -0.0872, B -0.0917 mm; spots 2.22 / 2.18 um |
| 21 x 21 x 1 | "hay wired rays... why the symmetry not hold?" | **A -3.0251, B -0.0995 mm; spots 425.65 / 2.30 um** |

23 and 22 are confirmed numerically, not just visually: the two arms agree to 0.004 mm and both
spots sit inside the 4.5 um pixel.

## The gate defect (fixed)

The 21 mm banner read:

```
SOLVE: ... the lens did not move -- the field was already delivered
  Face A field: 3.025   mm in front of the sensor
  Face B field: 0.09958 mm in front of the sensor
```

bugs/0752 split the focus measurement per formed image precisely so one arm could not speak for
the other. `_fov_already_delivered` never asked -- it read the TOP-LEVEL `offset_mm`, which here
carried face B's **0.09958**, a hair under the 0.1 mm tolerance. So the field was declared
delivered while face A sat 3 mm out with a 419 um spot. Whichever image is worst now decides,
the same rule bugs/0764's snap guard states.

**Honest scope:** this is demonstrated at unit level in the guard. It was NOT reproducible as a
whole-scene failure -- headless, the 21 mm solve runs rather than being gated, both before and
after the change. The fix is justified by the contract, not by a scene repro.

## The asymmetry (diagnosed, NOT fixed)

It survives the gate fix, so the gate was not its cause. Measured:

```
652 landing rays: face A launches 326, face B launches 326    <- launches exactly symmetric
bucket 'Face A field': 322 rays, waist 419.0 um
bucket 'Face B field': 299 rays, waist   0.42 um
```

The launches are symmetric to the ray, so this is not a bucketing or launch artifact
(the bugs/0757 failure mode is ruled out): arm A's cone genuinely fails to converge.

The one number that tracks it is how close the lens has been driven to the prism exit:

```
device 23 -> gap row 8 = 10.265 mm    both arms land
device 22 -> gap row 8 =  6.010 mm    both arms land
device 21 -> gap row 8 =  1.755 mm    arm A waists at 419 um
```

So the working hypothesis is an edge-of-machine effect -- with 1.755 mm of clearance one arm's
beam degrades first -- and the 14-20 mm band that refuses outright (bugs/0771) sits just beyond
it. That is a hypothesis with evidence, not a proven cause, and no fix is claimed.

## Guard

`KrakenOS/UI/validate_open3d_0773_delivered_asks_every_image.py`, penta phase **557**: the flag's
own numbers show the top-level offset inside tolerance while the worst image is not (A); a state
where both arms land is still delivered, so the gate is not merely disabled (B); single-image
scenes still read the top-level number (C); malformed image lists fall back rather than raise (D).
