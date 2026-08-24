"""bugs/0646: WHERE does the .py load time go?

User: "the loading of a .py file take super long time, can't you just freeze the ray
first, or don't trace the ray upon startup? Let the user click Trace Now."

This probe times the real load path stage by stage (the 3D viewers are CLOSED during a
load -- `_reset_complete_layout_runtime_state(close_viewers=True)` -- so what the user
feels is `load_layout_by_name` itself). Candidate hogs:

  - `_regenerate_missing_optical_solid_caches` (OCC meshing when caches are cold)
  - `_relearn_folded_m_correction_after_swap`   (bugs/0625 load-time re-measure: REAL traces)
  - `refresh_plot(suppress_analysis=True)`      (2D redraw; does it trace?)

Run (one heavy job at a time):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/probe_0646_load_time_breakdown.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENES = [
    PROJECT_ROOT / "attachment" / "machine_vision_ELS85.py",
    PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py",
    PROJECT_ROOT / "attachment" / "machine_vision_150mm_test.py",
]


def profile_scene(scene: Path) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    print(f"\n{'=' * 72}\n{scene.name}")
    editor = KrakenLayoutEditor()
    try:
        editor._prompt_for_missing_cad_assets = lambda: None  # modal on Xvfb

        timings: list[tuple[str, float]] = []

        def _wrap(name: str):
            original = getattr(editor, name)

            def timed(*args, **kwargs):
                t0 = time.perf_counter()
                try:
                    return original(*args, **kwargs)
                finally:
                    timings.append((name, time.perf_counter() - t0))

            setattr(editor, name, timed)

        for name in (
            "_regenerate_missing_optical_solid_caches",
            "_relearn_folded_m_correction_after_swap",
            "refresh_plot",
            "_sync_table",
            "_auto_assign_missing_elements",
            "_apply_camera_coverage_autofill",
            "_heal_negative_gaps_on_load",
        ):
            if hasattr(editor, name):
                _wrap(name)

        editor.layout_files["probe"] = scene
        t0 = time.perf_counter()
        editor.load_layout_by_name("probe")
        total = time.perf_counter() - t0

        print(f"  TOTAL load_layout_by_name: {total:8.3f} s")
        accounted = 0.0
        for name, dt in sorted(timings, key=lambda t: -t[1]):
            print(f"    {name:<48} {dt:8.3f} s")
            accounted += dt
        print(f"    {'(unaccounted: row build, settings, misc)':<48} {max(0.0, total - accounted):8.3f} s")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass


def main() -> int:
    # ONE APP PER PROCESS (the sweep-harness rule): the driver forks one subprocess per
    # scene; a second KrakenLayoutEditor after a teardown is not trustworthy.
    if len(sys.argv) > 1:
        profile_scene(Path(sys.argv[1]).resolve())
        return 0
    import subprocess

    for scene in SCENES:
        if not scene.exists():
            print(f"SKIP {scene.name}: not present")
            continue
        proc = subprocess.run(
            [sys.executable, "-u", str(Path(__file__).resolve()), str(scene)],
            capture_output=True, text=True, timeout=600,
        )
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            print(f"  WORKER FAILED ({proc.returncode}): {(proc.stderr or '')[-400:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
