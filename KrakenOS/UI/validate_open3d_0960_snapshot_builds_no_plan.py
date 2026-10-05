"""Guard for bugs/0960: a flag (and a recorded event) builds no STEP trace plan; a refused plan is kept.

Measured on om05a_folded: every flag froze the app for 5 s (M90aPro) to 12 s (X299-SSD). The
recorder's scene snapshot -- taken by every flag, and by every recorded mouse and key event while a
recording runs -- asked `_live_step_overlay_trace_rows()` for the optical STEP overlay's trace pose.
That builds the overlay's trace plan (an STL inspection and a STEP reconstruction, 8-12 s). On
om05a the plan's injection is then REFUSED (bugs/0725: it would move the sensor), and a refused
plan was never cached -- so every snapshot, and every trace with the overlay (Trace Now), built it
again. For two fields that come out empty when the injection is refused.

Driven in a real Qt shell on a scene in git, the overlay's plan builder and safety check stubbed
(counted), so the claims do not depend on vendor CAD:

  C  a REFUSED plan is built once: three traces with the overlay build it once, each returns the
     model's rows unchanged and no record; a row edit builds it again, and undoing the edit builds
     nothing (the earlier rows' plan is still kept)
  A  an ACCEPTED plan is built once too (as before): three traces, one build, one record each
  S  a snapshot builds NO plan: with nothing known it records `live_trace_known: False`; after a
     refused trace it records the refusal's reason; after an accepted one, the record's decenter
     and pose source
  F  a flag builds no plan, with nothing known yet and after
  R  on om05a_folded (when its vendor CAD is on this machine): the first snapshot after a load
     builds nothing and takes under 2 s; the first trace with the overlay builds the real plan once;
     the second takes under 2 s and builds nothing
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "SNAP0960_RESULT "
SKIP_MARK = "SNAP0960_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
REAL_SCENE = Path("attachment/om05a_folded.py")
REASON = "row 3 'stub' lost its traced pose"


def _shell(scene: Path):
    import tempfile
    import time

    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.qt.app import build

    open3d_inspector.ATTACHMENT_DIR = Path(tempfile.mkdtemp(prefix="flag0960_"))   # flags of this run
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(scene)

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(2.5)
    return app, window, view, settle


def stubbed_checks() -> dict:
    from dataclasses import asdict

    from KrakenOS.UI.layout_editor import SurfaceRow

    app, window, view, settle = _shell(SCENE)
    editor, inspector = window.editor, view.inspector
    if inspector is None or not getattr(inspector, "available", False):
        return {"rows": [["X", True, "SKIP: the embedded 3D inspector is unavailable"]]}
    recorder = inspector._event_recorder
    real_path = editor._step_path_for_label
    builds: list = []
    verdict = {"reason": REASON}

    def plan(*_args, **_kwargs):
        builds.append(1)
        return {"label": "optical", "row": SurfaceRow(**asdict(editor.rows[1])), "row_index": 2,
                "row_decenter_mm": [1.0, 2.0, 3.0], "pose_source": "stub", "transient_live_trace": True}

    # the overlay exists, its plan and its safety check are stubs (set AFTER the scene settled, so
    # no refresh ever tries to load the made-up STEP file)
    editor._step_path_for_label = lambda label: Path("/stub/optical.step") if label == "optical" else real_path(label)
    editor._step_overlay_optical_solid_row_plan = plan
    editor._live_step_overlay_injection_moves_optics = lambda *_a, **_k: verdict["reason"]
    editor._live_step_overlay_trace_plan_cache = {}
    rows = []

    def optical_pose() -> dict:
        snapshot = recorder.capture_scene_snapshot()
        return dict((snapshot.step_overlay_poses or {}).get("optical", {})) if snapshot is not None else {}

    def flag() -> int:
        before = len(builds)
        bundle = inspector.flag_bug()
        prompt = window.last_flag_description_dialog
        if prompt is not None and prompt.outcome is None:
            prompt.finish("discard")
        settle(0.1)
        return len(builds) - before if bundle is not None else -1

    # ---- S, F: nothing known yet ---------------------------------------------------------------
    pose_unknown = optical_pose()
    built_by_snapshot = len(builds)
    editor._live_step_overlay_trace_plan_cache = {}      # each claim starts from nothing known
    del builds[:]
    built_by_flag_unknown = flag()
    editor._live_step_overlay_trace_plan_cache = {}
    del builds[:]

    # ---- C: refused ----------------------------------------------------------------------------
    model_rows = editor.rows
    results = [editor._live_step_overlay_trace_rows() for _ in range(3)]
    refused_builds = len(builds)
    unchanged = all(traced is model_rows and records == [] for traced, records in results)
    status = str(editor.status_var.get())
    pose_refused = optical_pose()
    built_by_flag_known = flag()
    old = float(editor.rows[1].thickness)
    editor.rows[1].thickness = old + 1.0
    editor._live_step_overlay_trace_rows()
    after_edit = len(builds)
    editor.rows[1].thickness = old
    editor._live_step_overlay_trace_rows()
    after_undo = len(builds)
    rows.append(["C", refused_builds == 1 and unchanged and "lost its traced pose" in status
                 and after_edit == 2 and after_undo == 2,
                 f"refused: plans built over three traces {refused_builds}; each returned the model's rows and no "
                 f"record: {unchanged}; status {status[:70]!r}; after a row edit {after_edit}, after undoing it "
                 f"{after_undo}"])

    # ---- A: accepted ---------------------------------------------------------------------------
    verdict["reason"] = ""
    editor._live_step_overlay_trace_plan_cache = {}
    before = len(builds)
    results = [editor._live_step_overlay_trace_rows() for _ in range(3)]
    accepted_builds = len(builds) - before
    added = [(len(traced) - len(editor.rows), len(records)) for traced, records in results]
    pose_accepted = optical_pose()
    rows.append(["A", accepted_builds == 1 and added == [(1, 1)] * 3,
                 f"accepted: plans built over three traces {accepted_builds}; (rows added, records) {added}"])

    rows.append(["S", built_by_snapshot == 0 and pose_unknown.get("live_trace_known") is False
                 and "live_trace_refused" not in pose_unknown
                 and pose_refused.get("live_trace_known") is True and pose_refused.get("live_trace_refused") == REASON
                 and pose_accepted.get("live_trace_row_decenter_mm") == [1.0, 2.0, 3.0]
                 and pose_accepted.get("live_trace_pose_source") == "stub" and "live_trace_refused" not in pose_accepted,
                 f"plans built by a snapshot with nothing known: {built_by_snapshot}; it records "
                 f"{ {k: v for k, v in pose_unknown.items() if k.startswith('live_trace')} }; after a refused trace "
                 f"{ {k: v for k, v in pose_refused.items() if k.startswith('live_trace')} }; after an accepted one "
                 f"{ {k: v for k, v in pose_accepted.items() if k.startswith('live_trace')} }"])
    rows.append(["F", built_by_flag_unknown == 0 and built_by_flag_known == 0,
                 f"plans built by a flag: with nothing known {built_by_flag_unknown}, after a trace {built_by_flag_known}"])
    return {"rows": rows}


def real_checks() -> dict:
    import time

    app, window, view, settle = _shell(REAL_SCENE)
    editor, inspector = window.editor, view.inspector
    if inspector is None or not getattr(inspector, "available", False):
        return {"rows": [["R", True, "SKIP: the embedded 3D inspector is unavailable"]]}
    path = editor._step_path_for_label("optical")
    if path is None or not Path(path).exists():
        return {"rows": [["R", True, f"SKIP: om05a's optical STEP is not on this machine ({path})"]]}
    real = editor._step_overlay_optical_solid_row_plan
    builds: list = []
    editor._step_overlay_optical_solid_row_plan = lambda *a, **k: (builds.append(1), real(*a, **k))[1]
    editor._live_step_overlay_trace_plan_cache = {}
    recorder = inspector._event_recorder
    start = time.time()
    recorder.capture_scene_snapshot()
    snapshot_s, snapshot_builds = time.time() - start, len(builds)
    start = time.time()
    editor._live_step_overlay_trace_rows()
    first_s, first_builds = time.time() - start, len(builds)
    start = time.time()
    editor._live_step_overlay_trace_rows()
    second_s, second_builds = time.time() - start, len(builds)
    return {"rows": [["R", snapshot_builds == 0 and snapshot_s < 2.0 and first_builds == 1 and second_builds == 1
                      and second_s < 2.0,
                      f"om05a: first snapshot {snapshot_s:.2f} s, plans built {snapshot_builds}; first trace with the "
                      f"overlay {first_s:.1f} s, built {first_builds}; second {second_s:.2f} s, built "
                      f"{second_builds - first_builds} more"]]}


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0960_snapshot_builds_no_plan import stubbed_checks, real_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])["rows"]
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = _run("stubbed_checks()")
    rows += _run("real_checks()") if REAL_SCENE.exists() else [["R", True, f"SKIP: {REAL_SCENE} absent"]]
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
