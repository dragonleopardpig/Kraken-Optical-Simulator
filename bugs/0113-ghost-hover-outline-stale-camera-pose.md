# 0113 — A camera's hover outline ghosts at its old, pre-push-back location

**Report (2026-06-23, flag_20260623_074500_871):**
> "ghost highlight."

> (user hypothesis) "I suspect the ghost is from old location after BS is added
> and camera pushed back, not sure, please check as well."

The flag bundle was recorded in **measure mode** hovering the camera STEP body.
The gold hover outline (`hover_step_cell_key = (..., "reanchor", 1315)`) is a flat
**69.4 mm square at z = 589.56**, but the live camera body's front face sits at
**z = 603.07** — the outline floats **+13.51 mm in front** of the drawn body. The
user's hypothesis is exactly right: the beam-splitter promotion pushed the image
plane (and so the image-plane-aligned camera body) back, but the hover outline
stayed at the camera's former location.

Ground truth from `state.json`:

| | z front |
|---|---|
| `hover_outline_bounds` (the gold square) | 589.56 |
| `step_actor_bounds["camera"]` (live body) | 603.07 |
| Δ (ghost gap) | **+13.51** |

---

## Root cause — pose-blind cached snap geometry vs an image-plane-aligned body

The camera/led STEP face metadata is **pose-blind cached** (bugs/0111): it is
baked at most once per session because the bake is the full planar-clustering +
affine-fit + snap-STL pipeline (~18–35 s for the 228k-cell camera body), and
re-keying it on the image-plane target (bugs/0109) re-ran that bake on every
image-plane move / deselect, freezing the UI. The bake writes a **snap STL** at
the body's *then-current* world pose (`_step_overlay_face_metadata_compute`,
`source_stl`), and the face records carry world geometry baked from that pose.

The rendered camera body, however, **re-aligns to the live image plane every
refresh**: `_transformed_imported_camera_step_mesh` aligns the camera front face
to `image_plane_z - front_to_sensor`. So after the image plane moves (a solve, an
image-at-focus shift, a thickness edit, or — here — a beam-splitter promote
pushing the chain back), the drawn body is at the new z while the cached snap
geometry is still at the bake-time z.

The snap STL's face **cell indices do not map** to the live full-body display
mesh (different tessellation), so `face_indices_for_record` returns empty and
`_hover_overlay_for_step_face_impl` falls through to its **cached-STL fallback**
(`self._cad_scene_cache.face_outline(source_stl, …)`) — which draws the outline at
the **bake-time pose**. That is the ghost.

This is the cosmetic offset bugs/0109/0111 explicitly deferred: *"the cosmetic
hover-outline offset … must be fixed without re-baking (apply the axial delta on
read)."* This is that fix.

---

## Fix — stamp the bake-time alignment target; shift the outline on read

No re-bake. The metadata stays pose-blind cached; we record where it was baked and
correct on the way out.

1. **Stamp at bake** (`scene_placement_commands._step_overlay_face_metadata`):
   for a display-only label, after the compute and before caching,
   `metadata["alignment_target_z_at_bake"] = self._step_overlay_alignment_target_z(label)`
   (camera → `image_plane_z - front_to_sensor`; led → its z). The pose-blind cache
   key is unchanged, so the freeze-free contract (bugs/0111) holds — an image-plane
   move still returns the same cached object with its original bake-time stamp.

2. **Apply on read** (`open3d_inspector`):
   - `_display_only_overlay_axial_delta(label, metadata)` =
     `current_alignment_target − alignment_target_z_at_bake`; returns `0.0` for
     non-display-only labels, an unmoved plane, an unstamped (old) cache entry, or
     when there is no image plane.
   - `_hover_overlay_for_step_face_impl`, at the **cached-STL outline return only**,
     shifts the produced outline (`_translate_hover_mesh`, `inplace=False` so the
     cached source is untouched) and the fallback centre (`_shift_center_z`) by
     `(0, 0, delta_z)`. The live-mesh path (Path A) is left alone — when it fires it
     is already at the live pose.

Blast radius is tight: the delta is non-zero only for camera/led, and only when
the image plane has moved since the bake. Other labels and unmoved bodies shift by
0.

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_ghost_hover_outline_alignment` — two parts:
  - `run_checks()` (display-free, 6 assertions): the bake stamps
    `alignment_target_z_at_bake` for camera/led; the stamp survives a pose-blind
    cache hit (image-plane move ⇒ same object, bake-time stamp ⇒ non-zero delta);
    `_display_only_overlay_axial_delta` = current − baked (0 in the not-applicable
    cases); `_translate_hover_mesh` / `_shift_center_z` move a stale outline+centre
    onto the live body without mutating the cached source; the impl shifts the
    cached-STL outline by the delta; the bake stamps only display-only labels.
  - `render_alignment_proof()` (geometry/PNG snapshot): a stale outline at z=589.56
    is 13.51 mm off the live body at z=603.07 before the shift and < 1e-3 mm after.
- The bugs/0111 guard `validate_open3d_camera_overlay_hover_alignment` still passes
  (the stamp does not re-key the cache → no re-bake / freeze).
- Penta **phase 103** (new; baseline → 104 phases) runs `run_checks()` only
  (no rendering — keeps the validator marathon headless-safe).

In-app eyeball owed: headless can't drive a live VTK hover pick. Confirm in-app
that, after a beam-splitter promote pushes the camera back, hovering the camera in
measure mode draws the gold outline **on** the body (not floating in front of it).
