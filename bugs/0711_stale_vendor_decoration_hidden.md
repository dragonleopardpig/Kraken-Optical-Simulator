# 0711 — "the prism now shows duplicated RA mirrors, and other nonsense"

(flag_20260903_160711)

## Root cause

Two representations of the same hardware: the TRACED optical-solid rows
(bare wedges/cubes — these slide on a device resize, 0708-0710) and the
DECORATIVE vendor-assembly STEP overlay (`optical` label) — one rigid CAD
of the ORIGINAL 50 mm design, mirrors, brackets and all. After a re-seat
the decoration still draws every mirror at the old positions: duplicated
RA mirrors and "other nonsense" (stale brackets, LED housings).

## Fix

A monolith cannot be resized. After a successful re-seat,
`_retarget_split_field_to_part` HIDES the `optical` decoration overlay
(`set_step_label_hidden`, survives refreshes) and says so in the status:
"vendor assembly CAD hidden (it models the original device depth) — unhide
it from the Scene Components browser if wanted". The traced solids ARE the
new geometry (display follows physics); the browser can unhide the CAD any
time (e.g. after resizing back to the original depth).

## Guard

`validate_open3d_0704_device_resize_follow` (phase 513) gains A5: the
re-seat hides the optical decoration and narrates it — 11 checks green.
