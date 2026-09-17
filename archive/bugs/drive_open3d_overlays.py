"""Drive the real inspector with detector-coverage overlays ON to verify the two-arm overlays."""
from pathlib import Path
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _refresh, _save_vtk_snapshot
from KrakenOS.UI.scene_geometry import scene_target_active_dimensions
from KrakenOS.common_optical_layouts.beam_splitter_dual_mv_150_120 import SURFACES, SETTINGS

app = KrakenLayoutEditor(headless=True)
try:
    app.current_layout_file = Path("beam_splitter_dual_mv_150_120.py")
    app.rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in SURFACES]
    try:
        app._auto_assign_missing_elements(app.rows)
    except Exception as e:
        print("auto_assign err", e)
    app._apply_layout_settings(SETTINGS)
    app._normalize_special_rows()
    app._sync_table()
    app.refresh_plot(suppress_analysis=True)
    app.update_idletasks(); app.update()
    insp = _open_3d_inspector(app)
    for var in ("show_detector_overlays_var",):
        try:
            getattr(insp, var).set(True)
        except Exception as e:
            print(f"{var} err", e)
    _refresh(insp, live=True)
    cov = insp._add_detector_coverage_overlays(getattr(insp, "_current_system", None), getattr(insp, "_current_scene_bundle", None))
    print(f"detector coverage overlay actors drawn = {cov}")
    b = getattr(insp, "_current_scene_bundle", None)
    for t in (getattr(b, "targets", []) or []):
        if getattr(t, "is_detector", False):
            print(f"  {t.name}: sensor={scene_target_active_dimensions(t)} meta={getattr(t, 'metadata', {})}")
    for preset in ("iso",):
        try:
            insp.set_camera_preset(preset)
        except Exception as e:
            print("camera preset err", e)
    try:
        insp._renderer.ResetCamera()
    except Exception:
        pass
    _save_vtk_snapshot(insp, Path("/tmp/overlays_iso.png"))
    print("SNAPSHOT /tmp/overlays_iso.png")
finally:
    try:
        app.destroy()
    except Exception:
        pass
