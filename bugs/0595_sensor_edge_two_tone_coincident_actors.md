# 0595 — the sensor square's edge renders in two colours (coincident actors) (OPEN)

Flag `flag_20260809_100904_100`: *"I turn on Illumination overlays as well as other analysis, none
of them works. **Also note the sensor square edge is now split to 2 colors.**"*

The first half is **bugs/0593** (the field-aberration scan cannot run on a folded scene) — same
scene `machine_vision_Apo75.py`, same three overlays. This bug is the second half.

## Diagnosed from the recordings

Two actors draw the *same* detector square, at nearly the same plane. From `row_actor_bounds` in
both recent recordings:

| recording | actor | bounds (x, y, z) |
|---|---|---|
| `flag_20260809_100904_100` | row `8` | 233.279 … 265.862, ±16.292, **−5.058 … −5.041** |
| | row `100000` | 233.279 … 265.862, ±16.292, **−5.049 … −5.049** |
| `flag_20260809_102408_191` | row `8` | 285.795 … 318.378, ±16.292, **49.699 … 49.723** |
| | row `100000` | 285.795 … 318.378, ±16.292, **49.711 … 49.711** |

The x and y extents are **identical to the micron**; only z differs. The pseudo-row `100000` actor
is perfectly flat, while the real row-8 actor spans ~0.017–0.024 mm in z — a tilt of roughly
0.02 mm over the 32.6 mm width, i.e. about **0.04°** — and the flat actor sits at its mid-plane.

Two nearly-coplanar, nearly-coincident surfaces crossing each other at ~0.04° is textbook
**z-fighting**: along the rim, whichever actor is nearer alternates, so the edge renders as two
interleaved colours. It appears on both scenes, so it is not scene-specific.

## What to establish before fixing

1. **Who owns pseudo-row `100000`?** It is not a surface row; find what registers it (a detector
   overlay, the reached-image plane, or the pixel grid) and whether it is meant to coexist with the
   row-8 actor at all. If both are wanted, the overlay needs a depth offset / polygon offset rather
   than sharing the plane.
2. **Why is row 8 tilted by ~0.04°?** A detector that is supposed to be normal to its folded leg
   should be flat in its own frame. A small residual tilt is worth understanding on its own — it may
   be the same measured-in-station/placed-in-world residue as bugs/0576, at small amplitude, in
   which case the two-tone edge is a *symptom* of a placement error and suppressing the z-fight
   would hide it.

Do not fix this by nudging one actor: per `feedback_display_follows_physics`, if the tilt is real
the fix is in the placement, and if the duplicate is redundant the fix is to stop drawing it.

## Guard

An image-snapshot test (`feedback_image_snapshot_tests`) is the right guard — the defect is
visible and a property assertion on either actor alone would pass. Assert that the detector rim
renders a single colour, and separately that no two scene actors share x/y bounds to within a
micron while sitting within ~0.05 mm in z.
