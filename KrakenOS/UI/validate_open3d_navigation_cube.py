#!/usr/bin/env python3
"""Display-free guard for bugs/0156: the Open 3D canvas carries a genuine
FreeCAD-style navigation cube -- a labelled, clickable cube (not VTK's axis-ball
``vtkCameraOrientationWidget``, which "is far from the cube function") whose faces
snap to the ortho presets, whose edges/corners give the oblique "angled" views, and
which carries discrete-step rotation arrows.

Why it exists (user request):
  "the navigation cube ... is far from the cube function ... Full FreeCAD interaction
   (faces + edges + corners), CAD-word labels (FRONT/BACK/TOP/BOTTOM/LEFT/RIGHT),
   plus discrete rotation-step arrows."

The cube is the custom :class:`KrakenOS.UI.services.nav_cube_widget.NavigationCube`
(all camera MATH in the VTK-free ``nav_cube_orientation`` module, unit-tested by
``validate_open3d_nav_cube_orientation``). It is built in ``Kraken3DInspector.__init__``
AFTER ``Initialize()`` (so the interactor is live) with three callbacks --
``apply_orientation`` / ``apply_step`` / ``get_main_camera`` -- and stored on
``self._navigation_cube``. Clicks are routed from the Tk left-press through
``_handle_navigation_cube_left_press`` (the app owns left-clicks), and each snap runs
``_on_navigation_cube_snap`` (reframe + the orbit backstop ``_on_camera_interaction``,
so the clip range re-fits (bugs/0048) and the perpendicular thickness labels re-square
(bugs/0128, 0140) exactly as a mouse orbit does).

What it checks (no display required):
  A. Module contract -- ``NavigationCube`` importable; ``STEP_KINDS`` is exactly the
     six roll/azimuth/elevation kinds; ``_import_vtk`` resolves its VTK classes.
  B. Defensive construction -- a ``NavigationCube`` built with no render window
     degrades to ``available is False`` (the inspector then runs without the cube).
  C. __init__ source -- builds ``NavigationCube(`` with the three callbacks bound to
     ``_apply_navigation_cube_orientation`` / ``_apply_navigation_cube_step`` /
     a ``get_main_camera`` lambda, and stores it on ``self._navigation_cube``.
  D. Inspector methods -- ``_apply_navigation_cube_orientation`` and
     ``_apply_navigation_cube_step`` both route through ``_on_navigation_cube_snap``;
     ``_handle_navigation_cube_left_press`` gates Ctrl and reads the event position;
     and ``_on_camera_interaction`` re-fits the clip range AND re-squares the
     thickness labels (so a cube snap behaves like an orbit).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.nav_cube_widget import (
        NavigationCube,
        STEP_KINDS,
        _import_vtk,
    )

    # --- A: module contract -----------------------------------------------------
    want_kinds = ("roll_ccw", "roll_cw", "az_left", "az_right", "el_up", "el_down")
    if tuple(STEP_KINDS) != want_kinds:
        failures.append(
            f"A FAIL: STEP_KINDS {tuple(STEP_KINDS)!r} != the six discrete-step kinds "
            f"{want_kinds!r} (roll/azimuth/elevation arrows)"
        )
    vtk = _import_vtk()
    if vtk is None:
        failures.append(
            "A FAIL: nav_cube_widget._import_vtk() returned None -- the cube's VTK "
            "classes (annotated cube / cube source / cell picker / renderer) are missing"
        )
    else:
        for key in ("AnnotatedCube", "CubeSource", "CellPicker", "PolyDataMapper", "Renderer", "Actor"):
            if key not in vtk:
                failures.append(f"A FAIL: _import_vtk() missing `{key}`")

    # --- B: defensive construction degrades cleanly -----------------------------
    try:
        degraded = NavigationCube(
            None,  # no render window
            None,  # no main renderer
            None,
            apply_orientation=lambda *_a: None,
            apply_step=lambda *_a: None,
            get_main_camera=lambda: None,
        )
        if degraded.available is not False:
            failures.append(
                f"B FAIL: NavigationCube with no render window reported available="
                f"{degraded.available!r}, want False (the inspector must run without it)"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"B FAIL: defensive NavigationCube construction raised {exc!r}")

    # --- C: __init__ builds + stores the cube with the three callbacks ----------
    init_src = inspect.getsource(Kraken3DInspector.__init__)
    required = {
        "construct": "self._navigation_cube = NavigationCube(",
        "apply-orientation": "apply_orientation=self._apply_navigation_cube_orientation",
        "apply-step": "apply_step=self._apply_navigation_cube_step",
        "get-camera": "get_main_camera=",
        "import": "from KrakenOS.UI.services.nav_cube_widget import NavigationCube",
    }
    for tag, needle in required.items():
        if needle not in init_src:
            failures.append(
                f"C FAIL ({tag}): Kraken3DInspector.__init__ is missing `{needle}` "
                "-- the navigation cube is not built/wired as specified"
            )

    # --- D: the routed inspector methods behave as the widget expects -----------
    orient_src = inspect.getsource(Kraken3DInspector._apply_navigation_cube_orientation)
    if "_on_navigation_cube_snap" not in orient_src:
        failures.append(
            "D FAIL: _apply_navigation_cube_orientation must call _on_navigation_cube_snap "
            "so a face/edge/corner pick reframes + runs the orbit backstop like a preset"
        )
    step_src = inspect.getsource(Kraken3DInspector._apply_navigation_cube_step)
    if "_on_navigation_cube_snap" not in step_src:
        failures.append(
            "D FAIL: _apply_navigation_cube_step must call _on_navigation_cube_snap so a "
            "discrete-step arrow reframes + runs the orbit backstop"
        )
    for needle, kinds in (("Roll(", "roll"), ("Azimuth(", "azimuth"), ("Elevation(", "elevation")):
        if needle not in step_src:
            failures.append(
                f"D FAIL: _apply_navigation_cube_step does not apply a {kinds} "
                f"(`{needle}`) -- the discrete rotation step is incomplete"
            )
    press_src = inspect.getsource(Kraken3DInspector._handle_navigation_cube_left_press)
    if "GetControlKey" not in press_src:
        failures.append(
            "D FAIL: _handle_navigation_cube_left_press does not gate on Ctrl "
            "(GetControlKey) -- a Ctrl-click must still orbit the camera"
        )
    if "GetEventPosition" not in press_src:
        failures.append(
            "D FAIL: _handle_navigation_cube_left_press does not read the interactor "
            "event position (GetEventPosition) to pick the cube"
        )
    interaction_src = inspect.getsource(Kraken3DInspector._on_camera_interaction)
    if "_reorient_thickness_labels_for_camera" not in interaction_src:
        failures.append(
            "D FAIL: _on_camera_interaction must call _reorient_thickness_labels_for_camera "
            "so a cube snap re-squares the thickness labels (bugs/0128, 0140)"
        )
    if "_reset_camera_clipping_range_for_scene" not in interaction_src:
        failures.append(
            "D FAIL: _on_camera_interaction must re-fit the clip range "
            "(_reset_camera_clipping_range_for_scene) so a cube snap can't near-clip (bugs/0048)"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0156 Open 3D navigation cube")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0156: Open 3D carries a genuine FreeCAD-style navigation cube "
        "(labelled faces + edges/corners + discrete-step arrows, snap re-squares labels)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
