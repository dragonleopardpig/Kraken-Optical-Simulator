# 0615 — "Swap camera work, but the camera is flipped" (FIXED)

Flag `flag_20260812_131816_718`, build `bb222675`: after the 0614 seat fix the swapped
camera lands in the right PLACE but renders backwards. The user asked: flip option or
import-level fix — and "All ray tracing correct?"

## Is the tracing correct? YES.

The trace runs on the layout rows and the REGISTERED sensor (dims from the camera
database); the STEP body is a display decoration. The flag state's termination census
(287/160/6/105 over 558 paths) is identical to the pre-swap states — the flip changes
zero rays. (The only body→trace coupling is a bugs/0379 clear-aperture ray stop, which
this camera does not carry.)

## Why the body flips

Two composing causes:

1. **Same-file re-import wiped the pose.** The Apo75 scene carried baked
   `camera_step_rotation_x=180 / z=90` — the user's hand-applied correction for the
   hr25MCX STEP's axis convention. `import_camera_step` zeroed every rotation on ANY
   import, so re-importing the same camera rendered it backwards.
2. **A different vendor's STEP is a different convention.** The bugs/0308 mount-end
   heuristic (bore-fraction detect, default "max") is a guess, and per the bugs/0373
   lens lesson a mechanical STEP simply does not encode optical direction — no
   import-level rule can always be right for a NEW body.

## Fix (both levels, per the user's question)

- **Import level:** a SAME-FILE re-import preserves rotations + the direction flip
  (the pose encodes that vendor's convention — a no-op principle); a different file
  still resets, as its convention is unknown.
- **One-click flip:** `camera_step_reverse_direction` — persisted with the layout,
  mirrors `lens_step_reverse_direction` (bugs/0373) — seats the OPPOSITE native end
  toward the beam, overriding the 0308 heuristic. Offered as "Flip Camera Direction
  (front/rear)" on the camera's right-click menu (shared branch: 3D canvas + Scene
  Components tree). Display-only, no retrace; in the mesh cache signature.

Guards: phase 464's B legs assert the same-file pose no-op (rotations + flip
preserved); phase 333 asserts the flip entry + its routing.
