"""Camera + lens catalog matcher (bugs/0634, user feature).

Given a machine-vision requirement (FOV, object-space resolution, minimum working
distance, wavelength), test every registered CAMERA against every catalog LENS and list
the combinations that meet it. Pure first-order optics on NORMALISED specs -- display-free
and guardable; the enumeration (real camera records + lens surrogates -> these specs) and
the results dialog live elsewhere.

Per combination the criteria are (reusing the bugs/0631 relations):
  * resolution  -- camera pixel count >= FOV / resolution (both axes)
  * magnification -- m = sensor / FOV; a fixed-mag lens must bracket it, a fixed-focal
    lens can reach any m (then WD decides)
  * working distance -- WD = f·(1 + 1/|m|) >= WD_min (thin lens)
  * image circle -- lens image circle >= sensor diagonal
  * f/# (advisory) -- the lens nominal f/# should not exceed the diffraction budget
    (bugs/0633): a slower lens is diffraction-limited below the pixel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from KrakenOS.UI.services.system_selection import (
    diffraction_limited_working_fnumber,
    required_pixel_count,
    working_distance_for_focal_length,
)


@dataclass(frozen=True)
class MatchRequirement:
    fov_w_mm: float
    fov_h_mm: float
    resolution_um_per_px: float
    wd_min_mm: float | None = None
    wavelength_um: float = 0.55


@dataclass(frozen=True)
class CameraSpec:
    name: str
    sensor_w_mm: float
    sensor_h_mm: float
    pixels_w: int
    pixels_h: int
    folder: str | None = None               # bugs/0665: the vendor folder (for station building)

    @property
    def sensor_diagonal_mm(self) -> float:
        return math.hypot(self.sensor_w_mm, self.sensor_h_mm)


@dataclass(frozen=True)
class LensSpec:
    name: str
    focal_length_mm: float | None = None
    image_circle_mm: float | None = None
    fnumber: float | None = None            # nominal (infinity) f/#
    mag_min: float | None = None            # for a fixed-magnification lens
    mag_max: float | None = None
    folder: str | None = None               # bugs/0665: the catalog folder (for station building)


@dataclass(frozen=True)
class MatchResult:
    camera: str
    lens: str
    magnification: float
    working_distance_mm: float | None
    image_circle_mm: float | None
    lens_fnumber: float | None
    max_nominal_fnumber: float | None
    resolution_ok: bool
    magnification_ok: bool
    working_distance_ok: bool
    image_circle_ok: bool
    fnumber_ok: bool | None                  # None = unknown (lens f/# not stated)
    passes: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def match_combination(req: MatchRequirement, cam: CameraSpec, lens: LensSpec) -> MatchResult:
    """Test one camera+lens against the requirement. ``passes`` gates on the four HARD
    fits (resolution, magnification, WD, image circle); the f/# is advisory (a performance
    guideline, not a mechanical fit) so it is reported but does not fail the combination."""
    n_w = required_pixel_count(req.fov_w_mm, req.resolution_um_per_px)
    n_h = required_pixel_count(req.fov_h_mm, req.resolution_um_per_px)
    resolution_ok = cam.pixels_w >= n_w and cam.pixels_h >= n_h

    # Magnification the lens must give (width-driven, consistent with the calculator).
    m = cam.sensor_w_mm / req.fov_w_mm

    if lens.mag_min is not None or lens.mag_max is not None:
        # 5% band: a catalog range is nominal, and a fixed-mag lens (min==max) still has a
        # small usable spread -- don't exclude a near-exact match on rounding.
        lo = (lens.mag_min if lens.mag_min is not None else 0.0) * 0.95
        hi = (lens.mag_max if lens.mag_max is not None else float("inf")) * 1.05
        magnification_ok = lo <= m <= hi
    else:
        magnification_ok = True  # fixed-focal: any m in principle; WD is the real gate

    wd = None
    if lens.focal_length_mm and m > 1e-12:
        wd = working_distance_for_focal_length(lens.focal_length_mm, m)
    if req.wd_min_mm is None or req.wd_min_mm <= 0:
        working_distance_ok = True
    elif wd is None:
        working_distance_ok = False
    else:
        working_distance_ok = wd >= req.wd_min_mm - 1e-9

    if lens.image_circle_mm is None:
        image_circle_ok = True  # unknown -> do not fail on it (reported as unknown)
    else:
        # bugs/0665: a 1% corner tolerance -- vendor "max sensor format" pairings put the
        # sensor corners AT the circle (Edmund 11.0 mm circle vs the IMX264's 11.02 mm
        # diagonal); refusing the vendor's own pairing over 0.2% is not a fit judgement.
        image_circle_ok = lens.image_circle_mm >= cam.sensor_diagonal_mm * 0.99 - 1e-9

    # Diffraction budget (advisory): compare the lens NOMINAL f/# to the max nominal f/#
    # whose Airy disk stays ~2 px at the required pixel pitch.
    pitch_um = 1000.0 * cam.sensor_w_mm / n_w
    max_nominal_fno = None
    fnumber_ok: bool | None = None
    if req.wavelength_um and req.wavelength_um > 0:
        working_fno_max = diffraction_limited_working_fnumber(pitch_um, req.wavelength_um)
        max_nominal_fno = working_fno_max / (1.0 + m)
        if lens.fnumber is not None:
            fnumber_ok = lens.fnumber <= max_nominal_fno + 1e-9

    reasons = []
    if not resolution_ok:
        reasons.append(f"needs ≥{n_w}×{n_h}px, camera has {cam.pixels_w}×{cam.pixels_h}")
    if not magnification_ok:
        reasons.append(f"m={m:.3g} outside lens range [{lens.mag_min}, {lens.mag_max}]")
    if not working_distance_ok:
        reasons.append(
            f"WD {wd:.4g}mm < {req.wd_min_mm:.4g}mm" if wd is not None
            else "working distance unknown (no focal length)"
        )
    if not image_circle_ok:
        reasons.append(
            f"image circle {lens.image_circle_mm:.4g}mm < sensor diag {cam.sensor_diagonal_mm:.4g}mm"
        )
    if fnumber_ok is False:
        reasons.append(
            f"f/{lens.fnumber:.3g} slower than diffraction budget f/{max_nominal_fno:.3g} (advisory)"
        )

    passes = resolution_ok and magnification_ok and working_distance_ok and image_circle_ok
    return MatchResult(
        camera=cam.name,
        lens=lens.name,
        magnification=m,
        working_distance_mm=wd,
        image_circle_mm=lens.image_circle_mm,
        lens_fnumber=lens.fnumber,
        max_nominal_fnumber=max_nominal_fno,
        resolution_ok=resolution_ok,
        magnification_ok=magnification_ok,
        working_distance_ok=working_distance_ok,
        image_circle_ok=image_circle_ok,
        fnumber_ok=fnumber_ok,
        passes=passes,
        reasons=tuple(reasons),
    )


def _parse_mag_token(tok: str) -> float:
    if "." in tok:
        return float(tok)               # literal decimal, e.g. "0.5"
    if len(tok) == 2:                    # PYRITE compact "05" -> 0.5, "20" -> 2.0, "10" -> 1.0
        return float(tok) / 10.0
    return float(tok)                    # single digit, e.g. "1x" -> 1.0


# A magnification token: digits (optional dot-decimal) + "x", NOT glued to other
# alnum/dot (so "85_05x" reads "05x", not "85_05x"; "4.5V" is not a token).
_MAG_TOKEN = r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)x"


def parse_magnification_range(text: str):
    """Extract a magnification range (min, max) from a lens name/title, or None.

    Handles PYRITE compact tokens ("05x-20x" = 0.5x–2.0x, "10x" = 1.0x) and literal
    decimals ("0.5x-2.0x"). A single token → a fixed-magnification lens (min==max).
    Magnification is NOT a field on the surrogate, so the name is the only source (data
    map). Underscores are folder SEPARATORS here, never decimals."""
    import re

    ranged = re.search(_MAG_TOKEN + r"\s*(?:-|–|to)\s*" + _MAG_TOKEN, text, re.I)
    if ranged:
        try:
            a, b = _parse_mag_token(ranged.group(1)), _parse_mag_token(ranged.group(2))
            return (min(a, b), max(a, b))
        except ValueError:
            return None
    single = re.search(_MAG_TOKEN + r"(?![A-Za-z0-9.])", text, re.I)
    if single:
        try:
            v = _parse_mag_token(single.group(1))
            return (v, v)
        except ValueError:
            return None
    return None


_LENS_CATALOG_CACHE: dict = {}


def enumerate_cameras() -> list[CameraSpec]:
    """Every registered camera (built-in + imported) with a usable sensor + pixel count."""
    from KrakenOS.UI import camera_database

    try:
        camera_database.refresh_imported_cameras()
    except Exception:
        pass
    out: list[CameraSpec] = []
    for name, rec in dict(camera_database.CAMERA_DATABASE).items():
        if not isinstance(rec, dict):
            continue
        try:
            sw = float(rec.get("sensor_width_mm"))
            sh = float(rec.get("sensor_height_mm"))
            res = rec.get("resolution_px")
            nx, ny = int(res[0]), int(res[1])
        except (TypeError, ValueError, KeyError, IndexError):
            continue
        if sw > 0 and sh > 0 and nx > 0 and ny > 0:
            folder = None
            step_path = rec.get("step_path")
            if step_path:
                try:
                    from pathlib import Path as _P

                    candidate = _P(str(step_path))
                    if not candidate.is_absolute():
                        candidate = _P(__file__).resolve().parents[3] / candidate
                    folder = str(candidate.parent) if candidate.parent.exists() else None
                except Exception:
                    folder = None
            out.append(CameraSpec(str(name), sw, sh, nx, ny, folder=folder))
    return out


def _lens_dir():
    import os

    from pathlib import Path

    override = os.environ.get("KRAKEN_LENS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "attachment" / "Lens"


def enumerate_lenses(*, use_cache: bool = True) -> list[LensSpec]:
    """Every lens catalog folder under attachment/Lens with an optical source, loaded via
    the headless folder importer into a normalised LensSpec. Cached (scraping the datasheet
    PDFs is the slow part); pass use_cache=False to force a re-scan."""
    from KrakenOS.UI.services.machine_vision_folder_import import (
        import_lens_folder,
        scan_lens_folder,
    )

    lens_dir = _lens_dir()
    key = str(lens_dir)
    if use_cache and key in _LENS_CATALOG_CACHE:
        return list(_LENS_CATALOG_CACHE[key])
    out: list[LensSpec] = []
    if lens_dir.exists():
        for folder in sorted(p for p in lens_dir.iterdir() if p.is_dir()):
            try:
                if not scan_lens_folder(folder).has_optical_source:
                    continue
                model = import_lens_folder(str(folder))
            except Exception:
                continue
            fno = None
            if str(getattr(model, "aperture_type", "")).upper() == "FNO":
                try:
                    fno = float(model.aperture_value)
                except (TypeError, ValueError):
                    fno = None
            name = str(getattr(model, "title", "") or folder.name)
            mag = parse_magnification_range(name) or parse_magnification_range(folder.name)
            try:
                efl = float(model.effl) or None
            except (TypeError, ValueError):
                efl = None
            try:
                ic = float(model.image_diameter) or None
            except (TypeError, ValueError):
                ic = None
            out.append(LensSpec(
                name=name, focal_length_mm=efl, image_circle_mm=ic, fnumber=fno,
                mag_min=(mag[0] if mag else None), mag_max=(mag[1] if mag else None),
                folder=str(folder),
            ))
    _LENS_CATALOG_CACHE[key] = list(out)
    return out


def match_catalog(req: MatchRequirement, cameras, lenses) -> list[MatchResult]:
    """Every camera × every lens, passing combinations first, then by fewest failed
    criteria; within a rank, larger working-distance margin (more mechanical clearance)."""
    results = [match_combination(req, c, l) for c in cameras for l in lenses]

    def _sort_key(r: MatchResult):
        wd_margin = (r.working_distance_mm or 0.0) - (req.wd_min_mm or 0.0)
        return (0 if r.passes else 1, len(r.reasons), -wd_margin)

    results.sort(key=_sort_key)
    return results


def open_catalog_matcher_dialog(editor):
    """Camera + Lens Matcher: enter the requirement, then list every registered camera ×
    catalog lens combination that meets it (passing first). bugs/0634."""
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.services.system_selection import gather_system_selection_prefill

    parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
    dialog = tk.Toplevel(parent)
    dialog.title("Camera + Lens Matcher")
    try:
        dialog.transient(parent)
    except Exception:
        pass

    fov, _sensor, _pix = gather_system_selection_prefill(editor)

    def _pf(v):
        return f"{float(v):.6g}" if v else ""

    fov_w = tk.StringVar(value=_pf(fov[0] if fov else None))
    fov_h = tk.StringVar(value=_pf(fov[1] if fov else None))
    res_v = tk.StringVar(value="")
    wd_v = tk.StringVar(value="")
    wl_v = tk.StringVar(value="0.55")
    status = tk.StringVar(value="Enter the requirement and click Match.")

    top = ttk.Frame(dialog, padding=8)
    top.grid(row=0, column=0, sticky="ew")
    for i, (label, var) in enumerate([
        ("FOV W (mm):", fov_w), ("FOV H (mm):", fov_h), ("Res (µm/px):", res_v),
        ("Min WD (mm):", wd_v), ("λ (µm):", wl_v),
    ]):
        ttk.Label(top, text=label).grid(row=0, column=2 * i, padx=(6, 2), sticky="e")
        ttk.Entry(top, textvariable=var, width=8).grid(row=0, column=2 * i + 1, padx=(0, 4))

    cols = ("camera", "lens", "mag", "wd", "circle", "fno", "result")
    headers = {"camera": "Camera", "lens": "Lens", "mag": "|m|", "wd": "WD mm",
               "circle": "Img circle", "fno": "f/#", "result": "Result"}
    widths = {"camera": 160, "lens": 220, "mag": 60, "wd": 70, "circle": 80, "fno": 90, "result": 90}
    tree = ttk.Treeview(dialog, columns=cols, show="headings", height=14)
    for c in cols:
        tree.heading(c, text=headers[c])
        tree.column(c, width=widths[c], anchor="w")
    tree.grid(row=1, column=0, sticky="nsew", padx=8)
    vsb = ttk.Scrollbar(dialog, orient="vertical", command=tree.yview)
    vsb.grid(row=1, column=1, sticky="ns")
    tree.configure(yscrollcommand=vsb.set)
    dialog.rowconfigure(1, weight=1)
    dialog.columnconfigure(0, weight=1)
    tree.tag_configure("pass", background="#e6f5e6")
    tree.tag_configure("fail", foreground="#888888")

    detail = ttk.Label(dialog, textvariable=status, wraplength=760, justify="left")
    detail.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
    detail.bind(  # bugs/0636: reflow the status text to the live width
        "<Configure>", lambda e: detail.configure(wraplength=max(int(e.width) - 12, 120))
    )

    results_state: dict[int, MatchResult] = {}

    def _num(var):
        raw = (var.get() or "").strip()
        if not raw:
            return None
        try:
            v = float(raw)
        except ValueError:
            return "error"
        return v if v > 0 else "error"

    def _fmt(v, d=4):
        return "—" if v is None else f"{float(v):.{d}g}"

    def do_match():
        fw, fh, r = _num(fov_w), _num(fov_h), _num(res_v)
        wd, wl = _num(wd_v), _num(wl_v)
        if "error" in (fw, fh, r, wd, wl) or fw is None or fh is None or r is None:
            status.set("Enter a positive FOV width, height and resolution (WD/λ optional).")
            return
        status.set("Matching… (first run scrapes the lens datasheets, ~10–20 s)")
        dialog.update_idletasks()
        try:
            req = MatchRequirement(fw, fh, r, wd_min_mm=wd, wavelength_um=(wl or 0.55))
            cams = enumerate_cameras()
            lenses = enumerate_lenses()
            results = match_catalog(req, cams, lenses)
        except Exception as exc:  # noqa: BLE001
            status.set(f"Match failed: {exc}")
            return
        tree.delete(*tree.get_children())
        results_state.clear()
        n_pass = 0
        for idx, rr in enumerate(results):
            fno = ("—" if rr.lens_fnumber is None
                   else f"f/{_fmt(rr.lens_fnumber, 3)}≤f/{_fmt(rr.max_nominal_fnumber, 3)}"
                   if rr.max_nominal_fnumber is not None else f"f/{_fmt(rr.lens_fnumber, 3)}")
            tag = "pass" if rr.passes else "fail"
            if rr.passes:
                n_pass += 1
            iid = tree.insert("", "end", values=(
                rr.camera, rr.lens, _fmt(rr.magnification, 3), _fmt(rr.working_distance_mm, 4),
                _fmt(rr.image_circle_mm, 4), fno,
                "✓ match" if rr.passes else "✗",
            ), tags=(tag,))
            results_state[iid] = rr
        status.set(
            f"{n_pass} of {len(results)} combinations match "
            f"({len(cams)} cameras × {len(lenses)} lenses). Select a row for details."
        )

    def on_select(_e=None):
        sel = tree.selection()
        if not sel:
            return
        rr = results_state.get(sel[0])
        if rr is None:
            return
        if rr.passes:
            status.set(
                f"✓ {rr.camera} + {rr.lens}: |m|={rr.magnification:.3g}, "
                f"WD≈{_fmt(rr.working_distance_mm)} mm, image circle {_fmt(rr.image_circle_mm)} mm."
                + ("" if rr.fnumber_ok is not False else "  Note: lens f/# slower than the diffraction budget (advisory).")
            )
        else:
            status.set(f"✗ {rr.camera} + {rr.lens}: " + "; ".join(rr.reasons))

    tree.bind("<<TreeviewSelect>>", on_select)
    ttk.Button(top, text="Match", command=do_match).grid(row=0, column=10, padx=(8, 0))

    try:
        editor._show_centered_dialog(dialog)
    except Exception:
        pass
    return dialog
