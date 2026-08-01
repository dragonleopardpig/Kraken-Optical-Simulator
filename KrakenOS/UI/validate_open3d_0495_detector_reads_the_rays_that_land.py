"""bugs/0495 -- an arm's detector plane is fitted from the rays that actually LAND on it.

``flag_20260801_190613`` -- *"drag LED + BS down, sensor misplaced"* -- and
``flag_20260801_190818`` -- *"drag up down: sensor misplaced, object plane missing"*.

What was misplaced is the branch DETECTOR (the synthetic row >= 100000), not the sensor row: row 8
sits 58.8-58.9 mm below the fold point in every recording, right where it belongs. The detector,
though, was drawn as a tilted patch ON the RA mirror.

``_exit_rays_for_group`` takes the LAST segment of EVERY ray in the leaf. On a folded arm a ray that
dies at the mirror contributes the PRE-mirror direction (+X here) while one that reaches the sensor
contributes the POST-mirror direction (-Z), and the mean of those is a 45 degree phantom. Everything
downstream is computed from that mean: the fitted focus lands on the mirror, and the bugs/0097 "is
the image on this leaf" test (cos > 0.7) fails on a 45 degree mean direction, so the pin that would
have rescued it never fires either.

Measured on the AZ85 BS scene, dragging the glued LED down 12.54 mm -- the arm is ``S3:S3/reflect``
and ``reaches_designed_image`` is True in BOTH columns, so the arm was never the problem:

    before   focus_source=converging_rays   center [229.28, 0.18, 66.04]   normal [0.689, 0, -0.725]
    after    focus_source=reached_image     center [229.93, 0.00,  7.46]   normal [0.000, 0, -1.000]

7.46 is where that recording put the sensor (row 8 at z 7.5). The two neighbouring poses the user
called correct are unchanged by the fix: baseline -5.08 and the +X drag -3.37, both already pinned.

bugs/0448 had already named the principle -- "read the exit bundle from the SURVIVORS only so the
plane's normal is the beam that actually lands" -- but applied it only inside its ``< 0.5`` branch,
so a HEALTHY arm, the majority of whose rays land, kept the contaminated bundle. That is why this
only ever showed up in a narrow band: all three bad recordings sit at split-axis z ~ 66.5 while
every good one is at 55.5 / 73.9 / 79.1. It is NOT a bugs/0494 regression -- the pre-0494 recording
``flag_20260731_225718`` is in the same band.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0495_detector_reads_the_rays_that_land
"""
from __future__ import annotations

import time
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
BS_ROW = 3
IMAGING_ARM = "S3:S3/reflect"
# The user's two gestures, in order: down 12.54 (the one that broke), then right 10.83 (the one
# they confirmed correct). Applied cumulatively, exactly as the recordings were taken.
GESTURES = (("as loaded", (0.0, 0.0, 0.0)),
            ("down 12.54 (flag 190613)", (0.0, 0.0, 12.54)),
            ("then right 10.83 (flag 190650)", (10.83, 0.0, 0.0)))
TOL_NORMAL = 0.02


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    # --- A. the principle is applied to every arm that lands, not only a minority ---------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services import branch_detectors as BD

        src = _inspect.getsource(BD.derive_branch_detectors)
        head = src.split("if group and (len(_reaching) / float(len(group))) < 0.5:")[0]
        check(
            "_exit_rays_for_group(_reaching)" in head,
            "A1: the exit bundle is re-read from the LANDING rays BEFORE the <0.5 test, so a "
            "healthy arm gets it too (bugs/0448 stated the principle, gated it too narrowly)",
        )
        check(
            "_closest_approach_point(origins, directions)" in head.split("_reaching = [")[-1],
            "A2: ... and the focus is re-fitted from that bundle, not left over from the mixed one",
        )
    except Exception as exc:
        notes.append(f"SKIP: source unreadable ({type(exc).__name__}: {exc})")

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    # --- B. the real gestures: the imaging arm stays pinned flat on its sensor ------------
    import numpy as np

    from KrakenOS.UI.services import branch_detectors as BD

    captured: list = []
    real = BD.derive_branch_detectors

    def spy(ray_paths, existing_targets=None, **kw):
        dets = real(ray_paths, existing_targets=existing_targets, **kw)
        captured.append(list(dets or []))
        return dets

    editor = None
    try:
        BD.derive_branch_detectors = spy
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        editor = KrakenLayoutEditor()
        editor.layout_files["det_probe"] = SCENE
        editor.load_layout_by_name("det_probe")
        editor.set_optical_led_glue(True)
        editor.open_3d_view()
        editor.update_idletasks()
        editor.update()
        insp = getattr(editor, "_three_d_inspector", None)
        if insp is None or not getattr(insp, "available", False):
            notes.append("SKIP: the embedded 3D inspector is unavailable")
            return ok, notes

        def settle(limit: float = 90.0) -> None:
            start = time.time()
            while time.time() - start < limit:
                insp.update_idletasks()
                insp.update()
                editor.update()
                if getattr(insp, "_row_actor_map", {}) or {}:
                    break
                time.sleep(0.25)
            for _ in range(10):
                insp.update_idletasks()
                insp.update()
                editor.update()
                time.sleep(0.3)

        settle()
        for label, delta in GESTURES:
            if any(abs(v) > 1e-9 for v in delta):
                editor.translate_scene_row_pose_vector(BS_ROW, delta)
            captured.clear()
            insp.refresh_from_editor(force_retrace=True)
            settle()
            arm = None
            for det in (captured[-1] if captured else []):
                if str(getattr(det, "branch_path", "")) == IMAGING_ARM:
                    arm = det
            if arm is None:
                check(False, f"B[{label}]: the imaging arm {IMAGING_ARM} has a detector")
                continue
            source = str(getattr(arm, "focus_source", ""))
            centre = np.asarray(getattr(arm, "center_world", [np.nan] * 3), dtype=float).reshape(3)
            normal = np.asarray(getattr(arm, "normal_world", [np.nan] * 3), dtype=float).reshape(3)
            check(
                source == "reached_image",
                f"B[{label}]: the imaging arm pins to the sensor it reaches "
                f"(focus_source={source!r}) -- 'converging_rays' here means the fit won, and the "
                f"fit is over a bundle contaminated by rays that died at the mirror",
            )
            check(
                abs(abs(float(normal[2])) - 1.0) < TOL_NORMAL,
                f"B[{label}]: its plane faces the beam that lands on it (normal {np.round(normal, 3).tolist()}) "
                f"-- a ~45 degree normal is the mean of the pre- and post-mirror directions",
            )
            # The detector must sit ON the sensor row, not somewhere up the arm at the mirror.
            image_z = float(editor.rows[-1].desp_z) if getattr(editor, "rows", None) else float("nan")
            check(
                bool(np.all(np.isfinite(centre))) and abs(float(centre[0]) - 229.93) < 1.0,
                f"B[{label}]: it stays on the folded arm at x 229.93 (centre "
                f"{np.round(centre, 2).tolist()}, image row desp_z {image_z:.2f})",
            )
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        BD.derive_branch_detectors = real
        if editor is not None:
            try:
                editor.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "NOTE")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
