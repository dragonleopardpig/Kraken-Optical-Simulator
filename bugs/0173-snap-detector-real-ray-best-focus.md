# 0173 — "Snap detector to image plane" now works on beam-splitter / solid scenes

## Symptom (user)

The MV-150 test scene (with the BK7 beam-splitter cube the user keeps) opens with the
detector ~+2.7 mm off best focus. The right-click **"Snap detector to image plane (remove
defocus)"** did nothing — it reported *"best-focus image plane is not computable for this
layout."* (Not the "Snap to FOV" button — that solves field of view, not focus.)

## Root cause

`snap_detector_to_image_plane` moved the detector to the **paraxial** image conjugate
(`_paraxial_image_plane_z`). That solve is centered-refractive-only — it raises *"Paraxial
solve supports centered refractive systems only"* when a **3D solid / beam-splitter cube**
is in the path (the cube is a mesh solid, not a surface with a radius). So it returned None
and the snap bailed, leaving the defocus in place. (Independent of the surrogate — the
surrogate's Thin Lenses are paraxial-friendly; it's the *cube* that defeats the solve.)

## Fix

When the paraxial conjugate is unavailable, fall back to the **real-ray** on-axis best
focus: `_real_ray_best_focus_shift_for_rows` builds the mesh system, traces the on-axis 2D
spot, and returns the axial shift that minimises it (`_spot_best_focus_shift`, the same math
behind the Spot-map defocus warning). `snap_detector_to_image_plane` then moves the
back-focal gap (`rows[-2]`) by that shift, exactly as the paraxial path does.

On the MV-150 beam-splitter scene: paraxial None -> the snap moves the **Lens Rear Datum**
gap **+2.71 mm** (290.74 -> 293.45), dropping the on-axis spot 59 µm -> 0.09 µm. The
sequential 0166 build path and centered-lens paraxial snap are unchanged.

## Also: how to focus by hand (no pull needed)

The Spot map reports "detector +X mm off best focus". In the layout table, increase the
**Lens Rear Datum** thickness (the row just before Image — its thickness *is* the back-focal
distance) by that X. Or mark it Variable and click **Solve Best Focus**.

## Guard

`validate_open3d_snap_detector_best_focus` (display-free): on the MV-150 beam-splitter scene
the paraxial plane is None, the real-ray shift recovers the ~+2.7 mm defocus, and the snap
applies it; plus the fallback source contract. Penta phase 167. In-app eyeball owed.
