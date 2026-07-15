"""Camera database used by the layout editor.

The editor uses ``image_diameter_mm`` as the full image plane size when a camera
is selected.  Store the intended 2D layout dimension there explicitly; for
rectangular sensors the fallback is the larger active sensor side, not the
diagonal.
"""

from __future__ import annotations

import json
from pathlib import Path


CAMERA_NONE_LABEL = "None"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATTACHMENT_DIR = PROJECT_ROOT / "attachment"
ATTACHMENT_CAMERA_DIR = next(
    (
        path
        for path in (
            ATTACHMENT_DIR / "camera",
            ATTACHMENT_DIR / "Camera",
            ATTACHMENT_DIR / "Cameras",
        )
        if path.is_dir()
    ),
    ATTACHMENT_DIR / "camera",
)


def _preferred_existing_path(*candidates: Path) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


CAMERA_DATABASE: dict[str, dict[str, object]] = {
    "Allied Vision hr25MCX": {
        "manufacturer": "Allied Vision",
        "model": "hr25MCX",
        "product_code": "F004053",
        "product_series": "HR CoaXPress",
        "status": "Available",
        "datasheet": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "hr25MCX_Datasheet.pdf",
            Path.home() / "cameras" / "hr25MCX_Datasheet.pdf",
        ),
        "sensor_type": "Area scan",
        "chroma": "Mono",
        "spectrum": "Visible",
        "spectral_range_nm": (400.0, 1000.0),
        "resolution_px": (5120, 5120),
        "megapixels": 25.0,
        "sensor_model": "ON Semiconductor NOIP1SN025KA-GDI",
        "sensor_architecture": "CMOS",
        "shutter": "Global shutter",
        "sensor_width_mm": 23.04,
        "sensor_height_mm": 23.04,
        "sensor_diagonal_mm": 32.58,
        "sensor_format": "APS-H",
        "image_diameter_mm": 23.04,
        "pixel_size_um": (4.50, 4.50),
        "sensor_bit_depths": (8, 10),
        "pixel_formats": ("mono8", "mono10"),
        "max_frame_rate_fps": 81.0,
        "exposure_time_us_min": 35.0,
        "exposure_time_s_max": 60.0,
        "gain_db_range": (0.0, 18.0),
        "digital_interface": "CoaXPress CXP-6, 4 connections",
        "interface_connector": "DIN 1.0/2.3",
        "power_supply": "10 to 25 VDC, Power over CoaXPress",
        "power_consumption_w_typ": 15.0,
        "operating_temperature_housing_c": (-10.0, 60.0),
        "body_dimensions_lwh_mm": (56.0, 70.0, 70.0),
        "lens_mount": "M58x0.75",
        "weight_g": 420.0,
        "ip_class": "IP30",
        "camera_front_to_sensor_mm": 11.48,
        "step_path": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "3D_CAD_HR25xCXP.STEP",
            Path.home() / "cameras" / "3D_CAD_HR25xCXP.STEP",
        ),
    },
    "Allied Vision shr661MCX12": {
        "manufacturer": "Allied Vision",
        "model": "shr661MCX12",
        "product_code": "F004141",
        "product_series": "SHR CoaXPress",
        "status": "Available",
        "datasheet": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "shr661MCX12_Datasheet.pdf",
            Path.home() / "cameras" / "shr661MCX12_Datasheet.pdf",
        ),
        "sensor_type": "Area scan",
        "chroma": "Mono",
        "spectrum": "Visible",
        "spectral_range_nm": (400.0, 1000.0),
        "resolution_px": (13392, 9528),
        "megapixels": 127.6,
        "sensor_model": "Sony IMX661",
        "sensor_architecture": "CMOS",
        "shutter": "Global shutter",
        "sensor_width_mm": 46.2,
        "sensor_height_mm": 32.87,
        "sensor_diagonal_mm": 56.7,
        "sensor_format": "Type 3.6",
        "image_diameter_mm": 46.2,
        "pixel_size_um": (3.45, 3.45),
        "sensor_bit_depths": (8, 10, 12, 16),
        "pixel_formats": ("mono8", "mono10", "mono12", "mono16"),
        "max_frame_rate_fps": 20.3,
        "exposure_time_us_min": 1.0,
        "exposure_time_s_max": 60.0,
        "gain_db_range": (0.0, 36.0),
        "digital_interface": "CoaXPress CXP-12, 4 connections",
        "interface_connector": "micro-BNC",
        "power_supply": "10 to 25 VDC, Power over CoaXPress",
        "power_consumption_w_typ": 17.0,
        "operating_temperature_housing_c": (-10.0, 60.0),
        "body_dimensions_lwh_mm": (83.0, 80.0, 80.0),
        "lens_mount": "M72x0.75",
        "weight_g": 580.0,
        "ip_class": "IP30",
        "camera_front_to_sensor_mm": 19.88,
        "step_path": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "3D_CAD_shr661MCX.STEP",
            Path.home() / "cameras" / "3D_CAD_shr661MCX.STEP",
        ),
    },
    "Japan Bopixel BC-GM65M12X4-M42": {
        "manufacturer": "Japan Bopixel",
        "model": "BC-GM65M12X4-M42",
        "product_code": "BC-GM65M12X4",
        "product_series": "BC-G CoaXPress",
        "status": "Available",
        "datasheet": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "BC-Gx65M12X4_Spec_ver04_EN.pdf",
            Path.home() / "cameras" / "BC-Gx65M12X4_Spec_ver04_EN.pdf",
        ),
        "sensor_type": "Area scan",
        "chroma": "Mono",
        "spectrum": "Visible",
        "resolution_px": (9344, 7000),
        "megapixels": 65.0,
        "sensor_model": "Gpixel GMAX3265",
        "sensor_architecture": "CMOS",
        "shutter": "Global shutter",
        "sensor_width_mm": 29.90,
        "sensor_height_mm": 22.40,
        "sensor_diagonal_mm": 37.36,
        "image_diameter_mm": 29.90,
        "pixel_size_um": (3.2, 3.2),
        "sensor_bit_depths": (8,),
        "pixel_formats": ("mono8",),
        "exposure_time_us_min": 12.0,
        "exposure_time_s_max": 2.0,
        "digital_interface": "CoaXPress CXP-12, 4 connections",
        "interface_connector": "DIN 1.0/2.3",
        "power_supply": "PoCXP / External 24 VDC",
        "power_consumption_w_typ": 8.1,
        "operating_temperature_housing_c": (0.0, 60.0),
        "body_dimensions_lwh_mm": (66.3, 80.6, 80.0),
        "lens_mount": "M42 Mount",
        "weight_g": 735.0,
        "camera_front_to_sensor_mm": 11.5,
        "step_path": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "BC-GMC65M12X4-M42.STEP",
            Path.home() / "cameras" / "BC-GMC65M12X4-M42.STEP",
        ),
    },
    "Japan Bopixel BC-GN25M12X4": {
        "manufacturer": "Japan Bopixel",
        "model": "BC-GN25M12X4",
        "product_code": "BC-GN25M12X4",
        "product_series": "BC-G CoaXPress",
        "status": "Available",
        # The Mono (BC-GM), Color (BC-GC) and NIR (BC-GN) variants share this
        # spec sheet + body; this entry is the NIR variant (the 'X' in the file
        # names is the M/C/N chroma letter).
        "datasheet": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "BC-Gx25M12X4_Spec_EN_ver02_bopixel.pdf",
            Path.home() / "cameras" / "BC-Gx25M12X4_Spec_EN_ver02_bopixel.pdf",
        ),
        "sensor_type": "Area scan",
        "chroma": "NIR",
        "spectrum": "Visible + NIR",
        "spectral_range_nm": (300.0, 1100.0),
        "resolution_px": (5120, 5120),
        "megapixels": 25.0,
        "sensor_model": "Gpixel GMAX0505",
        "sensor_architecture": "CMOS",
        "shutter": "Global shutter",
        "sensor_width_mm": 12.80,
        "sensor_height_mm": 12.80,
        "sensor_diagonal_mm": 18.10,
        "image_diameter_mm": 12.80,
        "pixel_size_um": (2.5, 2.5),
        "sensor_bit_depths": (8, 10),
        "pixel_formats": ("mono8", "mono10"),
        "max_frame_rate_fps": 150.3,
        "exposure_time_us_min": 3.0,
        "exposure_time_s_max": 2.0,
        "digital_interface": "CoaXPress CXP-12, 4 connections",
        "interface_connector": "micro-BNC",
        "power_supply": "PoCXP / External 24 VDC",
        "power_consumption_w_typ": 7.4,
        "operating_temperature_housing_c": (0.0, 60.0),
        "body_dimensions_lwh_mm": (45.5, 70.0, 70.0),
        "lens_mount": "C Mount",
        "weight_g": 455.0,
        # C-mount flange focal distance: the sensor sits 17.526 mm behind the
        # C-mount reference flange.
        "camera_front_to_sensor_mm": 17.526,
        "step_path": _preferred_existing_path(
            ATTACHMENT_CAMERA_DIR / "BC-GM(C)25M12X4.STEP",
            Path.home() / "cameras" / "BC-GM(C)25M12X4.STEP",
        ),
    },
}


