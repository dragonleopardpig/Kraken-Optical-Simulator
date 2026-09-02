"""0693 (flag_20260902_115321): rotate RA mirror 1 -> lens surrogate leaves the body.

Reproduce the user's edit headlessly: rotate the "RA mirror 1 (50 mm)" solid so
its tilts go (0,90,-90) -> (-90,0,0) through the real rotation command, then
measure where the SURROGATE lens rows land vs where the lens STEP BODY lands.
Instrument `_set_step_placement_offset_xyz` to attribute every carry write.

Flag ground truth to match: mirror2 desp -> (9.2197, 43.5303, -657.1103),
lens placement_offset -> (15.5581, 0.2335, 9.2197).
"""
import traceback
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)

    rows = editor.rows
    m1 = next(i for i, r in enumerate(rows) if str(getattr(r, "name", "")) == "RA mirror 1 (50 mm)")
    m2 = next(i for i, r in enumerate(rows) if str(getattr(r, "name", "")) == "RA mirror 2 (40 mm)")
    lens_rows = [i for i, r in enumerate(rows)
                 if "PYRITE" in str(getattr(r, "name", "")) or "Vertex Datum" in str(getattr(r, "name", ""))]
    print("m1 row", m1, "m2 row", m2, "lens-ish rows", lens_rows[:6])

    # what world rotation carries the old orientation to the new one?
    r_old = rotation_matrix_from_kraken_tilts(0.0, 90.0, -90.0)
    r_new = rotation_matrix_from_kraken_tilts(-90.0, 0.0, 0.0)
    delta = np.asarray(r_new, dtype=float) @ np.asarray(r_old, dtype=float).T
    angle = float(np.degrees(np.arccos(np.clip((np.trace(delta) - 1.0) / 2.0, -1.0, 1.0))))
    axis_vec = np.array([delta[2, 1] - delta[1, 2], delta[0, 2] - delta[2, 0], delta[1, 0] - delta[0, 1]])
    n = float(np.linalg.norm(axis_vec))
    axis_vec = axis_vec / n if n > 1e-9 else axis_vec
    print(f"world delta rotation: {angle:.2f} deg about {np.round(axis_vec, 3)}")

    def snap(tag):
        r2 = rows[m2]
        print(f"[{tag}] m2 desp ({float(r2.desp_x):.4f}, {float(r2.desp_y):.4f}, {float(r2.desp_z):.4f}) "
              f"tilt ({float(r2.tilt_x):.1f}, {float(r2.tilt_y):.1f}, {float(r2.tilt_z):.1f})")
        print(f"[{tag}] lens offset {getattr(editor, 'lens_step_placement_offset_xyz', None)}")
        for i in lens_rows[:2] + lens_rows[-1:]:
            try:
                p = np.asarray(editor._surface_reference_world_point(i), dtype=float)
                print(f"[{tag}] row {i} ({rows[i].name}) ref {np.round(p, 3)}")
            except Exception as exc:
                print(f"[{tag}] row {i} ref FAILED {exc}")
        try:
            mesh = editor._transformed_imported_step_mesh_for_label("lens")
            b = np.asarray(mesh.bounds, dtype=float)
            print(f"[{tag}] lens BODY centre {np.round([(b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2], 3)}")
        except Exception as exc:
            print(f"[{tag}] lens body mesh FAILED {exc}")

    snap("before")

    real_set = editor._set_step_placement_offset_xyz

    def spy(label, value):
        stack = [f"{fr.name}:{fr.lineno}" for fr in traceback.extract_stack()[-6:-1]]
        print(f"SET offset[{label}] = {np.round(np.asarray(value, dtype=float), 4)}  via {' > '.join(stack)}")
        return real_set(label, value)

    editor._set_step_placement_offset_xyz = spy

    # the real command: axis/angle from the measured delta (expect a clean 90)
    axis_name = "xyz"[int(np.argmax(np.abs(axis_vec)))]
    signed = float(np.sign(axis_vec[int(np.argmax(np.abs(axis_vec)))]) * angle)
    print(f"calling rotate_scene_row_pose_world_axis(row={m1}, axis={axis_name!r}, delta={signed:.1f})")
    result = editor.rotate_scene_row_pose_world_axis(m1, axis_name, signed)
    print("command result:", str(result)[:200])
    editor._build_preview_system_rays_bundle(trace_rays=True)

    snap("after")
    r1 = rows[m1]
    print(f"m1 tilt now ({float(r1.tilt_x):.1f}, {float(r1.tilt_y):.1f}, {float(r1.tilt_z):.1f}) "
          f"(flag says (-90, 0, 0))")
    editor.destroy()


if __name__ == "__main__":
    main()
