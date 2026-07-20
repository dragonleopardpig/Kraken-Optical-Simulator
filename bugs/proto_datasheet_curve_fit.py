"""Prototype: fit a machine-vision surrogate to vendor datasheet performance curves.

Follow-up to bugs/0374. The Schneider/PYRITE datasheets embed their performance
plots (MTF, relative illumination, distortion, transmittance) as RASTER bitmap
images -- no text extractor can read them -- so this prototype DIGITISES the
raster with a projection-profile axis calibration (needs pdfplumber, the optional
`datasheet` extra) and fits the faithfully-reproducible effects.

Fidelity map (what an aberration-free two-group surrogate can honestly do):
  * Relative illumination falloff  -> FAITHFUL. Digitise + fit RI(h); the surrogate
    already carries a relative-illumination suite (bugs/0259-0262) whose per-field
    weight this tunes. This is the biggest real effect (to ~67% at the corner).
  * Distortion                     -> FAITHFUL but here NEGLIGIBLE (<0.2%); the
    ideal surrogate's 0% is already within the datasheet.
  * Transmittance vs wavelength    -> a scalar throughput (~90% flat); minor.
  * MTF                            -> NOT a faithful fit. Reproducing an MTF needs a
    field-dependent wavefront/PSF; MTF->OPD is non-unique without a vendor OPD file.
    Only an APPROXIMATE field-blur match is possible here; the faithful path stays a
    Zemax OPD export on Group 1 (advanced['WavefrontMap']).

Run:  .devenv/state/venv/bin/python bugs/proto_datasheet_curve_fit.py [datasheet.pdf]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DEFAULT_PDF = Path(
    "attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517/"
    "PYRITE_45_85_05x-20x_V38_1072517_datasheet.pdf"
)


# ---------------------------------------------------------------------------
# Raster plot location + axis calibration
# ---------------------------------------------------------------------------
@dataclass
class PlotRaster:
    rgb: np.ndarray            # HxWx3 uint8
    x_left: int
    x_right: int
    y_top: int
    y_bottom: int
    x_range: tuple[float, float]
    y_range: tuple[float, float]

    def field_of(self, px: float) -> float:
        f0, f1 = self.x_range
        return f0 + (px - self.x_left) / (self.x_right - self.x_left) * (f1 - f0)

    def value_of(self, py: float) -> float:
        v0, v1 = self.y_range  # v0 at y_bottom, v1 at y_top
        return v0 + (self.y_bottom - py) / (self.y_bottom - self.y_top) * (v1 - v0)


def _locate_plot_bbox(page, header_contains: str) -> tuple[float, float, float, float] | None:
    """The large square-ish plot image directly below a section header."""
    header_top = None
    needle = header_contains.lower()
    for w in page.extract_words():
        if needle in w["text"].lower():
            header_top = w["top"]
            break
    if header_top is None:
        # header words may be split; fall back to a line scan
        text_lines = (page.extract_text() or "").lower()
        if needle not in text_lines:
            return None
    plots = [
        im for im in page.images
        if (im["x1"] - im["x0"]) > 150 and 0.6 < (im["x1"] - im["x0"]) / (im["bottom"] - im["top"]) < 1.6
    ]
    if not plots:
        return None
    if header_top is not None:
        below = [im for im in plots if im["top"] >= header_top - 5]
        plots = below or plots
        plots.sort(key=lambda im: im["top"])
    return (plots[0]["x0"], plots[0]["top"], plots[0]["x1"], plots[0]["bottom"])


def _render_and_calibrate(
    page, bbox, x_range, y_range, dpi: int = 300
) -> PlotRaster | None:
    im = page.within_bbox(bbox).to_image(resolution=dpi).original.convert("RGB")
    arr = np.asarray(im)
    h, w, _ = arr.shape
    gray = arr.mean(axis=2)
    dark = gray < 90  # near-black axis spines (gridlines are lighter grey)
    col = dark.sum(axis=0)
    row = dark.sum(axis=1)
    cx = np.where(col > 0.55 * h)[0]
    ry = np.where(row > 0.55 * w)[0]
    if cx.size < 2 or ry.size < 2:
        return None
    return PlotRaster(
        rgb=arr,
        x_left=int(cx.min()), x_right=int(cx.max()),
        y_top=int(ry.min()), y_bottom=int(ry.max()),
        x_range=x_range, y_range=y_range,
    )


def _worst_case_envelope(pr: PlotRaster) -> np.ndarray:
    """Per-column lowest coloured-curve point -> the worst-case (conservative)
    relative-illumination bound across all F/# and magnification conditions."""
    arr = pr.rgb.astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    colored = (mx - mn > 45) & (mx > 90)  # saturated hue => a plotted curve
    rows = np.arange(pr.rgb.shape[0])[:, None]
    inside = (rows >= pr.y_top) & (rows <= pr.y_bottom)
    samples = []
    for xc in range(pr.x_left + 2, pr.x_right - 1):
        ys = np.where(colored[:, xc] & inside[:, 0])[0]
        if ys.size:
            samples.append((pr.field_of(xc), pr.value_of(ys.max())))  # max y = lowest value
    return np.asarray(samples)


def _signed_extent(pr: PlotRaster) -> tuple[float, float]:
    """Min/max plotted value over the whole data area (for distortion magnitude)."""
    arr = pr.rgb.astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    colored = (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b) > 45)
    ys, xs = np.where(colored)
    keep = (ys >= pr.y_top) & (ys <= pr.y_bottom) & (xs >= pr.x_left) & (xs <= pr.x_right)
    vals = np.array([pr.value_of(y) for y in ys[keep]])
    return (float(vals.min()), float(vals.max())) if vals.size else (0.0, 0.0)


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------
@dataclass
class RIFit:
    h_max: float
    c2: float
    c4: float
    rms_pct: float

    def weight(self, h: np.ndarray | float):
        u = np.asarray(h, dtype=float) / self.h_max
        return np.clip(1.0 - self.c2 * u**2 - self.c4 * u**4, 0.0, 1.0)


