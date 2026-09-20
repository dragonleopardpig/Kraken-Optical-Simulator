"""bugs/0838 guard -- the banner's place is computed from its TEXT, so it sits beside the HUD.

`flag_20260920_205738_022`: *"the banner position is not good, view blocking, please put it
back to beside the system resolution banner."*

bugs/0837's wrapping worked -- the 223-character STRAY LIGHT line wraps to three and nothing
is cut. But 0837 also made the placement decision depend on ``GetSize``, the very measurement
it had just shown to be untrustworthy: the HUD draws ~223 px and ``GetSize`` reported enough
for the anchor to compute x = 0.445 in one capture. With that number the "does the banner
FIT" test failed, so it chose the stacked fallback -- putting the banner ON TOP of the scene,
a worse outcome than the overflow the test was added to prevent. A flaky input used to make a
layout decision.

Placement now derives from the TEXT. Both actors are font size 13, and the ratio is MEASURED
off the flagged captures rather than assumed: the HUD's longest line is 32 characters in a
~223 px box and the wrapped banner's is 110 in a ~719 px box -- 7.0 and 6.5 px per character,
0.54 and 0.50 of the font size. The estimate is deterministic, needs no renderer, and is
wrong by a few pixels rather than by 800.

Checks:
  SOURCE   -- the placement path reads the text, and GetSize is gone from the decision.
  CALIBRATED - the estimator reproduces both drawn widths within tolerance, and errs HIGH
             (which moves the banner away from the HUD, never onto it).
  FLAGGED  -- the real flagged HUD + banner anchor BESIDE the HUD, not stacked.
  GAP      -- the banner starts clear of the HUD's own width.
  OVERSIZE -- a banner that genuinely cannot fit still stacks; the fallback is kept, not lost.
"""
from __future__ import annotations

import inspect as _inspect

FLAG_HUD = (
    "Resolution: 4.102 um/px\n"
    "Magnification: 1.1x (sensor/FOV)\n"
    "Pixels: 5120 x 5120\n"
    "Pixel size: 4.5 um\n"
    "Sensor roll: -90 deg (portrait)"
)
#: The REAL unwrapped lines from the capture. The guard wraps them itself rather than
#: hand-copying the wrapped form -- the first draft trimmed them to ~90 characters to keep this
#: file tidy and then "measured" a banner 70 px narrower than the one on screen.
FLAG_BANNER_RAW = [
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
# bugs/0840 moved both actors to COURIER, so these are re-measured for it -- by rendering off
# screen and asking VTK after a real render, not read off a screenshot. The Arial figures the
# first version carried (223 and 719) were right for the font that was there at the time.
DRAWN_HUD_PX = 256.0      # 32 chars in Courier @ 13
DRAWN_BANNER_PX = 879.0   # 110 chars in Courier @ 13


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_info_hud import solve_banner_anchor, text_actor_width_px
    from KrakenOS.UI import open3d_inspector as oi

    # Match the CALL, not the word: this function's comment explains what GetSize did wrong,
    # and a bare substring check failed on that prose the first time this guard ran -- the
    # third guard today to trip over its own explanation.
    place = _inspect.getsource(oi.Kraken3DInspector._place_solve_banner_beside_system_hud)
    # renderer.GetSize() is the VIEWPORT and is legitimate -- the banner needs the window
    # width. What must not come back is measuring the TEXT ACTORS. The first version of this
    # check forbade any ".GetSize(" and failed on the viewport read.
    calls_getsize = "hud.GetSize(" in place or "actor.GetSize(" in place
    if "text_actor_width_px" in place and not calls_getsize:
        notes.append("SOURCE = placement derives from the TEXT; GetSize is out of the decision")
    else:
        notes.append(
            "SOURCE placement still CALLS GetSize"
            if calls_getsize else "SOURCE placement does not use the text estimator"
        )
        ok = False

    from KrakenOS.UI.services.system_info_hud import wrap_banner_lines

    wrapped = "\n".join(wrap_banner_lines(FLAG_BANNER_RAW))
    hud_px = text_actor_width_px(FLAG_HUD, 13.0)
    banner_px = text_actor_width_px(wrapped, 13.0)
    hud_err = abs(hud_px - DRAWN_HUD_PX) / DRAWN_HUD_PX
    banner_err = abs(banner_px - DRAWN_BANNER_PX) / DRAWN_BANNER_PX
    if hud_err <= 0.20 and banner_err <= 0.20:
        notes.append(
            f"CALIBRATED = HUD {hud_px:.0f} px vs {DRAWN_HUD_PX:.0f} drawn ({hud_err:.0%}), "
            f"banner {banner_px:.0f} vs {DRAWN_BANNER_PX:.0f} ({banner_err:.0%})"
        )
    else:
        notes.append(
            f"CALIBRATED the estimator is off: HUD {hud_px:.0f}/{DRAWN_HUD_PX:.0f} "
            f"({hud_err:.0%}), banner {banner_px:.0f}/{DRAWN_BANNER_PX:.0f} ({banner_err:.0%})"
        )
        ok = False
    if hud_px >= DRAWN_HUD_PX and banner_px >= DRAWN_BANNER_PX:
        notes.append("CALIBRATED = it errs HIGH, which moves the banner away from the HUD")
    else:
        notes.append("CALIBRATED it errs LOW, which can push the banner onto the HUD")
        ok = False

    x_norm, y_norm = solve_banner_anchor(hud_px, banner_px, VIEW_W)
    if y_norm > 0.9:
        notes.append(
            f"FLAGGED = the flagged HUD + banner anchor BESIDE the HUD "
            f"(x={x_norm:.4f}, right edge {x_norm * VIEW_W + banner_px:.0f} of {VIEW_W:.0f})"
        )
    else:
        notes.append(f"FLAGGED the flagged banner still stacks over the scene: {(x_norm, y_norm)}")
        ok = False

    x_px = x_norm * VIEW_W
    if x_px > hud_px:
        notes.append(f"GAP = the banner starts at {x_px:.0f} px, clear of the HUD's {hud_px:.0f}")
    else:
        notes.append(f"GAP the banner starts at {x_px:.0f} px, inside the HUD's {hud_px:.0f}")
        ok = False

    huge = solve_banner_anchor(hud_px, 2400.0, VIEW_W)
    if huge == (0.012, 0.83):
        notes.append("OVERSIZE = a banner that genuinely cannot fit still stacks")
    else:
        notes.append(f"OVERSIZE the stacked fallback was lost: {huge}")
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
