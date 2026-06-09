"""Main layout-editor analysis controls and information panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


class _EditorBackedPanel:
    """Delegate widget-owned state back to the layout editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)


class MainAnalysisToolbarPanel(_EditorBackedPanel):
    """Build the 2D plot analysis toolbar."""

    def build(self, parent: tk.Widget) -> None:
        mode_button_groups = (
            (
                ("Spot", "spot"),
                ("RMS", "rms"),
                ("PSF", "psf"),
                ("MTF", "mtf"),
            ),
            (
                ("Pupil", "pupil"),
                ("Seidel", "seidel"),
                ("WFront", "wavefront"),
                ("Zernike", "zernike"),
            ),
            (
                ("FldCurv", "field_curvature"),
                ("Dist", "distortion"),
                ("Illum", "relative_illumination"),
                ("LatClr", "lateral_color"),
                ("Pol", "polarization"),
                ("Atmos", "atmosphere"),
            ),
            (
                ("PSFMap", "psf_map"),
                ("FldMap", "field_map"),
                ("IllMap", "illum_map"),
                ("WfeMap", "wavefront_map"),
                ("DetMap", "detector_map"),
                ("CohDet", "coherent_detector"),
                ("BField", "branch_field"),
                ("Diffr", "diffraction_detector"),
            ),
            (
                ("Interf", "interferogram"),
                ("TolCmp", "tolerance_compare"),
            ),
        )
        mode_tooltips = {
            "spot": "Spot Diagram: traced ray intercepts at the image or selected detector",
            "psf": "Point Spread Function",
            "psf_map": "Point Spread Function Map",
            "rms": "RMS Spot Radius",
            "field_curvature": "Field Curvature (tangential / sagittal best focus)",
            "distortion": "Distortion (percent vs field)",
            "relative_illumination": "Relative Illumination",
            "polarization": "Polarization analysis",
            "lateral_color": "Lateral Color",
            "detector_map": "Detector Power Map",
            "coherent_detector": "Coherent Detector Field Sum",
            "branch_field": "Branch Field Intensity / Phase + TEM00 Overlap",
            "diffraction_detector": "Diffraction Detector Angular Spectrum",
            "field_map": "Field Map",
            "illum_map": "Illumination Map",
            "wavefront_map": "Wavefront Error Map",
            "atmosphere": "Atmospheric Dispersion",
            "pupil": "Pupil Diagnostic",
            "seidel": "Seidel Aberrations",
            "wavefront": "Wavefront Analysis",
            "zernike": "Zernike Polynomial Fit",
            "interferogram": "Interferogram",
            "tolerance_compare": "Tolerance nominal-vs-worst spot overlay",
            "mtf": "Modulation Transfer Function",
        }
        self.analysis_mode_vars = {}
        for group in mode_button_groups:
            for _text, mode in group:
                self.analysis_mode_vars[mode] = tk.BooleanVar(value=False)
        ttk.Label(parent, text="Analysis").pack(side="left", padx=(0, 4))
        # Custom multi-select dropdown instead of a tk.Menu: a tk.Menu unposts on
        # every checkbutton click, but the user wants to tick several plots in one
        # pass, so this panel stays open until they click away / press Esc / Close.
        trigger = ttk.Button(
            parent, text="Select plots ▾", style="Toolbutton",
            command=self._toggle_analysis_dropdown,
        )
        trigger.pack(side="left", padx=(4, 0))
        self.analysis_mode_menubutton = trigger
        self.analysis_mode_menu = None
        self._analysis_dropdown_groups = mode_button_groups
        self._analysis_dropdown_tooltips = mode_tooltips
        self._analysis_dropdown_popup = None
        self._analysis_dropdown_outside_bind = None
        self._add_widget_tooltip(
            trigger,
            "Tick one or more analysis plots to display alongside the 2D layout. "
            "Stays open for multi-select; Esc / click away / Close to dismiss.",
        )

        # Real (z-buffered) 3D wavefront surface, alongside the 2D Zemax waterfall.
        wavefront_3d_button = ttk.Button(
            parent,
            text="WFront 3D",
            style="Toolbutton",
            command=self.open_wavefront_3d_view,
        )
        wavefront_3d_button.pack(side="left", padx=(6, 0))
        self.wavefront_3d_button = wavefront_3d_button
        self._add_widget_tooltip(
            wavefront_3d_button,
            "Open the latest Wavefront analysis as a real, rotatable 3D surface "
            "(PyVista/VTK). Run the Wavefront plot first.",
        )

    # -- Multi-select analysis dropdown (stays open across ticks) -------------

    def _toggle_analysis_dropdown(self) -> None:
        popup = getattr(self, "_analysis_dropdown_popup", None)
        if popup is not None and popup.winfo_exists():
            self._close_analysis_dropdown()
        else:
            self._open_analysis_dropdown()

    def _open_analysis_dropdown(self) -> None:
        trigger = self.analysis_mode_menubutton
        if trigger is None or not trigger.winfo_exists():
            return
        popup = tk.Toplevel(trigger)
        # Build hidden, then map at an explicit geometry: an override-redirect
        # window otherwise maps at the screen origin first (it lands top-left,
        # partly under the desktop bar) before any +x+y request is honoured.
        popup.withdraw()
        popup.wm_overrideredirect(True)
        try:
            popup.attributes("-topmost", True)
        except Exception:
            pass
        # Thin border (override-redirect windows have no frame of their own).
        border = tk.Frame(popup, background="#888c94")
        border.pack(fill="both", expand=True)
        body = ttk.Frame(border, padding=6)
        body.pack(fill="both", expand=True, padx=1, pady=1)
        ttk.Label(
            body, text="Analysis plots — tick multiple",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        for group_index, group in enumerate(self._analysis_dropdown_groups):
            if group_index > 0:
                ttk.Separator(body, orient="horizontal").pack(fill="x", pady=3)
            for text, mode in group:
                ttk.Checkbutton(
                    body,
                    text=self._analysis_dropdown_tooltips.get(mode, text),
                    variable=self.analysis_mode_vars[mode],
                    command=lambda m=mode: self.toggle_analysis_mode(m),
                ).pack(anchor="w", fill="x")
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=3)
        ttk.Button(
            body, text="Close", style="Toolbutton",
            command=self._close_analysis_dropdown,
        ).pack(anchor="e")

        popup.update_idletasks()
        pop_w = max(popup.winfo_reqwidth(), 1)
        pop_h = max(popup.winfo_reqheight(), 1)
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        # Anchor just below the trigger button (absolute screen coords), clamped
        # on-screen in both axes so it never lands under the bar or off an edge.
        x = trigger.winfo_rootx()
        y = trigger.winfo_rooty() + trigger.winfo_height()
        x = max(0, min(int(x), screen_w - pop_w))
        y = max(0, min(int(y), screen_h - pop_h))
        # Full WxH+x+y, then map: deiconify after the geometry is set so it
        # appears at the requested spot rather than the origin.
        popup.wm_geometry(f"{pop_w}x{pop_h}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        popup.update_idletasks()
        try:
            popup.focus_set()
        except Exception:
            pass
        popup.bind("<Escape>", lambda _e: self._close_analysis_dropdown())
        toplevel = trigger.winfo_toplevel()
        self._analysis_dropdown_outside_bind = toplevel.bind(
            "<Button-1>", self._analysis_dropdown_outside_click, add="+"
        )
        self._analysis_dropdown_popup = popup

    def _analysis_dropdown_outside_click(self, event) -> None:
        popup = getattr(self, "_analysis_dropdown_popup", None)
        if popup is None or not popup.winfo_exists():
            return
        px, py = event.x_root, event.y_root

        def _inside(widget) -> bool:
            try:
                wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
                return (
                    wx <= px <= wx + widget.winfo_width()
                    and wy <= py <= wy + widget.winfo_height()
                )
            except Exception:
                return False

        if not _inside(popup) and not _inside(self.analysis_mode_menubutton):
            self._close_analysis_dropdown()

    def _close_analysis_dropdown(self) -> None:
        popup = getattr(self, "_analysis_dropdown_popup", None)
        self._analysis_dropdown_popup = None
        bind_id = getattr(self, "_analysis_dropdown_outside_bind", None)
        if bind_id:
            try:
                self.analysis_mode_menubutton.winfo_toplevel().unbind("<Button-1>", bind_id)
            except Exception:
                pass
            self._analysis_dropdown_outside_bind = None
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass


class MainInformationPanel(_EditorBackedPanel):
    """Build the right-side information table."""

    def build(self, parent: tk.Widget) -> None:
        self.results_table = ttk.Treeview(parent, columns=("property", "value"), show="headings", selectmode="none")
        self.results_table.heading("property", text="Property")
        self.results_table.heading("value", text="Value")
        self.results_table.column("property", width=96, anchor="w", stretch=False)
        self.results_table.column("value", width=40, anchor="w", stretch=True)
        self.results_table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.results_table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.results_table.configure(yscrollcommand=scroll.set)
