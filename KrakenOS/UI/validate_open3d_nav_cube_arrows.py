#!/usr/bin/env python3
"""Display-free guard for bugs/0251: the Open 3D navigation cube's step ARROWS highlight on
hover (brighten toward white), the long face words fit the facet, and the arrows stand clear
of the cube body.

Why it exists (user flag 2026-07-07, third pass on the nav cube after 0249/0250):
  "B and M still overflow, F and T still overflow. Can make the arrow space out a bit from
   the cube body? Can make the arrows highlight when hover?"

The arrow highlight is a per-actor colour swap, so it is testable without a display: THIS
guard drives _set_arrow_hover / _clear_arrow_hover against fake actors and pins the label +
cube-frame sizing constants plus the hover wiring, so a future edit can't silently drop the
arrow highlight, regrow the label past the facet, or let the cube crowd the arrows again.

What it checks (no display required):
  A. A bare NavigationCube exposes the arrow-hover state (_arrow_base_colors,
     _arrow_hover_actor).
  B. _set_arrow_hover(actor) brightens that actor and leaves every other arrow at its base
     colour; it returns True and re-renders once.
  C. Moving the arrow hover restores the previous actor's base colour and brightens the new
     one -- exactly one arrow highlighted at a time.
  D. _clear_arrow_hover() / _set_arrow_hover(None) restores every arrow.
  E. Re-hovering the SAME arrow is a no-op (no redundant re-render).
  F. The brightened colour is distinctly lighter than the base (mix toward white), so the
     highlight actually reads.
  G. _FACE_TEXT_SCALE stays small enough for the 6-char BOTTOM to fit (<= 0.13) and
     _CUBE_FRAME_SCALE frames the cube small enough to clear the arrows (>= 1.05).
  H. Source contract: handle_hover picks the arrows and calls _set_arrow_hover; clear_hover
     clears the arrow hover; _arrow_entry_for / _remember_arrow_color exist and
     _build_arrow_renderer remembers each arrow's colour.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_nav_cube_arrows

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _FakeProp:
    def __init__(self, color):
        self.color = tuple(float(c) for c in color)

    def SetColor(self, r, g, b):
        self.color = (float(r), float(g), float(b))

    def GetColor(self):
        return self.color


class _FakeActor:
    """Stand-in for a vtkActor: an address (identity) + a settable colour property."""

    def __init__(self, addr, color):
        self._addr = addr
        self._prop = _FakeProp(color)

    def GetProperty(self):
        return self._prop

    def GetAddressAsString(self, _t):
        return self._addr


class _FakeWin:
    def __init__(self):
        self.renders = 0

    def Render(self):
        self.renders += 1


_ORBIT = (0.20, 0.55, 0.95)
_ROLL = (0.95, 0.60, 0.15)


def _bare_cube(W):
    """A NavigationCube with ONLY the arrow-hover state wired to fakes -- no VTK/display."""
    cube = W.NavigationCube.__new__(W.NavigationCube)
    a_up = _FakeActor("0xA", _ORBIT)
    a_roll = _FakeActor("0xB", _ROLL)
    cube._arrow_actors = [(a_up, "el_up"), (a_roll, "roll_cw")]
    cube._arrow_base_colors = {"0xA": _ORBIT, "0xB": _ROLL}
    cube._arrow_hover_actor = None
    cube._render_window = _FakeWin()
    return cube, a_up, a_roll


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []

    from KrakenOS.UI.services import nav_cube_widget as W

    # --- A: init exposes arrow-hover state ----------------------------------------
    try:
        src_init = inspect.getsource(W.NavigationCube.__init__)
        for attr in ("self._arrow_base_colors", "self._arrow_hover_actor"):
            if attr not in src_init:
                failures.append(f"A FAIL: NavigationCube.__init__ no longer sets {attr}")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"A FAIL: could not inspect NavigationCube.__init__: {exc!r}")

    # --- B: highlight one arrow ---------------------------------------------------
    cube, a_up, a_roll = _bare_cube(W)
    ret = cube._set_arrow_hover(a_up)
    if not ret:
        failures.append("B FAIL: _set_arrow_hover(arrow) returned False")
    if a_up.GetProperty().GetColor() == _ORBIT:
        failures.append("B FAIL: hovered arrow was not recoloured")
    if sum(a_up.GetProperty().GetColor()) <= sum(_ORBIT):
        failures.append("B FAIL: hovered arrow did not get lighter")
    if a_roll.GetProperty().GetColor() != _ROLL:
        failures.append("B FAIL: _set_arrow_hover disturbed a non-hovered arrow")
    if cube._arrow_hover_actor is not a_up:
        failures.append("B FAIL: _arrow_hover_actor is not the hovered arrow")
    if cube._render_window.renders != 1:
        failures.append(f"B FAIL: expected one re-render, got {cube._render_window.renders}")

    # --- C: move the hover --------------------------------------------------------
    cube._set_arrow_hover(a_roll)
    if a_up.GetProperty().GetColor() != _ORBIT:
        failures.append("C FAIL: previous arrow not restored to its base colour")
    if sum(a_roll.GetProperty().GetColor()) <= sum(_ROLL):
        failures.append("C FAIL: new arrow not brightened")
    lit = sum(
        1
        for a, base in ((a_up, _ORBIT), (a_roll, _ROLL))
        if a.GetProperty().GetColor() != base
    )
    if lit != 1:
        failures.append(f"C FAIL: expected exactly one brightened arrow, got {lit}")

    # --- D: clear -----------------------------------------------------------------
    cube._clear_arrow_hover()
    if a_up.GetProperty().GetColor() != _ORBIT or a_roll.GetProperty().GetColor() != _ROLL:
        failures.append("D FAIL: clear_arrow_hover left an arrow recoloured")
    if cube._arrow_hover_actor is not None:
        failures.append("D FAIL: _arrow_hover_actor not None after clear")

    # --- E: same-arrow re-hover is a no-op ----------------------------------------
    before = cube._render_window.renders
    cube._set_arrow_hover(a_up)
    after_first = cube._render_window.renders
    cube._set_arrow_hover(a_up)
    after_second = cube._render_window.renders
    if after_first != before + 1:
        failures.append("E FAIL: first arrow hover did not re-render")
    if after_second != after_first:
        failures.append("E FAIL: re-hovering the same arrow re-rendered (should be a no-op)")

    # --- F: brightened colour distinctly lighter ----------------------------------
    mix = getattr(W, "_ARROW_HOVER_MIX", None)
    if mix is None or not (0.0 < mix <= 1.0):
        failures.append(f"F FAIL: _ARROW_HOVER_MIX {mix} not in (0, 1]")
    else:
        for base in (_ORBIT, _ROLL):
            hi = tuple(c * (1.0 - mix) + mix for c in base)
            if sum(hi) - sum(base) < 0.3:
                failures.append(f"F FAIL: hover mix barely lightens {base} (delta {sum(hi)-sum(base):.2f})")

    # --- G: label fits + cube framed small ----------------------------------------
    if W._FACE_TEXT_SCALE > 0.13:
        failures.append(
            f"G FAIL: _FACE_TEXT_SCALE {W._FACE_TEXT_SCALE} > 0.13 -- 6-char BOTTOM will overflow"
        )
    frame = getattr(W, "_CUBE_FRAME_SCALE", None)
    if frame is None or frame < 1.05:
        failures.append(
            f"G FAIL: _CUBE_FRAME_SCALE {frame} < 1.05 -- cube not framed small enough to clear the arrows"
        )

    # --- H: source contract -------------------------------------------------------
    try:
        hover_src = inspect.getsource(W.NavigationCube.handle_hover)
        if "_set_arrow_hover" not in hover_src or "_arrow_entry_for" not in hover_src:
            failures.append("H FAIL: handle_hover no longer highlights arrows via _set_arrow_hover")
        clear_src = inspect.getsource(W.NavigationCube.clear_hover)
        if "_set_arrow_hover" not in clear_src:
            failures.append("H FAIL: clear_hover no longer clears the arrow hover")
        cls_src = inspect.getsource(W.NavigationCube)
        for token in ("def _arrow_entry_for", "def _remember_arrow_color", "def _set_arrow_hover"):
            if token not in cls_src:
                failures.append(f"H FAIL: NavigationCube lost arrow-hover method '{token}'")
        build_src = inspect.getsource(W.NavigationCube._build_arrow_renderer)
        if "_remember_arrow_color(" not in build_src:
            failures.append("H FAIL: _build_arrow_renderer no longer remembers arrow base colours")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"H FAIL: could not inspect NavigationCube arrow-hover wiring: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0251 nav-cube arrow hover / label fit / spacing")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0251: the nav-cube arrows brighten on hover (restoring the last), the long "
        "labels fit the facet, and the cube is framed small enough to clear the arrows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
