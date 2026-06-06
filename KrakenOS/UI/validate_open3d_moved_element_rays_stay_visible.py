"""Guard for bugs/0022 -- moving an element off the beam must not blank the trace.

Regression context
------------------
With "Show Clipped Rays" OFF, the 3D ray filter hides a ray that escaped without
reaching a surface and without a reflective fold (bug 0016 hides vignetted strays;
bug 0018 keeps a beam-splitter's reflected branch visible because it has
non-refractive steering). When the user shifts the beam-splitter cube sideways off
the optical axis (flag_20260606_220946 "beam splitter shifted out"), nothing hits
the cube -> no reflection -> every path escapes WITHOUT steering, and the on-axis
beam misses the (port-followed) detector too. The filter then hid *every* ray:
558 -> 0 rendered, a totally blank trace -- violating the invariant that rays must
not vanish when an element is moved.

Fix: ``_iter_3d_scene_ray_records`` only suppresses clipped rays when at least
one survives the filter; if the filter would hide EVERY ray, it shows them so the
beam's path stays visible.

Checks
------
A. Source: ``_iter_3d_scene_ray_records`` keeps the all-hidden fallback
   (``visible_paths if visible_paths else scene_paths``) -- fixture-free.
B. Render (needs the cube's source STEP + a display; SKIP otherwise): load the
   machine-vision prescription with Show Clipped Rays OFF, shift the beam-splitter
   cube -55 mm in X via its placement handle, and assert the trace still renders
   ray actors (was 0).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_moved_element_rays_stay_visible

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


def _rendered_ray_actors(inspector) -> int:
    return len(getattr(inspector, "_ray_actor_map", {}) or {})


def _trace(inspector) -> int:
    inspector.show_rays_var.set(True)
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    try:
        inspector._trace_live_now()
    except Exception:
        pass
    inspector.update_idletasks()
    return _rendered_ray_actors(inspector)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    # A -- source contract (fixture-free).
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    try:
        src = inspect.getsource(ThreeDSceneToolsMixin._iter_3d_scene_ray_records)
    except Exception as exc:
        src = ""
        notes.append(f"FAIL: cannot read _iter_3d_scene_ray_records source: {exc!r}")
        passed = False
    if src and "visible_paths if visible_paths else scene_paths" not in src:
        notes.append("FAIL: _iter_3d_scene_ray_records lost the all-hidden fallback (clipped filter can blank the trace)")
        passed = False

    if not PRESCRIPTION.exists():
        notes.append("SKIP: bug-0022 repro prescription unavailable")
        return passed, notes

    # B -- render: moving the cube off-axis must not blank the trace.
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
        settings = dict(getattr(module, "SETTINGS", {}) or {})
        cube_spec = surfaces[CUBE_ROW] if CUBE_ROW < len(surfaces) else {}
        advanced = (cube_spec.get("advanced", {}) or {}) if isinstance(cube_spec, dict) else {}
        source_text = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
        if not source_text or not _resolve_project_file_path(source_text).exists():
            notes.append("SKIP: beam-splitter cube source STEP unavailable")
            return passed, notes

        if not reuse:
            from KrakenOS.UI.layout_editor import KrakenLayoutEditor
            from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
            own_app = True

        app.rows = _rows_from_layout_info({"surfaces": surfaces})
        try:
            app._regenerate_missing_optical_solid_caches()
        except Exception:
            pass
        app._apply_layout_settings(settings)
        # The bug only manifests with the clipped-ray filter active.
        app.show_clipped_rays_var.set(False)
        app._sync_table()

        before = _trace(inspector)
        if before <= 0:
            notes.append(f"SKIP: baseline trace rendered no rays ({before}) -- cannot exercise the move")
            return passed, notes

        try:
            inspector._apply_scene_placement_translate_handle(CUBE_ROW, "x", -55.0)
        except Exception as exc:
            notes.append(f"FAIL: placement translate raised {exc!r}")
            passed = False
            return passed, notes

        after = _trace(inspector)
        if after <= 0:
            notes.append(f"FAIL: shifting the beam-splitter cube off-axis blanked the trace (rendered {before} -> {after} rays)")
            passed = False
        elif verbose:
            notes.append(f"rendered rays in-place={before}, after off-axis move={after} (stayed visible)")

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
        print("[PASS] bugs/0022: moving an element off the beam keeps the traced rays visible")
        return 0
    print("[FAIL] bugs/0022 moved-element ray-visibility guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
