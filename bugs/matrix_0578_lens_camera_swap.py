"""The user's objective, made testable: change the imaging lens at will, change the camera at
will, then solve for FOV -- and have the machine stay sane every time.

Rather than chase one flagged combination, sweep the vendor folders and record what each
(lens, camera) pair does. Per case it loads the scene FRESH, swaps, solves 23x23, and checks
invariants that must hold for ANY pair:

  A SWAP     the swap returns a model instead of raising
  B ATTACHED the lens BODY rides its surrogate ACROSS THE SOLVE (bugs/0574).
             Deliberately NOT checked across the swap: bugs/0568 re-seats the body transversely
             onto the surrogate axis there, so "body motion == surrogate motion" is false BY
             DESIGN at that step (the first run of this harness flagged a 5.4 mm "detach" that
             was simply that re-centre). The swap's own figure is printed for information.
  C RAYS     rays actually reach the sensor (target_termination > 0)
  D SANE     no runaway: the sensor stays inside a plausible envelope for this machine
  E SOLVE    the FOV solve either applies or refuses with a message -- never silently wrecks
  F NO-WORSE the action never takes a scene that HAD rays landing and leaves it with none

Cases: every lens against the scene's own camera, every camera against the scene's own lens,
plus a seeded sample of mixed pairs (seeded so a failure is reproducible -- Math.random-style
nondeterminism would make a red row impossible to re-run).

EACH CASE RUNS IN ITS OWN PROCESS. The first cut looped in one process and got exactly one
usable row: after the first ``destroy()`` VTK warns "A TkRenderWidget is being destroyed before
its associated vtkRenderWindow", the Tk/VTK state is corrupted, and every later
``KrakenLayoutEditor()`` raises before the case can be measured. Read naively that looked like
"most vendor lens folders cannot be imported" -- a conclusion about the product drawn entirely
from a defect in the harness. One app per process, and the parent only ever parses a result line.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/matrix_0578_lens_camera_swap.py
"""
from __future__ import annotations

import random
import sys
import traceback
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"
LENS_DIR = PROJECT_ROOT / "attachment" / "Lens"
CAMERA_DIR = PROJECT_ROOT / "attachment" / "Cameras"

ATTACH_TOL_MM = 0.05
SANE_SENSOR_ABS_MM = 1500.0     # this machine is ~0.5 m end to end; 1.5 m is already absurd
SEED = 20260806


def _step_folders(root: Path) -> list[Path]:
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if any(f.suffix.lower() in (".stp", ".step") for f in d.iterdir() if f.is_file()):
            out.append(d)
    return out


def _body_centre(app, label="lens"):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        if mesh is None:
            return None
        b = np.asarray(mesh.bounds, dtype=float)
        return np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2], dtype=float)
    except Exception:
        return None


def _datum_mid(app):
    try:
        mid = app._lens_surrogate_datum_mid_world()
        return None if mid is None else np.asarray(mid, dtype=float).reshape(3)
    except Exception:
        return None


def _ray_hits(app) -> int:
    """How many rays actually terminate on the detector."""
    try:
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception:
        return -1
    n = 0
    for path in list(getattr(bundle, "ray_paths", None) or []):
        if str(getattr(path, "termination_reason", "")) == "target_termination":
            n += 1
    return n


def _sensor_z(app):
    from KrakenOS.UI.services import row_placement

    try:
        return float(np.asarray(row_placement.world_pose(app, len(app.rows) - 1).position)[2])
    except Exception:
        return float("nan")


def _attach_err(before_body, before_datum, after_body, after_datum):
    if any(v is None for v in (before_body, before_datum, after_body, after_datum)):
        return None
    return float(np.linalg.norm((after_body - before_body) - (after_datum - before_datum)))


