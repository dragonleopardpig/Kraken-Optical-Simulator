"""Validate the lightweight Open 3D STEP carry state path.

This check does not open VTK. It verifies that snapped STEP carry motion can
persist placement offsets without forcing a full Open 3D scene rebuild on every
mouse snap step. The inspector layer then moves already-rendered actors in
place and performs one authoritative refresh on Drop.
"""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_lens_step_path = Path("/tmp/kraken-validation-arbitrary-optical.step")
        app.lens_step_largest_component_only = False
        calls: list[tuple[bool, str | None]] = []

        def _fake_refresh(*, camera_only: bool = False, step_label: str | None = None) -> None:
            calls.append((bool(camera_only), step_label))

        app._refresh_open_3d_views = _fake_refresh  # type: ignore[method-assign]

        app.translate_step_overlay(
            "lens",
            (1.0, 2.0, 3.0),
            grid_spacing_mm=1.0,
            refresh=False,
            record_history=False,
        )
        if calls:
            raise AssertionError(f"Lightweight carry unexpectedly refreshed Open 3D: {calls!r}")
        if app._step_placement_offset_xyz("lens") != (1.0, 2.0, 3.0):
            raise AssertionError("Lightweight carry did not persist the STEP placement offset.")
        if app.lens_step_largest_component_only is not False:
            raise AssertionError("Arbitrary optical STEP import mode did not preserve all STEP components.")

        app.translate_step_overlay("lens", (0.0, 0.0, 1.0), refresh=True, record_history=True)
        if calls != [(False, "lens")]:
            raise AssertionError(f"Explicit STEP translate refresh did not target the lens/optical overlay: {calls!r}")
        if app._step_placement_offset_xyz("lens") != (1.0, 2.0, 4.0):
            raise AssertionError("Explicit STEP translate did not persist the final placement offset.")
    finally:
        app.destroy()

    print("STEP carry lightweight validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
