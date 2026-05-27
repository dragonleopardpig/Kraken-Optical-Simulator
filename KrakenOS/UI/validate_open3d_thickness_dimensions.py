"""Validate Open 3D Thickness dimension service behavior without VTK/Tk."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService


@dataclass
class _Row:
    name: str
    surface: str
    thickness: float


class _StatusVar:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def set(self, message: str) -> None:
        self.messages.append(str(message))


class _Editor:
    def __init__(self) -> None:
        self.rows = [
            _Row("Object", "Object", 10.0),
            _Row("Lens front", "Standard", 5.0),
            _Row("Image", "Image", 0.0),
        ]
        self.status_var = _StatusVar()
        self.history_begin = 0
        self.history_commit = 0
        self.table_syncs = 0
        self.selected_rows: list[int] = []
        self.invalidations = 0
        self.badge_syncs = 0
        self.debug: list[str] = []

    def _begin_history_capture(self) -> None:
        self.history_begin += 1

    def _sync_table(self) -> None:
        self.table_syncs += 1

    def _select_table_row(self, row_index: int) -> None:
        self.selected_rows.append(int(row_index))

    def _commit_history_capture(self) -> None:
        self.history_commit += 1

    def _invalidate_preview_scene_trace(self) -> None:
        self.invalidations += 1

    def _sync_trace_state_badge(self) -> None:
        self.badge_syncs += 1

    def append_debug(self, message: str) -> None:
        self.debug.append(str(message))


class _Inspector:
    def __init__(self) -> None:
        self.editor = _Editor()
        self.status_var = _StatusVar()
        self.refreshes: list[bool] = []
        self._renderer = None

    def refresh_from_editor(self, *, force_retrace: bool = False) -> None:
        self.refreshes.append(bool(force_retrace))


def _new_service() -> tuple[Open3DThicknessDimensionService, _Inspector]:
    inspector = _Inspector()
    return Open3DThicknessDimensionService(inspector, pv_module=None, billboard_text_actor_cls=None), inspector


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    side = Open3DThicknessDimensionService.offset_direction(np.asarray((0.0, 0.0, 25.0), dtype=float))
    checks.append(("offset direction is finite", bool(np.all(np.isfinite(side))), repr(side)))
    checks.append(("offset direction is normalized", abs(float(np.linalg.norm(side)) - 1.0) < 1e-9, repr(side)))
    checks.append(("offset direction is perpendicular to segment", abs(float(np.dot(side, (0.0, 0.0, 1.0)))) < 1e-9, repr(side)))

    service, inspector = _new_service()
    ok = service.apply_dimension_value(0, 12.5)
    checks.append(("numeric edit succeeds", ok, inspector.status_var.messages[-1] if inspector.status_var.messages else ""))
    checks.append(("only selected row thickness changes", [row.thickness for row in inspector.editor.rows] == [12.5, 5.0, 0.0], repr(inspector.editor.rows)))
    checks.append(("edit synchronizes table once", inspector.editor.table_syncs == 1, str(inspector.editor.table_syncs)))
    checks.append(("edit selects the edited row", inspector.editor.selected_rows == [0], repr(inspector.editor.selected_rows)))
    checks.append(("edit retraces Open 3D once", inspector.refreshes == [True], repr(inspector.refreshes)))

    before = [row.thickness for row in inspector.editor.rows]
    bad = service.apply_dimension_value(1, float("nan"))
    checks.append(("non-finite edit is rejected", bad is False, repr(bad)))
    checks.append(("rejected edit preserves all thickness rows", [row.thickness for row in inspector.editor.rows] == before, repr(inspector.editor.rows)))

    service, inspector = _new_service()
    drag_state = {
        "row_index": 1,
        "initial_thickness": 5.0,
        "pending_thickness": 5.0,
        "display_direction": (1.0, 0.0),
        "mm_per_pixel": 0.25,
        "signed_pixels": 0.0,
        "moved": False,
    }
    service.apply_drag_motion(drag_state, 8, 0)
    service.apply_drag_motion(drag_state, 4, 0)
    checks.append(("drag accumulates signed motion", abs(float(drag_state["pending_thickness"]) - 8.0) < 1e-9, repr(drag_state)))
    service.finish_drag(drag_state)
    checks.append(("drag release commits only dragged row", [row.thickness for row in inspector.editor.rows] == [10.0, 8.0, 0.0], repr(inspector.editor.rows)))
    checks.append(("drag release retraces once", inspector.refreshes == [True], repr(inspector.refreshes)))

    service, inspector = _new_service()
    no_change_state = {
        "row_index": 0,
        "initial_thickness": 10.0,
        "pending_thickness": 10.0,
        "display_direction": (0.0, 1.0),
        "mm_per_pixel": 0.5,
        "signed_pixels": 0.0,
        "moved": False,
    }
    service.finish_drag(no_change_state)
    checks.append(("zero-change drag does not rewrite the table", inspector.editor.table_syncs == 0, str(inspector.editor.table_syncs)))
    checks.append(("zero-change drag does not retrace", inspector.refreshes == [], repr(inspector.refreshes)))

    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D thickness dimension validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print("Open 3D thickness dimension validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
