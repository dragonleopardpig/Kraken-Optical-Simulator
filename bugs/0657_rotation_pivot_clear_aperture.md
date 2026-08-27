# 0657 — Body rotations pivoted on the port-skewed centroid, not the clear aperture

**flag_20260827_145650:** "I flipped the lens, then I rotated the lens to orientate
the in-line illumination port, but now it is off axis." Follow-up, the user's own
diagnosis: "I rotate around the optical axis, I think the algorithm not taking the
clear aperture lens as the center of rotation, it also take into account the
illumination port, that is the reason it displaced from the optical axis."

**The user was right, to the millimetre.** `rotate_step_world_axis` implemented
"rotate in place" by holding `mesh.center` fixed (`offset += center_before −
center_after`). The #67-319 In-Line telecentric's illumination port drags that
centroid 5.35 mm off the clear-aperture barrel; a 270° roll about it therefore swung
the barrel 5.35·√2 = **7.566 mm** off the optical axis — exactly the
`placement_offset (−5.35, +5.35)` found stored in the flagged scene. Measured
control: with the stored offset zeroed, the ALIGNMENT itself is perfectly
roll-invariant (0.000 mm at 0°/90°/270° — the bugs/0077 CAD-cylinder centring), so
the entire displacement was the rotation gesture's own compensation.

## Fix (general)

- `_step_rotation_pivot_world(label)` — the in-place pivot is a point ON the CAD
  barrel axis for the lens (`_lens_step_overlay_axis_world_line`, the same
  clear-aperture anchor the alignment centres on); the centroid remains only for
  axis-less bodies (LED slabs, BS cubes — where it IS the right pivot).
- Right-click lens body → **"Re-centre Body on Optical Axis (transverse)"** — the
  bugs/0568 recentring as a one-click repair for any stale transverse offset
  (this scene's ±5.35, or old drags). Purely transverse; axial registration kept.

## Verified

On the user's own flagged scene: the repair verb takes 7.566 → 0.000 mm; the
sequence z+90, z−45, x+10, x−10, z+315 leaves the barrel at 0.0000 mm off-axis
(the centroid pivot displaced it 7.57 mm on the FIRST roll). Guard
`validate_open3d_0657_rotation_pivot_clear_aperture` (penta phase 493).

**User action for the flagged scene:** right-click the lens body → "Re-centre Body
on Optical Axis (transverse)" once, then save. Rotations after the fix stay on-axis.
