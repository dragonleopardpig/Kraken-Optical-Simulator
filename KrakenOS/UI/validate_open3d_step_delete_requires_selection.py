"""Display-free contract for bugs/0008: a bare Delete/BackSpace in the Open 3D
view must not silently remove the imported optical lens when nothing is
selected.

``delete_selected_step`` resolves its target through the step-state service's
``selected_import_label``, which returns the first candidate label that names a
*loaded* overlay -- regardless of whether it is actually selected. The shared
``_selected_imported_step_label_candidates`` ends with a hardcoded ``"optical"``
fallback (correct for the non-destructive carry/promote resolvers, which act on
"the current overlay"). When the destructive delete reused that list, the three
selection slots were ``None`` yet the fallback still resolved to ``"optical"``,
so a stray Delete/BackSpace -- the VTK key handler has no focus guard -- deleted
the imported lens with nothing selected (flag 341: ``selected_step_label: null``,
body gone, rows + axis preserved).

The fix gives delete its own ``_delete_target_import_label_candidates`` with no
``"optical"`` fallback, so an unselected delete is a no-op. This pins that seam
and source-couples ``delete_selected_step`` so a refactor can't silently route
the destructive path back through the permissive fallback. The rendered-pixel
guarantee lives in ``validate_open3d_step_delete_requires_selection_snapshot``
and Phase 15 of the comprehensive validator.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_delete_requires_selection
"""

from __future__ import annotations

import inspect
from pathlib import Path

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService


class _EditorStub:
    _selected_step_label = None
    rows: list = []

    def _step_path_for_label(self, label):
        return Path("/tmp/optic.step") if str(label or "").strip().lower() == "optical" else None


class _InspectorStub:
    _step_rotation_active_label = None
    _step_carry_active_label = None

    def __init__(self) -> None:
        self.editor = _EditorStub()


def _checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    stub = _InspectorStub()
    delete_candidates = Kraken3DInspector._delete_target_import_label_candidates(stub)
    carry_candidates = Kraken3DInspector._selected_imported_step_label_candidates(stub)

    checks.append(
        (
            "delete candidates omit the hardcoded optical fallback",
            "optical" not in tuple(delete_candidates),
            f"delete candidates still carry a label fallback: {delete_candidates!r}",
        )
    )
    checks.append(
        (
            "delete candidates are exactly the genuine selection slots",
            tuple(delete_candidates) == (None, None, None),
            f"expected (None, None, None) with nothing selected, got {delete_candidates!r}",
        )
    )
    checks.append(
        (
            "carry/promote candidates keep the optical fallback",
            len(carry_candidates) >= 1 and carry_candidates[-1] == "optical",
            f"non-destructive resolver lost its optical fallback: {carry_candidates!r}",
        )
    )

    # Resolver-level proof: with nothing selected the delete list yields no
    # import target (a no-op), whereas the old permissive list resolves to the
    # loaded optical overlay and would delete it.
    service = Open3DStepStateService(editor=_EditorStub(), valid_labels={"optical", "lens", "camera", "led"})
    safe = service.resolve_delete_selection(import_label_candidates=(None, None, None), row_index_candidates=())
    unsafe = service.resolve_delete_selection(
        import_label_candidates=(None, None, None, "optical"), row_index_candidates=()
    )
    checks.append(
        (
            "unselected delete resolves no import target",
            safe.import_label == "",
            f"unselected delete resolved import_label={safe.import_label!r} (would delete it)",
        )
    )
    checks.append(
        (
            "fallback list still resolves the loaded optical overlay",
            unsafe.import_label == "optical",
            f"sanity: fallback list should resolve optical, got {unsafe.import_label!r}",
        )
    )

    delete_src = inspect.getsource(Kraken3DInspector.delete_selected_step)
    checks.append(
        (
            "delete_selected_step uses the delete-only candidate list",
            "_delete_target_import_label_candidates" in delete_src,
            "delete_selected_step does not call _delete_target_import_label_candidates",
        )
    )
    checks.append(
        (
            "delete_selected_step does not reuse the permissive carry/promote list",
            "_selected_imported_step_label_candidates" not in delete_src,
            "delete_selected_step still routes through the optical-fallback candidate list",
        )
    )

    return checks


def main() -> int:
    checks = _checks()
    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D STEP delete-requires-selection validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print(f"Open 3D STEP delete-requires-selection validation passed ({len(checks)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
