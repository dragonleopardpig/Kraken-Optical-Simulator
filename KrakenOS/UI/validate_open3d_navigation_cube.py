#!/usr/bin/env python3
"""Display-free guard for bugs/0156: the Open 3D canvas carries a FreeCAD-style
interactive navigation cube (``vtkCameraOrientationWidget``) so the user can rotate
the canvas view by clicking a face/edge/corner handle -- including reversing the
look direction (the user's ask: object plane at NW-facing-SE -> SE-facing-NW).

Why it exists (user request):
  "refer attachment/2D.png, can we have this kind of navigation ball? I need to
   rotate the canvas view ... add a Navigation Ball just like FreeCAD."
  ("axis-handle interactive cube" chosen over the labelled-faces variant.)

The widget is the native VTK orientation cube. It is wired through the same lazy
``_load_3d_backends`` plumbing as the passive axes marker, then created in
``Kraken3DInspector.__init__`` AFTER ``Initialize()`` (so the interactor is live
when ``On()`` registers the handle observers). It is anchored to the UPPER-RIGHT so
it never collides with the passive axes marker in the lower-left, animation is left
OFF (instant snap, no embedded-Tk timer dependency -- matching the preset buttons),
and each snap routes through the existing orbit backstop ``_on_camera_interaction``
so the clip range re-fits (bugs/0048) and the perpendicular thickness labels
re-square for the new basis (bugs/0128, 0140) exactly as a mouse orbit does.

What it checks (no display required):
  A. Import wiring -- ``_load_3d_backends`` resolves ``vtkCameraOrientationWidget``
     to the real VTK class on BOTH layout_editor and the open3d_inspector re-export.
  B. Source contract -- ``Kraken3DInspector.__init__`` builds the widget with
     ``SetParentRenderer`` + ``AnchorToUpperRight`` + ``SetAnimate(False)`` + ``On()``,
     stores it on ``self._camera_orientation_widget``, and registers BOTH
     Interaction/EndInteraction observers bound to ``_on_camera_interaction``.
  C. Observer target -- ``_on_camera_interaction`` re-fits the clip range AND
     re-squares the thickness labels, so a cube snap behaves like an orbit (removing
     either call fails here).
  D. Behavioural VTK API -- the exact construction the inspector relies on
     (``SetParentRenderer`` on a bare renderer, ``AnchorToUpperRight``,
     ``SetAnimate(False)``) runs without a display and leaves animation OFF.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.UI import layout_editor as layout_editor_module
    from KrakenOS.UI import open3d_inspector as open3d_inspector_module
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    # --- A: import wiring resolves the real VTK class on both modules ----------
    open3d_inspector_module._load_3d_backends()
    le_cls = getattr(layout_editor_module, "vtkCameraOrientationWidget", None)
    oi_cls = getattr(open3d_inspector_module, "vtkCameraOrientationWidget", None)
    if le_cls is None:
        failures.append(
            "A FAIL: layout_editor._load_3d_backends did not resolve "
            "vtkCameraOrientationWidget (import plumbing broken)"
        )
    if oi_cls is None:
        failures.append(
            "A FAIL: open3d_inspector did not re-export vtkCameraOrientationWidget "
            "from layout_editor (re-export plumbing broken)"
        )
    if le_cls is not None and oi_cls is not None and le_cls is not oi_cls:
        failures.append(
            "A FAIL: the inspector re-export is a DIFFERENT class object than "
            "layout_editor's -- the lazy assignment is not threading through"
        )

    # --- B: __init__ builds + enables + observes the widget -------------------
    init_src = inspect.getsource(Kraken3DInspector.__init__)
    required = {
        "construct": "self._camera_orientation_widget = vtkCameraOrientationWidget()",
        "parent": "self._camera_orientation_widget.SetParentRenderer(self._renderer)",
        "anchor": "AnchorToUpperRight()",
        "no-animate": "self._camera_orientation_widget.SetAnimate(False)",
        "enable": "self._camera_orientation_widget.On()",
        "observe-interaction": '"InteractionEvent", self._on_camera_interaction',
        "observe-end": '"EndInteractionEvent", self._on_camera_interaction',
    }
    for tag, needle in required.items():
        if needle not in init_src:
            failures.append(
                f"B FAIL ({tag}): Kraken3DInspector.__init__ is missing `{needle}` "
                "-- the navigation cube is not built/enabled/observed as specified"
            )

    # --- C: the snap observer re-fits clip + re-squares labels like an orbit ---
    interaction_src = inspect.getsource(Kraken3DInspector._on_camera_interaction)
    if "_reorient_thickness_labels_for_camera" not in interaction_src:
        failures.append(
            "C FAIL: _on_camera_interaction must call "
            "_reorient_thickness_labels_for_camera so a cube snap re-squares the "
            "thickness labels for the new basis (bugs/0128, 0140)"
        )
    if "_reset_camera_clipping_range_for_scene" not in interaction_src:
        failures.append(
            "C FAIL: _on_camera_interaction must re-fit the clip range "
            "(_reset_camera_clipping_range_for_scene) so a cube snap can't near-clip "
            "the scene (bugs/0048)"
        )

    # --- D: the construction path runs display-free and keeps animation off ----
    if oi_cls is not None:
        try:
            import vtk

            widget = oi_cls()
            widget.SetParentRenderer(vtk.vtkRenderer())
            rep = widget.GetRepresentation()
            rep.AnchorToUpperRight()
            widget.SetAnimate(False)
            if bool(widget.GetAnimate()):
                failures.append(
                    "D FAIL: SetAnimate(False) did not stick -- the snap would "
                    "depend on the embedded-Tk animation timer"
                )
            if rep is None or "CameraOrientationRepresentation" not in type(rep).__name__:
                failures.append(
                    f"D FAIL: unexpected representation type {type(rep).__name__!r}"
                )
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(f"D FAIL: display-free construction raised {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0156 Open 3D navigation cube")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0156: Open 3D carries an interactive navigation cube "
        "(upper-right, no-animate, snap re-squares labels like an orbit)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
