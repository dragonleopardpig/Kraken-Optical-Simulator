# 0775 -- measure the delivered magnification from the rays, and check the claim

While chasing the 21 mm asymmetry the banner said *"delivering 22.05 x 22.05 mm (|m| 1.045)"* and
nothing in the app could contradict it: every readout that might have came from the same first
order that produced the claim. bugs/0774's LAW 2 reads backwards into an independent measurement:

```
LAW 2   |v|half = device * |m| / 2      ->      |m| = 2 * |v|half / device
```

The strip's imaged LENGTH over the device that produced it. Scene-independent -- unlike the strip
POSITION, whose coefficient (9.278 on om05a) is a property of that bench's arm offset and would be
a hardcoded scene constant in the simulator.

## Measured

| case | traced \|m\| | claimed \|m\| | apart |
|---|---|---|---|
| device 21, default FOV | 1.04519 | 1.04490 | 0.03% |
| device 30, FOV 34 | 0.67778 | 0.67765 | 0.02% |
| device 23, default FOV | 0.95431 | 0.95404 | 0.03% |

Quiet where it should be, against a 2% threshold. When it does fire it names both numbers and
which to believe:

> DELIVERED FIELD DISAGREES WITH THE CLAIM: the rays measure |m| 1.124 where the solve reports
> 1.045 (7.6% apart) -- trust the rays

Skipped entirely when the strip is CLIPPED: a clipped strip under-reports its own length, so the
measurement would lie in exactly the case bugs/0774's overflow warning already covers.

## What it settled

A claim made during the 21 mm investigation and withdrawn: that the solve was delivering |m|
1.1243 while reporting 1.0449. That number was back-solved from the strip POSITION on a blurred
strip. By LAW 2 the 21 mm strips measure 1.0452 against 1.0449 claimed -- **correctly magnified**.

So the 21 mm strips are the right SIZE in the wrong PLACE: a pointing error, not a magnification
error. That is a positive statement about the bug, where the previous five findings were all
eliminations (edge-of-machine, stray rays, lens jammed, lens-move capped, field off the sensor).

## Not done

The POSITION half. Asserting it needs `k` in `|u|outer = k * |m|`, and k is a per-bench constant.
Deriving it per scene would mean calibrating from a reference trace at load and asserting against
that thereafter -- real design, real risk of baking in a bad reference, and not something to build
on an assumption.

## Guard

`KrakenOS/UI/validate_open3d_0775_traced_magnification_checks_the_claim.py`, penta phase **559**:
a real disagreement is reported with both numbers and which to trust (A); the three measured cases
stay quiet, and the 2% threshold is bracketed rather than sat on -- 1.02-1.0 is
0.020000000000000018 in binary, so an at-the-line assertion tests the FPU and not the rule (B);
a clipped strip records no traced |m| at all (C); the arithmetic is LAW 2 inverted, and the
scene-specific position coefficient is not baked in (D).
