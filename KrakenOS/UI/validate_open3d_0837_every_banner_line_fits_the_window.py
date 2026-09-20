"""bugs/0837 guard -- every banner line fits, and the banner fits the window.

`flag_20260920_203630_905` ("the banner seems shift to the right") and
`flag_20260920_204200_878` ("this time banner at the left"), both on the Phase D build.

Two defects, both visible in the 20:36 capture:

1. **The lines were never wrapped.** bugs/0835 wrapped the refusal's ``reason`` and stopped
   there -- it fixed one line when the defect was in the formatter. The focus summary's lines
   never passed through it, and the STRAY LIGHT line ran to **223 characters**, rendered about
   1500 px, and was cut by the WINDOW EDGE at "...left out of the focus measu", losing "and
   drawn faint in the 3D scene". The same loss as 0835 with no character cap involved.

2. **Placement bounded only the START.** ``if x_norm > 0.72`` says nothing about where the
   banner ENDS. A start of 0.445 passed it and the banner still ran off a 2478 px window.

Both now come from one place each: every line is wrapped where the text is assembled, so any
future producer is covered, and the anchor is pure arithmetic that takes the banner's own
width.

Checks:
  SOURCE  -- wrapping happens at the assembly point, and the anchor reads the banner width.
  FLAG    -- the real 20:36 banner: 223-char line reproduced, then wrapped within budget.
  LOSSLESS-- rejoining the wrapped banner reproduces every line: nothing is dropped.
  ANCHOR  -- a banner that does not fit beside the HUD stacks instead; one that fits does not.
  EDGE    -- the flagged geometry (start 0.445, ~1500 px banner, 2478 px window) now stacks.
  SHORT   -- lines already inside the budget are untouched.
"""
from __future__ import annotations

import inspect as _inspect
import re

