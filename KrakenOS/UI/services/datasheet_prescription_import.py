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

import hashlib
import math
import re
import shutil
import subprocess
import tempfile
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


def _printable_ratio(text: str) -> float:
    """Share of characters that are printable Latin-1. bugs/0785: the test must count
    160..255 too -- the separators that decide a spec row are exactly there (``\xd7``
    MULTIPLICATION SIGN between "4096" and "3000", ``\xb5`` MICRO SIGN, ``\xb0``), and an
    ASCII-only test throws the row's separator away and with it the regex that needs it."""
    if not text:
        return 0.0
    ok = sum(
        1 for ch in text
        if 32 <= ord(ch) < 127 or 160 <= ord(ch) < 256 or ch in "\n\r\t"
    )
    return ok / len(text)


def _show_text(body: bytes, cmap: dict[int, str]) -> str:
    """One literal show-string, decoded through the active CMap when that yields
    anything and as a raw Latin-1 literal when it does not.

    bugs/0785 (error.png, "Could not extract a sensor size from this folder" on the
    Hikrobot MV-CH120-60UMUC): a datasheet routinely mixes fonts INSIDE one spec row --
    the labels in a simple font with no ToUnicode, the values in a subset CID font that
    has one (that sheet's F7 maps exactly ``. 3 4 5 m o s t x u -``). Decoding the whole
    page one way or the other therefore loses half of every row: the CMap pass returned 5
    ASCII letters, and the raw-literal pass had "Pixel size" with no pitch after it. Since
    every scraper regex is ``Label\\s*:?\\s*value``, a label separated from its value by the
    other font's dropped run can never match, and the import fails with a sensor size the
    sheet plainly states. Falling back PER SHOW-STRING keeps document order, so label and
    value stay adjacent whichever font each is set in."""
    decoded = _decode_show(body, cmap) if cmap else ""
    if decoded:
        return decoded
    literal = _unescape_pdf_literal(body)
    return literal if _printable_ratio(literal) > 0.8 else decoded


def _decode_content(stream: bytes, name_to_cmap: dict[str, dict[int, str]]) -> str:
    """Walk a content stream, switching CMaps on ``/Fn Tf`` and decoding every
    ``Tj`` / ``TJ`` show; a large negative ``TJ`` advance renders as a space.

    bugs/0785: a show-string whose font carries no usable ToUnicode falls back to its raw
    Latin-1 literal rather than being dropped -- see :func:`_show_text`."""
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
                    out.append(_show_text(show.group(1), current))
        elif stripped.endswith(b"TJ"):
            array = re.search(rb"\[(.*)\]\s*TJ", text, re.S).group(1)
            for element in _TJ_ELEMENT_RE.finditer(array):
                if element.group(1) is not None:
                    out.append(_show_text(element.group(1), current))
                elif element.group(2) is not None:
                    out.append(_decode_hex_show(element.group(2), current))
                elif element.group(3) is not None and int(element.group(3)) < -90:
                    out.append(" ")
    return "".join(out)


# bugs/0307: raw literal-harvest fallback for CID-font datasheets with no ToUnicode
# (BC-OM25M12X2). Shared by the camera + lens (Path C) importers.
_LITERAL_SHOW_RE = re.compile(rb"\((?:[^()\\]|\\.)*\)", re.S)
# bugs/0785: a PDF text object -- the only place a page may SHOW text.
_TEXT_OBJECT_RE = re.compile(rb"BT\b(.*?)\bET\b", re.S)
_PDF_ESCAPE_SIMPLE = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}  # n r t b f
# A CMap decode yielding fewer ASCII letters than this means the datasheet's CID
# fonts carry no usable ToUnicode -- fall back to raw literal harvesting. A real
# text-based datasheet returns thousands, so the fallback never fires for it.
_MIN_DECODED_LETTERS = 64


def _ascii_letter_count(text: str) -> int:
    return sum(1 for ch in text if ("a" <= ch <= "z") or ("A" <= ch <= "Z"))


def _unescape_pdf_literal(body: bytes) -> str:
    """Resolve PDF string escapes (``\\n \\( \\) \\\\ \\ddd`` octal) in one literal
    show-string, decoding the result as Latin-1 (covers the ``µ`` micro-sign,
    ``\\265``)."""
    out = bytearray()
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == 0x5C and i + 1 < n:  # backslash
            nxt = body[i + 1]
            if nxt in _PDF_ESCAPE_SIMPLE:
                out.append(_PDF_ESCAPE_SIMPLE[nxt])
                i += 2
                continue
            if 0x30 <= nxt <= 0x37:  # up to 3 octal digits
                j = i + 1
                digits = bytearray()
                while j < n and len(digits) < 3 and 0x30 <= body[j] <= 0x37:
                    digits.append(body[j])
                    j += 1
                out.append(int(bytes(digits), 8) & 0xFF)
                i = j
                continue
            out.append(nxt)  # \( \) \\ and any other escaped byte -> literal
            i += 2
            continue
        out.append(c)
        i += 1
    return out.decode("latin-1")


