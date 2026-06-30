# 0185 — BUG: a promoted right-angle MIRROR folds the rays but leaves the lens + camera on the old straight axis

## Flag

`attachment/recorded_bug_repros/flag_20260630_133944_068/` on the folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`):

> "Why the camera and lens are still in old location? They should have automatically
> relocate to the reflected path, correct?"

The user's mental model is right. The layout's mirror is a **promoted STEP optical solid** — a
right-angle mirror cube whose `S001/F002` face carries `function = "Mirror"` (interaction-face
normal `[0.707, 0, -0.707]`). The traced chief rays already fold +Z → +X off it: the recording's
`state.json` shows `axis:ray:139:segment:2` running `[-315.2, 0, 71.897] → [380.7, 0, 71.897]`,
i.e. straight along **+X** at the mirror height `z = 71.897`. But the sensor row, the lens rows,
and the lens/camera STEP overlays all stayed on the original **straight +Z** axis — the beam
folded away and left the hardware behind.

## Root cause — the full mirror is read as a straight-through, then the non-folding skip guard fires

A promoted solid re-poses its downstream sequential rows onto its exit branch via
`build_optical_solid_output_port_pose_overrides` (the "output-port follower" workflow). The
right-angle mirror defeats it in two steps:

1. **A mirror CUBE reads all six outer faces as inferred `Transmit/Port` outputs.** Among those
   inferred exits `select_optical_solid_output_face` prefers the +Z-aligned face (the bugs/0084
   axial preference, correct for a beam-splitter's real straight-through), so it picks the cube's
   **+Z face `F003`** as a "straight-through" exit.
2. **The non-folding skip guard then bails.** That exit is codirectional with +Z, so
   `_exit_frame_is_non_folding` is True and the guard did `row_index += 1; continue` — bugs/0022:
   an inferred, *non-folding* exit (a beam-splitter cube nudged sideways) must NOT drag the
   downstream rows onto the displaced face. For a beam splitter that is right; for a **full
   mirror** it is wrong, because a mirror has **no** straight-through — 100 % of the light
   reflects. So the rows were left on the straight +Z axis.

The lens/camera STEP overlays are seated on that same straight +Z cumulative-thickness axis by
`_cad_mesh_aligned_to_optical_axis`, so with the rows un-folded they floated on the old axis too.
Net visible defect: the rays fold to +X but the lens barrel and camera STEP do not — exactly what
the flag reported.

## Fix — two halves: fold the ROWS, then carry the OVERLAYS onto the same fold

### 1. ROWS — a full-mirror interaction face has no straight-through, so reflect instead of skip

`KrakenOS/UI/nonseq_output_ports.py`:
- `_solid_has_full_mirror_interaction_face(world_faces)` — True only when
  `select_optical_solid_interaction_face` is a face whose `function == "Mirror"`. A beam-splitter
  cube's interaction face is a `Beam Splitter` (not a `Mirror`), so it is intentionally excluded
  and keeps its real straight-through (bugs/0084-0091 unchanged).
- In `build_optical_solid_output_port_pose_overrides`, the non-folding skip branch now, before
  giving up, checks that predicate. For a full mirror it builds the reflected exit frame with the
  existing `_reflected_frame_from_interaction_face` (incoming +Z reflected off the `[0.707,0,-0.707]`
  mirror normal → **+X**) and drives the follower-row workflow onto that branch
  (`frame_source = "interaction_reflection_fallback"`). Any non-mirror solid still hits the original
  `row_index += 1; continue`, so behaviour is **identical** for every existing scene.

Result on the AZ85 layout: overrides for rows **[2..8]**, all at `z = 71.897` with optical axis
**+X** — row 2 (mirror exit gap) `[40, 0, 71.9]`, row 3 (Front Optical Vertex Datum / lens front
datum) `[82.45, 0, 71.9]`, row 8 (Image/Sensor) `[287.82, 0, 71.9]` — coinciding with the
recording's traced reflected chief ray.

### 2. OVERLAYS — one rigid fold transform carries the straight-axis meshes onto the anchor row's pose

`KrakenOS/UI/services/layout_polyline_display.py` (`LayoutPolylineDisplayMixin`):
- `_optical_axis_fold_world_transform_for_row(row_index)` reads the row's fold override and returns
  the single rigid world transform `F(v) = C + R·(v − S)`, where `S = (0,0,straight_z[row])` is the
  row's station on the straight axis and `C`/`R` are its folded centre/rotation. Returns **None**
  when the row has no fold override.
- `_mesh_with_world_transform` applies it (identity / None / non-finite all pass the mesh through
  untouched); `_fold_transform_signature` folds it into the overlay's cache key so a fold change
  re-meshes.
- Wired into `_transformed_imported_lens_step_mesh` (anchored on `_lens_front_datum_row_index`) and
  `_transformed_imported_camera_step_mesh` (anchored on `_image_plane_row_index`): the
  straight-axis-aligned mesh is folded onto the same +X branch the rows now sit on, so the lens
  STEP front datum lands at x ≈ 82 and the camera STEP sensor at x ≈ 288.

## Verification

- Guard `KrakenOS/UI/validate_open3d_ra_mirror_fold_follows_reflection.py` (display-free,
  `run_checks()`): mirror solid recognised as a full specular fold; a beam-splitter face (the same
  faces with `function` flipped to "Beam Splitter") is **NOT** treated as a fold; ≥6 downstream rows
  receive overrides; the image/sensor row folds onto +X (`x = 287.82`, `|z − 71.897| < 2`, axis +X);
  the image fold matches the camera overlay's anchor transform to `< 1e-6`; the lens STEP front
  datum (`x ≈ 82.45`) and the camera STEP sensor (`x ≈ 287.82`) both fold onto +X with a +X optical
  axis. **PASS.** Standalone, mirroring the sibling AZ85 guards (not a penta phase).
- Structure guard `validate_machine_vision_azure_85_ra_mirror.py` still **PASS**.
- **Beam-splitter regression** (the mirror gate must not touch a real straight-through):
  `validate_open3d_beam_splitter_transmit_and_second_axis` **PASS** (override_keys=[], transmit rays
  reach the lens datums and travel past the entrance) and `validate_open3d_moved_splitter_keeps_focus`
  **PASS** (bugs/0023: a cube nudged off-beam keeps the focus on station).
- **Non-folded scenes untouched** — on `machine_vision_150mm_datasheet_1x.py` and
  `machine_vision_85mm_azure_datasheet_05x_20x.py` the lens- and camera-row fold transforms are both
  `None`, so `_mesh_with_world_transform` passes the overlays through unchanged. Only a promoted
  full-mirror cube triggers the fold; no penta phase exercises one, so the marathon is unaffected.

## Note

In-app eyeball still owed (headless can't drive the live VTK render), but the whole defect — the
+Z-face straight-through pick, the skip that stranded the rows, and the overlays floating on the old
axis — is reproduced and asserted headlessly, and the folded rows/overlays land exactly on the
recording's traced reflected chief ray (+X at z = 71.897).
