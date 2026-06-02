"""Regression: optical STEP import is carry-first, not auto-promoted on import.

Requested UI change #2 (BRANCH_README, 2026-06-02): importing an optical STEP
must START in carry mode (orient first) and must NOT snap straight onto the
optical axis. An earlier build auto-promoted the overlay to analytic Standard
rows the moment it was imported (via a modal dialog inside
``import_optical_step``), which converted + snapped the body onto the axis with
no chance to correct orientation first.

This test calls the real ``import_optical_step`` with the file picker stubbed
and asserts the imported overlay stays an un-promoted, carryable overlay:

  * the overlay path is set;
  * no analytic rows were inserted (no ``StepAnalyticPromotion`` row, row count
    unchanged) -- i.e. it was NOT auto-promoted/snapped on import;
  * no import-time auto-promote dialog hook remains on the editor.

Promoting to analytic (which snaps to the axis) is now the explicit
"Promote STEP to Analytic Surfaces" action, whose glass-sequence prompt still
pre-fills from a Zemax sidecar -- guarded here too.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_optical_import_carry_first

Exit: 0 = pass, 1 = regression, 2 = environment can't render / no STEP fixture.
"""
from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _candidate_step_paths() -> list[Path]:
    candidates = [
        PROJECT_ROOT / "attachment" / "Lens" / "DCV" / "32996" / "step_32996.stp",
        PROJECT_ROOT / "attachment" / "Lens" / "ball_lens" / "step_63227.stp",
        PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step",
    ]
    return [path for path in candidates if path.exists()]


def _free_display() -> int:
    for num in (94, 93, 92, 91, 90):
        if not Path(f"/tmp/.X11-unix/X{num}").exists():
            return num
    return 124


def _start_xvfb(display: int, timeout: float = 15.0):
    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        return None, "Xvfb not found on PATH"
    proc = subprocess.Popen(
        [xvfb, f":{display}", "-screen", "0", "1280x900x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sock = Path(f"/tmp/.X11-unix/X{display}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return None, f"Xvfb exited early (code {proc.returncode})"
        if sock.exists():
            return proc, None
        time.sleep(0.2)
    proc.terminate()
    return None, f"Xvfb :{display} did not come up within {timeout:.0f}s"


def _ensure_display():
    if os.environ.get("DISPLAY"):
        return None, None
    display = _free_display()
    proc, err = _start_xvfb(display)
    if proc is None:
        return None, err
    os.environ["DISPLAY"] = f":{display}"
    return proc, None


def _run() -> int:
    steps = _candidate_step_paths()
    if not steps:
        print("SKIP: no optical STEP fixture available.", file=sys.stderr)
        return 2
    step_path = steps[0]

    from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor

    # Structural guard: the import-time auto-promote hook must be gone, and
    # import_optical_step must not reference it.
    if hasattr(KrakenLayoutEditor, "_offer_auto_promote_step_to_analytic"):
        print("FAIL: editor still has _offer_auto_promote_step_to_analytic (import-time auto-promote).", file=sys.stderr)
        return 1
    import_src = inspect.getsource(KrakenLayoutEditor.import_optical_step)
    if (
        "_offer_auto_promote_step_to_analytic(" in import_src
        or "promote_imported_step_to_analytic_surfaces(" in import_src
    ):
        print("FAIL: import_optical_step still promotes/snaps on import.", file=sys.stderr)
        return 1

    # The explicit promote prompt must still offer the Zemax pre-fill.
    prompt_src = inspect.getsource(Kraken3DInspector._analytic_step_material_sequence_prompt)
    if "_parse_zemax_glass_sequence" not in prompt_src:
        print("FAIL: explicit promote prompt lost the Zemax sidecar pre-fill.", file=sys.stderr)
        return 1

    app = KrakenLayoutEditor()
    try:
        app.update_idletasks()
        # Stub the file picker so import runs headless.
        app._ask_step_file = lambda *a, **k: step_path  # type: ignore[method-assign]

        def _promotion_rows() -> int:
            count = 0
            for row in list(getattr(app, "rows", []) or []):
                adv = getattr(row, "advanced", None)
                if isinstance(adv, dict) and isinstance(adv.get("StepAnalyticPromotion"), dict):
                    count += 1
            return count

        rows_before = len(app.rows)
        promo_before = _promotion_rows()

        returned = app.import_optical_step(refresh_open_3d=False)

        rows_after = len(app.rows)
        promo_after = _promotion_rows()

        failures: list[str] = []
        if returned is None or Path(returned) != step_path:
            failures.append(f"import_optical_step returned {returned!r}, expected {step_path}")
        if getattr(app, "imported_optical_step_path", None) is None:
            failures.append("imported_optical_step_path was not set (overlay missing)")
        if promo_after != promo_before:
            failures.append(
                f"import auto-promoted: StepAnalyticPromotion rows {promo_before} -> {promo_after}"
            )
        if rows_after != rows_before:
            failures.append(
                f"import inserted rows ({rows_before} -> {rows_after}); expected carry-first overlay, no new rows"
            )

        if failures:
            for msg in failures:
                print(f"FAIL: {msg}", file=sys.stderr)
            return 1

        print(
            "PASS: optical STEP import is carry-first "
            f"(overlay set, no promotion; rows {rows_before} unchanged). "
            "Explicit promote retains Zemax pre-fill."
        )
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def main() -> int:
    xvfb, err = _ensure_display()
    if err:
        print(f"SKIP: {err}", file=sys.stderr)
        return 2
    try:
        return _run()
    finally:
        if xvfb is not None:
            try:
                xvfb.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
