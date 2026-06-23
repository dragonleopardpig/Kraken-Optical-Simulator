"""Guard for bugs/0121 -- a right-click must act on the face the user currently
sees HOVER-HIGHLIGHTED, not on a different overlapping body the flaky VTK cell
picker happens to latch onto.

Regression context
------------------
A beam splitter ("optical" overlay) slid into the LED enclosure makes the two
translucent bodies overlap. The hover path
(`step_feature_pick_for_display_xy`) deterministically prefers a clean solid's
INTERNAL face -- the BS 45 deg splitting coating -- so the gold hover outline
reliably lands on the splitter. But `_right_click_pick_context` resolved WHICH
element to act on from the raw VTK cell-picker actor (`_actor_step_map`), and
for overlapping translucent solids that picker returns a pixel-varying external
shell face. So a right-click on the highlighted BS splitting face committed a
LED edge instead ("Highlight BS splitting surface, right click, selected surface
change to LED edge").

Fix: `_right_click_pick_context` captures the live `_hover_step_cell_key` BEFORE
re-picking and, when it identifies a STEP label different from the VTK-resolved
one, rebuilds the context for that hovered label via the deterministic
display-ray feature pick. The hover key is the source of truth for what the user
sees highlighted.

This guard is display-free: it drives the REAL helper methods bound off the
inspector class against a fake `self`, plus a source-contract check on
`_right_click_pick_context`. No VTK / embedded window is needed.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_right_click_prefers_hovered_face

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


class _FakeThroughPick:
    def __init__(self, point_world, normal_world, internal, face) -> None:
        self.point_world = np.asarray(point_world, dtype=float)
        self.normal_world = np.asarray(normal_world, dtype=float)
        self.internal = bool(internal)
        self.face = dict(face)


class _FakeInspector:
    """Minimal surface for `_hovered_step_label_and_row_from_key` and
    `_right_click_context_for_hovered_step` -- the two new helpers route through
    `_actor_step_map`, `_actor_row_map`, `is_step_label_hidden` and
    `_step_feature_pick_for_display_xy`, all faked here."""

    def __init__(self) -> None:
        self.bs_actor = "0xBS"
        self.led_actor = "0xLED"
        self.row_actor = "0xROW"
        self._actor_step_map = {self.bs_actor: "optical", self.led_actor: "led"}
        self._actor_row_map = {self.row_actor: 5}
        self._hover_step_cell_key = None
        self.hidden_labels: set[str] = set()
        # faked feature pick: label -> (point, normal, internal)
        self._pick_table = {
            "optical": ((1.0, 2.0, 245.0), (0.0, 0.0, 4.0), True),
            "led": ((40.0, -10.0, 240.0), (0.0, 1.0, 0.0), False),
        }

    def is_step_label_hidden(self, label) -> bool:
        return str(label).strip().lower() in self.hidden_labels

    def _step_feature_pick_for_display_xy(self, label, display_xy, *, actor=None, actor_key=None, cell_id=-1):
        entry = self._pick_table.get(str(label).strip().lower())
        if entry is None:
            return None
        point, normal, internal = entry
        face = {"face_id": f"{label}_face"}
        through = _FakeThroughPick(point, normal, internal, face)
        feature = (np.asarray(point, dtype=float), None, np.asarray(normal, dtype=float))
        return {"feature": feature, "through_pick": through, "face_id": face["face_id"], "surface_center": point}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    parse = Kraken3DInspector._hovered_step_label_and_row_from_key
    build = Kraken3DInspector._right_click_context_for_hovered_step
    fake = _FakeInspector()

    # A. Key parse: every hover-key form maps back to its (label, row).
    parse_cases = [
        (("step", "led", "f7"), ("led", None)),
        (("step", "bogus", 1), (None, None)),
        (("row", 3, "f2"), (None, 3)),
        ((fake.bs_actor, "passive", "Coating"), ("optical", None)),
        ((fake.led_actor, "display", "edge"), ("led", None)),
        ((fake.row_actor, 12), (None, 5)),
        (None, (None, None)),
        # a Measure re-anchor handle key must NOT be hijacked into a STEP/row pick
        (("0xHANDLE", "reanchor", 4), (None, None)),
    ]
    for key, expected in parse_cases:
        got = parse(fake, key)
        if got != expected:
            notes.append(f"FAIL: hover-key {key!r} parsed to {got!r}, expected {expected!r}")
            passed = False

    # B. Hovered-context build: an INTERNAL feature pick on the hovered label
    #    yields a context with that label, the face point, no row, no actor.
    ctx = build(fake, "optical", (196.0, 777.0), event=None)
    if not isinstance(ctx, dict):
        notes.append("FAIL: _right_click_context_for_hovered_step returned no context for 'optical'")
        passed = False
    else:
        if str(ctx.get("step_label")) != "optical":
            notes.append(f"FAIL: hovered context step_label={ctx.get('step_label')!r}, expected 'optical'")
            passed = False
        if ctx.get("row_index") is not None:
            notes.append(f"FAIL: hovered context row_index={ctx.get('row_index')!r}, expected None")
            passed = False
        if ctx.get("actor_key") is not None:
            notes.append("FAIL: hovered context must not carry a VTK actor_key")
            passed = False
        point = np.asarray(ctx.get("point_world", ()), dtype=float).reshape(-1)
        if point.size < 3 or not np.allclose(point[:3], (1.0, 2.0, 245.0)):
            notes.append(f"FAIL: hovered context point_world={tuple(point)} != BS face point (1,2,245)")
            passed = False
        normal = np.asarray(ctx.get("normal_world", ()), dtype=float).reshape(-1)
        if normal.size < 3 or abs(float(np.linalg.norm(normal[:3])) - 1.0) > 1e-6:
            notes.append("FAIL: hovered context normal_world is not unit-normalised")
            passed = False

    # A hidden hovered label yields no override (falls back to the VTK context).
    fake.hidden_labels = {"optical"}
    if build(fake, "optical", (196.0, 777.0), event=None) is not None:
        notes.append("FAIL: a hidden hovered label must not build a right-click context")
        passed = False
    fake.hidden_labels = set()
    if build(fake, "bogus", (1.0, 2.0), event=None) is not None:
        notes.append("FAIL: an invalid hovered label must not build a right-click context")
        passed = False

    # C. Behavioural decision (no VTK): hover identifies the BS while the VTK
    #    picker would resolve the LED -> the override must win and yield 'optical'.
    fake._hover_step_cell_key = (fake.bs_actor, "passive", "Coating")
    hovered_label, _hovered_row = parse(fake, fake._hover_step_cell_key)
    vtk_label = fake._actor_step_map.get(fake.led_actor)  # what the flaky picker returned
    if hovered_label != "optical":
        notes.append(f"FAIL: hover key did not resolve the BS ('optical'); got {hovered_label!r}")
        passed = False
    if hovered_label == vtk_label:
        notes.append("FAIL: test setup invalid -- hover and VTK label must differ to prove the override")
        passed = False
    decided = build(fake, hovered_label, (196.0, 777.0), event=None)
    if not isinstance(decided, dict) or str(decided.get("step_label")) != "optical":
        notes.append("FAIL: with the BS hovered and the LED under the VTK picker, the context is not the BS")
        passed = False

    # D. Source contract on the real _right_click_pick_context: the hover key is
    #    captured BEFORE the re-pick, and the hovered override is consulted BEFORE
    #    the raw VTK actor label is trusted.
    try:
        src = inspect.getsource(Kraken3DInspector._right_click_pick_context)
    except Exception as exc:
        notes.append(f"FAIL: cannot read _right_click_pick_context source: {exc!r}")
        return False, notes
    capture_idx = src.find("_hover_step_cell_key")
    pick_idx = src.find(".Pick(")
    parse_idx = src.find("_hovered_step_label_and_row_from_key")
    build_idx = src.find("_right_click_context_for_hovered_step")
    # The original code trusts the raw VTK actor label right above the bugs/0089
    # comment; the hovered override must be consulted before that point.
    raw_trust_idx = src.find("bugs/0089")
    if capture_idx < 0 or pick_idx < 0 or capture_idx > pick_idx:
        notes.append("FAIL: _right_click_pick_context must capture _hover_step_cell_key BEFORE re-picking")
        passed = False
    if parse_idx < 0 or build_idx < 0:
        notes.append("FAIL: _right_click_pick_context does not consult the hovered-face helpers")
        passed = False
    elif raw_trust_idx < 0 or build_idx > raw_trust_idx:
        notes.append(
            "FAIL: the hovered-face override must be consulted BEFORE trusting the raw VTK "
            "actor step label (bugs/0121)"
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
