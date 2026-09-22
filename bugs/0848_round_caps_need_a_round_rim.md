# 0848 -- synthetic round end-caps only for a body that is round

The other half of the yellow ghost outline, and the one seen first (day 1 of this run): hovering
om05a's housing drew a flat **75 x 156 mm** plane through it, labelled
`OPTICAL STEP outer +axis face face`. bugs/0847 fixed the variant on real STEP faces; this one
is not a STEP face at all.

## Mechanism

`open3d_round_lens_pick` exists for thin transparent vendor achromats: it synthesises two
end-caps ("outer +axis face" / "outer -axis face") from the body's point cloud, radius = the 97th
percentile of radial distance, hit-tested with 12% of that radius as slack. It runs for any body
tagged `_kraken_round_lens_like_step_body`, and the tag comes from `_mesh_round_lens_axis` -- a
**second-moment** test (two similar spreads, one thin one, thickness/diameter <= 0.85). A box
passes it. Nothing asks whether the rim is ROUND.

Measured across eight scenes -- om05a, Apo75, Pyrite85, ELS85, 150mm_GN, Pyrite45, Basler
telecentric, 35mm -- every body the test tagged was a false positive, and no real vendor lens
barrel was tagged at all (they are long barrels):

| body | rim radius variation with azimuth |
|---|---|
| om05a prism assembly (`optical`) | 52 % |
| Pyrite45 scene's **camera** | 58 % |
| Basler telecentric lens barrel | 98 % |
| a disc / turned lens | tessellation noise (0 % for an exact circle) |
| a square rim | 29 % |

## Fix

`rim_radius_variation(points, center, axis)`: the outermost radius per azimuth bin (36 bins),
`(max - min) / max`; None when fewer than 3/4 of the bins are populated. The synthetic caps are
made only when it is <= **0.2** -- a square is 0.29, the false positives 0.52-0.98.

The TAG itself is left alone: it also suppresses dense triangle edges on selection (bugs/0003),
and changing it would change how a selected prism assembly or camera draws. Only the claim
"this body has round end-caps" now requires a round body.

And the label: four hover lines built `f" {face_id} face"`, so a cap named "outer +axis face"
read "face face". `_face_note_text` does not repeat the noun. (The helper is private and named
apart from the `face_note` locals three of those functions already use -- a module-level
`face_note` would have been shadowed, and in one function called as a string.)

## Guard

`validate_open3d_0848_round_caps_need_a_round_rim.py`, display-free, penta phase 627. Drives the
REAL `round_lens_feature_for_display_xy` through a minimal fake inspector (a ray, one tagged
actor, the real geometry statics).

- **B1** CONTROL: a 100 x 80 x 30 box passes the round-lens test and, with the rim gate
  neutralised, the real pick synthesises "outer +axis face" for it; **B2** with the gate, none
- **C** a round cylinder still gets its synthetic cap
- **M** the metric: circle 0.000, square 0.282, a 5-point cloud not judged
- **R** the real prism assembly: still tagged by the second-moment test, rim varies 52%, no cap
  (SKIP if not checked out)
- **L** "outer +axis face" is not followed by another "face"; a real face id still is

`validate_open3d_lens_step_face_pick` keeps exactly its two pre-existing failures (identical on
the unpatched code); the other round-lens / hover guards pass.
