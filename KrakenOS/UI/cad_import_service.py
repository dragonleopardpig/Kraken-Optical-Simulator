from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import struct
from pathlib import Path


OPTICAL_SOLID_CAD_SUFFIXES = {".step", ".stp", ".iges", ".igs"}
OPTICAL_SOLID_STL_SUFFIXES = {".stl"}


def _cache_stem(path: Path) -> tuple[str, str]:
    stat = Path(path).stat()
    stamp = f"{int(stat.st_mtime)}_{int(stat.st_size)}"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(path).stem)
    return safe_name, stamp


def cached_cad_mesh_path(path: Path, cache_dir: Path) -> Path:
    cache_dir = Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name, stamp = _cache_stem(Path(path).expanduser())
    return cache_dir / f"{safe_name}_{stamp}.stl"


def cached_outer_cad_mesh_path(path: Path, solid_indices: tuple[int, ...], cache_dir: Path) -> Path:
    cache_dir = Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name, stamp = _cache_stem(Path(path).expanduser())
    solid_tag = "_".join(str(index) for index in solid_indices)
    return cache_dir / f"{safe_name}_{stamp}.outer_{solid_tag}.stl"


def cached_cad_reference_path(path: Path, solid_indices: tuple[int, ...], cache_dir: Path) -> Path:
    cache_dir = Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name, stamp = _cache_stem(Path(path).expanduser())
    solid_tag = "_".join(str(index) for index in solid_indices)
    return cache_dir / f"{safe_name}_{stamp}.ref_{solid_tag}.json"