def _harvest_literal_text(objs: dict[int, bytes]) -> str:
    """Fallback recovery for datasheets whose CID fonts carry no ToUnicode CMap
    (so :func:`_decode_content` yields nothing) but whose English spec table is
    set in simple fonts: harvest the raw ``(..)`` literal show-strings directly,
    with PDF escapes resolved. Pure stdlib; only reached when the CMap decode is
    essentially empty, so text-based datasheets are never affected."""
    parts: list[str] = []
    for raw in objs.values():
        stream = _inflate(raw)
        if b"Tj" not in stream and b"TJ" not in stream:
            continue
        # bugs/0785: harvest only INSIDE text objects. PDF can only show text between
        # ``BT`` and ``ET``, while an accessibility-tagged sheet (any Word/InDesign export)
        # writes one ``/P <</MCID n/Lang (en-US)>> BDC`` per run OUTSIDE them -- 380 of them
        # on the Hikrobot MV-CH120-60UMUC, 2738 on the Bopixel BC-Gx25M12X4. Harvesting the
        # whole stream glued "en-US" between every label and its value, which defeats every
        # ``Label\\s*:?\\s*value`` regex in both the camera and lens scrapers and made each
        # newly-added vendor look like an unreadable datasheet.
        for body in _TEXT_OBJECT_RE.finditer(stream):
            for lit in _LITERAL_SHOW_RE.finditer(body.group(1)):
                parts.append(_unescape_pdf_literal(lit.group(0)[1:-1]))
    return "".join(parts)


# bugs/0785: pdfminer writes "(cid:1239)" for a glyph it cannot map through the font.
# Those placeholders are NOT text -- and "cid" is three ASCII letters, so a naive letter
# count reads a page of them as a rich text layer. The ELS-85 sheet is exactly that: 1101
# "letters" of pure (cid:N), where the stdlib decoder below recovers the real 447.
_CID_PLACEHOLDER_RE = re.compile(r"\(cid:\d+\)")


def _useful_letter_count(text: str) -> int:
    """ASCII letters that are real text -- pdfminer's ``(cid:N)`` placeholders removed."""
    return _ascii_letter_count(_CID_PLACEHOLDER_RE.sub("", text or ""))


def _extract_pdf_text_pdfplumber(path: str | Path) -> str:
    """Page text via ``pdfplumber`` (pure-Python ``pdfminer.six``), or ``""``.

    bugs/0785: the hand-rolled decoder below understands the slice of PDF the
    datasheets seen so far happened to use; a real parser understands the format --
    cross-reference streams, object streams, every font encoding. The Bopixel
    BC-Gx25M12X4 sheet states its sensor plainly on page 4 ("Active Pixel 5120 (H) x
    5120 (V)", "Pixel Size 2.5 (H) x 2.5 (V) um") and the stdlib decoder returns only
    dot-leaders for it, so each new vendor kept landing on "Could not extract a sensor
    size" for a sheet that is perfectly readable.

    ``pdfplumber`` is a DECLARED dependency (pyproject.toml, devenv.nix), so this is
    not a new requirement -- but the import stays optional and every failure returns
    ``""``, because the stdlib path below still wins on the datasheets whose CID fonts
    carry no ToUnicode at all (pdfminer has nothing to map there, while the raw
    ``(..)`` literal harvest still recovers the English spec table).
    """
    try:
        import pdfplumber
    except Exception:
        return ""
    try:
        parts: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def _extract_pdf_text_stdlib(path: str | Path) -> str:
    """The hand-rolled per-font ToUnicode decode, with the raw-literal harvest as its own
    fallback. Pure stdlib; ``""`` on any failure."""
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
        text = "\n".join(chunks)
        if _ascii_letter_count(text) >= _MIN_DECODED_LETTERS:
            return text
        fallback = _harvest_literal_text(objs)
        return fallback if _ascii_letter_count(fallback) > _ascii_letter_count(text) else text
    except Exception:
        return ""


_OCR_CACHE_DIR = Path(__file__).resolve().parents[3] / "attachment" / "cad_cache" / "datasheet_ocr"
_OCR_MAX_PAGES = 8          # a datasheet states its spec table in the first pages or not at all
_OCR_RENDER_DPI = 300       # measured: 300 keeps the tolerance glyph in "110+-2"; ocrmypdf's own
                            # rasterisation loses it and reads "1102"
_OCR_TIMEOUT_S = 180


def _ocr_engine_available() -> bool:
    if _rapidocr_available():
        return True
    return bool(shutil.which("pdftoppm") and shutil.which("tesseract"))


def _rapidocr_available() -> bool:
    """bugs/0788: the in-process engine -- ``rapidocr-onnxruntime`` recognising a page that
    ``pdfplumber`` rasterised. Preferred over the external pair for two measured reasons, not
    for tidiness:

    * it keeps the glyph that decides the value. On the COOLENS sheet it returns ``110±2`` and
      ``280±2`` with the real MINUS-OR-PLUS character, where tesseract gives ``110+2`` at best
      and ``1102`` through ocrmypdf's rasteriser -- a 1102 mm working distance.
    * it returns a BOX per line, so a label pairs with the value in its own row by geometry.
      The external path depends on ``--psm 4`` happening to keep two side-by-side spec tables
      apart; that is luck, and luck is what bugs/0786 had to corroborate its way around.

    Both are optional. Without either, :func:`_extract_pdf_text_ocr` returns "" and the
    importer refuses exactly as it did before bugs/0787."""
    try:
        import pdfplumber  # noqa: F401
        import rapidocr_onnxruntime  # noqa: F401
    except Exception:
        return False
    return True


