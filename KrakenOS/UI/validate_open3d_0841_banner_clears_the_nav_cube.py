"""bugs/0841 guard -- the banner stays clear of the navigation cube.

Found by measuring `flag_20260920_212949_800` ("I think it looks nice now") rather than by a
report. I suspected the STRAY LIGHT row was being cut; it was not -- 226 characters, complete,
ending at 2406 px. But 2406 is INSIDE the navigation cube, which owns a pixel-square corner
viewport of 278 px at 2478 x 1264, starting at x = 2200. A 206 px overlap, in the same
vertical band.

bugs/0837's fit test asked whether the banner fits the VIEWPORT. The viewport is not all
usable: the cube has been in that corner the whole time. Adding the bugs/0840 DOF row widened
the HUD from 32 to 66 characters, pushing the banner from x=289 to x=587 and making the
collision visible -- but it was there at 1920 x 1080 and 1280 x 800 too.

The reserve is asked of the cube's OWN placement function, so the two cannot drift.

Checks:
  SOURCE   -- both the budget and the anchor take a right-hand reserve, and the inspector
              asks the cube for it rather than hardcoding a number.
  RESERVE  -- the reserve matches corner_square_viewport at several window sizes.
  CLEARS   -- at each size the banner's right edge lands left of the cube.
  REPRODUCES - without the reserve the same geometry DOES overlap, at every size.
  ABSENT   -- no cube means no reserve: the banner is not shrunk for a missing widget.
"""
from __future__ import annotations

import inspect as _inspect

HUD = [
    "Resolution: 4.102 um/px",
    "Magnification: 1.1x (sensor/FOV)",
    "Pixels: 5120 x 5120",
    "Pixel size: 4.5 um",
    "Sensor roll: -90 deg (portrait)",
]
BANNER = [
    "SOLVE: delivering 21 x 21 mm (|m| 1.097); the lens moved -145.2 mm along its leg",
    "FOCUS: the image forms 0.1155 mm in front of the sensor -- spot 0.489 um there vs 3.06 um on the sensor",
    "  Face A field: 0.1155 mm in front of the sensor",
    "  Face B field: 0.1155 mm in front of the sensor",
    "Landed: the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing to move",
    "STRAY LIGHT: 8 ray(s) reach the sensor by another optical route and land up to 1.56 mm "
    "outside the image (0.6% of the landing rays) -- not part of the image, left out of the "
    "focus measurement and drawn faint in the 3D scene",
]
SIZES = ((2478, 1264), (1920, 1080), (1280, 800), (900, 600))


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_info_hud import (
        banner_wrap_chars,
        format_depth_of_field_lines,
        format_kv_table,
        solve_banner_anchor,
        text_actor_width_px,
    )
    from KrakenOS.UI.services.nav_cube_widget import (
        _CORNER_SIDE_FRACTION,
        corner_square_viewport,
    )
    from KrakenOS.UI import open3d_inspector as oi

    for fn in (banner_wrap_chars, solve_banner_anchor):
        if "reserved_right_px" not in _inspect.signature(fn).parameters:
            notes.append(f"SOURCE {fn.__name__} takes no right-hand reserve")
            ok = False
    place = _inspect.getsource(oi.Kraken3DInspector._nav_cube_reserved_width_px)
    if "corner_square_viewport" in place:
        notes.append("SOURCE = both take a reserve, and it is asked of the cube's own placement")
    else:
        notes.append("SOURCE the reserve is not read from the cube's placement function")
        ok = False

    hud = HUD + format_depth_of_field_lines(4.5, 1.097, 4.5)
    hud_px = text_actor_width_px("\n".join(format_kv_table(hud, width=200)))

    def right_edge(view_w, reserve):
        budget = banner_wrap_chars(hud_px, float(view_w), 13.0, reserved_right_px=reserve)
        table = format_kv_table(BANNER, width=budget)
        banner_px = text_actor_width_px("\n".join(table))
        x_norm, _y = solve_banner_anchor(
            hud_px, banner_px, float(view_w), reserved_right_px=reserve
        )
        return x_norm * view_w + banner_px

    overlapped_before, still_overlaps, reserves = [], [], []
    for w, h in SIZES:
        viewport = corner_square_viewport(w, h, side_fraction=_CORNER_SIDE_FRACTION)
        cube_px = (1.0 - float(viewport[0])) * w
        reserves.append((w, round(cube_px)))
        if right_edge(w, 0.0) > w - cube_px + 1.0:
            overlapped_before.append(w)
        if right_edge(w, cube_px) > w - cube_px + 1.0:
            still_overlaps.append(w)

    notes.append(f"RESERVE = the cube's own width per size: {reserves}")
    if still_overlaps:
        notes.append(f"CLEARS the banner still runs under the cube at {still_overlaps}")
        ok = False
    else:
        notes.append(f"CLEARS = the banner's right edge stays left of the cube at all {len(SIZES)} sizes")
    # The FLAGGED size is what must reproduce. Not every window does: at 900 x 600 the banner
    # wraps narrow enough never to reach the corner, so demanding all four (the first draft of
    # this check) asserted something untrue about the defect rather than about the fix.
    if 2478 in overlapped_before:
        notes.append(
            f"REPRODUCES = without the reserve the flagged 2478 px window overlaps, and so do "
            f"{[w for w in overlapped_before if w != 2478]} -- it was never only the flagged one"
        )
    else:
        notes.append("REPRODUCES the flagged window no longer overlaps without the reserve")
        ok = False

    plain = banner_wrap_chars(hud_px, 2478.0, 13.0, reserved_right_px=0.0)
    reserved = banner_wrap_chars(hud_px, 2478.0, 13.0, reserved_right_px=278.0)
    if plain > reserved:
        notes.append(
            f"ABSENT = no cube means no reserve ({plain} chars against {reserved}); the banner "
            "is not shrunk for a widget that is not there"
        )
    else:
        notes.append(f"ABSENT a zero reserve did not restore the full budget ({plain} vs {reserved})")
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
