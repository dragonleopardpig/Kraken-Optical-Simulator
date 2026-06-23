"""Guard for bugs/0124 -- the passive STEP hover key must carry the RESOLVED
step label, so a right-click can recover the highlighted body even when the VTK
cell picker missed that body's own actor.

Regression context
------------------
bugs/0121 (commit c441ebb) made `_right_click_pick_context` override to the
HOVER-highlighted STEP face when the flaky VTK cell picker resolves a different
overlapping body. That override keys off `_hovered_step_label_and_row_from_key`
recovering the label from the live `_hover_step_cell_key`.

The fix shipped "eyeball owed" and the bug recurred (flag_20260624_073033_166):
a beam splitter ("optical" overlay) slid into the LED, the gold outline sat on
the BS splitting plane, yet the right-click still selected the LED edge. The
0124 instrumentation captured why::

    right_click_diagnostics = {
        "prior_hover_key": "(None, 'passive', 'S001/F001')",
        "hovered_label": null,            # <- resolver bailed
        "vtk_step_label": "led",
        "override_eligible": false,       # <- so the 0121 override never ran
        "override_fired": false,
    }

The passive hover key was built in `open3d_interaction.py` as
``(actor_key, "passive", face_id)``. When the BS is buried in the LED the VTK
cell pick lands on the LED shell (or nothing), so `step_label` is recovered from
the deterministic *fallback feature pick* while `actor_key` is ``None`` / the
LED's. The key's actor-key head then resolves to ``None`` (or worse, "led"), so
`_hovered_step_label_and_row_from_key` cannot recover "optical" and the override
is skipped.

Fix: lead the passive STEP hover key with the RESOLVED label --
``("step", step_label, face_id or cell_id)`` -- the form the resolver maps back
directly, independent of which actor the VTK picker happened to latch onto.

This guard is display-free: it drives the REAL resolver bound off the inspector
class against the key forms involved, plus a source-contract check on the
construction site in `open3d_interaction.py`. No VTK / embedded window needed.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_hover_key_carries_step_label

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _FakeInspector:
    """Minimal surface for `_hovered_step_label_and_row_from_key`. The resolver
    only consults `_actor_step_map` / `_actor_row_map` for the *actor-key* head;
    the ("step", ...) head -- the form the fix produces -- never touches them."""

    def __init__(self) -> None:
        # The LED shell is the actor the flaky picker latches onto; the BS
        # ("optical") overlay's own actor is NOT under the cursor in the bug.
        self._actor_step_map = {"0xLED": "led"}
        self._actor_row_map: dict[str, int] = {}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABEL_SET

    parse = Kraken3DInspector._hovered_step_label_and_row_from_key
    fake = _FakeInspector()

    # 0. The body the bug is about must be a real optical overlay label.
    if "optical" not in STEP_OVERLAY_LABEL_SET:
        notes.append("FAIL: 'optical' is not a STEP overlay label -- the override can never fire for a BS")
        passed = False

    # A. The FIXED key form recovers the BS label regardless of the actor the
    #    VTK picker returned (the resolver never looks at the maps for it).
    fixed_key = ("step", "optical", "S001/F001")
    got = parse(fake, fixed_key)
    if got != ("optical", None):
        notes.append(f"FAIL: fixed hover key {fixed_key!r} -> {got!r}, expected ('optical', None)")
        passed = False

    # B. The two BROKEN heads the old construction could produce both fail to
    #    recover "optical" -- this is exactly why the override no-opped live.
    #    b1: actor_key was None (this flag) -> head is not a str -> bails.
    broken_none = (None, "passive", "S001/F001")
    if parse(fake, broken_none) != (None, None):
        notes.append(f"FAIL: {broken_none!r} should be unrecoverable (None head), got {parse(fake, broken_none)!r}")
        passed = False
    #    b2: actor_key was the LED shell -> resolves to "led" (the WRONG body),
    #    so hovered_label == vtk_step_label and the override is skipped.
    broken_led = ("0xLED", "passive", "S001/F001")
    if parse(fake, broken_led) != ("led", None):
        notes.append(f"FAIL: {broken_led!r} should resolve to the LED shell ('led', None), got {parse(fake, broken_led)!r}")
        passed = False

    # C. End-to-end decision (no VTK): with the fixed key the hovered label is
    #    "optical" while the VTK picker resolved "led" -> the 0121 override is
    #    ELIGIBLE (hovered_label is not None and != vtk_step_label). With either
    #    broken key it is NOT eligible -- reproducing the live no-op.
    vtk_step_label = "led"  # what the flaky cell picker returned at right-click
    hovered_fixed, _ = parse(fake, fixed_key)
    eligible_fixed = hovered_fixed is not None and hovered_fixed != vtk_step_label
    if not eligible_fixed:
        notes.append("FAIL: the fixed hover key must make the bugs/0121 override ELIGIBLE (optical != led)")
        passed = False
    for broken in (broken_none, broken_led):
        hov, _ = parse(fake, broken)
        if hov is not None and hov != vtk_step_label:
            notes.append(f"FAIL: broken key {broken!r} unexpectedly eligible (hovered={hov!r}); test premise wrong")
            passed = False

    # D. Source contract: the passive STEP hover branch builds the key with the
    #    RESOLVED label as a ("step", ...) head, and the buggy actor-key head is
    #    gone. The construction lives on the hover handler in open3d_interaction.
    try:
        from KrakenOS.UI.services import open3d_interaction as _interaction
        src = inspect.getsource(_interaction)
    except Exception as exc:  # pragma: no cover - import/source failure
        notes.append(f"FAIL: cannot read open3d_interaction source: {exc!r}")
        return False, notes
    if 'hover_key = ("step", str(step_label).strip().lower(), face_id or int(cell_id))' not in src:
        notes.append(
            "FAIL: the passive STEP hover key must lead with the resolved step label "
            '("step", step_label, face_id or cell_id) (bugs/0124)'
        )
        passed = False
    if 'hover_key = (actor_key, "passive", face_id or int(cell_id))' in src:
        notes.append(
            "FAIL: the buggy actor-key-head passive hover key is back -- a missed VTK "
            "pick will drop the resolved label and break the bugs/0121 override"
        )
        passed = False

    if verbose:
        for note in notes:
            print(note)
        print("PASS" if passed else "FAIL")
    return passed, notes


if __name__ == "__main__":
    import sys

    ok, msgs = run_checks(verbose=True)
    if not ok:
        for m in msgs:
            print(m)
    sys.exit(0 if ok else 1)
