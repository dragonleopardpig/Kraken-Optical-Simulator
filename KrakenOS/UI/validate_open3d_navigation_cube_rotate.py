#!/usr/bin/env python3
"""Display-free guard for bugs/0158+0159+0228: the rotate-view toolbar buttons spin
the whole view 90 degrees per click, forward and reverse, about the SIGHT LINE --
the axis going straight INTO the monitor (``camera.Roll``) -- in EVERY view.

History of the contract:
  0158: "click a rotate button ... rotate the whole scene 90 degree" -- first cut
  was a turntable (``Azimuth``) everywhere.
  0159: "correct in ISO view, but in plane view for example YZ plane, it should
  spin around the perpendicular axis ... the axis that go into the center of the
  Monitor." -- plane views became a ROLL, oblique/Iso kept the turntable.
  0228 (flags 20260705_1354xx, a 4-step recording): on the ISO scene the
  turntable orbited the object around the beam column instead of spinning the
  picture -- "It should rotate through the axis into the Monitor." The rotation
  is now a ROLL in every view: the sight line NEVER changes (nothing swings to a
  different side), the image rotates in place like a sheet of paper, and four
  90-degree clicks return exactly to the start.

What it checks (no display required) -- the real ``Kraken3DInspector`` methods
bound to a light fake ``self`` whose fake renderer hands back a fake camera that
records ``Azimuth`` / ``Roll`` calls:
  A. OBLIQUE/ISO ``rotate_camera_view(+90)`` forwards exactly ``camera.Roll(90.0)``
     (and NEVER ``Azimuth`` -- the 0228 flag), then runs the settled-orbit refit
     (``_on_camera_interaction`` with an End event) and a render.
  B. OBLIQUE ``rotate_camera_view(-90)`` forwards ``camera.Roll(-90.0)``.
  C. PLANE view (sight line along a principal axis) rolls identically (+90).
  D. PLANE ``rotate_camera_view(-90)`` forwards ``camera.Roll(-90.0)``.
  E. SIGHT-LINE INVARIANT: a REAL ``vtkCamera`` at the Iso pose keeps its sight
     line bit-identical across the rotate (a roll cannot change it; the old
     azimuth swung it 90 degrees), and 4x90 clicks restore the view-up.
  F. It never calls ``OrthogonalizeViewUp``.
  G. No renderer / no active camera -> a safe no-op (no rotation, no render).
  H. If the rotation raises, the method returns BEFORE the refit/render.
  I. Source contract -- ``build_view_toolbar`` wires both rotate buttons to
     ``rotate_camera_view``; the method source calls ``.Roll(`` and calls
     NEITHER ``.Azimuth(`` nor ``.OrthogonalizeViewUp(``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_navigation_cube_rotate

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import math

# Sight lines (view direction = focal_point - position) used by the fakes.
_OBLIQUE_SIGHT = (-0.699, 0.405, 0.589)  # the Iso preset direction (bugs/0158 probe)
_PLANE_SIGHT = (-1.0, 0.0, 0.0)  # the +yz preset: camera on +X looking -X


class _FakeCamera:
    def __init__(self, sight=_OBLIQUE_SIGHT, raise_on_rotate: bool = False) -> None:
        self.azimuth_calls: list[float] = []
        self.roll_calls: list[float] = []
        self.orthogonalize_calls = 0
        self._raise = raise_on_rotate
        norm = math.sqrt(sum(c * c for c in sight)) or 1.0
        unit = tuple(c / norm for c in sight)
        # focal - position == unit*10 -> the normalised sight line is ``unit``.
        self._focal = (0.0, 0.0, 0.0)
        self._position = tuple(-c * 10.0 for c in unit)

    def GetPosition(self):
        return self._position

    def GetFocalPoint(self):
        return self._focal

    def Azimuth(self, angle) -> None:
        self.azimuth_calls.append(angle)
        if self._raise:
            raise RuntimeError("azimuth boom")

    def Roll(self, angle) -> None:
        self.roll_calls.append(angle)
        if self._raise:
            raise RuntimeError("roll boom")

    def OrthogonalizeViewUp(self) -> None:
        self.orthogonalize_calls += 1


class _FakeRenderer:
    def __init__(self, camera) -> None:
        self._camera = camera

    def GetActiveCamera(self):
        return self._camera


class _FakeInspector:
    """Minimal attribute bag carrying just what rotate_camera_view touches."""

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

    Kraken3DInspector.rotate_camera_view(fake, angle)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- A: OBLIQUE/ISO +90 rolls about the sight line (NEVER azimuth) ----------
    cam = _FakeCamera(_OBLIQUE_SIGHT)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if cam.roll_calls != [90.0]:
        failures.append(
            f"A FAIL: Iso +90 forwarded Roll{cam.roll_calls!r}, want [90.0] -- the view must "
            "spin about the axis into the monitor (bugs/0228)"
        )
    if cam.azimuth_calls:
        failures.append(
            f"A FAIL: Iso +90 azimuthed {cam.azimuth_calls!r} -- the turntable orbits the "
            "object around the scene instead of rotating the picture (the flagged 4-step recording)"
        )
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

    # --- B: OBLIQUE -90 rolls -90 ------------------------------------------------
    cam = _FakeCamera(_OBLIQUE_SIGHT)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, -90)
    if cam.roll_calls != [-90.0] or cam.azimuth_calls:
        failures.append(
            f"B FAIL: Iso -90 forwarded Roll{cam.roll_calls!r} Azimuth{cam.azimuth_calls!r}, "
            "want Roll [-90.0] only"
        )

    # --- C/D: PLANE view rolls identically ---------------------------------------
    for angle, label in ((90, "C"), (-90, "D")):
        cam = _FakeCamera(_PLANE_SIGHT)
        fake = _FakeInspector(_FakeRenderer(cam))
        _rotate(fake, angle)
        if cam.roll_calls != [float(angle)] or cam.azimuth_calls:
            failures.append(
                f"{label} FAIL: plane-view {angle:+d} forwarded Roll{cam.roll_calls!r} "
                f"Azimuth{cam.azimuth_calls!r}, want Roll [{float(angle)}] only (bugs/0159)"
            )
        if not fake.interaction_calls or fake.render_calls < 1:
            failures.append(f"{label} FAIL: plane-view rotation skipped the settled-orbit refit/render")

    # --- E: REAL vtkCamera -- the sight line is invariant; 4x90 returns to start -
    try:
        from vtkmodules.vtkRenderingCore import vtkCamera

        real = vtkCamera()
        real.SetFocalPoint(0.0, 0.0, 0.0)
        real.SetPosition(6.99, -4.05, -5.89)  # the Iso pose (sight = _OBLIQUE_SIGHT)
        real.SetViewUp(0.0, 1.0, 0.0)
        real.OrthogonalizeViewUp()

        def _sight():
            p = real.GetPosition()
            f = real.GetFocalPoint()
            v = tuple(f[i] - p[i] for i in range(3))
            n = math.sqrt(sum(c * c for c in v)) or 1.0
            return tuple(c / n for c in v)

        sight_before = _sight()
        up_before = real.GetViewUp()
        fake = _FakeInspector(_FakeRenderer(real))
        for _ in range(4):
            _rotate(fake, 90)
        sight_after = _sight()
        up_after = real.GetViewUp()
        sight_drift = max(abs(a - b) for a, b in zip(sight_before, sight_after))
        up_drift = max(abs(a - b) for a, b in zip(up_before, up_after))
        if sight_drift > 1e-9:
            failures.append(
                f"E FAIL: the sight line drifted {sight_drift:.2e} across the rotates -- a roll "
                "about the into-the-monitor axis can never change where the camera looks"
            )
        if up_drift > 1e-6:
            failures.append(
                f"E FAIL: four 90-degree clicks did not return the view-up (drift {up_drift:.2e})"
            )
    except Exception as exc:
        failures.append(f"E FAIL: real-vtkCamera invariant probe raised: {exc!r}")

    # --- F: never OrthogonalizeViewUp --------------------------------------------
    for sight, which in ((_OBLIQUE_SIGHT, "oblique"), (_PLANE_SIGHT, "plane")):
        cam = _FakeCamera(sight)
        fake = _FakeInspector(_FakeRenderer(cam))
        _rotate(fake, 90)
        if cam.orthogonalize_calls:
            failures.append(f"F FAIL: {which} rotation called OrthogonalizeViewUp")

    # --- G: no renderer / no active camera -> safe no-op -------------------------
    fake = _FakeInspector(None)
    _rotate(fake, 90)
    if fake.render_calls or fake.interaction_calls:
        failures.append("G FAIL: acted with no renderer (want a clean no-op)")
    fake = _FakeInspector(_FakeRenderer(None))
    _rotate(fake, 90)
    if fake.render_calls or fake.interaction_calls:
        failures.append("G FAIL: acted with no active camera (want a clean no-op)")

    # --- H: a raising rotation -> return before the refit/render -----------------
    cam = _FakeCamera(_OBLIQUE_SIGHT, raise_on_rotate=True)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if fake.interaction_calls or fake.render_calls:
        failures.append(
            "H FAIL: ran the refit/render after the rotation raised -- a failed rotation "
            "should leave the view untouched"
        )

    # --- I: source contract -------------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel

    method_src = inspect.getsource(Kraken3DInspector.rotate_camera_view)
    if ".Roll(" not in method_src:
        failures.append("I FAIL: rotate_camera_view does not call camera.Roll(")
    if ".Azimuth(" in method_src:
        failures.append(
            "I FAIL: rotate_camera_view calls camera.Azimuth( -- the turntable is the "
            "flagged bugs/0228 behaviour (the object orbits instead of the picture rotating)"
        )
    if ".OrthogonalizeViewUp(" in method_src:
        failures.append("I FAIL: rotate_camera_view calls OrthogonalizeViewUp")
    toolbar_src = inspect.getsource(Open3DTopControlsPanel.build_view_toolbar)
    if "rotate_camera_view(value)" not in toolbar_src:
        failures.append("I FAIL: build_view_toolbar does not wire the rotate_camera_view buttons")
    for needle, which in ((", -90)", "reverse"), (", 90)", "forward")):
        if needle not in toolbar_src:
            failures.append(
                f"I FAIL: build_view_toolbar lacks the {which} rotate angle ({needle.strip(', )')})"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0158+0159+0228 rotate-view buttons (roll about the into-the-monitor axis)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0228: the rotate-view buttons ROLL every view about the sight line "
        "(the axis into the monitor); the sight line is invariant and 4x90 returns to start"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
