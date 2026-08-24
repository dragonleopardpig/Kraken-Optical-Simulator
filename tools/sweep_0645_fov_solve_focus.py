"""bugs/0645 sweep — FOV solve must land the sensor at real-ray focus (or say why not)
on EVERY imaging-lens scene, in BOTH conjugate regimes.

The user's demand (flag_20260824_201312 arc): "After fixing a specific .py file, the other
.py file repeat the same problem. Please check all imaging lens, please provide general
solution rather than specific one." The 0645 fix is in the SHARED snap/solve pipeline; this
sweep is its cross-scene witness: every attachment machine-vision scene is solved for a
DEMAGNIFYING field (|m| ~ 0.42) and a MAGNIFYING field (|m| ~ 1.15, the regime the ELS85
20x20 flag exposed), and the state AFTER the solve must satisfy the honesty contract:

  FOCUSED       axial spot RMS at the sensor <= 0.25 mm (the solve delivered focus), or
  HONEST-LIMIT  the solve message carries the out-of-reach WARNING / refusal (the machine
                genuinely cannot reach the focus and the user was told).

Anything else -- defocus with a success message -- is the 0645 dishonesty and a RED row.

ONE APP PER PROCESS (the sweep-harness rule): the driver spawns one worker subprocess per
(scene, regime) case, sequentially (one heavy VTK job at a time). Fails LOUDLY on no-data.

Run (driver):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u tools/sweep_0645_fov_solve_focus.py
Run (single case, standalone repro):
    ... tools/sweep_0645_fov_solve_focus.py --scene attachment/machine_vision_ELS85.py --regime mag
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REGIME_SCALE = {"demag": 2.4, "mag": 0.87}
RMS_FOCUSED_MM = 0.25
HONEST_MARKS = ("WARNING", "beyond the fold's reach", "could not be reached", "refused")


def _axial_spot_rms(editor):
    """Axial traced spot RMS at the detector (the bugs/0576 world-frame observation)."""
    import numpy as np

    try:
        _s, _r, bundle = editor._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception:
        return float("nan"), 0
    launches, ends = [], []
    for path in list(getattr(bundle, "ray_paths", None) or []):
        # Folded scenes end landing rays with "target_termination"; SEQUENTIAL scenes
        # (measured on machine_vision_120mm_65M: 189 paths, all "image") use "image".
        if str(getattr(path, "termination_reason", "")) not in ("target_termination", "image"):
            continue
        pts = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        launches.append(pts[0, :3])
        ends.append(pts[-1, :3])
    if len(ends) < 4:
        return float("nan"), len(ends)
    try:
        stations = editor._row_z_positions()
        row0 = editor.rows[0]
        object_point = np.array(
            [float(row0.desp_x), float(row0.desp_y), float(stations[0]) + float(row0.desp_z)],
            dtype=float,
        )
    except Exception:
        object_point = np.zeros(3, dtype=float)
    launches = np.asarray(launches, dtype=float)
    offsets = np.linalg.norm(launches - object_point, axis=1)
    nearest = float(np.min(offsets))
    tolerance = max(1.0e-3, 0.02 * float(np.max(offsets) - nearest))
    keep = offsets <= nearest + tolerance
    arr = np.asarray(ends, dtype=float)[keep]
    if arr.shape[0] < 4:
        return float("nan"), int(arr.shape[0])
    return float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean())), int(arr.shape[0])


def run_worker(scene: Path, regime: str) -> int:
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    result = {"scene": scene.name, "regime": regime}
    editor = KrakenLayoutEditor()
    try:
        # Headless: the Missing-CAD-assets dialog is MODAL and invisible on Xvfb -- a scene
        # referencing CAD not in this checkout blocked a worker at 0.2% CPU until timeout.
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["sweep"] = scene
        editor.load_layout_by_name("sweep")
        inspector = _open_inspector(editor)
        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        sensor = qe.sensor_active_dimensions()
        if not sensor or len(sensor) < 2 or not all(v and float(v) > 0 for v in sensor[:2]):
            result["status"] = "SKIP"
            result["why"] = "no sensor dimensions (no registered camera on this scene)"
            print("RESULT: " + json.dumps(result), flush=True)
            return 0
        scale = REGIME_SCALE[regime]
        fov_w = round(float(sensor[0]) * scale, 2)
        fov_h = round(float(sensor[1]) * scale, 2)
        result["fov"] = [fov_w, fov_h]
        solved, message = inspector._quick_estimation_service().fov_solve(
            "object", "thickness", fov_w, fov_h, None
        )
        result["solved"] = bool(solved)
        result["message"] = str(message)
        rms, hits = _axial_spot_rms(editor)
        result["spot_rms_mm"] = None if rms != rms else round(rms, 4)
        result["axial_rays"] = int(hits)
        try:
            result["residual_mm"] = round(float(editor._traced_bundle_best_focus_shift()), 3)
        except Exception:
            result["residual_mm"] = None
        result["unreachable_mm"] = round(
            float(getattr(editor, "_snap_detector_unreachable_mm", 0.0) or 0.0), 3
        )
        result["refusal"] = str(getattr(editor, "_snap_detector_refusal", "") or "")
        honest = any(mark in result["message"] for mark in HONEST_MARKS)
        if not solved:
            # An explicit solve refusal is honest by construction.
            result["status"] = "HONEST-LIMIT"
        elif rms == rms and rms <= RMS_FOCUSED_MM:
            result["status"] = "FOCUSED"
        elif rms != rms:
            result["status"] = "NO-DATA"
        elif honest:
            result["status"] = "HONEST-LIMIT"
        else:
            result["status"] = "RED"
        print("RESULT: " + json.dumps(result), flush=True)
        return 0
    finally:
        try:
            editor.destroy()
        except Exception:
            pass


def run_driver() -> int:
    scenes = sorted((PROJECT_ROOT / "attachment").glob("machine_vision_*.py"))
    if not scenes:
        print("FAIL: no attachment machine_vision scenes found -- nothing swept.")
        return 1
    rows = []
    for scene in scenes:
        for regime in ("demag", "mag"):
            cmd = [
                sys.executable, "-u", str(Path(__file__).resolve()),
                "--scene", str(scene), "--regime", regime,
            ]
            print(f"--- {scene.name} [{regime}] ...", flush=True)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            record = None
            for line in (proc.stdout or "").splitlines():
                if line.startswith("RESULT: "):
                    record = json.loads(line[len("RESULT: "):])
            if record is None:
                record = {
                    "scene": scene.name, "regime": regime, "status": "NO-DATA",
                    "why": f"worker exit {proc.returncode}; tail: {(proc.stdout or '')[-300:]!r} "
                           f"{(proc.stderr or '')[-300:]!r}",
                }
            rows.append(record)
            print(f"    -> {record['status']}", flush=True)

    print(f"\n{'scene':<38} {'regime':<6} {'status':<12} {'RMS mm':>8} {'resid':>8} {'unreach':>8}")
    bad = 0
    for r in rows:
        rms = r.get("spot_rms_mm")
        print(
            f"{r['scene']:<38} {r['regime']:<6} {r['status']:<12} "
            f"{('n/a' if rms is None else f'{rms:.3f}'):>8} "
            f"{str(r.get('residual_mm', '')):>8} {str(r.get('unreachable_mm', '')):>8}"
        )
        if r["status"] in ("RED", "NO-DATA"):
            bad += 1
            print(f"    !! {r.get('message', r.get('why', ''))[:240]}")
    print(f"\n{len(rows)} cases: "
          f"{sum(r['status'] == 'FOCUSED' for r in rows)} FOCUSED, "
          f"{sum(r['status'] == 'HONEST-LIMIT' for r in rows)} HONEST-LIMIT, "
          f"{sum(r['status'] == 'SKIP' for r in rows)} SKIP, {bad} bad.")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene")
    parser.add_argument("--regime", choices=list(REGIME_SCALE))
    args = parser.parse_args()
    if args.scene:
        if not args.regime:
            parser.error("--scene requires --regime")
        return run_worker(Path(args.scene).resolve(), args.regime)
    return run_driver()


if __name__ == "__main__":
    raise SystemExit(main())
