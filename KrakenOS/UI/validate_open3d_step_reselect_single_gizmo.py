"""Display-free guard for bugs/0049.

Selecting a different imported STEP solid must tear down the previously
selected solid's rotation gizmo (a plain click is single-select), while
Shift+click keeps multiple gizmos (intentional multi-select). The recorded
repro showed the rotation-handle count climbing 6 -> 12 -> 18 as three
solids were clicked in turn -- prior handles never removed.

Two checks, both without an X server:

1. ``show_step_rotation_handler`` selection-set logic: plain click
   collapses to ``{label}``; Shift+click toggles a label in/out of the set;
   the primary (last-clicked) label and the reconciled set track correctly.

2. ``Open3DStepRotationHandleService`` reconcile mechanics: reconciling to a
   new label removes the prior label's six handle actors instead of stacking
   another six, and multi-label reconcile keeps exactly the targeted sets.
"""

from __future__ import annotations

import types

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_step_rotation_handles import (
    Open3DStepRotationHandleService,
)


class _FakeStatusVar:
    def __init__(self) -> None:
        self._value = ""

    def set(self, value: str) -> None:
        self._value = str(value)

    def get(self) -> str:
        return self._value


class _FakeEditor:
    def __init__(self) -> None:
        self._selected_step_label: str | None = None

    def _step_path_for_label(self, label: str):
        return f"/fake/{label}.STEP"

    def select_step_component(self, label: str) -> None:
        self._selected_step_label = str(label).strip().lower()


def _test_show_handler_selection_set() -> None:
    inspector = Kraken3DInspector.__new__(Kraken3DInspector)
    inspector.editor = _FakeEditor()
    inspector.status_var = _FakeStatusVar()
    inspector._step_rotation_active_label = None
    inspector._selected_step_labels = set()
    inspector._step_carry_active_label = None

    reconciled: list[set[str]] = []
    highlighted: list[set[str]] = []

    inspector._timing_start = lambda *a, **k: object()  # type: ignore[method-assign]
    inspector._timing_finish = lambda *a, **k: None  # type: ignore[method-assign]
    inspector.render = lambda *a, **k: None  # type: ignore[method-assign]
    inspector._show_rotation_handles = lambda: True  # type: ignore[method-assign]
    inspector._step_label_has_visible_body_actor = lambda label: True  # type: ignore[method-assign]
    inspector._step_rotation_handle_count_for_label = lambda label: 6  # type: ignore[method-assign]
    inspector._step_rotation_status_text = lambda label: f"{str(label).upper()} STEP"  # type: ignore[method-assign]
    inspector._set_step_highlight_set = lambda labels, **k: highlighted.append(  # type: ignore[method-assign]
        {str(l).strip().lower() for l in labels}
    )
    inspector._reconcile_step_rotation_handles = lambda labels: reconciled.append(  # type: ignore[method-assign]
        {str(l).strip().lower() for l in labels}
    )

    def _state() -> tuple[str | None, set[str]]:
        return inspector._step_rotation_active_label, set(inspector._selected_step_labels)

    # Plain click on the lens: single-select.
    inspector.show_step_rotation_handler("lens")
    if _state() != ("lens", {"lens"}) or reconciled[-1] != {"lens"}:
        raise AssertionError(f"plain lens click: {_state()} reconcile={reconciled[-1]}")

    # Plain click on the camera: prior lens selection collapses away.
    inspector.show_step_rotation_handler("camera")
    if _state() != ("camera", {"camera"}) or reconciled[-1] != {"camera"}:
        raise AssertionError(
            f"plain camera click must drop lens: {_state()} reconcile={reconciled[-1]}"
        )

    # Shift+click the led: intentional multi-select, both gizmos live.
    inspector.show_step_rotation_handler("led", additive=True)
    if _state() != ("led", {"camera", "led"}) or reconciled[-1] != {"camera", "led"}:
        raise AssertionError(f"shift led add: {_state()} reconcile={reconciled[-1]}")

    # Shift+click the led again: toggle it back off, camera remains primary.
    inspector.show_step_rotation_handler("led", additive=True)
    if _state() != ("camera", {"camera"}) or reconciled[-1] != {"camera"}:
        raise AssertionError(f"shift led toggle-off: {_state()} reconcile={reconciled[-1]}")

    # Shift+click the only remaining selection off: empty set, no primary.
    inspector.show_step_rotation_handler("camera", additive=True)
    if _state() != (None, set()) or reconciled[-1] != set():
        raise AssertionError(f"shift camera toggle-off to empty: {_state()} reconcile={reconciled[-1]}")

    # A plain click after an empty selection re-selects cleanly.
    inspector.show_step_rotation_handler("lens")
    if _state() != ("lens", {"lens"}):
        raise AssertionError(f"plain re-select after empty: {_state()}")

    print("show_step_rotation_handler selection-set logic passed.")


class _FakeRenderer:
    def __init__(self) -> None:
        self.removed: list[object] = []

    def RemoveActor(self, actor) -> None:
        self.removed.append(actor)


class _FakeMesh:
    n_points = 64


class _ReconcileEditor:
    def _step_path_for_label(self, label: str):
        return f"/fake/{label}.STEP"

    def _transformed_imported_step_mesh_for_label(self, label: str):
        return _FakeMesh()

    def append_debug(self, *_a, **_k) -> None:
        pass


