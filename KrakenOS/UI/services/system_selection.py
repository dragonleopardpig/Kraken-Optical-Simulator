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


def nyquist_frequency_lp_per_mm(pixel_pitch_um: float) -> float:
    """Sensor Nyquist spatial frequency = 1 / (2·pitch), in line-pairs/mm.

    The lens must hold useful MTF contrast here to resolve at the pixel level."""
    p = float(pixel_pitch_um)
    if not (p > 0):
        raise ValueError("pixel_pitch_um must be positive")
    return 500.0 / p  # 1/(2·p_mm) with p_mm = p/1000


def diffraction_limited_working_fnumber(pixel_pitch_um: float, wavelength_um: float) -> float:
    """The slowest (largest) WORKING f/# whose diffraction Airy disk (2.44·λ·N) still
    spans ~2 pixels -- the Nyquist match. A slower lens blurs past a pixel by diffraction
    alone; a faster one usually pays in aberrations. Returns the WORKING (image-space) f/#."""
    p = float(pixel_pitch_um)
    lam = float(wavelength_um)
    if not (p > 0 and lam > 0):
        raise ValueError("pixel_pitch_um and wavelength_um must be positive")
    return 2.0 * p / (2.44 * lam)  # == p / (1.22·λ)


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
    nyquist_lp_per_mm: float | None = None
    diffraction_working_fnumber_max: float | None = None
    diffraction_nominal_fnumber_max: float | None = None
    target_spot_diameter_um: float | None = None
    wavelength_um: float | None = None
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
    wavelength_um: float = 0.55,
) -> SystemSelection:
    """Size a camera + lens from the requirements.

    ``fov_wh_mm``/``sensor_wh_mm`` are ``(width, height)`` in mm. ``sensor_wh_mm`` is the
    candidate sensor size (from the registered camera, or a user entry): it fixes the
    magnification and therefore the lens. Without it only the pixel count -- the pure
    sampling requirement -- is returned. ``wd_min_mm`` gates the lens focal length.
    ``wavelength_um`` drives the lens PERFORMANCE targets (Nyquist / diffraction f/# /
    target spot) -- what the lens must resolve to feed the pixel, not just fit the field.
    """
    fov_w, fov_h = float(fov_wh_mm[0]), float(fov_wh_mm[1])
    notes: list[str] = []
    n_w = required_pixel_count(fov_w, resolution_um_per_px)
    n_h = required_pixel_count(fov_h, resolution_um_per_px)

    mag_w = mag_h = None
    min_f = wd = image_circle = pitch = None
    nyquist = fno_work = fno_nom = target_spot = None
    lam = float(wavelength_um) if wavelength_um and float(wavelength_um) > 0 else None
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
            m = 0.5 * (mag_w + mag_h)
            if wd_min_mm is not None and float(wd_min_mm) > 0:
                min_f = min_focal_length_for_working_distance(float(wd_min_mm), m)
                wd = working_distance_for_focal_length(min_f, m)
            # Lens PERFORMANCE targets from the required pixel pitch (image-space).
            nyquist = nyquist_frequency_lp_per_mm(pitch)
            # 2x the LINEAR (H/V) pixel pitch: the axis-Nyquist match (2 samples per
            # resolved line pair). This is a frequency criterion referenced to the axis
            # pitch, NOT a 2D circle tiled onto square pixels -- a round spot cannot match
            # the square sampling lattice on the diagonal (the corners of the square
            # passband go unused), so the axis pitch is the reference by convention.
            target_spot = 2.0 * pitch
            if lam is not None:
                fno_work = diffraction_limited_working_fnumber(pitch, lam)
                # A lens is specced by its NOMINAL (infinity) f/#: working = (1+|m|)·nominal.
                fno_nom = fno_work / (1.0 + m)
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
        nyquist_lp_per_mm=nyquist,
        diffraction_working_fnumber_max=fno_work,
        diffraction_nominal_fnumber_max=fno_nom,
        target_spot_diameter_um=target_spot,
        wavelength_um=lam,
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


