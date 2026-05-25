"""Measured surface error-map parsing and validation helpers."""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np


def _finite_numeric_array(value) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.size == 0:
        raise ValueError("empty array")
    if not np.all(np.isfinite(arr)):
        raise ValueError("contains non-finite values")
    return arr


def _error_map_space_scalar(value) -> float:
    arr = _finite_numeric_array(value).ravel()
    if arr.size == 1:
        spacing = float(arr[0])
    else:
        positive = arr[arr > 0.0]
        if positive.size != arr.size:
            raise ValueError("SPACE entries must be positive")
        if not np.allclose(positive, float(np.median(positive)), rtol=1e-6, atol=1e-12):
            raise ValueError("SPACE must be a scalar or equal x/y spacing values")
        spacing = float(np.median(positive))
    if spacing <= 0.0:
        raise ValueError("SPACE must be positive")
    return spacing


def _error_map_arrays(value) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("Error_map must be [X, Y, Z, SPACE]")
    x_values, y_values, z_values, space = value
    x_arr = _finite_numeric_array(x_values).astype(float, copy=False).ravel()
    y_arr = _finite_numeric_array(y_values).astype(float, copy=False).ravel()
    z_arr = _finite_numeric_array(z_values).astype(float, copy=False).ravel()
    if x_arr.size != y_arr.size or x_arr.size != z_arr.size:
        raise ValueError(f"X/Y/Z sample counts must match; got {x_arr.size}, {y_arr.size}, {z_arr.size}")
    if x_arr.size < 3:
        raise ValueError("at least three X/Y/Z samples are required")
    if not np.any(z_arr != 0.0):
        raise ValueError("Z samples are all zero; clear Error_map instead of storing a nominal zero map")
    return x_arr, y_arr, z_arr, _error_map_space_scalar(space)


def _error_map_literal(value) -> list[object]:
    x_arr, y_arr, z_arr, spacing = _error_map_arrays(value)
    return [x_arr.tolist(), y_arr.tolist(), z_arr.tolist(), spacing]


def _positive_unique_steps(values: np.ndarray) -> np.ndarray:
    unique_values = np.unique(np.asarray(values, dtype=float).ravel())
    if unique_values.size < 2:
        return np.array([], dtype=float)
    steps = np.diff(np.sort(unique_values))
    scale = max(float(np.max(np.abs(unique_values))), 1.0)
    return steps[steps > (scale * 1e-12)]


def _infer_error_map_spacing(x_values: np.ndarray, y_values: np.ndarray) -> float:
    steps = np.concatenate((_positive_unique_steps(x_values), _positive_unique_steps(y_values)))
    if steps.size == 0:
        return 1.0
    return float(np.median(steps))


def _error_map_from_xyz_columns(columns: np.ndarray, *, source: str) -> list[object]:
    arr = np.asarray(columns, dtype=float)
    if arr.ndim != 2 or arr.shape[1] < 3:
        raise ValueError(f"{source} must contain x, y, z columns")
    xyz = arr[:, :3]
    if not np.all(np.isfinite(xyz)):
        raise ValueError(f"{source} contains non-finite x/y/z values")
    spacing = _infer_error_map_spacing(xyz[:, 0], xyz[:, 1])
    return _error_map_literal([xyz[:, 0], xyz[:, 1], xyz[:, 2], spacing])


def _error_map_from_z_matrix(z_values: np.ndarray, *, source: str) -> list[object]:
    z_arr = np.asarray(z_values, dtype=float)
    if z_arr.ndim != 2:
        raise ValueError(f"{source} must be a 2D Z matrix")
    if min(z_arr.shape) < 2:
        raise ValueError(f"{source} Z matrix must have at least 2 rows and 2 columns")
    if not np.all(np.isfinite(z_arr)):
        raise ValueError(f"{source} contains non-finite Z values")
    y_indices, x_indices = np.indices(z_arr.shape, dtype=float)
    return _error_map_literal([x_indices.ravel(), y_indices.ravel(), z_arr.ravel(), 1.0])


def _npz_value(data: np.lib.npyio.NpzFile, *aliases: str):
    lower_keys = {str(key).strip().lower(): key for key in data.files}
    for alias in aliases:
        key = lower_keys.get(alias.lower())
        if key is not None:
            return data[key]
    return None


def _load_error_map_npz(path: Path) -> list[object]:
    with np.load(path, allow_pickle=False) as data:
        x_values = _npz_value(data, "X", "x", "x_values", "xvalues")
        y_values = _npz_value(data, "Y", "y", "y_values", "yvalues")
        z_values = _npz_value(data, "Z", "z", "z_values", "zvalues")
        if x_values is None or y_values is None or z_values is None:
            raise ValueError(".npz error maps must contain X, Y, and Z arrays")
        spacing = _npz_value(data, "SPACE", "space", "spacing", "pitch")
        if spacing is None:
            spacing = _infer_error_map_spacing(np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float))
        return _error_map_literal([x_values, y_values, z_values, spacing])


