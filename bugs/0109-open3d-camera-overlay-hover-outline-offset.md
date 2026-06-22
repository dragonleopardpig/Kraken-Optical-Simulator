# 0109 — Camera STEP hover outline is offset / ghosted off the rendered body

**Flags (2026-06-22):**
- `attachment/recorded_bug_repros/flag_20260622_161110_657` — *"ghost highlight"*
- `attachment/recorded_bug_repros/flag_20260622_161129_828` — *"offset highlight"*
- `attachment/recorded_bug_repros/flag_20260622_161146_544` — *"offset highlight."*

Hovering a face of the imported **camera** STEP body draws the gold face-hover
outline ~17 mm in front of (and not aligned with) the rendered camera body — a
stranded "ghost" highlight that does not sit on what is drawn.

---

## Evidence (from the flag `state.json`s)

All three are a **passive / idle** face hover on the camera body
(`interaction_mode='idle'`, `hover_step_cell_key=(None,'passive','F005'|'F006'|'F037')`),
with `step_overlay_poses/camera/placement_offset_xyz=[0,0,0]` (no manual drag):

| | rendered camera body (`step_actor_bounds/camera`) | gold hover outline (`hover_outline_bounds`) |
|---|---|---|
| x | [-35.0, 35.0] | [-32, 32] / [-19, 19] |
| y | [-35.0, 35.0] | ±35 / -32 (one face) |
| **z** | **[607.27, 680.90]** | **[589.86, 640.36]** |

The outline's x/y sit inside the body's transformed frame (so it is *not* native
STL coordinates), but its z is shifted **forward by exactly 17.41 mm**
(`607.27 − 589.86 = 17.41`). The outline is the camera's face geometry baked at
an **earlier image-plane alignment**, while the body is drawn at the current one.

---

## Root cause

The camera STEP body is **not** positioned by a translate/rotate gesture. Its
axial pose is driven by the layout's image plane:
`_transformed_imported_camera_step_mesh` aligns the camera front face to
`camera_front_z = _current_image_plane_z() - _current_camera_front_to_sensor_mm()`
(`layout_polyline_display.py:1283`). That target **is** folded into the rendered
mesh's cache signature (`:1286`), so the body re-aligns whenever the image plane
moves (a solve, an image-at-focus shift, a thickness edit, a camera/sensor
reassignment).

But the **face-metadata** cache key did not track it. For the display-only
labels (`camera`/`led`/`lens`), `_step_overlay_face_metadata`
(`scene_placement_commands.py`) deliberately keys only on `(label, stat_key)`
— pose-blind — to avoid re-paying the cold STEP-import cost. The metadata bakes
world-space face geometry (`centroid_world`/`normal_world`/outline) from the
*then-current* aligned mesh. So after the image plane moved, the rendered body
went to the new pose while the cached face geometry — and therefore the gold
hover outline built from it — stayed at the body's **former** pose.

The existing `_invalidate_step_overlay_face_metadata_cache` (bug 0050) only fires
on a STEP translate/rotate, which never happens for an image-plane-driven move,
so the stale entry was never dropped.

(The legacy "keep the camera metadata pose-blind, the recompute is 35 s" comment
conflated the **cold STEP import** with the **recompute**. The import is
path-cached (`_load_step_mesh`, `_external_cad_mesh_cache`); the actual recompute
on the cached 228 k-cell camera mesh is **subsecond** — measured 0.02 s
extract+triangulate, 0.1 s normals — exactly as bug 0050's "freeze-free" note
already claimed. So re-keying on the alignment target is freeze-free.)

---

## Fix (`services/scene_placement_commands.py`)

New `_step_overlay_alignment_target_z(label)` returns the image-plane-driven
axial target for the overlays that have one — `image_plane_z - front_to_sensor`
for the camera, the z translation for the led, `None` otherwise.
`_step_overlay_face_metadata` folds it into the cache key for the display-only
labels:

```python
else:
    align_target = self._step_overlay_alignment_target_z(label)
    if align_target is not None:
        cache_key = cache_key + (("align_z", align_target),)
```

So when the image plane moves, the camera/led metadata cache key changes, the
next hover/pick recomputes the face geometry against the freshly-aligned mesh,
and the gold outline tracks the rendered body. Translate/rotate offsets stay
handled by the existing 0050 invalidation; analytic labels keep their full
pose signature.

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_camera_overlay_hover_alignment` — penta
  **phase 95** (new; baseline → 96 phases). Checks: the alignment-target
  accessor (camera/led/none); the functional cache (unchanged plane = hit, moved
  plane = recompute baked at the new target, never the stale entry); the source
  folds the alignment target.

In-app eyeball owed: headless can't drive the live VTK passive face hover, so
confirm in-app that hovering the camera body after a solve / image-plane move
lands the gold outline on the drawn body (no forward ghost).
