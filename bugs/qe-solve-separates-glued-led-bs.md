# QE "solve for thickness" separated the glued LED+BS (and defocused the detector)

## Symptom (flag_20260628_212404 + recording_20260628_212459 + the YZ flag)
With the LED glued to the promoted BS, changing the FOV + "solve for thickness" moved the BS
(gap-to-solid 199 → 322) while the glued LED stayed at "Object LED = 200" → the LED enclosure and
the BS detached by ~122 mm. The recording's `row_actor_bounds` show the BS front sliding 201.7 →
322 while the LED overlay offset stayed 0; the whole downstream (and the detector) shifted, so the
detector defocused.

## Why (user's intent)
The LED must sit as close to the object as the machine allows (min 200 mm) for uniform
illumination — it is a FIXED constraint and must be EXCLUDED from Quick Estimation. QE should solve
the lens + detector for the FOV/focus, never the LED+BS.

## Root cause
QE's `object_thickness_row()` returns row 0 — the object→BS gap — and `_apply_conjugate_pair`
writes `rows[0] = object_distance`. That gap IS the LED+BS position, so solving moved the unit. The
BS↔LED glue (bugs/0133) is one-directional (LED→BS) and never carries the LED back, so the LED was
left behind.

## Fix
`_object_locked_redirect_row`: when the LED is glued and a promoted solid sits right after the
object gap, return the first air gap AFTER the solid. `_apply_conjugate_pair` then redirects the
object-distance change to THAT gap — moving the LENS by the same delta instead of the object gap.
Geometrically `object→lens += delta` and `lens→detector` is unchanged in BOTH cases, so the
conjugate (focus + FOV) is IDENTICAL, but the LED+BS stays put. If the FOV needs the lens nearer
than the locked unit allows (negative gap), QE refuses with a note rather than separating. Unglued
→ the old behavior.

## Verified (display-free)
MV150, LED glued, FOV solve wanting object_distance=322: rows[0] (LED+BS) UNCHANGED at 202.146, lens
gap rows[2] 17.85 → 137.7, back focal 210; object→lens = 394.854 == the normal solve's 394.854
(identical conjugate). Unglued: rows[0] → 322 (normal). guard `validate_open3d_qe_object_locked`.
