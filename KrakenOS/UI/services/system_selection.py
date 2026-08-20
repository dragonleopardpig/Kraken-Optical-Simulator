"""System-selection sizing calculator (bugs/0631, user feature).

The machine-vision selection problem: given a required FIELD OF VIEW, an object-space
RESOLUTION (um/px), and a MINIMUM WORKING DISTANCE, determine the matching camera and
lens specs. Pure first-order optics -- no scene, no trace -- so it is display-free and
fully guardable; a dialog (open3d_inspector) just renders these numbers.

Governing relations (thin lens, lateral magnification |m|):
  * sampling:        N = FOV_mm * 1000 / r            (min sensor pixels across the FOV)
  * magnification:   m = sensor_mm / FOV_mm           (the HUD's System Magnification)
  * object distance: WD = f * (|m| + 1) / |m|         (front-conjugate working distance)
      -> f for a target WD:  f = WD * |m| / (|m| + 1)
      -> WD rises with f at fixed m, so meeting WD >= WD_min needs f >= that value.
  * image circle:    the lens must cover the sensor diagonal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def required_pixel_count(fov_mm: float, resolution_um_per_px: float) -> int:
    """Minimum sensor pixels across a FOV axis to meet the object-space sampling.

    ``N = FOV / (r / 1000)``, rounded UP -- fewer pixels would under-sample the field."""
    fov = float(fov_mm)
    r = float(resolution_um_per_px)
    if not (fov > 0 and r > 0):
        raise ValueError("fov_mm and resolution_um_per_px must be positive")
    return int(math.ceil(fov * 1000.0 / r))


def system_magnification(sensor_mm: float, fov_mm: float) -> float:
    """Optical lateral magnification |m| = sensor / FOV (the HUD's System Magnification)."""
    sensor = float(sensor_mm)
    fov = float(fov_mm)
    if not (sensor > 0 and fov > 0):
        raise ValueError("sensor_mm and fov_mm must be positive")
    return sensor / fov


def working_distance_for_focal_length(focal_length_mm: float, magnification: float) -> float:
    """Front-conjugate working distance WD = f (|m| + 1) / |m| (thin lens)."""
    f = float(focal_length_mm)
    m = abs(float(magnification))
    if not (f > 0 and m > 1e-12):
        raise ValueError("focal_length_mm and magnification must be positive")
    return f * (m + 1.0) / m


def min_focal_length_for_working_distance(wd_min_mm: float, magnification: float) -> float:
    """The shortest focal length whose working distance still reaches ``wd_min``.

    Inverting ``WD = f(|m|+1)/|m|``: ``f = WD * |m| / (|m| + 1)``. WD rises with f at
    fixed m, so a lens of AT LEAST this EFL clears the minimum working distance."""
    wd = float(wd_min_mm)
    m = abs(float(magnification))
    if not (wd > 0 and m > 1e-12):
        raise ValueError("wd_min_mm and magnification must be positive")
    return wd * m / (m + 1.0)


@dataclass(frozen=True)
class SystemSelection:
    """Computed camera + lens specs for a FOV / resolution / WD requirement."""

    required_pixels_w: int
    required_pixels_h: int
    magnification_w: float | None = None
    magnification_h: float | None = None
    min_focal_length_mm: float | None = None
    working_distance_mm: float | None = None  # the WD at the min EFL (== wd_min by construction)
    image_circle_min_mm: float | None = None
    required_pixel_pitch_um: float | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def magnification(self) -> float | None:
        if self.magnification_w is None or self.magnification_h is None:
            return None
        return 0.5 * (self.magnification_w + self.magnification_h)


def compute_system_selection(
    fov_wh_mm,
    resolution_um_per_px: float,
    wd_min_mm: float | None = None,
    sensor_wh_mm=None,
) -> SystemSelection:
    """Size a camera + lens from the requirements.

    ``fov_wh_mm``/``sensor_wh_mm`` are ``(width, height)`` in mm. ``sensor_wh_mm`` is the
    candidate sensor size (from the registered camera, or a user entry): it fixes the
    magnification and therefore the lens. Without it only the pixel count -- the pure
    sampling requirement -- is returned. ``wd_min_mm`` gates the lens focal length.
    """
    fov_w, fov_h = float(fov_wh_mm[0]), float(fov_wh_mm[1])
    notes: list[str] = []
    n_w = required_pixel_count(fov_w, resolution_um_per_px)
    n_h = required_pixel_count(fov_h, resolution_um_per_px)

    mag_w = mag_h = None
    min_f = wd = image_circle = pitch = None
    if sensor_wh_mm is not None:
        sw, sh = float(sensor_wh_mm[0]), float(sensor_wh_mm[1])
        if sw > 0 and sh > 0:
            mag_w = system_magnification(sw, fov_w)
            mag_h = system_magnification(sh, fov_h)
            image_circle = math.hypot(sw, sh)
            pitch = 1000.0 * sw / n_w  # sensor of this size at the min pixel count
            if abs(mag_w - mag_h) > 0.01 * max(mag_w, mag_h):
                notes.append(
                    f"FOV aspect {fov_w:.4g}:{fov_h:.4g} differs from sensor aspect "
                    f"{sw:.4g}:{sh:.4g} -- magnification differs per axis; match the FOV "
                    "aspect to the sensor for a single value."
                )
            if wd_min_mm is not None and float(wd_min_mm) > 0:
                m = 0.5 * (mag_w + mag_h)
                min_f = min_focal_length_for_working_distance(float(wd_min_mm), m)
                wd = working_distance_for_focal_length(min_f, m)
    elif wd_min_mm is not None and float(wd_min_mm) > 0:
        notes.append("Enter a sensor size to size the lens (magnification + focal length).")

    return SystemSelection(
        required_pixels_w=n_w,
        required_pixels_h=n_h,
        magnification_w=mag_w,
        magnification_h=mag_h,
        min_focal_length_mm=min_f,
        working_distance_mm=wd,
        image_circle_min_mm=image_circle,
        required_pixel_pitch_um=pitch,
        notes=notes,
    )


def gather_system_selection_prefill(editor):
    """Prefill (fov_wh, sensor_wh, camera_pixels) from the editor's current scene/camera.

    Best-effort -- any missing piece just leaves that field blank in the dialog."""
    from types import SimpleNamespace

    fov = sensor = pixels = None
    try:
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService

        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        fov = qe.object_fov_dimensions()
        sensor = qe.sensor_active_dimensions()
    except Exception:
        fov = sensor = None
    try:
        record = editor._current_camera_record()
        if isinstance(record, dict):
            res = record.get("resolution_px")
            pixels = (int(res[0]), int(res[1])) if res else None
    except Exception:
        pixels = None
    return fov, sensor, pixels


def open_system_selection_dialog(editor, *, fov_wh=None, sensor_wh=None, camera_pixels=None):
    """Modeless System Selection Calculator: enter FOV + object-space resolution + minimum
    working distance (+ a candidate sensor size) and read the matching camera + lens specs
    live. Scene-independent; prefilled from the current scene/camera when available."""
    import tkinter as tk
    from tkinter import ttk

    parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
    dialog = tk.Toplevel(parent)
    dialog.title("System Selection Calculator")
    try:
        dialog.transient(parent)
        dialog.resizable(False, False)
    except Exception:
        pass

    def _pf(value):
        return f"{float(value):.6g}" if value else ""

    fov_w_var = tk.StringVar(value=_pf(fov_wh[0] if fov_wh else None))
    fov_h_var = tk.StringVar(value=_pf(fov_wh[1] if fov_wh else None))
    res_var = tk.StringVar(value="")
    wd_var = tk.StringVar(value="")
    sw_var = tk.StringVar(value=_pf(sensor_wh[0] if sensor_wh else None))
    sh_var = tk.StringVar(value=_pf(sensor_wh[1] if sensor_wh else None))
    out_var = tk.StringVar(value="")

    ttk.Label(
        dialog,
        text=("Enter the requirement — FOV, object-space resolution, and the minimum "
              "working distance — to size the matching camera and lens."),
        wraplength=380, justify="left",
    ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

    rows = [
        ("FOV width (mm):", fov_w_var),
        ("FOV height (mm):", fov_h_var),
        ("Resolution (µm/px):", res_var),
        ("Minimum working distance (mm):", wd_var),
        ("Sensor width (mm):", sw_var),
        ("Sensor height (mm):", sh_var),
    ]
    for i, (label, var) in enumerate(rows, start=1):
        ttk.Label(dialog, text=label).grid(row=i, column=0, padx=(12, 4), pady=2, sticky="e")
        ttk.Entry(dialog, textvariable=var, width=14).grid(
            row=i, column=1, padx=(0, 12), pady=2, sticky="ew"
        )
    ttk.Label(
        dialog, text="Sensor size is the candidate camera's — it sets the magnification "
        "and lens. Leave it blank for the pixel-count requirement only.",
        foreground="#888888", wraplength=380, justify="left",
    ).grid(row=len(rows) + 1, column=0, columnspan=2, padx=12, pady=(2, 8), sticky="w")

    ttk.Separator(dialog, orient="horizontal").grid(
        row=len(rows) + 2, column=0, columnspan=2, sticky="ew", padx=12, pady=4
    )
    out_label = ttk.Label(dialog, textvariable=out_var, justify="left", wraplength=380)
    out_label.grid(row=len(rows) + 3, column=0, columnspan=2, padx=12, pady=(4, 12), sticky="w")

    def _num(var):
        raw = (var.get() or "").strip()
        if not raw:
            return None
        try:
            v = float(raw)
        except ValueError:
            return "error"
        return v if v > 0 else "error"

    def recompute(*_a):
        fov_w, fov_h = _num(fov_w_var), _num(fov_h_var)
        res = _num(res_var)
        wd = _num(wd_var)
        sw, sh = _num(sw_var), _num(sh_var)
        if "error" in (fov_w, fov_h, res, wd, sw, sh):
            out_var.set("Enter positive numbers (or leave optional boxes blank).")
            return
        if fov_w is None or fov_h is None or res is None:
            out_var.set("Enter FOV width, height and resolution to size the camera.")
            return
        sensor = (sw, sh) if (sw and sh) else None
        try:
            result = compute_system_selection((fov_w, fov_h), res, wd_min_mm=wd, sensor_wh_mm=sensor)
        except Exception as exc:  # noqa: BLE001
            out_var.set(f"Cannot compute: {exc}")
            return
        lines = format_system_selection_lines(result)
        if camera_pixels is not None:
            meets = camera_pixels[0] >= result.required_pixels_w and camera_pixels[1] >= result.required_pixels_h
            lines.append(
                f"Current camera {camera_pixels[0]}×{camera_pixels[1]} px: "
                + ("meets the pixel requirement." if meets else "UNDER the pixel requirement.")
            )
        lines.extend(result.notes)
        out_var.set("\n".join(lines))

    for var in (fov_w_var, fov_h_var, res_var, wd_var, sw_var, sh_var):
        var.trace_add("write", recompute)
    recompute()

    ttk.Button(dialog, text="Close", command=dialog.destroy).grid(
        row=len(rows) + 4, column=0, columnspan=2, pady=(0, 12)
    )
    try:
        editor._show_centered_dialog(dialog)
    except Exception:
        pass
    # Modeless (like the design popups) so it can sit open beside the scene.
    return dialog


def _fmt(value: float, digits: int = 4) -> str:
    return f"{float(value):.{digits}g}"


def format_system_selection_lines(result: SystemSelection) -> list[str]:
    """Human-readable result rows for the calculator dialog."""
    lines = [f"Camera: ≥ {result.required_pixels_w} × {result.required_pixels_h} px"]
    if result.magnification is not None:
        if result.magnification_w is not None and abs(
            result.magnification_w - (result.magnification_h or 0.0)
        ) <= 0.01 * max(result.magnification_w, result.magnification_h or 1e-9):
            lines.append(f"Magnification: {_fmt(result.magnification, 3)}× (sensor/FOV)")
        else:
            lines.append(
                f"Magnification: {_fmt(result.magnification_w, 3)}× (w) / "
                f"{_fmt(result.magnification_h, 3)}× (h)"
            )
    if result.image_circle_min_mm is not None:
        lines.append(f"Lens image circle: ≥ {_fmt(result.image_circle_min_mm)} mm")
    if result.min_focal_length_mm is not None and result.working_distance_mm is not None:
        lines.append(
            f"Lens EFL: ≥ {_fmt(result.min_focal_length_mm)} mm "
            f"(WD {_fmt(result.working_distance_mm)} mm at that EFL; longer EFL → longer WD)"
        )
    if result.required_pixel_pitch_um is not None:
        lines.append(f"Pixel pitch at this sensor: {_fmt(result.required_pixel_pitch_um, 3)} µm")
    return lines
