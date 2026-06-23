"""Summarize the Open 3D timing log -- a quick profile of where load / refresh time goes.

The app always writes one JSON line per stage to the timing log (no flag needed); set
``KRAKEN_OPEN3D_TRACE=1`` to also capture the deep-trace hot paths (mouse-move, pickers).

Usage, after using the app::

    python -m KrakenOS.UI.summarize_open3d_timing            # latest log
    python -m KrakenOS.UI.summarize_open3d_timing <log.jsonl>

Reads ~/.cache/krakenos/logs/open3d_timing_latest.jsonl (override $KRAKEN_OPEN3D_TIMING_LOG).
"""
from __future__ import annotations

import collections
import json
import sys

from KrakenOS.UI.services.open3d_timing import open3d_timing_log_path


def summarize(path=None) -> None:
    path = path or open3d_timing_log_path()
    try:
        rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    except FileNotFoundError:
        print(f"no timing log at {path} (run the app first)")
        return
    if not rows:
        print(f"empty timing log at {path}")
        return
    perf = [float(r.get("perf_ms", 0.0)) for r in rows]
    print(f"{path}")
    print(f"{len(rows)} events over {max(perf) - min(perf):.0f} ms\n")

    # Every event carrying duration_ms, ranked by total time spent.
    by_event: dict[str, list[float]] = collections.defaultdict(list)
    for r in rows:
        if "duration_ms" in r:
            by_event[str(r.get("event"))].append(float(r.get("duration_ms", 0.0)))
    print(f"{'event':34} {'n':>5} {'total ms':>10} {'mean':>8} {'max':>8}")
    for ev, d in sorted(by_event.items(), key=lambda kv: -sum(kv[1])):
        print(f"{ev:34} {len(d):5} {sum(d):10.0f} {sum(d) / len(d):8.1f} {max(d):8.0f}")

    # refresh_scene stage breakdown -- which part of a 3D refresh costs.
    ref = [r for r in rows if r.get("event") == "refresh_scene_timing"]
    if ref:
        print(f"\nrefresh_scene stages ({len(ref)} refresh(es)), in execution order:")
        stages = (
            "mesh_collect_ms", "prep_ms", "actor_clear_ms", "surface_actor_ms",
            "overlay_ms", "ray_actor_ms", "axis_ms", "step_overlay_ms",
            "thickness_dim_ms", "detector_overlay_ms", "finalize_ms",
        )
        for k in stages:
            vals = [float(r.get(k, 0.0)) for r in ref]
            print(f"  {k:20} total={sum(vals):8.0f}  mean={sum(vals) / len(vals):7.1f}  max={max(vals):7.0f}")
        # Whatever the named stages do not cover (inter-span slivers / un-instrumented work).
        gaps = [
            float(r.get("duration_ms", 0.0)) - sum(float(r.get(k, 0.0)) for k in stages)
            for r in ref
        ]
        print(f"  {'(unaccounted)':20} total={sum(gaps):8.0f}  mean={sum(gaps) / len(gaps):7.1f}  max={max(gaps):7.0f}")

    # system builds split by build flag (build=1 runs the slow Prerequisites3D solids).
    builds = [r for r in rows if r.get("event") == "build_system_from_specs"]
    if builds:
        print(f"\nsystem builds ({len(builds)}):")
        by_flag: dict[int, list[float]] = collections.defaultdict(list)
        for r in builds:
            by_flag[int(r.get("build", 0))].append(float(r.get("duration_ms", 0.0)))
        for flag, d in sorted(by_flag.items()):
            tag = " (Prerequisites3D solids)" if flag == 1 else ""
            print(f"  build={flag}: n={len(d)} total={sum(d):.0f}ms mean={sum(d) / len(d):.0f}ms{tag}")


if __name__ == "__main__":
    summarize(sys.argv[1] if len(sys.argv) > 1 else None)
