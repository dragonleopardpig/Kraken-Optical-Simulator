"""Camera database used by the layout editor.

The editor uses ``image_diameter_mm`` as the full image plane size when a camera
is selected.  Store the intended 2D layout dimension there explicitly; for
rectangular sensors the fallback is the larger active sensor side, not the
diagonal.
"""

from __future__ import annotations

from pathlib import Path


CAMERA_NONE_LABEL = "None"

CAMERA_DATABASE: dict[str, dict[str, object]] = {
    "Allied Vision hr25MCX": {
        "manufacturer": "Allied Vision",
        "model": "hr25MCX",
        "product_code": "F004053",
        "product_series": "HR CoaXPress",
        "status": "Available",
        "datasheet": Path.home() / "cameras" / "hr25MCX_Datasheet.pdf",
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
        "step_path": Path.home() / "cameras" / "3D_CAD_HR25xCXP.STEP",
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
