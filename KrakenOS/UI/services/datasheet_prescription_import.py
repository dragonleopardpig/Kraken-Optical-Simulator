"""Datasheet-PDF -> first-order cardinals (Path C of the folder importer).

Most vendors ship a **datasheet PDF** but no Zemax ``.zmx`` prescription and no
Black-Box ``System/Prescription Data`` dump.  This module recovers the first-order
cardinals from the datasheet alone so a paraxial surrogate can still be built.

The Schneider / PYRITE spec table lists, per lens::

    f'eff [mm]   82.39     <- effective focal length (EFL)
    SF   [mm]   -60.14     <- first vertex  -> front focal point
    S'F' [mm]    60.14     <- last  vertex  -> back  focal point
    HH'  [mm]    -1.31     <- inter-principal-plane distance (cross-check)
    d [mm] Σ     43.19     <- first-to-last vertex span (the two-group "span")
    F/5.6 ... F/45         <- F-number range (min = fastest)
    Max. sensor size [mm]  100   <- image-circle diameter

Because SF, S'F' and f'eff are all present, BOTH principal planes are recovered
exactly (``ppa = SF + f'eff``; ``ppp = S'F' - f'eff``), so Path C can use the same
exact two-group solve as the readable-``.zmx`` Path A -- a strict improvement over
the EFL+span-only symmetric Black-Box Path B.

The PDF text extractor is **pure stdlib** (``re`` + ``zlib``): the Schneider PDFs
embed subset CID fonts (``MPDFAA+`` prefixes) whose 2-byte glyph codes need each
font's own ``ToUnicode`` CMap.  A single merged CMap collides across fonts, so the
decoder tracks the active ``/Fn Tf`` and switches CMaps per font.  The content
streams are FlateDecode (zlib); the ToUnicode CMaps themselves are stored
uncompressed, so ``zlib.decompress`` failing is expected -> use the raw bytes.

No third-party dependency is introduced (the tooling rule: must work for any
GitHub user with the stock environment).
"""

from __future__ import annotations

import math
import re
import zlib
from dataclasses import dataclass
from pathlib import Path


# ----------------------------------------------------------------------------
# Pure-stdlib PDF text extraction (per-font ToUnicode)
# ----------------------------------------------------------------------------
_OBJ_RE = re.compile(rb"\b(\d+) 0 obj\b(.*?)\bendobj", re.S)
_STREAM_RE = re.compile(rb"stream\r?\n", re.S)
_FONT_DICT_RE = re.compile(rb"/Font\s*<<(.*?)>>", re.S)
_FONT_REF_RE = re.compile(rb"/([A-Za-z0-9_+.-]+)\s+(\d+)\s+0\s+R")
_TOUNICODE_RE = re.compile(rb"/ToUnicode\s+(\d+)\s+0\s+R")
_BFCHAR_RE = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE_RE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_HEXPAIR_RE = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
_HEXTRIP_RE = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
# One content-token: a font switch, a (..)Tj / <..>Tj show, or a [..]TJ show.
# Font resource names are generalised beyond the Schneider ``/F\d+`` template so
# vendor camera datasheets (Allied Vision ``/F9../F12``, Bopixel ``/C2_0``/``/TT0``)
# switch CMaps too, and shows may be literal ``(..)`` OR hex ``<..>`` strings
# (Allied Vision camera sheets use hex shows exclusively).
_CONTENT_TOKEN_RE = re.compile(
    rb"/([A-Za-z0-9_+.-]+)\s+[\d.]+\s+Tf"
    rb"|<([0-9A-Fa-f\s]+)>\s*Tj"
    rb"|\((?:[^()\\]|\\.)*\)\s*Tj"
    rb"|\[(?:[^\]]*)\]\s*TJ",
    re.S,
)
_TJ_ELEMENT_RE = re.compile(rb"\((.*?)(?<!\\)\)|<([0-9A-Fa-f\s]+)>|(-?\d+)", re.S)


def _object_streams(data: bytes) -> dict[int, bytes]:
    """Map ``obj number -> raw stream bytes`` for every ``N 0 obj ... endobj`` that
    carries a ``stream``.  Raw (still compressed / still encoded) on purpose."""
    out: dict[int, bytes] = {}
    for match in _OBJ_RE.finditer(data):
        body = match.group(2)
        stream = _STREAM_RE.search(body)
        if stream is None:
            continue
        raw = body[stream.end():]
        end = raw.find(b"endstream")
        if end >= 0:
            raw = raw[:end]
        out[int(match.group(1))] = raw.rstrip(b"\r\n")
    return out


