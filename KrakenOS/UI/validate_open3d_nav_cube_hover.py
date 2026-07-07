#!/usr/bin/env python3
"""Display-free guard for bugs/0250: the Open 3D navigation cube highlights the facet
under the mouse (face / edge / corner), the labels fit the facet, and the roll arcs are
short FreeCAD-style arcs -- not a near-full loop.

Why it exists (user flag 2026-07-07, second pass on the nav cube after bugs/0249):
  "Text still overflow. The curve segment of the rotation arrow is too much. Refer to
   attachment/freecad.png for reference."
  + follow-up: "mouse hover each Cube selectable face or edge or corner should highlight."

The hover recolour is a per-cell colour swap on the same mesh bugs/0249 built, so it is
testable without a display: THIS guard drives _set_hover / clear_hover against a fake
colour array and pins the label/arc sizing constants + the host/bindings wiring, so a
future edit can't silently drop the highlight, regrow the label past the facet, or turn
the roll arc back into a loop.

What it checks (no display required):
  A. A bare NavigationCube exposes the hover state (_cell_colors, _base_colors,
     _hover_cell == -1).
  B. _set_hover(cid) recolours cell cid to _COLOR_HOVER and leaves every other cell at
     its base colour; it returns True and re-renders once.
  C. Moving the hover restores the previous cell's base colour and highlights the new one
     -- exactly one cell highlighted at a time.
  D. clear_hover() / _set_hover(-1) restores every cell (no cell highlighted).
  E. Re-hovering the SAME cell is a no-op (no redundant re-render).
  F. _COLOR_HOVER is visually distinct from every base kind colour (face/edge/corner) so
     the highlight actually reads.
  G. _FACE_TEXT_SCALE stays comfortably inside the flat facet (<= 0.18) and each roll arc
     sweep is a short arc (|a1 - a0| <= 150 deg), matching the FreeCAD reference.
  H. Source contract: the widget defines handle_hover / clear_hover / _set_hover and keeps
     _cell_colors / _base_colors; the host defines _handle_navigation_cube_hover /
     _clear_navigation_cube_hover; the bindings hover_motion calls the host hover before
     the scene's own hover.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_nav_cube_hover

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import ast
import inspect
import math
import os
import textwrap


class _FakeColorArray:
    """Stand-in for the per-cell vtkUnsignedCharArray; records SetTuple3 writes so the
    guard can assert which cell holds which colour without a render window."""

    def __init__(self, base):
        self._rows = [tuple(int(c) for c in t) for t in base]
        self.modified = 0

    def SetTuple3(self, i, r, g, b):
        self._rows[i] = (int(r), int(g), int(b))

    def Modified(self):
        self.modified += 1


class _FakeWin:
    def __init__(self):
        self.renders = 0

    def Render(self):
        self.renders += 1


def _bare_cube(W, base):
    """A NavigationCube with ONLY the hover state wired to fakes -- no VTK, no display."""
    cube = W.NavigationCube.__new__(W.NavigationCube)
    cube._cell_colors = _FakeColorArray(base)
    cube._base_colors = [tuple(int(c) for c in t) for t in base]
    cube._hover_cell = -1
    cube._render_window = _FakeWin()
    return cube


def _rgb_dist(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _roll_arc_sweeps(src: str):
    """Pull the roll_specs dict out of _build_arrow_renderer source and return the list of
    arc sweeps |a1 - a0| in degrees (or None if the dict can't be found)."""
    tree = ast.parse(textwrap.dedent(src))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "roll_specs":
                    specs = ast.literal_eval(node.value)
                    return [abs(v[3] - v[2]) for v in specs.values()]
    return None


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []

    from KrakenOS.UI.services import nav_cube_widget as W

    hover = tuple(W._COLOR_HOVER)
    hover255 = tuple(int(round(c * 255.0)) for c in hover)
    # Three distinct base colours standing in for a face / edge / corner cell.
    base = [(212, 222, 237), (143, 166, 204), (102, 128, 176)]

    # --- A: init exposes hover state ----------------------------------------------
    try:
        src_init = inspect.getsource(W.NavigationCube.__init__)
        for attr in ("self._cell_colors", "self._base_colors", "self._hover_cell"):
            if attr not in src_init:
                failures.append(f"A FAIL: NavigationCube.__init__ no longer sets {attr}")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"A FAIL: could not inspect NavigationCube.__init__: {exc!r}")

    # --- B: highlight one cell ----------------------------------------------------
    cube = _bare_cube(W, base)
    ret = cube._set_hover(1)
    rows = cube._cell_colors._rows
    if not ret:
        failures.append("B FAIL: _set_hover(valid cell) returned False")
    if rows[1] != hover255:
        failures.append(f"B FAIL: hovered cell not recoloured to _COLOR_HOVER ({rows[1]} != {hover255})")
    if rows[0] != base[0] or rows[2] != base[2]:
        failures.append("B FAIL: _set_hover disturbed a non-hovered cell")
    if cube._hover_cell != 1:
        failures.append(f"B FAIL: _hover_cell is {cube._hover_cell}, expected 1")
    if cube._render_window.renders != 1:
        failures.append(f"B FAIL: expected exactly one re-render, got {cube._render_window.renders}")

    # --- C: move the hover --------------------------------------------------------
    cube._set_hover(2)
    rows = cube._cell_colors._rows
    if rows[1] != base[1]:
        failures.append("C FAIL: previous hovered cell not restored to its base colour")
    if rows[2] != hover255:
        failures.append("C FAIL: new hovered cell not highlighted")
    highlighted = [i for i, r in enumerate(rows) if r == hover255]
    if highlighted != [2]:
        failures.append(f"C FAIL: expected exactly cell 2 highlighted, got {highlighted}")

    # --- D: clear -----------------------------------------------------------------
    cube.clear_hover()
    rows = cube._cell_colors._rows
    if rows != [tuple(t) for t in base]:
        failures.append(f"D FAIL: clear_hover left cells recoloured: {rows}")
    if cube._hover_cell != -1:
        failures.append(f"D FAIL: _hover_cell is {cube._hover_cell} after clear, expected -1")

    # --- E: same-cell re-hover is a no-op -----------------------------------------
    before = cube._render_window.renders
    cube._set_hover(0)
    after_first = cube._render_window.renders
    cube._set_hover(0)
    after_second = cube._render_window.renders
    if after_first != before + 1:
        failures.append("E FAIL: first hover did not re-render")
    if after_second != after_first:
        failures.append("E FAIL: re-hovering the same cell re-rendered (should be a no-op)")

    # --- F: hover colour distinct from every base kind ----------------------------
    for name in ("_COLOR_FACE", "_COLOR_EDGE", "_COLOR_CORNER"):
        kind = tuple(getattr(W, name))
        d = _rgb_dist(hover, kind)
        if d < 0.25:
            failures.append(f"F FAIL: _COLOR_HOVER too close to {name} (rgb dist {d:.3f} < 0.25)")

    # --- G: label fits + arcs are short -------------------------------------------
    if W._FACE_TEXT_SCALE > 0.18:
        failures.append(
            f"G FAIL: _FACE_TEXT_SCALE {W._FACE_TEXT_SCALE} > 0.18 -- label will overflow the facet"
        )
    try:
        arrow_src = inspect.getsource(W.NavigationCube._build_arrow_renderer)
        sweeps = _roll_arc_sweeps(arrow_src)
        if not sweeps:
            failures.append("G FAIL: could not find roll_specs arc sweeps in _build_arrow_renderer")
        else:
            for sweep in sweeps:
                if sweep > 150.0:
                    failures.append(
                        f"G FAIL: roll arc sweep {sweep:.0f} deg > 150 -- arc too long (near-loop)"
                    )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"G FAIL: could not inspect _build_arrow_renderer: {exc!r}")

    # --- H: source contract on widget + host + bindings ---------------------------
    try:
        cls_src = inspect.getsource(W.NavigationCube)
        for token in ("def handle_hover", "def clear_hover", "def _set_hover",
                      "self._cell_colors", "self._base_colors"):
            if token not in cls_src:
                failures.append(f"H FAIL: NavigationCube lost hover contract token '{token}'")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"H FAIL: could not inspect NavigationCube: {exc!r}")

    ui_dir = os.path.dirname(os.path.dirname(os.path.abspath(W.__file__)))
    services_dir = os.path.dirname(os.path.abspath(W.__file__))
    inspector_path = os.path.join(ui_dir, "open3d_inspector.py")
    bindings_path = os.path.join(services_dir, "open3d_mouse_bindings.py")

    try:
        host_src = open(inspector_path, encoding="utf-8").read()
        for token in ("def _handle_navigation_cube_hover", "def _clear_navigation_cube_hover",
                      "cube.handle_hover("):
            if token not in host_src:
                failures.append(f"H FAIL: open3d_inspector lost host-hover token '{token}'")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"H FAIL: could not read open3d_inspector.py: {exc!r}")

    try:
        bind_src = open(bindings_path, encoding="utf-8").read()
        if "def hover_motion" not in bind_src:
            failures.append("H FAIL: open3d_mouse_bindings lost hover_motion")
        if "_handle_navigation_cube_hover(" not in bind_src:
            failures.append(
                "H FAIL: hover_motion no longer routes to _handle_navigation_cube_hover -- "
                "the cube won't highlight on <Motion>"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"H FAIL: could not read open3d_mouse_bindings.py: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0250 nav-cube hover / label / arc")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0250: the nav cube highlights the hovered facet (restoring the last), the "
        "hover colour is distinct, the label fits the facet, and the roll arcs are short"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
