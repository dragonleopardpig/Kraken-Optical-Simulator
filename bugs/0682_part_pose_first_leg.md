# 0682 — device part flipped out of the prism gap (flag_20260901_131224_844)

## Symptom
"The 3D object is still dislocate, not positioned in the center big gap of the
prism." After the 0681 housing fix, the 50x50x1 device box rendered at z 0..+50 —
skewering outer prism A (z 0.1..10.8) and sticking 40 mm out of the assembly,
instead of occupying the device slot between the outer prisms (z -58..0).

## Root cause
`_inspection_part_pose` (open3d_inspector.py) resolved the object->lens SENSE from
the object->IMAGE diagonal. In the folded armA scene the image sits around three
corners at (-272.7, -11, -19.6), so the diagonal carries a NEGATIVE z component;
the sign test then flipped the object-plane normal to -z and `box_corners` extended
the body along +z into the prism. Straight scenes never exposed this (diagonal ~
launch direction).

## Fix (general)
The sense now comes from the FIRST LEG: object -> the first downstream row whose
world reference point is > 1 mm away (outer prism A at (0,0,5.35) here -> +z). The
first leg IS the launch direction in every scene, folded or straight, and needs no
traced rays (fast-load safe). The object-target normal still provides the exact
plane normal; only the +- choice uses the leg. Straight scenes unchanged
(first leg == diagonal direction there); phases 495-500 (inspection-cell family)
re-run green.

## Verified
- Part box now z -50..0, x +-25, y +-0.5: face A ON the object plane, body filling
  the prism gap (z -57.9..0.1).
- Guard: 0672 validator A7 opens the real 3D view and pins the drawn box corners
  (phase 505). Full guard 12/12 PASS.
- Visual: re-render from the flag's camera pose shows the plate inside the housing
  slot.
