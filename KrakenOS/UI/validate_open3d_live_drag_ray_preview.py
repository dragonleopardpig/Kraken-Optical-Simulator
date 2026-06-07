"""Guard for bugs/0024 -- Live Mode shows a live ray preview while an element is
dragged, via a sparse fan + a rays-only refresh (no full scene rebuild).

Checks
------
Source contracts (always run):
A. ``_current_ray_count`` honours ``_drag_preview_ray_count_override``.
B. the placement drag sets that override and schedules a live refresh under
   Live Mode.
C. ``_refresh_live_preview_scene`` flushes the pending drag and takes the
   rays-only path while a drag is active; ``_finish_placement_drag`` clears the
   override; ``_refresh_rays_only`` exists.

Render (needs a display + the cube's source STEP; SKIP otherwise):
D. with Live Mode on and a pending placement drag, the live preview moves the
   model, traces a sparse fan (fewer ray actors), and refreshes ONLY the ray
   actors -- the body/row actors are left untouched.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_live_drag_ray_preview

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import inspect
import os
from pathlib import Path

os.environ.pop("WAYLAND_DISPLAY", None)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESCRIPTION = PROJECT_ROOT / "attachment" / "machine_vision_150mm_measured_test.py"
CUBE_ROW = 6


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    def _src(obj, name):
        try:
            return inspect.getsource(getattr(obj, name))
        except Exception as exc:
            notes.append(f"FAIL: cannot read {name} source: {exc!r}")
            return ""

    # A
    if "_drag_preview_ray_count_override" not in _src(KrakenLayoutEditor, "_current_ray_count"):
        notes.append("FAIL: _current_ray_count ignores the drag ray-count override")
        passed = False
    # B
    drag_src = _src(Kraken3DInspector, "_apply_placement_drag_motion")
    if "_drag_preview_ray_count_override" not in drag_src or 'schedule_live_refresh("placement drag")' not in drag_src:
        notes.append("FAIL: placement drag does not set the override + schedule a live refresh")
        passed = False
    # C
    live_src = _src(Kraken3DInspector, "_refresh_live_preview_scene")
    if "_flush_pending_placement_drag_for_live" not in live_src or "_refresh_rays_only" not in live_src:
        notes.append("FAIL: live preview does not flush the drag and take the rays-only path")
        passed = False
    if "_drag_preview_ray_count_override = None" not in _src(Kraken3DInspector, "_finish_placement_drag"):
        notes.append("FAIL: _finish_placement_drag does not clear the drag ray-count override")
        passed = False
    if not hasattr(Open3DSceneRefreshService, "_refresh_rays_only"):
        notes.append("FAIL: Open3DSceneRefreshService._refresh_rays_only missing")
        passed = False

    # D -- render behaviour.
    if not PRESCRIPTION.exists():
        notes.append("SKIP: bug-0024 repro prescription unavailable")
        return passed, notes

    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display
    from KrakenOS.UI.layout_editor import _resolve_project_file_path

    reuse = app is not None and inspector is not None
    xvfb_proc = None
    if not reuse:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            notes.append(f"SKIP: cannot render ({env_err})")
            return passed, notes

    own_app = False
    try:
        from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info

        module = _load_layout_module(PRESCRIPTION)
        surfaces = list(getattr(module, "SURFACES", []) or [])
        cube = surfaces[CUBE_ROW] if CUBE_ROW < len(surfaces) else {}
        adv = (cube.get("advanced", {}) or {}) if isinstance(cube, dict) else {}
        src = str(adv.get("OpticalSolidSourcePath", "") or "").strip()
        if not src or not _resolve_project_file_path(src).exists():
            notes.append("SKIP: beam-splitter cube source STEP unavailable")
            return passed, notes

        if not reuse:
            from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
            own_app = True

        app.rows = _rows_from_layout_info({"surfaces": surfaces})
        try:
            app._regenerate_missing_optical_solid_caches()
        except Exception:
            pass
        app._apply_layout_settings(dict(getattr(module, "SETTINGS", {}) or {}))
        app._sync_table()
        inspector.show_rays_var.set(True)
        inspector.refresh_from_editor(force_retrace=True)
        inspector.update_idletasks()
        try:
            inspector._trace_live_now()
        except Exception:
            pass
        inspector.update_idletasks()

        full_rays = len(inspector._ray_actor_map or {})
        full_bodies = len(inspector._row_actor_map or {})
        if full_rays <= 0 or full_bodies <= 0:
            notes.append(f"SKIP: baseline render empty (rays={full_rays}, bodies={full_bodies})")
            return passed, notes

        inspector.live_mode_var.set(True)
        inspector._placement_drag_state = {"kind": "translate", "row_index": CUBE_ROW, "axis": "x", "pending_translate_mm": 2.0}
        app._drag_preview_ray_count_override = 3
        desp0 = float(app.rows[CUBE_ROW].desp_x)
        try:
            inspector._refresh_live_preview_scene("placement drag")
        except Exception as exc:
            notes.append(f"FAIL: live drag preview raised {exc!r}")
            passed = False
            return passed, notes
        desp1 = float(app.rows[CUBE_ROW].desp_x)
        drag_rays = len(inspector._ray_actor_map or {})
        drag_bodies = len(inspector._row_actor_map or {})

        if abs(desp1 - desp0) < 1e-6:
            notes.append(f"FAIL: drag preview did not flush the pending move into the model (desp_x {desp0}->{desp1})")
            passed = False
        if drag_rays >= full_rays:
            notes.append(f"FAIL: drag preview did not trace a sparse fan (ray actors {full_rays}->{drag_rays})")
            passed = False
        if drag_bodies != full_bodies:
            notes.append(f"FAIL: rays-only drag preview disturbed the body actors ({full_bodies}->{drag_bodies})")
            passed = False
        elif verbose:
            notes.append(f"drag preview: desp_x {desp0}->{desp1}, ray actors {full_rays}->{drag_rays}, body rows kept {drag_bodies}")

        # restore
        app._drag_preview_ray_count_override = None
        inspector._placement_drag_state = None

        if own_app:
            try:
                app.destroy()
            except Exception:
                pass
        return passed, notes
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0024: Live Mode drag shows a sparse-fan, rays-only live preview")
        return 0
    print("[FAIL] bugs/0024 live-drag ray-preview guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