def _ocr_rows_to_text(boxes: "list[tuple]") -> str:
    """Rebuild reading order from recognised boxes: group by row, then left to right.

    This is the whole point of a box-returning engine -- ``Working Distance (mm)`` and its
    ``110±2`` end up adjacent in the text the existing scrapers read, without relying on a
    page-segmentation mode to have kept the columns apart."""
    import numpy as np

    items = []
    for box, text, _confidence in boxes or []:
        if not str(text).strip():
            continue
        ys = [float(pt[1]) for pt in box]
        xs = [float(pt[0]) for pt in box]
        items.append((float(np.mean(ys)), float(np.mean(xs)),
                      float(max(ys) - min(ys)), str(text).strip()))
    if not items:
        return ""
    items.sort(key=lambda r: r[0])
    # a row is "within half a line height of the row we are building" -- measured from the
    # boxes themselves, so it follows the sheet's own type size instead of a magic number
    rows: "list[list[tuple]]" = []
    current: "list[tuple]" = []
    anchor = None
    for y, x, height, text in items:
        tol = max(height, 8.0) * 0.6
        if anchor is None or abs(y - anchor) <= tol:
            current.append((x, text))
            anchor = y if anchor is None else (anchor + y) / 2.0
        else:
            rows.append(current)
            current, anchor = [(x, text)], y
    if current:
        rows.append(current)
    return "\n".join(" ".join(t for _x, t in sorted(row)) for row in rows)


def _extract_pdf_text_rapidocr(path: str | Path) -> str:
    """bugs/0788: rasterise with pdfplumber and recognise in process. "" on any failure."""
    if not _rapidocr_available():
        return ""
    try:
        import numpy as np
        import pdfplumber
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        parts: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages[:_OCR_MAX_PAGES]:
                image = page.to_image(resolution=_OCR_RENDER_DPI).original.convert("RGB")
                result, _elapsed = engine(np.asarray(image))
                parts.append(_ocr_rows_to_text(result))
        return "\n".join(p for p in parts if p)
    except Exception:
        return ""


def _extract_pdf_text_layout(path: str | Path) -> str:
    """Page text assembled from CHARACTER POSITIONS, honouring a rotated title block.

    bugs/0791. This is the answer to the failure bugs/0565 worked around: a CAD drawing's title
    block is typeset ROTATED, and a reading-order extractor then walks it the wrong way, emitting
    every label in one run and every value in another --

        Optical MgnificationResolution(um)W.D(mm)N.AF/#...4.0X 652.090.1612.5...

    -- so no ``Label\\s*:?\\s*value`` regex can pair them, and the sheet looks like it states
    nothing. On the SPO TCL4.0X-65DI-5M every one of its 284 characters has ``upright=False``.

    Rotating the frame (the row coordinate becomes ``x0``, the advance becomes ``top``) and
    grouping by row recovers the table exactly as the vendor drew it:

        Optical Mgnification 4.0X  W.D(mm) 65
        F/# 12.5  D.O.F (COC:20um) 31.3um
        Resolution(um) 2.09  N.A 0.16

    No OCR, no DWG, no external binary -- the text was always there, in the right places.
    """
    try:
        import pdfplumber
    except Exception:
        return ""
    try:
        import statistics

        pages: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                chars = [c for c in page.chars if str(c.get("text", "")).strip()]
                if not chars:
                    continue
                rotated = sum(1 for c in chars if not c.get("upright")) > len(chars) / 2
                row_of = (lambda c: float(c["x0"])) if rotated else (lambda c: float(c["top"]))
                run_of = (lambda c: float(c["top"])) if rotated else (lambda c: float(c["x0"]))
                # one tolerance for the page, from the median glyph size: a per-character
                # tolerance splits a single label whose glyphs differ in size
                size = statistics.median([float(c.get("size") or 3.0) for c in chars]) or 3.0
                tol = max(size * 0.6, 0.5)
                lines: "list[list[dict]]" = []
                current: "list[dict]" = []
                anchor = None
                for char in sorted(chars, key=lambda c: (row_of(c), run_of(c))):
                    if anchor is None or abs(row_of(char) - anchor) <= tol:
                        current.append(char)
                        anchor = row_of(char) if anchor is None else anchor
                    else:
                        lines.append(current)
                        current, anchor = [char], row_of(char)
                if current:
                    lines.append(current)
                out: list[str] = []
                for line in lines:
                    run = sorted(line, key=run_of)
                    # the gap is measured against each glyph's OWN set width. pdfplumber reports
                    # a rotated glyph with its axes swapped, so the advance extent is
                    # bottom - top there and x1 - x0 otherwise; using the nominal size instead
                    # glued labels together, and using the line's median advance split wide
                    # glyphs ("OpticalM gnification").
                    def _extent(c):
                        return (float(c["bottom"]) - float(c["top"]) if rotated
                                else float(c["x1"]) - float(c["x0"]))

                    text, previous = "", None
                    for char in run:
                        if previous is not None and run_of(char) - previous > size * 0.28:
                            text += " "
                        text += str(char["text"])
                        previous = run_of(char) + _extent(char)
                    text = " ".join(text.split())
                    if text:
                        out.append(text)
                pages.append("\n".join(out))
        return "\n".join(p for p in pages if p)
    except Exception:
        return ""


def _extract_pdf_text_tesseract(path: str | Path) -> str:
    """The external pair: ``pdftoppm`` renders, ``tesseract`` recognises. ``""`` when absent.

    ``--psm 4`` (a single column of variable-size text) is what keeps two side-by-side spec
    tables apart; ``--psm 6`` merges them and a label loses its value to the neighbouring
    table. 300 dpi is what keeps the tolerance glyph: "110+-2" survives as "110+2" so the
    value regex stops at 110, where ocrmypdf's own rasteriser yields "1102".
    """
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "page"
            subprocess.run(
                ["pdftoppm", "-r", str(_OCR_RENDER_DPI), "-png",
                 "-f", "1", "-l", str(_OCR_MAX_PAGES), str(Path(path)), str(base)],
                check=True, capture_output=True, timeout=_OCR_TIMEOUT_S,
            )
            parts: list[str] = []
            for image in sorted(Path(tmp).glob("page*.png")):
                done = subprocess.run(
                    ["tesseract", str(image), "stdout", "--psm", "4"],
                    check=True, capture_output=True, timeout=_OCR_TIMEOUT_S,
                )
                parts.append(done.stdout.decode("utf-8", errors="replace"))
        return "\n".join(parts)
    except Exception:
        return ""


