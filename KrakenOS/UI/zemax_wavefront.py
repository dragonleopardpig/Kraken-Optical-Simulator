from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


_FLOAT_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")


@dataclass(frozen=True)
class ZemaxWavefrontMap:
    path: str
    wavelength_um: float
    values_waves: np.ndarray
    raw_units: str
    header: tuple[str, ...] = ()

    @property
    def shape(self) -> tuple[int, int]:
        return tuple(int(value) for value in self.values_waves.shape)

    @property
    def values_nm(self) -> np.ndarray:
        return np.asarray(self.values_waves, dtype=float) * float(self.wavelength_um) * 1000.0

    @property
    def finite_values_waves(self) -> np.ndarray:
        values = np.asarray(self.values_waves, dtype=float)
        return values[np.isfinite(values)]

    @property
    def pv_waves(self) -> float:
        finite = self.finite_values_waves
        return float(np.nanmax(finite) - np.nanmin(finite)) if finite.size else float("nan")

    @property
    def rms_waves(self) -> float:
        finite = self.finite_values_waves
        if not finite.size:
            return float("nan")
        centered = finite - float(np.nanmean(finite))
        return float(np.sqrt(np.nanmean(centered * centered)))


def _decode_text(path: Path) -> str:
    data = path.read_bytes()
    encodings = ("utf-16", "utf-16le", "utf-8-sig", "utf-8", "latin-1")
    for encoding in encodings:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if text.count("\x00") > max(2, len(text) // 20):
            continue
        return text
    return data.decode("latin-1", errors="replace")


def _parse_wavelength_um(lines: list[str]) -> float | None:
    pattern = re.compile(
        r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?)\s*"
        r"(?P<unit>u?m|µm|μm|micron|microns|nanometer|nanometers|nm)\b",
        re.IGNORECASE,
    )
    for line in lines:
        if "wave" not in line.lower():
            continue
        match = pattern.search(line)
        if not match:
            continue
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit in {"nm", "nanometer", "nanometers"}:
            return value / 1000.0
        return value
    return None


def _parse_grid_size(lines: list[str]) -> tuple[int, int] | None:
    patterns = (
        re.compile(r"(?:pupil\s+)?grid\s+size\D+(\d+)\D+by\D+(\d+)", re.IGNORECASE),
        re.compile(r"(\d+)\s+by\s+(\d+)", re.IGNORECASE),
    )
    for line in lines:
        lowered = line.lower()
        if "grid" not in lowered and "pupil" not in lowered:
            continue
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return int(match.group(1)), int(match.group(2))
    return None


def _raw_units_from_header(lines: list[str]) -> str:
    unit_lines = []
    for line in lines[:80]:
        lowered = line.lower()
        if "wavelength" in lowered or re.search(r"\blambda\b", lowered):
            continue
        if re.search(r"\b(data|units?|values?|opd|map)\b", lowered):
            unit_lines.append(lowered)
    unit_header = "\n".join(unit_lines)
    if re.search(r"\b(waves?|fringes?)\b", unit_header):
        return "waves"
    if re.search(r"\b(nm|nanometer|nanometers)\b", unit_header):
        return "nm"
    return "waves"


def _numeric_tokens(line: str) -> list[float]:
    stripped = line.strip()
    if not stripped:
        return []
    if not re.match(r"^[+\-.\d]", stripped):
        return []
    return [float(match.group(0)) for match in _FLOAT_RE.finditer(stripped)]


def _parse_numeric_grid(lines: list[str], grid_size: tuple[int, int]) -> np.ndarray:
    rows, cols = (int(grid_size[0]), int(grid_size[1]))
    data_rows: list[list[float]] = []
    started = False
    for line in lines:
        tokens = _numeric_tokens(line)
        if not started:
            if len(tokens) >= min(cols, 2):
                started = True
            else:
                continue
        if started:
            if len(tokens) >= min(cols, 2):
                data_rows.append(tokens)
                continue
            if data_rows:
                break
    if not data_rows:
        raise ValueError("Could not find Zemax Wavefront Map data rows.")
    if len(data_rows) >= rows and all(len(row) >= cols for row in data_rows[:rows]):
        grid = np.asarray([row[:cols] for row in data_rows[:rows]], dtype=float)
    else:
        flat = np.asarray([value for row in data_rows for value in row], dtype=float)
        expected = rows * cols
        if flat.size < expected:
            raise ValueError(f"Expected {expected} wavefront values, found {flat.size}.")
        grid = flat[:expected].reshape((rows, cols))
    return np.flipud(grid)


