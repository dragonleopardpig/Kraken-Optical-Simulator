"""Compare lens STEP + disc placement between om05a_folded.py (reference) and
om05a_folded_80mm.py (flagged). Prints lens STEP world bounds, front-datum world
station, and EVERY thin disc-like actor >20mm anywhere in the scene."""
import sys
from pathlib import Path
import numpy as np

def census(scene):
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path(scene).resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)
    editor.open_3d_view()
    editor.update_idletasks(); editor.update()
    insp = editor._three_d_inspector
    insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
    _settle(editor, 1.0)

    print(f"### {scene}")
    try:
        mesh = editor._transformed_imported_step_mesh_for_label("lens")
        print("lens STEP world bounds:", [round(float(v), 1) for v in mesh.bounds])
    except Exception as exc:
        print("lens STEP mesh unavailable:", exc)
    # front-datum world station via the surface transform of its row
    for i, r in enumerate(editor.rows):
        if "Front Optical Vertex Datum" in str(getattr(r, "name", "")):
            try:
                t = editor._surface_transform_for_rows(editor.rows, i)
                print(f"front datum row {i} world origin:", [round(float(v), 2) for v in np.asarray(t)[:3, 3]])
            except Exception as exc:
                print("front datum transform unavailable:", exc)
            break
    props = insp._renderer.GetViewProps()
    props.InitTraversal()
    while True:
        p = props.GetNextProp()
        if p is None:
            break
        try:
            if not p.GetVisibility():
                continue
            b = p.GetBounds()
            if b is None:
                continue
            ext = sorted([b[1] - b[0], b[3] - b[2], b[5] - b[4]])
            if ext[0] < 6.0 and ext[1] > 25.0 and ext[1] < 200.0 and ext[2] < 200.0:
                col = p.GetProperty().GetColor() if hasattr(p, "GetProperty") else (0, 0, 0)
                cx, cy, cz = 0.5 * (b[0] + b[1]), 0.5 * (b[2] + b[3]), 0.5 * (b[4] + b[5])
                print(f"DISC at ({cx:8.1f},{cy:7.1f},{cz:7.1f}) dia~{ext[1]:.1f}x{ext[2]:.1f} "
                      f"col=({col[0]:.2f},{col[1]:.2f},{col[2]:.2f})")
        except Exception:
            continue
    editor.destroy()

if __name__ == "__main__":
    census(sys.argv[1])
