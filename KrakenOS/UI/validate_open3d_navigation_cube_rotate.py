#!/usr/bin/env python3
"""Display-free guard for bugs/0158+0159: the rotate-view toolbar buttons swing
the whole view 90 degrees per click, forward and reverse. The rotation AXIS is
view-aware (FreeCAD navigation-cube "rotate" arrows):

  * Oblique / Iso view  -> a turntable about the view-up vector (``camera.Azimuth``)
    so two clicks (180) views the scene from the opposite side (bugs/0158).
  * Face-on plane view  -> a ROLL about the sight line, the axis going straight
    INTO the monitor (``camera.Roll``), so the plane spins in place. An azimuth
    here would swing the camera OFF the plane onto a neighbouring face (bugs/0159).

Why it exists (user reports):
  0158: "click a rotate button ... rotate the whole scene 90 degree ... Refer
  what the cube navigator of FreeCAD does."
  0159: "correct in ISO view, but in plane view for example YZ plane, it should
  spin around the perpendicular axis ... the axis that go into the center of the
  Monitor."

What it checks (no display required) -- the real ``Kraken3DInspector`` methods
bound to a light fake ``self`` whose fake renderer hands back a fake camera that
records ``Azimuth`` / ``Roll`` calls and exposes a controllable sight line:
  A. OBLIQUE view, ``rotate_camera_view(+90)`` forwards exactly
     ``camera.Azimuth(90.0)`` (and NOT ``Roll``), then runs the settled-orbit
     refit (``_on_camera_interaction`` with an End event) and a render.
  B. OBLIQUE ``rotate_camera_view(-90)`` forwards ``camera.Azimuth(-90.0)``.
  C. PLANE view (sight line along a principal axis), ``rotate_camera_view(+90)``
     forwards ``camera.Roll(90.0)`` (and NOT ``Azimuth``), then refits + renders.
  D. PLANE ``rotate_camera_view(-90)`` forwards ``camera.Roll(-90.0)``.
  E. The view discriminator ``_camera_sight_line_is_axis_aligned`` is True for an
     axis-aligned sight line and False for the oblique Iso one.
  F. It NEVER calls ``OrthogonalizeViewUp`` -- that would drift the turntable axis
     so four 90 clicks would not return to the start (bugs/0158 root cause).
  G. No renderer / no active camera -> a safe no-op (no rotation, no render).
  H. If the rotation raises, the method returns BEFORE the refit/render.
  I. Source contract -- ``build_view_toolbar`` wires both rotate buttons to
     ``rotate_camera_view``; the method source calls both ``.Azimuth(`` and
     ``.Roll(``, consults the axis-aligned check, and never calls
     ``.OrthogonalizeViewUp(``.

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

    def _camera_sight_line_is_axis_aligned(self, camera):
        # Exercise the REAL discriminator against the fake camera.
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector

        return Kraken3DInspector._camera_sight_line_is_axis_aligned(self, camera)

    def _on_camera_interaction(self, *args) -> None:
        self.interaction_calls.append(args)

    def render(self) -> None:
        self.render_calls += 1


def _rotate(fake, angle) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    Kraken3DInspector.rotate_camera_view(fake, angle)


def _is_axis_aligned(camera) -> bool:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    return Kraken3DInspector._camera_sight_line_is_axis_aligned(object(), camera)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- A: OBLIQUE +90 forwards Azimuth(90), then settled-orbit refit + render -
    cam = _FakeCamera(_OBLIQUE_SIGHT)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if cam.azimuth_calls != [90.0]:
        failures.append(f"A FAIL: oblique +90 forwarded Azimuth{cam.azimuth_calls!r}, want [90.0]")
    if cam.roll_calls:
        failures.append(f"A FAIL: oblique +90 also rolled {cam.roll_calls!r} (want azimuth only)")
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

    # --- B: OBLIQUE -90 forwards Azimuth(-90) ----------------------------------
    cam = _FakeCamera(_OBLIQUE_SIGHT)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, -90)
    if cam.azimuth_calls != [-90.0]:
        failures.append(f"B FAIL: oblique -90 forwarded Azimuth{cam.azimuth_calls!r}, want [-90.0]")

    # --- C: PLANE +90 forwards Roll(90) (NOT Azimuth) + refit + render ---------
    cam = _FakeCamera(_PLANE_SIGHT)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if cam.roll_calls != [90.0]:
        failures.append(
            f"C FAIL: plane-view +90 forwarded Roll{cam.roll_calls!r}, want [90.0] -- a "
            "face-on plane view must spin about the sight line (the axis into the monitor)"
        )
    if cam.azimuth_calls:
        failures.append(
            f"C FAIL: plane-view +90 azimuthed {cam.azimuth_calls!r} -- that swings the "
            "camera OFF the plane onto a neighbouring face (bugs/0159)"
        )
    if not fake.interaction_calls or fake.render_calls < 1:
        failures.append("C FAIL: plane-view rotation skipped the settled-orbit refit/render")

    # --- D: PLANE -90 forwards Roll(-90) ---------------------------------------
    cam = _FakeCamera(_PLANE_SIGHT)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, -90)
    if cam.roll_calls != [-90.0]:
        failures.append(f"D FAIL: plane-view -90 forwarded Roll{cam.roll_calls!r}, want [-90.0]")

    # --- E: the view discriminator separates plane from oblique ----------------
    if not _is_axis_aligned(_FakeCamera(_PLANE_SIGHT)):
        failures.append(
            "E FAIL: _camera_sight_line_is_axis_aligned False for a principal-axis sight "
            "line -- plane views would azimuth instead of roll"
        )
    if _is_axis_aligned(_FakeCamera(_OBLIQUE_SIGHT)):
        failures.append(
            "E FAIL: _camera_sight_line_is_axis_aligned True for the oblique Iso sight line "
            "-- the Iso turntable would roll instead of azimuth"
        )

    # --- F: never OrthogonalizeViewUp (turntable axis must not drift) ----------
    for sight, which in ((_OBLIQUE_SIGHT, "oblique"), (_PLANE_SIGHT, "plane")):
        cam = _FakeCamera(sight)
        fake = _FakeInspector(_FakeRenderer(cam))
        _rotate(fake, 90)
        if cam.orthogonalize_calls:
            failures.append(
                f"F FAIL: {which} rotation called OrthogonalizeViewUp -- it re-tilts the "
                "view-up so the turntable axis drifts and 4x90 no longer returns to start"
            )

    # --- G: no renderer / no active camera -> safe no-op -----------------------
    fake = _FakeInspector(None)
    _rotate(fake, 90)
    if fake.render_calls or fake.interaction_calls:
        failures.append("G FAIL: acted with no renderer (want a clean no-op)")
    fake = _FakeInspector(_FakeRenderer(None))
    _rotate(fake, 90)
    if fake.render_calls or fake.interaction_calls:
        failures.append("G FAIL: acted with no active camera (want a clean no-op)")

    # --- H: a raising rotation -> return before the refit/render ---------------
    cam = _FakeCamera(_OBLIQUE_SIGHT, raise_on_rotate=True)
    fake = _FakeInspector(_FakeRenderer(cam))
    _rotate(fake, 90)
    if fake.interaction_calls or fake.render_calls:
        failures.append(
            "H FAIL: ran the refit/render after the rotation raised -- a failed rotation "
            "should leave the view untouched"
        )

    # --- I: source contract -----------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel

    method_src = inspect.getsource(Kraken3DInspector.rotate_camera_view)
    if ".Azimuth(" not in method_src:
        failures.append("I FAIL: rotate_camera_view does not call camera.Azimuth( (oblique turntable)")
    if ".Roll(" not in method_src:
        failures.append("I FAIL: rotate_camera_view does not call camera.Roll( (plane-view roll)")
    if "_camera_sight_line_is_axis_aligned" not in method_src:
        failures.append(
            "I FAIL: rotate_camera_view does not consult _camera_sight_line_is_axis_aligned "
            "-- the rotation axis would not be view-aware"
        )
    # Match the CALL form (leading dot, trailing paren), not the explanatory
    # comment that names OrthogonalizeViewUp to warn against re-adding it.
    if ".OrthogonalizeViewUp(" in method_src:
        failures.append(
            "I FAIL: rotate_camera_view calls OrthogonalizeViewUp (drifts the turntable axis)"
        )
    toolbar_src = inspect.getsource(Open3DTopControlsPanel.build_view_toolbar)
    if "rotate_camera_view(value)" not in toolbar_src:
        failures.append(
            "I FAIL: build_view_toolbar does not wire the rotate_camera_view buttons"
        )
    for needle, which in ((", -90)", "reverse"), (", 90)", "forward")):
        if needle not in toolbar_src:
            failures.append(
                f"I FAIL: build_view_toolbar lacks the {which} rotate angle ({needle.strip(', )')})"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0158+0159 rotate-view buttons (view-aware 90 swing)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0158+0159: the rotate-view buttons azimuth an oblique/Iso view "
        "and ROLL a face-on plane view (no OrthogonalizeViewUp), refit, and render"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
