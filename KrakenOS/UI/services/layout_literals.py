"""Literal conversion helpers for saved layout serialization."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.custom_surfaces import encode_custom_surface_value


_UNSERIALIZABLE_LAYOUT_VALUE = object()


def _layout_literal_value(value):
    """Return a Python-literal representation, or a sentinel when unsupported."""
    encoded_custom = encode_custom_surface_value(value)
    if encoded_custom is not None and encoded_custom is not value:
        return _layout_literal_value(encoded_custom)
    if value is None or isinstance(value, (str, int, float, bool, np.floating, np.integer)):
        return value
    if isinstance(value, np.ndarray):
        return np.asarray(value).tolist()
    if isinstance(value, (list, tuple)):
        converted = []
        for item in value:
            literal = _layout_literal_value(item)
            if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
                return _UNSERIALIZABLE_LAYOUT_VALUE
            converted.append(literal)
        return converted
    if isinstance(value, dict):
        converted = {}
        for key, item in value.items():
            literal = _layout_literal_value(item)
            if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
                return _UNSERIALIZABLE_LAYOUT_VALUE
            converted[str(key)] = literal
        return converted
    return _UNSERIALIZABLE_LAYOUT_VALUE
