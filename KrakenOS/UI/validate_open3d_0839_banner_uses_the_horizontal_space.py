"""bugs/0839 guard -- the banner uses the horizontal space, and goes vertical only when out.

`flag_20260920_211254_784`, after bugs/0838 put the banner back beside the HUD:
*"as you can see, the banner should make use of the horizontal space more, vertical comes
later if run out of horizontal space."*

bugs/0835 and bugs/0837 wrapped to a FIXED 110 characters. On the flagged 2478 px window that
drew the banner about 725 px wide and stacked 8 lines while ~1400 px sat empty to its right.
A constant cannot know the window.

The budget is now the room that is actually there: viewport, less where the banner starts
beside the HUD, less a margin, over the per-character advance. The 223-character STRAY LIGHT
line then stops wrapping at all on a wide window, and still wraps on a narrow one.

Checks:
  SOURCE     -- the wrap budget is computed from the viewport at the assembly point.
  HORIZONTAL -- on the flagged 2478 px window the 223-char line does NOT wrap.
  FEWER      -- it uses fewer lines than the fixed-110 rule it replaces.
  VERTICAL   -- a narrower window wraps MORE: vertical does come later, not never.
  FITS       -- at every width tried the banner's right edge stays inside the viewport.
  FLOOR      -- a cramped window degrades to a readable column, not to slivers.
"""
from __future__ import annotations

import inspect as _inspect

HUD = (
    "Resolution: 4.102 um/px\n"
    "Magnification: 1.1x (sensor/FOV)\n"
    "Pixels: 5120 x 5120\n"
    "Pixel size: 4.5 um\n"
    "Sensor roll: -90 deg (portrait)"
)
RAW = [
    "SOLVE: delivering 21 x 21 mm (|m| 1.097); the lens moved -145.2 mm along its leg",
    "FOCUS: the image forms 0.1155 mm in front of the sensor -- spot 0.489 um there vs 3.06 um on the sensor",
    "  Face A field: 0.1155 mm in front of the sensor",
    "  Face B field: 0.1155 mm in front of the sensor",
    "Landed: the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing to move",
    "STRAY LIGHT: 8 ray(s) reach the sensor by another optical route and land up to 1.56 mm "
    "outside the image (0.6% of the landing rays) -- not part of the image, left out of the "
    "focus measurement and drawn faint in the 3D scene",
]
FLAG_VIEW_W = 2478.0


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_info_hud import (
        BANNER_MIN_WRAP_CHARS,
        BANNER_REASON_WIDTH,
        banner_wrap_chars,
        solve_banner_anchor,
        text_actor_width_px,
        wrap_banner_lines,
    )
    from KrakenOS.UI import open3d_inspector as oi

    src = _inspect.getsource(oi.Kraken3DInspector._update_solve_refusal_banner)
    if "banner_wrap_chars(" in src:
        notes.append("SOURCE = the wrap budget is computed from the viewport at the assembly point")
    else:
        notes.append("SOURCE the banner still wraps to a constant")
        ok = False

    hud_px = text_actor_width_px(HUD, 13.0)

    def measure(view_w):
        budget = banner_wrap_chars(hud_px, view_w, 13.0)
        wrapped = wrap_banner_lines(RAW, width=budget)
        banner_px = text_actor_width_px("\n".join(wrapped), 13.0)
        x_norm, _y = solve_banner_anchor(hud_px, banner_px, view_w)
        return budget, wrapped, banner_px, x_norm * view_w + banner_px

    longest_raw = max(len(line) for line in RAW)
    budget, wrapped, banner_px, right = measure(FLAG_VIEW_W)
    if budget >= longest_raw and max(len(t) for t in wrapped) == longest_raw:
        notes.append(
            f"HORIZONTAL = on {FLAG_VIEW_W:.0f} px the budget is {budget} chars, so the "
            f"{longest_raw}-char line does not wrap at all"
        )
    else:
        notes.append(
            f"HORIZONTAL the {longest_raw}-char line still wraps on a {FLAG_VIEW_W:.0f} px "
            f"window (budget {budget})"
        )
        ok = False

    fixed = wrap_banner_lines(RAW, width=int(BANNER_REASON_WIDTH))
    if len(wrapped) < len(fixed):
        notes.append(
            f"FEWER = {len(wrapped)} lines against the fixed-{int(BANNER_REASON_WIDTH)} rule's "
            f"{len(fixed)}"
        )
    else:
        notes.append(f"FEWER no improvement: {len(wrapped)} lines vs {len(fixed)}")
        ok = False

    narrow_budget, narrow_wrapped, _px, _r = measure(900.0)
    if len(narrow_wrapped) > len(wrapped) and narrow_budget < budget:
        notes.append(
            f"VERTICAL = a 900 px window wraps to {len(narrow_wrapped)} lines at "
            f"{narrow_budget} chars -- vertical comes later, not never"
        )
    else:
        notes.append(f"VERTICAL a narrow window did not wrap more: {len(narrow_wrapped)} lines")
        ok = False

    overflow = []
    for view_w in (2478.0, 1920.0, 1600.0, 1280.0, 900.0, 640.0):
        _b, _w, _px, right_edge = measure(view_w)
        if right_edge > view_w + 1.0:
            overflow.append((view_w, round(right_edge, 1)))
    if overflow:
        notes.append(f"FITS the banner runs past the viewport at {overflow}")
        ok = False
    else:
        notes.append("FITS = the right edge stays inside the viewport at every width tried")

    tiny = banner_wrap_chars(hud_px, 320.0, 13.0)
    if tiny == int(BANNER_MIN_WRAP_CHARS):
        notes.append(
            f"FLOOR = a cramped window floors at {BANNER_MIN_WRAP_CHARS} chars rather than "
            "degrading to slivers"
        )
    else:
        notes.append(f"FLOOR a 320 px window produced {tiny} chars")
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