def fit_relative_illumination(field: np.ndarray, ri_pct: np.ndarray) -> RIFit:
    """RI(h)/RI(0) = 1 - c2 (h/hmax)^2 - c4 (h/hmax)^4, enforcing RI(0)=1
    (relative illumination is normalised to unity on-axis)."""
    h_max = float(field.max())
    u = field / h_max
    y = ri_pct / 100.0
    # design matrix for (1 - y) = c2 u^2 + c4 u^4
    A = np.column_stack([u**2, u**4])
    coeffs, *_ = np.linalg.lstsq(A, 1.0 - y, rcond=None)
    c2, c4 = float(coeffs[0]), float(coeffs[1])
    model = 1.0 - c2 * u**2 - c4 * u**4
    rms = float(np.sqrt(np.mean((model - y) ** 2)) * 100.0)
    return RIFit(h_max=h_max, c2=c2, c4=c4, rms_pct=rms)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def run(pdf_path: Path, out_png: Path) -> dict:
    import pdfplumber

    report: dict = {"pdf": str(pdf_path)}
    with pdfplumber.open(str(pdf_path)) as pdf:
        ri_pr = dist_pr = None
        for page in pdf.pages:
            if ri_pr is None:
                bbox = _locate_plot_bbox(page, "Rel. illumination")
                if bbox:
                    ri_pr = _render_and_calibrate(page, bbox, (0.0, 31.3), (0.0, 100.0))
            if dist_pr is None:
                bbox = _locate_plot_bbox(page, "Distortion")
                if bbox:
                    dist_pr = _render_and_calibrate(page, bbox, (0.0, 31.3), (-0.2, 0.2))
            if ri_pr and dist_pr:
                break

    if ri_pr is None:
        report["error"] = "relative-illumination plot not found"
        return report

    samples = _worst_case_envelope(ri_pr)
    fit = fit_relative_illumination(samples[:, 0], samples[:, 1])
    report["ri_samples"] = int(len(samples))
    report["ri_fit"] = {"h_max_mm": fit.h_max, "c2": fit.c2, "c4": fit.c4, "rms_pct": fit.rms_pct}
    report["ri_corner_pct"] = float(samples[np.argmax(samples[:, 0]), 1])

    if dist_pr is not None:
        lo, hi = _signed_extent(dist_pr)
        report["distortion_max_abs_pct"] = max(abs(lo), abs(hi))

    _plot(ri_pr, samples, fit, report, out_png)
    return report


def _plot(ri_pr, samples, fit, report, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hh = np.linspace(0, fit.h_max, 200)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(samples[:, 0], samples[:, 1], ".", ms=3, color="tab:red",
            label=f"digitised worst-case ({len(samples)} pts)")
    ax.plot(hh, 100.0 * fit.weight(hh), "-", lw=2, color="tab:blue",
            label=f"fit: 1 - {fit.c2:.4f}u² - {fit.c4:.4f}u²²  (rms {fit.rms_pct:.2f}%)")
    ax.set_xlabel("Image height / mm")
    ax.set_ylabel("Relative illumination / %")
    ax.set_title("Datasheet relative-illumination -> surrogate weight (prototype)")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def main() -> int:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        print(f"datasheet not found: {pdf_path}")
        return 1
    out_png = Path("bugs/_proto_datasheet_ri_fit.png")
    report = run(pdf_path, out_png)
    print("=" * 70)
    print("Datasheet performance-curve fit prototype")
    print("=" * 70)
    print(f"PDF: {report['pdf']}")
    if "error" in report:
        print(f"ERROR: {report['error']}")
        return 1
    fit = report["ri_fit"]
    print(f"\nRELATIVE ILLUMINATION (faithful):")
    print(f"  digitised {report['ri_samples']} worst-case points; corner RI = {report['ri_corner_pct']:.1f}%")
    print(f"  fit  RI(h)/RI(0) = 1 - {fit['c2']:.4f}(h/{fit['h_max_mm']:.1f})^2 - {fit['c4']:.4f}(h/{fit['h_max_mm']:.1f})^4")
    print(f"  fit rms = {fit['rms_pct']:.2f}%  ->  surrogate per-field illumination weight w(h)")
    rifit = RIFit(fit["h_max_mm"], fit["c2"], fit["c4"], fit["rms_pct"])
    print("  weight table (feeds the bugs/0259-0262 relative-illumination suite):")
    for h in (0.0, 0.25, 0.5, 0.75, 1.0):
        hmm = h * fit["h_max_mm"]
        print(f"      h={hmm:5.1f}mm ({h:.2f}·h_max)  w={rifit.weight(hmm):.3f}")
    if "distortion_max_abs_pct" in report:
        d = report["distortion_max_abs_pct"]
        verdict = "NEGLIGIBLE -- ideal surrogate's 0% already matches" if d < 0.5 else "fit as a radial polynomial"
        print(f"\nDISTORTION (faithful): max |distortion| = {d:.3f}%  ->  {verdict}")
    print("\nMTF (approximate only): raster curves; a faithful fit needs a vendor OPD")
    print("  file (advanced['WavefrontMap'] on Group 1). Not attempted here.")
    print(f"\nverification plot: {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
