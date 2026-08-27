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


# bugs/0307: raw literal-harvest fallback for CID-font datasheets with no ToUnicode
# (BC-OM25M12X2). Shared by the camera + lens (Path C) importers.
_LITERAL_SHOW_RE = re.compile(rb"\((?:[^()\\]|\\.)*\)", re.S)
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
        for lit in _LITERAL_SHOW_RE.finditer(stream):
            parts.append(_unescape_pdf_literal(lit.group(0)[1:-1]))
    return "".join(parts)


def extract_pdf_text(path: str | Path) -> str:
    """Best-effort plain text from a (subset-CID-font) vendor datasheet PDF.

    Pure stdlib; returns ``""`` on any failure so callers degrade gracefully.
    When the per-font ToUnicode decode comes back essentially empty -- some
    datasheets embed CID fonts with no ToUnicode map at all, plus rasterised
    tables -- fall back to harvesting the raw ``(..)`` literals, which recovers
    any English spec text that is set in simple (directly Latin-1) fonts.
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
        text = "\n".join(chunks)
        if _ascii_letter_count(text) >= _MIN_DECODED_LETTERS:
            return text
        fallback = _harvest_literal_text(objs)
        return fallback if _ascii_letter_count(fallback) > _ascii_letter_count(text) else text
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
    # bugs/0647: the vendor's Optimum Working Distance (object -> front housing rim,
    # the plane a bench user can actually measure to) and the |m| it pairs with.
    # Together with the EFL they pin the front principal plane RELATIVE TO THE
    # HOUSING: principal-behind-rim = f(1+1/m) - WD. The ELS-85 surrogate's nominal
    # symmetric principal split sat 9.45 mm too deep, so every on-screen standoff
    # read ~9 mm short of the bench.
    optimum_wd: float | None = None
    optimum_wd_mag: float | None = None

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
    if mag is None or not (0.05 <= mag <= 20.0):
        return None
    wd = _first_float(text, r"(?i)Working\s+Distance\s*\(\s*mm\s*\)\s*:?\s*(\d+\.?\d*)")
    if wd is None or not (1.0 <= wd <= 5000.0):
        return None
    # Corroboration (the bugs/0565 lesson -- a wrong prescription is far worse than a
    # clear refusal): the title of this format repeats both numbers as "0.75X, 110mm WD".
    if re.search(rf"{re.escape(f'{wd:g}')}\s*mm\s+WD", text) is None:
        return None
    if re.search(rf"(?<![\d.]){re.escape(f'{mag:g}')}X", text) is None:
        return None
    length = _first_float(text, r"(?i)(?<![a-z] )Length\s*\(\s*mm\s*\)\s*:?\s*(\d+\.?\d*)")
    if length is None or not (5.0 <= length <= 2000.0):
        return None
    mount = re.search(r"(?i)Mount\s*:?\s*(C|CS|TFL|F)\s*-?\s*Mount", text)
    if mount is None:
        return None
    flange = _MOUNT_FLANGE_MM.get(mount.group(1).upper())
    if flange is None:
        return None
    total = wd + length + flange
    effl = total / (2.0 + mag + 1.0 / mag)
    if not (1.0 <= effl <= 2000.0):
        return None
    # The bugs/0647 registration law must be satisfiable: 0 < f(1+1/m) - WD < f.
    offset = effl * (1.0 + 1.0 / mag) - wd
    if not (0.0 < offset < effl):
        return None
    cardinals = DatasheetCardinals(effl=round(effl, 4))
    cardinals.magnification = -abs(mag)  # a finite-conjugate lens inverts
    cardinals.optimum_wd = wd
    cardinals.optimum_wd_mag = abs(mag)
    # The housing length is the honest vertex span: a telecentric barrel is far
    # longer than its EFL (here 160 mm vs 70.4), and both the STEP-extent span (the
    # body's Z can be its DIAMETER when the CAD axis is not Z) and the 0.7*EFL cap
    # produce a block too short to hold the principal f(1+1/m)-WD behind the rim --
    # the bugs/0647 refit then has no room and falls back to the advisory.
    cardinals.span = round(length, 4)
    cardinals.fno = _first_float(text, r"(?i)Aperture\s*\(\s*f\s*/#\s*\)\s*:?\s*f?\s*/?\s*(\d+\.?\d*)")
    cardinals.image_circle = _first_float(
        text, r"(?i)Maximum\s+Image\s+Circle\s*\(\s*mm\s*\)\s*:?\s*(\d+\.?\d*)"
    )
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
    """
    text = extract_pdf_text(path)
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
        # bugs/0565: the designation carries the aperture too ("ELS-85/4.5"), and it is the
        # only F-number a drawing title block exposes to the flattened text.
        cardinals.fno = designation_fno
    cardinals.image_circle = _first_float(text, r"Max\.\s*sensor size\s*\[mm\]\s*(\d[\d.]*)")
    if cardinals.image_circle is None:
        # bugs/0371: "image circle max. (mm) 82" spelling.
        cardinals.image_circle = _first_float(
            text, r"(?i)image\s+circle\s+max\.?\s*[\[(]\s*mm\s*[\])]\s*(\d+\.?\d*)"
        )

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
