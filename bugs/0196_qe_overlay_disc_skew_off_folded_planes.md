# 0196 — Quick-Estimation FOV overlay discs render tilted off the folded planes ("2 planes each")

## Symptom
On the folded Pyrite/AZ85 periscope, enabling Quick Estimation (or double-clicking the FOV plane and
solving) drew the object FOV circle and the image/sensor rectangle **tilted**, floating beside the
real object and image planes rather than lying in them. The user read it as a duplicate:
"object plane and image plane: 2 of them each."

## Root cause
`quick_estimation_overlay.QuickEstimationOverlayService.add_overlays` computed a **single** normal
for every overlay disc:

```python
axis = img_pt - obj_pt          # object -> image DIAGONAL
u, v = _basis(axis)
```

On a straight system the object and image lie on one axis, so the diagonal *is* the plane normal and
this looked fine. On a **folded** system the object plane and the detector plane sit on different
legs of the periscope, so `img_pt - obj_pt` is a slanted vector pointing across the fold. Every
disc — the object FOV circle, the image circle, the recommended-sensor rectangle, and the two
pickable plane disks — was built in the plane perpendicular to that diagonal, i.e. **tilted ~45°**
off both real planes.

Measured on the folded AZ85: the object FOV circle sat 24.1 mm out of the true object plane, and the
image circle 7.6 mm out of the detector plane.

## Fix
`add_overlays` now takes each plane's **own** normal from the scene bundle's target rows (the object
target's `normal_world` and the detector target's `normal_world`) and draws each disc square to it:

```python
obj_normal = axis            # fallback for a straight system with no bundle normals
img_normal = axis
for target_row in (getattr(scene_bundle, "targets", None) or []):
    n = ...                  # normal_world, validated finite + non-zero
    if target_row.is_detector: img_normal = n
    elif target_row.is_object: obj_normal = n
u, v     = _basis(obj_normal)   # object-plane basis
u_i, v_i = _basis(img_normal)   # image-plane basis
```

The object FOV circle + object pick disk use `(obj_normal, u, v)`; the image circle, sensor rectangle,
image ghost circle, and image pick disk use `(img_normal, u_i, v_i)`. When the bundle carries no
normals (a straight system) both fall back to the old diagonal, so unfolded scenes are byte-for-byte
unchanged.

## Verification
`KrakenOS/UI/validate_open3d_qe_overlay_square_to_plane.py` (penta phase 210), on the folded AZ85:
- **OBJECT SQUARE** — FOV circle lies in the object plane (out-of-plane 0.0 mm) and is *not* coplanar
  with the diagonal (24.1 mm off it).
- **IMAGE SQUARE** — image circle lies in the detector plane (0.0 mm), 7.6 mm off the diagonal.
- **PICK DISKS SQUARE** — the two pickable plane disks use `obj_normal` (+Z) and `img_normal` (+X).
- **FOLDED DISTINCT** — the two plane normals genuinely differ (+Z vs +X), i.e. the shared-diagonal
  bug was observable here.

Overlays are a VTK render and can't be pixel-validated headless (llvmpipe SIGSEGV); this guard checks
the geometry the renderer consumes. In-app visual confirm owed.