def build_system_selection_form(parent, editor, *, compact: bool = False, prefill: bool = True):
    """Build the calculator's inputs + live output into ``parent`` (a dialog or a panel
    section). Returns a controller with ``.recompute()``, ``.out_var``, ``.next_row`` and
    ``.set_prefill()`` (re-pull FOV/sensor/pixels from the current scene/camera).

    ``compact`` uses short labels + narrow entries for the 3D left panel; the wide dialog
    uses full labels. The bugs/0631 first-order core is shared."""
    import tkinter as tk
    from tkinter import ttk
    from types import SimpleNamespace

    wrap = 250 if compact else 380
    ew = 9 if compact else 14
    pad = (0, 4) if compact else (12, 4)

    fov = sensor = pixels = None
    if prefill:
        fov, sensor, pixels = gather_system_selection_prefill(editor)
    state = {"pixels": pixels}

    def _pf(value):
        return f"{float(value):.6g}" if value else ""

    fov_w_var = tk.StringVar(value=_pf(fov[0] if fov else None))
    fov_h_var = tk.StringVar(value=_pf(fov[1] if fov else None))
    res_var = tk.StringVar(value="")
    wd_var = tk.StringVar(value="")
    sw_var = tk.StringVar(value=_pf(sensor[0] if sensor else None))
    sh_var = tk.StringVar(value=_pf(sensor[1] if sensor else None))
    wl_var = tk.StringVar(value="0.55")  # bugs/0633: λ drives the lens performance targets
    out_var = tk.StringVar(value="")

    def _reflowing_label(text=None, **kw):
        """bugs/0636: a wrapped label that RE-WRAPS to its live width on resize (Tk keeps a
        fixed wraplength otherwise, so the text never reflows when the window widens)."""
        lbl = ttk.Label(parent, text=text, justify="left", wraplength=wrap, **kw)
        margin = 4 if compact else 24

        def _on_configure(event):
            lbl.configure(wraplength=max(int(event.width) - margin, 80))

        lbl.bind("<Configure>", _on_configure)
        return lbl

    parent.columnconfigure(1, weight=1)
    row = 0
    if not compact:
        _reflowing_label(
            "Enter the requirement — FOV, object-space resolution, and the minimum "
            "working distance — to size the matching camera and lens.",
        ).grid(row=row, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="ew")
        row += 1

    field_rows = [
        (("FOV W (mm):" if compact else "FOV width (mm):"), fov_w_var),
        (("FOV H (mm):" if compact else "FOV height (mm):"), fov_h_var),
        (("Res (µm/px):" if compact else "Resolution (µm/px):"), res_var),
        (("Min WD (mm):" if compact else "Minimum working distance (mm):"), wd_var),
        (("Sensor W (mm):" if compact else "Sensor width (mm):"), sw_var),
        (("Sensor H (mm):" if compact else "Sensor height (mm):"), sh_var),
        (("λ (µm):" if compact else "Wavelength (µm):"), wl_var),
    ]
    for label, var in field_rows:
        ttk.Label(parent, text=label).grid(row=row, column=0, padx=pad, pady=2, sticky="e" if not compact else "w")
        ttk.Entry(parent, textvariable=var, width=ew).grid(
            row=row, column=1, padx=(0, 12 if not compact else 0), pady=2, sticky="ew"
        )
        row += 1
    _reflowing_label(
        ("Sensor size is the candidate camera's — leave blank for the pixel count only."
         if compact else
         "Sensor size is the candidate camera's — it sets the magnification and lens. "
         "Leave it blank for the pixel-count requirement only."),
        foreground="#888888",
    ).grid(row=row, column=0, columnspan=2, padx=(0 if compact else 12, 0), pady=(2, 6), sticky="ew")
    row += 1
    ttk.Separator(parent, orient="horizontal").grid(
        row=row, column=0, columnspan=2, sticky="ew", padx=(0 if compact else 12, 0), pady=4
    )
    row += 1
    _reflowing_label(textvariable=out_var).grid(
        row=row, column=0, columnspan=2, padx=(0 if compact else 12, 0), pady=(4, 6), sticky="ew"
    )
    row += 1

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
        res, wd = _num(res_var), _num(wd_var)
        sw, sh = _num(sw_var), _num(sh_var)
        wl = _num(wl_var)
        if "error" in (fov_w, fov_h, res, wd, sw, sh, wl):
            out_var.set("Enter positive numbers (optional boxes may be blank).")
            return
        if fov_w is None or fov_h is None or res is None:
            out_var.set("Enter FOV width, height and resolution.")
            return
        sensor_wh = (sw, sh) if (sw and sh) else None
        try:
            result = compute_system_selection(
                (fov_w, fov_h), res, wd_min_mm=wd, sensor_wh_mm=sensor_wh,
                wavelength_um=(wl if wl else 0.55),
            )
        except Exception as exc:  # noqa: BLE001
            out_var.set(f"Cannot compute: {exc}")
            return
        lines = format_system_selection_lines(result)
        cam = state.get("pixels")
        if cam is not None:
            meets = cam[0] >= result.required_pixels_w and cam[1] >= result.required_pixels_h
            lines.append(
                f"Current camera {cam[0]}×{cam[1]} px: "
                + ("meets the pixel requirement." if meets else "UNDER the pixel requirement.")
            )
        lines.extend(result.notes)
        out_var.set("\n".join(lines))

    def set_prefill():
        f, s, p = gather_system_selection_prefill(editor)
        state["pixels"] = p
        if f:
            fov_w_var.set(_pf(f[0]))
            fov_h_var.set(_pf(f[1]))
        if s:
            sw_var.set(_pf(s[0]))
            sh_var.set(_pf(s[1]))
        recompute()

    for var in (fov_w_var, fov_h_var, res_var, wd_var, sw_var, sh_var, wl_var):
        var.trace_add("write", recompute)
    recompute()

    return SimpleNamespace(recompute=recompute, out_var=out_var, next_row=row, set_prefill=set_prefill)


