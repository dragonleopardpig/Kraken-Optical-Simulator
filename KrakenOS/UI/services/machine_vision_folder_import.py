"""Folder-based machine-vision lens import -> paraxial surrogate (item 3).

The user points at a single vendor *lens folder*; everything useful in it is
ingested and a first-order **surrogate** layout is synthesised automatically:

* the Zemax sequential prescription (``.zmx``) drives the optics -- KrakenOS's
  own ``Parax`` solve (glasses resolved from the catalogs) gives the real EFL and
  BOTH principal planes, and a two-group ideal ``Thin Lens`` "Blackbox" model is
  solved to reproduce them *exactly* between a Front and Rear Optical Vertex
  Datum (the same blackbox shape as the hand-built AZURE 85 / 150 surrogates);
* the mechanical ``STEP`` is wired as the ``lens_step_path`` overlay;
* a Zemax wavefront-map export (``wavefront/Mag1.0.txt``) is wired onto the first
  Thin-Lens row's ``advanced['WavefrontMap']`` so the existing augmentation turns
  the aberration-free surrogate into the vendor's real spot;
* the datasheet PDF and any spot-radius / MTF exports are catalogued in the
  provenance header.

The emitted module is a normal ``machine_vision_<slug>.py`` -- because its stem
starts with ``machine_vision_`` it is discovered into ``machine_vision_files``
and is therefore loadable from the Top menu AND insertable from the right-click
"Machine Vision Lens" cascade (item 2), with no further wiring.

This module is PURE / headless: no Tk, no VTK.  The Parax solve uses the build=0
(no-GL) system builder, so it runs under the validators.  The editor command
(``import_machine_vision_lens_from_folder``) owns the folder chooser, writes the
emitted source into ``common_optical_layouts/`` and loads it.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from KrakenOS.UI.services.datasheet_prescription_import import (
    DatasheetCardinals,
    parse_datasheet_cardinals,
)
from KrakenOS.UI.services.zemax_prescription_import import (
    ZemaxImportDefaults,
    load_zemax_zmx_data,
)
from KrakenOS.UI.surface_table_model import (
    SurfaceRow,
    surface_row_to_spec,
    surface_rows_from_records,
)


# ----------------------------------------------------------------------------
# Asset classification
# ----------------------------------------------------------------------------
_STEP_SUFFIXES = frozenset({".step", ".stp"})
_PDF_SUFFIXES = frozenset({".pdf"})
# Sequential prescriptions KrakenOS can parse first-order data from.
_PRESCRIPTION_SUFFIXES = frozenset({".zmx"})
# CODE V sequence files -- not parsed here, recorded as an alternative source.
_CODEV_SUFFIXES = frozenset({".seq"})
# Zemax archives -- a Black Box (``*_BB*.zar``) hides its surfaces, so it cannot
# drive the optics; it is recorded for provenance and the optics come from the
# System/Prescription Data text dump instead.
_ZAR_SUFFIXES = frozenset({".zar"})

# Sniff tokens for Zemax text analysis exports masquerading as .txt.
_WAVEFRONT_TOKENS = ("wavefront map", "pupil grid", "peak to valley")
_SPOT_TOKENS = ("spot diagram", "image coordinate", "rms radius")
_MTF_TOKENS = ("modulation transfer", "mtf", "spatial frequency")
# A Zemax "System/Prescription Data" report dump -- the first-order truth a Black
# Box lens still exposes (EFL, F/#, pupils, magnification) even with its surfaces
# encrypted.  This is NOT a .zmx surface list; it is parsed by the Path-B builder.
_PRESCRIPTION_DATA_TOKENS = (
    "prescription data",
    "effective focal length",
    "back focal length",
)


@dataclass
class LensFolderAssets:
    """Everything classified out of a vendor lens folder.

    Paths are kept absolute here; the surrogate builder converts the wired ones
    to project-relative when it knows the project root.
    """

    folder: Path
    step_files: list[Path] = field(default_factory=list)
    pdf_files: list[Path] = field(default_factory=list)
    prescription_files: list[Path] = field(default_factory=list)
    prescription_data_files: list[Path] = field(default_factory=list)
    blackbox_files: list[Path] = field(default_factory=list)
    codev_files: list[Path] = field(default_factory=list)
    wavefront_files: list[Path] = field(default_factory=list)
    spot_radius_files: list[Path] = field(default_factory=list)
    mtf_files: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def primary_prescription(self) -> Path | None:
        return self.prescription_files[0] if self.prescription_files else None

    @property
    def primary_prescription_data(self) -> Path | None:
        return self.prescription_data_files[0] if self.prescription_data_files else None

    @property
    def has_optical_source(self) -> bool:
        # A datasheet PDF is a valid last-resort optical source (Path C); most
        # vendors ship one even when no .zmx / Black-Box dump is available.
        return bool(
            self.prescription_files or self.prescription_data_files or self.pdf_files
        )

    @property
    def primary_step(self) -> Path | None:
        return self.step_files[0] if self.step_files else None

    @property
    def primary_pdf(self) -> Path | None:
        return self.pdf_files[0] if self.pdf_files else None

    @property
    def primary_wavefront(self) -> Path | None:
        return self.wavefront_files[0] if self.wavefront_files else None

    @property
    def primary_spot_radius(self) -> Path | None:
        return self.spot_radius_files[0] if self.spot_radius_files else None


def _sniff_text(path: Path) -> str:
    try:
        payload = path.read_bytes()[:8192]
    except Exception:
        return ""
    for encoding in ("utf-16", "utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return payload.decode(encoding).lower()
        except Exception:
            continue
    return ""


def _looks_like_zemax_prescription(path: Path) -> bool:
    """A text .txt prescription (not an analysis export) carries the .zmx ``SURF``
    token records, not the human-readable report tables."""
    text = _sniff_text(path)
    if not text:
        return False
    if any(token in text for token in (*_WAVEFRONT_TOKENS, *_SPOT_TOKENS)):
        return False
    return ("\nsurf " in text or text.startswith("surf ")) and "type " in text


def _looks_like_prescription_data(path: Path, text: str | None = None) -> bool:
    """A Zemax System/Prescription Data report dump (the Black-Box first-order
    truth): the human-readable cardinal table, not a .zmx surface list.  Note it
    mentions "MTF Units", so this must be tested before the loose analysis-token
    sniffs."""
    if text is None:
        text = _sniff_text(Path(path))
    if not text:
        return False
    hits = sum(token in text for token in _PRESCRIPTION_DATA_TOKENS)
    return hits >= 2


def scan_lens_folder(folder: str | Path) -> LensFolderAssets:
    """Classify every file under ``folder`` (recursively) into lens assets."""
    folder = Path(folder)
    assets = LensFolderAssets(folder=folder)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")

    for path in sorted(folder.rglob("*"), key=lambda p: p.as_posix().lower()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        lowered = path.as_posix().lower()
        in_wavefront_dir = "/wavefront/" in lowered or lowered.endswith("/wavefront")
        in_spot_dir = "spot radius" in lowered or "/spot/" in lowered
        in_mtf_dir = "/mtf/" in lowered

        if suffix in _STEP_SUFFIXES:
            assets.step_files.append(path)
        elif suffix in _PDF_SUFFIXES:
            assets.pdf_files.append(path)
        elif suffix in _PRESCRIPTION_SUFFIXES:
            assets.prescription_files.append(path)
        elif suffix in _ZAR_SUFFIXES:
            assets.blackbox_files.append(path)
        elif suffix in _CODEV_SUFFIXES:
            assets.codev_files.append(path)
        elif suffix == ".txt":
            text = _sniff_text(path)
            # The prescription-data dump mentions "MTF Units"/spot terms, so it
            # must win over the loose analysis-token sniffs below.
            if _looks_like_prescription_data(path, text):
                assets.prescription_data_files.append(path)
            elif in_wavefront_dir or any(token in text for token in _WAVEFRONT_TOKENS):
                assets.wavefront_files.append(path)
            elif in_spot_dir or any(token in text for token in _SPOT_TOKENS):
                assets.spot_radius_files.append(path)
            elif in_mtf_dir or any(token in text for token in _MTF_TOKENS):
                assets.mtf_files.append(path)
            elif _looks_like_zemax_prescription(path):
                assets.prescription_files.append(path)

    # Prefer a wavefront map literally named Mag1.0.txt (the augmentation default).
    assets.wavefront_files.sort(key=lambda p: (p.name.lower() != "mag1.0.txt", p.as_posix().lower()))
    assets.spot_radius_files.sort(key=lambda p: (p.name.lower() != "mag1.0.txt", p.as_posix().lower()))

    if not assets.has_optical_source:
        assets.notes.append(
            "No Zemax .zmx prescription, System/Prescription Data dump, or datasheet "
            "PDF found; cannot derive optics."
        )
    elif not assets.prescription_files and assets.prescription_data_files:
        assets.notes.append(
            "Black-box lens: optics derived from the System/Prescription Data dump "
            "(EFL / F-number / magnification), not a decoded surface prescription."
        )
    elif not assets.prescription_files and not assets.prescription_data_files and assets.pdf_files:
        assets.notes.append(
            "Datasheet-only lens: optics derived from the datasheet PDF spec table "
            "(no .zmx prescription or Black-Box dump present)."
        )
    return assets


# ----------------------------------------------------------------------------
# First-order surrogate solve
# ----------------------------------------------------------------------------
@dataclass
class TwoGroupSolution:
    """Two ideal thin groups (focal lengths ``f1``/``f2``) separated by ``d`` and
    placed ``g1`` behind the front datum / ``g2`` ahead of the rear datum, that
    reproduce a target (EFL, front PP, rear PP, span) exactly."""

    f1: float
    f2: float
    d: float
    g1: float
    g2: float
    method: str


def _default_known_glass_names() -> Callable[[], set[str]]:
    def names() -> set[str]:
        try:
            import KrakenOS as Kos

            return {str(name).strip().upper() for name in getattr(Kos.Setup(), "NAMES", [])}
        except Exception:
            return set()

    return names


def default_import_defaults() -> ZemaxImportDefaults:
    """Plausible Zemax-import string defaults (the surrogate overrides SETTINGS,
    so these only seed fields the prescription itself does not pin)."""
    return ZemaxImportDefaults(
        projection_display_mode="Full 3D",
        source_model="Pupil / field",
        pupil_pattern="Meridional fan",
        gaussian_input_mode="Waist + offset",
        gaussian_waist_side="Waist before source",
        source_angular_weight="Uniform solid angle",
        wavefront_style="Wavefront Function",
        tolerance_compare_view="Spot overlay",
        atmos_plot_mode="Refraction / dispersion",
        folded_detector_policy="Trace events",
    )


def _normalized_cardinals(rows: list[SurfaceRow], wavelength: float) -> tuple[float, float, float]:
    """(EFL, ppa, ppp) from a real build=0 ``Parax`` solve, object-distance
    independent: object / last-optical / image thicknesses are zeroed first,
    exactly as ``layout_editor._exact_paraxial_solution_for_rows`` does, so ppa is
    the front principal plane behind the first optical surface and ppp the
    negative of the rear principal plane ahead of the last optical surface."""
    from KrakenOS.UI.services import paraxial_tools

    rows_copy = [SurfaceRow(**asdict(row)) for row in rows]
    rows_copy[0].thickness = 0.0
    rows_copy[-2].thickness = 0.0
    rows_copy[-1].thickness = 0.0
    specs = [surface_row_to_spec(row) for row in rows_copy]
    system = paraxial_tools._build_system_from_specs(
        specs, build=0, apply_optical_solid_output_ports=False
    )
    _, _, _, _a, _b, _c, _d, effl, ppa, ppp, *_rest = system.Parax(float(wavelength))
    return float(effl), float(ppa), float(ppp)


def solve_two_thin_groups(
    effl: float,
    ppa: float,
    ppp: float,
    span: float,
) -> TwoGroupSolution:
    """Solve two ideal thin groups reproducing (EFL, ppa, ppp, span) exactly.

    ``span`` is the front-to-rear optical-vertex distance; the datums land on the
    real glass vertices.  A symmetric (f1=f2) closed form is preferred when it
    keeps both groups inside the span; otherwise a bounded search over the group
    separation finds an asymmetric pair that does.  Both reproduce all four
    cardinals exactly -- the choice only affects where the (fictitious) thin
    groups are drawn relative to the vendor STEP body.
    """
    if not (math.isfinite(effl) and effl > 0.0):
        raise ValueError("surrogate needs a positive, finite effective focal length")
    if not (math.isfinite(span) and span > 0.0):
        raise ValueError("surrogate needs a positive optical-vertex span")
    Q = 1.0 / effl
    HH = span - ppa + ppp  # signed inter-principal-plane distance (rear PP z - front PP z)

    # Symmetric closed form: (d*p)^2 = -HH/effl, p = Q/(2 - d*p).
    symmetric: TwoGroupSolution | None = None
    k2 = -HH * Q
    if k2 > 0.0:
        k = math.sqrt(k2)
        if 0.0 < k < 2.0:
            p = Q / (2.0 - k)
            d = k / p
            x_h = k / Q
            symmetric = TwoGroupSolution(1.0 / p, 1.0 / p, d, ppa - x_h, -ppp - x_h, "symmetric")
    if symmetric is not None and symmetric.g1 >= 0.0 and symmetric.g2 >= 0.0:
        return symmetric

    # Asymmetric search: for each group separation d the two powers are the roots
    # of t^2 - summ t + prod, with prod/summ fixed by EFL and the span constraint;
    # keep the feasible (both gaps >= 0) candidate that sits most cleanly inside.
    best_score = -math.inf
    best: TwoGroupSolution | None = None
    steps = 600
    for index in range(1, steps):
        d = span * index / steps
        prod = -HH * Q / (d * d)  # p1 * p2
        summ = Q + d * prod  # p1 + p2
        disc = summ * summ - 4.0 * prod
        if disc < 0.0:
            continue
        root = math.sqrt(disc)
        for p1, p2 in (((summ - root) / 2.0, (summ + root) / 2.0), ((summ + root) / 2.0, (summ - root) / 2.0)):
            if abs(p1) < 1e-9 or abs(p2) < 1e-9:
                continue
            g1 = ppa - d * p2 / Q
            g2 = -ppp - d * p1 / Q
            score = min(g1, g2)
            if score < 0.0:
                continue
            if score > best_score:
                best_score = score
                best = TwoGroupSolution(1.0 / p1, 1.0 / p2, d, g1, g2, "asymmetric")
    if best is not None:
        return best
    if symmetric is not None:
        return symmetric
    raise ValueError(
        "could not solve a two-group surrogate for these cardinals "
        f"(EFL={effl:.4g}, ppa={ppa:.4g}, ppp={ppp:.4g}, span={span:.4g})"
    )


# ----------------------------------------------------------------------------
# Black-box path: System/Prescription Data dump -> cardinals -> surrogate
# ----------------------------------------------------------------------------
_PRESCRIPTION_DATA_NUMBER = r"[^\n:]*:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"


@dataclass
class PrescriptionData:
    """First-order cardinals scraped from a Zemax System/Prescription Data dump.

    A Black-Box lens hides its surfaces but still reports these, which is enough
    to synthesise an EFL-correct two-group surrogate at the configured conjugate.
    """

    effl: float | None = None
    back_focal_length: float | None = None
    total_track: float | None = None
    image_space_fno: float | None = None
    working_fno: float | None = None
    epd: float | None = None
    entrance_pupil_position: float | None = None
    exit_pupil_position: float | None = None
    stop_radius: float | None = None
    paraxial_image_height: float | None = None
    magnification: float | None = None
    max_radial_field: float | None = None
    wavelength: float | None = None
    field_count: int | None = None
    field_type: str | None = None
    title: str | None = None

    @property
    def object_mode(self) -> str:
        """Finite when a real magnification is reported, else Infinity."""
        m = self.magnification
        if m is None or abs(m) < 1e-6 or not math.isfinite(m):
            return "Infinity"
        return "Finite"


def _scrape_number(text: str, label: str) -> float | None:
    match = re.search(re.escape(label) + _PRESCRIPTION_DATA_NUMBER, text)
    if match is None:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_prescription_data(path: Path | str) -> PrescriptionData | None:
    """Parse a Zemax System/Prescription Data text dump, or ``None`` if it is not
    one / carries no effective focal length."""
    text = _sniff_text(Path(path))
    if not text or "prescription data" not in text:
        return None
    # _sniff_text lowercases; scrape against the lowercased labels.
    data = PrescriptionData(
        effl=_scrape_number(text, "effective focal length"),
        back_focal_length=_scrape_number(text, "back focal length"),
        total_track=_scrape_number(text, "total track"),
        image_space_fno=_scrape_number(text, "image space f/#"),
        working_fno=_scrape_number(text, "working f/#"),
        epd=_scrape_number(text, "entrance pupil diameter"),
        entrance_pupil_position=_scrape_number(text, "entrance pupil position"),
        exit_pupil_position=_scrape_number(text, "exit pupil position"),
        stop_radius=_scrape_number(text, "stop radius"),
        paraxial_image_height=_scrape_number(text, "paraxial image height"),
        magnification=_scrape_number(text, "paraxial magnification"),
        max_radial_field=_scrape_number(text, "maximum radial field"),
        wavelength=_scrape_number(text, "primary wavelength"),
    )
    count = _scrape_number(text, "fields")
    if count is not None and count > 0:
        data.field_count = int(round(count))
    field_type = re.search(r"field type\s*:\s*([^\n]+)", text)
    if field_type is not None:
        data.field_type = field_type.group(1).strip()
    title = re.search(r"\ntitle\s*:\s*([^\n]+)", text)
    if title is not None:
        data.title = title.group(1).strip()
    if data.effl is None or not (math.isfinite(data.effl) and abs(data.effl) > 1e-6):
        return None
    return data


def solve_symmetric_two_groups(
    effl: float,
    span: float,
    *,
    edge_margin: float = 1.4,
) -> tuple[TwoGroupSolution, float, float]:
    """Two equal ideal groups inside ``span`` that reproduce ``effl`` exactly.

    Used by the Black-Box path where only EFL + a mechanical span are known (the
    principal-plane split is not recoverable, so a symmetric pair sized to the
    span is the honest choice).  Returns ``(solution, ppa, ppp)`` -- the resulting
    front/rear principal planes the conjugate placement then uses.
    """
    if not (math.isfinite(effl) and effl > 0.0):
        raise ValueError("surrogate needs a positive, finite effective focal length")
    if not (math.isfinite(span) and span > 0.0):
        raise ValueError("surrogate needs a positive optical span")
    margin = min(max(float(edge_margin), 0.0), span * 0.45)
    d = min(span - 2.0 * margin, effl * 0.999)
    if d <= 0.0:
        raise ValueError("optical span is too small for a two-group surrogate")
    # d*x^2 - 2x + 1/effl = 0 ; take the low-power root so the groups stay weak.
    power = (1.0 - math.sqrt(max(0.0, 1.0 - d / effl))) / d
    focal = 1.0 / power
    x_h = d * effl * power  # = d * effl / focal, the PP offset from each group
    ppa = margin + x_h
    ppp = -(margin + x_h)
    solution = TwoGroupSolution(focal, focal, d, margin, margin, "efl-span-symmetric")
    return solution, ppa, ppp


def _step_optical_axis_extent(step_path: Path | str) -> float | None:
    """The STEP body's extent along the optical (Z) axis, used as the surrogate
    span when a mechanical body is bundled.  Lazy OCC import; ``None`` on any
    failure so the caller can fall back to an EFL-derived default."""
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.Bnd import Bnd_Box
        from OCC.Core.BRepBndLib import brepbndlib
    except Exception:
        return None
    try:
        reader = STEPControl_Reader()
        if reader.ReadFile(str(step_path)) != 1:  # IFSelect_RetDone
            return None
        reader.TransferRoots()
        shape = reader.OneShape()
        box = Bnd_Box()
        brepbndlib.Add(shape, box)
        xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    except Exception:
        return None
    extents = [
        abs(xmax - xmin),
        abs(ymax - ymin),
        abs(zmax - zmin),
    ]
    z_extent = extents[2]
    # Lens STEPs are conventionally authored along Z (the import sets rotation 0);
    # if Z is degenerate fall back to the largest extent so we still get a span.
    if math.isfinite(z_extent) and z_extent > 1e-3:
        return float(z_extent)
    largest = max(extents)
    return float(largest) if math.isfinite(largest) and largest > 1e-3 else None


def _surrogate_span_from_assets(effl: float, step_path: Path | None) -> tuple[float, str]:
    """Pick the optical span for a Black-Box surrogate: the bundled STEP body's
    optical-axis extent (capped to a sane fraction of EFL), else EFL/3.

    NB (bugs/0417): using the STEP GLASS extent instead of the body extent was tried and REVERTED --
    for a lens whose ideal two-group surrogate is geometrically wider than its physical glass (the
    cardinals demand it, e.g. the Excellitas Apo 75 / 0703), ``solve_two_thin_groups`` cannot keep the
    groups inside the glass span and returns NEGATIVE datum margins, so the optical GROUPS overhang by
    MORE than the datum reference planes did. The body extent is the sensible tradeoff (groups stay
    inside; only the reference datum planes stick out ~1.5 mm). Any "surrogate doesn't fit" that
    remains is inherent to a wider-than-glass surrogate, not a span-choice bug."""
    if step_path is not None:
        extent = _step_optical_axis_extent(step_path)
        if extent is not None:
            span = min(max(extent, 0.05 * effl), 0.7 * effl)
            return round(span, 4), "step-body-extent"
    return round(effl / 3.0, 4), "efl-default"


def _finite_conjugate_gaps(
    effl: float,
    magnification: float | None,
    ppa: float,
    ppp: float,
    object_mode: str,
    back_focal_length: float | None,
) -> tuple[float, float]:
    """Object->front-datum and rear-datum->image gaps that put the surrogate at
    the configured conjugate.  Finite: from the transverse magnification; Infinity:
    image at the rear focal point (object placed a nominal distance away)."""
    rear_pp_ahead = -ppp  # positive: rear PP is this far ahead of the rear datum
    if object_mode == "Infinity" or magnification is None or abs(magnification) < 1e-6:
        image_gap = effl - rear_pp_ahead
        return 100.0, max(round(image_gap, 6), 1.0)
    m = float(magnification)
    object_distance = effl * (1.0 - 1.0 / m)  # |u|, in front of the front PP
    image_distance = effl * (1.0 - m)  # v, behind the rear PP
    object_gap = abs(object_distance) - ppa
    image_gap = image_distance - rear_pp_ahead
    return max(round(object_gap, 6), 1.0), max(round(image_gap, 6), 1.0)


# ----------------------------------------------------------------------------
# Surrogate model + source emission
# ----------------------------------------------------------------------------
@dataclass
class SurrogateModel:
    title: str
    slug: str
    object_mode: str
    wavelength: float
    effl: float
    ppa: float
    ppp: float
    span: float
    object_thickness: float
    back_focal_distance: float
    solution: TwoGroupSolution
    stop_diameter: float
    front_aperture: float
    rear_aperture: float
    object_diameter: float
    image_diameter: float
    aperture_type: str
    aperture_value: str
    settings: dict
    surfaces: list[dict]
    source_prescription: str
    step_rel_path: str | None
    wavefront_rel_path: str | None
    spot_radius_rel_path: str | None
    pdf_name: str | None
    notes: list[str] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return f"machine_vision_{self.slug}.py"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("_", str(text).strip().lower()).strip("_")
    return slug or "lens"


def _project_relative(path: Path | None, project_root: Path | None) -> str | None:
    if path is None:
        return None
    path = Path(path)
    if project_root is not None:
        try:
            return path.resolve().relative_to(Path(project_root).resolve()).as_posix()
        except ValueError:
            pass
    return path.as_posix()


@dataclass
class _SurrogateCore:
    """Path-specific optical results the shared assembler turns into a model."""

    effl: float
    ppa: float
    ppp: float
    span: float
    solution: TwoGroupSolution
    object_mode: str
    wavelength: float
    object_gap: float
    image_gap: float
    stop_diameter: float
    front_aperture: float
    rear_aperture: float
    object_diameter: float
    image_diameter: float
    aperture_type: str
    aperture_value: str
    settings_base: dict
    source_label: str
    title_seed: str
    extra_notes: list[str] = field(default_factory=list)


def build_surrogate_from_assets(
    assets: LensFolderAssets,
    *,
    name: str | None = None,
    known_glass_names: Callable[[], set[str]] | None = None,
    import_defaults: ZemaxImportDefaults | None = None,
    project_root: Path | None = None,
) -> SurrogateModel:
    """Build a :class:`SurrogateModel` from classified folder assets.

    Three optical sources are supported, tried in order of fidelity:

    * a readable Zemax ``.zmx`` sequential prescription -> exact ``Parax``
      cardinals and a two-group solve that reproduces them (Path A);
    * a Zemax System/Prescription Data dump from a Black-Box lens (no decodable
      surfaces) -> an EFL-correct symmetric two-group surrogate sized to the
      bundled STEP body and placed at the reported conjugate (Path B);
    * the vendor **datasheet PDF** alone (no ``.zmx`` / no dump) -> cardinals
      scraped from the spec table; when it lists both focal distances (SF & S'F')
      the exact two-group solve is used, else an EFL+span symmetric fallback
      (Path C).  Most vendors ship only a datasheet, so this is the common case.
    """
    if not assets.has_optical_source:
        raise ValueError(
            "No Zemax .zmx prescription, no System/Prescription Data dump, and no "
            "datasheet PDF was found in the selected folder; cannot derive the "
            "lens optics."
        )
    if known_glass_names is None:
        known_glass_names = _default_known_glass_names()
    if import_defaults is None:
        import_defaults = default_import_defaults()
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    if assets.primary_prescription is not None:
        core = _core_from_prescription(assets, known_glass_names, import_defaults)
    elif assets.primary_prescription_data is not None:
        core = _core_from_prescription_data(assets)
    else:
        core = _core_from_datasheet(assets)
    return _assemble_surrogate(core, assets, name=name, project_root=project_root)


def _core_from_prescription(
    assets: LensFolderAssets,
    known_glass_names: Callable[[], set[str]],
    import_defaults: ZemaxImportDefaults,
) -> _SurrogateCore:
    """Path A: exact cardinals from a readable ``.zmx`` via KrakenOS ``Parax``."""
    prescription = assets.primary_prescription
    info = load_zemax_zmx_data(
        Path(prescription), known_glass_names=known_glass_names, defaults=import_defaults
    )
    rows = surface_rows_from_records(list(info.get("surfaces", [])))
    if len(rows) < 3:
        raise ValueError("Prescription does not contain an Object -> optics -> Image stack.")
    settings = dict(info.get("settings", {}))
    wavelength = _safe_float(settings.get("wavelength"), 0.55)

    effl, ppa, ppp = _normalized_cardinals(rows, wavelength)
    optical = rows[1:-1]
    span = sum(float(row.thickness) for row in optical[:-1])
    object_mode = str(settings.get("object_mode", "Finite"))
    object_gap = 100.0 if object_mode == "Infinity" else float(rows[0].thickness)
    image_gap = float(optical[-1].thickness)
    solution = solve_two_thin_groups(effl, ppa, ppp, span)

    aperture_type = str(settings.get("aperture_type", "FNO"))
    aperture_value = str(settings.get("aperture_value", "4"))
    stop_diameter = _stop_diameter(effl, aperture_type, aperture_value, optical)

    front_aperture = _positive(rows[1].diameter, 25.0)
    rear_aperture = _positive(optical[-1].diameter, front_aperture)
    object_diameter = _positive(rows[0].diameter, max(front_aperture, rear_aperture))
    image_diameter = _positive(rows[-1].diameter, rear_aperture)

    notes: list[str] = []
    if solution.method == "symmetric" and (solution.g1 < 0.0 or solution.g2 < 0.0):
        notes.append(
            "A thin-group sits outside the glass span for this strongly asymmetric "
            "lens; the first-order cardinals are still reproduced exactly."
        )

    return _SurrogateCore(
        effl=effl,
        ppa=ppa,
        ppp=ppp,
        span=span,
        solution=solution,
        object_mode=object_mode,
        wavelength=wavelength,
        object_gap=object_gap,
        image_gap=image_gap,
        stop_diameter=stop_diameter,
        front_aperture=front_aperture,
        rear_aperture=rear_aperture,
        object_diameter=object_diameter,
        image_diameter=image_diameter,
        aperture_type=aperture_type,
        aperture_value=aperture_value,
        settings_base=settings,
        source_label=Path(prescription).name,
        title_seed=str(info.get("title") or prescription.stem),
        extra_notes=notes,
    )


def _core_from_prescription_data(assets: LensFolderAssets) -> _SurrogateCore:
    """Path B: an EFL-correct symmetric surrogate from a Black-Box prescription
    dump, sized to the bundled STEP body and placed at the reported conjugate."""
    dump = assets.primary_prescription_data
    data = parse_prescription_data(dump)
    if data is None or data.effl is None:
        raise ValueError(
            "The System/Prescription Data dump did not yield an effective focal "
            "length; cannot derive the lens optics."
        )
    effl = abs(float(data.effl))
    wavelength = _safe_float(data.wavelength, 0.55)
    object_mode = data.object_mode

    span, span_source = _surrogate_span_from_assets(effl, assets.primary_step)
    solution, ppa, ppp = solve_symmetric_two_groups(effl, span)
    object_gap, image_gap = _finite_conjugate_gaps(
        effl, data.magnification, ppa, ppp, object_mode, data.back_focal_length
    )

    if data.stop_radius and data.stop_radius > 0.0:
        stop_diameter = round(2.0 * data.stop_radius, 4)
        aperture_type = "EPD"
        aperture_value = _fmt(data.epd if (data.epd and data.epd > 0.0) else 2.0 * data.stop_radius)
    elif data.epd and data.epd > 0.0:
        stop_diameter = round(float(data.epd), 4)
        aperture_type, aperture_value = "EPD", _fmt(data.epd)
    else:
        fno = data.image_space_fno or data.working_fno or 8.0
        stop_diameter = round(effl / fno, 4)
        aperture_type, aperture_value = "FNO", _fmt(fno)

    lens_aperture = _positive(data.epd, stop_diameter * 1.4)
    field_radius = _positive(data.paraxial_image_height or data.max_radial_field, lens_aperture)
    image_diameter = round(2.0 * field_radius, 4)
    if data.paraxial_image_height or data.max_radial_field:
        # bugs/0662: elements cover the stated field (see the datasheet path).
        lens_aperture = round(max(float(lens_aperture), image_diameter + stop_diameter), 4)
    object_diameter = (
        image_diameter if object_mode == "Finite" else round(max(lens_aperture, image_diameter), 4)
    )

    settings_base: dict = {"object_mode": object_mode, "wavelength": wavelength}
    if data.field_count:
        settings_base["field_count"] = data.field_count
    if data.max_radial_field:
        settings_base["field_value"] = data.max_radial_field
    field_type = _map_field_type(data.field_type)
    if field_type:
        settings_base["field_type"] = field_type

    folder_name = Path(assets.folder).name
    title_seed = f"{folder_name} {data.title}".strip() if data.title else folder_name

    notes = [
        f"Optical span = {span:.4g} mm ({span_source}); the two ideal groups are a "
        "symmetric EFL-equivalent, so the principal-plane split is nominal (the "
        "Black-Box surfaces are not decoded).",
    ]
    if data.back_focal_length:
        notes.append(f"Vendor back focal length = {data.back_focal_length:.4g} mm.")

    return _SurrogateCore(
        effl=effl,
        ppa=ppa,
        ppp=ppp,
        span=span,
        solution=solution,
        object_mode=object_mode,
        wavelength=wavelength,
        object_gap=object_gap,
        image_gap=image_gap,
        stop_diameter=stop_diameter,
        front_aperture=lens_aperture,
        rear_aperture=lens_aperture,
        object_diameter=object_diameter,
        image_diameter=image_diameter,
        aperture_type=aperture_type,
        aperture_value=aperture_value,
        settings_base=settings_base,
        source_label=Path(dump).name,
        title_seed=title_seed,
        extra_notes=notes,
    )


def _core_from_datasheet(assets: LensFolderAssets) -> _SurrogateCore:
    """Path C: first-order cardinals from the vendor datasheet PDF alone.

    When the datasheet lists both focal distances (SF & S'F') BOTH principal
    planes are recovered, so the exact two-group solve (as Path A) reproduces all
    four cardinals; otherwise an EFL+span symmetric surrogate is the honest
    fallback (as Path B).  The conjugate is placed from the datasheet's nominal
    magnification when present, else the object is left at infinity.
    """
    pdf = assets.primary_pdf
    cardinals = parse_datasheet_cardinals(pdf) if pdf is not None else None
    if cardinals is None or cardinals.effl is None:
        raise ValueError(
            "No Zemax .zmx prescription, no System/Prescription Data dump, and the "
            "datasheet PDF did not yield an effective focal length; cannot derive "
            "the lens optics."
        )
    return _core_from_datasheet_cardinals(cardinals, assets)


def _core_from_datasheet_cardinals(
    cardinals: DatasheetCardinals, assets: LensFolderAssets
) -> _SurrogateCore:
    """Turn scraped datasheet cardinals into a surrogate core (split out so the
    cardinals->optics step is unit-testable without a real PDF)."""
    effl = abs(float(cardinals.effl))
    wavelength = 0.55
    object_mode = cardinals.object_mode

    # Span: the datasheet's first-to-last vertex distance (Sigma d) keeps the
    # cardinals self-consistent; else the bundled STEP body extent; else EFL/3.
    if cardinals.span and cardinals.span > 0.0:
        span, span_source = round(float(cardinals.span), 4), "datasheet vertex span"
    else:
        span, span_source = _surrogate_span_from_assets(effl, assets.primary_step)

    if cardinals.has_principal_planes:
        ppa = float(cardinals.ppa)
        ppp = float(cardinals.ppp)
        solution = solve_two_thin_groups(effl, ppa, ppp, span)
        solve_note = (
            "Both principal planes recovered from the datasheet (SF + S'F'); the "
            "two ideal groups reproduce all four cardinals exactly."
        )
    else:
        solution, ppa, ppp = solve_symmetric_two_groups(effl, span)
        solve_note = (
            "Datasheet lists no focal distances; the two ideal groups are a "
            "symmetric EFL-equivalent (the principal-plane split is nominal)."
        )

    object_gap, image_gap = _finite_conjugate_gaps(
        effl, cardinals.magnification, ppa, ppp, object_mode, None
    )

    fno = cardinals.fno if (cardinals.fno and cardinals.fno > 0.0) else 8.0
    stop_diameter = round(effl / fno, 4)
    aperture_type, aperture_value = "FNO", _fmt(fno)

    lens_aperture = round(stop_diameter * 1.4, 4)
    # bugs/0662 (flag_20260830_180206 "rays are passing beyond the diameter of the
    # first and last lens surrogate"): 1.4x the STOP is the pupil footprint on-axis;
    # a finite-conjugate lens's front/rear elements must also cover the FIELD they
    # image (a 1x telecentric with a 2.5 mm pupil images an 11 mm circle -- its
    # elements are >= 13.5 mm, not 3.5). The trace was already right (bugs/0624
    # extends blackbox apertures); the DRAWN discs were the pupil, not the glass.
    if cardinals.image_circle and cardinals.image_circle > 0.0:
        field_cover = float(cardinals.image_circle)
        if cardinals.magnification and abs(float(cardinals.magnification)) > 1e-9:
            field_cover *= max(1.0, 1.0 / abs(float(cardinals.magnification)))
        lens_aperture = round(max(lens_aperture, field_cover + stop_diameter), 4)
    image_diameter = (
        round(float(cardinals.image_circle), 4)
        if (cardinals.image_circle and cardinals.image_circle > 0.0)
        else round(stop_diameter * 1.4, 4)
    )
    if object_mode == "Finite" and cardinals.magnification:
        object_diameter = round(image_diameter / abs(float(cardinals.magnification)), 4)
    else:
        object_diameter = round(max(lens_aperture, image_diameter), 4)

    settings_base: dict = {"object_mode": object_mode, "wavelength": wavelength}
    # bug 0295: complete the surrogate the way the hand-authored machine_vision_*
    # presets are -- carry the field so the object-plane FOV rectangle and the
    # off-axis ray fans render.  A bare object_mode/wavelength dict left the field
    # undefined, so the coverage overlay had no image radius (detector_coverage_
    # overlay: sys_image_radius is None -> skip) and drew the object plane as a
    # plain disc traced by the on-axis ray alone.  field_value is the datasheet's
    # max real image height = image-circle/2; once a camera is glued the Stage-2
    # sync overrides it with the true sensor half-height.
    field_radius = round(image_diameter / 2.0, 4)
    if field_radius > 0.0:
        settings_base["field_type"] = "Real Image Height"
        settings_base["field_value"] = field_radius
        settings_base["field_count"] = 3

    folder_name = Path(assets.folder).name
    title_seed = f"{folder_name} {cardinals.title}".strip() if cardinals.title else folder_name

    notes = [
        f"Optical span = {span:.4g} mm ({span_source}).",
        solve_note,
        "Optics derived from the datasheet PDF; no .zmx prescription or Black-Box "
        "System/Prescription Data dump was present.",
    ]
    hh_check = cardinals.hh_from_cardinals
    if cardinals.hh is not None and hh_check is not None:
        notes.append(
            f"Principal-plane cross-check HH' = {hh_check:.3g} mm vs datasheet "
            f"{cardinals.hh:.3g} mm."
        )

    return _SurrogateCore(
        effl=effl,
        ppa=ppa,
        ppp=ppp,
        span=span,
        solution=solution,
        object_mode=object_mode,
        wavelength=wavelength,
        object_gap=object_gap,
        image_gap=image_gap,
        stop_diameter=stop_diameter,
        front_aperture=lens_aperture,
        rear_aperture=lens_aperture,
        object_diameter=object_diameter,
        image_diameter=image_diameter,
        aperture_type=aperture_type,
        aperture_value=aperture_value,
        settings_base=settings_base,
        source_label=assets.primary_pdf.name if assets.primary_pdf else "datasheet",
        title_seed=title_seed,
        extra_notes=notes,
    )


def _assemble_surrogate(
    core: _SurrogateCore,
    assets: LensFolderAssets,
    *,
    name: str | None,
    project_root: Path,
) -> SurrogateModel:
    """Shared assembly: wire STEP/wavefront overlays, build SETTINGS/SURFACES."""
    step_rel = _project_relative(assets.primary_step, project_root)
    wavefront_rel = _project_relative(assets.primary_wavefront, project_root)
    spot_rel = _project_relative(assets.primary_spot_radius, project_root)
    pdf_name = assets.primary_pdf.name if assets.primary_pdf else None

    title = name or _default_title(core.title_seed, Path(assets.folder).name)
    slug = slugify(name or core.title_seed or Path(assets.folder).name)

    settings = _surrogate_settings(
        base=core.settings_base,
        effl=core.effl,
        object_mode=core.object_mode,
        aperture_type=core.aperture_type,
        aperture_value=core.aperture_value,
        step_rel=step_rel,
    )
    surfaces = _surrogate_surfaces(
        solution=core.solution,
        object_gap=core.object_gap,
        image_gap=core.image_gap,
        stop_diameter=core.stop_diameter,
        front_aperture=core.front_aperture,
        rear_aperture=core.rear_aperture,
        object_diameter=core.object_diameter,
        image_diameter=core.image_diameter,
        wavefront_rel=wavefront_rel,
    )
    notes = list(assets.notes) + list(core.extra_notes)

    return SurrogateModel(
        title=title,
        slug=slug,
        object_mode=core.object_mode,
        wavelength=core.wavelength,
        effl=core.effl,
        ppa=core.ppa,
        ppp=core.ppp,
        span=core.span,
        object_thickness=core.object_gap,
        back_focal_distance=core.image_gap,
        solution=core.solution,
        stop_diameter=core.stop_diameter,
        front_aperture=core.front_aperture,
        rear_aperture=core.rear_aperture,
        object_diameter=core.object_diameter,
        image_diameter=core.image_diameter,
        aperture_type=core.aperture_type,
        aperture_value=core.aperture_value,
        settings=settings,
        surfaces=surfaces,
        source_prescription=core.source_label,
        step_rel_path=step_rel,
        wavefront_rel_path=wavefront_rel,
        spot_radius_rel_path=spot_rel,
        pdf_name=pdf_name,
        notes=notes,
    )


def import_lens_folder(
    folder: str | Path,
    *,
    name: str | None = None,
    project_root: Path | None = None,
) -> SurrogateModel:
    """Convenience: scan ``folder`` then build the surrogate model."""
    assets = scan_lens_folder(folder)
    return build_surrogate_from_assets(assets, name=name, project_root=project_root)


def _safe_float(value, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def _positive(value, fallback: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return result if math.isfinite(result) and result > 0.0 else float(fallback)


def _stop_diameter(effl: float, aperture_type: str, aperture_value: str, optical: list[SurfaceRow]) -> float:
    if aperture_type.upper() == "FNO":
        fno = _safe_float(aperture_value, 0.0)
        if fno > 0.0:
            return round(effl / fno, 4)
    if aperture_type.upper() in {"EPD", "ENTRANCE PUPIL DIAMETER"}:
        epd = _safe_float(aperture_value, 0.0)
        if epd > 0.0:
            return round(epd, 4)
    for row in optical:
        if row.surface == "Aperture" and float(row.diameter) > 0.0:
            return round(float(row.diameter), 4)
    return round(effl / 8.0, 4)


def _default_title(raw_title: str, fallback_stem: str) -> str:
    title = str(raw_title or "").strip()
    if not title:
        title = str(fallback_stem or "lens").replace("_", " ").title()
    if "machine vision" not in title.lower():
        title = f"Machine Vision {title}"
    return title


def _fmt(value) -> str:
    """Compact numeric string for a SETTINGS aperture value."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def _map_field_type(raw: str | None) -> str | None:
    if not raw:
        return None
    low = str(raw).lower()
    if "paraxial image" in low:
        return "Paraxial Image Height"
    if "image height" in low:
        return "Real Image Height"
    if "object height" in low:
        return "Object Height"
    if "angle" in low:
        return "Angle"
    return None


