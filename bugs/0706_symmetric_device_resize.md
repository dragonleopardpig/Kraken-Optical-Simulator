# 0706 — symmetric device resize (flag_20260903_125205)

Flag: "Resize device to 15x15x1mm, the device shrink on one side, can you
make the device to shrink symmetrically so that the device is always at the
middle of the big gap of the two top RA mirrors?"

The 0704 retarget anchored face A on the object plane, so a resize kept face
A fixed and pulled everything toward one side. The user's anchor is the GAP
CENTRE between the two towers.

## Fix (`_retarget_split_field_to_part` rewritten symmetric)

- The anchor is the authored `mirror_launch_plane_z` — the towers' midplane
  IS the gap centre, and it stays INVARIANT under a symmetric resize. That
  also keeps the mirrored faceB launch exact at every device size: a launch
  plane at centre+d/2 mirrors onto centre−d/2 by construction.
- On resize: near band -> centre + depth/2, far band -> centre − depth/2,
  faceB launch plane -> the far face, aperture -> the new face size, and the
  drawn part box re-centres via `axis_offset_mm` (its active face is pinned
  at object_point + offset).
- Bands not sitting at centre ± old_depth/2 are left byte-identical.
- A second resize stays centred (guard A4) — the scheme is stable.

om05a 50→15: faces at −17.5 / −32.5, mirror plane −25 (unchanged), part
offset −17.5. Live-verified + rendered (`bugs/0706_symmetric_resize.png`):
both bands with their FOV labels sit symmetric about the centre V, in the
middle of the big gap.

Note (unchanged 0704 contract): hardware is never auto-moved, and the object
ROW still launches from its authored plane until the user re-solves — with a
15 mm device neither face sits on the towers' as-built object planes; the
trace shows that honestly, and lens distance/selection is the user's next
design step (their own stated workflow).

## Guard

`validate_open3d_0704_device_resize_follow` re-pinned symmetric (A1 faces
about −25, A2 mirror-plane invariance, A3 part-offset re-centre, A4 second
resize stable, B/C hands-off, D FOV band widths) — penta phase 513.