# bugs/0788: the two engines have COMPLEMENTARY weaknesses, measured on the COOLENS
# WWK10-110CP-111V3 spec table, so neither is declared the winner:
#
#   rapidocr   keeps the glyph that decides the value -- "110±2" and "280±2" with the real
#              character -- and returns a box per line so a label pairs with the value in its
#              own row by geometry. BUT its detector misses isolated single-character cells:
#              the row "Best Aperture (F/#) | 7 ... Mount | C" comes back with the labels and
#              neither value, and a missing mount means no flange and no derivation.
#   tesseract  finds those one-character cells, but mangles "110±2" to "110+2" (usable) and,
#              through ocrmypdf's rasteriser, to "1102" (a 1102 mm working distance).
#
# So the caller tries each reading in turn and keeps the first that yields a usable, CORROBORATED
# result. Merging the two texts was rejected: a regex would then take whichever number appeared
# first, silently mixing two engines' readings of the same cell.
_OCR_ENGINES = (
    ("rapidocr", lambda p: _extract_pdf_text_rapidocr(p)),
    ("tesseract", lambda p: _extract_pdf_text_tesseract(p)),
)


def _ocr_cached(path: str | Path, engine: str, produce) -> str:
    """One engine's reading of one file, cached beside the other generated caches (gitignored)
    because OCR is slow and a datasheet does not change."""
    try:
        digest = hashlib.md5(Path(path).read_bytes()).hexdigest()
    except Exception:
        return ""
    cached = _OCR_CACHE_DIR / f"{digest}.{engine}.txt"
    try:
        if cached.is_file():
            return cached.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    text = produce(path)
    if not text.strip():
        return ""
    try:
        _OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(text, encoding="utf-8")
    except Exception:
        pass
    return text


def text_candidates(path: str | Path) -> "list[str]":
    """Readings to try when the ordinary text layer yields nothing usable, cheapest first.

    bugs/0791 puts the position-aware layout reading ahead of the OCR engines: it costs a
    fraction of a second, needs no binary, and fixes the commonest reason a legible datasheet
    reads as empty -- a rotated CAD title block walked in the wrong order.
    """
    out: list[str] = []
    layout = _extract_pdf_text_layout(path)
    if layout.strip():
        out.append(layout)
    out.extend(ocr_text_candidates(path))
    return out


def ocr_text_candidates(path: str | Path) -> "list[str]":
    """Every available engine's reading of ``path``, best-first. Empty when none is installed.

    :func:`_ocr_engine_available` is the MASTER switch and is consulted before the cache, so a
    caller (or a guard) that turns OCR off gets the pre-bugs/0787 behaviour exactly -- an honest
    refusal -- rather than a stale reading from a previous run.
    """
    if not _ocr_engine_available():
        return []
    out: list[str] = []
    for engine, produce in _OCR_ENGINES:
        text = _ocr_cached(path, engine, produce)
        if text.strip():
            out.append(text)
    return out


def _extract_pdf_text_ocr(path: str | Path) -> str:
    """LAST resort: rasterise the pages and recognise them. ``""`` when unavailable.

    bugs/0787: some vendors ship the spec table as a PICTURE. The COOLENS WWK10-110CP-111V3
    datasheet states its whole first order -- magnification, working distance, mount, housing
    length -- in a table that carries 26 of the page's 212 character objects, all of them the
    title; there is simply no text to decode, so bugs/0785's work cannot reach it.

    Returns the FIRST engine's reading; callers that can judge the result (they can tell whether
    a scrape succeeded) should use :func:`ocr_text_candidates` and try each in turn.

    Nothing here is trusted on its own: the caller still has to corroborate the numbers
    (bugs/0786 checks them against the sheet's own printed total), which is what makes reading a
    picture safe at all.
    """
    candidates = ocr_text_candidates(path)
    return candidates[0] if candidates else ""


def extract_pdf_text(path: str | Path) -> str:
    """Best-effort plain text from a vendor datasheet PDF.

    Two extractors run and the better result wins: a real PDF parser
    (:func:`_extract_pdf_text_pdfplumber`) and the pure-stdlib per-font ToUnicode decoder
    (:func:`_extract_pdf_text_stdlib`).  Returns ``""`` when neither recovers anything, so
    callers degrade gracefully.

    bugs/0785: neither one wins everywhere, which is why they compete rather than one being
    tried first.  The parser reads sheets the stdlib decoder cannot (the Bopixel
    BC-Gx25M12X4 states its sensor plainly on page 4 and the decoder returns only
    dot-leaders); the decoder reads sheets the parser cannot (the AZURE ELS-85's fonts carry
    no ToUnicode, so pdfminer emits 218 ``(cid:N)`` placeholders where the raw ``(..)``
    literal harvest recovers the real title block).  **The stdlib result wins ties**, so a
    sheet that both read equally well keeps the exact text every existing scraper was
    written and regression-tested against.
    """
    parsed = _CID_PLACEHOLDER_RE.sub("", _extract_pdf_text_pdfplumber(path))
    native = _extract_pdf_text_stdlib(path)
    return parsed if _ascii_letter_count(parsed) > _ascii_letter_count(native) else native


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
    # bugs/0647: the vendor's Optimum Working Distance (object -> front housing rim,
    # the plane a bench user can actually measure to) and the |m| it pairs with.
    # Together with the EFL they pin the front principal plane RELATIVE TO THE
    # HOUSING: principal-behind-rim = f(1+1/m) - WD. The ELS-85 surrogate's nominal
    # symmetric principal split sat 9.45 mm too deep, so every on-screen standoff
    # read ~9 mm short of the bench.
    optimum_wd: float | None = None
    optimum_wd_mag: float | None = None
    # bugs/0656: a FIXED-CONJUGATE lens (telecentric with a named mount) carries its
    # mount's flange focal distance -- the image plane sits this far behind the
    # housing rear face, so the camera MOUNTS to the lens instead of being solved
    # toward it. None for ordinary variable-conjugate lenses.
    mount_flange_mm: float | None = None
    # bugs/0668: only an object-space TELECENTRIC's front glass spans the object
    # field (its chief rays are parallel); an ordinary lens funnels the field
    # through its pupil. The disc-sizing rule branches on this.
    telecentric: bool = False
    # bugs/0792: the catalogue pins the CONJUGATES but not the focal length. Set when the
    # coincident-principal-plane derivation is provably wrong for this magnification, so the
    # surrogate builder solves for the lens (two groups inside the housing) instead of for an f.
    conjugate_constrained: bool = False
    # bugs/0807: where the vendor drawing puts the IRIS (the aperture stop of an object-space
    # telecentric), in mm behind the housing's front face, and the radius of the barrel in front
    # of it. None when the source does not state them.
    stop_from_front_mm: float | None = None
    stop_source: str | None = None
    stop_ring_mm: tuple | None = None   # the dimensioned iris ring the stop sits in, if any
    front_barrel_radius_mm: float | None = None

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


