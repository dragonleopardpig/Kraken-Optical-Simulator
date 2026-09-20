"""System-information HUD for the Open 3D canvas (bugs/0628, user feature).

Four rows in the top-left corner of the 3D scene:

    Resolution:    10.74 um/px      (delivered FOV / camera pixel count)
    Magnification: 0.419x           (sensor size / delivered FOV -- the optical |m|)
    Pixels:        5120 x 5120      (camera resolution)
    Pixel size:    2.5 um

The FOV comes from ``QuickEstimationService.object_fov_dimensions()`` -- the same
DELIVERED-field reader the drawn green FOV square uses (bugs/0602 doctrine: display
readers use delivered values), so the HUD can never disagree with the scene. Camera
pixel data comes from the registered camera record; rows degrade gracefully when a
source is missing (no camera -> no pixel rows; no finite FOV -> no optical rows;
nothing -> the HUD hides).
"""

from __future__ import annotations

from types import SimpleNamespace


def _fmt(value: float, digits: int = 4) -> str:
    return f"{float(value):.{digits}g}"


def _pair_or_single(a: float, b: float, unit: str, digits: int = 4) -> str:
    """One value when the two axes agree within 1%, else both."""
    if abs(a - b) <= 0.01 * max(abs(a), abs(b), 1e-12):
        return f"{_fmt((a + b) / 2.0, digits)}{unit}"
    return f"{_fmt(a, digits)}{unit} / {_fmt(b, digits)}{unit}"


def format_system_info_lines(fov_wh, sensor_wh, resolution_px, pixel_size_um) -> list[str]:
    """Pure formatter -- display-free and guardable.

    ``fov_wh`` / ``sensor_wh``: (width, height) in mm or None.
    ``resolution_px``: (N1, N2) or None.  ``pixel_size_um``: (w, h) um or None.
    """
    lines: list[str] = []

    fov_ok = (
        fov_wh is not None
        and len(fov_wh) >= 2
        and all(v is not None and float(v) > 0 for v in fov_wh[:2])
    )
    res_ok = (
        resolution_px is not None
        and len(resolution_px) >= 2
        and all(v is not None and int(v) > 0 for v in resolution_px[:2])
    )
    sensor_ok = (
        sensor_wh is not None
        and len(sensor_wh) >= 2
        and all(v is not None and float(v) > 0 for v in sensor_wh[:2])
    )

    if fov_ok and res_ok:
        rx = float(fov_wh[0]) / int(resolution_px[0]) * 1000.0
        ry = float(fov_wh[1]) / int(resolution_px[1]) * 1000.0
        lines.append(f"Resolution: {_pair_or_single(rx, ry, ' um/px')}")
    if fov_ok and sensor_ok:
        mx = float(sensor_wh[0]) / float(fov_wh[0])
        my = float(sensor_wh[1]) / float(fov_wh[1])
        lines.append(f"Magnification: {_pair_or_single(mx, my, 'x', digits=3)} (sensor/FOV)")
    if res_ok:
        lines.append(f"Pixels: {int(resolution_px[0])} x {int(resolution_px[1])}")
    if (
        pixel_size_um is not None
        and len(pixel_size_um) >= 2
        and all(v is not None and float(v) > 0 for v in pixel_size_um[:2])
    ):
        lines.append(
            f"Pixel size: {_pair_or_single(float(pixel_size_um[0]), float(pixel_size_um[1]), ' um', digits=3)}"
        )
    return lines


def format_sensor_roll_lines(orientation) -> list[str]:
    """bugs/0808: say when the camera is rolled -- and when the roll is not a quarter turn, that the
    sensor is modelled at the nearest one (the launched field and the solves are axis-aligned)."""
    if not isinstance(orientation, dict):
        return []
    try:
        roll = float(orientation.get("roll_deg", 0.0))
        residual = float(orientation.get("residual_deg", 0.0))
        quarter = int(orientation.get("quarter_turns", 0))
    except (TypeError, ValueError):
        return []
    if abs(roll) < 1e-6 or abs(abs(roll) - 180.0) < 1e-6:
        return []
    if abs(residual) < 0.05:
        return [f"Sensor roll: {roll:.0f} deg" + (" (portrait)" if quarter % 2 else "")]
    return [f"Sensor roll: {roll:.4g} deg -- modelled at {90 * round(roll / 90.0):.0f} deg "
            f"(only quarter turns rotate the field)"]