def _surrogate_settings(
    *,
    base: dict,
    effl: float,
    object_mode: str,
    aperture_type: str,
    aperture_value: str,
    step_rel: str | None,
) -> dict:
    settings = dict(base)
    settings["object_mode"] = object_mode
    settings["display_orientation"] = settings.get("display_orientation", "YZ")
    settings["projection_display_mode"] = "Full 3D"
    settings["aperture_type"] = aperture_type
    settings["aperture_value"] = aperture_value
    settings["show_cardinals"] = True
    settings["lens_step_path"] = step_rel or ""
    settings.setdefault("lens_step_largest_component_only", False)
    settings.setdefault("lens_step_rotation_x_deg", 0.0)
    settings.setdefault("lens_step_rotation_y_deg", 0.0)
    settings.setdefault("lens_step_rotation_z_deg", 0.0)
    settings.setdefault("lens_step_axis_offset_xy", [0.0, 0.0])
    settings.setdefault("lens_step_placement_offset_xyz", [0.0, 0.0, 0.0])
    return settings


def _surrogate_surfaces(
    *,
    solution: TwoGroupSolution,
    object_gap: float,
    image_gap: float,
    stop_diameter: float,
    front_aperture: float,
    rear_aperture: float,
    object_diameter: float,
    image_diameter: float,
    wavefront_rel: str | None,
) -> list[dict]:
    group_split = solution.d / 2.0

    group1_advanced: dict = {}
    if wavefront_rel:
        group1_advanced["WavefrontMap"] = {"path": wavefront_rel}

    surfaces: list[dict] = [
        {
            "surface": "Object",
            "name": "Object",
            "rc": 0.0,
            "thickness": round(object_gap, 6),
            "diameter": round(object_diameter, 4),
            "glass": "AIR",
        },
        {
            "surface": "Standard",
            "name": "Front Optical Vertex Datum",
            "rc": 0.0,
            "thickness": round(solution.g1, 6),
            "diameter": round(front_aperture, 4),
            "glass": "AIR",
        },
        {
            "surface": "Thin Lens",
            "name": "Blackbox Group 1",
            "rc": round(solution.f1, 6),
            "thickness": round(group_split, 6),
            "diameter": round(front_aperture, 4),
            "glass": "AIR",
        },
        {
            "surface": "Aperture",
            "name": "Aperture Stop",
            "rc": 0.0,
            "thickness": round(solution.d - group_split, 6),
            "diameter": round(max(2.0, stop_diameter), 4),
            "glass": "AIR",
        },
        {
            "surface": "Thin Lens",
            "name": "Blackbox Group 2",
            "rc": round(solution.f2, 6),
            "thickness": round(solution.g2, 6),
            "diameter": round(rear_aperture, 4),
            "glass": "AIR",
        },
        {
            "surface": "Standard",
            "name": "Rear Optical Vertex Datum",
            "rc": 0.0,
            "thickness": round(image_gap, 6),
            "diameter": round(rear_aperture, 4),
            "glass": "AIR",
        },
        {
            "surface": "Image",
            "name": "Image / Sensor",
            "rc": 0.0,
            "thickness": 0.0,
            "diameter": round(image_diameter, 4),
            "glass": "AIR",
        },
    ]
    if group1_advanced:
        surfaces[2]["advanced"] = group1_advanced
    return surfaces


