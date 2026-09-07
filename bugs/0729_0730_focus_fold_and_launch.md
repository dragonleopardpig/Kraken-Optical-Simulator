# 0729 / 0730 — the focus plane must follow the fold, and the launch must come from the device

Two flags on build 5d8137c9, both on `attachment/om05a_folded_80mm.py`.

## 0729 — `flag_20260907_094552_625`: the focused image was drawn past the 40 mm RA mirror

> "the focused image shown at the bottom of the 40mm RA mirror? Please check whether this is
> correct." … "I think it skip the fold. It should be located somewhere near the Filter."

Correct on both counts. The bugs/0728 placement extrapolated the FINAL STRAIGHT SEGMENT of the
rays by the measured waist offset. Measured on om05a:

| | |
|---|---|
| waist offset (measured, along the sensor normal) | −78.55 mm |
| last leg, RA mirror 2 → sensor | **60.31 mm** |
| so the straight extrapolation overshoots the fold by | **+18.24 mm** |
| drawn at | (272.63, **76.79**, −25) — past the mirror |
| walking the REAL traced path back 78.55 mm lands at | **(248.64, 52.80, −14.88)**, travelling +x |
| the Filter sits at | x ≈ 249.95 |

So the distance was right and the placement skipped the fold, exactly as the user said.

**Fix.** `focus_point_along_paths(polylines, directions, offset_mm, image_axis)` walks each ray of
the winning field back from its END along its own traced polyline by its own path length to that
plane, `|offset| / |d·n|` (an oblique ray travels further than the axial distance). The rays
converge at the waist, so the walked-back points coincide; their mean is the focus point and the
mean local segment direction is the plane's normal. `focus_waist_from_grouped_rays` now reports
`group_index` so the caller knows which field set the plane;
`_measure_focused_image_plane` stashes `focus_center_world` / `focus_normal_world`, and the specs
prefer them, falling back to the straight extrapolation when a scene has no fold in the way.

Guard: `validate_open3d_0729_focus_plane_follows_the_fold` = penta phase 528.

## 0730 — `flag_20260907_095208_913`: rays launched from off the device

> "rays are not launched from 6 points. The blue rays seems go hay wired."

Censused: the imaging source launched from a **3 × 3 grid at (±29.38, ±29.38, 0)** — sensor/|m| in
BOTH axes — while the inspected face is a **50 × 1 mm strip**. Two thirds of the field points sat
29 mm above and below a 1 mm-tall device, launching from empty space; their rays wandered through
the tower (the "haywire" cyan). Only **35 of 4332** traced paths reached the sensor.

**Fix (general).** `_imaging_fov_half_extents` is intersected with the physical inspected face
(`_object_face_half_extents` → `_clamp_launch_to_object_face`): a field point outside the object
is not a field point. And in `_sample_imaging_field_grid_pairs`, an axis whose span is under 10%
of the other carries no separable field information (three samples across 1 mm sit inside the
blur), so it is sampled once at the centre. The rule is the ASPECT, not the size — a 1.5 × 1.5 mm
microscope field still gets the full 3 × 3 grid.

Measured after, on the same scene:

| | before | after |
|---|---|---|
| imaging launch points | 9, on a square grid off the device | **3, on the face** (+3 from face B = the 6 the user expected) |
| rays reaching the sensor | 35 | **477** |
| missed the image | 1025 | 109 |

Scenes with no declared inspection part are untouched.

Guard: `validate_open3d_0730_launch_on_the_object_face` = penta phase 529.

## Follow-up

The user's next call, tracked separately: *"Refusal of solve is unnecessary for the case of image
location shift since we already have image detached from sensor shows up. Only apply to real
collision will do."*