# ----------------------------------------------------------------------------
# Imported-camera registry (attachment/Cameras/imported_cameras.json)
# ----------------------------------------------------------------------------
# Vendor cameras brought in via the folder importer
# (``KrakenOS.UI.services.camera_folder_import``) are persisted to a Filen-synced
# JSON sidecar next to the vendor assets rather than edited into the literal
# above.  Fold that registry into ``CAMERA_DATABASE`` at import so
# ``camera_model_for_step_path`` and the dropdown pick imported cameras up.
# Hand-authored built-ins always win: an imported camera only ever ADDS a new
# model, never overrides one.  The path must match
# ``camera_folder_import.IMPORTED_CAMERAS_JSON``.
IMPORTED_CAMERAS_JSON = ATTACHMENT_DIR / "Cameras" / "imported_cameras.json"

# The registry JSON stores these as lists / project-relative path strings; the
# built-in records carry tuples / absolute Paths.  Convert on the way in so an
# imported record is indistinguishable from a hand-authored one.
_IMPORTED_TUPLE_FIELDS = (
    "resolution_px",
    "pixel_size_um",
    "spectral_range_nm",
    "body_dimensions_lwh_mm",
    "sensor_bit_depths",
    "pixel_formats",
)
_IMPORTED_PATH_FIELDS = ("step_path", "datasheet")