def model_designation_cardinals(text: str) -> tuple[float | None, float | None]:
    """Focal length and F-number recovered from a vendor MODEL DESIGNATION (bugs/0565).

    Some vendors ship a CAD **drawing title block** rather than a spec table.  AZURE
    Photonics' ``ELS-85 4.5V16K_specification.pdf`` is one: its labels and its values live in
    separate text runs, so the flattened extraction reads

        ``...(Focal Length)F.O.V(DxVxH)...26mmD85mmELS-85/4.5V16Kg10-4141.85mm4.5Manual...``

    -- every label is orphaned from its number and no ``Focal length`` pattern can pair them.
    The designation itself, though, is unambiguous: ``ELS-85/4.5`` is the vendor's own name for
    an 85 mm f/4.5 lens, and the hand-built ``machine_vision_AZ85_RA_Mirror`` surrogate for this
    exact folder uses precisely 85 mm with an ``Aperture Stop F/4.5`` of diameter
    18.8889 = 85/4.5.

    Two things keep this from becoming number-soup, because the same flattened text also
    contains decoys like ``10-4141.85mm``:

    * the token must be ``LETTERS-<number>/<number>`` -- a bare ``F/4.5`` or a date-like
      ``10-41`` cannot match; and
    * the focal length must be CORROBORATED by the same number appearing as ``<n>mm``
      elsewhere in the sheet (here ``D85mm``, the orphaned Focal Length value).

    Without corroboration this returns ``None`` and the caller refuses exactly as before -- a
    wrong prescription is far worse than a clear "cannot derive the lens optics".
    """
    if not text:
        return None, None
    # No ``\b`` before the series letters: the flattened title-block text GLUES the designation
    # onto the previous value ("...26mmD85mmELS-85/4.5..."), so there is no word boundary there.
    # Anchor on the uppercase run instead.
    pattern = r"(?<![A-Z])([A-Z]{2,5})-(\d{1,4}(?:\.\d+)?)\s*/\s*(\d{1,2}(?:\.\d+)?)"
    for match in re.finditer(pattern, text):
        raw_focal, raw_fno = match.group(2), match.group(3)
        try:
            focal, fno = float(raw_focal), float(raw_fno)
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(focal) and math.isfinite(fno)):
            continue
        if not (1.0 <= focal <= 2000.0 and 0.5 <= fno <= 64.0):
            continue
        if re.search(rf"{re.escape(raw_focal)}\s*mm", text) is None:
            continue
        return focal, fno
    return None, None


# bugs/0653: flange focal distances for the mounts a fixed-conjugate sheet can name.
# The image plane of a machine-vision lens designed for a named mount sits this far
# behind its mount shoulder -- the vendor's own design constraint, not a guess.
_MOUNT_FLANGE_MM = {
    "C": 17.526,
    "CS": 12.526,
    "TFL": 17.526,  # TFL (M35x0.75) keeps the C-mount flange distance by definition
    "F": 46.5,
}


def _scrape_image_circle(text: str) -> "float | None":
    """The image-circle diameter, under every spelling a vendor has used for it.

    bugs/0789: this lives in ONE place because it was in two, and the telecentric path knew
    only the Edmund spelling. The COOLENS WWK10-110CP-111V3 states it as
    ``Max Sensor Size (Φmm) | 18.0(1.1")`` -- the same datum, in the row that decides how wide
    the lens's glass has to be -- so its surrogate was drawn and apertured at 1.4x the STOP
    (Ø14.0) inside a Ø44 barrel, where bugs/0662's own rule (field + pupil) gives Ø28.0.

    The unit is written ``(mm)``, ``[mm]`` or ``(Φmm)``, and an OCR'd sheet renders that Φ as
    ``@`` or ``®P`` -- so a couple of characters before ``mm`` are tolerated. Being lenient
    about a LABEL is safe here for the same reason as in bugs/0786: it only decides where to
    look, and the value is bounded below against a plausible physical range. An image circle
    sizes apertures; unlike the EFL it cannot move the first order.
    """
    for pattern in (
        r"Max\.\s*sensor size\s*\[mm\]\s*(\d[\d.]*)",
        r"(?i)image\s+circle\s+max\.?\s*[\[(]\s*mm\s*[\])]\s*(\d+\.?\d*)",
        r"(?i)Maximum\s+Image\s+Circle\s*[\[(]\s*mm\s*[\])]\s*:?\s*(\d+\.?\d*)",
        # bugs/0789: "Max Sensor Size (Φmm) 18.0(1.1\")" -- and its OCR spellings of the Φ
        r"(?i)Max\.?\s*Sensor\s*Size\s*[\[(]\s*[^)\]]{0,4}mm\s*[\])]\s*:?\s*(\d+\.?\d*)",
    ):
        value = _first_float(text, pattern)
        if value is not None and 1.0 <= value <= 400.0:
            return value
    return None