def _run_case(lens_dir: Path, camera_dir: Path | None) -> dict:
    """One fresh scene, one swap pair, one solve. Returns a result row."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    res = {
        "lens": lens_dir.name, "camera": "(scene)" if camera_dir is None else camera_dir.name,
        "swap": "-", "camera_swap": "n/a", "attach": "-", "attach_swap": "-", "rays_before": -1, "rays_after_swap": -1,
        "rays_after_solve": -1, "sensor_z": float("nan"), "solve": "-", "notes": "",
    }
    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        res["rays_before"] = _ray_hits(app)

        if camera_dir is not None:
            # bugs/0586: replace_camera_from_folder RETURNS None on a declined import (it no
            # longer hangs on a modal). Record that, or a row reads as a camera swap that never
            # happened -- BC-GM25M12X1/X4 have no scrapeable sensor size and came back looking
            # identical to a success.
            try:
                imported = app.replace_camera_from_folder(str(camera_dir), refresh_open_3d=False)
                res["camera_swap"] = "ok" if imported is not None else "declined"
                if imported is None:
                    res["notes"] += (
                        f"camera DECLINED: {str(app.status_var.get())[:90]}; "
                    )
            except Exception as exc:
                res["camera_swap"] = f"RAISED {type(exc).__name__}"
                res["notes"] += f"camera swap raised {type(exc).__name__}: {str(exc)[:50]}; "

        b0, d0 = _body_centre(app), _datum_mid(app)
        try:
            model = app.swap_imaging_lens_from_folder(str(lens_dir), refresh=False)
            res["swap"] = "ok" if model is not None else "None"
        except Exception as exc:
            res["swap"] = f"RAISED {type(exc).__name__}"
            res["notes"] += f"{str(exc)[:70]}; "
            return res
        res["rays_after_swap"] = _ray_hits(app)

        b1, d1 = _body_centre(app), _datum_mid(app)
        try:
            solved, message = inspector._quick_estimation_service().fov_solve(
                "object", "thickness", 23.0, 23.0, None
            )
            res["solve"] = "ok" if solved else "refused"
            res["notes"] += str(message)[:90]
        except Exception as exc:
            res["solve"] = f"RAISED {type(exc).__name__}"
            res["notes"] += f"{str(exc)[:70]}; "

        b2, d2 = _body_centre(app), _datum_mid(app)
        err_swap = _attach_err(b0, d0, b1, d1)
        err_solve = _attach_err(b1, d1, b2, d2)
        # Only the SOLVE figure is an invariant -- see the module docstring.
        res["attach"] = "n/a" if err_solve is None else f"{err_solve:.4f}"
        res["attach_swap"] = "n/a" if err_swap is None else f"{err_swap:.4f}"
        res["rays_after_solve"] = _ray_hits(app)
        res["sensor_z"] = _sensor_z(app)
    except Exception as exc:
        # Keep the exception TYPE, MESSAGE and the deepest frame. The first cut truncated to 80
        # characters, which reduced every aborted case to "HARNESS Traceback (most recent call
        # last): File ..." -- enough to know it broke, useless for knowing why.
        frames = traceback.format_exc().strip().splitlines()
        where = next((l.strip() for l in reversed(frames) if l.strip().startswith("File ")), "")
        res["notes"] += f"HARNESS {type(exc).__name__}: {str(exc)[:120]} | {where[-110:]}"
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return res


def _verdict(r: dict) -> tuple[bool, str]:
    fails = []
    # A case that produced NO DATA is not a pass. The first version of this harness only failed
    # on RAISED/None, so a case that aborted before the swap printed all -1/nan and came out
    # PASS -- silent truncation reading as success, which is exactly the failure mode that makes
    # a sweep worse than useless. Missing data is its own verdict.
    if r["swap"] == "-" or r["rays_before"] < 0:
        return False, "0:no data (case aborted before it could be measured)"
    if r["swap"].startswith("RAISED") or r["swap"] == "None":
        fails.append("A:swap")
    if r["attach"] not in ("-", "n/a"):
        try:
            if float(r["attach"]) > ATTACH_TOL_MM:
                fails.append(f"B:detach {r['attach']}mm")
        except ValueError:
            pass
    if r["rays_after_solve"] == 0:
        fails.append("C:no rays")
    z = r["sensor_z"]
    if z == z and abs(z) > SANE_SENSOR_ABS_MM:
        fails.append(f"D:runaway z={z:.0f}")
    if r["solve"].startswith("RAISED"):
        fails.append("E:solve raised")
    if r["rays_before"] > 0 and r["rays_after_solve"] == 0:
        fails.append("F:made worse")
    return (not fails), ",".join(fails)


def _run_case_subprocess(lens_dir: Path, camera_dir: Path | None, timeout_s: int = 900) -> dict:
    """One case, one fresh interpreter. See the module docstring for why this is not a loop."""
    import json
    import subprocess

    cmd = [sys.executable, str(Path(__file__).resolve()), "--case", str(lens_dir)]
    if camera_dir is not None:
        cmd += ["--camera", str(camera_dir)]
    base = {
        "lens": lens_dir.name, "camera": "(scene)" if camera_dir is None else camera_dir.name,
        "swap": "-", "camera_swap": "n/a", "attach": "-", "attach_swap": "-", "rays_before": -1,
        "rays_after_swap": -1, "rays_after_solve": -1, "sensor_z": float("nan"),
        "solve": "-", "notes": "",
    }
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        base["notes"] = f"TIMEOUT after {timeout_s}s"
        return base
    for line in reversed((proc.stdout or "").splitlines()):
        if line.startswith("RESULT "):
            try:
                base.update(json.loads(line[len("RESULT "):]))
                return base
            except Exception:
                break
    tail = ((proc.stderr or proc.stdout or "").strip().splitlines() or ["no output"])[-1]
    base["notes"] = f"CHILD rc={proc.returncode}: {tail[:130]}"
    return base


def _child_main(argv) -> int:
    import json
    import faulthandler
    import signal

    # bugs/0579: several vendor folders HANG the swap rather than failing it. py-spy is not
    # installed here, so let the child dump its own stack on demand instead:
    #     kill -USR1 <pid>
    # prints the full Python traceback of every thread to stderr, which is exactly what is
    # needed to name the frame a hang is sitting in. Also arm a hard backstop so a hung child
    # leaves evidence even when nobody is watching it.
    try:
        faulthandler.enable()
        faulthandler.register(signal.SIGUSR1, all_threads=True, chain=False)
        faulthandler.dump_traceback_later(600, repeat=True, exit=False)
    except Exception:
        pass

    lens = Path(argv[argv.index("--case") + 1])
    camera = Path(argv[argv.index("--camera") + 1]) if "--camera" in argv else None
    res = _run_case(lens, camera)
    print("RESULT " + json.dumps(res, default=str), flush=True)
    return 0


def main() -> int:
    if "--case" in sys.argv:
        return _child_main(sys.argv)
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    lenses = _step_folders(LENS_DIR)
    cameras = _step_folders(CAMERA_DIR)
    print(f"{len(lenses)} lens folders, {len(cameras)} camera folders\n")

    rng = random.Random(SEED)
    cases = [(l, None) for l in lenses]
    default_lens = next((l for l in lenses if "PYRITE_45_85" in l.name), lenses[0])
    cases += [(default_lens, c) for c in cameras]
    cases += [(rng.choice(lenses), rng.choice(cameras)) for _ in range(6)]

    print(f"{'lens':34} {'camera':16} {'swap':5} {'reseat':>8} {'attach':>8} "
          f"{'rays b/s/a':>14} {'sensorZ':>10} {'solve':8} verdict")
    rows = []
    for lens_dir, camera_dir in cases:
        r = _run_case_subprocess(lens_dir, camera_dir)
        ok, why = _verdict(r)
        rows.append((r, ok, why))
        print(f"{r['lens'][:34]:34} {r['camera'][:16]:16} {r['swap'][:5]:5} {r['attach_swap']:>8} {r['attach']:>8} "
              f"{r['rays_before']:>4}/{r['rays_after_swap']:>4}/{r['rays_after_solve']:>4} "
              f"{r['sensor_z']:>10.2f} {r['solve'][:8]:8} {'PASS' if ok else 'FAIL ' + why}",
              flush=True)
        if not ok and r["notes"]:
            # Print the reason WITH the row -- the summary at the end is too late to steer a
            # long sweep, and an aborted case has no other trace.
            print(f"{'':34} {'':16} -> {r['notes'][:150]}", flush=True)

    print("\n" + "=" * 100)
    bad = [(r, w) for r, ok, w in rows if not ok]
    print(f"{len(rows) - len(bad)}/{len(rows)} pairs sane")
    for r, w in bad:
        print(f"  FAIL {r['lens']} + {r['camera']}: {w}")
        if r["notes"]:
            print(f"       {r['notes'][:150]}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
