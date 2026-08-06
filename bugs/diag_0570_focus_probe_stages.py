"""Why does ``_traced_bundle_best_focus_shift`` return None on the saved Pyrite85 BS scene?

It is the measurement BOTH the FOV solve's finisher (bugs/0490) and the right-click
"Snap detector to image plane (remove defocus)" consume, so a None there is the whole of
flag_20260806_102150 + flag_20260806_102258.  This walks its stages and prints the count at
each one, then -- for whatever rays survive -- the spread-vs-shift curve, so the sign of the
correction is measured rather than argued.

Run:
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0570_focus_probe_stages.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"


def main() -> int:
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["probe"] = SCENE
        editor.load_layout_by_name("probe")

        system, rays, bundle = editor._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        paths = list(getattr(bundle, "ray_paths", None) or [])
        print(f"bundle ray_paths: {len(paths)}")
        print("terminations:", dict(collections.Counter(
            str(getattr(p, "termination_reason", "")) for p in paths
        )))

        targets = list(getattr(bundle, "targets", None) or [])
        detectors = [t for t in targets if bool(getattr(t, "is_detector", False))]
        print(f"targets: {len(targets)} | detectors: {len(detectors)}")
        for t in detectors:
            meta = getattr(t, "metadata", None) or {}
            print(
                f"   detector centre={np.round(np.asarray(t.center_world, dtype=float), 3).tolist()} "
                f"normal={np.round(np.asarray(t.normal_world, dtype=float), 3).tolist()} "
                f"focus_source={meta.get('focus_source')!r}"
            )
        if not detectors:
            print("-> no detector target: _traced_bundle_best_focus_shift returns None here")
            return 0
        detector = detectors[-1]
        normal = np.asarray(detector.normal_world, dtype=float).reshape(3)
        normal = normal / max(float(np.linalg.norm(normal)), 1e-12)

        candidates = []
        for path in paths:
            if str(getattr(path, "termination_reason", "")) != "target_termination":
                continue
            pts = np.asarray(getattr(path, "points_world", []), dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            step = pts[-1, :3] - pts[-2, :3]
            length = float(np.linalg.norm(step))
            if length <= 1e-9:
                continue
            candidates.append((pts[0, :3].copy(), pts[-1, :3].copy(), step / length))
        print(f"candidates (target_termination with a usable final segment): {len(candidates)}")
        if not candidates:
            print("-> STAGE 'candidates' is what returns None")
            return 0

        stations = editor._row_z_positions()
        row0 = editor.rows[0]
        object_point = np.asarray(
            [float(row0.desp_x), float(row0.desp_y), float(stations[0]) + float(row0.desp_z)],
            dtype=float,
        )
        launches = np.asarray([c[0] for c in candidates], dtype=float)
        offsets = np.linalg.norm(launches - object_point, axis=1)
        nearest = float(np.min(offsets))
        spread = float(np.max(offsets) - nearest)
        tolerance = max(1.0e-3, 0.02 * spread)
        keep = [c for c, o in zip(candidates, offsets) if o <= nearest + tolerance]
        print(
            f"object_point={np.round(object_point,3).tolist()} | launch offsets: "
            f"min {nearest:.3f} max {float(np.max(offsets)):.3f} spread {spread:.3f} "
            f"tolerance {tolerance:.4f} -> axial rays kept: {len(keep)} (needs >= 4)"
        )
        if len(keep) < 4:
            print("-> STAGE 'axial field' is what returns None")
            wide = [c for c, o in zip(candidates, offsets) if o <= nearest + max(1.0, 0.10 * spread)]
            print(f"   (a 10%-of-spread window would keep {len(wide)})")
            keep = wide
        if len(keep) < 4:
            return 0

        origins = np.asarray([c[1] for c in keep], dtype=float)
        directions = np.asarray([c[2] for c in keep], dtype=float)

        def spread_at(shift: float) -> float:
            along = float(shift) / np.clip(directions @ normal, 1.0e-6, None)
            pts = origins + directions * along[:, None]
            centred = pts - pts.mean(axis=0)
            transverse = centred - np.outer(centred @ normal, normal)
            return float(np.sqrt((transverse ** 2).sum(axis=1).mean()))

        print("\nspread (mm RMS) along the detector normal:")
        for s in (-120, -90, -60, -40, -20, -10, 0, 10, 20, 40, 60, 90, 120):
            print(f"   shift {s:+5d} -> {spread_at(float(s)):9.4f}")
        grid = np.linspace(-150.0, 150.0, 601)
        values = [spread_at(float(g)) for g in grid]
        best = float(grid[int(np.argmin(values))])
        print(f"\nwaist at shift {best:+.3f} mm along the detector normal "
              f"(RMS {min(values):.5f} vs {spread_at(0.0):.5f} at the detector)")
        centre = np.asarray(detector.center_world, dtype=float)
        moved = centre + normal * best
        print(f"detector centre {np.round(centre,3).tolist()} -> waist at {np.round(moved,3).tolist()}")
        mirror = None
        for i, row in enumerate(editor.rows):
            promo = (getattr(row, "advanced", None) or {}).get("StepOverlayPromotion") or {}
            if promo and not promo.get("station_neutral"):
                from KrakenOS.UI.services import row_placement

                mirror = np.asarray(row_placement.world_pose(editor, i).position, dtype=float)
        if mirror is not None:
            print(
                f"fold mirror at {np.round(mirror,3).tolist()}: sensor->mirror "
                f"{float(np.linalg.norm(mirror-centre)):.3f} mm now, "
                f"{float(np.linalg.norm(mirror-moved)):.3f} mm at the waist "
                f"({'TOWARD the mirror' if np.linalg.norm(mirror-moved) < np.linalg.norm(mirror-centre) else 'AWAY from the mirror'})"
            )
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
