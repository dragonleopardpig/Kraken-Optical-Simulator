"""Display-backed smoke check for Open 3D STEP carry placement.

Run this under a real display or Xvfb. It opens the embedded Tk/VTK 3D
inspector, activates carry mode for a tracked vendor STEP file, verifies that
the carry grid and rotation handles are rendered, and applies one snapped drag
step through the same carry path used by the mouse bindings.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"


def _capture_widget(widget, output_path: Path) -> None:
    try:
        from PIL import ImageGrab
    except Exception as exc:
        raise RuntimeError(f"Pillow ImageGrab is required for snapshots: {exc}") from exc
    widget.update_idletasks()
    widget.update()
    x0 = int(widget.winfo_rootx())
    y0 = int(widget.winfo_rooty())
    x1 = x0 + int(widget.winfo_width())
    y1 = y0 + int(widget.winfo_height())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(max(0, x0), max(0, y0), x1, y1)).convert("RGB").save(output_path, optimize=True)


def _actor_input(actor) -> str:
    if actor is None:
        return ""
    try:
        return str(actor.GetInput())
    except Exception:
        return ""


def _cube_spacing_from_text(text: str) -> float | None:
    match = re.search(r"([0-9.]+)\s*mm cube grid|cube\s+([0-9.]+)\s*mm", text)
    if not match:
        return None
    value = match.group(1) or match.group(2)
    try:
        return float(value)
    except Exception:
        return None


def _open_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        reason = getattr(inspector, "unavailable_reason", "") if inspector is not None else "3D inspector did not open"
        raise RuntimeError(f"Embedded 3D inspector unavailable: {reason}")
    inspector.geometry("1280x860+80+60")
    inspector.deiconify()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.4)
    inspector.update()
    return inspector


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Optional PNG path for the smoke scene.")
    args = parser.parse_args()

    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected tracked STEP fixture: {PRISM_42779_STEP}")

    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1500x920+20+20")
        try:
            app.auto_save_plot_var.set(False)
        except Exception:
            pass
        app.imported_lens_step_path = PRISM_42779_STEP
        app.select_step_component("lens")
        inspector = _open_inspector(app)

        inspector.start_selected_step_carry()
        inspector.update_idletasks()
        inspector.update()
        if inspector._step_carry_label() != "lens":
            raise AssertionError("Open 3D did not enter lens STEP carry mode.")
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        inspector.update()
        if not getattr(inspector, "_actor_step_rotate_map", {}):
            raise AssertionError("STEP rotation handles were not present during carry mode.")
        status = str(inspector.status_var.get())
        if "STEP carry grid=" not in status:
            raise AssertionError(f"3D status did not report a STEP carry grid: {status!r}")
        try:
            grid_count = int(status.split("STEP carry grid=", 1)[1].split("|", 1)[0].strip())
        except Exception as exc:
            raise AssertionError(f"Could not parse STEP carry grid count from status: {status!r}") from exc
        if grid_count <= 0:
            raise AssertionError(f"Expected non-empty STEP carry grid, got {grid_count}.")
        badge_spacing = _cube_spacing_from_text(_actor_input(inspector._mode_badge_actor))
        grid_spacing = _cube_spacing_from_text(_actor_input(inspector._placement_grid_status_actor))
        if badge_spacing is None or grid_spacing is None or abs(badge_spacing - grid_spacing) > 1e-9:
            raise AssertionError(
                "STEP carry badge/grid spacing mismatch: "
                f"badge={badge_spacing!r}, grid={grid_spacing!r}."
            )

        state = inspector._step_carry_drag_state_from_current_press()
        if state is None:
            raise AssertionError("Could not create a STEP carry drag state from the live 3D inspector.")
        before = app._step_placement_offset_xyz("lens")
        inspector._step_carry_drag_state = state
        inspector._apply_step_carry_drag_motion(inspector._step_carry_pixels_per_grid_step() * 1.35, 0.0)
        after = app._step_placement_offset_xyz("lens")
        if before == after:
            raise AssertionError("STEP carry drag did not move the persistent lens placement offset.")
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        inspector.update()
        badge_spacing = _cube_spacing_from_text(_actor_input(inspector._mode_badge_actor))
        grid_spacing = _cube_spacing_from_text(_actor_input(inspector._placement_grid_status_actor))
        if badge_spacing is None or grid_spacing is None or abs(badge_spacing - grid_spacing) > 1e-9:
            raise AssertionError(
                "STEP carry badge/grid spacing mismatch after snapped drag: "
                f"badge={badge_spacing!r}, grid={grid_spacing!r}."
            )
        if args.snapshot is not None:
            inspector.update_idletasks()
            inspector.update()
            time.sleep(0.2)
            inspector.update()
            _capture_widget(inspector, args.snapshot)
    finally:
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        app.destroy()

    print("Open 3D STEP carry smoke validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
