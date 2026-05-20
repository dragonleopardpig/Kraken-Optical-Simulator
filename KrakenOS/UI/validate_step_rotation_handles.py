"""Validate in-scene STEP rotation handle generation and write-through."""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"


def main() -> int:
    le._load_3d_backends()
    if le.pv is None:
        raise RuntimeError("PyVista is required for STEP rotation handle validation.")
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_lens_step_path = PRISM_42779_STEP
        app.select_step_component("lens")

        inspector = Kraken3DInspector.__new__(Kraken3DInspector)
        inspector.editor = app
        inspector.status_var = app.status_var
        inspector._step_rotation_active_label = None

        records: list[tuple[object, dict[str, object]]] = []

        def record_actor(mesh, **kwargs):
            records.append((mesh, kwargs))
            return object()

        inspector._add_mesh_actor = record_actor  # type: ignore[method-assign]

        mesh = le.pv.Cube(center=(3.0, -2.0, 25.0), x_length=8.0, y_length=5.0, z_length=12.0)
        center_extent = Kraken3DInspector._step_rotation_handle_center_and_extent(mesh)
        if center_extent is None:
            raise AssertionError("Expected a center/extent for the synthetic STEP mesh.")
        center, extent = center_extent
        if tuple(round(float(value), 6) for value in center) != (3.0, -2.0, 25.0):
            raise AssertionError(f"Unexpected handle center: {center!r}")
        if round(float(extent), 6) != 12.0:
            raise AssertionError(f"Unexpected handle extent: {extent!r}")

        count = inspector._add_step_rotation_handles("lens", mesh)
        if count != 3 or len(records) != 3:
            raise AssertionError(f"Expected three STEP rotation handles, got count={count}, records={len(records)}.")
        rotate_specs = sorted(
            tuple(record[1].get("pick_step_rotate", ())) for record in records
        )
        expected_specs = sorted(
            (
                ("lens", "x", 90.0),
                ("lens", "y", 90.0),
                ("lens", "z", 90.0),
            )
        )
        if rotate_specs != expected_specs:
            raise AssertionError(f"Unexpected STEP rotation pick specs: {rotate_specs!r}")
        if any(int(getattr(record[0], "n_points", 0)) <= 0 for record in records):
            raise AssertionError("A STEP rotation handle mesh was empty.")
        if not any(int(getattr(record[0], "n_cells", 0)) > 32 for record in records):
            raise AssertionError("STEP rotation handles did not include arrowhead geometry.")

        for axis in ("x", "y", "z"):
            app._set_step_rotation_deg_tuple("lens", (25.0, 40.0, 65.0))
            before_matrix = app._step_rotation_matrix_from_angles(*app._step_rotation_deg_tuple("lens"))
            expected_matrix = app._world_axis_rotation_matrix(axis, 90.0) @ before_matrix
            center_before = tuple(round(float(value), 6) for value in app._transformed_imported_step_mesh_for_label("lens").center)
            inspector._apply_step_rotation_handle("lens", axis, 90.0)
            center_after = tuple(round(float(value), 6) for value in app._transformed_imported_step_mesh_for_label("lens").center)
            after_matrix = app._step_rotation_matrix_from_angles(*app._step_rotation_deg_tuple("lens"))
            if not le.np.allclose(after_matrix, expected_matrix, atol=1e-8):
                raise AssertionError(f"STEP {axis.upper()} handle did not apply a world-axis rotation.")
            if center_before != center_after:
                raise AssertionError(
                    "STEP rotation handles should rotate immediately around the component center, "
                    f"got before={center_before}, after={center_after} for axis {axis!r}."
                )
        if app._selected_step_label != "lens" or inspector._step_rotation_active_label != "lens":
            raise AssertionError("STEP rotation handle did not preserve the selected STEP component.")

        app._set_step_rotation_deg_tuple("lens", (0.0, 0.0, 0.0))
        app._set_step_placement_offset_xyz("lens", (0.0, 0.0, 0.0))
        app.translate_step_overlay("lens", (1.0, -2.0, 3.0), grid_spacing_mm=1.0)
        if app._step_placement_offset_xyz("lens") != (1.0, -2.0, 3.0):
            raise AssertionError("STEP carry placement did not write persistent 3D placement offset state.")
    finally:
        app.destroy()

    print("STEP rotation handle validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
