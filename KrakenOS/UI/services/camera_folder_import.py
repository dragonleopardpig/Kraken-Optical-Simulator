"""Folder-based vendor-camera import -> a CAMERA_DATABASE record (camera analogue
of the machine-vision lens folder importer).

The user points at a single vendor *camera folder*; everything useful in it is
ingested and a camera record is synthesised automatically:

* the mechanical ``STEP`` becomes the body overlay and the stable identifier that
  ``camera_database.camera_model_for_step_path`` reverse-looks-up (so importing
  the STEP couples the surrogate to this camera's sensor exactly like picking it
  from the dropdown);
* the vendor **datasheet PDF** spec table is scraped for the sensor size, pixel
  pitch, resolution, spectral range, lens mount, body dimensions and weight -- the
  same fields the hand-authored ``CAMERA_DATABASE`` entries carry;
* a structured **sidecar** (``*.json`` with camera fields) is honoured first when
  present, so a vendor whose datasheet PDF cannot be text-extracted (e.g. one that
  hides its objects in compressed object streams) can still be imported by dropping
  a one-off JSON beside the STEP.

The record is written to ``attachment/Cameras/imported_cameras.json`` and merged
into ``CAMERA_DATABASE`` at import; hand-authored built-in entries always win, so
an imported camera only ever ADDS a new model.

This module is PURE / headless: no Tk, no VTK.  The editor command
(``import_vendor_camera_from_folder``) owns the folder chooser and the
import+couple; here we only classify, parse and persist.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from KrakenOS.UI.services.datasheet_prescription_import import extract_pdf_text


# ----------------------------------------------------------------------------
# Persistence location (Filen-synced attachment/, next to the vendor assets)
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
IMPORTED_CAMERAS_JSON = PROJECT_ROOT / "attachment" / "Cameras" / "imported_cameras.json"

_STEP_SUFFIXES = frozenset({".step", ".stp"})
_PDF_SUFFIXES = frozenset({".pdf"})
_SIDECAR_SUFFIXES = frozenset({".json"})

# Standard lens-mount flange focal distances (mount -> sensor, mm).  Only the
# universally-standard mounts are listed; proprietary M-mounts (M42/M58/M72)
# vary per vendor and are left unset unless the datasheet gives the dimension.
_MOUNT_FLANGE_MM = {
    "C": 17.526,
    "CS": 12.526,
    "F": 46.5,   # Nikon F
    "EF": 44.0,  # Canon EF
    "EF-S": 44.0,
    "T2": 55.0,
    "M72": None,
    "M58": None,
    "M42": None,
}


@dataclass
class CameraFolderAssets:
    """Everything classified out of a vendor camera folder."""

    folder: Path
    step_files: list[Path] = field(default_factory=list)
    pdf_files: list[Path] = field(default_factory=list)
    sidecar_files: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def primary_step(self) -> Path | None:
        return self.step_files[0] if self.step_files else None

    @property
    def primary_pdf(self) -> Path | None:
        return self.pdf_files[0] if self.pdf_files else None

    @property
    def primary_sidecar(self) -> Path | None:
        return self.sidecar_files[0] if self.sidecar_files else None

    @property
    def has_spec_source(self) -> bool:
        return bool(self.sidecar_files or self.pdf_files)


def _looks_like_camera_sidecar(path: Path) -> bool:
    """A structured camera sidecar carries at least a sensor size (the one field
    the coupling needs); the importer's own ``imported_cameras.json`` registry is
    NOT a per-folder sidecar and is skipped."""
    if path.name.lower() == IMPORTED_CAMERAS_JSON.name.lower():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    keys = {str(k).lower() for k in payload}
    return "sensor_width_mm" in keys or "sensor_size_mm" in keys


def scan_camera_folder(folder: str | Path) -> CameraFolderAssets:
    """Classify every file under ``folder`` (recursively) into camera assets."""
    folder = Path(folder)
    assets = CameraFolderAssets(folder=folder)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")

    for path in sorted(folder.rglob("*"), key=lambda p: p.as_posix().lower()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in _STEP_SUFFIXES:
            assets.step_files.append(path)
        elif suffix in _PDF_SUFFIXES:
            assets.pdf_files.append(path)
        elif suffix in _SIDECAR_SUFFIXES and _looks_like_camera_sidecar(path):
            assets.sidecar_files.append(path)

    if not assets.has_spec_source:
        assets.notes.append(
            "No datasheet PDF and no camera .json sidecar found; cannot derive the "
            "camera sensor specification."
        )
    if assets.primary_step is None:
        assets.notes.append(
            "No STEP body found; the camera record is registered but has no 3D "
            "overlay and will not auto-couple on STEP import."
        )
    return assets


# ----------------------------------------------------------------------------
# Datasheet spec scrape
# ----------------------------------------------------------------------------
@dataclass
class CameraSpec:
    """Sensor + mechanical spec scraped from a vendor camera datasheet PDF.

    ``sensor_width_mm`` / ``sensor_height_mm`` are the only hard requirement (the
    detector-coverage coupling needs the sensor size); every other field is a
    best-effort bonus filled when the datasheet lists it.
    """

    manufacturer: str | None = None
    model: str | None = None
    product_code: str | None = None
    product_series: str | None = None
    status: str | None = None
    sensor_type: str | None = None
    chroma: str | None = None
    spectrum: str | None = None
    spectral_range_nm: tuple[float, float] | None = None
    resolution_px: tuple[int, int] | None = None
    megapixels: float | None = None
    sensor_model: str | None = None
    sensor_architecture: str | None = None
    shutter: str | None = None
    sensor_width_mm: float | None = None
    sensor_height_mm: float | None = None
    sensor_diagonal_mm: float | None = None
    pixel_size_um: tuple[float, float] | None = None
    sensor_bit_depths: tuple[int, ...] | None = None
    pixel_formats: tuple[str, ...] | None = None
    max_frame_rate_fps: float | None = None
    digital_interface: str | None = None
    interface_connector: str | None = None
    body_dimensions_lwh_mm: tuple[float, float, float] | None = None
    lens_mount: str | None = None
    weight_g: float | None = None
    ip_class: str | None = None
    camera_front_to_sensor_mm: float | None = None

    @property
    def has_sensor_size(self) -> bool:
        return bool(
            self.sensor_width_mm and self.sensor_width_mm > 0.0
            and self.sensor_height_mm and self.sensor_height_mm > 0.0
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", value).strip().strip(",;:")
    return text or None


def _field(text: str, label: str, stop: str) -> str | None:
    """Capture the run after ``label:`` up to the next ``stop`` label (the
    extracted datasheet text runs fields together with no separators)."""
    match = re.search(re.escape(label) + r"\s*:?\s*(.+?)\s*" + stop, text)
    return _clean(match.group(1)) if match else None


def _num(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    if match is None:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_camera_datasheet(path: str | Path) -> CameraSpec | None:
    """Scrape a vendor camera datasheet PDF into a :class:`CameraSpec`.

    Returns ``None`` when the PDF cannot be text-extracted or yields no sensor
    size (so the folder importer can fall through to the sidecar / a clear error).
    """
    text = extract_pdf_text(path)
    if not text:
        return None
    # Collapse to a single space-free-ish blob but keep intra-value spaces; the
    # datasheet text already concatenates label/value pairs.
    blob = re.sub(r"[ \t]+", " ", text.replace("\r", " ").replace("\n", " "))

    spec = CameraSpec()
    spec.model = _field(blob, "Model", r"Product code")
    spec.product_code = _field(blob, "Product code", r"Product series")
    spec.product_series = _field(blob, "Product series", r"Status")
    spec.status = _field(blob, "Status", r"Sensor")
    spec.sensor_type = _field(blob, "Sensor type", r"Chroma")
    spec.chroma = _field(blob, "Chroma", r"Spectrum")
    spec.spectrum = _field(blob, "Spectrum", r"Spectral range|Resolution|Sensor model")
    spec.sensor_model = _field(blob, "Sensor model", r"Sensor architecture")
    spec.sensor_architecture = _field(blob, "Sensor architecture (material)", r"Shutter")
    spec.shutter = _field(blob, "Shutter type(s)", r"Sensor size")
    spec.digital_interface = _field(blob, "Digital interface", r"Interface connector")
    spec.interface_connector = _field(blob, "Interface connector", r"FW features|$")
    spec.ip_class = _field(blob, "IP class", r"Lens mount")
    spec.lens_mount = _field(blob, "Lens mount(s)", r"Weight")
    if spec.lens_mount is None:
        spec.lens_mount = _field(blob, "Lens mount", r"Weight")

    low = _num(blob, r"Spectral range\s*:?\s*([\d.]+)\s*nm")
    high = _num(blob, r"Spectral range\s*:?\s*[\d.]+\s*nm to\s*([\d.]+)\s*nm")
    if low is not None and high is not None:
        spec.spectral_range_nm = (low, high)

    res = re.search(r"(?:Resolution|Active\s*Pixel)\s*:?\s*([\d,]+)\s*[×xX]\s*([\d,]+)", blob)
    if res is None:
        # "5120 (H) x 5120 (V)" spec-table form (Bopixel BC-OM/GN datasheets); the
        # >=3-digit guard keeps it off the pixel-pitch row's own "(H) x (V)".
        res = re.search(r"([\d,]{3,})\s*\(H\)\s*[×xX]\s*([\d,]{3,})\s*\(V\)", blob)
    if res is not None:
        try:
            spec.resolution_px = (int(res.group(1).replace(",", "")),
                                  int(res.group(2).replace(",", "")))
        except ValueError:
            pass
    spec.megapixels = _num(blob, r"\(([\d.]+)\s*MP\)")

    size = re.search(
        r"Sensor size\s*:?\s*([\d.]+)\s*[×xX]\s*([\d.]+)\s*mm(?:\s*\(([\d.]+)\s*mm)?", blob
    )
    if size is not None:
        spec.sensor_width_mm = float(size.group(1))
        spec.sensor_height_mm = float(size.group(2))
        if size.group(3):
            spec.sensor_diagonal_mm = float(size.group(3))

    pixel = re.search(r"Pixel size\s*:?\s*([\d.]+)\s*[^\d×xX]*[×xX]\s*([\d.]+)", blob)
    if pixel is None:
        # "4.5 (H) x 4.5 (V) µm" form; anchor on the micro-sign so the resolution
        # row's "(H) x (V)" is not misread as a pixel pitch.
        pixel = re.search(
            r"([\d.]+)\s*\(H\)\s*[×xX]\s*([\d.]+)\s*\(V\)\s*[µμu]m", blob
        )
    if pixel is not None:
        spec.pixel_size_um = (float(pixel.group(1)), float(pixel.group(2)))

    if not spec.has_sensor_size and spec.resolution_px and spec.pixel_size_um:
        # bugs/0307: no explicit "Sensor size ... mm" row (Bopixel PYTHON-25K sheets
        # -- e.g. BC-OM25M12X2 -- list the sensor only as Active Pixel + Pixel Size):
        # derive the active-area size from resolution x pixel pitch (um -> mm).
        rw, rh = spec.resolution_px
        pw, ph = spec.pixel_size_um
        spec.sensor_width_mm = rw * pw / 1000.0
        spec.sensor_height_mm = rh * ph / 1000.0
        if spec.sensor_diagonal_mm is None:
            spec.sensor_diagonal_mm = math.hypot(spec.sensor_width_mm, spec.sensor_height_mm)

    depths = re.findall(r"(\d+)\s*-?\s*Bit", blob)
    if depths:
        spec.sensor_bit_depths = tuple(sorted({int(d) for d in depths}))
    # "Monochrome pixel formats:mono8, mono10" -- anchor on the real format tokens
    # so the bare "Pixel formats" section header (followed by "Sensor bit depth")
    # is not mistaken for the value.
    formats = re.search(
        r"pixel formats\s*:\s*((?:mono|bayer|rgb|bgr|polar|raw)[a-z0-9]*"
        r"(?:\s*,\s*[a-z0-9]+)*)",
        blob,
        re.I,
    )
    if formats is not None:
        spec.pixel_formats = tuple(
            f.strip() for f in formats.group(1).split(",") if f.strip()
        ) or None

    spec.max_frame_rate_fps = _num(blob, r"Max\.?\s*frame rate\s*:?\s*([\d.]+)")
    spec.weight_g = _num(blob, r"Weight\s*:?\s*([\d.]+)\s*g")

    body = re.search(
        r"Body dimensions[^:]*:?\s*([\d.]+)\s*[×xX]\s*([\d.]+)\s*[×xX]\s*([\d.]+)", blob
    )
    if body is not None:
        spec.body_dimensions_lwh_mm = (
            float(body.group(1)), float(body.group(2)), float(body.group(3))
        )

    spec.camera_front_to_sensor_mm = _scrape_flange(blob, spec.lens_mount)

    if not spec.has_sensor_size:
        return None
    return spec


def _scrape_flange(blob: str, lens_mount: str | None) -> float | None:
    """Best-effort flange-focal-distance (front datum -> sensor, mm): a datasheet
    dimension if the text carries one, else the mount's standard FFD, else None."""
    for pattern in (
        r"sensor distance\s*:?\s*([\d.]+)",
        r"flange (?:focal )?distance\s*:?\s*([\d.]+)",
        r"\bFFD\s*:?\s*([\d.]+)",
        r"flange back\s*:?\s*([\d.]+)",
    ):
        value = _num(blob, pattern)
        if value is not None and value > 0.0:
            return round(value, 4)
    if lens_mount:
        token = re.match(r"\s*([A-Za-z0-9-]+)", lens_mount)
        if token is not None:
            std = _MOUNT_FLANGE_MM.get(token.group(1).upper())
            if std:
                return float(std)
    return None


