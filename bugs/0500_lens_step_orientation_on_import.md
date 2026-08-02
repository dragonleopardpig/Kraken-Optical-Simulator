# 0500 — get the lens STEP's front/rear orientation right at import

User requirement, 2026-08-01:

> when importing a lens and glued automatically, please note that there was cases where the lens
> STEP was flipped after import. So improve the algorithm to make the lens in correct orientation
> the first time. Worst case if it is flipped, user are forced to unglue it and manually flip it.
> But in this case make sure the front and rear surrogate lens correctly attach to the lens STEP
> front and rear lens location.

Two deliverables, in priority order:

1. **Get it right the first time.** The folder import should land the barrel the correct way round.
2. **Make the manual recovery sound.** If it is still flipped, unglue → flip must leave the
   surrogate's FRONT datum on the STEP's front optical location and the REAR datum on its rear —
   not merely mirror the body.

## What already exists

* `lens_step_reverse_direction` — a persisted flip flag (bugs/0373), described as *"mechanical STEPs
  carry no optical direction, re-pinning the opposite barrel end at the front datum"*. So the flip
  is already representable and already survives save/reload; the gap is choosing it correctly.
* `improve_lens_surrogate_rear_to_step` glues the REAR datum onto the STEP's rear face, computing
  the rear face as *"the axial extreme farther from the (front-pinned) front datum"*. That
  definition is orientation-dependent: flip the body and it silently picks the other end.
* `_surrogate_span_from_assets` (`machine_vision_folder_import.py`) already reads the STEP body's
  axial extent to size the surrogate, so the importer is holding the CAD geometry at exactly the
  moment the orientation decision has to be made.
* bugs/0497 added `step_glue_reference_offset_xyz`, the recorded placement. A flip has to update it,
  or "glue to surrogate" will restore the pre-flip pose.

## The signature to exploit

Measured on the AZ85 scene while correctly oriented (bugs/0497):

```
STEP body   x[67.81, 127.00]      datums  front 71.66   rear 126.66
front overhang 3.85 mm            rear overhang 0.34 mm
```

The barrel is **markedly asymmetric** about its own optical span — 3.85 mm of mechanics ahead of
the front vertex, 0.34 mm behind the rear. A flipped import inverts that signature (0.34 front /
3.85 rear), which makes orientation *detectable from geometry the importer already has*, without
needing the vendor to declare a direction.

The surrogate side carries the matching asymmetry independently: a two-group surrogate solved from
the vendor cardinals has front and rear principal-plane offsets that are generally unequal. Matching
the CAD's mechanical asymmetry against the surrogate's optical asymmetry gives a direction cue that
does not depend on STEP metadata at all.

Worth checking first, though, whether the vendor folders carry an explicit cue (a datum/flange face,
a thread, a named face) — a declared direction beats an inferred one, and the inference above should
be the fallback rather than the primary rule.

## Guard it will need

* import a folder whose CAD is known-flipped and assert the barrel lands the right way round;
* assert the front datum sits at the STEP's front optical location and the rear datum at its rear —
  the overhangs in the expected order, not merely a correct total span;
* flip manually and assert the datums re-attach to the correct ends, and that the bugs/0497 glue
  reference is updated so a later "glue to surrogate" restores the FLIPPED pose;
* assert an already-correct import is untouched.

## Not started

Recorded from the user's description. No reproduction yet — the flip was reported as intermittent
("there was cases"), so the first job is to find a folder that reproduces it and capture what
distinguishes it from one that imports correctly.

## Deliverable 2 SHIPPED (2026-08-01) — the manual flip now attaches the optics

Measured on the AZ85 scene before the fix: flipping left the mechanical slab in place
(bounds identical) and slid the GLASS inside it — the optical surfaces landed **3.507 mm off
the datums** (leading glass vertex at 90.19 vs front datum 93.70). Two stacked causes:

* the bugs/0374 glass-centre pin only ran on an UNTILTED close barrel — and a lens on a folded
  arm always carries a y-rotation, so the folded case always took the plain body-face pin, which
  re-pins the OPPOSITE mechanical end on a flip;
* the x/y rotations pivot about the bbox centre, re-registering the slab and silently discarding
  any pre-rotation axial correction (a mirrored slab has the same bbox — which is also why the
  defect was invisible to bounds-based checks).

Fix: `_lens_step_flip_axial_shift()` = `(body_hi − glass_centre) − (glass_centre − body_lo)`
from the native glass metrics, applied in `_cad_mesh_aligned_to_optical_axis` AFTER the
rotations, along the rotated barrel axis (composing x-rot, y-rot, roll onto +z). The flip then
mirrors the body about its GLASS-SPAN CENTRE — the mechanical ends swap around the fixed optics.
The pin (`_lens_step_display_front_z`) is now face-independent (always the unflipped
registration), so nothing changes for an unflipped barrel and every recorded placement offset
stays valid; consequently the bugs/0497/0503 glue reference survives a flip unchanged (glue is a
no-op across flip, no re-record needed — resolving the "flip has to update the reference" note
above by construction).

Verified: overhangs swap exactly (3.849/0.342 → 0.342/3.849) about the unmoved datums on the
folded AZ85; flip-back restores bit-exact; offscreen renders show the barrel mirrored (mount
flange and front bell swap ends) with the glass staying on the datum discs.

Guard: `validate_open3d_0500_flip_attaches_optics.py`, penta phase 407.

**Deliverable 1 (right the first time) remains open** — needs a vendor folder that reproduces
the flipped import; the overhang-asymmetry signature above is the planned detection cue.
