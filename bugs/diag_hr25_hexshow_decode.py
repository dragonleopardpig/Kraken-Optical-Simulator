"""Feasibility probe: can the hr25MCX Allied Vision datasheet be decoded by
adding HEX-STRING show support (`<..>Tj` and hex elements in `[..]TJ`) to the
existing per-font ToUnicode machinery? If real spec words fall out, a small
extractor extension recovers the whole table.

Run: .devenv/state/venv/bin/python bugs/diag_hr25_hexshow_decode.py
"""
from __future__ import annotations

import re
import zlib
from pathlib import Path

from KrakenOS.UI.services.datasheet_prescription_import import (
    _font_cmaps,
    _object_streams,
    _inflate,
)

PDF = Path("attachment/Cameras/hr25MCX_Datasheet.pdf")

# font switch, hex-string show, literal show, TJ array
_TOKEN = re.compile(
    rb"/(F\d+)\s+[\d.]+\s+Tf"
    rb"|<([0-9A-Fa-f\s]+)>\s*Tj"
    rb"|\((?:[^()\\]|\\.)*\)\s*Tj"
    rb"|\[(?:[^\]]*)\]\s*TJ",
    re.S,
)
_TJ_HEX = re.compile(rb"<([0-9A-Fa-f\s]+)>|(-?\d+)")


def decode_hex(hexbytes: bytes, cmap: dict[int, str]) -> str:
    h = re.sub(rb"\s+", b"", hexbytes)
    out = []
    for i in range(0, len(h) - 3, 4):
        code = int(h[i:i + 4], 16)
        out.append(cmap.get(code, ""))
    return "".join(out)


def main() -> int:
    data = PDF.read_bytes()
    objs = _object_streams(data)
    cmaps = _font_cmaps(data, objs)
    print("fonts with ToUnicode CMap:", {k: len(v) for k, v in cmaps.items()})
    chunks: list[str] = []
    for raw in objs.values():
        stream = _inflate(raw)
        if b"Tf" not in stream or (b"Tj" not in stream and b"TJ" not in stream):
            continue
        current: dict[int, str] = {}
        for tok in _TOKEN.finditer(stream):
            whole = tok.group(0)
            if tok.group(1) is not None:  # font switch
                current = cmaps.get(tok.group(1).decode(), {})
            elif tok.group(2) is not None:  # hex Tj
                chunks.append(decode_hex(tok.group(2), current))
            elif whole.endswith(b"Tj"):  # literal Tj
                s = re.search(rb"\((.*)\)\s*Tj", whole, re.S)
                if s:
                    chunks.append(s.group(1).decode("latin-1", "replace"))
            elif whole.endswith(b"TJ"):
                arr = re.search(rb"\[(.*)\]\s*TJ", whole, re.S).group(1)
                for el in _TJ_HEX.finditer(arr):
                    if el.group(1) is not None:
                        chunks.append(decode_hex(el.group(1), current))
                    elif el.group(2) is not None and int(el.group(2)) < -90:
                        chunks.append(" ")
    text = "".join(chunks)
    print(f"[{len(text)} chars decoded]")
    print(text[:3000])
    # spot-check the fields the camera record needs
    for probe in ("Sensor size", "23.04", "Pixel size", "4.50", "5120", "5,120",
                  "M58", "hr25MCX", "Resolution", "Weight", "420"):
        print(f"  {'FOUND' if probe in text else 'miss ':5} {probe!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