def telecentric_conjugate_cardinals(text: str) -> DatasheetCardinals | None:
    """bugs/0653 (error.png, Edmund #67-304 CompactTL): derive the EFL of a
    fixed-conjugate TELECENTRIC sheet that states NO focal length anywhere.

    Such a sheet pins the whole first order mechanically instead: a fixed
    magnification m, the working distance WD (object -> front housing), the housing
    length L, and a named mount whose flange focal distance FFD fixes where the
    vendor intends the sensor. The total conjugate is then T = WD + L + FFD, and
    with coincident principal planes (HH' = 0, the same nominal the bugs/0565
    designation path accepts) the thin-lens identity T = f(2 + m + 1/m) gives

        f = (WD + L + FFD) / (2 + m + 1/m).

    The import-time bugs/0647 refit then re-anchors the front principal to the
    housing (principal-behind-rim = f(1+1/m) - WD), so the surrogate delivers the
    sheet's own contract -- m at WD with the image at the flange -- regardless of
    the HH' nominal. Every value is corroborated before use (the title repeats
    "<m>X, <WD>mm WD" on this format); anything missing or ambiguous refuses, and
    the caller keeps its honest "cannot derive the lens optics" error.
    """
    if not text or re.search(r"(?i)telecentric", text) is None:
        return None
    mag = _first_float(text, r"(?i)Primary\s+Magnification\s+PMAG\s*:?\s*(\d+\.?\d*)\s*X")
    if mag is None:
        mag = _first_float(text, r"(?i)Telecentric\s+Lens\s+Magnification\s*:?\s*(\d+\.?\d*)")
    if mag is None:
        mag = _first_float(text, r"(?i)\bMagnification\s*:?\s*(\d+\.?\d*)\s*X")
    if mag is None:
        # bugs/0786: a spec TABLE puts the unit in the label and the bare number in the cell --
        # "Magnification (x) | 1.0" (COOLENS WWK10-110CP) -- so there is no "X" after the value
        # to anchor on. Same row, same meaning, different typography.
        mag = _first_float(text, r"(?i)\bMagnification\s*\(\s*x\s*\)\s*:?\s*(\d+\.?\d*)")
    if mag is None or not (0.05 <= mag <= 20.0):
        return None
    wd = _first_float(text, r"(?i)Working\s+Distance\s*\(\s*mm\s*\)\s*:?\s*(\d+\.?\d*)")
    if wd is None or not (1.0 <= wd <= 5000.0):
        return None
    length = _first_float(text, r"(?i)(?<![a-z] )Length\s*\(\s*mm\s*\)\s*:?\s*(\d+\.?\d*)")
    if length is None or not (5.0 <= length <= 2000.0):
        return None
    mount = re.search(r"(?i)Mount\s*:?\s*(C|CS|TFL|F)\s*-?\s*Mount", text)
    if mount is None:
        # bugs/0786: a Mechanical Specifications table states the mount as a bare cell,
        # "Mount | C", with the word "Mount" only in the label column.
        mount = re.search(r"(?i)\bMount\s*:?\s*(C|CS|TFL|F)\s*(?:\n|\r|$|\s{2,})", text)
    if mount is None:
        return None
    flange = _MOUNT_FLANGE_MM.get(mount.group(1).upper())
    if flange is None:
        return None
    total = wd + length + flange
    # Corroboration -- the bugs/0565 lesson, a wrong prescription is far worse than a clear
    # refusal. Two independent ways to earn it; either suffices.
    #
    #  (i) the Edmund title repeats both numbers: "0.75X, 110mm WD".
    #  (ii) bugs/0786: the sheet states its OWN total and says how it is built. COOLENS prints
    #       "Length of I/O (mm) 280+-2" with the note "Length of I/O = WD + Length + Back Focal
    #       Length" -- which IS wd + length + flange. Checking the arithmetic against the
    #       vendor's own printed total is stronger than matching their title typography, and it
    #       is what catches an OCR'd sheet: recognising "110+-2" as "1102" gives a total of
    #       1272 mm against a printed 280, so the sheet refutes the misread itself.
    corroborated = (
        re.search(rf"{re.escape(f'{wd:g}')}\s*mm\s+WD", text) is not None
        and re.search(rf"(?<![\d.]){re.escape(f'{mag:g}')}X", text) is not None
    )
    if not corroborated:
        stated = _first_float(
            text,
            # bugs/0786: the LABEL may be OCR'd -- "Length of I/0O (mm)" for "Length of I/O
            # (mm)" (tesseract reads the O as a zero). Being lenient about a label is safe;
            # the VALUE it introduces is still checked against wd+length+flange below, which
            # is what actually guards the number.
            r"(?i)(?:Length\s*of\s*[I1l]\s*/\s*[O0]+|Total\s+Track|Overall\s+Length|OAL)"
            r"\s*\(\s*mm\s*\)\s*:?\s*(\d+\.?\d*)",
        )
        if stated is None:
            return None
        # the tolerance the sheet itself prints on that row (+-2 here); allow a little more for
        # a back-focal rounded to one decimal, never enough to admit a misread order of magnitude
        if abs(stated - total) > max(3.0, 0.02 * stated):
            return None
        corroborated = True
    effl = total / (2.0 + mag + 1.0 / mag)
    if not (1.0 <= effl <= 2000.0):
        return None
    # bugs/0647's registration law: 0 < f(1+1/m) - WD < f, i.e. the front principal plane lands
    # inside the housing. bugs/0792: when it does NOT, that is not a bad datasheet -- above about
    # 1x it is unsatisfiable for every real lens of this class (a 4x at 65 mm WD would need a
    # 325 mm track; Edmund's own 62-793 has 192.5 and the SPO 225). Hand the conjugates to the
    # builder and let it solve for the LENS rather than refusing.
    offset = effl * (1.0 + 1.0 / mag) - wd
    conjugate_constrained = not (0.0 < offset < effl)
    cardinals = DatasheetCardinals(effl=round(effl, 4))
    cardinals.telecentric = True
    cardinals.conjugate_constrained = bool(conjugate_constrained)
    cardinals.magnification = -abs(mag)  # a finite-conjugate lens inverts
    cardinals.optimum_wd = wd
    cardinals.optimum_wd_mag = abs(mag)
    cardinals.mount_flange_mm = float(flange)  # bugs/0656: the image is AT the flange
    # The housing length is the honest vertex span: a telecentric barrel is far
    # longer than its EFL (here 160 mm vs 70.4), and both the STEP-extent span (the
    # body's Z can be its DIAMETER when the CAD axis is not Z) and the 0.7*EFL cap
    # produce a block too short to hold the principal f(1+1/m)-WD behind the rim --
    # the bugs/0647 refit then has no room and falls back to the advisory.
    cardinals.span = round(length, 4)
    cardinals.fno = _first_float(text, r"(?i)Aperture\s*\(\s*f\s*/#\s*\)\s*:?\s*f?\s*/?\s*(\d+\.?\d*)")
    cardinals.image_circle = _scrape_image_circle(text)
    stock = re.search(r"#(\d{2}-\d{3})", text)
    if stock is not None:
        cardinals.lens_id = stock.group(1)
    title = re.search(r"([\d.]+X,\s*\d+\.?\d*mm\s+WD[^#]{0,80}?Telecentric\s+Lens)", text)
    if title is not None:
        cardinals.title = title.group(1).strip()
    return cardinals


