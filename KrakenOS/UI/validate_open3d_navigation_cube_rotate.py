#!/usr/bin/env python3
"""Display-free guard for bugs/0158: the rotate-view toolbar buttons swing the
camera 90 degrees about the scene (a turntable / azimuth), forward and reverse.

Why it exists (user report, follow-up to bugs/0156/0157):
  "I am at ISO view ... click a rotate button ... Object Plane change from
  North-West to North-East ... rotate another 90 degree ... South-East ... For YZ
  view or any other plane view ... rotate the whole scene 90 degree as well. Refer
  what the cube navigator of FreeCAD does."

The interactive navigation cube (bugs/0156/0157) only SNAPS to a face/edge/corner
orthographic view; it never sweeps between views. This adds
``Kraken3DInspector.rotate_camera_azimuth(angle)``, called by two View-toolbar
buttons (``rotate_camera_azimuth(-90)`` / ``(+90)``), which spins the whole view 90
degrees per click -- two clicks (180) views the scene from the opposite side.

What it checks (no display required) -- the real method bound to a light fake
``self`` whose fake renderer hands back a fake camera that records ``Azimuth``:
  A. ``rotate_camera_azimuth(+90)`` forwards exactly ``camera.Azimuth(90.0)``, then
     runs the settled-orbit refit (``_on_camera_interaction`` with an End event) and
     a render.
  B. ``rotate_camera_azimuth(-90)`` forwards ``camera.Azimuth(-90.0)``.
  C. It does NOT call ``OrthogonalizeViewUp`` -- that would drift the turntable axis
     so four 90 clicks would not return to the start (bugs/0158 root cause).
  D. No renderer / no active camera -> a safe no-op (no Azimuth, no render).
  E. If ``Azimuth`` raises, the method returns BEFORE the refit/render.
  F. Source contract -- ``build_view_toolbar`` wires both rotate buttons; the method
     source calls ``.Azimuth(`` and not ``OrthogonalizeViewUp``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube_rotate

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _FakeCamera:
    def __init__(self, raise_on_azimuth: bool = False) -> None:
        self.azimuth_calls: list[float] = []
        self.orthogonalize_calls = 0
        self._raise = raise_on_azimuth

    def Azimuth(self, angle) -> None:
        self.azimuth_calls.append(angle)
        if self._raise:
            raise RuntimeError("azimuth boom")

    def OrthogonalizeViewUp(self) -> None:
        self.orthogonalize_calls += 1


class _FakeRenderer:
    def __init__(self, camera) -> None:
        self._camera = camera

    def GetActiveCamera(self):
        return self._camera


class _FakeInspector:
    """Minimal attribute bag carrying just what rotate_camera_azimuth touches."""

    def __init__(self, renderer) -> None:
        self._renderer = renderer
        self.interaction_calls: list[tuple] = []
        self.render_calls = 0

    def _on_camera_interaction(self, *args) -> None:
        self.interaction_calls.append(args)

    def render(self) -> None:
        self.render_calls += 1


def _rotate(fake, angle) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    Kraken3DInspector.rotate_camera_azimuth(fake, angle)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- A: +90 forwards Azimuth(90), then settled-orbit refit + render --------
    cam = _FakeCamera()
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if cam.azimuth_calls != [90.0]:
        failures.append(f"A FAIL: +90 forwarded Azimuth{cam.azimuth_calls!r}, want [90.0]")
    if not fake.interaction_calls:
        failures.append(
            "A FAIL: did not run the settled-orbit refit (_on_camera_interaction) -- "
            "the clip range / thickness labels / view-relative dims would go stale"
        )
    else:
        ev = fake.interaction_calls[-1]
        if not any("End" in str(a) for a in ev):
            failures.append(
                f"A FAIL: _on_camera_interaction args {ev!r} lack an End event -- the "
                "bugs/0152 view-relative dimensions would not re-place after the jump"
            )
    if fake.render_calls < 1:
        failures.append(
            "A FAIL: did not render after the rotation -- a button press, unlike a "
            "mouse orbit, has no VTK interaction event to trigger a render"
        )

    # --- B: -90 forwards Azimuth(-90) ------------------------------------------
    cam = _FakeCamera()
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, -90)
    if cam.azimuth_calls != [-90.0]:
        failures.append(f"B FAIL: -90 forwarded Azimuth{cam.azimuth_calls!r}, want [-90.0]")

    # --- C: never OrthogonalizeViewUp (turntable axis must not drift) ----------
    cam = _FakeCamera()
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if cam.orthogonalize_calls:
        failures.append(
            "C FAIL: called OrthogonalizeViewUp -- it re-tilts the view-up onto the new "
            "sight line so the turntable axis drifts and 4x90 no longer returns to start"
        )

    # --- D: no renderer / no active camera -> safe no-op -----------------------
    fake = _FakeInspector(None)
    _rotate(fake, 90)
    if fake.render_calls or fake.interaction_calls:
        failures.append("D FAIL: acted with no renderer (want a clean no-op)")
    fake = _FakeInspector(_FakeRenderer(None))
    _rotate(fake, 90)
    if fake.render_calls or fake.interaction_calls:
        failures.append("D FAIL: acted with no active camera (want a clean no-op)")

    # --- E: Azimuth raises -> return before the refit/render -------------------
    cam = _FakeCamera(raise_on_azimuth=True)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if fake.interaction_calls or fake.render_calls:
        failures.append(
            "E FAIL: ran the refit/render after Azimuth raised -- a failed rotation "
            "should leave the view untouched"
        )

    # --- F: source contract -----------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel

    method_src = inspect.getsource(Kraken3DInspector.rotate_camera_azimuth)
    if ".Azimuth(" not in method_src:
        failures.append("F FAIL: rotate_camera_azimuth does not call camera.Azimuth(")
    # Match the CALL form (leading dot, trailing paren), not the explanatory
    # comment that names OrthogonalizeViewUp to warn against re-adding it.
    if ".OrthogonalizeViewUp(" in method_src:
        failures.append(
            "F FAIL: rotate_camera_azimuth calls OrthogonalizeViewUp (drifts the turntable axis)"
        )
    toolbar_src = inspect.getsource(Open3DTopControlsPanel.build_view_toolbar)
    if "rotate_camera_azimuth(value)" not in toolbar_src:
        failures.append(
            "F FAIL: build_view_toolbar does not wire the rotate_camera_azimuth buttons"
        )
    for needle, which in ((", -90)", "reverse"), (", 90)", "forward")):
        if needle not in toolbar_src:
            failures.append(
                f"F FAIL: build_view_toolbar lacks the {which} rotate angle ({needle.strip(', )')})"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0158 rotate-view buttons (90 azimuth turntable)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0158: the rotate-view buttons forward camera.Azimuth(+-90) "
        "(no OrthogonalizeViewUp), refit like a settled orbit, and render"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