def system_info_hud_text(editor) -> str:
    """Gather the HUD inputs from the live editor and format them.

    Every source is best-effort: a scene without finite imaging or without a
    registered camera simply loses the dependent rows.
    """
    fov = sensor = None
    try:
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService

        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        fov = qe.object_fov_dimensions()
        sensor = qe.sensor_active_dimensions()
    except Exception:
        fov = sensor = None
    resolution = pixel_size = None
    try:
        record = editor._current_camera_record()
        if isinstance(record, dict):
            resolution = record.get("resolution_px")
            pixel_size = record.get("pixel_size_um")
    except Exception:
        resolution = pixel_size = None
    # bugs/0808: the FOV and sensor pairs are in the WORLD frame (width = horizontal); a camera
    # rolled a quarter turn carries its pixel rows vertically, so pair them the same way.
    orientation = None
    try:
        orientation = editor._camera_sensor_orientation()
    except Exception:
        orientation = None
    if isinstance(orientation, dict) and orientation.get("swapped"):
        try:
            if resolution is not None and len(resolution) >= 2:
                resolution = (resolution[1], resolution[0])
            if pixel_size is not None and len(pixel_size) >= 2:
                pixel_size = (pixel_size[1], pixel_size[0])
        except TypeError:
            pass
    lines = format_system_info_lines(fov, sensor, resolution, pixel_size)
    lines = lines + format_sensor_roll_lines(orientation)
    # bugs/0719: the NON-banner focus-residual readout -- the lens is at the requested WD,
    # the sensor was left where the vendor put it, and the exact conjugate's track mismatch
    # is a number the user needs to see in the scene (not a refusal, so not the red banner).
    try:
        lines = lines + format_focus_residual_lines(
            editor.__dict__.get("_fov_solve_focus_residual_info")
        )
    except Exception:
        pass
    # bugs/0840 (user request): object-side depth of field at the one-pixel criterion. The
    # f-number comes from the aperture the scene is actually set to -- FNO only, because an
    # EPD or NA entry is not an f-number and converting one silently would be a fabricated
    # input to a number the user will act on.
    try:
        aperture_type = str(editor.aperture_type_var.get() or "").strip().upper()
        if aperture_type == "FNO":
            magnification = None
            if fov is not None and sensor is not None:
                try:
                    magnification = float(sensor[0]) / float(fov[0])
                except (TypeError, ValueError, ZeroDivisionError, IndexError):
                    magnification = None
            pixel = None
            if pixel_size is not None and len(pixel_size) >= 1:
                pixel = pixel_size[0]
            lines = lines + format_depth_of_field_lines(
                editor.aperture_value_var.get(), magnification, pixel
            )
    except Exception:
        pass
    # bugs/0840: the HUD is point form too -- align it. Generous width: the HUD sits top-left
    # against nothing, so its rows should not wrap, only line up.
    return "\n".join(format_kv_table(lines, width=200))


