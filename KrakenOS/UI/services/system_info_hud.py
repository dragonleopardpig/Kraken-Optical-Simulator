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
    lines = format_system_info_lines(fov, sensor, resolution, pixel_size)
    # bugs/0719: the NON-banner focus-residual readout -- the lens is at the requested WD,
    # the sensor was left where the vendor put it, and the exact conjugate's track mismatch
    # is a number the user needs to see in the scene (not a refusal, so not the red banner).
    try:
        lines = lines + format_focus_residual_lines(
            editor.__dict__.get("_fov_solve_focus_residual_info")
        )
    except Exception:
        pass
    return "\n".join(lines)


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
        lines.append(reason if len(reason) <= 110 else reason[:107] + "...")
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
