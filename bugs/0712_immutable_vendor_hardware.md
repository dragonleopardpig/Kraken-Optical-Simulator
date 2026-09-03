# 0712 — USER DIRECTIVE: the vendor hardware is immutable

User (2026-09-03, after the 0708-0711 slide arc): "the vendor provided STEP
file should remain constant, no modification (including sliding of element)
is allowed. The only change is the device itself. Everything should remain
where they are."

This supersedes the slide mechanism entirely (0708 far-tower slide, 0709
centre-V plane ride, 0710 leg-fold ride, 0711 decoration hide).

## New contract (`_retarget_split_field_to_part` v4)

On a device resize:
- the device box stays CENTRED in the fixed gap (faces at the hardware
  symmetry plane +/- depth/2), via `axis_offset_mm` only;
- both green bands attach to the device faces;
- the faceB launch MARKER follows the far face; `mirror_launch_plane_z` is
  the hardware's fixed symmetry plane and is NEVER rewritten;
- NO row, solid, overlay or decoration moves or hides — the vendor CAD stays
  visible and correct (`_slide_far_tower_rows` and its three stamped classes
  are DELETED);
- the status states the consequence: the as-built optics still image their
  original object planes — refocus / solve FOV / select a lens to focus on
  the new faces (the user's stated workflow: size -> FOV -> lens selection).

## Guard

`validate_open3d_0704_device_resize_follow` (penta phase 513) rewritten:
A1 faces centred in the fixed gap, A2 mirror plane fixed, A3 offset-only
re-centre, A4 EVERY row byte-identical + no overlay hidden, A5 second
resize stable about the fixed plane, B/C hands-off, D FOV band widths —
8 checks green. Live: 12/12 om05a solids byte-identical through a 15x15x1
resize.