def parse_datasheet_cardinals(path: str | Path) -> DatasheetCardinals | None:
    """Scrape first-order cardinals from a vendor datasheet PDF.

    Returns ``None`` when the PDF cannot be read or yields no effective focal
    length (so the folder importer can fall through to a clear "no source" error).

    bugs/0787: when the text layer yields nothing, fall back to OCR -- some sheets print their
    spec table as a picture. OCR runs ONLY on this failure, so a readable datasheet never pays
    for it, and its numbers still have to earn bugs/0786's corroboration before they are used.
    """
    cardinals = _cardinals_from_text(extract_pdf_text(path))
    if cardinals is not None and cardinals.effl:
        return cardinals
    for recognised in text_candidates(path):
        candidate = _cardinals_from_text(recognised)
        if candidate is not None and candidate.effl:
            return candidate
        cardinals = cardinals or candidate
    return cardinals


def _cardinals_from_text(text: str) -> DatasheetCardinals | None:
    """The scrape itself, on already-extracted text (bugs/0787 split it out so the same body
    serves both the text layer and the OCR retry)."""
    if not text:
        return None

    effl = _first_float(text, r"f['’]eff\s*\[mm\]\s*(-?\d[\d.]*)")
    if effl is None:
        # Fall back to the plain "Focal length" spec-row when f'eff is absent.
        effl = _first_float(text, r"Focal len\w*\s*\[?mm?\]?\s*(-?\d[\d.]*)")
    if effl is None:
        # bugs/0371: Rodenstock/LINOS-style sheets (Apo-Rodagon etc.) write
        # "focal length f' (mm) 74.9" -- lower case, an f' token between label and
        # value, and PARENTHESISED units. Accept both unit styles generally.
        effl = _first_float(
            text, r"(?i)focal\s+len\w*\s*f?['’]?\s*[\[(]\s*mm\s*[\])]\s*(-?\d+\.?\d*)"
        )
    if effl is None:
        # bugs/0658 (error.png #85-869): the Edmund FIXED-FOCAL stock page writes the
        # row as "Focal Length FL (mm):35.00" -- the FL token between the label and
        # the parenthesised unit defeats every pattern above.
        effl = _first_float(
            text, r"(?i)Focal\s+Length\s+FL\s*\(\s*mm\s*\)\s*:?\s*(-?\d+\.?\d*)"
        )
    designation_fno: float | None = None
    if effl is None:
        # bugs/0565: LAST resort -- a drawing title block whose labels and values were
        # delaminated by the flattened text extraction. See model_designation_cardinals.
        effl, designation_fno = model_designation_cardinals(text)
    if effl is None:
        # bugs/0653: a fixed-conjugate TELECENTRIC sheet (Edmund CompactTL) states no
        # focal length at all -- the conjugates derive it. Fully self-contained
        # (magnification + WD + housing length + mount flange, all corroborated).
        telecentric = telecentric_conjugate_cardinals(text)
        if telecentric is not None:
            return telecentric
    if effl is None or not (math.isfinite(effl) and abs(effl) > 1e-6):
        return None

    cardinals = DatasheetCardinals(effl=abs(effl))
    cardinals.telecentric = re.search(r"(?i)telecentric", text) is not None
    cardinals.front_focal = _first_float(text, r"(?<![A-Za-z'])SF\s*\[mm\]\s*(-?\d[\d.]*)")
    cardinals.back_focal = _first_float(text, r"S'F'\s*\[mm\]\s*(-?\d[\d.]*)")
    cardinals.hh = _first_float(text, r"HH'\s*\[mm\]\s*(-?\d[\d.]*)")
    # bugs/0371: the same rows in the (mm)-style sheets, with an optional "*)"
    # in-air footnote marker between the unit and the value. The number token is
    # kept tight ((-?\d+\.?\d*)) so a column-glued run like "-44.2f-stop0" still
    # yields the clean leading value. HH'/span are deliberately NOT extended to
    # the (mm) style: those rows glue their columns ("-14.355.6") and a misparse
    # would silently corrupt the solve -- SF + S'F' + EFL are sufficient for the
    # exact two-group solution, the honest subset.
    if cardinals.front_focal is None:
        cardinals.front_focal = _first_float(
            text, r"(?<![A-Za-z'])SF\s*\(\s*mm\s*\)\s*(?:\*\)\s*)?(-?\d+\.?\d*)"
        )
    if cardinals.back_focal is None:
        cardinals.back_focal = _first_float(
            text, r"S'F'\s*\(\s*mm\s*\)\s*(?:\*\)\s*)?(-?\d+\.?\d*)"
        )
    # Sigma d row: "d [mm] Σ 43.19" -- the "d" glues onto the previous number, so
    # anchor on the sigma glyph (U+03A3), the only one in the table.
    cardinals.span = _first_float(text, r"Σ\s*(-?\d[\d.]*)")
    cardinals.fno = _first_float(text, r"F/(\d+\.?\d*)\s*\.\.\.\s*F/")
    if cardinals.fno is None:
        # bugs/0658: the Edmund stock-page row "Aperture (f/#):f/1.8 - f/16" -- the
        # leading value is the fastest stop, the "fastest F-number" this field means.
        cardinals.fno = _first_float(
            text, r"(?i)Aperture\s*\(\s*f\s*/#\s*\)\s*:?\s*f?\s*/?\s*(\d+\.?\d*)"
        )
    if cardinals.fno is None:
        # bugs/0565: the designation carries the aperture too ("ELS-85/4.5"), and it is the
        # only F-number a drawing title block exposes to the flattened text.
        cardinals.fno = designation_fno
    # bugs/0789: one helper, every spelling -- see :func:`_scrape_image_circle`. It used to be
    # two lists, and the telecentric path's knew only the Edmund one.
    cardinals.image_circle = _scrape_image_circle(text)

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
    if cardinals.magnification is None:
        # bugs/0371: "magnification W [range] -1 [ -1.2 ... -0.8]" spelling -- the
        # nominal value precedes the bracketed range.
        cardinals.magnification = _first_float(
            text, r"(?i)magnification\s+\w?\s*\[range\]\s*(-?\d+\.?\d*)"
        )

    parse_optimum_working_distance(text, cardinals)  # bugs/0647

    return cardinals


