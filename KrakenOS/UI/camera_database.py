"""Camera database used by the layout editor.

The editor uses ``image_diameter_mm`` as the full image plane size when a camera
is selected.  Store the intended 2D layout dimension there explicitly; for
rectangular sensors the fallback is the larger active sensor side, not the
diagonal.
"""

from __future__ import annotations

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
}


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
