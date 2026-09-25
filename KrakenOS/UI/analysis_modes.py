"""The analysis plots a user can tick, toolkit-free (docs/design_qt_migration.md phase 6).

The 24 plots, their grouping in the picker and their tooltips were literals inside the Tk
toolbar's `build()`, so the Qt shell had no way to offer them (bugs/0899). They are data.

These CAPTIONS are deliberately not `layout_plot_controller.ANALYSIS_MODE_LABELS`: that table
holds the long names the status line and the plot titles use ("Wavefront", "Polarization"),
while a toolbar button has room for "WFront" and "Pol". Both are right for their job, so both
stay -- `mode_label` reaches the long one when prose is what is wanted.
"""
from __future__ import annotations

from KrakenOS.UI.layout_plot_controller import analysis_mode_label

#: the picker's groups, in order: (caption, mode) exactly as the Tk toolbar declared them
MODE_GROUPS = (
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

#: mode -> what the picker says about it
MODE_TOOLTIPS = {
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

#: every mode a user can tick, in picker order
MODES = tuple(mode for group in MODE_GROUPS for _caption, mode in group)

PICKER_HINT = ("Tick one or more analysis plots to display alongside the 2D layout. "
               "Stays open for multi-select; Esc / click away / Close to dismiss.")


def mode_caption(mode: str) -> str:
    """The toolbar button's short caption."""
    for group in MODE_GROUPS:
        for caption, key in group:
            if key == mode:
                return caption
    return mode_label(mode)


def mode_label(mode: str) -> str:
    """The long name, for prose -- the status line, a plot title."""
    return analysis_mode_label(mode)


def selection_label(count: int) -> str:
    """What the picker's own button reads: the model decides, both shells show it."""
    return "Select plots \u25be" if not count else f"Plots: {int(count)} \u25be"
