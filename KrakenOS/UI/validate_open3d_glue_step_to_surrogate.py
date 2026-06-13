"""Guard: the "Glue STEP to Surrogate" action re-applies an imported overlay's
automatic optical-surrogate placement by clearing its manual drag offsets.

User feature (after bugs/0077): glue should be automatic AND available on the
right-click menu, so a STEP that was dragged off its auto-aligned station snaps
back -- a lens re-centres on its CAD cylinder axis (0077) with the front datum on
the surrogate; the camera sensor returns to the Image plane; the LED returns to
its object-distance station.

`ScenePlacementMixin.glue_step_overlay_to_surrogate(label)` clears
``<label>_step_axis_offset_xy`` and ``<label>_step_placement_offset_xyz`` (the two
manual-drag offsets consumed by ``_cad_mesh_aligned_to_optical_axis``), preserving
orientation/resize. This guard drives that method on a stub mixin instance -- no
Tk, no render -- proving a dragged overlay is re-glued and that a clean overlay is
a no-op.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_glue_step_to_surrogate

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations


class _StatusVar:
    def __init__(self) -> None:
        self._value = ""

    def set(self, value: str) -> None:
        self._value = str(value)

    def get(self) -> str:
        return self._value


def _make_stub():
    """A minimal ScenePlacementMixin instance: real offset getters/setters + the
    glue method, with the side-effect hooks stubbed to no-ops."""
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    stub = object.__new__(ScenePlacementMixin)
    stub.status_var = _StatusVar()
    stub._live_step_overlay_trace_plan_cache = {}
    stub._history = []
    # side-effect hooks the real offset setters call -- no-ops for the test
    stub._invalidate_step_overlay_face_metadata_cache = lambda *a, **k: None
    stub._invalidate_preview_scene_trace = lambda *a, **k: None
    stub._clear_step_overlay_axis_anchor = lambda *a, **k: None
    stub._begin_history_capture = lambda *a, **k: None
    stub._commit_history_capture = lambda *a, **k: None
    stub._step_overlay_display_label = lambda label: str(label).upper()
    stub._step_path_for_label = lambda label: "/tmp/fake_lens.stp"
    return stub


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    try:
        stub = _make_stub()
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: glue-action deps unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. a dragged lens is re-glued (offsets cleared) ----------------------
    stub._set_step_axis_offset_xy("lens", (5.0, -3.0))
    stub._set_step_placement_offset_xyz("lens", (1.5, 2.5, -4.0))
    ok(stub._step_axis_offset_xy("lens") != (0.0, 0.0),
       "A0: precondition -- the lens carries a manual lateral drag offset")

    moved = stub.glue_step_overlay_to_surrogate("lens")
    ok(moved is True, "A1: gluing a dragged lens reports it moved")
    ok(stub._step_axis_offset_xy("lens") == (0.0, 0.0),
       f"A2: lens lateral offset cleared to (0,0) (got {stub._step_axis_offset_xy('lens')})")
    ok(stub._step_placement_offset_xyz("lens") == (0.0, 0.0, 0.0),
       f"A3: lens placement offset cleared to (0,0,0) (got {stub._step_placement_offset_xyz('lens')})")

    # --- B. a second glue is a no-op (already on the surrogate) ---------------
    moved_again = stub.glue_step_overlay_to_surrogate("lens")
    ok(moved_again is False, "B1: re-gluing an already-glued lens is a no-op (reports no move)")
    ok("already glued" in stub.status_var.get().lower(),
       f"B2: status explains it is already glued (got {stub.status_var.get()!r})")

    # --- C. works per-label and only touches the targeted overlay -------------
    stub._set_step_axis_offset_xy("camera", (2.0, 2.0))
    stub._set_step_placement_offset_xyz("led", (0.0, 0.0, 9.0))
    ok(stub.glue_step_overlay_to_surrogate("camera") is True,
       "C1: gluing the camera clears its offset independently")
    ok(stub._step_axis_offset_xy("camera") == (0.0, 0.0),
       "C2: camera offset cleared")
    ok(stub._step_placement_offset_xyz("led") == (0.0, 0.0, 9.0),
       "C3: the untouched LED overlay keeps its offset (glue is per-label)")

    # --- D. unknown / unimported label is rejected, not crashed ---------------
    ok(stub.glue_step_overlay_to_surrogate("not-a-label") is False,
       "D1: an unknown overlay label returns False (no crash)")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Glue-STEP-to-surrogate validation passed.")
        return 0
    print("Glue-STEP-to-surrogate validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