def open_system_selection_dialog(editor):
    """Modeless System Selection Calculator dialog. Prefilled from the current scene/camera;
    resizable and self-fitting so the (growing) result text is never clipped (bugs/0632)."""
    import tkinter as tk
    from tkinter import ttk

    parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
    dialog = tk.Toplevel(parent)
    dialog.title("System Selection Calculator")
    try:
        dialog.transient(parent)
        dialog.resizable(True, True)  # bugs/0632: let the user enlarge; also self-fits below
    except Exception:
        pass

    form = build_system_selection_form(dialog, editor, compact=False)
    ttk.Button(dialog, text="Close", command=dialog.destroy).grid(
        row=form.next_row, column=0, columnspan=2, pady=(0, 12)
    )

    def _fit_to_content(*_a):
        # bugs/0632: the result text grows as inputs change (extra notes, the camera-check
        # line); grow the window to fit so nothing clips. Never shrinks below the user's size.
        if not dialog.winfo_exists():
            return
        dialog.update_idletasks()
        need_h = dialog.winfo_reqheight()
        need_w = max(dialog.winfo_reqwidth(), dialog.winfo_width())
        if dialog.winfo_height() < need_h:
            dialog.geometry(f"{need_w}x{need_h}")

    form.out_var.trace_add("write", lambda *_a: dialog.after_idle(_fit_to_content))
    try:
        editor._show_centered_dialog(dialog)
    except Exception:
        pass
    dialog.after(120, _fit_to_content)
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
        lines.append(
            f"Required pixel pitch (at this sensor): {_fmt(result.required_pixel_pitch_um, 3)} µm"
        )
    if result.nyquist_lp_per_mm is not None:
        lines.append(f"Sensor Nyquist: {_fmt(result.nyquist_lp_per_mm, 3)} lp/mm (target MTF here)")
    if result.diffraction_working_fnumber_max is not None:
        line = f"Max working f/# (diffraction ≈2 px): f/{_fmt(result.diffraction_working_fnumber_max, 3)}"
        if result.diffraction_nominal_fnumber_max is not None:
            line += f"  (nominal f/{_fmt(result.diffraction_nominal_fnumber_max, 3)})"
        lines.append(line)
    if result.target_spot_diameter_um is not None:
        lines.append(
            f"Target spot ≈ {_fmt(result.target_spot_diameter_um, 3)} µm (2× axis pixel pitch, per H/V)"
        )
    return lines
