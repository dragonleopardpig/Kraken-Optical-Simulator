# 0708 — resize launches off the object plane + FOV in the size dialog (flag_20260903_133247)

Flag: "changed device size, click Apply and Solve for this FOV, the ray is no
launching from the Object Plane. I think better to put FOV in the change
device size pop up dialog so that user can input both values."

## Root cause — the 0706 display-offset scheme

0706 centred the DEVICE between the fixed towers by moving both green bands
(face A to z=−17.5) while the imaging launch stayed on the walk origin (z=0)
— a green object plane no ray comes from. The flag is the immediate symptom.

## Fix — face A stays on the launch plane; the FAR TOWER slides (supersedes 0706)

`_retarget_split_field_to_part` v3:

- Face A NEVER leaves the walk origin — that is where the imaging launch
  physically starts.
- The 0706 ask ("device always at the middle of the big gap of the two top RA
  mirrors") is honoured the physical way: `_slide_far_tower_rows` slides the
  FAR TOWER with the far face, so the gap re-centres around the device. That
  is also the correct new station design, and it keeps the mirrored faceB
  launch EXACT (hardware symmetric about the new mirror plane by
  construction).
- Far-train membership: classified ONCE from the pristine symmetric geometry
  (world-placed UNTILTED solid rows on the far side whose z mirrors onto a
  partner's z about the gap centre) and STAMPED
  (`ScenePlacement.far_tower`) — after a big slide a far element can CROSS
  the centre and geometric pairing would misclassify it on the next resize.
  Unpaired far solids and tilted leg folds never move. Stations untouched
  (pure `desp_z += delta`).
- Bands: near at the launch plane, far at −depth; faceB launch on the far
  face; mirror plane at −depth/2.

HONEST LIMIT: the vendor monolith encodes the 50 mm device. After a big
shrink the slid far half of the centre V no longer meets the near half, so
the two arms land on the shared lens leg displaced — the 3D shows it, and
that is the information the user is exploring for ("different device size …
affect lens distance and selection"). Only new prism hardware closes it.

## FOV in the size dialog

The Inspection Part dialog gains "Required FOV (mm, blank = face +5%)";
"Apply + Solve FOV to this face" passes it to
`solve_fov_to_inspection_face(fov=…)` — an explicit FOV is authoritative
(no +5% margin). The 15×15×1 + FOV 20 production case is one dialog visit.

## Guards

`validate_open3d_0704_device_resize_follow` (penta phase 513) re-pinned:
A1 face A anchored / far → −depth, A2 faceB launch + mirror plane, A3a
paired far-tower slide, A3b near/tilted/unpaired never move, A4 second
resize consistent via the stamp, B/C hands-off, D FOV band widths.