class _ReconcileInspector:
    def __init__(self) -> None:
        self._renderer = _FakeRenderer()
        self._actor_by_key: dict[str, object] = {}
        self._actor_step_rotate_map: dict[str, tuple[str, str, float]] = {}
        self._actor_step_rotate_visual_keys: set[str] = set()
        self._actor_step_translate_map: dict[str, tuple[str, str, float]] = {}
        self._actor_step_follow_map: dict[str, str] = {}
        self._step_follow_actor_map: dict[str, list[str]] = {}
        self._hover_rotation_handle_key: str | None = None
        self.editor = _ReconcileEditor()

    def _show_rotation_handles(self) -> bool:
        return True


def _register_handles(inspector: _ReconcileInspector, label: str) -> int:
    """Mimic ``add_handles`` actor tagging: 6 rotate + 3 arc + 3 translate."""
    def _tag(key: str) -> None:
        inspector._actor_by_key[key] = object()
        inspector._actor_step_follow_map[key] = label
        inspector._step_follow_actor_map.setdefault(label, []).append(key)

    for axis in ("x", "y", "z"):
        for delta in (-90.0, 90.0):
            key = f"{label}:rot:{axis}:{delta}"
            _tag(key)
            inspector._actor_step_rotate_map[key] = (label, axis, float(delta))
        arc_key = f"{label}:arc:{axis}"
        _tag(arc_key)
        inspector._actor_step_rotate_visual_keys.add(arc_key)
        tr_key = f"{label}:tr:{axis}"
        _tag(tr_key)
        inspector._actor_step_translate_map[tr_key] = (label, axis, 1.0)
    return 6


def _test_service_reconcile_removes_prior() -> None:
    inspector = _ReconcileInspector()
    service = Open3DStepRotationHandleService(
        inspector,  # type: ignore[arg-type]
        pv_module=object(),
        valid_labels={"lens", "camera", "led", "optical"},
    )

    def fake_add_handles(self, label, mesh):  # noqa: ANN001
        return _register_handles(inspector, str(label).strip().lower())

    service.add_handles = types.MethodType(fake_add_handles, service)  # type: ignore[method-assign]

    def total_rotate() -> int:
        return len(inspector._actor_step_rotate_map)

    # Select the lens: six rotate-pick actors.
    service.reconcile_to_labels({"lens"})
    if service.handle_count_for_label("lens") != 6 or total_rotate() != 6:
        raise AssertionError(f"lens select: lens={service.handle_count_for_label('lens')} total={total_rotate()}")

    # Reselect the camera: the lens handles must be gone, not stacked.
    service.reconcile_to_labels({"camera"})
    if (
        service.handle_count_for_label("lens") != 0
        or service.handle_count_for_label("camera") != 6
        or total_rotate() != 6
    ):
        raise AssertionError(
            "reselect camera must drop lens handles: "
            f"lens={service.handle_count_for_label('lens')} "
            f"camera={service.handle_count_for_label('camera')} total={total_rotate()}"
        )
    if service._labels_with_handles() != {"camera"}:
        raise AssertionError(f"labels_with_handles after camera reselect: {service._labels_with_handles()!r}")

    # Multi-select camera + led: exactly twelve handles, no third set.
    service.reconcile_to_labels({"camera", "led"})
    if (
        service.handle_count_for_label("camera") != 6
        or service.handle_count_for_label("led") != 6
        or total_rotate() != 12
    ):
        raise AssertionError(
            "multi-select camera+led: "
            f"camera={service.handle_count_for_label('camera')} "
            f"led={service.handle_count_for_label('led')} total={total_rotate()}"
        )

    # Collapse back to a single lens selection: all prior handles removed.
    service.reconcile_to_labels({"lens"})
    if (
        service.handle_count_for_label("lens") != 6
        or service.handle_count_for_label("camera") != 0
        or service.handle_count_for_label("led") != 0
        or total_rotate() != 6
    ):
        raise AssertionError(
            "collapse to lens: "
            f"lens={service.handle_count_for_label('lens')} total={total_rotate()}"
        )

    # The bookkeeping maps must be fully consistent -- no stale keys lingering
    # in the follow / visual / translate maps after the removals.
    live_keys = set(inspector._actor_by_key)
    for key in inspector._actor_step_rotate_map:
        if key not in live_keys:
            raise AssertionError(f"stale rotate key: {key!r}")
    for key in inspector._actor_step_rotate_visual_keys:
        if key not in live_keys:
            raise AssertionError(f"stale visual key: {key!r}")
    for key in inspector._actor_step_translate_map:
        if key not in live_keys:
            raise AssertionError(f"stale translate key: {key!r}")
    for key in inspector._actor_step_follow_map:
        if key not in live_keys:
            raise AssertionError(f"stale follow key: {key!r}")

    # Clearing to an empty selection removes everything.
    service.reconcile_to_labels(set())
    if total_rotate() != 0 or inspector._actor_by_key:
        raise AssertionError(f"empty reconcile left actors: total={total_rotate()} actors={len(inspector._actor_by_key)}")

    print("Open3DStepRotationHandleService reconcile mechanics passed.")


def main() -> int:
    _test_show_handler_selection_set()
    _test_service_reconcile_removes_prior()
    print("STEP reselect single-gizmo validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
