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
    return "\n".join(format_system_info_lines(fov, sensor, resolution, pixel_size))


def format_solve_refusal_lines(info) -> list[str]:
    """bugs/0717 (user directive: "The UI shouldn't silently fail and display as
    though it is working"): the in-scene SOLVE-REFUSED banner. Pure formatter --
    display-free and guardable. ``info`` is the dict the FOV solve stashes on
    refusal; returns [] when there is nothing to show."""
    if not isinstance(info, dict) or not info:
        return []
    lines: list[str] = ["SOLVE REFUSED -- the drawn scene does NOT deliver this request"]
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
            move += f"; room available {float(room):.4g} mm (short by {float(need) - float(room):.4g})"
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
    if penetration is not None:
        if float(penetration) < 0.0:
            lines.append(
                f"FORCED: lens PENETRATES {obstacle or 'the next component'} by "
                f"{-float(penetration):.4g} mm -- the working-condition limit"
            )
        else:
            lines.append(
                f"FORCED: applied; {float(penetration):.4g} mm clearance to "
                f"{obstacle or 'the next component'}"
            )
    else:
        lines.append('right-click the Device -> "Force FOV (show collision)" to SEE the limit')
    return lines
