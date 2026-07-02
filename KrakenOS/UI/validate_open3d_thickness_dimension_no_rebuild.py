"""Display-free guard for bugs/0204: the thickness-dimension overlay must read each row's
world origin from the ALREADY-BUILT system, not rebuild+force-mesh the whole system per call.

The 3-D thickness-dimension overlay (services/open3d_thickness_dimensions.py) calls
``_surface_reference_world_point`` TWICE per dimension (near + far endpoint). On the folded
AZ85 RA-mirror scene that is 16 dimensions -> 32 calls per refresh. The old fallback flowed
through ``_surface_origin_for_rows`` -> ``_surface_transform_for_rows`` ->
``_build_system_from_specs(...)`` with the DEFAULT ``apply_optical_solid_output_ports=True``,
which force-meshes the promoted BK7 cube (OCC "Creating solid objects for optical elements")
ONCE PER CALL -> ~40 s / refresh (the user's "loading is exceptionally long ... rebuild of
solid elements").

The fix (services/scene_placement_commands.py ``_surface_reference_world_point``) reads the
row's origin straight from the passed system's transform list -- the mirror of
``_surface_reference_world_normal``'s ``[:3, 2]`` normal read, taking ``[:3, 3]`` instead --
and only falls back to the rebuild when no system is passed (headless callers) or it carries
no transforms.

Asserts (display-free, on the live AZ85 editor):
  1. correctness: for EVERY thickness-loop row (rows[:-1]) the fast path
     ``_surface_reference_world_point(i, system=system)`` equals the old rebuild
     ``_surface_origin_for_rows(rows, i)`` within 1e-6 mm (the fix moves no dimension);
  2. no-rebuild: the fast path triggers ZERO ``_build_system_from_specs`` rebuilds and ZERO
     ``apply_optical_solid_output_port_system_overrides`` force-meshes, where the old rebuild
     path force-meshes the cube once per row -- so a revert to the rebuild is caught.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_dimension_no_rebuild

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import (
    _AZ85,
    _ROW_SPEC_KEYS,
    _build_editor,
)
from KrakenOS.UI.layout_editor import _build_system_from_specs
import KrakenOS.UI.services.layout_table_workbench as ltw
import KrakenOS.UI.layout_editor as le  # force-mesh is imported into THIS namespace (le:189)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        specs = [{k: getattr(r, k) for k in _ROW_SPEC_KEYS} for r in editor.rows]
        if specs and getattr(editor, "metal_catalogs", None):
            specs[0]["_metal_catalogs"] = editor.metal_catalogs
        system = _build_system_from_specs(specs)  # the scene system (force-mesh applied once)

        counts = {"build": 0, "mesh": 0}
        real_build = ltw._build_system_from_specs
        real_mesh = le.apply_optical_solid_output_port_system_overrides

        def counting_build(*a, **k):
            counts["build"] += 1
            return real_build(*a, **k)

        def counting_mesh(*a, **k):
            counts["mesh"] += 1
            return real_mesh(*a, **k)

        n = len(editor.rows)

        # FAST PATH: pass the already-built system.
        ltw._build_system_from_specs = counting_build
        le.apply_optical_solid_output_port_system_overrides = counting_mesh
        fast: dict[int, object] = {}
        try:
            for i in range(n - 1):  # thickness loop is rows[:-1]
                try:
                    fast[i] = np.asarray(
                        editor._surface_reference_world_point(i, system=system), float
                    ).reshape(3)
                except Exception as exc:
                    fast[i] = f"ERR:{exc}"
        finally:
            ltw._build_system_from_specs = real_build
            le.apply_optical_solid_output_port_system_overrides = real_mesh
        fast_build, fast_mesh = counts["build"], counts["mesh"]

        # SLOW PATH: force the old rebuild (no system -> _surface_origin_for_rows).
        counts["build"] = counts["mesh"] = 0
        ltw._build_system_from_specs = counting_build
        le.apply_optical_solid_output_port_system_overrides = counting_mesh
        slow: dict[int, object] = {}
        try:
            for i in range(n - 1):
                try:
                    slow[i] = np.asarray(
                        editor._surface_origin_for_rows(editor.rows, i), float
                    ).reshape(3)
                except Exception as exc:
                    slow[i] = f"ERR:{exc}"
        finally:
            ltw._build_system_from_specs = real_build
            le.apply_optical_solid_output_port_system_overrides = real_mesh
        slow_build, slow_mesh = counts["build"], counts["mesh"]

    # --- 1. correctness -----------------------------------------------------
    max_delta = 0.0
    compared = 0
    for i in range(n - 1):
        f, s = fast.get(i), slow.get(i)
        if isinstance(f, str) or isinstance(s, str):
            if isinstance(f, str) and isinstance(s, str):
                continue  # both skip (STL / face-anchored row returns earlier) -> shared, fine
            notes.append(f"row {i}: fast/slow disagree on availability (fast={f!r} slow={s!r})")
            continue
        d = float(np.max(np.abs(f - s)))
        max_delta = max(max_delta, d)
        compared += 1
        if d >= 1e-6:
            notes.append(f"row {i}: origin mismatch |Δ|={d:.3e} mm (fast={f} slow={s})")
    if compared < 1:
        notes.append("no rows reached the shared fast/slow origin path -- guard is inert")

    # --- 2. no-rebuild ------------------------------------------------------
    if fast_build != 0 or fast_mesh != 0:
        notes.append(
            f"fast path rebuilt the system {fast_build}x / force-meshed {fast_mesh}x "
            "(expected 0/0 -- it must read the passed system's transforms)"
        )
    if slow_mesh < 1:
        notes.append(
            f"control: the old rebuild path force-meshed {slow_mesh}x (expected >=1) -- "
            "the AZ85 promoted cube may not be loading, so the guard is not exercising the regression"
        )

    ok = not notes
    notes.insert(
        0,
        f"FAST rebuilds={fast_build} force-mesh={fast_mesh}; SLOW rebuilds={slow_build} "
        f"force-mesh={slow_mesh}; rows compared={compared}; max |Δorigin|={max_delta:.2e} mm",
    )
    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
