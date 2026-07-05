"""Display-free guard for bugs/0223 -- the off-thread (subprocess) preview trace must be
EXACTLY equivalent to the synchronous trace, and its capture mode must never leak into or
corrupt the synchronous path.

Architecture under test (services/trace_preview_async.py): the main thread runs the preview
pipeline in CAPTURE mode (sampling runs normally; ``_trace_preview_bundles`` records the
exact launch arrays and traces nothing), ships ``{row specs, settings, sampling mode,
captured bundles}`` to a worker process, which REPLAYS the captured launch arrays through
its own rebuilt pipeline (its sampling only picks the dispatcher branch) and returns the
raykeeper (SYSTEM detached) + the finished scene bundle; the main thread re-binds its own
system and writes the same trace state a synchronous run would have.

Because the launch arrays are captured on the main thread, there is no editor-replication
fidelity question -- but equivalence must be PROVEN, not assumed:

  (A) TWO-MIRROR AZ85 (the user's folded relay, 3249-ray cone): capture -> pickle ->
      in-process worker -> pickle -> apply produces the SAME path count, detector centre
      and every ray endpoint (atol 1e-9) as the direct synchronous trace, and binds the
      editor state (dirty=False, last_rays/_last_scene_bundle are the worker's, and the
      signature cache reports a HIT so downstream reuse sees the applied scene).
  (B) SINGLE-MIRROR AZ85: the same equivalence on the single-fold path.
  (C) NO LEAK: after a capture the flag is cleared and a subsequent SYNCHRONOUS trace still
      traces real rays (a leaked capture list would silently swallow every future trace).
  (D) SUBPROCESS: the real ``python -m ...trace_preview_async payload result`` round-trip
      (pickle file under /dev/shm) returns the same path count with no error field.
  (E) WIRED: the capture/replay choke point exists in ``_trace_preview_bundles`` and the
      capture short-circuit exists in ``_build_preview_system_rays_bundle``.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_async_trace_equivalence
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import os
import pickle
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.services.trace_preview_async import (
    apply_async_trace_result,
    capture_async_trace_payload,
    run_async_trace_payload,
    shm_scratch_dir,
)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import (
    _AZ85,
    _LAYOUTS,
    _build_editor,
)
from KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover import (
    _promote_mirror2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TRACE_PREVIEW_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "trace_preview.py"
_SCENE_TOOLS_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "three_d_scene_tools.py"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _detector(bundle):
    for target in getattr(bundle, "targets", []) or []:
        if getattr(target, "is_detector", False):
            return np.asarray(target.center_world, dtype=float).reshape(3)
    return None


def _endpoints(bundle):
    return np.asarray(
        [np.asarray(path.points_world, dtype=float)[-1][:3] for path in bundle.ray_paths]
    )


def _equivalence_case(label: str, *, promote_second: bool) -> list[Check]:
    checks: list[Check] = []
    settings = _load_python_data(_LAYOUTS / _AZ85).get("settings", {})
    editor = _quiet(_build_editor, _AZ85)
    if promote_second:
        _quiet(_promote_mirror2, editor)
    _s1, _r1, direct_bundle = _quiet(
        editor._build_preview_system_rays_bundle, update_state=True
    )
    payload, system_main = _quiet(
        capture_async_trace_payload, editor, settings=dict(settings)
    )
    capture_calls = 0 if payload is None else len(payload.get("capture") or [])
    launch_rays = 0 if payload is None else int(payload.get("total_launch_rays", 0))
    checks.append(Check(
        f"{label}: capture produces a payload (bundles recorded, single traced system)",
        payload is not None and capture_calls > 0,
        f"capture_calls={capture_calls} launch_rays={launch_rays}",
    ))
    if payload is None:
        return checks
    blob = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    result = _quiet(run_async_trace_payload, pickle.loads(blob))
    result = pickle.loads(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL))
    _s2, rays2, async_bundle = _quiet(
        apply_async_trace_result, editor, system_main, result
    )
    d1, d2 = _detector(direct_bundle), _detector(async_bundle)
    e1, e2 = _endpoints(direct_bundle), _endpoints(async_bundle)
    same_paths = len(direct_bundle.ray_paths) == len(async_bundle.ray_paths)
    checks.append(Check(
        f"{label}: worker trace is EXACTLY the synchronous trace (paths + detector + every endpoint)",
        bool(
            same_paths
            and d1 is not None and d2 is not None
            and np.allclose(d1, d2, atol=1e-9)
            and np.allclose(e1, e2, atol=1e-9)
        ),
        f"paths {len(direct_bundle.ray_paths)} vs {len(async_bundle.ray_paths)}; "
        f"detector {None if d1 is None else np.round(d1, 4)} vs {None if d2 is None else np.round(d2, 4)}",
    ))
    cache_hit = _quiet(editor._current_preview_scene_trace)
    checks.append(Check(
        f"{label}: apply binds the editor trace state (dirty=False, cache HIT on the applied scene)",
        bool(
            editor._preview_scene_trace_dirty is False
            and editor.last_rays is rays2
            and editor._last_scene_bundle is async_bundle
            and cache_hit is not None
            and cache_hit[2] is async_bundle
        ),
        f"dirty={editor._preview_scene_trace_dirty} last_rays_bound={editor.last_rays is rays2} "
        f"cache_hit={'HIT' if cache_hit is not None else 'MISS'}",
    ))
    return checks


def validate_async_trace_equivalence() -> list[Check]:
    checks: list[Check] = []

    # ============ (A) folded TWO-MIRROR relay (the user's AZ85 scene) ============ #
    checks.extend(_equivalence_case("two-mirror", promote_second=True))

    # ============ (B) SINGLE-MIRROR fold ======================================== #
    checks.extend(_equivalence_case("single-mirror", promote_second=False))

    # ============ (C) capture never leaks into the synchronous path ============= #
    editor = _quiet(_build_editor, _AZ85)
    settings = _load_python_data(_LAYOUTS / _AZ85).get("settings", {})
    payload, _system = _quiet(capture_async_trace_payload, editor, settings=dict(settings))
    flag_cleared = getattr(editor, "_preview_trace_bundle_capture", "missing") is None
    _s, _r, sync_bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    checks.append(Check(
        "capture clears its flag and a subsequent SYNC trace still traces real rays (no leak)",
        bool(flag_cleared and sync_bundle is not None and len(sync_bundle.ray_paths) > 100),
        f"flag_cleared={flag_cleared} sync_paths={0 if sync_bundle is None else len(sync_bundle.ray_paths)}",
    ))

    # ============ (D) the real subprocess round-trip ============================ #
    sub_ok = False
    sub_detail = "payload unavailable"
    if payload is not None:
        scratch = shm_scratch_dir()
        payload_path = os.path.join(scratch, "kraken_async_guard_payload.pkl")
        result_path = os.path.join(scratch, "kraken_async_guard_result.pkl")
        try:
            with open(payload_path, "wb") as handle:
                pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            proc = subprocess.run(
                [sys.executable, "-m", "KrakenOS.UI.services.trace_preview_async",
                 payload_path, result_path],
                capture_output=True, text=True, timeout=400,
            )
            with open(result_path, "rb") as handle:
                sub_result = pickle.load(handle)
            sub_paths = int(sub_result.get("ray_path_count", -1))
            sub_ok = bool(
                proc.returncode == 0
                and not sub_result.get("error")
                and sub_paths == len(sync_bundle.ray_paths)
            )
            sub_detail = (
                f"exit={proc.returncode} paths={sub_paths} (expect {len(sync_bundle.ray_paths)}) "
                f"error={str(sub_result.get('error', ''))[:120]!r}"
            )
        except Exception as exc:
            sub_detail = f"subprocess round-trip raised: {exc!r}"
        finally:
            for path in (payload_path, result_path):
                try:
                    os.remove(path)
                except OSError:
                    pass
    checks.append(Check(
        "the real subprocess entry (python -m ... payload result) reproduces the same trace",
        sub_ok, sub_detail,
    ))

    # ============ (E) wiring ==================================================== #
    try:
        preview_src = _TRACE_PREVIEW_SRC.read_text(encoding="utf-8")
        tools_src = _SCENE_TOOLS_SRC.read_text(encoding="utf-8")
    except Exception:
        preview_src = tools_src = ""
    wired = (
        "_preview_trace_bundle_capture" in preview_src
        and "_preview_trace_bundle_replay" in preview_src
        and "async trace replay underrun" in preview_src
        and "_preview_trace_bundle_capture" in tools_src
    )
    checks.append(Check(
        "the capture/replay choke point + the capture short-circuit are wired",
        wired,
        f"choke_capture={'_preview_trace_bundle_capture' in preview_src} "
        f"choke_replay={'_preview_trace_bundle_replay' in preview_src} "
        f"short_circuit={'_preview_trace_bundle_capture' in tools_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_async_trace_equivalence()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_async_trace_equivalence()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Async-trace-equivalence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