def format_focus_residual_lines(info) -> list[str]:
    """bugs/0719: HUD lines for a SUCCESSFUL FOV solve whose exact conjugate would have
    needed vendor hardware (camera/sensor) or the object to move -- the lens was moved to
    the working distance, nothing else. Pure formatter -- display-free and guardable.
    ``info`` is the ``_fov_solve_focus_residual_info`` dict; [] when there is none."""
    if not isinstance(info, dict) or not info:
        return []
    lines: list[str] = []
    residual = info.get("image_delta_mm")
    if residual is not None:
        verb = "shortened" if float(residual) < 0.0 else "lengthened"
        lines.append(
            f"Focus residual: the exact conjugate needs the object/sensor track {verb} by "
            f"{abs(float(residual)):.4g} mm (device stage / camera focus is your call)"
        )
    # bugs/0754 (flag 20260908_133248_992, user: "Why the image is not landed on the sensor?
    # I need a configuration to land the image on the sensor"): the residual says how far this
    # misses; a fixed track focuses exactly two magnifications, so NAME them. Without this the
    # scene reports a failure and no way out.
    for entry in list(info.get("in_focus_fields") or []):
        if not isinstance(entry, dict):
            continue
        try:
            field_w = float(entry["field_w_mm"])
            field_h = float(entry["field_h_mm"])
            magnitude = float(entry["m"])
        except (KeyError, TypeError, ValueError):
            continue
        lines.append(
            f"This track DOES focus a {field_w:.4g} x {field_h:.4g} mm object field "
            f"(|m| {magnitude:.4g}) -- ask for that and the image lands on the sensor"
        )
    moved = info.get("lens_move_mm")
    tail = "Lens at WD"
    if moved is not None:
        wd_verb = "shortened" if float(moved) < 0.0 else "lengthened"
        tail += f" (moved {float(moved):+.4g} mm along its leg; WD {wd_verb} by {abs(float(moved)):.4g} mm)"
    tail += "; vendor hardware untouched -- Trace Now shows the true focus"
    lines.append(tail)
    return lines


def solve_banner_outcome(info) -> str:
    """bugs/0726: what the banner is actually reporting.

    ``"refused"``      nothing was applied -- the solve could not deliver the request.
    ``"forced_crash"`` a forced move was applied and the lens body PENETRATES hardware.
    ``"forced_fits"``  a forced move was applied and it FITS (clearance remains).
    ``""``             nothing to report.

    The user forced a solve to SEE a collision and got "SOLVE REFUSED -- inspect the 3D
    overlap" over a move that left 20 mm of clearance, while the status line said the solve
    succeeded (flag_20260907_083535_680: "forced crash. But the lens is not crashing").
    A forced move that fits is neither a refusal nor an overlap.
    """
    if not isinstance(info, dict) or not info:
        return ""
    applied = info.get("forced_moved_mm") is not None or info.get("forced_penetration_mm") is not None
    if not applied:
        return "refused"
    penetration = info.get("forced_penetration_mm")
    try:
        if penetration is not None and float(penetration) < 0.0:
            return "forced_crash"
    except (TypeError, ValueError):
        pass
    return "forced_fits"


#: bugs/0835: the banner panel is sized to its longest line, so this is what keeps the block
#: readable. The reason used to be CUT to it; it is now WRAPPED to it.
BANNER_REASON_WIDTH = 110
#: More than this and it is a runaway, not an explanation.
BANNER_REASON_MAX_LINES = 4


def wrap_banner_reason(
    reason, *, width: int = BANNER_REASON_WIDTH, max_lines: int = BANNER_REASON_MAX_LINES
) -> list[str]:
    """bugs/0835: the refusal's reason WRAPPED onto continuation lines instead of cut off.

    ``reason[:107] + "..."`` kept the panel narrow by throwing away the end of the sentence.
    On flag_20260920_182008 that read:

        that field needs the lens -131.2 mm along its leg, but only 129.2 mm of physical
        room is left before its bo...

    and the words it swallowed were the ones worth having: WHICH body the lens reaches
    ("RA mirror 1 (50 mm)"), the station gap, the shortfall, and the remedy. The whole sentence
    is 250 characters; the user saw 107 of them, ending mid-word.

    Wrapping keeps the panel exactly as wide as the cap intended while keeping the sentence.
    Hyphens are never break points, so "ELS-85", "48-926" and "-131.2" stay whole; a token
    longer than the whole width (there is no such number, but a path would be) is broken rather
    than allowed to overflow the panel the cap exists to protect.
    """
    import textwrap

    text = str(reason or "").strip()
    if not text:
        return []
    try:
        wrapped = textwrap.wrap(
            text,
            width=int(width),
            subsequent_indent="  ",
            break_long_words=True,
            break_on_hyphens=False,
            max_lines=int(max_lines),
            placeholder=" ...",
        )
    except Exception:
        # Never let the formatter be the thing that fails: the un-wrapped sentence beats none.
        return [text]
    return wrapped or [text]


