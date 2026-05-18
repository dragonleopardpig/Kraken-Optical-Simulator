"""Validate in-scene STEP rotation handle generation and write-through."""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


def main() -> int:
    le._load_3d_backends()
    if le.pv is None:
        raise RuntimeError("PyVista is required for STEP rotation handle validation.")

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_lens_step_path = Path("/tmp/kraken-validation-lens.step")
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
        if count != 6 or len(records) != 6:
            raise AssertionError(f"Expected six STEP rotation handles, got count={count}, records={len(records)}.")
        rotate_specs = sorted(
            tuple(record[1].get("pick_step_rotate", ())) for record in records
        )
        expected_specs = sorted(
            (
                ("lens", "x", -90.0),
                ("lens", "x", 90.0),
                ("lens", "y", -90.0),
                ("lens", "y", 90.0),
                ("lens", "z", -90.0),
                ("lens", "z", 90.0),
            )
        )
        if rotate_specs != expected_specs:
            raise AssertionError(f"Unexpected STEP rotation pick specs: {rotate_specs!r}")
        if any(int(getattr(record[0], "n_points", 0)) <= 0 for record in records):
            raise AssertionError("A STEP rotation handle mesh was empty.")

        inspector._apply_step_rotation_handle("lens", "x", 90.0)
        inspector._apply_step_rotation_handle("lens", "y", -90.0)
        inspector._apply_step_rotation_handle("lens", "z", 90.0)
        if (
            float(app.lens_step_rotation_x_deg) != 90.0
            or float(app.lens_step_rotation_y_deg) != 270.0
            or float(app.lens_step_rotation_z_deg) != 90.0
        ):
            raise AssertionError(
                "STEP rotation handles did not write through to the persistent lens STEP rotation state."
            )
        if app._selected_step_label != "lens" or inspector._step_rotation_active_label != "lens":
            raise AssertionError("STEP rotation handle did not preserve the selected STEP component.")
    finally:
        app.destroy()

    print("STEP rotation handle validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
