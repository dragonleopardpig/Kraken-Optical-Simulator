"""Validate saved-layout literal serialization stays editor-independent."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.custom_surfaces import extra_radial_sine
from KrakenOS.UI.services.layout_literals import _UNSERIALIZABLE_LAYOUT_VALUE, _layout_literal_value


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures: list[str] = []

    literal = _layout_literal_value({"a": np.asarray([1, 2]), 3: (True, None)})
    if literal != {"a": [1, 2], "3": [True, None]}:
        failures.append(f"Unexpected nested literal conversion: {literal!r}")

    custom_literal = _layout_literal_value([extra_radial_sine, np.asarray([4.0, 0.25])])
    if custom_literal != {"kind": "extra_surface", "preset": "radial_sine", "params": [4.0, 0.25]}:
        failures.append(f"Unexpected custom ExtraData literal conversion: {custom_literal!r}")

    if _layout_literal_value(object()) is not _UNSERIALIZABLE_LAYOUT_VALUE:
        failures.append("Unsupported objects must return the unserializable sentinel.")

    writer_source = (PROJECT_ROOT / "KrakenOS/UI/services/layout_file_writer.py").read_text(encoding="utf-8")
    forbidden_writer_tokens = (
        "def _layout_module(",
        "from KrakenOS.UI import layout_editor",
        "_layout_module()",
        "le.",
    )
    for token in forbidden_writer_tokens:
        if token in writer_source:
            failures.append(f"layout_file_writer.py still depends on layout_editor via {token!r}")

    layout_source = (PROJECT_ROOT / "KrakenOS/UI/layout_editor.py").read_text(encoding="utf-8")
    if "def _layout_literal_value(" in layout_source:
        failures.append("_layout_literal_value must stay in services/layout_literals.py")
    if "_UNSERIALIZABLE_LAYOUT_VALUE = object()" in layout_source:
        failures.append("_UNSERIALIZABLE_LAYOUT_VALUE must stay in services/layout_literals.py")

    if failures:
        print("Layout literal contract validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Layout literal contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
