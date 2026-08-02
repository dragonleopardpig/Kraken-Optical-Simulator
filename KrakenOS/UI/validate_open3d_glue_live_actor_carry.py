"""Guard for bugs/0137 -- a glued beam splitter follows the LED during a LIVE drag.

Regression context
------------------
The user glued the beam splitter to the LED, then dragged the LED: the LED body
tracked the cursor but the glued beam splitter stayed frozen until mouse-up ("after
glued, moving the LED, BS is not following live.").

Each drag frame carries the partner's DATA (``_carry_glued_optical_led`` updates the
BS overlay offset or promoted-row pose) but the actor carry
(``_translate_step_overlay_actors``) only ever moved the *dragged* label's actors --
so the partner's actors lagged a whole drag behind the data, snapping into place only
when the post-drag rebuild re-derived them.

The fix adds ``_mirror_glued_partner_actors``: at the actor chokepoint it mirrors the
same world delta onto the glued partner's ACTORS, resolving the partner exactly as the
DATA carry does (BS = the 'optical' overlay OR a promoted optical-solid row; LED =
always an overlay). The partner move is glue-suppressed (``carry_glue=False``, so it
cannot carry back onto the dragged body) and render-deferred (``render=False``, so the
single render at the end of the dragged label's carry repaints both bodies at once).

This guard is display-free. It calls the real ``_mirror_glued_partner_actors`` on a
tiny stub so the partner resolution + delegation are exercised as production code, then
pins the source contracts (the actor carry mirrors under the ``carry_glue`` gate; the
row carry honours a ``render`` keyword).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_glue_live_actor_carry

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import numpy as np


class _FakeEditor:
    """Just enough of the editor for the partner resolution: the glue flag and the two
    partner locators. ``overlay_labels`` are the labels that resolve to a STEP overlay;
    ``promoted_row`` is the promoted optical-solid row index (or None)."""

    def __init__(self, *, glued: bool, overlay_labels, promoted_row=None) -> None:
        self._optical_led_glued = bool(glued)
        self._overlay_labels = {str(s).strip().lower() for s in overlay_labels}
        self._promoted_row = promoted_row

    def _step_path_for_label(self, label: str):
        return "stub/path.step" if str(label).strip().lower() in self._overlay_labels else None

    def _promoted_optical_solid_row_index(self, label: str = "optical"):
        return self._promoted_row


class _MirrorStub:
    """Self for the real ``_mirror_glued_partner_actors``: an editor accessor plus the
    two actor movers, which here only RECORD their calls (no VTK actors headless)."""

    def __init__(self, editor: _FakeEditor) -> None:
        self.editor = editor
        self.overlay_calls: "list[tuple]" = []
        self.row_calls: "list[tuple]" = []

    def _translate_step_overlay_actors(self, label, delta, *, carry_glue=True, render=True):
        self.overlay_calls.append(
            (str(label).strip().lower(), tuple(float(v) for v in np.asarray(delta).reshape(-1)[:3]),
             bool(carry_glue), bool(render))
        )
        return 1

    def _translate_row_actors(self, row_index, delta, *, render=True):
        self.row_calls.append(
            (int(row_index), tuple(float(v) for v in np.asarray(delta).reshape(-1)[:3]), bool(render))
        )
        return 1


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    except Exception as exc:
        notes.append(f"FAIL: could not import Kraken3DInspector: {exc!r}")
        return False, notes

    mirror = Kraken3DInspector._mirror_glued_partner_actors
    delta = (3.0, -2.0, 1.0)

    # A1. LED dragged, BS is an overlay: the BS-overlay actors get the same delta,
    #     glue-suppressed (no carry-back) and render-deferred.
    stub = _MirrorStub(_FakeEditor(glued=True, overlay_labels={"led", "optical"}))
    mirror(stub, "led", delta)
    if not stub.overlay_calls:
        notes.append("FAIL: LED drag did not mirror the glued BS overlay actors (bugs/0137)")
        passed = False
    else:
        label, got_delta, carry_glue, render = stub.overlay_calls[0]
        if label != "optical":
            notes.append(f"FAIL: LED drag mirrored '{label}', expected the 'optical' BS (bugs/0137)")
            passed = False
        if got_delta != tuple(float(v) for v in delta):
            notes.append(f"FAIL: partner moved by {got_delta!r}, expected {delta!r} (bugs/0137)")
            passed = False
        if carry_glue:
            notes.append(
                "FAIL: the partner actor move was NOT glue-suppressed (carry_glue=True) -- it could "
                "mirror back onto the dragged LED (bugs/0137)"
            )
            passed = False
        if render:
            notes.append(
                "FAIL: the partner actor move rendered on its own (render=True) -- a double render "
                "per drag frame (bugs/0137)"
            )
            passed = False
    if stub.row_calls:
        notes.append("FAIL: an overlay BS partner should not go through the row mover (bugs/0137)")
        passed = False

    # A2. LED dragged, BS is a PROMOTED ROW (overlay lookup misses, row index resolves):
    #     the promoted-row actors get the delta, render-deferred.
    stub2 = _MirrorStub(_FakeEditor(glued=True, overlay_labels={"led"}, promoted_row=4))
    mirror(stub2, "led", delta)
    if not stub2.row_calls:
        notes.append("FAIL: LED drag did not mirror the promoted BS row actors (bugs/0137)")
        passed = False
    else:
        row_index, got_delta, render = stub2.row_calls[0]
        if row_index != 4:
            notes.append(f"FAIL: promoted BS mirror used row {row_index}, expected 4 (bugs/0137)")
            passed = False
        if got_delta != tuple(float(v) for v in delta):
            notes.append(f"FAIL: promoted BS row moved by {got_delta!r}, expected {delta!r} (bugs/0137)")
            passed = False
        if render:
            notes.append("FAIL: the promoted BS row move rendered on its own (render=True) (bugs/0137)")
            passed = False
    if stub2.overlay_calls:
        notes.append("FAIL: a promoted BS partner should not go through the overlay mover (bugs/0137)")
        passed = False

    # A3. Nothing glued: the mirror is inert (no partner moves at all).
    stub3 = _MirrorStub(_FakeEditor(glued=False, overlay_labels={"led", "optical"}))
    mirror(stub3, "led", delta)
    if stub3.overlay_calls or stub3.row_calls:
        notes.append("FAIL: an unglued drag still moved a partner -- the mirror must be inert (bugs/0137)")
        passed = False

    # A4. Symmetric free case: BS overlay dragged -> the LED overlay follows.
    stub4 = _MirrorStub(_FakeEditor(glued=True, overlay_labels={"led", "optical"}))
    mirror(stub4, "optical", delta)
    if not stub4.overlay_calls or stub4.overlay_calls[0][0] != "led":
        notes.append(
            "FAIL: dragging the BS overlay did not mirror onto the LED (symmetric direction, bugs/0137)"
        )
        passed = False

    # B. Source contract: the actor carry mirrors under the carry_glue gate; the row carry
    #    honours a render keyword.
    try:
        overlay_src = inspect.getsource(Kraken3DInspector._translate_step_overlay_actors)
    except Exception as exc:
        notes.append(f"FAIL: could not read _translate_step_overlay_actors source: {exc!r}")
        return False, notes
    if "carry_glue" not in overlay_src or "_mirror_glued_partner_actors(label, delta)" not in overlay_src:
        notes.append(
            "FAIL: _translate_step_overlay_actors no longer mirrors the glued partner's actors -- the "
            "BS would lag behind the LED again (bugs/0137)"
        )
        passed = False
    elif overlay_src.find("if carry_glue") < 0 or overlay_src.find("if carry_glue") > overlay_src.find(
        "_mirror_glued_partner_actors(label, delta)"
    ):
        notes.append(
            "FAIL: the partner mirror is not gated by carry_glue -- the partner move could recurse "
            "(bugs/0137)"
        )
        passed = False

    try:
        row_src = inspect.getsource(Kraken3DInspector._translate_row_actors)
    except Exception as exc:
        notes.append(f"FAIL: could not read _translate_row_actors source: {exc!r}")
        return False, notes
    if "render: bool = True" not in row_src or "if render:" not in row_src:
        notes.append(
            "FAIL: _translate_row_actors no longer honours a render keyword -- the promoted-BS mirror "
            "would force a double render per frame (bugs/0137)"
        )
        passed = False

    # C. bugs/0514: the LIVE assembly follow. The row-carry of a glued BS routes each
    #    frame through the LED translate (assembly model write) and every drag path
    #    applies the translate breadcrumbs so station rows / surrogate legs / glued
    #    sources track the cursor instead of jumping at release.
    try:
        carry_src = inspect.getsource(Kraken3DInspector._apply_row_carry_drag_motion)
        step_src = inspect.getsource(Kraken3DInspector._apply_step_carry_motion_delta)
        applier_src = inspect.getsource(Kraken3DInspector._apply_translate_row_shift_breadcrumbs)
    except Exception as exc:
        notes.append(f"FAIL (0514): live-follow sources unreadable: {exc!r}")
        return False, notes
    if (
        'translate_step_overlay(' not in carry_src
        or "alt_suspend_glue" not in carry_src
        or "_apply_translate_row_shift_breadcrumbs" not in carry_src
    ):
        notes.append(
            "FAIL (0514): the glued-BS row carry no longer routes frames through the LED "
            "translate with breadcrumb actor follow -- the LED would jump at release again"
        )
        passed = False
    if "_apply_translate_row_shift_breadcrumbs" not in step_src:
        notes.append(
            "FAIL (0514): the STEP carry no longer applies row-shift breadcrumbs -- the lens "
            "surrogate would lag the barrel again"
        )
        passed = False
    if "_last_translate_row_shifts" not in applier_src or "_last_translate_source_shifts" not in applier_src:
        notes.append("FAIL (0514): the breadcrumb applier no longer reads both shift lists")
        passed = False
    try:
        arrow_src = inspect.getsource(Kraken3DInspector._apply_placement_drag_motion)
    except Exception as exc:
        notes.append(f"FAIL (0514): arrow-drag source unreadable: {exc!r}")
        return False, notes
    if (
        "_mirror_glued_partner_actors" not in arrow_src
        or "alt_suspend_glue" not in arrow_src
        or "glued_to_led" not in arrow_src
    ):
        notes.append(
            "FAIL (0514): the placement-ARROW drag no longer previews the glued LED + sources "
            "per frame -- they would teleport at release again ('one after another')"
        )
        passed = False

    if verbose:
        notes.append(
            "checked: _mirror_glued_partner_actors moves an overlay BS / promoted-row BS / symmetric LED, "
            "is inert when unglued, suppresses carry-back + render; the actor carry mirrors under carry_glue "
            "and the row carry honours render; 0514 live assembly follow wired (row carry -> LED translate + "
            "breadcrumbs, step carry -> breadcrumbs)"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0137: a glued beam splitter follows the LED live")
        return 0
    print("[FAIL] bugs/0137 glued-BS live-follow guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
