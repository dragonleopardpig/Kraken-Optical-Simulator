"""0683: (a) verify the centred part box; (b) MEASURE arm A's delivered object-side
field band -- a fine y-scan of field points through the real chain launch. Evidence
for the split-FOV question (flag 133605)."""
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.inspection_part import box_corners, normalize_inspection_part_spec

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False

    # fine y-scan: x=0, y from -16 to +16 in 1 mm steps (patch the launch grid)
    ys = [float(y) for y in np.linspace(-16.0, 16.0, 33)]
    editor._sample_imaging_field_grid_pairs = lambda: [(0.0, y) for y in ys]

    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    editor.open_3d_view()
    editor.update_idletasks()
    editor.update()
    inspector = editor._three_d_inspector
    pose = inspector._inspection_part_pose(system, bundle)
    spec = normalize_inspection_part_spec(getattr(editor, "inspection_part_spec", None))
    corners = np.asarray(box_corners(spec, pose[0], pose[1]))
    print("part z:", round(corners[:, 2].min(), 2), "..", round(corners[:, 2].max(), 2))

    per_y: dict[float, list[int]] = {y: [0, 0] for y in ys}
    for rp in (bundle.ray_paths or []):
        if str(getattr(rp, "source_id", "") or "") == "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[0])):
            continue
        y0 = min(ys, key=lambda y: abs(y - float(p[0][1])))
        if abs(y0 - float(p[0][1])) > 0.6:
            continue
        per_y[y0][0] += 1
        if bool(getattr(rp, "reaches_image", False)):
            per_y[y0][1] += 1
    delivered = []
    for y in ys:
        launched, reached = per_y[y]
        if launched:
            frac = reached / launched
            mark = "#" * int(round(10 * frac))
            print(f"  y {y:+6.1f}: {reached:3d}/{launched:3d} {mark}")
            if frac >= 0.2:
                delivered.append(y)
    if delivered:
        print(f"delivered band (>=20% reach): y {min(delivered):+.1f} .. {max(delivered):+.1f}")
    editor.destroy()


if __name__ == "__main__":
    main()
