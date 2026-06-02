"""Regression (bug 0003): STEP promotion must not emit InvalidMeshWarning.

Imported STEP meshes carry per-triangle face-index cell arrays
(`kraken_step_face_index`, ...) sized to the source tessellation. The
promotion path runs `mesh.extract_surface(...).triangulate()` and saves an
STL; once the cell count changes those arrays go stale (wrong length) and
pyvista raises `InvalidMeshWarning` on the triangulate / STL save -- seen on
the aspheric achromat fixture (arrays length 2227 on a 1115-cell mesh).

`step_overlay_promotion._mesh_without_cell_data` drops the cell arrays before
the topology change (the STL output stores no cell data; face metadata is
recovered separately), removing the warning at the root.

This test is display-free. It injects a deliberately length-mismatched cell
array at the VTK layer (bypassing pyvista's assignment-time validation),
confirms the raw save warns, then confirms the fix makes the save warning-free.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_promotion_mesh_warning_free
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pyvista as pv
from vtkmodules.util.numpy_support import numpy_to_vtk

from KrakenOS.UI.services.step_overlay_promotion import _mesh_without_cell_data


def _box_polydata() -> pv.PolyData:
    box = pv.Box().triangulate()
    return pv.PolyData(box.points, box.faces)


def _inject_mismatched_cell_array(mesh: pv.PolyData) -> None:
    """Attach a `kraken_step_face_index` cell array that is too long for the
    mesh (the stale-array state), bypassing pyvista's length check."""
    bad = np.zeros(int(mesh.n_cells) * 2 + 1, dtype=np.int32)
    arr = numpy_to_vtk(bad, deep=True)
    arr.SetName("kraken_step_face_index")
    mesh.GetCellData().AddArray(arr)


def _save_warns(mesh: pv.PolyData) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "m.stl"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True).save(str(out))
        return any("InvalidMeshWarning" in type(w.message).__name__ or "incorrect length" in str(w.message) for w in caught)


def main() -> int:
    failures: list[str] = []

    # 1) A stale (length-mismatched) cell array trips the warning on the raw
    #    promotion chain -- proves the test is meaningful.
    stale = _box_polydata()
    _inject_mismatched_cell_array(stale)
    if int(stale.GetCellData().GetArray("kraken_step_face_index").GetNumberOfTuples()) == int(stale.n_cells):
        failures.append("could not construct a length-mismatched cell array (test setup)")
    elif not _save_warns(stale):
        failures.append("expected the raw chain on a stale-array mesh to emit InvalidMeshWarning, but it did not")

    # 2) _mesh_without_cell_data clears the arrays, so the same chain is
    #    warning-free.
    fixed = _mesh_without_cell_data(stale)
    remaining = list(fixed.cell_data.keys())
    if "kraken_step_face_index" in remaining:
        failures.append(f"_mesh_without_cell_data left kraken_step_* cell arrays: {remaining}")
    if _save_warns(fixed):
        failures.append("chain still emitted InvalidMeshWarning after _mesh_without_cell_data")

    # 3) The original mesh is untouched (helper works on a copy).
    if "kraken_step_face_index" not in [stale.GetCellData().GetArrayName(i) for i in range(stale.GetCellData().GetNumberOfArrays())]:
        failures.append("_mesh_without_cell_data mutated the input mesh (should copy)")

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}", file=sys.stderr)
        return 1
    print("PASS: STEP promotion mesh chain is InvalidMeshWarning-free after _mesh_without_cell_data; input mesh untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
