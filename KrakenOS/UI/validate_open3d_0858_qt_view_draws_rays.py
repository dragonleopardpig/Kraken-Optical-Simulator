"""Display-free guard: the Qt viewport draws the traced light (bugs/0858,
docs/design_qt_migration.md phase 2).

A view that shows the glass but not the light is a CAD view. The rays come from the model's own
display pipeline -- the same bounding, inset and per-ray styling the Tk 3D view uses -- because
those steps carry physics: `_bounded_3d_ray_points_for_display` is what makes a ray that MISSES
the detector visibly miss instead of stopping short, and the terminal style is what says whether
it landed.

The Qt half runs in a SUBPROCESS on the xcb platform and needs a DISPLAY; without one, or without
PySide6, the R sections report SKIP.

  R1 one actor per ray record the model yields, recomputed independently through the same helpers
  R2 the drawn geometry is the BOUNDED display polyline, point for point -- not the raw ray
     points, which is what would silently break the missed-ray invariant
  R3 colour, opacity and width come from `_ray_terminal_3d_style`, and a ray is drawn unlit
  R4 the elements and the rays come from ONE system build per redraw -- drawn light must belong
     to the drawn glass (and a second build would double the cost of every refresh)
  R5 View -> Show Rays hides only the rays, and a redraw honours the menu's current state
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def _expected_ray_lines(editor, rays, bundle) -> list[tuple[int, tuple]]:
    """Recompute what the viewport should have drawn, through the model's own helpers."""
    from KrakenOS.UI.scene_projector import scene_display_center_radius

    centre, radius = scene_display_center_radius(bundle)
    paths = editor._scene_ray_path_by_index(bundle)
    inset = editor._ray_vertex_display_inset(radius)
    expected: list[tuple[int, tuple]] = []
    for ray_index, colour, points, terminal_status in editor._iter_3d_scene_ray_records(
            rays, bundle):
        path = paths.get(int(ray_index))
        display_points, _bounded = editor._bounded_3d_ray_points_for_display(
            points, centre, radius, terminal_status=terminal_status,
            terminal_target=editor._missed_detector_target_for_path(bundle, path),
            terminal_direction=editor._terminal_display_direction_for_path(path))
        line = editor._ray_segment_mesh_for_3d_display(display_points, vertex_inset=inset)
        if line is None or int(getattr(line, "n_points", 0)) < 2:
            continue
        style = editor._ray_terminal_3d_style(colour, terminal_status)
        expected.append((int(line.GetNumberOfPoints()),
                         tuple(round(float(v), 6) for v in line.GetBounds()),
                         tuple(round(float(c), 6) for c in style["line_color"]),
                         round(float(style["line_opacity"]), 6),
                         round(float(style["line_width"]), 6)))
    return expected


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.viewport import PREVIEW_SAMPLING

    rows: list[list] = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()

    # ---- R4 one build per redraw ---------------------------------------------------------------
    editor = window.editor
    builds = {"count": 0}
    real_build = editor._build_preview_system_rays_bundle

    def counted(*args, **kwargs):
        builds["count"] += 1
        return real_build(*args, **kwargs)

    editor._build_preview_system_rays_bundle = counted
    try:
        window.load_layout_path(SCENE)
        app.processEvents()
        drawn = window.refresh_from_model()
        builds_per_redraw = builds["count"]
    finally:
        del editor._build_preview_system_rays_bundle
    viewport = window.viewport
    row("R4", builds_per_redraw == 2 and drawn["error"] is None,
        f"the load and the redraw built the system once each ({builds_per_redraw} builds for 2 "
        f"redraws), so each frame's rays and elements come from the same traced system")

    # ---- R1 / R2 / R3 against an independent recomputation --------------------------------------
    system, rays, bundle = editor._build_preview_system_rays_bundle(
        sampling_mode=PREVIEW_SAMPLING, update_state=False)
    expected = _expected_ray_lines(editor, rays, bundle)
    actual = []
    for actor in viewport.ray_actors:
        mesh = actor.GetMapper().GetInput()
        prop = actor.GetProperty()
        actual.append((int(mesh.GetNumberOfPoints()),
                       tuple(round(float(v), 6) for v in mesh.GetBounds()),
                       tuple(round(float(c), 6) for c in prop.GetColor()),
                       round(float(prop.GetOpacity()), 6),
                       round(float(prop.GetLineWidth()), 6)))
    row("R1", len(actual) == len(expected) > 0 and drawn["rays"] == len(actual),
        f"{len(actual)} ray actors for the {len(expected)} ray records the model yields "
        f"(the window reported {drawn['rays']})")

    geometry_matches = [a[:2] == b[:2] for a, b in zip(actual, expected)]
    first_bad = next((i for i, same in enumerate(geometry_matches) if not same), None)
    row("R2", all(geometry_matches) and geometry_matches,
        f"every ray's drawn polyline equals the model's BOUNDED display polyline, point count and "
        f"bounds" + ("" if first_bad is None else
                     f" -- first mismatch at {first_bad}: {actual[first_bad][:2]} vs "
                     f"{expected[first_bad][:2]}"))

    styles_match = [a[2:] == b[2:] for a, b in zip(actual, expected)]
    unlit = all(not bool(actor.GetProperty().GetLighting()) for actor in viewport.ray_actors)
    row("R3", all(styles_match) and styles_match and unlit,
        f"colour, opacity and width of all {len(actual)} rays come from the terminal style "
        f"(sample {actual[0][2:] if actual else None}) and every ray is drawn unlit ({unlit})")

    # ---- R5 the toggle --------------------------------------------------------------------------
    action = window.action_manager["show_rays"]
    action.setChecked(False)
    window.toggle_rays_action(False)
    app.processEvents()
    hidden = [bool(actor.GetVisibility()) for actor in viewport.ray_actors]
    others_visible = all(bool(actor.GetVisibility()) for actor in viewport.element_actors)
    window.refresh_from_model()  # a redraw must not bring them back
    after_redraw = [bool(actor.GetVisibility()) for actor in viewport.ray_actors]
    action.setChecked(True)
    window.toggle_rays_action(True)
    shown = [bool(actor.GetVisibility()) for actor in viewport.ray_actors]
    row("R5", not any(hidden) and others_visible and not any(after_redraw) and all(shown)
        and len(shown) > 0,
        f"Show Rays off hid all {len(hidden)} rays and left the elements visible "
        f"({others_visible}); a redraw honoured the menu ({not any(after_redraw)}); on again "
        f"showed all {len(shown)}")

    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the viewport needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0858_qt_view_draws_rays import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Qt subprocess", False, "timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Qt rays", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP R1-R5: {rows[0][2]}")
    else:
        for name, passed, detail in rows:
            ok(passed, f"{name}: {detail}")
    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