def parse_optimum_working_distance(text: str, cardinals: DatasheetCardinals) -> None:
    """bugs/0647: recover the vendor's Optimum Working Distance + its pairing |m|.

    On the AZURE ELS-85 sheet the flattened text delaminates labels from values
    (bugs/0565), so the WD value cannot be paired with its label positionally --
    but it CAN be pinned by physics. With the pairing magnification m*, a real
    working distance must satisfy  f/m* < WD < f(1+1/m*)  (the principal plane
    sits INSIDE the object leg, 0 < offset < f). On the ELS soup that window
    (85, 170) admits exactly one "<n>mm" token: 142. The decoys fall out on
    their own: the back focus arrives glued as "10-4141.85mm" (matches 4141.85,
    out of window), TTL 196.8 and the 26/68/85 tokens are outside the window,
    and the EFL itself is excluded explicitly. Ambiguity (zero or 2+ survivors)
    refuses -- a wrong housing calibration is worse than none.

    Pairing rule for m*: a "0.5X,1.0X,2.0X"-style magnification list containing
    1.0 pairs the optimum with 1.0x (the vendor's own suitable-distance row
    lists the optimum under 1.0x); else a single nominal magnification from the
    sheet; else a single-entry list; else refuse."""
    effl = cardinals.effl
    if effl is None or not math.isfinite(effl) or effl <= 0.0:
        return
    if not re.search(r"(?i)optimum\s+working\s+distance", text):
        return
    mags = [
        float(v)
        for v in re.findall(r"(?<![\dA-Za-z.])(\d+(?:\.\d+)?)\s*[Xx](?![A-Za-z0-9])", text)
        if float(v) > 0.0
    ]
    pairing: float | None = None
    if any(abs(m - 1.0) < 1e-6 for m in mags):
        pairing = 1.0
    elif cardinals.magnification is not None and abs(cardinals.magnification) > 1e-9:
        pairing = abs(float(cardinals.magnification))
    elif len(set(mags)) == 1 and mags:
        pairing = mags[0]
    if pairing is None:
        return
    low, high = effl / pairing, effl * (1.0 + 1.0 / pairing)
    known = {round(float(v), 2) for v in (effl, cardinals.back_focal, cardinals.hh, cardinals.span) if v is not None}
    survivors = []
    for token in re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)mm", text):
        try:
            value = float(token)
        except ValueError:
            continue
        if not (low < value < high):
            continue
        if round(value, 2) in known:
            continue
        offset = effl * (1.0 + 1.0 / pairing) - value
        if not (0.0 < offset < effl):
            continue
        survivors.append(value)
    if len(set(survivors)) != 1:
        return
    cardinals.optimum_wd = survivors[0]
    cardinals.optimum_wd_mag = pairing