def render_surrogate_layout_source(model: SurrogateModel) -> str:
    """Emit a self-contained ``machine_vision_<slug>.py`` layout module source."""
    import pprint

    provenance: list[str] = [
        "# Auto-generated machine-vision lens surrogate (folder import, item 3).",
        "#",
        f"# Source prescription : {model.source_prescription}",
    ]
    if model.step_rel_path:
        provenance.append(f"# Mechanical STEP     : {model.step_rel_path}")
    if model.pdf_name:
        provenance.append(f"# Datasheet PDF       : {model.pdf_name}")
    if model.wavefront_rel_path:
        provenance.append(f"# Wavefront (OPD) map : {model.wavefront_rel_path}")
    if model.spot_radius_rel_path:
        provenance.append(f"# Spot-radius export  : {model.spot_radius_rel_path}")
    provenance.extend(
        [
            "#",
            "# This is NOT the vendor prescription -- it is a first-order paraxial",
            "# blackbox (two ideal Thin-Lens groups + stop between Front/Rear Optical",
            "# Vertex Datums) solved from KrakenOS's Parax to reproduce the real lens",
            "# cardinals exactly:",
            f"#   EFL = {model.effl:.6g} mm",
            f"#   front principal plane = {model.ppa:.6g} mm behind the front vertex",
            f"#   rear  principal plane = {-model.ppp:.6g} mm ahead of the rear vertex",
            f"#   front-to-rear optical-vertex span = {model.span:.6g} mm",
            f"#   two-group solve = {model.solution.method} "
            f"(f1={model.solution.f1:.6g}, f2={model.solution.f2:.6g}, d={model.solution.d:.6g})",
            "# Because the surrogate is ideal it carries no real aberration -- a traced",
            "# spot is defocus only.  A wired wavefront map (above) augments it with the",
            "# vendor's real OPD; otherwise drop one in beside the STEP to do so.",
        ]
    )
    for note in model.notes:
        provenance.append(f"# Note: {note}")

    lines = [
        '"""Machine-vision lens surrogate generated by folder import."""',
        "",
        "\n".join(provenance),
        "",
        f"TITLE = {model.title!r}",
        "",
        f"SETTINGS = {pprint.pformat(model.settings, width=100, sort_dicts=True)}",
        "",
        f"SURFACES = {pprint.pformat(model.surfaces, width=100, sort_dicts=False)}",
        "",
    ]
    return "\n".join(lines)
