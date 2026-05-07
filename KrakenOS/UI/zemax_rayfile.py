"""Zemax non-sequential Source File ray database helpers.

Zemax ``NSC_SFIL`` objects reference binary ``.DAT`` ray databases.  The UI
uses these helpers to expose those files as first-class illumination sources
instead of collapsing the containing ``NONSEQCO`` surface into a dummy stop.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

import numpy as np


ZEMAX_RAYFILE_HEADER_BYTES = 208
ZEMAX_RAYFILE_RECORD_FLOATS = 7
ZEMAX_RAYFILE_RECORD_BYTES = ZEMAX_RAYFILE_RECORD_FLOATS * 4


@dataclass(frozen=True, slots=True)
class ZemaxSourceFileRef:
    """One ``NSC_SFIL`` source reference found in a Zemax non-sequential file."""

    index: int
    rayfile_path: Path
    spectrum_path: Path | None = None
    wavelength_um: float | None = None
    wavelength_min_um: float | None = None
    wavelength_max_um: float | None = None


@dataclass(frozen=True, slots=True)
class ZemaxRayfileSummary:
    """Lightweight metadata for a Zemax binary ray database."""

    path: Path
    record_count: int
    header_record_count: int | None
    source_label: str


def read_zemax_text(path: str | Path) -> str:
    """Decode a text Zemax file using the encodings seen in exported ``.zmx``."""

    payload = Path(path).read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8", "latin-1"):
        try:
            text = payload.decode(encoding)
        except UnicodeDecodeError:
            continue
        if ("SURF" in text or "MODE NSC" in text or "NSOH" in text) and ("\n" in text or "\r" in text):
            return text
    raise ValueError(f"{Path(path).name} does not look like a text Zemax file.")


def _zemax_tokens(line: str) -> list[str]:
    try:
        return shlex.split(line, comments=False, posix=True)
    except Exception:
        return line.split()


def _resolve_relative(base: Path, text: str | None) -> Path | None:
    if text is None:
        return None
    cleaned = str(text).strip().strip('"')
    if not cleaned:
        return None
    path = Path(cleaned).expanduser()
    if path.is_absolute():
        return path
    return base.parent / path


def _float_token(tokens: list[str], index: int) -> float | None:
    try:
        value = float(tokens[index])
    except Exception:
        return None
    return float(value) if np.isfinite(value) else None


def find_zemax_nsc_source_files(path: str | Path) -> list[ZemaxSourceFileRef]:
    """Return non-sequential Source File references from a text Zemax file."""

    zmx_path = Path(path)
    text = read_zemax_text(zmx_path)
    if "NSC_SFIL" not in text:
        return []

    refs: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        tokens = _zemax_tokens(line)
        if not tokens:
            continue
        key = tokens[0].upper()
        if key == "NSOH" and len(tokens) >= 2:
            object_type = tokens[1].upper()
            if object_type == "NSC_SFIL":
                if current is not None:
                    refs.append(current)
                current = {"rayfile_path": _resolve_relative(zmx_path, tokens[-1])}
                continue
            if current is not None:
                refs.append(current)
                current = None
            continue
        if current is None:
            continue
        if key == "NSCS" and len(tokens) >= 4 and tokens[1] == "7" and tokens[2] == "3":
            wavelength_min = _float_token(tokens, 7)
            wavelength_max = _float_token(tokens, 8)
            if wavelength_min is not None and wavelength_max is not None:
                current["wavelength_min_um"] = wavelength_min
                current["wavelength_max_um"] = wavelength_max
                current["wavelength_um"] = 0.5 * (wavelength_min + wavelength_max)
            if len(tokens) >= 11:
                current["spectrum_path"] = _resolve_relative(zmx_path, tokens[-1])

    if current is not None:
        refs.append(current)

    output: list[ZemaxSourceFileRef] = []
    for index, ref in enumerate(refs, start=1):
        rayfile_path = ref.get("rayfile_path")
        if not isinstance(rayfile_path, Path):
            continue
        output.append(
            ZemaxSourceFileRef(
                index=index,
                rayfile_path=rayfile_path,
                spectrum_path=ref.get("spectrum_path") if isinstance(ref.get("spectrum_path"), Path) else None,
                wavelength_um=ref.get("wavelength_um") if isinstance(ref.get("wavelength_um"), float) else None,
                wavelength_min_um=ref.get("wavelength_min_um") if isinstance(ref.get("wavelength_min_um"), float) else None,
                wavelength_max_um=ref.get("wavelength_max_um") if isinstance(ref.get("wavelength_max_um"), float) else None,
            )
        )
    return output


def zemax_rayfile_record_count(path: str | Path) -> tuple[int, int | None]:
    """Return ``(actual_records, header_records)`` for a Zemax binary rayfile."""

    ray_path = Path(path)
    size = ray_path.stat().st_size
    payload_size = size - ZEMAX_RAYFILE_HEADER_BYTES
    if payload_size < 0 or payload_size % ZEMAX_RAYFILE_RECORD_BYTES != 0:
        raise ValueError(f"{ray_path.name} is not a supported Zemax 7-float .DAT rayfile.")
    actual = payload_size // ZEMAX_RAYFILE_RECORD_BYTES
    header_records: int | None = None
    try:
        header = np.fromfile(ray_path, dtype="<i4", count=2)
        if header.size >= 2 and int(header[1]) > 0:
            header_records = int(header[1])
    except Exception:
        header_records = None
    return int(actual), header_records


def summarize_zemax_rayfile(path: str | Path) -> ZemaxRayfileSummary:
    ray_path = Path(path)
    actual, header_records = zemax_rayfile_record_count(ray_path)
    try:
        header_text = ray_path.read_bytes()[8:64].split(b"\0", 1)[0].decode("ascii", errors="ignore").strip()
    except Exception:
        header_text = ""
    return ZemaxRayfileSummary(
        path=ray_path,
        record_count=actual,
        header_record_count=header_records,
        source_label=header_text or ray_path.stem,
    )


def sample_zemax_rayfile(path: str | Path, sample_count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sample a deterministic subset of ``x,y,z,l,m,n,flux`` ray records."""

    ray_path = Path(path)
    record_count, _header_count = zemax_rayfile_record_count(ray_path)
    if record_count <= 0:
        empty = np.asarray([], dtype=float)
        return empty, empty, empty, empty, empty, empty, empty
    wanted = max(1, min(int(sample_count), int(record_count)))
    data = np.memmap(
        ray_path,
        dtype="<f4",
        mode="r",
        offset=ZEMAX_RAYFILE_HEADER_BYTES,
        shape=(record_count, ZEMAX_RAYFILE_RECORD_FLOATS),
    )
    if wanted >= record_count:
        selected = np.asarray(data, dtype=float)
    else:
        indices = np.linspace(0, record_count - 1, wanted, dtype=np.int64)
        selected = np.asarray(data[indices], dtype=float)
    selected = selected[np.all(np.isfinite(selected[:, :6]), axis=1)]
    if selected.size <= 0:
        empty = np.asarray([], dtype=float)
        return empty, empty, empty, empty, empty, empty, empty
    directions = selected[:, 3:6].astype(float)
    norms = np.linalg.norm(directions, axis=1)
    keep = norms > 1e-12
    selected = selected[keep]
    directions = directions[keep]
    norms = norms[keep]
    if selected.size <= 0:
        empty = np.asarray([], dtype=float)
        return empty, empty, empty, empty, empty, empty, empty
    directions = directions / norms[:, None]
    flux = selected[:, 6].astype(float)
    flux = np.where(np.isfinite(flux) & (flux >= 0.0), flux, 0.0)
    return (
        selected[:, 0].astype(float),
        selected[:, 1].astype(float),
        selected[:, 2].astype(float),
        directions[:, 0].astype(float),
        directions[:, 1].astype(float),
        directions[:, 2].astype(float),
        flux,
    )
