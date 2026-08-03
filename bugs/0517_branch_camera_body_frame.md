# 0517 — detector redesign B2 (remainder): a reflect-branch camera BODY adopts its branch frame

## The gap

Detector-redesign B2 shipped per-branch camera *registration* (sensor size blends into the
branch detector, `branch_detector_camera_assignments` persists), and the camera *body* STEP
overlay has always ridden the sequential Image row's fold transform
(`_optical_axis_fold_world_transform_for_row(_image_plane_row_index())`). Right for the
transmit/image arm; wrong for a camera registered to a REFLECT branch detector: the sensor
plane lives on the reflect arm (e.g. the dual-lens scene's MV120 arm folded +Y) while the body
still draws on the image arm — the long-standing "OFF-AXIS reflect-detector camera-BODY
3-D-frame placement" remainder.

## Fix

Frame-level, mirroring the fold-transform architecture (no seat-time rotation writes — the
body *follows* the branch through refreshes):

- `_build_scene_bundle` stashes each branch detector's world frame
  (`_branch_detector_world_frames`: branch_path → center/normal/focus_source). Merge-only, so
  auxiliary partial bundle builds (two-arm fold parts, analysis sub-bundles) cannot wipe it.
- New `_camera_branch_world_transform()` (layout_polyline_display): when exactly ONE branch
  assignment exists and its arm does NOT reach the designed Image, return
  `F(v) = C + R (v − S)` — S = the straight sensor anchor `(0, 0, image_plane_z)` the aligned
  mesh is built around, C = the branch detector centre, R = the minimal rotation carrying +Z
  onto the branch normal (`_rotation_between_directions`, antiparallel-safe). The SENSOR lands
  on the detector and the front face sits `front_to_sensor` upstream BY CONSTRUCTION; the
  user's stored rotations/offsets remain their own in-frame adjustments.
- `_transformed_imported_camera_step_mesh` prefers this transform over the Image-row fold
  transform; the memo signature already hashes whichever transform is active.
- `seat_camera_on_sensor` writes its world shift back through Rᵀ when the branch frame is
  engaged (a straight-frame offset reaches the world through R); the shipped Image-row path
  keeps its raw-add behaviour byte-identical.
- All editor-attribute reads go through `self.__dict__` (the 0082 tkinter `__getattr__` trap).

No-op cases (today's behaviour byte-identical): no assignment; several assignments (one body
cannot serve two arms); the assigned arm reaches the designed Image; untraced scene.

## Guard

`validate_open3d_0517_branch_camera_body_frame.py` (penta phase 416): SOURCE wiring checks +
the real dual-lens scene (`beam_splitter_dual_mv_150_120` + BC-OM25M): assign the reflect
branch, assert the transform engages, the mesh's front face lands `front_to_sensor` upstream
of the detector along the branch normal, and the body centres laterally on the branch axis.