def _merge_imported_cameras(path: Path | None = None) -> None:
    path = Path(path) if path is not None else IMPORTED_CAMERAS_JSON
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(payload, dict):
        return
    for name, record in payload.items():
        if not isinstance(record, dict):
            continue
        # bugs/0310: never let an imported record clobber a built-in camera, but
        # DO add/UPDATE imported entries. The old ``str(name) in CAMERA_DATABASE``
        # skip also blocked a *re-import* from updating an already-merged camera,
        # so entering the flange distance (0309) on a second import wrote the JSON
        # but never reached the running session (the sensor stayed at the mount
        # face). Keying the guard to the built-in snapshot lets refresh update.
        if str(name) in _BUILTIN_CAMERA_NAMES:
            continue
        merged = dict(record)
        for key in _IMPORTED_PATH_FIELDS:
            value = merged.get(key)
            if isinstance(value, str) and value:
                candidate = Path(value)
                merged[key] = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
        for key in _IMPORTED_TUPLE_FIELDS:
            if isinstance(merged.get(key), list):
                merged[key] = tuple(merged[key])
        CAMERA_DATABASE[str(name)] = merged


def refresh_imported_cameras() -> None:
    """Re-fold the imported-camera registry JSON into ``CAMERA_DATABASE``.

    The import-time merge already ran at module load; call this after the folder
    importer writes a new record so a *running* session picks the camera up
    (dropdown + ``camera_model_for_step_path``) without a restart.
    """
    _merge_imported_cameras()


# bugs/0310: snapshot the built-in camera names BEFORE folding the imported
# registry so a later ``refresh_imported_cameras`` can UPDATE an imported entry
# without ever overwriting a built-in camera of the same name.
_BUILTIN_CAMERA_NAMES = frozenset(CAMERA_DATABASE)

_merge_imported_cameras()


def camera_names() -> list[str]:
    return sorted(CAMERA_DATABASE)


def camera_record(name: str) -> dict[str, object] | None:
    record = CAMERA_DATABASE.get(str(name).strip())
    return dict(record) if isinstance(record, dict) else None


def camera_image_diameter_mm(name: str) -> float | None:
    record = camera_record(name)
    if record is None:
        return None
    value = record.get("image_diameter_mm")
    if value is not None:
        return float(value)
    width = record.get("sensor_width_mm")
    height = record.get("sensor_height_mm")
    if width is not None and height is not None:
        return max(float(width), float(height))
    return None


def camera_sensor_active_mm(name: str) -> tuple[float, float] | None:
    """Return the vendor active-sensor ``(width_mm, height_mm)`` or ``None``.

    This is the physical detector active area from the datasheet (e.g. the
    hr25MCX is 23.04 x 23.04 mm), used to draw the detector footprint at its
    real size instead of falling back to the image-surface clear aperture.
    """
    record = camera_record(name)
    if record is None:
        return None
    width = record.get("sensor_width_mm")
    height = record.get("sensor_height_mm")
    if width is None or height is None:
        return None
    try:
        w = float(width)
        h = float(height)
    except (TypeError, ValueError):
        return None
    if not (w > 0.0 and h > 0.0):
        return None
    return w, h


