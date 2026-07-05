# 0232 — a trailing (2nd) fold mirror must fold ONLY the camera, not the lens group

**Status: FIXED for NEW promotes. A free-placed RA mirror promoted near the camera (a second,
trailing fold) now inserts at the END of the chain (before the sensor), so it folds ONLY the
camera. NOTE: an already-saved scene with the mirror at the wrong row is baked — the user must
UNPROMOTE + RE-PROMOTE the 2nd mirror to pick up the fix. Also partly stale (see below).**

## The report

flag_20260705_172709 (re-saved `attachment/machine_vision_Pyrite85_RA_Mirror.py`): "after second
RA promoted, it should only fold the camera." The Pyrite periscope — object → mirror-1 (folds up)
→ lens group → mirror-2 → camera — where mirror-2 sits right before the camera.

## Root cause (confirmed on the exact re-saved scene)

The free-placed 2nd mirror was inserted at **row 2** — right after the FIRST mirror, BEFORE the
lens group (rows 4-8). The promote's insert index came from the table selection
(`max(selected)+1`), so with the first mirror selected it landed at row 2. The pose-override walk
(`build_optical_solid_output_port_pose_overrides`) folds EVERY row after the mirror, so it swept
the whole lens chain onto the fold branch: lens element "Blackbox Group 1" (row 5) folded to the
mirror-2 branch at (0, 190.6, 120.6) along with the camera — not "only the camera".

A trailing fold mirror must be the **LAST optical element before the sensor** (like AZ85's 2nd
mirror at row 8, which folds ONLY the image/camera row 9) so the fold moves only the camera.

## The fix

`_promote_step_and_assign_face_function_inner` (open3d_face_assignment): when the scene ALREADY
has a promoted mirror fold (`_promoted_mirror_fold_row_indices()` non-empty) AND the user is
assigning a **Full-Reflecting** face, the promotion inserts at the end
(`promote_insert_at = len(self.editor.rows)`; `_step_overlay_insert_index` clamps a large index to
before-Image) instead of after the selected row. The FIRST fold has no existing mirror → keeps its
place (near the object). A beam splitter / non-mirror face is unaffected.

## Verification

`validate_open3d_trailing_fold_mirror_insert` (display-free, penta phase 205): on the two-mirror
AZ85 the LAST promoted mirror folds ONLY the image/camera row (mechanism); the insert clamps a
large index to before-Image; a Full-Reflecting assignment with an existing fold picks the end
index; the face-assign wiring is present. Regression: offbeam (0224/0226), periscope (0230),
retroreflect-dive, carryover all green; `face_context_assignment` has the SAME pre-existing
unrelated failure (split coplanar face pair) with and without this change.

## Caveats

- **Stale**: the flag screenshot predates the 17:19 fold-sign fix (1ea0fff5) — it shows the old
  collinear/parallel behavior. A restart is needed to see the current fold at all.
- **Baked scene**: the saved layout has the 2nd mirror at row 2; the fix only changes NEW promotes.
  Unpromote + re-promote the 2nd mirror (or move its row after the lens group) to fix the scene.
- **Insert position**: the fix puts a trailing fold mirror at the END (before the sensor), matching
  the flagged "fold to camera" intent + AZ85. A mirror dropped MID-chain (between lens groups) would
  still want its exact physical position — a follow-up if that use case arises.
