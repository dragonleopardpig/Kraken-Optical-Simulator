"""Diagnostic for bugs/0441: which frame does the drawn Aperture ring live in,
pre vs post the 0433 freeze? Compares each surface mesh's SVD plane normal with
the row's MESH-convention local +Z (rotation_matrix_from_kraken_tilts)."""
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts


def normals_by_row(app, tag):
    print(f"--- {tag}")
    system = app.build_system(require_solids=True, force_rebuild=True)
    for item in app._iter_3d_surface_meshes(system, include_reference_surfaces=True):
        row_index = getattr(item, "row_index", None)
        mesh = getattr(item, "mesh", None)
        kind = getattr(item, "kind", "?")
        if row_index is None or mesh is None or row_index >= len(app.rows):
            continue
        row = app.rows[row_index]
        surf = str(getattr(row, "surface", "?"))
        if surf not in ("Aperture", "Standard", "Thin Lens"):
            continue
        try:
            pts = np.asarray(mesh.points, dtype=float)
            if pts.shape[0] < 3:
                continue
            c = pts.mean(axis=0)
            _u, _s, vh = np.linalg.svd(pts - c, full_matrices=False)
            n = vh[-1] / max(float(np.linalg.norm(vh[-1])), 1e-12)
            rot = rotation_matrix_from_kraken_tilts(
                float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)
            )
            zloc = rot @ np.array([0.0, 0.0, 1.0])
            dot = abs(float(n @ zloc))
            print(
                f"  row {row_index} {surf:9s} {str(getattr(row, 'name', ''))[:24]:26s} "
                f"kind={kind} center=({c[0]:7.1f},{c[1]:5.1f},{c[2]:7.1f}) "
                f"normal=({n[0]:+.2f},{n[1]:+.2f},{n[2]:+.2f}) |n.zmesh|={dot:.3f}"
            )
        except Exception as exc:  # pragma: no cover - diagnostic
            print(f"  row {row_index} {surf}: ERR {exc!r}")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        app.load_layout_by_name("az85")
        normals_by_row(app, "PRISTINE (live fold)")
        app.add_beam_splitter_to_led(kind="plate")
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        normals_by_row(app, "POST-FREEZE")
    finally:
        app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