def split_label(line: str) -> "tuple[str, str, str]":
    """bugs/0840: ``(indent, label, detail)`` for a banner/HUD line.

    Every line these actors produce is already point form -- ``SOLVE: ...``, ``FOCUS: ...``,
    ``Pixel size: ...`` -- which is a two-column structure being rendered as prose. The user
    said so: *"since the banner use a point form, why not display it as a table?"*

    Splits on the FIRST ``": "``. A label is only a label if it is short and carries no
    sentence punctuation, so ``"SOLVE REFUSED -- the drawn scene does NOT deliver this
    request"`` stays one full-width row rather than being cut at some interior colon.
    """
    raw = str(line or "")
    stripped = raw.lstrip()
    indent = raw[: len(raw) - len(stripped)]
    head, sep, tail = stripped.partition(": ")
    if not sep or len(head) > 24 or any(ch in head for ch in ".!?;"):
        return indent, "", stripped
    return indent, head, tail


def format_kv_table(lines, *, width: int, gap: int = 2) -> list[str]:
    """bugs/0840: render point-form lines as an aligned two-column table.

    The label column is as wide as the widest label; the detail column takes the rest and
    wraps into it, with continuations indented to the column so a wrapped value still reads as
    one cell. A line with no label spans the full width -- headings like "SOLVE REFUSED ..."
    are not values and should not be forced into a column.

    Alignment by space padding only works in a MONOSPACE font, which is why bugs/0840 moves
    both actors to Courier. In the Arial they used before, "MMMM" and "iiii" are 0.919 and
    0.227 of the font size per character, so padded columns would be ragged by design.
    """
    rows = [split_label(line) for line in list(lines or [])]
    label_w = max((len(indent) + len(label) for indent, label, _d in rows if label), default=0)
    if label_w <= 0:
        return wrap_banner_lines(lines, width=width)
    detail_w = max(int(width) - label_w - int(gap), BANNER_MIN_WRAP_CHARS)
    out: list[str] = []
    for indent, label, detail in rows:
        if not label:
            out.extend(wrap_banner_lines([indent + detail], width=int(width)))
            continue
        head = (indent + label).ljust(label_w) + " " * int(gap)
        pieces = wrap_banner_lines([detail], width=detail_w) or [""]
        out.append(head + pieces[0])
        for piece in pieces[1:]:
            out.append(" " * (label_w + int(gap)) + piece.lstrip())
    return out


def format_depth_of_field_lines(f_number, magnification, pixel_size_um) -> list[str]:
    """bugs/0840: OBJECT-SIDE depth of field at the one-pixel blur criterion.

        DOF = 2 N c (1 + |m|) / m^2        c = one pixel, N = the lens f-number

    The user chose object side explicitly, and it is the one their work asks about: how much
    DEVICE DEPTH stays inside a pixel of blur. The banner already reports an image-side
    residual ("the image forms 0.1155 mm in front of the sensor"), so this row names its side,
    its criterion and every input -- two depths on one screen with no labels is the bugs/0828
    failure waiting to happen.

    Returns [] unless all three inputs are usable; a depth of field computed from a guessed
    f-number would be worse than none.
    """
    try:
        n = float(f_number)
        m = abs(float(magnification))
        c_mm = float(pixel_size_um) / 1000.0
    except (TypeError, ValueError):
        return []
    if not (n > 0.0) or not (m > 1.0e-9) or not (c_mm > 0.0):
        return []
    dof = 2.0 * n * c_mm * (1.0 + m) / (m * m)
    if not (dof > 0.0) or dof != dof:
        return []
    return [
        f"DOF (1 px): {dof:.4g} mm object side "
        f"(N {n:.4g}, |m| {m:.4g}, c {c_mm * 1000.0:.4g} um)"
    ]


