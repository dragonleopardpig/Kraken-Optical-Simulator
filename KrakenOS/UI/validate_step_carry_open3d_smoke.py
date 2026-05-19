"""Display-backed smoke check for Open 3D STEP carry placement.

Run this under a real display or Xvfb. It opens the embedded Tk/VTK 3D
inspector, activates carry mode for a tracked vendor STEP file, verifies that
free carry and rotation handles are available without drawing a cube lattice,
applies one free drag through the same carry path used by the mouse bindings,
and validates the explicit STEP-face-normal to optical-axis snap service.
"""

from __future__ import annotations

import argparse
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


def _activate_hold_drag(inspector: Kraken3DInspector, label: str = "optical") -> dict[str, object]:
    press_xy = (320, 260)
    inspector._cancel_step_carry_hold_timer()
    inspector._left_drag_active = True
    inspector._left_drag_moved = False
    inspector._left_drag_start_xy = press_xy
    inspector._left_drag_last_xy = press_xy
    inspector._step_carry_hold_candidate_label = label
    inspector._step_carry_hold_press_xy = press_xy
    inspector._step_carry_hold_pick_world = None
    inspector._activate_step_carry_hold()
    inspector.update_idletasks()
    inspector.update()
    state = inspector._step_carry_drag_state
    if not isinstance(state, dict):
        raise AssertionError("STEP carry hold-drag did not create a drag state.")
    if inspector._step_carry_follow_state is not None:
        raise AssertionError("STEP carry unexpectedly entered the removed pointer-follow mode.")
    if inspector._step_carry_grip_actor is None:
        raise AssertionError("STEP carry hold-drag did not draw the in-scene grip cursor.")
    for key in ("drag_plane_origin", "drag_plane_normal", "drag_anchor_world", "start_center_world"):
        if key not in state:
            raise AssertionError(f"STEP carry hold-drag state missing {key!r}.")
    return state


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
        app.imported_optical_step_path = PRISM_42779_STEP
        app.select_step_component("optical")
        inspector = _open_inspector(app)

        inspector.start_selected_step_carry()
        inspector.update_idletasks()
        inspector.update()
        if inspector._step_carry_label() != "optical":
            raise AssertionError("Open 3D did not enter optical STEP carry mode.")
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        inspector.update()
        if not getattr(inspector, "_actor_step_rotate_map", {}):
            raise AssertionError("STEP rotation handles were not present during carry mode.")
        status = str(inspector.status_var.get())
        if "STEP carry active=1" not in status:
            raise AssertionError(f"3D status did not report active free STEP carry: {status!r}")
        if inspector._step_carry_grid_mode() != "Free":
            raise AssertionError("STEP carry should default to Free movement.")
        if "free plane movement" not in _actor_input(inspector._placement_grid_status_actor):
            raise AssertionError("STEP carry Free mode did not appear in the 3D status overlay.")

        inspector.step_carry_grid_var.set("Free")
        inspector._on_step_carry_grid_selected()
        inspector.update_idletasks()
        inspector.update()
        _activate_hold_drag(inspector, "optical")
        hold_before = app._step_placement_offset_xyz("optical")
        inspector._apply_step_carry_drag_motion(0.0, 0.0, current_xy=(620, 260))
        hold_after = app._step_placement_offset_xyz("optical")
        if hold_before == hold_after:
            inspector._apply_step_carry_drag_motion(0.0, 0.0, current_xy=(900, 260))
            hold_after = app._step_placement_offset_xyz("optical")
        if hold_before == hold_after:
            raise AssertionError("STEP carry drag-plane motion did not move persistent placement offset.")
        if inspector._step_carry_drag_state is not None:
            inspector._finish_step_carry_drag(inspector._step_carry_drag_state)

        state = _activate_hold_drag(inspector, "optical")
        before = app._step_placement_offset_xyz("optical")
        inspector._step_carry_drag_state = state
        inspector._apply_step_carry_drag_motion(0.0, 0.0, current_xy=(620, 260))
        after = app._step_placement_offset_xyz("optical")
        if before == after:
            inspector._apply_step_carry_drag_motion(0.0, 0.0, current_xy=(900, 260))
            after = app._step_placement_offset_xyz("optical")
        if before == after:
            raise AssertionError("STEP carry drag plane did not move the persistent optical placement offset.")
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        inspector.update()
        if "free plane movement" not in _actor_input(inspector._placement_grid_status_actor):
            raise AssertionError("STEP carry Free status disappeared after drag.")
        if inspector._step_carry_drag_state is not None:
            inspector._finish_step_carry_drag(inspector._step_carry_drag_state)
        mesh = app._transformed_imported_step_mesh_for_label("optical")
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            raise AssertionError("STEP mesh unavailable for normal-to-axis snap validation.")
        center = mesh.center
        normal_before = app._step_rotation_deg_tuple("optical")
        result = app.snap_step_feature_normal_to_optical_axis("optical", center, (1.0, 0.0, 0.0))
        if result is None:
            raise AssertionError("STEP normal-to-axis snap did not return a result.")
        if app._step_rotation_deg_tuple("optical") == normal_before:
            raise AssertionError("STEP normal-to-axis snap did not update STEP rotation state.")
        if args.snapshot is not None:
            inspector.update_idletasks()
            inspector.update()
            time.sleep(0.2)
            inspector.update()
            _capture_widget(inspector, args.snapshot)
        inspector.stop_step_carry()
        if inspector._step_carry_label() is not None:
            raise AssertionError("Drop STEP carry did not leave carry mode.")
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