def _load_error_map_npy(path: Path) -> list[object]:
    arr = np.load(path, allow_pickle=False)
    if arr.dtype.fields:
        names = {str(name).strip().lower(): name for name in arr.dtype.names or ()}
        if {"x", "y", "z"}.issubset(names):
            columns = np.column_stack([arr[names["x"]], arr[names["y"]], arr[names["z"]]])
            return _error_map_from_xyz_columns(columns, source=path.name)
        raise ValueError(".npy structured arrays must have x, y, and z fields")
    data = np.asarray(arr, dtype=float)
    if data.ndim == 3 and data.shape[0] >= 3:
        spacing = _infer_error_map_spacing(data[0], data[1])
        return _error_map_literal([data[0], data[1], data[2], spacing])
    if data.ndim == 2 and data.shape[1] == 3:
        return _error_map_from_xyz_columns(data, source=path.name)
    if data.ndim == 2:
        return _error_map_from_z_matrix(data, source=path.name)
    raise ValueError(".npy error maps must be x/y/z columns, stacked X/Y/Z grids, or a 2D Z matrix")


def _first_data_line(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
    return ""


def _load_error_map_text(path: Path) -> list[object]:
    first_line = _first_data_line(path)
    if not first_line:
        raise ValueError(f"{path.name} is empty")
    delimiter = "," if "," in first_line else None
    has_header = bool(re.search(r"[A-Za-z]", first_line))
    if has_header:
        data = np.genfromtxt(path, delimiter=delimiter, names=True, comments="#", dtype=float, encoding=None)
        names = {str(name).strip().lower(): name for name in (data.dtype.names or ())}
        if not {"x", "y", "z"}.issubset(names):
            raise ValueError("headered error-map text files must include x, y, and z columns")
        if data.shape == ():
            data = np.asarray([data], dtype=data.dtype)
        columns = np.column_stack([data[names["x"]], data[names["y"]], data[names["z"]]])
        if "space" in names:
            spacing_values = np.asarray(data[names["space"]], dtype=float).ravel()
            spacing = spacing_values if spacing_values.size else _infer_error_map_spacing(columns[:, 0], columns[:, 1])
            return _error_map_literal([columns[:, 0], columns[:, 1], columns[:, 2], spacing])
        return _error_map_from_xyz_columns(columns, source=path.name)

    data = np.genfromtxt(path, delimiter=delimiter, comments="#", dtype=float)
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 1:
        if arr.size < 3:
            raise ValueError(f"{path.name} must contain x/y/z columns or a 2D Z matrix")
        arr = arr.reshape(1, -1)
    if arr.ndim == 2 and arr.shape[1] == 3:
        return _error_map_from_xyz_columns(arr, source=path.name)
    if arr.ndim == 2:
        return _error_map_from_z_matrix(arr, source=path.name)
    raise ValueError(f"{path.name} must contain x/y/z columns or a 2D Z matrix")


def _load_error_map_file(path: Path | str) -> list[object]:
    resolved = Path(path).expanduser()
    suffix = resolved.suffix.lower()
    if suffix == ".npz":
        return _load_error_map_npz(resolved)
    if suffix == ".npy":
        return _load_error_map_npy(resolved)
    if suffix in {".csv", ".txt", ".dat", ".tsv"}:
        return _load_error_map_text(resolved)
    raise ValueError(f"Unsupported error-map format: {resolved.suffix or resolved.name}")


def _error_map_summary(value) -> str:
    try:
        x_arr, y_arr, z_arr, spacing = _error_map_arrays(value)
    except Exception as exc:
        return f"Invalid Error_map: {exc}"
    z_rms = float(np.sqrt(np.mean(np.square(z_arr))))
    return (
        f"{x_arr.size} samples; "
        f"X {float(np.min(x_arr)):.6g}..{float(np.max(x_arr)):.6g} mm, "
        f"Y {float(np.min(y_arr)):.6g}..{float(np.max(y_arr)):.6g} mm, "
        f"Z {float(np.min(z_arr)):.6g}..{float(np.max(z_arr)):.6g} mm, "
        f"RMS {z_rms:.6g} mm, SPACE {spacing:.6g} mm."
    )


def _validate_error_map(value) -> list[str]:
    try:
        _error_map_arrays(value)
    except Exception as exc:
        return [f"Error_map contains invalid data: {exc}."]
    return []