def wrap_banner_lines(lines, *, width: int = BANNER_REASON_WIDTH) -> list[str]:
    """bugs/0837: wrap EVERY banner line, not just the refusal's reason.

    bugs/0835 wrapped ``reason`` and stopped there. It fixed one line when the defect was in
    the formatter: the focus summary's own lines never passed through it, and on
    flag_20260920_203630 the STRAY LIGHT line ran to **223 characters** -- twice the budget --
    rendered about 1500 px wide, and was cut off by the WINDOW EDGE at "...left out of the
    focus measu", losing "and drawn faint in the 3D scene". Same loss as 0835, a different
    mechanism: no character cap was involved, the text simply ran past the viewport.

    Applied at the single point where the banner's text is assembled, so every producer is
    covered -- the refusal block, the focus summary, the placement-move lines, and whatever is
    added next. An already-short line is returned untouched.
    """
    out: list[str] = []
    for line in list(lines or []):
        text = str(line or "")
        if not text.strip():
            out.append(text)
            continue
        if len(text) <= int(width):
            out.append(text)
            continue
        out.extend(wrap_banner_reason(text, width=width))
    return out


#: bugs/0840: a vtkTextActor's advance width per character, as a fraction of its font size.
#: Both actors are COURIER now, and this is measured -- not estimated -- by rendering off
#: screen and asking VTK afterwards:
#:
#:     Courier @ 13   32 chars -> 256 px    110 -> 879 px    223 -> 1783 px
#:                    "MMMM..." -> 0.615    "iiii..." -> 0.612
#:
#: 8.000 px per character, 0.615 of the font size, for every sample including all-M and
#: all-i. bugs/0838 had to approximate because the actors were Arial, where the same probe
#: gives 0.919 for "MMMM" and 0.227 for "iiii" -- a per-character width that does not exist.
#: Monospace is what makes a TABLE possible and the width exact at the same time.
BANNER_CHAR_WIDTH_RATIO = 0.615
#: The frame and background a text actor paints around its text.
BANNER_FRAME_PAD_PX = 12.0


def text_actor_width_px(text, font_size_px: float = 13.0) -> float:
    """bugs/0838: how wide a text actor will render, computed from its TEXT.

    VTK's ``GetSize`` is the obvious way to ask and it is not trustworthy here: the banner's
    placement used it and produced a position that disagreed with the HUD on screen by 4x
    (285 px drawn, ~1055 px reported), because ``_update_system_info_hud`` sets the text
    without rendering and ``GetSize`` can report the last RENDERED extent. bugs/0837 then used
    that number to decide whether the banner FITS, so one bad reading sent the banner to the
    stacked fallback, on top of the scene -- a worse outcome than the overflow it was added to
    prevent.

    Deriving from the text is deterministic, needs no renderer, and is testable. It is an
    ESTIMATE and says so; a few percent of error moves the banner a few pixels, which is the
    right failure mode for a layout offset. A wrong ``GetSize`` moved it 800.
    """
    lines = str(text or "").splitlines() or [""]
    longest = max((len(line) for line in lines), default=0)
    return longest * float(font_size_px) * BANNER_CHAR_WIDTH_RATIO + BANNER_FRAME_PAD_PX


#: Never wrap narrower than this, however cramped the window: below it the banner stops being
#: readable prose and becomes a column.
BANNER_MIN_WRAP_CHARS = 48


def banner_wrap_chars(
    hud_width_px, view_width_px, font_size_px: float = 13.0, *, reserved_right_px: float = 0.0
) -> int:
    """bugs/0839: how many characters fit on ONE banner line, given the room beside the HUD.

    The user's words: *"the banner should make use of the horizontal space more, vertical comes
    later if run out of horizontal space."* bugs/0835 and bugs/0837 wrapped to a FIXED 110
    characters, which on a 2478 px window drew the banner about 725 px wide and left ~1400 px
    of empty space to its right while stacking text vertically. A constant cannot know the
    window.

    So the budget is the room that is actually there: the viewport, less where the banner
    starts beside the HUD, less a margin, divided by the per-character advance. On the flagged
    2478 px window beside a 241 px HUD that is ~300 characters, so the 223-character STRAY
    LIGHT line stops wrapping at all -- one line, ending around x=1884 of 2478.

    Floored at :data:`BANNER_MIN_WRAP_CHARS` so a narrow window degrades to a readable column
    rather than to slivers.
    """
    try:
        view_w = float(view_width_px)
        hud_w = float(hud_width_px)
    except (TypeError, ValueError):
        return int(BANNER_REASON_WIDTH)
    if not (view_w > 1.0):
        return int(BANNER_REASON_WIDTH)
    x_norm, _y = solve_banner_anchor(hud_w, 0.0, view_w, reserved_right_px=reserved_right_px)
    try:
        reserved = max(0.0, float(reserved_right_px))
    except (TypeError, ValueError):
        reserved = 0.0
    available_px = view_w - reserved - (x_norm * view_w) - BANNER_FRAME_PAD_PX - 12.0
    per_char = max(float(font_size_px) * BANNER_CHAR_WIDTH_RATIO, 1.0e-6)
    return max(int(BANNER_MIN_WRAP_CHARS), int(available_px / per_char))