def camera_pixel_pitch_mm(name: str) -> tuple[float, float] | None:
    """Return the vendor pixel pitch ``(pitch_x_mm, pitch_y_mm)`` or ``None``.

    Converts the datasheet ``pixel_size_um`` (e.g. the hr25MCX / SVS 25MP is 4.50 um) to
    millimetres -- the cell size of the sensor's pixel lattice, used to draw the pixel grid
    a spot lands on.
    """
    record = camera_record(name)
    if record is None:
        return None
    pixel_size = record.get("pixel_size_um")
    if not (isinstance(pixel_size, (tuple, list)) and len(pixel_size) == 2):
        return None
    try:
        px = float(pixel_size[0])
        py = float(pixel_size[1])
    except (TypeError, ValueError):
        return None
    if not (px > 0.0 and py > 0.0):
        return None
    return px / 1000.0, py / 1000.0


def camera_resolution_px(name: str) -> tuple[int, int] | None:
    """Return the vendor sensor resolution ``(nx, ny)`` in pixels, or ``None``."""
    record = camera_record(name)
    if record is None:
        return None
    resolution = record.get("resolution_px")
    if not (isinstance(resolution, (tuple, list)) and len(resolution) == 2):
        return None
    try:
        nx = int(resolution[0])
        ny = int(resolution[1])
    except (TypeError, ValueError):
        return None
    if not (nx > 0 and ny > 0):
        return None
    return nx, ny


def camera_image_coverage_mm(name: str) -> tuple[float, float] | None:
    """Image-circle coverage for a camera's vendor sensor.

    Returns ``(image_diameter_mm, real_image_height_mm)`` where
    ``image_diameter_mm`` is the sensor **diagonal** -- the smallest image
    circle that fully covers the rectangular sensor, corners included -- and
    ``real_image_height_mm`` is its half, i.e. the max real image semi-height
    that lands the outermost field on the sensor corner. Selecting a camera
    auto-fills these so the image circle covers the sensor instead of merely
    inscribing it (sensor width = the inscribed circle, which clips the
    corners). ``None`` when the camera has no vendor sensor size.
    """
    sensor = camera_sensor_active_mm(name)
    if sensor is None:
        return None
    width, height = sensor
    diagonal = float((width * width + height * height) ** 0.5)
    if not (diagonal > 0.0):
        return None
    return diagonal, 0.5 * diagonal


def camera_model_for_step_path(step_path: str | Path | None) -> str | None:
    """Best-effort match of an imported camera STEP file back to a known camera
    model, so importing the vendor STEP couples the surrogate to that camera's
    sensor exactly like picking it from the dropdown (bug 0295 Stage 2:
    "after lens imported ... it must synchronize with the subsequent camera").

    Matches on the resolved absolute path first, then falls back to a
    case-insensitive filename match -- the vendor STEP filename is the stable
    identifier, so a synced/copied ``3D_CAD_HR25xCXP.STEP`` still resolves.
    Returns the camera name, or ``None`` when the STEP is not a known vendor
    camera (the raw body is then shown as-is, no sensor coupling).
    """
    if not step_path:
        return None
    candidate = Path(str(step_path)).expanduser()
    try:
        candidate_resolved = candidate.resolve()
    except OSError:
        candidate_resolved = candidate
    candidate_name = candidate.name.strip().lower()
    filename_match: str | None = None
    for name, record in CAMERA_DATABASE.items():
        db_path = record.get("step_path")
        if not db_path:
            continue
        db_path = Path(str(db_path)).expanduser()
        try:
            if db_path.resolve() == candidate_resolved:
                return name
        except OSError:
            pass
        if filename_match is None and db_path.name.strip().lower() == candidate_name:
            filename_match = name
    return filename_match


def camera_short_summary(name: str) -> str:
    record = camera_record(name)
    if record is None:
        return ""
    width = float(record.get("sensor_width_mm", 0.0))
    height = float(record.get("sensor_height_mm", 0.0))
    resolution = record.get("resolution_px")
    if isinstance(resolution, tuple) and len(resolution) == 2:
        res_text = f"{int(resolution[0])}x{int(resolution[1])}"
    else:
        res_text = "unknown resolution"
    pixel_size = record.get("pixel_size_um")
    if isinstance(pixel_size, tuple) and len(pixel_size) == 2:
        pixel_text = f"{float(pixel_size[0]):.3g}x{float(pixel_size[1]):.3g} um"
    else:
        pixel_text = "unknown pixel"
    return f"{width:.4g}x{height:.4g} mm, {res_text}, {pixel_text}"
