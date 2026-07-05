"""Display-free guard: the bug recorder captures DIALOG-level actions, not just canvas events.

The recorder only hooks the 3D VTK canvas (mouse press/release/move), so a flagged workflow that
ran through a Tk dialog -- the FOV plane DOUBLE-CLICK that opens the popup, the typed field values,
and the "Solve for Thickness" / "Apply split" buttons -- was INVISIBLE in the replay (it looked like
bare canvas clicks; the user: "shouldn't your full recording recorded all these?"). The recorder
already has a `record_command(label, payload)` API; the fix routes the dialog action points through
a `_record_dialog_command` helper so they appear as command events.

  (A) CAPTURE: record_command appends a "command" event with the label + payload (the plane, the
      solve mode + field values, the split leg + value).
  (B) WIRED: the FOV double-click, the FOV solve, and the fold-split apply all call
      _record_dialog_command; the helper routes to record_command.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_recorder_captures_dialogs
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types
from dataclasses import dataclass

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.open3d_event_recorder import Open3DEventRecorder


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def validate_recorder_captures_dialogs() -> list[Check]:
    checks: list[Check] = []

    # ---- (A) record_command captures a dialog action -------------------------------------- #
    rec = Open3DEventRecorder(types.SimpleNamespace())
    rec._snapshot_scene = lambda: None  # bypass the inspector snapshot for the unit test
    rec.recording = True
    rec.events = []
    rec._t0 = 0.0
    rec.record_command("fov_popup_open", {"plane": "object", "row": 0})
    rec.record_command("fov_solve", {"plane": "object", "mode": "thickness", "width": 55.0, "height": 55.0})
    rec.record_command("fold_split_apply", {"plane": "object", "leg": "far", "value": 50.0})
    labels = [e.label for e in rec.events]
    kinds = {e.kind for e in rec.events}
    solve_ev = next((e for e in rec.events if e.label == "fov_solve"), None)
    checks.append(Check(
        "CAPTURE: record_command logs the dialog actions with their field values",
        len(rec.events) == 3
        and kinds == {"command"}
        and labels == ["fov_popup_open", "fov_solve", "fold_split_apply"]
        and solve_ev is not None
        and solve_ev.payload.get("width") == 55.0,
        f"events={len(rec.events)} labels={labels} solve_payload={None if solve_ev is None else solve_ev.payload}",
    ))

    # ---- (B) the dialog action points are wired to the recorder --------------------------- #
    helper = inspect.getsource(Kraken3DInspector._record_dialog_command)
    dbl = inspect.getsource(Kraken3DInspector._maybe_open_fov_popup_from_double_click)
    solve = inspect.getsource(Kraken3DInspector._apply_quick_estimation_fov_solve)
    section = inspect.getsource(Kraken3DInspector._add_folded_conjugate_split_section)
    wired = (
        "record_command" in helper
        and '_record_dialog_command("fov_popup_open"' in dbl
        and "_record_dialog_command(" in solve
        and '"fov_solve"' in solve
        and "_record_dialog_command(" in section
        and '"fold_split_apply"' in section
    )
    checks.append(Check(
        "WIRED: the FOV double-click, the FOV solve, and the fold-split apply record dialog commands",
        wired,
        f"helper={'record_command' in helper} dblclick={'fov_popup_open' in dbl} "
        f"solve={'fov_solve' in solve} split={'fold_split_apply' in section}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_recorder_captures_dialogs()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_recorder_captures_dialogs()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Recorder-captures-dialogs validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