def load_zemax_wavefront_map(path: str | Path) -> ZemaxWavefrontMap:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f"Zemax Wavefront Map file not found: {file_path}")
    text = _decode_text(file_path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    wavelength_um = _parse_wavelength_um(lines)
    if wavelength_um is None or not np.isfinite(wavelength_um) or wavelength_um <= 0.0:
        raise ValueError("Could not find a positive wavelength in the Zemax Wavefront Map header.")
    grid_size = _parse_grid_size(lines)
    if grid_size is None:
        raise ValueError("Could not find pupil grid size in the Zemax Wavefront Map header.")
    raw_values = _parse_numeric_grid(lines, grid_size)
    raw_units = _raw_units_from_header(lines)
    if raw_units == "nm":
        values_waves = raw_values / (float(wavelength_um) * 1000.0)
    else:
        values_waves = raw_values
    return ZemaxWavefrontMap(
        path=str(file_path),
        wavelength_um=float(wavelength_um),
        values_waves=np.asarray(values_waves, dtype=float),
        raw_units=raw_units,
        header=tuple(lines[:80]),
    )


def sample_wavefront_grid(values: np.ndarray, x_norm: np.ndarray, y_norm: np.ndarray) -> np.ndarray:
    grid = np.asarray(values, dtype=float)
    x = np.asarray(x_norm, dtype=float).ravel()
    y = np.asarray(y_norm, dtype=float).ravel()
    if grid.ndim != 2 or min(grid.shape) < 2:
        return np.full_like(x, np.nan, dtype=float)
    rows, cols = grid.shape
    u = (np.clip(x, -1.0, 1.0) + 1.0) * 0.5 * (cols - 1)
    v = (np.clip(y, -1.0, 1.0) + 1.0) * 0.5 * (rows - 1)
    u0 = np.floor(u).astype(int)
    v0 = np.floor(v).astype(int)
    u1 = np.clip(u0 + 1, 0, cols - 1)
    v1 = np.clip(v0 + 1, 0, rows - 1)
    u0 = np.clip(u0, 0, cols - 1)
    v0 = np.clip(v0, 0, rows - 1)
    du = u - u0
    dv = v - v0
    q00 = grid[v0, u0]
    q10 = grid[v0, u1]
    q01 = grid[v1, u0]
    q11 = grid[v1, u1]
    weights = np.stack(((1.0 - du) * (1.0 - dv), du * (1.0 - dv), (1.0 - du) * dv, du * dv), axis=0)
    samples = np.stack((q00, q10, q01, q11), axis=0)
    finite = np.isfinite(samples)
    weighted = np.where(finite, samples * weights, 0.0)
    total_weight = np.where(finite, weights, 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        result = weighted.sum(axis=0) / total_weight
    result[total_weight <= 0.0] = np.nan
    return result


def normalized_pupil_coordinates(x_pupil: np.ndarray, y_pupil: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x_pupil, dtype=float).ravel()
    y = np.asarray(y_pupil, dtype=float).ravel()
    x_scale = float(np.nanmax(np.abs(x))) if x.size else 1.0
    y_scale = float(np.nanmax(np.abs(y))) if y.size else 1.0
    if not np.isfinite(x_scale) or x_scale <= 1e-12:
        x_scale = 1.0
    if not np.isfinite(y_scale) or y_scale <= 1e-12:
        y_scale = 1.0
    return np.clip(x / x_scale, -1.0, 1.0), np.clip(y / y_scale, -1.0, 1.0)
