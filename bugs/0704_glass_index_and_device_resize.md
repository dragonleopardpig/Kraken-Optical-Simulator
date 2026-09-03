# 0704 — glass-index validation + device-size option (flag_20260903_110804)

Flag: "Please validate the ray tracing actually takes into account of glass
refractive index. … Please add device size (length, width, thickness) changing
option. The green object plane should attach automatically to new device side
location. Let user to input required FOV as usual. Practical example: a device
size of 15x15x1mm requires about 20mm [FOV]." Follow-up note: "there is a
piece of glass right after the imaging lens."

## 1 — refractive index: VALIDATED first-principles

`validate_open3d_0704_glass_index_in_trace` (penta phase 512) traces a
converging pencil through a 10 mm MESH cube (an STL solid row — exactly how
the om05a prisms trace) twice: row glass AIR vs BK7.

- AIR: focus lands at the aim to 3 decimals (z = 60.000).
- BK7: focus shifts **+3.418 mm**, the plate law t(1−1/n) = +3.407 mm (0.3%,
  the plate law's own small-angle approximation at these ray angles).
- The oblique marginal ray exits laterally displaced 0.23 mm vs AIR — rays
  physically bend at the mesh faces.

The NS mesh trace applies the index. Supporting history: the 0696
phantom-glass forensics observed per-event `medium_change AIR→BK7`
bookkeeping; the 0297 first-order carries the prisms' reduced path t(1−1/n)
(~8.5 mm per fold), which the measured focus agrees with.

## 1b — the glass after the imaging lens

The user's note refers to the `Filter 48-926` row: Standard flat, **glass
N-BK7, thickness 1.0 mm**, followed by an AIR row — a real 1 mm N-BK7 plate
in the trace, refracting under the machinery just validated (its ~0.34 mm
focus contribution is inside the balanced-focus solve).

## 2 — device size option

The size entry point already exists: **Inspection Part dialog** (W/H/D +
part STEP + Apply / Apply+Solve-FOV). What was missing is the split-field
follow-through, now in `set_inspection_part_spec` →
`_retarget_split_field_to_part`:

- the far (face B) green band re-anchors to the new back face (face A stays
  the object-plane anchor);
- the mirrored faceB launch follows: `source_z = −depth`,
  `mirror_launch_plane_z = −depth/2`, aperture = the new face size
  (radius_x = width/2, radius_y = height/2);
- scenes whose bands don't sit on the part's faces — and non-split scenes —
  are left byte-identical;
- **hardware is never auto-moved**: re-seating the B-arm prisms around the
  new face is the user's design decision (the Move verbs), and the trace
  honestly shows any mismatch. For a 15 mm device the B tower must come
  35 mm toward face A before the mirrored launch images again.

FOV "as usual": a successful object-FOV solve
(`QuickEstimationService.fov_solve` → `_update_split_field_band_widths`)
writes the delivered width into BOTH bands, so the green planes draw the
field the user asked for (15×15×1 device + FOV 20 → bands 20 wide on both
faces).

Verified live on `om05a_folded_80mm.py`: 50→15 resize moves the Face B band
to z=−15, faceB launch to z=−15 / mirror plane −7.5 / aperture 7.5×0.5, with
the status line narrating the moves.

## Guards

- `validate_open3d_0704_glass_index_in_trace` = penta **phase 512**.
- `validate_open3d_0704_device_resize_follow` = penta **phase 513** (A1/A2
  follow, B foreign-bands hands-off, C non-split hands-off, D FOV band-width
  follow).
