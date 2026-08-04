# 0533 (OPEN) — the split's reflected child never re-crosses its own solid

## Evidence

`diag_0531b_plate_ghost_geometry.py`: the plate-BS ghost (`S3/transmit -> S3/reflect`)
reflects at the BACK face — geometrically correct, verified against the shared 45° normal
— and then terminates `no_next_intersection` while sitting 1.2 mm INSIDE the glass. The
front face (same solid, surface id 3, 1.2 mm ahead along the ray) is never intersected,
so the exit refraction is skipped and the ghost flies off 15–17° high with its IN-GLASS
direction. Zoom flag_20260804_084655 shows the rays crossing the drawn plate outline with
no kink.

A real plane-parallel-plate ghost exits through the front face and emerges PARALLEL to
the primary reflected beam (classic laterally-offset plate ghost).

## Suspected mechanism

The split-branch spawn excludes "the surface we just left" to avoid an immediate re-hit —
if that exclusion is keyed on the SOLID/surface id (the whole promoted mesh is S3) rather
than the local face/hit-point epsilon, the child skips its own solid entirely. The RA
prism's internal reflections DO find their exits (event type `reflection`), so the defect
is specific to the split-spawn path.

Violates [[feedback-random-element-ray-trace]] (rays must not vanish) and the user's
overlay-ON truth principle. Fix in the NS loop's split seeding; verify the ghost then
exits parallel with the 0532 corrected power.