def cached_cad_section_path(path: Path, solid_indices: tuple[int, ...], cache_dir: Path) -> Path:
    cache_dir = Path(cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name, stamp = _cache_stem(Path(path).expanduser())
    solid_tag = "_".join(str(index) for index in solid_indices)
    return cache_dir / f"{safe_name}_{stamp}.section_v3_{solid_tag}.json"


def python_with_import(module_name: str, *, candidates: tuple[str, ...] | None = None) -> str:
    candidate_list: list[str] = []
    default_candidates = (
        sys.executable,
        shutil.which("python3"),
        "/run/current-system/sw/bin/python3",
    )
    for candidate in candidates or default_candidates:
        if candidate and candidate not in candidate_list:
            candidate_list.append(candidate)
    for candidate in candidate_list:
        try:
            result = subprocess.run(
                [candidate, "-c", f"import {module_name}"],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            continue
        if result.returncode == 0:
            return candidate
    raise RuntimeError(f"No python interpreter with '{module_name}' available")


def stl_mesh_has_facets(path: Path) -> bool:
    path = Path(path).expanduser()
    try:
        stat = path.stat()
    except OSError:
        return False
    if stat.st_size <= 0:
        return False
    try:
        with path.open("rb") as handle:
            head = handle.read(4096)
            if head.lstrip().lower().startswith(b"solid"):
                return b"facet" in head.lower()
            if stat.st_size >= 84:
                handle.seek(80)
                raw_count = handle.read(4)
                if len(raw_count) == 4:
                    triangle_count = struct.unpack("<I", raw_count)[0]
                    return triangle_count > 0 and stat.st_size >= 84 + 50 * triangle_count
    except OSError:
        return False
    return stat.st_size > 128


def convert_step_to_stl(source_path: Path, target_path: Path, *, gmsh_bin: str | None = None) -> None:
    gmsh = gmsh_bin or shutil.which("gmsh")
    if gmsh is None:
        raise RuntimeError("gmsh is required for STEP/IGES import but was not found")
    source_path = Path(source_path).expanduser()
    target_path = Path(target_path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    geo_path = target_path.with_suffix(".geo")
    quoted_source = str(source_path).replace("\\", "/")
    quoted_target = str(target_path).replace("\\", "/")
    geo_path.write_text(
        "\n".join(
            [
                'SetFactory("OpenCASCADE");',
                f'Merge "{quoted_source}";',
                "Mesh.CharacteristicLengthMin = 2;",
                "Mesh.CharacteristicLengthMax = 4;",
                "Mesh.Algorithm = 6;",
                "Mesh 2;",
                f'Save "{quoted_target}";',
                "",
            ]
        ),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [gmsh, "-format", "stl", "-save_all", "-2", str(geo_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        try:
            geo_path.unlink()
        except OSError:
            pass
    if result.returncode != 0 and stl_mesh_has_facets(target_path):
        return
    if result.returncode != 0 or not stl_mesh_has_facets(target_path):
        message = (result.stderr or result.stdout or "CAD conversion failed").strip()
        if result.returncode == 0:
            message = f"CAD conversion produced an empty STL: {target_path}"
        raise RuntimeError(message.splitlines()[0] if message else "CAD conversion failed")


def _build_optical_solid_cad_mesh(source_path: Path, stl_path: Path, suffix: str) -> None:
    """Mesh a CAD source into ``stl_path``, preferring in-process OCC for STEP.

    STEP/STP goes through OpenCascade (``build_step_optical_solid_mesh``) when the
    ``KRAKENOS_BREP_OPTICAL_SOLID`` flag is on: it writes the STL from the same
    tessellation as the face metadata sidecar, so the editor can list the real
    B-Rep faces. On any failure (OCC missing, unreadable STEP) it falls back to
    the gmsh STL path -- and removes a stale sidecar first so the fallback STL is
    never mis-read as B-Rep-backed. IGES and the flag-off case use gmsh directly.
    """
    from KrakenOS.UI.services.step_optical_solid_brep import (
        brep_optical_solid_enabled,
        build_step_optical_solid_mesh,
        face_sidecar_path,
    )

    if suffix in {".step", ".stp"} and brep_optical_solid_enabled():
        try:
            build_step_optical_solid_mesh(source_path, stl_path)
            return
        except Exception:
            sidecar = face_sidecar_path(stl_path)
            try:
                sidecar.unlink()
            except OSError:
                pass
    convert_step_to_stl(source_path, stl_path)


def optical_solid_mesh_path_from_source(
    source_path: Path,
    *,
    cache_dir: Path,
    stl_suffixes: set[str] | frozenset[str] = OPTICAL_SOLID_STL_SUFFIXES,
    cad_suffixes: set[str] | frozenset[str] = OPTICAL_SOLID_CAD_SUFFIXES,
) -> tuple[Path, Path | None, str]:
    source_path = Path(source_path).expanduser()
    if not source_path.exists():
        raise FileNotFoundError(f"Optical solid file not found: {source_path}")
    suffix = source_path.suffix.lower()
    if suffix in stl_suffixes:
        return source_path, None, "STL"
    if suffix in cad_suffixes:
        stl_path = cached_cad_mesh_path(source_path, cache_dir)
        if not stl_mesh_has_facets(stl_path):
            _build_optical_solid_cad_mesh(source_path, stl_path, suffix)
        return stl_path, source_path, suffix.lstrip(".").upper()
    raise ValueError("Unsupported optical solid file. Use STL, STEP/STP, or IGES/IGS.")


def _cad_tool_path(tools_dir: Path, tool_name: str) -> Path:
    script_path = Path(tools_dir).expanduser() / tool_name
    if not script_path.exists():
        raise RuntimeError(f"CAD tool not found: {script_path}")
    return script_path


def _cad_tool_error(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    message = (result.stderr or result.stdout or fallback).strip()
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    return lines[-1] if lines else fallback


def extract_step_outer_subset_to_stl(
    source_path: Path,
    target_path: Path,
    solid_indices: tuple[int, ...],
    *,
    tools_dir: Path,
) -> None:
    script_path = _cad_tool_path(tools_dir, "cad_extract_outer_shell.py")
    python_bin = python_with_import("OCC")
    result = subprocess.run(
        [
            python_bin,
            str(script_path),
            str(source_path),
            str(target_path),
            "--solids",
            ",".join(str(index) for index in solid_indices),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not Path(target_path).exists():
        raise RuntimeError(_cad_tool_error(result, "Outer-shell extraction failed"))


def extract_step_reference(
    source_path: Path,
    target_path: Path,
    solid_indices: tuple[int, ...],
    *,
    tools_dir: Path,
) -> dict[str, object]:
    script_path = _cad_tool_path(tools_dir, "cad_detect_reference.py")
    python_bin = python_with_import("OCC")
    result = subprocess.run(
        [
            python_bin,
            str(script_path),
            str(source_path),
            "--solids",
            ",".join(str(index) for index in solid_indices),
            "--json-out",
            str(target_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not Path(target_path).exists():
        raise RuntimeError(_cad_tool_error(result, "CAD reference extraction failed"))
    return json.loads(Path(target_path).read_text(encoding="utf-8"))


def extract_step_section_profile(
    source_path: Path,
    target_path: Path,
    solid_indices: tuple[int, ...],
    *,
    tools_dir: Path,
) -> dict[str, object]:
    script_path = _cad_tool_path(tools_dir, "cad_section_profile.py")
    python_bin = python_with_import("OCC")
    result = subprocess.run(
        [
            python_bin,
            str(script_path),
            str(source_path),
            "--solids",
            ",".join(str(index) for index in solid_indices),
            "--json-out",
            str(target_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not Path(target_path).exists():
        raise RuntimeError(_cad_tool_error(result, "CAD section extraction failed"))
    return json.loads(Path(target_path).read_text(encoding="utf-8"))
