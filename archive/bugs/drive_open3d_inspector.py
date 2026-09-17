"""Faithful repro: load dual-lens like File>Open (rows + apply_settings + refresh_plot), then Open 3D."""
from pathlib import Path
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _save_vtk_snapshot
from KrakenOS.common_optical_layouts.beam_splitter_dual_mv_150_120 import SURFACES, SETTINGS


def count(b):
    rp = list(getattr(b, "ray_paths", []) or []) if b is not None else []
    ta = sum(1 for p in rp if str(getattr(p, "branch_path", "") or "").startswith("twoarm/"))
    return len(rp), ta


app = KrakenLayoutEditor(headless=True)
try:
    app.current_layout_file = Path("beam_splitter_dual_mv_150_120.py")
    app.rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in SURFACES]
    try:
        app._auto_assign_missing_elements(app.rows)
    except Exception as e:
        print("auto_assign err", e)
    try:
        app._apply_layout_settings(SETTINGS)
    except Exception as e:
        print("apply_settings err", e)
    app._normalize_special_rows()
    app._sync_table()
    app.refresh_plot(suppress_analysis=True)          # <-- the load-time refresh (NO cache invalidation)
    app.update_idletasks(); app.update()
    lb = getattr(app, "_last_scene_bundle", None)
    print(f"AFTER LOAD: _last_scene_bundle paths/twoarm={count(lb)} dirty={getattr(app, '_preview_scene_trace_dirty', None)}")
    insp = _open_3d_inspector(app)                     # <-- Open 3D (reuses the cache?)
    print(f"OPEN_3D: _current_scene_bundle paths/twoarm={count(getattr(insp, '_current_scene_bundle', None))}")
    _save_vtk_snapshot(insp, Path("/tmp/load_3d_open.png"))
    print("SNAPSHOT /tmp/load_3d_open.png")
finally:
    try:
        app.destroy()
    except Exception:
        pass
