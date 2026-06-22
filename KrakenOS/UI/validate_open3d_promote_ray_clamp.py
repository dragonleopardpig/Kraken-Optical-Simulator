"""Guard for bugs/0105 -- promoting a STEP overlay to an optical solid clamps the
forced post-promote retrace to a sparse 3-ray fan so the promote lands fast.

A promoted optical-solid row makes ``has_promoted_step_optical_solid_rows()``
permanently True, so every later refresh forces a full branched physics retrace
(~90s on a beam-splitter scene). The promote's own forced retrace is clamped to
3 rays per field; the override is cleared afterwards so the next explicit trace
restores full ray density.

Checks (all display-free -- the machine-vision render SIGSEGVs headless):
A. ``_current_ray_count`` honours ``_promote_preview_ray_count_override``.
B. the promote site sets the override to 3 and clears it (= None) around the
   forced ``refresh_from_editor(force_retrace=True)``.
C. functional: with the override set, ``_current_ray_count`` returns the clamp;
   cleared, it falls back to the ray-count var; the drag override still works.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_promote_ray_clamp

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    def _src(obj, name):
        try:
            return inspect.getsource(getattr(obj, name))
        except Exception as exc:
            notes.append(f"FAIL: cannot read {name} source: {exc!r}")
            return ""

    # A -- _current_ray_count honours the promote override.
    ray_count_src = _src(KrakenLayoutEditor, "_current_ray_count")
    if "_promote_preview_ray_count_override" not in ray_count_src:
        notes.append("FAIL: _current_ray_count ignores the promote ray-count override")
        passed = False

    # B -- the promote site sets the override to 3 and clears it around the
    # forced retrace.
    promote_src = _src(Kraken3DInspector, "_promote_step_overlay_to_optical_solid_row")
    if "_promote_preview_ray_count_override = 3" not in promote_src:
        notes.append("FAIL: promote does not clamp the forced retrace to 3 rays")
        passed = False
    if "_promote_preview_ray_count_override = None" not in promote_src:
        notes.append("FAIL: promote does not clear the ray-count override after the retrace")
        passed = False
    if "force_retrace=True" not in promote_src:
        notes.append("FAIL: promote no longer forces a retrace")
        passed = False
    # the clear must run in a finally so a failing retrace can't leak the clamp.
    if "finally:" not in promote_src:
        notes.append("FAIL: promote does not clear the override in a finally (clamp could leak on error)")
        passed = False

    # C -- functional override behaviour on a lightweight stand-in (no Tk app, so
    # this stays display-free and segfault-free).
    fn = KrakenLayoutEditor._current_ray_count

    class _Var:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

    class _Fake:
        pass

    fake = _Fake()
    fake.ray_count_var = _Var(31)

    try:
        if int(fn(fake)) != 31:
            notes.append(f"FAIL: baseline ray count not honoured (got {fn(fake)}, want 31)")
            passed = False
        fake._promote_preview_ray_count_override = 3
        if int(fn(fake)) != 3:
            notes.append(f"FAIL: promote override not honoured (got {fn(fake)}, want 3)")
            passed = False
        fake._promote_preview_ray_count_override = None
        if int(fn(fake)) != 31:
            notes.append(f"FAIL: clearing the promote override did not restore full density (got {fn(fake)}, want 31)")
            passed = False
        fake._drag_preview_ray_count_override = 5
        if int(fn(fake)) != 5:
            notes.append(f"FAIL: drag override regressed (got {fn(fake)}, want 5)")
            passed = False
    except Exception as exc:
        notes.append(f"FAIL: _current_ray_count override probe raised {exc!r}")
        passed = False

    if verbose and passed:
        notes.append("promote ray clamp: override honoured (3), cleared restores 31, drag override intact")
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0105: promote clamps the forced retrace to a sparse 3-ray fan")
        return 0
    print("[FAIL] bugs/0105 promote ray-clamp guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
