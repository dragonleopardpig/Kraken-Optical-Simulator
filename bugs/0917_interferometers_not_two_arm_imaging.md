# 0917 -- the interferometers were being traced as two-arm IMAGING scenes (a real regression)

Found by the ungated sweep: `validate_phase6_path_workbench` ("No depth>=2 traced BRANCH_PATH")
and `validate_gaussian_branch_frames` ("interaction_frames=0") both failed on the Michelson
Interferometer example.

## Measured

The Michelson traced TWO ray paths, `twoarm/transmit` and `twoarm/reflect`, with no beam-splitter
events at all: just `aperture` x16, `image` x4 and `transmission` x2. The two-arm display fold
(bugs/0100, 6732892e, 2026-06-19) had taken it over. That fold traces each arm straight and
sequentially and bends one arm for display. It is right for a splitter feeding two IMAGING arms,
each with its own lens and camera. It cannot represent an interferometer, whose light returns
through the splitter and recombines; the North Star says a beam splitter is non-sequential.

## Root cause

`_imaging_branch_leaves` called an arm "imaging" when its leaf held any Aperture row. The
interferometer arms carry clear-aperture clips, and the Michelson has three apertures BEFORE the
split, which the old check counted too.

A scan of all 171 layouts in `attachment/` and the built-in library found four scenes the fold
took. The arms after the split:

| Scene | Arm contents after the split |
|---|---|
| `beam_splitter_dual_mv_150_120` | Thin Lens, Aperture, Thin Lens (two cameras) |
| Mach-Zehnder | Mirror, Aperture |
| Michelson | Aperture x4, Mirror |
| Twyman-Green | Aperture x2, Mirror |

"Has its own Image row" would have dropped the dual-camera scene too: its image is the global
one. The real difference is refracting optics.

## Fix

An imaging arm has an Aperture in its leaf (as before) AND a refracting surface (`Standard`,
`Thin Lens`) among its OWN rows after the split. Rescanning all 171 layouts: only
`beam_splitter_dual_mv_150_120` folds, and the three interferometers trace non-sequentially again.

## Verified

- `phase6_path_workbench`, `gaussian_branch_frames` and `phase6_complete` pass.
- 26 gated branch/two-arm phases (om05a's 505 included) pass.

## Also in this batch (stale checks)

- **`validate_attachment_paths`.** It required a datasheet for every camera. CAM-SV25MCCXP
  (bugs/0691) declares none and carries its specs inline. The rule is now: every DECLARED file
  resolves, and a camera without a datasheet carries its specs itself.
- **`validate_optical_solid_face_roles`.** The hover-clear moved into `open3d_inspector` in the
  05-26 extraction. The check now runs the REAL editor hook and the REAL inspector method on a
  stub holding stale state, and requires it all cleared.
