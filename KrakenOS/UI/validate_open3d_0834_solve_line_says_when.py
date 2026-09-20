"""bugs/0834 guard -- a SOLVE line that no longer describes the scene says so.

flag_20260920_182008 ("setting device size to 20x20x1, solver refused, everything correct?").
The refusal itself was correct and every number in it checked out.  But the banner carried,
three lines apart:

    delivered now: |m| 0.407  FOV 56.57 x 56.57 mm          <- the refusal, current
    SOLVE: delivering 52.5 x 52.5 mm (|m| 0.4389); the lens moved -25.19 mm along its leg

Both correct.  The second was the record of the PREVIOUS solve: ``_solve_summary_info`` is
written when a solve applies and never revisited, so resizing the device (which is what moved
the delivered field from 52.5 to 56.57) left it standing as though it were now.  Nothing on
screen said which was which -- the bugs/0828 failure again, a number without its parent, this
time the parent being WHEN.

The repair re-MEASURES the delivered field every time the banner is drawn and captions the
line when it disagrees.  The line is not deleted: the user still wants to know the lens moved
-25.19 mm.

Checks:
  SOURCE   -- the comparison exists and the inspector measures and passes the live field.
  FLAG     -- the flagged pair is captioned, and the caption names 56.57.
  CURRENT  -- an unchanged scene is NOT captioned (no nagging a correct line).
  UNKNOWN  -- an unmeasurable present is never a reason to caption: no delivered_now, or a
              stash with no |m|, leaves the line alone.
  TOLERANCE-- float-noise drift is not staleness; the flagged 7% is.
"""
from __future__ import annotations

import inspect as _inspect

FLAG_STASH = {
    "requested_fov_wh": (50.0, 50.0),
    "delivered_fov_wh": (52.5, 52.5),
    "delivered_m": 0.4389,
    "lens_move_mm": -25.19,
}
FLAG_NOW = (0.40728, (56.57, 56.57))

#: system_info_hud truncates its reason line at this width; the panel is sized to it.
BANNER_LINE_CHARS = 110


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.detector_coverage_overlay import (
        format_focus_summary_lines,
        solve_summary_superseded,
    )

    def _solve_line(stash, now):
        for line in format_focus_summary_lines(None, stash, delivered_now=now):
            if line.startswith("SOLVE"):
                return line
        return ""

    from KrakenOS.UI import open3d_inspector as oi

    src = _inspect.getsource(oi)
    if "_delivered_field_now" in src and "delivered_now=self._delivered_field_now()" in src:
        notes.append("SOURCE = the inspector measures the live field and passes it to the banner")
    else:
        notes.append("SOURCE the banner does not pass a measured delivered_now")
        ok = False

    flagged = format_focus_summary_lines(None, FLAG_STASH, delivered_now=FLAG_NOW)
    line = _solve_line(FLAG_STASH, FLAG_NOW)
    caption = next((text for text in flagged if text.lstrip().startswith("--")), "")
    if "superseded" in line and "56.57" in caption:
        notes.append(f"FLAG = the flagged line is captioned: {line!r} / {caption!r}")
    else:
        notes.append(f"FLAG the flagged line is not captioned with what the scene delivers: {flagged!r}")
        ok = False
    # This session put three layout defects on screen that every logic check passed. Measure.
    overlong = [text for text in flagged if len(text) > BANNER_LINE_CHARS]
    if overlong:
        notes.append(
            f"WIDTH a banner line exceeds the {BANNER_LINE_CHARS}-char cap the reason text is "
            f"truncated to: {[(len(t), t) for t in overlong]}"
        )
        ok = False
    else:
        notes.append(
            f"WIDTH = every line fits the {BANNER_LINE_CHARS}-char banner cap "
            f"(longest {max(len(t) for t in flagged)})"
        )
    if "-25.19" in line and "52.5" in line:
        notes.append("FLAG = the history is KEPT -- the move and the field it delivered are still there")
    else:
        notes.append(f"FLAG the superseded line dropped what the solve did: {line!r}")
        ok = False

    current = _solve_line(FLAG_STASH, (0.4389, (52.5, 52.5)))
    if current.startswith("SOLVE:") and "superseded" not in current:
        notes.append("CURRENT = a line that still describes the scene is left alone")
    else:
        notes.append(f"CURRENT an accurate line was captioned anyway: {current!r}")
        ok = False

    unknowns = {
        "no delivered_now": _solve_line(FLAG_STASH, None),
        "stash without |m|": _solve_line({k: v for k, v in FLAG_STASH.items() if k != "delivered_m"}, FLAG_NOW),
        "unmeasurable now": _solve_line(FLAG_STASH, (0.0, (0.0, 0.0))),
    }
    bad = {tag: text for tag, text in unknowns.items() if "superseded" in text}
    if bad:
        notes.append(f"UNKNOWN an unmeasurable present captioned the line anyway: {bad}")
        ok = False
    else:
        notes.append("UNKNOWN = an unknown present never captions the line")

    noise = solve_summary_superseded(FLAG_STASH, (0.4389 * 1.0002, (52.49, 52.49)))
    real = solve_summary_superseded(FLAG_STASH, FLAG_NOW)
    if not noise and real:
        notes.append("TOLERANCE = 0.02% drift is noise, the flagged 7% is staleness")
    else:
        notes.append(f"TOLERANCE noise={noise!r} real={real!r} -- the threshold does not separate them")
        ok = False

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
