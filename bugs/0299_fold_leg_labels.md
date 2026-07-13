# 0299 — "the last distance is not 50mm as stated in the constraint"

User flag `flag_20260713_213400_546`: *"I constraint first and last distance to 50mm, FOV set to
54x54mm. Every thickness correct?"* — followed by *"one thing to note, the last distance is not 50mm
as stated in the constraint."*

## What actually happened

The optics were **correct**. Replaying the flagged action produces the flagged state to 4 decimals:

| | flag (the app) | replay |
|---|---|---|
| S7 lens rear → mirror 2 | 50.0001 | 50.0000 |
| S8 mirror 2 → sensor | 43.1167 | 43.1167 |
| mirror 1 → lens front | 206.0688 | 206.0687 |
| \|m\| | — | 0.426667 = 23.04/54 → FOV exactly 54×54 |
| focus | — | traced on-axis spot RMS 0.000008 mm |

The app pinned the **lens rear → mirror** leg to 50, not **mirror → sensor**. That is exactly what
`image_segment = ("near", 50)` produces, and it is *not* what `("far", 50)` produces:

```
tick "mirror → sensor = 50"        ->  S7 = 43.1167,  S8 = 50.0000    (what the user wanted)
tick "last surface → mirror = 50"  ->  S7 = 50.0000,  S8 = 43.1167    (what the app produced)
```

The plumbing is sound end-to-end — the checkbox → `("near"|"far", value)` getter, the
`segment` / `image_segment` params, and `_apply_folded_image_split` all agree, and pinning `far`
demonstrably lands the leg exactly (`far=30` → 30.000000). So the app honoured the box that was
ticked.

## Root cause: the label invited the mistake

The image-side group was labelled:

```
[ ] Constrain last surface → mirror distance (mm):     <- the SECOND-TO-LAST leg
[ ] Constrain mirror → sensor distance (mm):           <- the LAST leg
```

A user pinning "the last distance" reads the word **last** on the *first* checkbox and ticks it.
The word "last" was sitting on the wrong leg. (Symmetrically, the object group put "first" in
"mirror → first surface", which is the *second* leg.)

## Fix

Name each leg by **where it sits in the folded beam**, and let "first"/"last" appear only on the
legs that really are first and last:

| | before | after |
|---|---|---|
| object near | Constrain object → mirror distance | Constrain object → mirror distance — **first leg** |
| object far | Constrain mirror → **first surface** distance | Constrain mirror → **lens front** distance |
| image near | Constrain **last surface** → mirror distance | Constrain **lens rear** → mirror distance |
| image far | Constrain mirror → sensor distance | Constrain mirror → sensor distance — **last leg** |

The solve's status message follows suit (`Image distance split: lens rear->mirror … , mirror->sensor …`),
so the readback names the same legs as the dialog.

No physics changed. `validate_open3d_folded_image_segment_split` pins the new near-leg label.
