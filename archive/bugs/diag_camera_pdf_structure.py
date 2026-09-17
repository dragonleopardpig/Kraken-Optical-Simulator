"""Probe why the stdlib extractor recovers no text from the camera datasheets:
list font-resource names, the `Tf` font-switch names actually used in content
streams, ToUnicode presence, and a sample decoded show-string width.

Run: .devenv/state/venv/bin/python bugs/diag_camera_pdf_structure.py
"""
from __future__ import annotations

import re
import zlib
from pathlib import Path

CAMERAS = Path("attachment/Cameras")
SHEETS = ["hr25MCX_Datasheet.pdf", "BC-Gx25M12X4_Spec_EN_ver02_bopixel.pdf"]

_OBJ_RE = re.compile(rb"\b(\d+) 0 obj\b(.*?)\bendobj", re.S)
_STREAM_RE = re.compile(rb"stream\r?\n", re.S)


def objects(data: bytes) -> dict[int, bytes]:
    out = {}
    for m in _OBJ_RE.finditer(data):
        body = m.group(2)
        s = _STREAM_RE.search(body)
        if s is None:
            continue
        raw = body[s.end():]
        end = raw.find(b"endstream")
        if end >= 0:
            raw = raw[:end]
        out[int(m.group(1))] = raw.rstrip(b"\r\n")
    return out


def inflate(raw: bytes) -> bytes:
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def main() -> int:
    for name in SHEETS:
        path = CAMERAS / name
        print("=" * 78)
        print(name)
        print("=" * 78)
        data = path.read_bytes()
        n_obj = len(_OBJ_RE.findall(data))
        print(f"classic 'N 0 obj' objects: {n_obj}")
        print(f"/ObjStm: {data.count(b'/ObjStm')}  XRef stream /Type /XRef: {data.count(b'/XRef')}")
        # Font resource names anywhere
        font_names = sorted(set(re.findall(rb"/([A-Za-z][A-Za-z0-9_+.-]*)\s+\d+\s+0\s+R",
                                           b" ".join(re.findall(rb"/Font\s*<<(.*?)>>", data, re.S)))))
        print("Font resource names in /Font dicts:", [n.decode(errors='replace') for n in font_names][:20])
        # Tf operators used in content streams
        objs = objects(data)
        tf_names = set()
        tj_widths = []
        sample = b""
        for raw in objs.values():
            stream = inflate(raw)
            if b"Tf" not in stream:
                continue
            for m in re.finditer(rb"/([A-Za-z0-9_+.-]+)\s+[\d.]+\s+Tf", stream):
                tf_names.add(m.group(1))
            if (b"Tj" in stream or b"TJ" in stream) and not sample:
                # grab a sample slice around first BT
                bt = stream.find(b"BT")
                sample = stream[bt:bt + 400] if bt >= 0 else stream[:400]
            for m in re.finditer(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", stream):
                tj_widths.append(len(m.group(1)))
        print("Tf font-switch names in content:", sorted(n.decode(errors='replace') for n in tf_names)[:20])
        print("num (..)Tj show-strings:", len(tj_widths), " sample lengths:", tj_widths[:12])
        print("--- sample content-stream slice ---")
        print(sample.decode("latin-1", errors="replace"))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
