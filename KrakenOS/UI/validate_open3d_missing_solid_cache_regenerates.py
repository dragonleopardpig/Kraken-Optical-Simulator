"""Guard for bugs/0021 -- a missing promoted-solid cache must regenerate from
its source STEP and render, never blank the whole Open 3D view.

Regression context
------------------
A promoted optical solid stores a *derived* body mesh in ``Solid_3d_stl`` plus
the original CAD in ``OpticalSolidSourcePath``. The cache used to live in
``~/.cache/krakenos`` (machine-local, not synced), so opening the layout on
another machine found the cache missing. Two things then went wrong:

1. ``Prerequisites3D.pv.read(Solid_3d_stl)`` raised ``FileNotFoundError`` and
   aborted the *entire* system build -- every surface vanished, the whole 3D
   view went blank (not just the one solid).
2. The missing-assets dialog complained about the derived ``.stl`` cache rather
   than the source STEP, and a plain Skip left the scene blank.

The fix (bugs/0021):

* the CAD cache lives under the synced ``attachment/`` folder now;
* on open, a missing ``Solid_3d_stl`` whose ``OpticalSolidSourcePath`` is present
  is silently regenerated from that source (stored project-relative);
* the missing-assets scan no longer flags a regenerable derived cache -- it
  targets the source STEP, which the dialog regenerates from on relocate;
* a still-unrecoverable ``Solid_3d_stl`` is neutralised to ``"None"`` at system
  build (analytic fallback) so the scene renders a placeholder, never blank.

Checks
------
Fixture-free (always run):
  A. ``scan_missing_assets`` does NOT flag ``Solid_3d_stl`` when its source STEP
     is present (it is regenerable); it DOES flag ``OpticalSolidSourcePath``
     when the source itself is gone.

Editor-backed (need a display; SKIP without one):
  B. the system build neutralises a missing ``Solid_3d_stl`` (no source) to
     ``"None"`` instead of carrying the dead path into ``pv.read``.

Render (need the cube's source STEP, an Open 3D fixture; SKIP when absent):
  C. opening the machine-vision prescription with the cache missing regenerates
     ``Solid_3d_stl`` from the source STEP (path now resolves, is project-
     relative, and is no longer the old ~/.cache path);
  D. the rebuilt scene is NOT blank -- the file-backed cube row draws actors.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_missing_solid_cache_regenerates

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# Never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESCRIPTION = PROJECT_ROOT / "attachment" / "machine_vision_150mm_measured_test.py"
CUBE_ROW = 6
_LEGACY_CACHE_HINT = ".cache"


def _scan_checks(notes: list[str]) -> bool:
    """Check A: the scan treats the source STEP -- not the derived cache -- as
    the dependency. Fixture-free (synthetic rows, temp files)."""
    from KrakenOS.UI.surface_table_model import SurfaceRow
    from KrakenOS.UI.services.missing_assets_scan import scan_missing_assets

    ok = True
    with tempfile.TemporaryDirectory() as td:
        present_step = Path(td) / "src.step"
        present_step.write_text("dummy", encoding="utf-8")
        missing_stl = str(Path(td) / "nope_cache.stl")  # never created

        # (a) missing cache + PRESENT source -> nothing flagged (regenerable).
        row = SurfaceRow(
            surface="Standard",
            advanced={"Solid_3d_stl": missing_stl, "OpticalSolidSourcePath": str(present_step)},
        )
        flagged = {a.key for a in scan_missing_assets([row], editor=None)}
        if "Solid_3d_stl" in flagged:
            notes.append("FAIL: scan flagged a regenerable Solid_3d_stl whose source STEP is present")
            ok = False
        if flagged:
            notes.append(f"FAIL: scan flagged {sorted(flagged)} when the source STEP is present (expected none)")
            ok = False

        # (b) missing cache + MISSING source -> the SOURCE is flagged, not the cache.
        missing_step = str(Path(td) / "gone.step")
        row2 = SurfaceRow(
            surface="Standard",
            advanced={"Solid_3d_stl": missing_stl, "OpticalSolidSourcePath": missing_step},
        )
        flagged2 = {a.key for a in scan_missing_assets([row2], editor=None)}
        if "OpticalSolidSourcePath" not in flagged2:
            notes.append("FAIL: scan did not flag a missing source STEP")
            ok = False
        if "Solid_3d_stl" in flagged2:
            notes.append("FAIL: scan flagged the derived cache instead of the missing source STEP")
            ok = False
    return ok


def _safety_net_check(app, notes: list[str]) -> bool:
    """Check B: a missing Solid_3d_stl with no recoverable source is neutralised
    to 'None' at system build so pv.read never sees a dead path."""
    from KrakenOS.UI.surface_table_model import SurfaceRow
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    saved_rows = app.rows
    try:
        app.rows = [
            SurfaceRow(surface="Object", thickness=10.0),
            SurfaceRow(
                surface="Standard",
                thickness=5.0,
                glass="BK7",
                advanced={"Solid_3d_stl": "/no/such/dir/missing_body_0021.stl"},
            ),
            SurfaceRow(surface="Image"),
        ]
        specs = app._serializable_row_specs()
        system = _build_system_from_specs(specs, build=0)
        value = str(getattr(system.SDT_0[1], "Solid_3d_stl", "None"))
        if value != "None":
            notes.append(f"FAIL: missing Solid_3d_stl not neutralised at build (got {value!r})")
            return False
    except Exception as exc:
        notes.append(f"FAIL: safety-net build raised {exc!r}")
        return False
    finally:
        app.rows = saved_rows
    return True


def _render_regenerate_check(app, inspector, notes: list[str]) -> bool:
    """Checks C+D: open the prescription with the cube cache missing; it must
    regenerate from the source STEP (relative path) and render (not blank)."""
    from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info
    from KrakenOS.UI.layout_editor import _resolve_project_file_path
    from KrakenOS.UI.services import cad_cache_paths

    module = _load_layout_module(PRESCRIPTION)
    surfaces = list(getattr(module, "SURFACES", []) or [])
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    cube_spec = surfaces[CUBE_ROW] if CUBE_ROW < len(surfaces) else {}
    advanced = (cube_spec.get("advanced", {}) or {}) if isinstance(cube_spec, dict) else {}
    source_text = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
    if not source_text or not _resolve_project_file_path(source_text).exists():
        notes.append("SKIP: cube source STEP (OpticalSolidSourcePath) unavailable")
        return True

    # Redirect the cache under the project to a throwaway dir so the regenerated
    # path is project-relative AND we don't disturb the real attachment cache.
    saved_cache_dir = cad_cache_paths.CAD_CACHE_DIR
    tmp_cache = PROJECT_ROOT / "attachment" / f".test_regen_cache_{os.getpid()}"
    cad_cache_paths.CAD_CACHE_DIR = tmp_cache
    passed = True
    try:
        app.rows = _rows_from_layout_info({"surfaces": surfaces})
        before = str((app.rows[CUBE_ROW].advanced or {}).get("Solid_3d_stl") or "")
        # Sanity: the prescription's cached STL is genuinely absent here.
        if before and _resolve_project_file_path(before).exists():
            notes.append("SKIP: cube cache already present -- cannot exercise regeneration")
            return True

        app._regenerate_missing_optical_solid_caches()

        after = str((app.rows[CUBE_ROW].advanced or {}).get("Solid_3d_stl") or "")
        if not after or not _resolve_project_file_path(after).exists():
            notes.append(f"FAIL: cube Solid_3d_stl did not regenerate (after={after!r})")
            passed = False
        else:
            if os.path.isabs(after):
                notes.append(f"FAIL: regenerated cache path is not project-relative ({after})")
                passed = False
            if _LEGACY_CACHE_HINT in after.split(os.sep):
                notes.append(f"FAIL: regenerated cache still points into a ~/.cache path ({after})")
                passed = False

        app._apply_layout_settings(settings)
        app._sync_table()
        inspector.show_rays_var.set(False)
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks()
        inspector.update()

        try:
            total = int(inspector._renderer.GetViewProps().GetNumberOfItems())
        except Exception:
            total = 0
        cube_actors = len(inspector._row_actor_map.get(CUBE_ROW, []) or [])
        if total <= 0:
            notes.append("FAIL: scene is blank after regeneration (0 renderer actors)")
            passed = False
        if cube_actors <= 0:
            notes.append(f"FAIL: file-backed cube row {CUBE_ROW} drew no actors after regeneration")
            passed = False
    except Exception as exc:
        notes.append(f"FAIL: render/regeneration raised {exc!r}")
        passed = False
    finally:
        cad_cache_paths.CAD_CACHE_DIR = saved_cache_dir
        shutil.rmtree(tmp_cache, ignore_errors=True)
    return passed


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    # A -- fixture-free scan behaviour.
    if not _scan_checks(notes):
        passed = False

    if not PRESCRIPTION.exists():
        notes.append("SKIP: bug-0021 repro prescription unavailable")
        return passed, notes

    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    reuse = app is not None and inspector is not None
    xvfb_proc = None
    if not reuse:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            notes.append(f"SKIP: cannot render ({env_err})")
            return passed, notes

    own_app = False
    try:
        if not reuse:
            from KrakenOS.UI.layout_editor import KrakenLayoutEditor
            from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
            own_app = True

        # B -- safety-net neutralisation.
        if not _safety_net_check(app, notes):
            passed = False

        # C + D -- regenerate from source and render.
        if not _render_regenerate_check(app, inspector, notes):
            passed = False

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
        print("[PASS] bugs/0021: missing solid cache regenerates from source; scene never blanks")
        return 0
    print("[FAIL] bugs/0021 missing-solid-cache guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