def solve_banner_anchor(
    hud_width_px, banner_width_px, view_width_px, *, reserved_right_px: float = 0.0
) -> "tuple[float, float]":
    """bugs/0837: where the solve banner sits, as ``(x, y)`` in normalized viewport.

    Beside the system HUD when the WHOLE banner fits there; stacked underneath when it does
    not. The pre-0837 rule bounded only the START -- ``if x_norm > 0.72`` -- which says nothing
    about whether the banner's own width clears the right edge. Measured on
    flag_20260920_203630: a start of 0.445 passed that check and the banner still ran off a
    2478 px window.

    Pure arithmetic so it can be checked without a renderer, which is the half that was never
    testable before.
    """
    try:
        view_w = float(view_width_px)
        hud_w = float(hud_width_px)
        banner_w = float(banner_width_px or 0.0)
    except (TypeError, ValueError):
        return 0.012, 0.83
    if not (view_w > 1.0) or not (hud_w > 0.0):
        return 0.012, 0.83
    gap_px = 18.0
    margin_px = 12.0
    # bugs/0841: the viewport is not all usable. The navigation cube owns a square in the TOP
    # RIGHT -- 278 px of a 2478 px window -- in the same vertical band the banner occupies, so
    # a fit test against the full width let the banner run underneath it. Measured on the
    # flagged capture: the banner ended at 2406 with the cube starting at 2200, a 206 px
    # overlap. The right edge the banner may reach is the window LESS that square.
    try:
        reserved = max(0.0, float(reserved_right_px))
    except (TypeError, ValueError):
        reserved = 0.0
    usable_w = max(view_w - reserved, 1.0)
    x_norm = 0.012 + (hud_w + gap_px) / view_w
    fits = banner_w <= 0.0 or (x_norm * view_w + banner_w + margin_px) <= usable_w
    if x_norm > 0.72 or not fits:
        return 0.012, 0.83
    return x_norm, 0.985


