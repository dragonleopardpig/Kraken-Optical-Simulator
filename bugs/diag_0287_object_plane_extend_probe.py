"""bugs/0287 gate -- the reflected coaxial flood is NEVER recorded reaching the object plane (deepest
recorded z is the cube bottom, ~202mm; the "surface 0" hits are just LED launch points at x=60). To
render the user's flip+55x78 setup we must PROPAGATE each flood ray past its last recorded hit: extend
it along the recorded OUTGOING direction (out_l/out_m/out_n) to z=0, then bin the footprint that lands
inside the object aperture.

This probe answers the empirical gate BEFORE any production change:
  (1) do the flood records actually carry a downward (out_n<0) terminal segment (the split-reflect leg)?
  (2) when extended to z=0, does a real fraction land inside the object aperture (radius ~16.3mm)?
  (3) is that object footprint 2-SIDED (fold/x dark, perp/y uniform) -- the pattern the user expects --
      rather than radial or uniform?

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0287_object_plane_extend_probe.py
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import (
    _build_runtime_system,
    _rows_from_layout_info,
    _snapshot_editor,
)


def _load_editor(path: Path):
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _flip_absorber_to_transmit(editor):
    flipped = []
    for row in editor.rows:
        adv = getattr(row, "advanced", None)
        if not isinstance(adv, dict):
            continue
        meta = adv.get("OpticalSolidFaces")
        if not isinstance(meta, dict):
            continue
        for face in meta.get("faces", []):
            if str(face.get("function", "")).strip() == "Absorber/Mechanical":
                face["function"] = "Transmit/Port"
                face["role"] = "Output"
                flipped.append(str(face.get("face_id")))
    return flipped


def _object_index(editor) -> int:
    try:
        return int(editor._source_object_coupling_object_index())
    except Exception:
        return 0


def _extend_to_object_plane(records, object_z=0.0, min_down=0.2):
    """For each record, walk its hits, find the LAST hit whose OUTGOING direction points toward the
    object plane (out_n < -min_down), and extend from that point to z=object_z. Returns (x0, y0, downnote)."""
    pts = []
    per_record_downcount = []
    sample_dump = []
    for r in records:
        hits = r.get("hits") or []
        best = None
        downs = 0
        for h in hits:
            try:
                out_n = float(h.get("out_n"))
            except Exception:
                continue
            if not np.isfinite(out_n) or out_n >= -float(min_down):
                continue
            downs += 1
            try:
                x = float(h.get("x")); y = float(h.get("y")); z = float(h.get("z"))
                ol = float(h.get("out_l")); om = float(h.get("out_m"))
            except Exception:
                continue
            if not all(np.isfinite(v) for v in (x, y, z, ol, om, out_n)):
                continue
            best = (x, y, z, ol, om, out_n, str(h.get("surface")), str(h.get("event") or h.get("event_kind") or ""))
        per_record_downcount.append(downs)
        if best is None:
            continue
        x, y, z, ol, om, on, surf, ev = best
        t = (object_z - z) / on  # on<0, z>object_z -> t>0 (forward)
        if t <= 0:
            continue
        x0 = x + t * ol
        y0 = y + t * om
        pts.append((x0, y0))
        if len(sample_dump) < 8:
            sample_dump.append(
                f"last-down hit surf={surf} ev={ev} @({x:.1f},{y:.1f},{z:.1f}) "
                f"dir=({ol:.3f},{om:.3f},{on:.3f}) -> object({x0:.2f},{y0:.2f})"
            )
    return np.asarray(pts, dtype=float), per_record_downcount, sample_dump


def _profile(px, py, half):
    """Bin (px,py) within [-half,half]^2 and report axis edge ratios (center-normalized)."""
    bins = 12
    edges = np.linspace(-half, half, bins + 1)
    H, _, _ = np.histogram2d(px, py, bins=[edges, edges])
    H = H.T  # [iy, ix]
    ny, nx = H.shape
    cy, cx = ny // 2, nx // 2
    # center 2x2 block as reference so a single empty center bin doesn't blow up the ratio
    c = float(np.mean(H[cy - 1:cy + 1, cx - 1:cx + 1])) or 1.0
    lx = 0.5 * (np.mean(H[cy - 1:cy + 1, 0]) + np.mean(H[cy - 1:cy + 1, -1])) / c
    ly = 0.5 * (np.mean(H[0, cx - 1:cx + 1]) + np.mean(H[-1, cx - 1:cx + 1])) / c
    corner = float(np.mean([H[0, 0], H[0, -1], H[-1, 0], H[-1, -1]])) / c
    x_dark, y_dark = lx < 0.85, ly < 0.85
    shape = ("RADIAL (both axes dark)" if x_dark and y_dark
             else "2-SIDED (x/fold dark, y/perp uniform)" if x_dark and not y_dark
             else "2-SIDED (y/perp dark, x/fold uniform)" if y_dark and not x_dark
             else "UNIFORM (no dark edges)")
    return f"x/fold-edge={lx:.3f} y/perp-edge={ly:.3f} corner={corner:.3f} => {shape}"


def _run(radius_x, radius_y, tag):
    path = Path("attachment/machine_vision_150mm_test.py")
    editor = _load_editor(path)
    flipped = _flip_absorber_to_transmit(editor)
    spec = {
        "source_id": "source:coax-probe", "name": "Coaxial probe LED",
        "model": "Random rectangle source", "role": "illumination",
        "physical": True, "enabled": True,
        "source_x": 60.0, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": float(radius_x), "radius_y": float(radius_y), "radius": float(max(radius_x, radius_y)),
        "cone_deg": 18.0, "ray_count": 6000, "power": 1.0,
        "wavelength": float(editor._current_wavelength()), "seed": 7,
    }
    editor.layout_scene_source_specs = [spec]

    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays

    try:
        records = editor._coupled_object_illumination_records(system, float(wavelength))
    except Exception as exc:
        print(f"[{tag}] accessor raised: {exc!r}")
        return
    obj_idx = _object_index(editor)
    obj_r = float(editor.rows[obj_idx].diameter) / 2.0

    pts, downcount, dump = _extend_to_object_plane(records)
    n_records = len(records)
    n_with_down = int(np.count_nonzero(np.asarray(downcount) > 0))
    print(f"[{tag}] flipped={flipped} records={n_records} object_r={obj_r:.2f}")
    print(f"    records with a downward (out_n<0) leg = {n_with_down}")
    print(f"    extended-to-z0 points = {len(pts)}")
    if pts.size:
        r = np.hypot(pts[:, 0], pts[:, 1])
        in_ap = int(np.count_nonzero(r <= obj_r))
        print(f"    x0 range=[{pts[:,0].min():.1f},{pts[:,0].max():.1f}] "
              f"y0 range=[{pts[:,1].min():.1f},{pts[:,1].max():.1f}]")
        print(f"    landing inside object aperture (r<={obj_r:.1f}) = {in_ap}")
        if in_ap >= 30:
            keep = r <= obj_r
            print(f"    APERTURE FOOTPRINT: {_profile(pts[keep,0], pts[keep,1], obj_r)}")
        # also the full footprint (before aperture clip) to see the illumination shape
        half = float(max(abs(pts[:,0]).max(), abs(pts[:,1]).max(), 1.0))
        print(f"    FULL FOOTPRINT (half={half:.1f}): {_profile(pts[:,0], pts[:,1], half)}")
    for line in dump:
        print("      ", line)
    print(flush=True)


def main() -> int:
    if not Path("attachment/machine_vision_150mm_test.py").exists():
        print("fixture missing")
        return 1
    _run(radius_x=27.5, radius_y=39.0, tag="rx=27.5 ry=39.0")
    _run(radius_x=39.0, radius_y=27.5, tag="rx=39.0 ry=27.5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
