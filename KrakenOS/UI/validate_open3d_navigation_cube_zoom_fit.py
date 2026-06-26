#!/usr/bin/env python3
"""Display-free guard for bugs/0160: clicking the interactive navigation cube
(bugs/0156/0157, ``vtkCameraOrientationWidget``) must zoom-to-extent like the
top-bar preset buttons, instead of leaving the scene tiny.

Why it exists (user report):
  "that little cube navigator, when click, the default zoom is not extent window,
  very small, different from the behaviour from the top bar buttons."

Root cause: the cube snap reorients the camera but PRESERVES the parallel scale
(the orthographic zoom); its observers only ran ``_on_camera_interaction`` (the
orbit backstop), which deliberately never re-fits the zoom (it also runs on mouse
orbits, where auto-zoom would fight the wheel). The fix gives the cube its own
End handler ``_on_navigation_cube_snap`` that reframes via
``_fit_view_to_scene_for_current_orientation`` -- recenter + zoom-to-extent for
the cube's chosen orientation -- then runs the usual backstop and renders.

What it checks (no display required) -- the real ``Kraken3DInspector`` methods
bound to a light fake ``self`` whose fake renderer hands back a fake camera that
records ``SetParallelProjection`` / ``SetParallelScale`` / ``SetPosition`` /
``SetFocalPoint``, with ``_camera_fit_bounds`` returning a known asymmetric box:
  A. AXIS-ALIGNED fit (camera looking -X): turns parallel projection ON and sets
     the parallel scale to the EXACT ``_parallel_scale_for_orthographic_fit`` of
     the box's projected (Z, Y) spans, recenters the focal point on the box
     centre, and preserves the view direction (the cube's orientation is kept).
  B. OBLIQUE fit (Iso-like direction): parallel projection ON, a finite positive
     scale, focal on the box centre, view direction preserved.
  C. ``_on_navigation_cube_snap`` runs the fit FIRST, then ``_on_camera_interaction``
     with an End event, then a render -- in that order.
  D. No renderer / no active camera -> the fit is a safe no-op (returns False,
     touches nothing).
  E. Source contract -- the cube wiring binds ``_on_navigation_cube_snap`` to the
     widget's ``EndInteractionEvent``; the snap consults
     ``_fit_view_to_scene_for_current_orientation`` and ``_on_camera_interaction``;
     and the fit calls ``_parallel_scale_for_orthographic_fit`` +
     ``SetParallelScale``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube_zoom_fit

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


# Camera looking straight down -X (the +yz preset direction): position on +X,
# focal at origin, +Y up. right = (0,0,-1) measures Z; true_up = (0,1,0) measures Y.
_AXIS_POSITION = (200.0, 0.0, 0.0)
_AXIS_FOCAL = (0.0, 0.0, 0.0)
_AXIS_UP = (0.0, 1.0, 0.0)
# An oblique Iso-like direction (no principal axis dominates).
_OBLIQUE_POSITION = (190.0, -110.0, -160.0)
_OBLIQUE_FOCAL = (0.0, 0.0, 0.0)
_OBLIQUE_UP = (0.0, 1.0, 0.0)
# A deliberately ASYMMETRIC, OFF-CENTRE box so the fit math is unambiguous.
_BOUNDS = np.array([-10.0, 30.0, -4.0, 4.0, -25.0, 15.0], dtype=float)
_ASPECT = 1.4


def _unit(vec):
    vec = np.asarray(vec, dtype=float)
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm else vec


class _FakeCamera:
    def __init__(self, position, focal, view_up):
        self._position = tuple(float(c) for c in position)
        self._focal = tuple(float(c) for c in focal)
        self._view_up = tuple(float(c) for c in view_up)
        self.parallel_projection = None
        self.parallel_scale = None

    def GetPosition(self):
        return self._position

    def GetFocalPoint(self):
        return self._focal

    def GetViewUp(self):
        return self._view_up

    def SetPosition(self, *xyz):
        self._position = tuple(float(c) for c in xyz)

    def SetFocalPoint(self, *xyz):
        self._focal = tuple(float(c) for c in xyz)

    def SetParallelProjection(self, flag):
        self.parallel_projection = int(flag)

    def SetParallelScale(self, scale):
        self.parallel_scale = float(scale)


class _FakeRenderer:
    def __init__(self, camera):
        self._camera = camera

    def GetActiveCamera(self):
        return self._camera


def _fit_fake(camera):
    """A light ``self`` carrying just what _fit_view_to_scene_for_current_orientation
    touches: a renderer, the scene bounds, the aspect and the REAL parallel-scale
    helper."""
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    class _FitFake:
        _renderer = _FakeRenderer(camera)

        def _camera_fit_bounds(self):
            return _BOUNDS.copy()

        def _render_aspect(self):
            return _ASPECT

        _parallel_scale_for_orthographic_fit = staticmethod(
            Kraken3DInspector._parallel_scale_for_orthographic_fit
        )

    return _FitFake()


def _call_fit(fake):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    return Kraken3DInspector._fit_view_to_scene_for_current_orientation(fake)


def _expected_fit():
    """The fit the real method must produce for _BOUNDS, regardless of camera
    orientation: recenter on the box centre and size the parallel scale to the
    projected spans."""
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    center = np.array(
        [
            0.5 * (_BOUNDS[0] + _BOUNDS[1]),
            0.5 * (_BOUNDS[2] + _BOUNDS[3]),
            0.5 * (_BOUNDS[4] + _BOUNDS[5]),
        ],
        dtype=float,
    )
    radius = max(
        float(_BOUNDS[1] - _BOUNDS[0]),
        float(_BOUNDS[3] - _BOUNDS[2]),
        float(_BOUNDS[5] - _BOUNDS[4]),
        1.0,
    )
    distance = max(radius * 2.2, 50.0)
    return center, radius, distance, Kraken3DInspector._parallel_scale_for_orthographic_fit


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    center, radius, distance, scale_fn = _expected_fit()

    # --- A: AXIS-ALIGNED fit -- exact scale, recenter, orientation preserved ----
    cam = _FakeCamera(_AXIS_POSITION, _AXIS_FOCAL, _AXIS_UP)
    before_dir = _unit(np.array(cam.GetFocalPoint(), float) - np.array(cam.GetPosition(), float))
    ok = _call_fit(_fit_fake(cam))
    if not ok:
        failures.append("A FAIL: the axis-aligned fit returned False (did not reframe)")
    if cam.parallel_projection != 1:
        failures.append(
            f"A FAIL: parallel projection not enabled (got {cam.parallel_projection!r}) -- "
            "the orthographic zoom-to-extent would not apply"
        )
    # right=(0,0,-1) -> Z span (40); true_up=(0,1,0) -> Y span (8).
    want_scale = scale_fn(40.0, 8.0, _ASPECT)
    if cam.parallel_scale is None or abs(cam.parallel_scale - want_scale) > 1e-6:
        failures.append(
            f"A FAIL: parallel scale {cam.parallel_scale!r} != fit {want_scale:.6f} -- the "
            "cube snap did not zoom-to-extent like the preset buttons (bugs/0160)"
        )
    if float(np.linalg.norm(np.array(cam.GetFocalPoint(), float) - center)) > 1e-6:
        failures.append(
            f"A FAIL: focal point {cam.GetFocalPoint()!r} not recentered on the scene "
            f"centre {center.tolist()!r}"
        )
    after_dir = _unit(np.array(cam.GetFocalPoint(), float) - np.array(cam.GetPosition(), float))
    if float(np.linalg.norm(after_dir - before_dir)) > 1e-9:
        failures.append(
            f"A FAIL: view direction changed {before_dir.tolist()!r} -> {after_dir.tolist()!r} "
            "-- the cube's chosen orientation must be preserved"
        )
    # Position slid back along the view direction by the preset-style distance.
    want_pos = center - before_dir * distance
    if float(np.linalg.norm(np.array(cam.GetPosition(), float) - want_pos)) > 1e-6:
        failures.append(
            f"A FAIL: camera position {cam.GetPosition()!r} != centre - dir*{distance:.1f} "
            f"= {want_pos.tolist()!r}"
        )

    # --- B: OBLIQUE fit -- ON, positive finite scale, recenter, dir preserved ---
    cam = _FakeCamera(_OBLIQUE_POSITION, _OBLIQUE_FOCAL, _OBLIQUE_UP)
    before_dir = _unit(np.array(cam.GetFocalPoint(), float) - np.array(cam.GetPosition(), float))
    ok = _call_fit(_fit_fake(cam))
    if not ok or cam.parallel_projection != 1:
        failures.append("B FAIL: the oblique fit did not enable an orthographic reframe")
    if cam.parallel_scale is None or not (cam.parallel_scale > 0.0) or not np.isfinite(cam.parallel_scale):
        failures.append(f"B FAIL: oblique parallel scale not finite-positive ({cam.parallel_scale!r})")
    if float(np.linalg.norm(np.array(cam.GetFocalPoint(), float) - center)) > 1e-6:
        failures.append("B FAIL: oblique fit did not recenter the focal point on the scene")
    after_dir = _unit(np.array(cam.GetFocalPoint(), float) - np.array(cam.GetPosition(), float))
    if float(np.linalg.norm(after_dir - before_dir)) > 1e-9:
        failures.append("B FAIL: oblique fit changed the view direction (orientation not preserved)")

    # --- C: _on_navigation_cube_snap orchestration: fit -> interaction -> render -
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    class _SnapFake:
        def __init__(self):
            self.log: list = []

        def _fit_view_to_scene_for_current_orientation(self):
            self.log.append("fit")
            return True

        def _on_camera_interaction(self, *args):
            self.log.append(("interaction", args))

        def render(self):
            self.log.append("render")

    snap = _SnapFake()
    Kraken3DInspector._on_navigation_cube_snap(snap)
    kinds = [item if isinstance(item, str) else item[0] for item in snap.log]
    if kinds != ["fit", "interaction", "render"]:
        failures.append(
            f"C FAIL: snap order {kinds!r} != ['fit','interaction','render'] -- the zoom-fit "
            "must run before the orbit backstop and the render"
        )
    else:
        ev_args = snap.log[1][1]
        if not any("End" in str(a) for a in ev_args):
            failures.append(
                f"C FAIL: _on_camera_interaction args {ev_args!r} lack an End event -- the "
                "bugs/0152 view-relative dimensions would not re-place after the snap"
            )

    # --- D: no renderer / no active camera -> safe no-op (returns False) --------
    class _NoRenderer:
        _renderer = None

        def _camera_fit_bounds(self):
            raise AssertionError("must not be reached with no renderer")

    if Kraken3DInspector._fit_view_to_scene_for_current_orientation(_NoRenderer()) is not False:
        failures.append("D FAIL: fit with no renderer did not return False (want a clean no-op)")
    if _call_fit(_fit_fake(None)) is not False:
        failures.append("D FAIL: fit with no active camera did not return False (want a no-op)")

    # --- E: source contract -----------------------------------------------------
    init_src = inspect.getsource(Kraken3DInspector.__init__)
    if '"EndInteractionEvent", self._on_navigation_cube_snap' not in init_src:
        failures.append(
            "E FAIL: the navigation cube does not bind _on_navigation_cube_snap to its "
            "EndInteractionEvent -- a snap would not zoom-to-extent (bugs/0160)"
        )
    snap_src = inspect.getsource(Kraken3DInspector._on_navigation_cube_snap)
    if "_fit_view_to_scene_for_current_orientation" not in snap_src:
        failures.append("E FAIL: _on_navigation_cube_snap does not call the zoom-to-extent fit")
    if "_on_camera_interaction" not in snap_src:
        failures.append(
            "E FAIL: _on_navigation_cube_snap does not run the settled-orbit backstop "
            "(_on_camera_interaction) -- clip range / labels / dims would go stale"
        )
    fit_src = inspect.getsource(Kraken3DInspector._fit_view_to_scene_for_current_orientation)
    if "_parallel_scale_for_orthographic_fit" not in fit_src or "SetParallelScale" not in fit_src:
        failures.append(
            "E FAIL: the fit does not size the parallel scale via "
            "_parallel_scale_for_orthographic_fit + SetParallelScale"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0160 navigation-cube zoom-to-extent")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0160: a navigation-cube snap recenters + zooms-to-extent for its "
        "orientation like the top-bar preset buttons, then runs the backstop and renders"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