def format_solve_refusal_lines(info) -> list[str]:
    """bugs/0717 (user directive: "The UI shouldn't silently fail and display as
    though it is working"): the in-scene SOLVE-REFUSED banner. Pure formatter --
    display-free and guardable. ``info`` is the dict the FOV solve stashes on
    refusal; returns [] when there is nothing to show."""
    if not isinstance(info, dict) or not info:
        return []
    outcome = solve_banner_outcome(info)
    if outcome == "forced_crash":
        # applied AND overlapping -- this is the collision the user asked to see
        lines: list[str] = ["FORCED SOLVE APPLIED -- the lens PENETRATES hardware (inspect the 3D overlap)"]
    elif outcome == "forced_fits":
        # applied and it FITS: never call this a refusal, and never send the user
        # looking for an overlap that is not there (bugs/0726)
        lines = ["FORCED SOLVE APPLIED -- the lens FITS: nothing collides"]
    else:
        lines = ["SOLVE REFUSED -- the drawn scene does NOT deliver this request"]
    req = info.get("requested_fov_wh")
    target_m = info.get("target_m")
    if req and len(req) >= 2:
        head = f"requested FOV {float(req[0]):g} x {float(req[1]):g} mm"
        if target_m:
            head += f"  (needs |m| {float(target_m):.3f})"
        lines.append(head)
    need = info.get("lens_move_needed_mm")
    room = info.get("leg_room_mm")
    if need is not None:
        move = f"lens must move {float(need):+.4g} mm along its leg"
        if room is not None:
            # bugs/0719 (judge must-fix): ``need`` is SIGNED (negative = toward the object),
            # so the shortfall is |need| - room -- the signed form printed "short by -333.5"
            # on the om05a refusal while the solve text said 13.8 mm.
            shortfall = abs(float(need)) - float(room)
            # bugs/0740: an AABB clearance that lands on zero prints as "1.203e-11 mm", which
            # reads like a measurement rather than "there is none". Below a micron it IS none.
            room_mm = 0.0 if abs(float(room)) < 1.0e-3 else float(room)
            room_text = "no room at all" if room_mm == 0.0 else f"room available {room_mm:.4g} mm"
            if shortfall > 0.0:
                move += f"; {room_text} (short by {shortfall:.4g} mm)"
            else:
                move += f"; {room_text}"
        lines.append(move)
    delivered_m = info.get("delivered_m")
    delivered_fov = info.get("delivered_fov_wh")
    if delivered_m or delivered_fov:
        now = "delivered now:"
        if delivered_m:
            now += f" |m| {float(delivered_m):.3f}"
        if delivered_fov and len(delivered_fov) >= 2:
            now += f"  FOV {float(delivered_fov[0]):.4g} x {float(delivered_fov[1]):.4g} mm"
        lines.append(now)
    reason = str(info.get("reason", "") or "").strip()
    if reason:
        lines.extend(wrap_banner_reason(reason))
    penetration = info.get("forced_penetration_mm")
    obstacle = str(info.get("forced_obstacle", "") or "")
    forced_moved = info.get("forced_moved_mm")
    # bugs/0719 (judge 3d): key the FORCED block on the move having been APPLIED, not on a
    # penetration number existing -- a forced move that finds no obstacle body along its leg
    # (room None) must still read as FORCED, never fall through to the Force hint below.
    if penetration is not None or forced_moved is not None:
        # bugs/0719 (judge): the PHYSICAL room the gate measured is stashed as
        # forced_room_mm -- render it, so the banner carries the number the limit came from.
        forced_room = info.get("forced_room_mm")
        room_text = ""
        if forced_room is not None:
            try:
                room_text = f" ({float(forced_room):.4g} mm of physical room)"
            except (TypeError, ValueError):
                room_text = ""
        if penetration is None:
            station = info.get("forced_station_room_mm")
            station_text = ""
            if station is not None:
                try:
                    station_text = f" (leg gap {float(station):.4g} mm)"
                except (TypeError, ValueError):
                    station_text = ""
            if str(info.get("forced_room_method", "") or "") == "unmeasured" and obstacle:
                # a solid IS there but the lens body could not be measured (no STEP mesh on a
                # frozen leg) -- say that; never "no obstacle body found"
                lines.append(
                    f"FORCED: applied; moved {float(forced_moved):.4g} mm -- room to {obstacle} "
                    f"NOT measurable (no lens body mesh){station_text}"
                )
            else:
                lines.append(
                    f"FORCED: applied; moved {float(forced_moved):.4g} mm -- no obstacle body found "
                    f"along the leg{station_text}"
                )
        elif float(penetration) < 0.0:
            lines.append(
                f"FORCED: lens PENETRATES {obstacle or 'the next component'} by "
                f"{-float(penetration):.4g} mm{room_text} -- the working-condition limit"
            )
        else:
            lines.append(
                f"FORCED: applied; {float(penetration):.4g} mm clearance to "
                f"{obstacle or 'the next component'} body{room_text}"
            )
        # bugs/0719: the forced move is capped at the fold mirror's station so no leg gap
        # ever goes negative -- say so, with both numbers.
        capped = info.get("forced_capped_mm")
        if capped is not None:
            drawn = info.get("forced_drawn_mm", info.get("forced_moved_mm"))
            drawn_text = f", drawn {float(drawn):.4g} mm" if drawn is not None else ""
            lines.append(
                f"FORCED: move capped at the fold mirror station (requested "
                f"{float(capped):.4g} mm{drawn_text})"
            )
    else:
        lines.append('right-click the Device -> "Force FOV (show collision)" to SEE the limit')
    return lines
