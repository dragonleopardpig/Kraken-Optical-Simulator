#!/usr/bin/env python3
"""Regression test for bugs/0001: selecting an analytic lens must not go all-red.

A selected row's body actor should show a PINK translucent fill. For dense
solid bodies -- file-backed STL solids AND glassy analytic lens bodies
(revolved drums, Standard caps, promoted-STEP body plates) -- the per-triangle
edge wireframe must be suppressed on selection. Otherwise the red edges smother
the pink fill and the lens reads as solid red (the reported bug).

This pins the contract of ``Kraken3DInspector._set_row_actor_selected`` directly
on VTK actors, so it runs headless: building sources/mappers/actors and reading
back vtkProperty needs no X display and no full Tk app -- only ``Render()`` would.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_analytic_lens_select_not_all_red
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import vtk

from KrakenOS.UI.open3d_inspector import Kraken3DInspector

PINK = (1.0, 0.45, 0.65)  # selected body fill
RED = (1.0, 0.0, 0.0)     # selected sparse-surface outline edges


def _make_actor(*, opacity: float = 0.5, edge_visibility: int = 0) -> "vtk.vtkActor":
    src = vtk.vtkSphereSource()
    src.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(src.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(0.2, 0.3, 0.4)
    prop.SetOpacity(opacity)
    prop.SetEdgeVisibility(edge_visibility)
    prop.SetLineWidth(1.0)
    return actor


def _approx(a, b, tol: float = 1e-3) -> bool:
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def main() -> int:
    failures: list[str] = []

    # Case A -- the bug: a glassy analytic lens body must suppress its
    # per-triangle edges on selection and show the pink fill, not solid red.
    glassy = _make_actor()
    glassy._kraken_glassy_lens_body = True
    Kraken3DInspector._set_row_actor_selected(glassy, True)
    gp = glassy.GetProperty()
    if int(gp.GetEdgeVisibility()) != 0:
        failures.append(
            f"glassy lens body: edge visibility must be 0 on select (got {gp.GetEdgeVisibility()}) "
            "-- red triangle wireframe would smother the fill (all-red regression)"
        )
    if not _approx(gp.GetColor(), PINK):
        failures.append(
            f"glassy lens body: fill must be pink {PINK} (got {tuple(round(c, 3) for c in gp.GetColor())})"
        )

    # Case B -- existing behavior preserved: file-backed solid bodies still
    # suppress edges (this was the original penta-prism fix).
    file_backed = _make_actor()
    file_backed._kraken_file_backed_row_body = True
    Kraken3DInspector._set_row_actor_selected(file_backed, True)
    if int(file_backed.GetProperty().GetEdgeVisibility()) != 0:
        failures.append("file-backed solid body: edge visibility must be 0 on select (existing fix regressed)")

    # Case C -- intended outline preserved: a plain sparse surface (no body
    # flag) keeps the bright-red edge outline on selection.
    sparse = _make_actor()
    Kraken3DInspector._set_row_actor_selected(sparse, True)
    sp = sparse.GetProperty()
    if int(sp.GetEdgeVisibility()) != 1:
        failures.append("sparse surface: edge visibility must be 1 on select (red outline expected)")
    if not _approx(sp.GetEdgeColor(), RED):
        failures.append(
            f"sparse surface: edge color must be red {RED} (got {tuple(round(c, 3) for c in sp.GetEdgeColor())})"
        )

    # Case D -- deselect restores the captured baseline (edges back off).
    Kraken3DInspector._set_row_actor_selected(glassy, False)
    if int(glassy.GetProperty().GetEdgeVisibility()) != 0:
        failures.append("glassy lens body: deselect must restore baseline edge visibility (0)")

    if failures:
        print("[FAIL] analytic-lens selection all-red regression test")
        for item in failures:
            print("   -", item)
        return 1
    print(
        "[PASS] analytic-lens selection: glassy + file-backed bodies suppress edges "
        "(pink fill, not all-red); sparse surfaces keep the red outline; deselect restores baseline"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
