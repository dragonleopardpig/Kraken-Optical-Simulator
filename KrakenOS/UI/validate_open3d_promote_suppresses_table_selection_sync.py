"""Display-free guard: promoting a STEP solid must NOT pink a distant element's
datum via a table-selection 3-D sync against the mid-rebuild actor map (bug 0145).

Background
----------
A row highlight pinks every actor whose ``_actor_row_map[key]`` equals the
selected row index (``open3d_selection_representation.apply_row_selection``). The
ONLY way a promote can pink the wrong element is a ``highlight_row`` driven from
``_sync_surface_selection`` (the table-selection -> 3-D bridge) while the inspector
is mid-promote: the retrace+refresh has not yet repopulated ``_actor_row_map``, so
that index still names whatever sat there in the PRE-promote scene -- the upstream
imaging lens's "Lens Front Datum".

Bug 0139 removed the *synchronous* ``_select_table_row`` trigger from the
promote-and-assign caller. But ``_select_table_indices`` / ``_sync_table`` still
schedule a deferred ``<<TreeviewSelect>>`` sync, and on the slow beam-splitter
promote that deferred sync lands WHILE the map is stale -> the lens datum flashes
pink for the whole frozen promote. (The user could not screenshot it: the promote
is synchronous, so the flag key cannot fire mid-promote.)

Fix
---
``_sync_surface_selection`` now skips the Open 3-D ``highlight_row`` when
``_suppress_3d_row_selection_sync`` is set, and
``_promote_step_and_assign_face_function`` sets that flag across the whole
promote+refresh (cleared in ``finally``). The promote still does its OWN
authoritative highlight against the FRESH map -- the scene rebuild's re-apply and
an explicit ``inspector.highlight_row`` -- both DIRECT calls that bypass
``_sync_surface_selection``, so only the stale flash is dropped. The 2-D layout
overlay + status sync are untouched (suppression is surgical to the 3-D pink).

This guard, with no rendering, drives the REAL methods with fake selves to pin:

  1. BUG PATH -- with the flag unset, a table-selection sync DOES call the
     inspector's ``highlight_row`` (this is the path that, mid-promote, pinks the
     lens).
  2. FIX -- with the flag set, the same sync does NOT call ``highlight_row``.
  3. SURGICAL -- with the flag set, the 2-D layout-selection overlay + status are
     STILL updated (suppression drops only the 3-D pink, not all selection
     feedback).
  4. WRAPPER (normal) -- the real ``_promote_step_and_assign_face_function`` sets
     the flag True for the duration of the inner body and clears it to False after.
  5. WRAPPER (finally) -- if the inner body raises, the flag is STILL cleared (a
     stuck flag would mute all later selection highlighting).
  6. SOURCE WIRING -- the gate + the set/finally-clear exist in source.

Penta phase 134 (baseline -> 134).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService


class _FakeInspector3D:
    available = True

    def __init__(self) -> None:
        self.highlight_calls: list = []

    def winfo_exists(self) -> bool:
        return True

    def highlight_row(self, row_index) -> None:
        self.highlight_calls.append(row_index)


class _FakeWorkbench:
    """Carries only what the real ``_sync_surface_selection`` reads/writes."""

    def __init__(self, *, suppress: bool) -> None:
        self._layout_selected_ray_index = 7
        self._three_d_inspector = _FakeInspector3D()
        self._legacy_3d_plotter = None
        self._suppress_3d_row_selection_sync = suppress
        self.rows = [SimpleNamespace(name=f"row{i}") for i in range(4)]
        self.overlay_calls: list = []
        self.status_texts: list = []
        self.status_var = SimpleNamespace(set=self.status_texts.append)

    def _update_layout_selection_overlay(self, row_index) -> None:
        self.overlay_calls.append(row_index)


class _FakeEditorFlagHolder:
    def __init__(self) -> None:
        self._suppress_3d_row_selection_sync = False


class _FakeFaceService:
    """Drives the REAL promote wrapper; records the flag seen INSIDE the inner."""

    def __init__(self, *, inner_raises: bool = False) -> None:
        self.editor = _FakeEditorFlagHolder()
        self.inner_called = False
        self.flag_during_inner = None
        self._inner_raises = inner_raises

    def _promote_step_and_assign_face_function_inner(self, *_args, **_kwargs) -> None:
        self.inner_called = True
        self.flag_during_inner = bool(self.editor._suppress_3d_row_selection_sync)
        if self._inner_raises:
            raise RuntimeError("inner blew up")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        status = "PASS" if passed else "FAIL"
        notes.append(f"{name} | {status}" + (f" | {detail}" if detail else ""))

    sync = LayoutTableWorkbenchMixin._sync_surface_selection
    promote = Open3DFaceAssignmentService._promote_step_and_assign_face_function

    # 1) BUG PATH: flag unset -> the table-selection sync drives highlight_row -----
    wb_open = _FakeWorkbench(suppress=False)
    sync(wb_open, 1, from_table=True)
    record(
        "unsuppressed table-selection sync DOES highlight the 3-D row",
        wb_open._three_d_inspector.highlight_calls == [1],
        f"highlight_calls={wb_open._three_d_inspector.highlight_calls}",
    )

    # 2) FIX: flag set -> the same sync does NOT touch the 3-D highlight -----------
    wb_supp = _FakeWorkbench(suppress=True)
    sync(wb_supp, 1, from_table=True)
    record(
        "suppressed table-selection sync skips the stale 3-D highlight",
        wb_supp._three_d_inspector.highlight_calls == [],
        f"highlight_calls={wb_supp._three_d_inspector.highlight_calls}",
    )

    # 3) SURGICAL: suppression drops ONLY the 3-D pink, not 2-D feedback -----------
    surgical = (
        wb_supp.overlay_calls == [1]
        and any("Selected row 1" in text for text in wb_supp.status_texts)
    )
    record(
        "suppression keeps the 2-D layout overlay + status sync",
        surgical,
        f"overlay_calls={wb_supp.overlay_calls} status={wb_supp.status_texts}",
    )

    # 4) WRAPPER (normal): flag True during inner, cleared to False after ----------
    svc = _FakeFaceService()
    promote(svc, "optical", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), "Partial Reflecting / Transmitting", face_id="S001/F001")
    wrapper_normal = (
        svc.inner_called
        and svc.flag_during_inner is True
        and svc.editor._suppress_3d_row_selection_sync is False
    )
    record(
        "promote wrapper sets the flag for the inner body and clears it after",
        wrapper_normal,
        f"inner_called={svc.inner_called} during={svc.flag_during_inner} "
        f"after={svc.editor._suppress_3d_row_selection_sync}",
    )

    # 5) WRAPPER (finally): a raising inner still clears the flag ------------------
    svc_boom = _FakeFaceService(inner_raises=True)
    raised = False
    try:
        promote(svc_boom, "optical", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), "Partial Reflecting / Transmitting")
    except RuntimeError:
        raised = True
    record(
        "promote wrapper clears the flag even when the inner body raises",
        raised
        and svc_boom.flag_during_inner is True
        and svc_boom.editor._suppress_3d_row_selection_sync is False,
        f"raised={raised} during={svc_boom.flag_during_inner} "
        f"after={svc_boom.editor._suppress_3d_row_selection_sync}",
    )

    # 6) SOURCE WIRING ------------------------------------------------------------
    wb_src = (Path(__file__).resolve().parent / "services" / "layout_table_workbench.py").read_text(encoding="utf-8")
    fa_src = (Path(__file__).resolve().parent / "services" / "open3d_face_assignment.py").read_text(encoding="utf-8")
    gate = 'getattr(self, "_suppress_3d_row_selection_sync", False)' in wb_src and "not suppress_3d_sync" in wb_src
    set_flag = "self.editor._suppress_3d_row_selection_sync = True" in fa_src
    clear_in_finally = (
        "finally:" in fa_src and "self.editor._suppress_3d_row_selection_sync = False" in fa_src
    )
    calls_inner = "_promote_step_and_assign_face_function_inner(" in fa_src
    record(
        "source: sync gated on the flag; wrapper sets + finally-clears it",
        gate and set_flag and clear_in_finally and calls_inner,
        f"gate={gate} set={set_flag} finally_clear={clear_in_finally} inner={calls_inner}",
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] promote suppresses the stale table-selection 3-D highlight (bug 0145)"
        if ok
        else "[FAIL] promote stale-highlight suppression regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
