"""Guard for bugs/0138 -- Set-Clear-Aperture hover renders only on face transitions.

Regression context
------------------
While the clear-aperture pick was armed, sweeping the cursor over the body was
sluggish ("significantly slow down after previous actions."). The flag's scene_state
shows every remaining mouse-move was in step_clear_aperture_pick mode with steady
actor counts -- so it was per-move work, not a leak.

``_update_clear_aperture_hover_highlight`` ran on every mouse-move and (1) called
``self.render()`` unconditionally -- a full scene render per pixel, defeating the
change-gate in ``_set_step_hover_outline`` -- and (2) keyed the hover on the per-pixel
``cell_id``, which differs every pixel even when nothing is highlighted, so the gate
never tripped.

The fix keys the hover on the RESOLVED face id (a stable None off any window) and drops
the unconditional render, leaving ``_set_step_hover_outline``'s change-gate to render
only on an actual face<->face / face<->none transition.

This guard is display-free. It runs the real ``_set_step_hover_outline_impl`` against a
probe to prove the change-gate short-circuits on an unchanged key (the gate the fix now
relies on), then pins the source contracts (no unconditional render in the hover method;
the hover key is the face id, not the cell id).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture_hover_render

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _GateProbe:
    """Self for the real ``_set_step_hover_outline_impl`` change-gate. ``_renderer`` is a
    property so we can detect whether the method advanced PAST the unchanged-key gate
    (an unchanged key must return before touching the renderer)."""

    def __init__(self, hover_key) -> None:
        self._hover_step_cell_key = hover_key
        self._hover_step_outline_actor = None
        self.renderer_touched = False

    @property
    def _renderer(self):
        self.renderer_touched = True
        return object()  # non-None: the method proceeds past the renderer guard


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    except Exception as exc:
        notes.append(f"FAIL: could not import Kraken3DInspector: {exc!r}")
        return False, notes

    impl = Kraken3DInspector._set_step_hover_outline_impl
    key = ("clear_aperture", "led", 3)

    # A1. Unchanged key -> the gate returns before touching the renderer (no render work).
    gated = _GateProbe(hover_key=key)
    impl(gated, None, key, render=False)
    if gated.renderer_touched:
        notes.append(
            "FAIL: _set_step_hover_outline_impl did NOT short-circuit on an unchanged hover key -- "
            "the CA-pick hover would still do render work every pixel (bugs/0138)"
        )
        passed = False

    # A2. Changed key -> the method advances past the gate and adopts the new key.
    changed = _GateProbe(hover_key=("clear_aperture", "led", 0))
    impl(changed, None, key, render=False)
    if not changed.renderer_touched:
        notes.append(
            "FAIL: _set_step_hover_outline_impl wrongly short-circuited a CHANGED hover key -- a new "
            "face would not update (bugs/0138)"
        )
        passed = False
    if changed._hover_step_cell_key != key:
        notes.append(
            f"FAIL: a changed hover key was not adopted (got {changed._hover_step_cell_key!r}, "
            f"expected {key!r}) (bugs/0138)"
        )
        passed = False

    # B. Source contract: the CA hover defers its render to the change-gate and keys on the
    #    resolved face id, not the per-pixel cell id.
    try:
        hover_src = inspect.getsource(Kraken3DInspector._update_clear_aperture_hover_highlight)
    except Exception as exc:
        notes.append(f"FAIL: could not read _update_clear_aperture_hover_highlight source: {exc!r}")
        return False, notes
    if "self.render()" in hover_src:
        notes.append(
            "FAIL: _update_clear_aperture_hover_highlight still calls self.render() -- the per-pixel "
            "full-scene render is back (bugs/0138)"
        )
        passed = False
    if '("clear_aperture", wanted, face_id)' not in hover_src:
        notes.append(
            "FAIL: the CA hover key is no longer the resolved face id -- key on face_id, not the "
            "per-pixel cell id (bugs/0138)"
        )
        passed = False
    if "int(cell_id))" in hover_src:
        notes.append(
            "FAIL: the CA hover key still embeds int(cell_id) -- it changes every pixel and defeats "
            "the change-gate (bugs/0138)"
        )
        passed = False

    # C. Source contract: the gate the fix relies on is intact.
    try:
        impl_src = inspect.getsource(Kraken3DInspector._set_step_hover_outline_impl)
    except Exception as exc:
        notes.append(f"FAIL: could not read _set_step_hover_outline_impl source: {exc!r}")
        return False, notes
    if "hover_key == self._hover_step_cell_key" not in impl_src:
        notes.append(
            "FAIL: _set_step_hover_outline_impl no longer change-gates on the hover key -- the CA hover "
            "fix loses the gate it defers to (bugs/0138)"
        )
        passed = False
    if "if render:" not in impl_src:
        notes.append(
            "FAIL: _set_step_hover_outline_impl no longer guards its render with `if render:` (bugs/0138)"
        )
        passed = False

    if verbose:
        notes.append(
            "checked: the unchanged-key gate short-circuits (and a changed key advances + is adopted); the "
            "CA hover drops self.render() and keys on face_id, not int(cell_id); the impl gate is intact"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0138: CA-pick hover renders only on face transitions")
        return 0
    print("[FAIL] bugs/0138 CA-pick hover render-storm guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
