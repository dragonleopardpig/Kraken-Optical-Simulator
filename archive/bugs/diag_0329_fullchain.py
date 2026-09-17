"""bugs/0329 full-chain: run the REAL step_feature_pick_for_display_xy for the recorded
camera+cursor [886,607], with the REAL editor (KrakenLayoutEditor) and a VTK-camera
_world_to_display_2d. If it returns the square (F053), the top-priority 0328 mined path
fires end-to-end -> the live app that showed whole-panel F005 was STALE.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, vtk
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.open3d_round_lens_pick import step_feature_pick_for_display_xy

CURSOR = (886.0, 607.0); W, H = 1838, 904


class _FakeInspector:
    _opening_loop_hover_feature = Kraken3DInspector._opening_loop_hover_feature
    _clear_aperture_opening_face_index = Kraken3DInspector._clear_aperture_opening_face_index
    _clear_aperture_opening_edge_feature = Kraken3DInspector._clear_aperture_opening_edge_feature
    _clear_aperture_outline = Kraken3DInspector._clear_aperture_outline
    _hover_overlay_for_feature = staticmethod(Kraken3DInspector._hover_overlay_for_feature)
    _edge_pick_alt_active = False
    _picker = None

    def __init__(self, editor, project):
        self.editor = editor
        self._project = project
        self._ca_opening_face_index_cache = {}

    def _world_to_display_2d(self, point):
        return self._project(point)

    def _step_label_is_round_lens_like(self, label):
        return False

    def _step_face_ray_pick_for_display_xy(self, label, xy):
        return None

    def _coarse_step_face_ray_pick_for_display_xy(self, label, xy):
        return None

    def _picked_feature_info_cached(self, *a, **k):
        return None


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    app.imported_led_step_path = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0

    ren = vtk.vtkRenderer()
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(W, H)
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(285.12211524555573, 44.86112856896071, 121.92167776210495)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.13607788549386488, 0.9877295233717259, -0.0766367910300376)
    cam.SetParallelScale(101.15273775216139)
    ren.ResetCameraClippingRange(); rw.Render()

    def project(p):
        p = np.asarray(p, dtype=float).reshape(-1)
        if p.size < 3 or not np.all(np.isfinite(p[:3])):
            return None
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0); ren.WorldToDisplay()
        return np.asarray(ren.GetDisplayPoint(), dtype=float)[:2]

    inspector = _FakeInspector(app, project)
    hit = step_feature_pick_for_display_xy(inspector, "led", CURSOR)
    if not isinstance(hit, dict):
        print(f"PICK: {hit!r} (no feature)")
    else:
        fid = hit.get("face_id")
        sc = np.asarray(hit.get("surface_center", []), dtype=float).reshape(-1)
        ov = hit["feature"][1]
        is_line = int(ov.GetNumberOfLines()) > 0 and int(ov.GetNumberOfPolys()) == 0
        print(f"PICK: face_id={fid!r} line_overlay={is_line} "
              f"surface_center=({sc[0]:.1f},{sc[1]:.1f},{sc[2]:.1f})" if sc.size >= 3 else f"PICK: face_id={fid!r}")
        print("=> square (F053) means the 0328 mined path fires end-to-end; whole-panel means a gap.")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
