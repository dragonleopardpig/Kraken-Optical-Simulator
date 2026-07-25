"""Guard: a selected element's move/rotate gizmo renders always-on-top.

bugs/0112: when an element is selected, its move/rotate gizmo (rotation arcs +
arrowheads + translate arrows) could be **buried** behind an adjacent body -- the
handle you needed to grab was hidden behind, e.g., a camera body sitting next to
the selected optical solid. VTK has no clean per-actor depth-test disable, so the
gizmo handles now render in a dedicated **overlay renderer**: a second renderer on
its own layer that shares the main camera, composites over the scene colour
(``PreserveColorBuffer``) and clears its own depth buffer
(``PreserveDepthBuffer`` off) so the handles always draw in front. Per-renderer
picking keeps a buried handle grabbable (the overlay is picked first).

This validator has two parts:

* ``run_checks`` -- display-free source/structure assertions that the overlay
  renderer is built with the right layer/preserve flags, that every gizmo-handle
  ``_add_mesh_actor`` call routes to the overlay (``overlay_on_top=True``), that
  the pick/remove helpers exist, that the full refresh clears the overlay, and
  that the interaction service picks the overlay first.
* ``render_overlay_proof`` -- a headless image-snapshot (needs a GL context /
  Xvfb) that reproduces the inspector's exact layered setup with an occluder in
  the main layer and a gizmo actor geometrically **behind** it in the overlay,
  and asserts the gizmo pixel wins (on top), while the same actor placed in the
  main layer stays occluded. Run from ``main`` when a display is available.

Penta phase 102 (baseline -> 103) runs ``run_checks`` only (no rendering, so the
phase stays safe inside the validator marathon).
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path


def _module_source(module) -> str:
    path = inspect.getsourcefile(module) or inspect.getfile(module)
    return Path(path).read_text(encoding="utf-8")


def run_checks() -> list[tuple[str, bool, str]]:
    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.services import open3d_step_rotation_handles
    from KrakenOS.UI.services import open3d_scene_refresh
    from KrakenOS.UI.services import open3d_interaction

    results: list[tuple[str, bool, str]] = []

    inspector_src = _module_source(open3d_inspector)
    handles_src = _module_source(open3d_step_rotation_handles)
    refresh_src = _module_source(open3d_scene_refresh)
    interaction_src = _module_source(open3d_interaction)

    # 1) the overlay renderer is declared and built with always-on-top flags.
    declared = "self._gizmo_overlay_renderer = None" in inspector_src
    built = all(
        tok in inspector_src
        for tok in (
            "self._gizmo_overlay_renderer = vtkRenderer()",
            "self._gizmo_overlay_renderer.SetLayer(2)",
            "self._gizmo_overlay_renderer.SetActiveCamera(self._renderer.GetActiveCamera())",
            "self._gizmo_overlay_renderer.SetPreserveColorBuffer(True)",
            "self._gizmo_overlay_renderer.SetPreserveDepthBuffer(False)",
            "render_window.SetNumberOfLayers(3)",
            "render_window.AddRenderer(self._gizmo_overlay_renderer)",
        )
    )
    results.append(
        ("overlay renderer declared + built always-on-top (shared camera, preserve colour, clear depth)",
         declared and built, f"declared={declared}, built={built}")
    )

    # 2) _add_mesh_actor takes overlay_on_top and routes those actors to the overlay.
    add_src = inspect.getsource(open3d_inspector.Kraken3DInspector._add_mesh_actor)
    has_param = "overlay_on_top: bool = False" in add_src
    routes = (
        "if overlay_on_top and self._gizmo_overlay_renderer is not None:" in add_src
        and "self._gizmo_overlay_renderer.AddActor(actor)" in add_src
    )
    results.append(
        ("_add_mesh_actor routes overlay_on_top actors to the overlay renderer",
         has_param and routes, f"param={has_param}, routes={routes}")
    )

    # 3) gizmo-priority pick + dual-renderer remove helpers exist.
    has_pick = hasattr(open3d_inspector.Kraken3DInspector, "_pick_actor_with_gizmo_overlay")
    has_remove = hasattr(open3d_inspector.Kraken3DInspector, "_remove_actor_from_renderers")
    pick_src = inspect.getsource(open3d_inspector.Kraken3DInspector._pick_actor_with_gizmo_overlay) if has_pick else ""
    pick_overlay_first = "Pick(x, y, 0.0, overlay)" in pick_src
    results.append(
        ("inspector defines gizmo-priority pick + dual-renderer remove helpers",
         has_pick and has_remove and pick_overlay_first,
         f"pick={has_pick}, remove={has_remove}, overlay_first={pick_overlay_first}")
    )

    # 4) every STEP rotation-handle actor (arc + arrowhead + translate arrow) is on the overlay.
    handle_overlay = handles_src.count("overlay_on_top=True")
    handle_remove = "inspector._remove_actor_from_renderers(actor)" in handles_src
    no_bare_remove = "inspector._renderer.RemoveActor(actor)" not in handles_src
    results.append(
        ("STEP rotation-handle service: all 3 handle kinds on the overlay + dual-renderer remove",
         handle_overlay >= 3 and handle_remove and no_bare_remove,
         f"overlay_on_top={handle_overlay}, helper_remove={handle_remove}, no_bare_remove={no_bare_remove}")
    )

    # 5) placement (native-row) translate + rotate handles route to the overlay too.
    place_overlay = inspector_src.count("overlay_on_top=True")
    results.append(
        ("placement translate + rotate handles route to the overlay (>=3 sites)",
         place_overlay >= 3, f"overlay_on_top sites in inspector={place_overlay}")
    )

    # 6) the full scene refresh clears the overlay layer alongside the main one.
    refresh_clears = "self._gizmo_overlay_renderer.RemoveAllViewProps()" in refresh_src
    results.append(
        ("full refresh clears the gizmo overlay (no stale stacked handles)",
         refresh_clears, f"clears_overlay={refresh_clears}")
    )

    # 7) interaction service picks the overlay first on click + on passive hover.
    press_overlay = 'site="left_click_gizmo"' in interaction_src
    hover_overlay = "getattr(self, \"_gizmo_overlay_renderer\", None) or self._renderer" in interaction_src
    results.append(
        ("interaction service picks the overlay first (click + hover)",
         press_overlay and hover_overlay, f"click={press_overlay}, hover={hover_overlay}")
    )

    return results


def render_overlay_proof(png_path: str | None = None) -> tuple[bool, str]:
    """Reproduce the inspector's layered setup; prove the gizmo draws on top.

    Returns (passed, detail). Needs a GL context (DISPLAY / Xvfb); raises on a
    headless box with no GL, so callers should guard on a display being present.
    """
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    def build(gizmo_on_overlay: bool):
        rw = vtk.vtkRenderWindow()
        rw.SetSize(240, 240)
        rw.SetNumberOfLayers(3)
        main = vtk.vtkRenderer()
        main.SetLayer(0)
        main.SetBackground(1.0, 1.0, 1.0)
        rw.AddRenderer(main)

        # Occluder: a big grey body near the camera (the adjacent element).
        body = vtk.vtkCubeSource()
        body.SetXLength(6.0); body.SetYLength(6.0); body.SetZLength(1.0); body.SetCenter(0, 0, 3)
        bm = vtk.vtkPolyDataMapper(); bm.SetInputConnection(body.GetOutputPort())
        ba = vtk.vtkActor(); ba.SetMapper(bm); ba.GetProperty().SetColor(0.6, 0.6, 0.6)
        main.AddActor(ba)

        # Gizmo handle: a saturated red cone geometrically BEHIND the occluder.
        giz = vtk.vtkConeSource()
        giz.SetHeight(2.0); giz.SetRadius(0.8); giz.SetCenter(0, 0, -2); giz.SetResolution(24)
        gm = vtk.vtkPolyDataMapper(); gm.SetInputConnection(giz.GetOutputPort())
        ga = vtk.vtkActor(); ga.SetMapper(gm)
        prop = ga.GetProperty()
        prop.SetColor(0.95, 0.05, 0.05)
        prop.SetInterpolationToFlat(); prop.SetAmbient(0.85); prop.SetDiffuse(0.15)

        # Same flags the inspector uses for the overlay renderer.
        overlay = vtk.vtkRenderer()
        overlay.SetLayer(2)
        overlay.SetActiveCamera(main.GetActiveCamera())
        overlay.SetPreserveColorBuffer(True)
        overlay.SetPreserveDepthBuffer(False)
        rw.AddRenderer(overlay)

        (overlay if gizmo_on_overlay else main).AddActor(ga)

        cam = main.GetActiveCamera()
        cam.SetPosition(0, 0, 16); cam.SetFocalPoint(0, 0, 0); cam.SetViewUp(0, 1, 0)
        main.ResetCamera()
        cam.SetClippingRange(1.0, 40.0)  # cover both depths (gizmo sits behind)
        rw.Render()

        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.ReadFrontBufferOff(); w2i.Update()
        img = w2i.GetOutput(); dx, dy, _ = img.GetDimensions()
        arr = vtk_to_numpy(img.GetPointData().GetScalars()).reshape(dy, dx, -1)
        if png_path and gizmo_on_overlay:
            try:
                writer = vtk.vtkPNGWriter(); writer.SetFileName(str(png_path)); writer.SetInputData(img); writer.Write()
            except Exception:
                pass
        return arr[dy // 2, dx // 2][:3]

    on_top = build(True)      # gizmo in the overlay -> should win
    occluded = build(False)   # same gizmo in the main layer -> should be hidden by grey

    gizmo_wins = bool(int(on_top[0]) > 150 and int(on_top[1]) < 90 and int(on_top[2]) < 90)
    control_occluded = bool(abs(int(occluded[0]) - int(occluded[1])) < 40 and int(occluded[1]) > 120)
    detail = f"overlay center RGB={tuple(int(v) for v in on_top)}, main-layer center RGB={tuple(int(v) for v in occluded)}"
    return (gizmo_wins and control_occluded), detail


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed

    if os.environ.get("DISPLAY"):
        try:
            png = os.environ.get("KRAKEN_GIZMO_OVERLAY_PNG") or "/tmp/gizmo_overlay_on_top.png"
            passed, det = render_overlay_proof(png)
            print(f"render proof: gizmo draws on top of an occluder | {'PASS' if passed else 'FAIL'} | {det}; png={png}")
            ok = ok and passed
        except Exception as exc:  # pragma: no cover - GL/driver dependent
            print(f"render proof skipped (no usable GL context): {exc}")
    else:
        print("render proof skipped (no DISPLAY); run under Xvfb for the image-snapshot proof")

    print("[PASS] gizmo overlay always-on-top wired" if ok else "[FAIL] gizmo overlay on-top regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
