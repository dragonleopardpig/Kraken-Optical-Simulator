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
                ("FC/Dist", "field_curvature"),
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
            "field_curvature": "Field Curvature / Distortion",
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
        ttk.Label(parent, text="Analysis").pack(side="left", padx=(0, 4))
        menubutton = ttk.Menubutton(parent, text="Select plots ▾", style="Toolbutton")
        menu = tk.Menu(menubutton, tearoff=False)
        menubutton.configure(menu=menu)
        for group_index, group in enumerate(mode_button_groups):
            if group_index > 0:
                menu.add_separator()
            for text, mode in group:
                var = tk.BooleanVar(value=False)
                self.analysis_mode_vars[mode] = var
                menu.add_checkbutton(
                    label=mode_tooltips.get(mode, text),
                    onvalue=True,
                    offvalue=False,
                    variable=var,
                    command=lambda m=mode: self.toggle_analysis_mode(m),
                )
        menubutton.pack(side="left", padx=(4, 0))
        self.analysis_mode_menubutton = menubutton
        self.analysis_mode_menu = menu
        self._add_widget_tooltip(
            menubutton,
            "Tick one or more analysis plots to display alongside the 2D layout",
        )


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
