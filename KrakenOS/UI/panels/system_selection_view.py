"""The Tk view of the System Selection Calculator (bugs/0980).

The calculator's live form -- seven inputs and a result that recomputes as you type -- and the
window that holds it for the Tk app's menu. The form is also embedded, compact, in the 3D view's
left panel (`panels/open3d_live_controls.py`). Both lived at the bottom of
`services/system_selection.py`, the calculator's first-order core, which is why that module reached
for tkinter.

Another shell shows the calculator as a row form instead (`row_forms/system_selection.py`); the
model's command `open_system_selection_calculator` picks.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from KrakenOS.UI.services.system_selection import (
    gather_system_selection_prefill,
    system_selection_text,
)


def build_system_selection_form(parent, editor, *, compact: bool = False, prefill: bool = True):
    """Build the calculator's inputs + live output into ``parent`` (a dialog or a panel
    section). Returns a controller with ``.recompute()``, ``.out_var``, ``.next_row`` and
    ``.set_prefill()`` (re-pull FOV/sensor/pixels from the current scene/camera).

    ``compact`` uses short labels + narrow entries for the 3D left panel; the wide dialog
    uses full labels. The bugs/0631 first-order core is shared."""

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
        # bugs/0930: parsed and composed in ONE place, shared with the Qt form
        out_var.set(system_selection_text({
            "fov_w": fov_w_var.get(), "fov_h": fov_h_var.get(), "resolution": res_var.get(),
            "wd_min": wd_var.get(), "sensor_w": sw_var.get(), "sensor_h": sh_var.get(),
            "wavelength": wl_var.get(),
        }, state.get("pixels")))

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
