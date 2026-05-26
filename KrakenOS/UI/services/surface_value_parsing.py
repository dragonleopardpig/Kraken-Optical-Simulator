"""Pure surface value parsing and native-variable helpers."""

from __future__ import annotations

import ast
import re

import numpy as np


def _coerce_opt_flag(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() in {"*", "1", "true", "True", "yes", "on"}


def _coerce_bounds(value) -> tuple[float, float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (float(value[0]), float(value[1]))
    return None


def _compact_surface_attr_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _normalize_native_variable_name(value: object) -> str:
    text = str(value).strip()
    compact = _compact_surface_attr_name(text)
    aliases = {
        "r": "Rc",
        "rc": "Rc",
        "radius": "Rc",
        "curvature": "Rc",
        "thick": "Thickness",
        "thickness": "Thickness",
        "k": "k",
        "conic": "k",
        "conicconstant": "k",
    }
    return aliases.get(compact, text)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _compact_surface_attr_name(value)
        if not key or key in seen:
            continue
        ordered.append(value)
        seen.add(key)
    return ordered


def _native_variable_names(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text[0:1] in {"[", "(", "{"}:
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                parsed = None
            if parsed is not None and parsed is not value:
                return _native_variable_names(parsed)
        raw_parts = re.split(r"[\s,;]+", text)
    elif isinstance(value, (list, tuple, set)):
        names: list[str] = []
        for item in value:
            names.extend(_native_variable_names(item))
        return _dedupe_preserve_order(names)
    else:
        raw_parts = [str(value)]
    names = []
    for part in raw_parts:
        name = _normalize_native_variable_name(part)
        if _compact_surface_attr_name(name) in {"", "none", "empty", "enpty"}:
            continue
        names.append(name)
    return _dedupe_preserve_order(names)


def _dedupe_float_values(values: list[float], *, decimals: int = 9) -> list[float]:
    ordered: list[float] = []
    seen: set[float] = set()
    for value in values:
        numeric = float(value)
        if not np.isfinite(numeric):
            continue
        key = round(numeric, decimals)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(numeric)
    return ordered


def _parse_float_sequence_text(text: str) -> list[float]:
    raw = str(text or "").strip()
    if not raw:
        return []
    parsed = None
    if raw[0:1] in {"[", "(", "{"}:
        try:
            parsed = ast.literal_eval(raw)
        except Exception:
            parsed = None
    if parsed is not None:
        if isinstance(parsed, (int, float)):
            return [float(parsed)]
        if isinstance(parsed, (list, tuple, set)):
            return [float(item) for item in parsed]
        raise ValueError("Expected a number list.")

    values: list[float] = []
    for token in re.split(r"[\s,;]+", raw):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            parts = [part.strip() for part in token.split(":") if part.strip()]
            if len(parts) not in {2, 3}:
                raise ValueError(f"Invalid range token: {token!r}")
            start = float(parts[0])
            stop = float(parts[1])
            step = float(parts[2]) if len(parts) == 3 else (1.0 if stop >= start else -1.0)
            if abs(step) <= 1e-12:
                raise ValueError("Range step cannot be zero.")
            direction = 1.0 if step > 0 else -1.0
            current = start
            guard = 0
            while (current - stop) * direction <= 1e-9:
                values.append(float(current))
                current += step
                guard += 1
                if guard > 1000:
                    raise ValueError("Range expands to too many values.")
            continue
        values.append(float(token))
    return _dedupe_float_values(values)


def _format_float_sequence(values: object) -> str:
    try:
        sequence = _parse_float_sequence_text(str(values)) if isinstance(values, str) else [float(item) for item in values]
    except Exception:
        return ""
    return ", ".join(f"{float(value):g}" for value in sequence)


def _native_variable_matches(candidate: object, parameter: object) -> bool:
    return (
        _compact_surface_attr_name(_normalize_native_variable_name(candidate))
        == _compact_surface_attr_name(_normalize_native_variable_name(parameter))
    )
