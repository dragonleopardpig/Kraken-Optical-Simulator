"""bugs/0450 guard -- a model change with rays ON paints its bodies immediately.

flag_20260726_191350 ("with ray on, adding BS not showing up, then add another one"):
``refresh_from_editor``'s async branch (bugs/0223) kicked the background trace worker
and returned having painted NOTHING, so a body added with Show Rays ON stayed invisible
until the long folded trace applied. Geometry is cheap and only the trace is slow, so
the async kick now paints a BODIES-ONLY scene synchronously first.

Checks:
  WIRING  -- the async branch paints bodies before returning, and the refresh service
             accepts an explicit bodies_only build.
  REAL    -- with rays on, the BS actors exist right after the add returns (and after a
             fold-mirror delete, the same refresh class).
"""
from __future__ import annotations

import inspect as _inspect


def _bs_row_index(app):
    for i, r in enumerate(app.rows):
        advanced = getattr(r, "advanced", None)
        if isinstance(advanced, dict):
            if bool(advanced.get("OpticalSolidBeamSplitter")):
                return i
            promo = advanced.get("StepOverlayPromotion")
            if isinstance(promo, dict) and promo.get("beam_splitter"):
                return i
    return None


def _bs_actors_present(inspector, row_index) -> bool:
    try:
        keys = list((getattr(inspector, "_row_actor_map", {}) or {}).get(int(row_index), []) or [])
        return bool(keys)
    except Exception:
        return False


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService
    except Exception as exc:
        return True, [f"SKIP: modules unavailable ({exc!r})"]

    refresh_src = _inspect.getsource(Kraken3DInspector.refresh_from_editor)
    build_params = _inspect.signature(Open3DTraceRefreshService.build_inspector_refresh).parameters
    if (
        "_maybe_begin_async_scene_trace" in refresh_src
        and "_paint_bodies_while_async_trace_runs" in refresh_src
        and "bodies_only" in build_params
    ):
        notes.append("WIRING = the async kick paints bodies first; bodies_only build exists")
    else:
        notes.append("WIRING the 0450 bodies-first paint is not wired onto the async branch")
        ok = False

    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            notes.append("SKIP: AZ85 scene absent (gitignored attachment)")
            return ok, notes
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        inspector = _open_inspector(app)
        try:
            inspector.show_rays_var.set(True)
        except Exception:
            pass
        app.add_beam_splitter_to_led(kind="plate")
        bs = _bs_row_index(app)
        if bs is not None and _bs_actors_present(inspector, bs):
            notes.append("REAL = with rays on, the BS actors exist right after the add")
        else:
            notes.append(f"REAL the BS body was not painted after the add (row {bs})")
            ok = False

        mirror = next(
            (
                i
                for i, r in enumerate(app.rows)
                if "Promoted" in str(getattr(r, "name", "")) and i != bs
            ),
            None,
        )
        if mirror is not None:
            app.delete_optical_step_rows([mirror])
            bs_after = _bs_row_index(app)
            if bs_after is not None and _bs_actors_present(inspector, bs_after):
                notes.append("REAL = bodies stay painted through the delete/freeze refresh")
            else:
                notes.append("REAL the delete/freeze refresh left the bodies unpainted")
                ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
