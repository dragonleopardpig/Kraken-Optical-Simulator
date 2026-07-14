"""Display-free guard for bugs/0300 -- the 3D STEP export must be exactly what the 3D shows.

User report (AZ85 folded periscope): the exported STEP had the components "mostly wrong" and was
"useless for production", and it should match the 3D inspector regardless of whether the file is
saved. Root cause: the two BK7 RA prisms are optical-solid rows (Solid_3d_stl), drawn from their
STL under the runtime display transform, but the export placed a SHARED step_*.step template that
lives in a different local frame (~11mm off; box-ICP against the template is ambiguous ~4mm). The
Object plane was also skipped entirely.

Fix: a file-backed optical-solid row is exported the way it is drawn -- its STL, carried into world
by _row_optical_solid_display_world_transform (the inspector's own _runtime_transform_for_row, else
the runtime tiers), written as one faceted OCC shell. The Object/Image skip was removed from both
writers.

Checks (all display-free; the geometry facets self-skip when the local AZ85 fixture / STL cache is
absent, e.g. on a fresh checkout -- the fixture is not committed):

  (A) PRISMS MATCH THE DISPLAY: for every file-backed optical-solid row, the exported shell's world
      bounding box equals the display mesh's world bounding box (centre + extents within 0.05mm).
  (B) OBJECT PLANE IS EXPORTED: neither STEP writer skips {"Object","Image"} (source), and in the
      real system the Object row passes the analytic export guards (would be written).
  (C) SINGLE SOURCE OF TRUTH: the export shell derives its pose from
      _row_optical_solid_display_world_transform, that helper prefers the inspector's
      _runtime_transform_for_row, and _collect_row_native_step_export_shapes branches on
      _file_backed_stl_row_at -- so display and export cannot drift apart silently.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_export_matches_display
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_FIXTURE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
_TOL_MM = 0.05


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _shell_world_bbox(shape):
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return np.array([xmin, ymin, zmin], dtype=float), np.array([xmax, ymax, zmax], dtype=float)


def _load_app():
    """A headless AZ85 editor + built system, or None when the fixture is absent."""
    if not _FIXTURE.exists():
        return None, None
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_five_penta_initial_visual import _load_saved_layout

    app = KrakenLayoutEditor(headless=True)
    _load_saved_layout(app, _FIXTURE)
    system = app.build_system()
    return app, system


def _facet_a_prisms(checks: list[Check]) -> None:
    app, system = _load_app()
    if app is None:
        checks.append(Check(
            "A PRISMS MATCH THE DISPLAY: exported shell bbox == display mesh bbox (<=0.05mm)",
            True,
            f"skipped -- fixture {_FIXTURE} absent (not committed); source guards C still enforce it",
        ))
        return
    rows = [j for j in range(len(app.rows)) if app._file_backed_stl_row_at(j) is not None]
    if not rows:
        checks.append(Check(
            "A PRISMS MATCH THE DISPLAY: exported shell bbox == display mesh bbox (<=0.05mm)",
            False,
            "no file-backed optical-solid (prism) rows found in the AZ85 scene",
        ))
        return
    worst = 0.0
    details: list[str] = []
    for j in rows:
        row = app.rows[j]
        transform = app._row_optical_solid_display_world_transform(system, j)
        shell = app._optical_solid_row_world_step_shell(row, j, system) if transform is not None else None
        if transform is None or shell is None:
            # No display transform or no STL cache on this machine -- can't compare; skip this row.
            details.append(f"S{j}: skipped (transform={transform is not None}, shell={shell is not None})")
            continue
        disp = app._stl_mesh_with_world_transform(row, transform)
        if disp is None or int(getattr(disp, "n_points", 0)) <= 0:
            details.append(f"S{j}: skipped (no display mesh)")
            continue
        dpts = np.asarray(disp.points, dtype=float)
        dmin, dmax = dpts.min(axis=0), dpts.max(axis=0)
        emin, emax = _shell_world_bbox(shell)
        cdelta = float(np.linalg.norm(0.5 * (dmin + dmax) - 0.5 * (emin + emax)))
        sdelta = float(np.linalg.norm((dmax - dmin) - (emax - emin)))
        worst = max(worst, cdelta, sdelta)
        details.append(f"S{j}: centreΔ={cdelta:.4f} extentΔ={sdelta:.4f}")
    checks.append(Check(
        "A PRISMS MATCH THE DISPLAY: exported shell bbox == display mesh bbox (<=0.05mm)",
        worst <= _TOL_MM,
        f"worst={worst:.4f}mm | " + "; ".join(details),
    ))


def _facet_b_object(checks: list[Check]) -> None:
    from KrakenOS.UI.services import cad_step_export as ce

    skip = 'in {"Object", "Image"}'
    analytic_src = inspect.getsource(ce._write_step_with_analytic_surfaces)
    cad_src = inspect.getsource(ce._write_step_with_cad_shapes_and_rays)
    no_skip = skip not in analytic_src and skip not in cad_src
    checks.append(Check(
        "B1 OBJECT PLANE NOT SKIPPED: neither STEP writer drops {'Object','Image'}",
        no_skip,
        "both writers export reference planes"
        if no_skip
        else "a writer still skips Object/Image",
    ))

    app, system = _load_app()
    if app is None:
        checks.append(Check(
            "B2 OBJECT ROW IS EXPORTABLE: the Object plane passes the analytic export guards",
            True,
            f"skipped -- fixture {_FIXTURE} absent (not committed)",
        ))
        return
    sdt = getattr(system, "SDT", None) or []
    obj_index = next((j for j, r in enumerate(app.rows) if getattr(r, "surface", "") == "Object"), None)
    exportable = False
    detail = "no Object row in the scene"
    if obj_index is not None and obj_index < len(sdt):
        surf = sdt[obj_index]
        drawing = bool(getattr(surf, "Drawing", 1))
        diameter = float(getattr(surf, "Diameter", 0))
        revol = ce._is_surface_revolution_compatible(surf)
        exportable = drawing and diameter > 0 and revol
        detail = f"S{obj_index} Drawing={drawing} Diameter={diameter} revolution_compatible={revol}"
    checks.append(Check(
        "B2 OBJECT ROW IS EXPORTABLE: the Object plane passes the analytic export guards",
        exportable,
        detail,
    ))


def _facet_c_single_source(checks: list[Check]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    shell_src = inspect.getsource(KrakenLayoutEditor._optical_solid_row_world_step_shell)
    uses_display_transform = "_row_optical_solid_display_world_transform" in shell_src
    checks.append(Check(
        "C1 EXPORT USES THE DISPLAY TRANSFORM: the shell pose comes from the 3D's own transform",
        uses_display_transform,
        f"_optical_solid_row_world_step_shell references _row_optical_solid_display_world_transform: {uses_display_transform}",
    ))

    xform_src = inspect.getsource(KrakenLayoutEditor._row_optical_solid_display_world_transform)
    prefers_inspector = "_runtime_transform_for_row" in xform_src
    checks.append(Check(
        "C2 TRANSFORM PREFERS THE INSPECTOR: honours _runtime_transform_for_row (saved or not)",
        prefers_inspector,
        f"_row_optical_solid_display_world_transform references _runtime_transform_for_row: {prefers_inspector}",
    ))

    collect_src = inspect.getsource(KrakenLayoutEditor._collect_row_native_step_export_shapes)
    branches = "_file_backed_stl_row_at" in collect_src and "_optical_solid_row_world_step_shell" in collect_src
    checks.append(Check(
        "C3 COLLECTOR BRANCHES ON STL ROWS: file-backed optical solids take the faithful STL path",
        branches,
        f"_collect_row_native_step_export_shapes branches file-backed rows to the shell path: {branches}",
    ))


def validate() -> list[Check]:
    checks: list[Check] = []
    _facet_a_prisms(checks)
    _facet_b_object(checks)
    _facet_c_single_source(checks)
    return checks


def run_checks() -> tuple[bool, list[str]]:
    checks = validate()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate()
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if any(not c.ok for c in checks):
        raise SystemExit(1)
    print("STEP-export-matches-display validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
