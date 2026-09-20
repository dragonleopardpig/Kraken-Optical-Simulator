"""bugs/0835 guard -- the refusal's reason wraps instead of losing its ending.

flag_20260920_182008. The banner read:

    that field needs the lens -131.2 mm along its leg, but only 129.2 mm of physical
    room is left before its bo...

``reason[:107] + "..."`` kept the panel narrow by throwing the rest away. The whole sentence
is 254 characters and the 147 it discarded were the ones worth having: WHICH body the lens
reaches ("RA mirror 1 (50 mm)"), the station gap, the shortfall, and the remedy. It cut
mid-word, which is at least how the user could tell something was missing rather than ended.

Wrapping keeps the panel exactly as wide as the cap intended -- the panel is sized to its
longest line -- while keeping the sentence.

Checks:
  SOURCE    -- the truncation is gone and the wrapper is what the banner calls.
  OLD       -- the old rule really did cut mid-word and swallow the obstacle's name, so a
               revert cannot pass.
  WIDTH     -- every wrapped line fits the cap (this session has shipped three layout
               defects that every logic check passed; widths get measured).
  LOSSLESS  -- re-joining the lines reproduces the sentence: nothing is dropped.
  HYPHENS   -- "ELS-85", "48-926" and "-131.2" are never split across a line break.
  RUNAWAY   -- a reason that will not end is capped, and says so.
  BANNER    -- the real formatter emits the wrapped lines for the flagged refusal.
"""
from __future__ import annotations

import inspect as _inspect
import re

FLAG_REASON = (
    "that field needs the lens -131.2 mm along its leg, but only 129.2 mm of physical room is "
    "left before its body reaches RA mirror 1 (50 mm) (station gap 180.5 mm; short by 1.983 mm) "
    "-- a different lens / working distance, or Force FOV to SEE the collision."
)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import system_info_hud as hud

    width = int(hud.BANNER_REASON_WIDTH)
    # Match the EXECUTABLE line, not the phrase: the wrapper's own docstring quotes the old
    # expression to explain itself, and a substring check failed on that prose the first time
    # this guard ran.
    src = _inspect.getsource(hud.format_solve_refusal_lines)
    if "len(reason) <= " in src:
        notes.append("SOURCE the truncation is still in the formatter")
        ok = False
    elif "wrap_banner_reason(reason)" in src:
        notes.append("SOURCE = the banner wraps the reason rather than cutting it")
    else:
        notes.append("SOURCE the banner does not call the wrapper")
        ok = False

    # The pre-0835 rule, re-run here.
    old = FLAG_REASON[:107] + "..."
    if len(FLAG_REASON) > width and "RA mirror 1" not in old and not old[106].isspace():
        notes.append(
            f"OLD = the old rule really did cut mid-word and lose the obstacle: ...{old[-24:]!r}"
        )
    else:
        notes.append("OLD the flagged reason no longer reproduces the defect; the guard proves nothing")
        ok = False

    lines = hud.wrap_banner_reason(FLAG_REASON)
    overlong = [(len(text), text) for text in lines if len(text) > width]
    if overlong:
        notes.append(f"WIDTH a wrapped line exceeds the {width}-char cap: {overlong}")
        ok = False
    else:
        notes.append(
            f"WIDTH = {len(lines)} lines, longest {max(len(t) for t in lines)}, cap {width}"
        )

    rejoined = re.sub(r"\s+", " ", " ".join(text.strip() for text in lines)).strip()
    if rejoined == re.sub(r"\s+", " ", FLAG_REASON).strip():
        notes.append("LOSSLESS = re-joining the lines reproduces the sentence exactly")
    else:
        notes.append(f"LOSSLESS the wrap changed the text: {rejoined!r}")
        ok = False
    for token in ("RA mirror 1 (50 mm)", "station gap", "Force FOV"):
        if token not in rejoined:
            notes.append(f"LOSSLESS the wrap dropped {token!r}")
            ok = False

    hyphen_text = (
        "swapping the ELS-85 for the PYRITE 45-85 needs the lens -131.2 mm along its leg, and the "
        "Filter 48-926 is only 0.271 mm away, so the barrel reaches it before the field is "
        "delivered -- pick a shorter back focal distance or move the fold arm."
    )
    hyphen_lines = hud.wrap_banner_reason(hyphen_text)
    split_tokens = [
        token for token in ("ELS-85", "45-85", "48-926", "-131.2")
        if not any(token in text for text in hyphen_lines)
    ]
    if split_tokens:
        notes.append(f"HYPHENS a hyphenated token was split across lines: {split_tokens}")
        ok = False
    else:
        notes.append("HYPHENS = ELS-85 / 45-85 / 48-926 / -131.2 all survive the wrap whole")

    short = "no imaging-lens block to drive."
    if hud.wrap_banner_reason(short) == [short]:
        notes.append("SHORT = a reason that already fits is passed through untouched")
    else:
        notes.append(f"SHORT a short reason was altered: {hud.wrap_banner_reason(short)!r}")
        ok = False

    runaway = hud.wrap_banner_reason("the lens will not fit " * 200)
    if len(runaway) <= int(hud.BANNER_REASON_MAX_LINES) and runaway[-1].rstrip().endswith("..."):
        notes.append(
            f"RUNAWAY = capped at {len(runaway)} lines and says it was cut "
            f"(max {hud.BANNER_REASON_MAX_LINES})"
        )
    else:
        notes.append(f"RUNAWAY a runaway reason was not capped: {len(runaway)} lines")
        ok = False

    banner = hud.format_solve_refusal_lines(
        {
            "requested_fov_wh": (21.0, 1.05),
            "target_m": 1.097,
            "lens_move_needed_mm": -131.2,
            "leg_room_mm": 129.2,
            "delivered_m": 0.407,
            "delivered_fov_wh": (56.57, 56.57),
            "reason": FLAG_REASON,
        }
    )
    if any("RA mirror 1 (50 mm)" in text for text in banner):
        wide = [(len(t), t) for t in banner if len(t) > width]
        if wide:
            notes.append(f"BANNER a real banner line exceeds the cap: {wide}")
            ok = False
        else:
            notes.append(
                f"BANNER = the real refusal names its obstacle, in {len(banner)} lines, "
                f"longest {max(len(t) for t in banner)}"
            )
    else:
        notes.append(f"BANNER the real refusal still does not name its obstacle: {banner!r}")
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