def _inflate(raw: bytes) -> bytes:
    """FlateDecode a stream; the ToUnicode CMaps are stored uncompressed, so a
    zlib failure means the bytes are already plaintext -- return them as-is."""
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def _parse_cmap(stream: bytes) -> dict[int, str]:
    """A ToUnicode CMap: ``bfchar`` single mappings + ``bfrange`` contiguous runs,
    each ``<glyph-code> -> <UTF-16BE>``."""
    cmap: dict[int, str] = {}
    for block in _BFCHAR_RE.finditer(stream):
        for pair in _HEXPAIR_RE.finditer(block.group(1)):
            src = int(pair.group(1), 16)
            dst = pair.group(2)
            cmap[src] = "".join(chr(int(dst[i:i + 4], 16)) for i in range(0, len(dst), 4))
    for block in _BFRANGE_RE.finditer(stream):
        for trip in _HEXTRIP_RE.finditer(block.group(1)):
            lo = int(trip.group(1), 16)
            hi = int(trip.group(2), 16)
            base = int(trip.group(3)[:4], 16)
            for offset, code in enumerate(range(lo, hi + 1)):
                cmap[code] = chr(base + offset)
    return cmap


def _font_cmaps(data: bytes, objs: dict[int, bytes]) -> dict[str, dict[int, str]]:
    """``/Fn -> ToUnicode CMap`` for every font resource.  Font resource names
    (``/F1``../``/F7``) are global/stable across the Schneider template, so a single
    name->cmap table serves all content streams."""
    name_to_cmap: dict[str, dict[int, str]] = {}
    for font_dict in _FONT_DICT_RE.finditer(data):
        for ref in _FONT_REF_RE.finditer(font_dict.group(1)):
            name = ref.group(1).decode()
            font_obj = int(ref.group(2))
            font_body = b""
            found = re.search(rb"\b%d 0 obj\b(.*?)\bendobj" % font_obj, data, re.S)
            if found is not None:
                font_body = found.group(1)
            tunicode = _TOUNICODE_RE.search(font_body)
            if tunicode is None:
                continue
            cmap = _parse_cmap(_inflate(objs.get(int(tunicode.group(1)), b"")))
            if cmap:
                name_to_cmap[name] = cmap
    return name_to_cmap


def _decode_show(raw: bytes, cmap: dict[int, str]) -> str:
    """Decode one show-string's 2-byte glyph codes through the active CMap."""
    raw = raw.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
    return "".join(cmap.get(raw[i] * 256 + raw[i + 1], "") for i in range(0, len(raw) - 1, 2))


def _decode_hex_show(hex_bytes: bytes, cmap: dict[int, str]) -> str:
    """Decode a hex show-string ``<0031 0052 ...>`` (whitespace tolerated) as
    2-byte CID codes through the active CMap.  Camera datasheets (Allied Vision,
    Bopixel) emit their text this way rather than as literal ``(..)`` strings."""
    packed = re.sub(rb"\s+", b"", hex_bytes)
    return "".join(
        cmap.get(int(packed[i:i + 4], 16), "") for i in range(0, len(packed) - 3, 4)
    )


def _decode_content(stream: bytes, name_to_cmap: dict[str, dict[int, str]]) -> str:
    """Walk a content stream, switching CMaps on ``/Fn Tf`` and decoding every
    ``Tj`` / ``TJ`` show; a large negative ``TJ`` advance renders as a space."""
    out: list[str] = []
    current: dict[int, str] = {}
    for token in _CONTENT_TOKEN_RE.finditer(stream):
        text = token.group(0)
        font = re.match(rb"/([A-Za-z0-9_+.-]+)\s+[\d.]+\s+Tf", text)
        if font is not None:
            current = name_to_cmap.get(font.group(1).decode(), {})
            continue
        stripped = text.rstrip()
        if stripped.endswith(b"Tj"):
            hex_show = re.match(rb"<([0-9A-Fa-f\s]+)>\s*Tj", text)
            if hex_show is not None:
                out.append(_decode_hex_show(hex_show.group(1), current))
            else:
                show = re.search(rb"\((.*)\)\s*Tj", text, re.S)
                if show is not None:
                    out.append(_decode_show(show.group(1), current))
        elif stripped.endswith(b"TJ"):
            array = re.search(rb"\[(.*)\]\s*TJ", text, re.S).group(1)
            for element in _TJ_ELEMENT_RE.finditer(array):
                if element.group(1) is not None:
                    out.append(_decode_show(element.group(1), current))
                elif element.group(2) is not None:
                    out.append(_decode_hex_show(element.group(2), current))
                elif element.group(3) is not None and int(element.group(3)) < -90:
                    out.append(" ")
    return "".join(out)


def extract_pdf_text(path: str | Path) -> str:
    """Best-effort plain text from a (subset-CID-font) vendor datasheet PDF.

    Pure stdlib; returns ``""`` on any failure so callers degrade gracefully.
    """
    try:
        data = Path(path).read_bytes()
    except Exception:
        return ""
    if b"%PDF" not in data[:1024]:
        return ""
    try:
        objs = _object_streams(data)
        name_to_cmap = _font_cmaps(data, objs)
        chunks: list[str] = []
        for raw in objs.values():
            stream = _inflate(raw)
            if b"Tf" in stream and (b"Tj" in stream or b"TJ" in stream):
                chunks.append(_decode_content(stream, name_to_cmap))
        return "\n".join(chunks)
    except Exception:
        return ""


