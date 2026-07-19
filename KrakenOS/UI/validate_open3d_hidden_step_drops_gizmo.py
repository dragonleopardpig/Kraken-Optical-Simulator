"""Guard for bugs/0136 -- hiding a STEP element tears down its move/rotate gizmo.

Regression context
------------------
The user hid the LED in the Scene Components browser and its selection gizmo --
the rotate ring plus the translate arrows -- stayed on screen ("Hiding LED leave
the gizmo visible.").

``set_step_label_hidden`` hid the body actors via
``_all_actor_keys_for_step_label``, but that set sweeps only the rotate-RING
handles (``_actor_step_rotate_map``); the translate arrows
(``_actor_step_translate_map``) and the ring visual
(``_actor_step_rotate_visual_keys``) are not in it, and even the rotate handles are
merely turned invisible (the handle objects survive). So the gizmo outlived the
body.

The fix calls ``_reconcile_step_rotation_handles(self._selected_step_labels)`` in
the hide branch. ``_reconcile_step_rotation_handles`` already filters out hidden
labels, so the just-hidden label drops out of the reconcile target and the handle
service's ``remove_for_label`` deletes its full gizmo (rotate map, translate map,
ring visual, follow map). The unhide path's overlay refresh rebuilds the gizmo when
the label is the selected one, so the round-trip stays symmetric.

This guard is display-free. It calls the real ``_reconcile_step_rotation_handles``
on a tiny stub so the hidden-label filter is exercised as production code, then
pins the source contracts (the hide branch reconciles; the handle remover clears
the translate + visual maps too).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_hidden_step_drops_gizmo

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    try:
        return (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
    except Exception:
        return ""


class _FakeHandleService:
    def __init__(self) -> None:
        self.reconciled_with: "set[str] | None" = None

    def reconcile_to_labels(self, labels) -> bool:
        self.reconciled_with = set(labels)
        return True


class _ReconcileStub:
    """Just enough of the inspector for _reconcile_step_rotation_handles: a hidden
    set + the handle-service accessor. The real method runs against this."""

    def __init__(self, hidden, invisible=()) -> None:
        self._hidden = {str(h).strip().lower() for h in hidden}
        self._invisible = {str(h).strip().lower() for h in invisible}
        self._service = _FakeHandleService()

    def is_step_label_hidden(self, label: str) -> bool:
        return str(label).strip().lower() in self._hidden

    def _step_label_has_only_invisible_body_actors(self, label: str) -> bool:
        return str(label).strip().lower() in self._invisible

    def _open3d_step_rotation_handle_service(self):
        return self._service


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    except Exception as exc:
        notes.append(f"FAIL: could not import Kraken3DInspector: {exc!r}")
        return False, notes

    # A. Logic: reconciling a selection that includes a HIDDEN label must drop that
    #    label from the reconcile target (so its gizmo is removed) while keeping the
    #    other selected, visible labels.
    stub = _ReconcileStub(hidden={"led"})
    Kraken3DInspector._reconcile_step_rotation_handles(stub, {"led", "optical"})
    got = stub._service.reconciled_with
    if got is None:
        notes.append("FAIL: _reconcile_step_rotation_handles never called reconcile_to_labels")
        passed = False
    else:
        if "led" in got:
            notes.append(
                "FAIL: the hidden 'led' label survived into the reconcile target -- its gizmo "
                "would not be torn down (bugs/0136)"
            )
            passed = False
        if "optical" not in got:
            notes.append(
                "FAIL: the visible 'optical' label was dropped from the reconcile target -- "
                "hiding one element must not strip another's gizmo (bugs/0136)"
            )
            passed = False

    # A hidden-only selection reconciles to the empty set (gizmo fully gone).
    stub2 = _ReconcileStub(hidden={"led"})
    Kraken3DInspector._reconcile_step_rotation_handles(stub2, {"led"})
    if stub2._service.reconciled_with != set():
        notes.append(
            f"FAIL: hiding the only selected label did not clear the gizmo target "
            f"(got {stub2._service.reconciled_with!r}, expected empty) (bugs/0136)"
        )
        passed = False

    # Normal-to-Sensor is a temporary actor hide, not a browser-hidden label.
    # It must follow the same no-gizmo contract without corrupting hidden state.
    stub3 = _ReconcileStub(hidden=set(), invisible={"camera"})
    Kraken3DInspector._reconcile_step_rotation_handles(stub3, {"camera", "optical"})
    if stub3._service.reconciled_with != {"optical"}:
        notes.append(
            "FAIL: a temporarily invisible camera survived into the gizmo reconcile target "
            f"(got {stub3._service.reconciled_with!r})"
        )
        passed = False

    # B. Source contract: the hide branch of set_step_label_hidden reconciles.
    try:
        hide_src = inspect.getsource(Kraken3DInspector.set_step_label_hidden)
    except Exception as exc:
        notes.append(f"FAIL: could not read set_step_label_hidden source: {exc!r}")
        return False, notes
    if "_reconcile_step_rotation_handles(self._selected_step_labels)" not in hide_src:
        notes.append(
            "FAIL: set_step_label_hidden no longer reconciles the rotation handles -- a hidden "
            "element's gizmo would survive (bugs/0136)"
        )
        passed = False
    else:
        # The reconcile must sit in the hide branch (before the else), not the unhide one.
        hide_idx = hide_src.find("_reconcile_step_rotation_handles(self._selected_step_labels)")
        else_idx = hide_src.find("\n        else:")
        if else_idx >= 0 and hide_idx > else_idx:
            notes.append(
                "FAIL: the rotation-handle reconcile is in the unhide branch, not the hide branch "
                "(bugs/0136)"
            )
            passed = False

    # C. Mechanism: the handle remover clears the translate arrows + ring visual too,
    #    so the full gizmo (not just the rotate-ring handles) goes with the body.
    rot_src = _read("KrakenOS/UI/services/open3d_step_rotation_handles.py")
    for token in (
        "_actor_step_translate_map.pop(actor_key, None)",
        "_actor_step_rotate_visual_keys.discard(actor_key)",
    ):
        if token not in rot_src:
            notes.append(
                f"FAIL: remove_for_label no longer clears '{token}' -- the translate arrows or "
                "ring visual would be stranded after a hide (bugs/0136)"
            )
            passed = False

    if verbose:
        notes.append(
            "checked: _reconcile_step_rotation_handles drops hidden labels (and clears a hidden-only "
            "selection); the hide branch reconciles; remove_for_label clears the translate + visual maps"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0136: hiding a STEP element drops its gizmo")
        return 0
    print("[FAIL] bugs/0136 hidden-step gizmo guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