FLAG_BANNER = [
    "SOLVE: delivering 21 x 21 mm (|m| 1.097); the lens moved -145.2 mm along its leg",
    "FOCUS: the image forms 0.1155 mm in front of the sensor -- spot 0.489 um there vs 3.06 um on the sensor",
    "  Face A field: 0.1155 mm in front of the sensor",
    "  Face B field: 0.1155 mm in front of the sensor",
    "Landed: the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing to move",
    "STRAY LIGHT: 8 ray(s) reach the sensor by another optical route and land up to 1.56 mm "
    "outside the image (0.6% of the landing rays) -- not part of the image, left out of the "
    "focus measurement and drawn faint in the 3D scene",
]
VIEW_W = 2478.0
HUD_W = 285.0


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_info_hud import (
        BANNER_REASON_WIDTH,
        solve_banner_anchor,
        wrap_banner_lines,
    )
    from KrakenOS.UI import open3d_inspector as oi

    width = int(BANNER_REASON_WIDTH)
    src = _inspect.getsource(oi.Kraken3DInspector._update_solve_refusal_banner)
    place = _inspect.getsource(oi.Kraken3DInspector._place_solve_banner_beside_system_hud)
    # bugs/0840 replaced the plain wrap at this point with the table formatter, which wraps
    # each cell -- and the gate BLOCKED here, because this check named the CALL instead of the
    # claim. The second time in one session that one of my guards pinned an implementation and
    # failed on its own successor (bugs/0838 did it to bugs/0837's GetSize check). What must
    # stay true is that the LINES ARE LAID OUT where they are assembled, so no producer can
    # emit an unbounded line.
    lays_out = "wrap_banner_lines(lines" in src or "format_kv_table(lines" in src
    if lays_out:
        notes.append("SOURCE = every line is laid out where the banner text is assembled")
    else:
        notes.append("SOURCE the assembly point does not bound its lines")
        ok = False
    # bugs/0838 superseded HOW the width is obtained: this check originally demanded
    # `GetSize(renderer, banner_size)`, and when 0838 replaced that with a text-derived
    # estimate the gate BLOCKED on this phase -- two of my own guards contradicting each
    # other. The durable claim is that placement knows the banner's own width and feeds the
    # pure anchor, not which call supplies it.
    measures_banner = "text_actor_width_px(" in place or "GetSize(renderer, banner_size)" in place
    if "solve_banner_anchor(" in place and measures_banner:
        notes.append("SOURCE = placement measures the BANNER's own width and uses the pure anchor")
    else:
        notes.append("SOURCE placement does not read the banner width")
        ok = False

    longest = max(len(line) for line in FLAG_BANNER)
    if longest > 2 * width:
        notes.append(
            f"FLAG = the real 20:36 banner really did carry a {longest}-char line "
            f"({longest / width:.1f}x the {width} budget) -- the defect reproduces"
        )
    else:
        notes.append(f"FLAG the flagged banner's longest line is {longest}; it no longer reproduces")
        ok = False

    wrapped = wrap_banner_lines(FLAG_BANNER)
    over = [(len(t), t[:48]) for t in wrapped if len(t) > width]
    if over:
        notes.append(f"FLAG a wrapped line still exceeds {width}: {over}")
        ok = False
    else:
        notes.append(
            f"FLAG = wrapped to {len(wrapped)} lines, longest {max(len(t) for t in wrapped)}, "
            f"budget {width}"
        )

    flat_in = re.sub(r"\s+", " ", " ".join(FLAG_BANNER)).strip()
    flat_out = re.sub(r"\s+", " ", " ".join(wrapped)).strip()
    if flat_in == flat_out:
        notes.append("LOSSLESS = rejoining the wrapped banner reproduces every line exactly")
    else:
        notes.append("LOSSLESS the wrap changed the banner's text")
        ok = False
    for token in ("drawn faint in the 3D scene", "nothing to move", "Face B field"):
        if token not in flat_out:
            notes.append(f"LOSSLESS the wrap dropped {token!r}")
            ok = False

    beside = solve_banner_anchor(HUD_W, 700.0, VIEW_W)
    # 1500 px beside a 285 px HUD genuinely FITS (333 + 1500 + 12 = 1845 of 2478) -- the first
    # draft of this check asserted it stacked, and the code was right. Use a width that really
    # cannot fit, so the check tests the rule rather than my arithmetic.
    stacked = solve_banner_anchor(HUD_W, 2200.0, VIEW_W)
    if beside[1] > 0.9 and beside[0] > 0.012:
        notes.append(f"ANCHOR = a banner that FITS sits beside the HUD at x={beside[0]:.3f}")
    else:
        notes.append(f"ANCHOR a fitting banner was stacked anyway: {beside}")
        ok = False
    if stacked == (0.012, 0.83):
        notes.append(
            "ANCHOR = a banner too wide to fit beside the HUD (2200 px of a 2478 px window) "
            "stacks underneath"
        )
    else:
        notes.append(f"ANCHOR an overflowing banner was left beside the HUD: {stacked}")
        ok = False

    # The flagged geometry exactly: start 0.445 implies a HUD measured at ~1055 px.
    flagged = solve_banner_anchor(1055.0, 1500.0, VIEW_W)
    old_x = 0.012 + (1055.0 + 18.0) / VIEW_W
    if old_x <= 0.72 and flagged == (0.012, 0.83):
        notes.append(
            f"EDGE = the flagged geometry (old rule put it at x={old_x:.3f}, which its own "
            f"0.72 check passed) now stacks instead of running off the window"
        )
    else:
        notes.append(f"EDGE the flagged geometry still places at {flagged} (old x={old_x:.3f})")
        ok = False

    short = ["SOLVE: delivering 21 x 21 mm", "  Face A field: 0.1155 mm in front of the sensor"]
    if wrap_banner_lines(short) == short:
        notes.append("SHORT = lines already inside the budget are untouched")
    else:
        notes.append(f"SHORT a short line was altered: {wrap_banner_lines(short)!r}")
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
