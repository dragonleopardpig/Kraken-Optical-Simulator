#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_zar_module():
    try:
        from zmxtools import zar

        return zar
    except Exception:
        pass

    env_path = Path(__file__).resolve().parents[2] / "zmxtools"
    if env_path.exists():
        sys.path.insert(0, str(env_path))
        try:
            from zmxtools import zar

            return zar
        except Exception:
            pass

    raise SystemExit(
        "zmxtools is required to read .zar archives. "
        "Install it or add its repo to PYTHONPATH."
    )


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-16", "utf-16le", "utf-8", "latin1"):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("latin1", errors="replace")


def _parse_surface_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("SURF "):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _line_value(block: list[str], prefix: str) -> str | None:
    for line in block:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _parse_zmx_summary(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    blocks = _parse_surface_blocks(lines)

    surfaces: list[dict[str, Any]] = []
    station = 0.0
    for block in blocks:
        surf_index = int(block[0].split()[1])
        surface_type = _line_value(block, "  TYPE ") or ""
        comment = _line_value(block, "  COMM ") or ""
        disz_text = _line_value(block, "  DISZ ") or "0"
        diam_text = _line_value(block, "  DIAM ") or ""
        curv_text = _line_value(block, "  CURV ") or ""
        clap_text = _line_value(block, "  CLAP ") or ""
        stop = any(line.strip() == "STOP" for line in block)
        try:
            thickness_to_next = float(disz_text.split()[0])
        except Exception:
            thickness_to_next = 0.0
        try:
            diameter = float(diam_text.split()[0])
        except Exception:
            diameter = None
        try:
            curvature = float(curv_text.split()[0])
        except Exception:
            curvature = None
        surfaces.append(
            {
                "surface": surf_index,
                "station_mm": station,
                "type": surface_type,
                "comment": comment,
                "thickness_to_next_mm": thickness_to_next,
                "diameter_mm": diameter,
                "curvature_mm_inv": curvature,
                "stop": stop,
                "clear_aperture": clap_text,
            }
        )
        station += thickness_to_next

    header = {}
    for key in ("NAME ", "MODE ", "UNIT ", "ENPD ", "GCAT ", "YFLN ", "FTYP ", "ROPD "):
        for line in lines:
            if line.startswith(key):
                header[key.strip()] = line[len(key) :].strip()
                break

    wavelengths_nm: list[float] = []
    for line in lines:
        if not line.startswith("WAVM "):
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                wavelengths_nm.append(float(parts[2]) * 1000.0)
            except Exception:
                continue

    blackboxes = [surface for surface in surfaces if surface["type"] == "BLACKBOX"]
    return {
        "header": header,
        "wavelengths_nm": wavelengths_nm,
        "surface_count": len(surfaces),
        "surfaces": surfaces,
        "blackbox_surfaces": blackboxes,
        "image_station_mm": station,
    }


def inspect_archive(archive_path: Path, extract_dir: Path | None = None) -> dict[str, Any]:
    zar = _load_zar_module()
    items = list(zar.read(archive_path))
    if extract_dir is not None:
        zar.extract(archive_path, extract_dir)

    members = [{"name": item.file_name, "size_bytes": len(item.unpacked_contents)} for item in items]
    zmx_entries = [item for item in items if item.file_name.lower().endswith(".zmx")]
    zmx_summaries = []
    for item in zmx_entries:
        zmx_summaries.append(
            {
                "file_name": item.file_name,
                **_parse_zmx_summary(_decode_text(item.unpacked_contents)),
            }
        )

    return {
        "archive": str(archive_path),
        "member_count": len(members),
        "members": members,
        "zmx_models": zmx_summaries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a Zemax .zar archive and summarize .zmx/BLACKBOX content.")
    parser.add_argument("archive_path", type=Path)
    parser.add_argument("--extract-dir", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = inspect_archive(args.archive_path.expanduser().resolve(), args.extract_dir)
    output = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.json_out is not None:
        args.json_out.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