# ----------------------------------------------------------------------------
# Spec / sidecar -> CAMERA_DATABASE record
# ----------------------------------------------------------------------------
_VENDOR_TOKENS = (
    "Allied Vision", "Bopixel", "Basler", "FLIR", "Teledyne", "Ximea", "Baumer",
    "IDS", "Lucid", "Hikrobot", "Sony", "Emergent", "JAI", "SVS-Vistek", "SVS Vistek",
)


def _guess_manufacturer(assets: CameraFolderAssets, spec: CameraSpec | None) -> str | None:
    haystacks = [Path(assets.folder).name]
    if assets.primary_pdf is not None:
        haystacks.append(assets.primary_pdf.name)
    if spec is not None and spec.product_series:
        haystacks.append(spec.product_series)
    hay = " ".join(haystacks).lower()
    for vendor in _VENDOR_TOKENS:
        if vendor.lower() in hay:
            return vendor
    return None


@dataclass
class ImportedCamera:
    """The outcome of a camera folder import."""

    name: str
    record: dict
    spec: CameraSpec | None
    assets: CameraFolderAssets
    notes: list[str] = field(default_factory=list)


def _project_relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def build_camera_record_from_assets(
    assets: CameraFolderAssets, *, name: str | None = None
) -> ImportedCamera:
    """Build a CAMERA_DATABASE-shaped record from classified folder assets.

    A structured ``.json`` sidecar wins when present (the user curated it); else
    the datasheet PDF spec table is scraped.  Raises ``ValueError`` when neither
    yields a sensor size.
    """
    notes: list[str] = list(assets.notes)
    sidecar_record: dict | None = None
    spec: CameraSpec | None = None

    if assets.primary_sidecar is not None:
        try:
            sidecar_record = json.loads(assets.primary_sidecar.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Could not read camera sidecar {assets.primary_sidecar.name}: {exc}")
        notes.append(f"Sensor spec from sidecar {assets.primary_sidecar.name}.")
    else:
        spec = parse_camera_datasheet(assets.primary_pdf) if assets.primary_pdf else None
        if spec is None or not spec.has_sensor_size:
            raise ValueError(
                "Could not extract a sensor size from this folder. Provide a vendor "
                "datasheet PDF whose spec table is text-based, or drop a camera .json "
                "sidecar (with at least sensor_width_mm / sensor_height_mm) beside the "
                "STEP file."
            )
        notes.append(f"Sensor spec scraped from datasheet {assets.primary_pdf.name}.")

    manufacturer = _guess_manufacturer(assets, spec)
    record = _assemble_record(assets, spec, sidecar_record, manufacturer)
    display_name = _display_name(name, sidecar_record, spec, manufacturer, assets)

    if record.get("camera_front_to_sensor_mm") is None:
        notes.append(
            "Flange-to-sensor distance not found in the datasheet (it lives in the "
            "mechanical drawing); the image-plane axial auto-snap is skipped until it "
            "is set. Sensor size + FOV coupling are unaffected."
        )
    return ImportedCamera(
        name=display_name, record=record, spec=spec, assets=assets, notes=notes
    )


def _assemble_record(
    assets: CameraFolderAssets,
    spec: CameraSpec | None,
    sidecar: dict | None,
    manufacturer: str | None,
) -> dict:
    record: dict = {}
    if spec is not None:
        record.update({k: v for k, v in asdict(spec).items() if v is not None})
    if manufacturer and "manufacturer" not in record:
        record["manufacturer"] = manufacturer

    width = record.get("sensor_width_mm")
    height = record.get("sensor_height_mm")
    if width and height and not record.get("sensor_diagonal_mm"):
        record["sensor_diagonal_mm"] = round(float((width ** 2 + height ** 2) ** 0.5), 4)
    if width and "image_diameter_mm" not in record:
        # CAMERA_DATABASE convention: image_diameter_mm is the intended 2D layout
        # dimension = the larger active sensor side (not the diagonal).
        record["image_diameter_mm"] = float(max(width, height or width))

    record["step_path"] = _project_relative(assets.primary_step)
    record["datasheet"] = _project_relative(assets.primary_pdf)

    # A sidecar overrides / augments the scraped record (user-authored truth).
    if isinstance(sidecar, dict):
        record.update({k: v for k, v in sidecar.items() if v is not None})
        # Re-fill derived fields the sidecar may have left out.
        w = record.get("sensor_width_mm")
        h = record.get("sensor_height_mm")
        if w and h and not record.get("sensor_diagonal_mm"):
            record["sensor_diagonal_mm"] = round(float((w ** 2 + h ** 2) ** 0.5), 4)
        if w and "image_diameter_mm" not in record:
            record["image_diameter_mm"] = float(max(w, h or w))

    # Normalise tuple-ish fields JSON round-trips as lists.
    for key in ("resolution_px", "pixel_size_um", "spectral_range_nm",
                "body_dimensions_lwh_mm", "sensor_bit_depths", "pixel_formats"):
        if isinstance(record.get(key), tuple):
            record[key] = list(record[key])
    return record


def _display_name(
    name: str | None,
    sidecar: dict | None,
    spec: CameraSpec | None,
    manufacturer: str | None,
    assets: CameraFolderAssets,
) -> str:
    if name and name.strip():
        return name.strip()
    if isinstance(sidecar, dict) and sidecar.get("name"):
        return str(sidecar["name"]).strip()
    model = (spec.model if spec else None) or (
        sidecar.get("model") if isinstance(sidecar, dict) else None
    )
    if model:
        return f"{manufacturer} {model}".strip() if manufacturer else str(model).strip()
    return Path(assets.folder).name.strip() or "Imported Camera"


# ----------------------------------------------------------------------------
# Registry persistence (attachment/Cameras/imported_cameras.json)
# ----------------------------------------------------------------------------
def load_imported_cameras(path: Path | None = None) -> dict[str, dict]:
    """Read the imported-camera registry ``{name: record}``; ``{}`` when absent."""
    path = Path(path) if path is not None else IMPORTED_CAMERAS_JSON
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_imported_camera(
    name: str, record: dict, *, path: Path | None = None
) -> Path:
    """Merge one ``{name: record}`` into the imported-camera registry JSON and
    return the registry path.  Paths in ``record`` are stored project-relative."""
    path = Path(path) if path is not None else IMPORTED_CAMERAS_JSON
    registry = load_imported_cameras(path)
    registry[str(name)] = record
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    return path


def import_camera_folder(
    folder: str | Path, *, name: str | None = None, persist: bool = True
) -> ImportedCamera:
    """Scan ``folder``, build the camera record, and (by default) persist it to
    the imported-camera registry so ``camera_database`` picks it up."""
    assets = scan_camera_folder(folder)
    imported = build_camera_record_from_assets(assets, name=name)
    if persist:
        write_imported_camera(imported.name, imported.record)
    return imported
