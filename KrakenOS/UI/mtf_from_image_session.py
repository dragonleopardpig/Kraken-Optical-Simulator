"""Measure MTF from a captured image, as a model (docs/design_qt_migration.md phase 5g, bugs/0938).

Two target types, one box at a time drawn on the image:

* **Slanted edge** (ISO 12233, :mod:`KrakenOS.EdgeMTF`) -- ONE box over a dark/bright edge gives a
  WHOLE MTF curve. The default: most captured "MTF targets" are edges.
* **USAF three-bar** (:mod:`KrakenOS.USAFMTF`) -- a box over EACH three-bar element (group / element
  / bar orientation set first); every element contributes ONE point.

The Tk dialog kept all of this in one closure. It is here now, toolkit-neutral: the image, the mode,
the next-ROI fields, the calibration, the ROIs in ORIGINAL image pixels (a view divides its display
coordinates by its scale, so the fit always runs on the full-resolution capture), the result and the
two message lines. `panels/mtf_from_image_dialog.py` (Tk) and `qt/dialogs/mtf_from_image_dialog.py`
(Qt) only draw it and forward the mouse.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np

TITLE = "Measure MTF from Image"
ORIENTATIONS = ("vertical", "horizontal")
#: the image is shown scaled to fit this box
MAX_DISPLAY = (660, 560)
#: a box smaller than this many DISPLAY pixels is taken as a stray click
MIN_BOX_DISPLAY_PX = 8
IMAGE_FILETYPES = [("Images", "*.png *.tif *.tiff *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
INSTRUCTIONS = {
    "edge": ("Slanted edge: drag ONE box over a dark/bright edge, then Compute → full MTF curve (cycles/pixel; "
             "set pixel pitch for lp/mm)."),
    "usaf": ("USAF three-bar: set Group/Element/Bars, drag a box over EACH three-bar element (one point per "
             "element), then Compute."),
}
#: the frequency axes each mode offers; the first is the default
FREQUENCY_SPACES = {"edge": ("pixel", "image"), "usaf": ("object", "image")}
ROI_COLUMNS = (("g", "Grp", 40), ("e", "El", 34), ("orient", "Bars", 74), ("roi", "ROI (px)", 150),
               ("mtf", "MTF", 60), ("r2", "R²", 56))
CALIBRATION_FIELDS = (("magnification", "Magnification |m| (USAF image-space)"),
                      ("target_contrast", "Target contrast (USAF, 0-1]"),
                      ("pixel_pitch", "Pixel pitch [µm] (for lp/mm)"))
ENLARGE_HINT = "Click the plot to enlarge (opens in the image viewer)."


def style_mtf_axes(ax) -> None:
    """Pin both axes to a common 0.0 origin (no matplotlib margin) and put the Y ticks at
    0.0, 0.2, ..., 1.0 (user request, bugs/0411)."""
    ax.set_xlim(left=0.0)
    ax.set_ylim(0.0, 1.05)
    ax.set_yticks(np.arange(0.0, 1.001, 0.2))
    ax.margins(x=0.0)


def _opt_float(text) -> float | None:
    text = str(text).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


class MtfFromImageSession:
    """One "Measure MTF from Image" session. Views write their fields into ``fields`` /
    ``calibration`` (text, as typed) and redraw on ``notify``."""

    def __init__(self, editor: Any = None) -> None:
        self.editor = editor
        self.listeners: list[Callable[[], None]] = []
        self.path: Path | None = None
        self.gray = None
        self.image_size: tuple[int, int] | None = None
        self.mode = "edge"
        self.fields = {"group": "2", "element": "1", "orientation": "vertical", "cycles": "3"}
        self.calibration = {"magnification": "", "target_contrast": "1.0", "pixel_pitch": "", "space": "pixel"}
        self.rois: list[dict] = []
        self.result = None
        self.status = "Import a captured image to begin."
        self.instruction = INSTRUCTIONS["edge"]

    def notify(self) -> None:
        for listener in list(self.listeners):
            listener()

    # ---- mode + image -----------------------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        """Edge or USAF: switches the instruction and the frequency axes, and drops the ROIs (a USAF
        element box means nothing to the edge fit, and the reverse)."""
        self.mode = "usaf" if mode == "usaf" else "edge"
        self.calibration["space"] = FREQUENCY_SPACES[self.mode][0]
        self.instruction = INSTRUCTIONS[self.mode]
        self.clear_rois(notify=False)
        self.notify()

    def frequency_spaces(self) -> tuple:
        return FREQUENCY_SPACES[self.mode]

    def load_image(self, path) -> bool:
        from PIL import Image

        from KrakenOS.USAFMTF import load_grayscale_image

        try:
            gray = load_grayscale_image(str(path))
            with Image.open(str(path)) as image:
                size = image.size
        except Exception as exc:
            self.status = f"Could not load image: {exc}"
            self.notify()
            return False
        self.path, self.gray, self.image_size = Path(path), gray, (int(size[0]), int(size[1]))
        self.clear_rois(notify=False)
        scale = self.display_scale()
        self.status = (f"Loaded {self.path.name} ({size[0]}×{size[1]}px @ {scale:.2f}×). "
                       + ("Drag one box over the edge." if self.mode == "edge" else "Drag a box over each element."))
        self.notify()
        return True

    def display_rgb(self):
        """The image as the views show it: RGB, scaled to fit `MAX_DISPLAY` (never enlarged)."""
        from PIL import Image

        with Image.open(str(self.path)) as image:
            rgb = image.convert("RGB")
        w, h = rgb.size
        scale = self.display_scale()
        return rgb.resize((max(1, int(w * scale)), max(1, int(h * scale))))

    def display_scale(self) -> float:
        if self.image_size is None:
            return 1.0
        w, h = self.image_size
        return min(MAX_DISPLAY[0] / w, MAX_DISPLAY[1] / h, 1.0)

    # ---- ROIs ------------------------------------------------------------------------------------------
    def add_roi_display(self, x0: float, y0: float, x1: float, y1: float) -> bool:
        """A box dragged in DISPLAY coordinates: stored in image pixels (display / scale)."""
        if self.gray is None:
            return False
        cx0, cx1 = sorted((float(x0), float(x1)))
        cy0, cy1 = sorted((float(y0), float(y1)))
        if (cx1 - cx0) < MIN_BOX_DISPLAY_PX or (cy1 - cy0) < MIN_BOX_DISPLAY_PX:
            self.status = "Box too small -- drag a larger rectangle."
            self.notify()
            return False
        s = self.display_scale()
        roi_px = (round(cx0 / s, 1), round(cy0 / s, 1), round(cx1 / s, 1), round(cy1 / s, 1))
        if self.mode == "edge":
            self.rois = [{"kind": "edge", "roi": roi_px, "label": "edge"}]     # a SINGLE edge box
            self.result = None
            self.status = "Edge ROI set. Click Compute MTF."
            self.notify()
            return True
        try:
            group = int(self.fields["group"])
            element = int(self.fields["element"])
            cycles = float(self.fields["cycles"])
            orientation = str(self.fields["orientation"]).strip().lower()
            if orientation not in ORIENTATIONS or not 1 <= element <= 6 or cycles <= 0:
                raise ValueError
        except (TypeError, ValueError):
            self.status = "Set a valid Group (int), Element (1-6), Bars, Cycles (>0) before drawing."
            self.notify()
            return False
        self.rois.append({"kind": "usaf", "group": group, "element": element, "orientation": orientation,
                          "cycles": cycles, "roi": roi_px, "label": f"G{group}E{element}"})
        self.fields["element"] = str(element + 1 if element < 6 else 1)     # the next element, ready
        self.status = f"Added ROI G{group}E{element}. {len(self.rois)} ROI(s); Compute when ready."
        self.notify()
        return True

    def roi_display_box(self, index: int) -> tuple:
        """ROI ``index`` back in display coordinates (what a view draws)."""
        s = self.display_scale()
        x0, y0, x1, y1 = self.rois[index]["roi"]
        return (x0 * s, y0 * s, x1 * s, y1 * s)

    def roi_caption(self, index: int) -> str:
        roi = self.rois[index]
        return "edge" if roi["kind"] == "edge" else f"G{roi['group']}E{roi['element']} {roi['orientation'][0].upper()}"

    def roi_rows(self) -> list[tuple[str, ...]]:
        rows = []
        for roi in self.rois:
            box, mtf, r2 = roi["roi"], roi.get("_mtf"), roi.get("_r2")
            rows.append((str(roi.get("group", "")), str(roi.get("element", "")), str(roi.get("orientation", "edge")),
                         f"{box[0]:g},{box[1]:g},{box[2]:g},{box[3]:g}",
                         "" if mtf is None else f"{mtf:.3f}", "" if r2 is None else f"{r2:.3f}"))
        return rows

    def delete_roi(self, index: int) -> None:
        if 0 <= int(index) < len(self.rois):
            self.rois.pop(int(index))
            self.notify()

    def clear_rois(self, *, notify: bool = True) -> None:
        self.rois = []
        self.result = None
        if notify:
            self.notify()

    # ---- compute ---------------------------------------------------------------------------------------
    def compute(self) -> bool:
        """Fit the ROIs (edge: the one box, or the whole image when none is drawn)."""
        from KrakenOS.EdgeMTF import measure_slanted_edge_mtf
        from KrakenOS.USAFMTF import analyze_usaf_image

        if self.gray is None:
            self.status = "Import an image first."
            self.notify()
            return False
        pitch = _opt_float(self.calibration["pixel_pitch"])
        if self.mode == "edge":
            roi = self.rois[0]["roi"] if self.rois else None
            try:
                self.result = measure_slanted_edge_mtf(self.gray, roi, pixel_pitch_um=pitch)
            except Exception as exc:
                self.status = f"Edge MTF failed: {exc}"
                self.notify()
                return False
            mtf50 = self.result.mtf50_cycles_per_px()
            self.status = (f"Edge MTF: angle {self.result.edge_angle_deg:.1f}°"
                           + (f", MTF50 {mtf50:.3f} cyc/px" if mtf50 else "")
                           + (f" ({mtf50 * 1000.0 / pitch:.1f} lp/mm)" if (mtf50 and pitch) else "") + ".")
            self.notify()
            return True
        if not self.rois:
            self.status = "Draw at least one ROI over a three-bar element first."
            self.notify()
            return False
        mag = _opt_float(self.calibration["magnification"])
        contrast = _opt_float(self.calibration["target_contrast"]) or 1.0
        if self.calibration["space"] == "image" and mag is None:
            self.status = "USAF image-space frequency needs a Magnification |m|."
            self.notify()
            return False
        rois = [{"group": r["group"], "element": r["element"], "roi": r["roi"], "orientation": r["orientation"],
                 "cycles": r["cycles"], "label": r["label"]} for r in self.rois]
        try:
            self.result = analyze_usaf_image(self.gray, rois, magnification=mag, pixel_pitch_um=pitch,
                                             target_contrast=contrast)
        except Exception as exc:
            self.status = f"Compute failed: {exc}"
            self.notify()
            return False
        for roi, measurement in zip(self.rois, self.result.measurements):
            roi["_mtf"], roi["_r2"] = float(measurement.mtf), float(measurement.fit_r_squared)
        self.status = (f"Computed {len(self.result.measurements)} point(s). MTF = image contrast / target "
                       f"contrast ({contrast:g}).")
        self.notify()
        return True

    def draw(self, ax) -> None:
        """The MTF curve (or empty styled axes) on a matplotlib axis -- both views' plot."""
        ax.clear()
        ax.set_title("MTF")
        if self.result is not None:
            space = self.calibration["space"]
            if self.mode == "edge":
                space = "image" if space == "image" else "pixel"
            try:
                self.result.plot(frequency_space=space, ax=ax)
            except Exception as exc:
                self.status = (f"Plot failed: {exc}" if self.mode == "edge" else f"Plotted 0 points: {exc}")
        style_mtf_axes(ax)
        ax.grid(True, alpha=0.25)

    # ---- output ----------------------------------------------------------------------------------------
    def default_csv_name(self) -> str:
        return self.path.with_name(f"{self.path.stem}_mtf.csv").name if self.path else "mtf.csv"

    def save_csv(self, path) -> bool:
        if self.result is None:
            self.status = "Compute the MTF before saving."
            self.notify()
            return False
        try:
            self.result.save_csv(path)
            self.status = f"Saved {Path(path).name}."
        except Exception as exc:
            self.status = f"Save failed: {exc}"
        self.notify()
        return self.status.startswith("Saved")

    def enlarge(self, figure) -> Path | None:
        """bugs/0415: match the main-window Analysis curves -- the current figure as a high-res PNG,
        opened in the system image viewer (zoom / pan / save there)."""
        try:
            from KrakenOS.UI.services.layout_import_export import SCREENSHOT_DIR as out_dir
        except Exception:
            out_dir = Path(".")
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        stem = self.path.stem if self.path else "capture"
        image_path = Path(out_dir) / f"kraken_mtf_from_image_{stem}.png"
        try:
            figure.savefig(image_path, dpi=300, bbox_inches="tight")
        except Exception as exc:
            self.status = f"Could not render the enlarged plot: {exc}"
            self.notify()
            return None
        try:
            self.editor._open_image_with_system_viewer(image_path)
            self.status = f"Opened enlarged MTF plot in the image viewer: {image_path.name}"
        except Exception as exc:
            self.status = f"Saved {image_path.name}, but the system viewer failed: {exc}"
        self.notify()
        return image_path