# ----------------------------------------------------------------------------
# Cardinal scrape
# ----------------------------------------------------------------------------
@dataclass
class DatasheetCardinals:
    """First-order cardinals scraped from a vendor datasheet PDF.

    ``effl`` is the only hard requirement.  When both ``front_focal`` (SF) and
    ``back_focal`` (S'F') are present the principal planes -- and therefore an
    exact two-group solve -- are available (:pyattr:`has_principal_planes`).
    """

    effl: float | None = None
    front_focal: float | None = None   # SF   : first vertex -> front focal point (<0)
    back_focal: float | None = None    # S'F' : last  vertex -> back  focal point (>0)
    hh: float | None = None            # HH'  : inter-principal-plane distance
    span: float | None = None          # Sigma d : first-to-last vertex distance
    fno: float | None = None           # fastest F-number (min of the range)
    image_circle: float | None = None  # Max. sensor size = image-circle diameter
    magnification: float | None = None  # nominal transverse magnification (signed, <0)
    mag_label: str | None = None       # the "1.0x" / "0.5x-2.0x" title token
    title: str | None = None
    lens_id: str | None = None

    @property
    def ppa(self) -> float | None:
        """Front datum -> front principal plane H (``SF + f'eff``)."""
        if self.front_focal is None or self.effl is None:
            return None
        return self.front_focal + self.effl

    @property
    def ppp(self) -> float | None:
        """Rear principal plane H' -> rear datum, negated (``S'F' - f'eff``)."""
        if self.back_focal is None or self.effl is None:
            return None
        return self.back_focal - self.effl

    @property
    def has_principal_planes(self) -> bool:
        return self.ppa is not None and self.ppp is not None

    @property
    def object_mode(self) -> str:
        m = self.magnification
        if m is None or abs(m) < 1e-6 or not math.isfinite(m):
            return "Infinity"
        return "Finite"

    @property
    def hh_from_cardinals(self) -> float | None:
        """Cross-check inter-principal-plane distance ``span - ppa + ppp``; should
        equal the datasheet ``HH'`` when everything parsed consistently."""
        if self.span is None or self.ppa is None or self.ppp is None:
            return None
        return self.span - self.ppa + self.ppp


def _first_float(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    if match is None:
        return None
    try:
        value = float(match.group(1))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_datasheet_cardinals(path: str | Path) -> DatasheetCardinals | None:
    """Scrape first-order cardinals from a vendor datasheet PDF.

    Returns ``None`` when the PDF cannot be read or yields no effective focal
    length (so the folder importer can fall through to a clear "no source" error).
    """
    text = extract_pdf_text(path)
    if not text:
        return None

    effl = _first_float(text, r"f['’]eff\s*\[mm\]\s*(-?\d[\d.]*)")
    if effl is None:
        # Fall back to the plain "Focal length" spec-row when f'eff is absent.
        effl = _first_float(text, r"Focal len\w*\s*\[?mm?\]?\s*(-?\d[\d.]*)")
    if effl is None or not (math.isfinite(effl) and abs(effl) > 1e-6):
        return None

    cardinals = DatasheetCardinals(effl=abs(effl))
    cardinals.front_focal = _first_float(text, r"(?<![A-Za-z'])SF\s*\[mm\]\s*(-?\d[\d.]*)")
    cardinals.back_focal = _first_float(text, r"S'F'\s*\[mm\]\s*(-?\d[\d.]*)")
    cardinals.hh = _first_float(text, r"HH'\s*\[mm\]\s*(-?\d[\d.]*)")
    # Sigma d row: "d [mm] Σ 43.19" -- the "d" glues onto the previous number, so
    # anchor on the sigma glyph (U+03A3), the only one in the table.
    cardinals.span = _first_float(text, r"Σ\s*(-?\d[\d.]*)")
    cardinals.fno = _first_float(text, r"F/(\d+\.?\d*)\s*\.\.\.\s*F/")
    cardinals.image_circle = _first_float(text, r"Max\.\s*sensor size\s*\[mm\]\s*(\d[\d.]*)")

    lens_id = re.search(r"ID \[standard\]\s*(\d+)", text)
    if lens_id is not None:
        cardinals.lens_id = lens_id.group(1)

    title = re.search(r"(PYRITE\s+\S+(?:\s+V\d+)?)", text)
    if title is not None:
        cardinals.title = title.group(1).strip()

    mag_label = re.search(r"PYRITE\s+[\d.]+/[\d.]+/([\d.]+x(?:-[\d.]+x)?)", text)
    if mag_label is not None:
        cardinals.mag_label = mag_label.group(1)

    # Nominal magnification: prefer the "Rec. magnification range <nominal> (...)"
    # value (already negative); else the title's first magnitude, made negative
    # because a finite-conjugate machine-vision lens inverts the image.
    rec_mag = _first_float(text, r"Rec\.\s*magnification range\s*(-\d[\d.]*)")
    if rec_mag is not None:
        cardinals.magnification = rec_mag
    else:
        title_mag = _first_float(text, r"PYRITE\s+[\d.]+/[\d.]+/([\d.]+)x")
        if title_mag is not None and title_mag > 0.0:
            cardinals.magnification = -abs(title_mag)

    return cardinals
