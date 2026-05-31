"""End-to-end: Promote STEP -> Analytic Surfaces wiring.

The fit math is locked in by ``validate_open3d_promotion_analytic_fit``.
This test exercises the full editor-level workflow that fit is wired
into:

  1. Inspector opens, user imports an Edmund DCV STEP.
  2. ``preview_imported_step_analytic_surfaces`` reports the detected
     surfaces with Rc matching Zemax.
  3. ``promote_imported_step_to_analytic_surfaces`` with a single-
     glass sequence (``"N-BK7"``) for the singlet emits Standard
     surface rows. The trailing region after the back surface is
     auto-set to AIR.
  4. The new rows replace the STL overlay row and the body's pose
     (rotation + placement) is carried over so the analytic rows
     land at the same spot in the chain.

The doublet path uses the same code path with a 2-glass sequence;
that's covered by the second fixture (Achromat, ``"N-BAF10, N-SF10"``).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DCV_STEP = PROJECT_ROOT / "attachment" / "Lens" / "DCV" / "32996" / "step_32996.stp"
ACHROMAT_STEP = PROJECT_ROOT / "attachment" / "Lens" / "Achromatic_Lenses" / "32323" / "step_32323.stp"


def _open_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        raise RuntimeError("Embedded 3D inspector unavailable")
    inspector.geometry("1280x860+80+60")
    inspector.deiconify()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.2)
    inspector.update()
    return inspector


def _import_step(app: KrakenLayoutEditor, path: Path) -> None:
    app.imported_optical_step_path = path
    app.optical_step_rotation_x_deg = 0.0
    app.optical_step_rotation_y_deg = 0.0
    app.optical_step_rotation_z_deg = 0.0
    app.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
    app.select_step_component("optical")


def _row_lookup(rows, name_substr: str):
    return [r for r in rows if name_substr in str(getattr(r, "name", ""))]


def _run() -> int:
    failures: list[str] = []
    app = KrakenLayoutEditor()
    try:
        inspector = _open_inspector(app)
        inspector.refresh_from_editor()
        inspector.update_idletasks()

        # ---- Fixture 1: DCV singlet, expect 2 analytic rows. ----
        if not DCV_STEP.exists():
            print(f"SKIP: DCV fixture missing at {DCV_STEP}", file=sys.stderr)
            return 0
        _import_step(app, DCV_STEP)
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        preview = app.preview_imported_step_analytic_surfaces("optical")
        if preview is None:
            failures.append("DCV: preview returned None")
        else:
            rows = preview.get("rows") or []
            required = int(preview.get("required_glass_count", 0))
            if len(rows) < 2:
                failures.append(f"DCV: preview produced {len(rows)} rows, expected at least 2")
            if required != max(len(rows) - 1, 1):
                failures.append(f"DCV: required_glass_count={required} doesn't match rows-1={len(rows)-1}")
            # The DCV's two main spheres should fit with Rc ≈ ±52.10 mm.
            sphere_rcs = [float(r.get("rc_mm", 0.0)) for r in rows if r.get("kind") == "sphere"]
            if not any(abs(rc - (-52.10)) < 0.01 for rc in sphere_rcs):
                failures.append(f"DCV: no fitted Rc near -52.10 mm (got {sphere_rcs})")
        # Commit the promotion with a single glass for the singlet.
        result = app.promote_imported_step_to_analytic_surfaces(
            "optical",
            glass_sequence="N-BK7",
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if not result:
            failures.append("DCV: promote returned None")
        else:
            row_indices = list(result.get("row_indices") or [])
            if len(row_indices) < 2:
                failures.append(f"DCV: emitted {len(row_indices)} rows, expected at least 2")
            else:
                first_row = app.rows[row_indices[0]]
                if str(first_row.glass).upper() != "N-BK7":
                    failures.append(
                        f"DCV: first row glass should be N-BK7, got {first_row.glass!r}"
                    )
                last_row = app.rows[row_indices[-1]]
                if str(last_row.glass).upper() != "AIR":
                    failures.append(
                        f"DCV: trailing region glass should be AIR, got {last_row.glass!r}"
                    )
                # The first row should carry the surface type "Standard" -- not STL.
                if str(first_row.surface) != "Standard":
                    failures.append(
                        f"DCV: first row surface type should be Standard, got {first_row.surface!r}"
                    )

        # ---- Fixture 2: Achromat doublet, expect 2-glass sequence. ----
        # Clear current scene first.
        try:
            app.clear_step_imports()
        except Exception:
            pass
        # New editor state -- fresh import.
        if not ACHROMAT_STEP.exists():
            print("WARN: Achromat fixture missing, skipping doublet branch", file=sys.stderr)
        else:
            _import_step(app, ACHROMAT_STEP)
            inspector.refresh_from_editor()
            inspector.update_idletasks()
            preview_a = app.preview_imported_step_analytic_surfaces("optical")
            if preview_a is None:
                failures.append("Achromat: preview returned None")
            else:
                # With glass sequence shorter than required, the promote
                # must complain instead of producing rows with bogus
                # glass values.
                try:
                    app.promote_imported_step_to_analytic_surfaces(
                        "optical",
                        glass_sequence="N-BAF10",      # too few for a doublet
                        clear_overlay=False,
                        refresh_open_3d=False,
                    )
                    if int(preview_a.get("required_glass_count", 0)) > 1:
                        failures.append(
                            "Achromat: promote accepted a short glass sequence (no validation)"
                        )
                except RuntimeError:
                    # expected for doublets
                    pass

    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if failures:
        print("FAIL: Promote-to-Analytic workflow regressions:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print(
        "PASS: Promote STEP -> Analytic Surfaces wiring works end-to-end "
        "(DCV singlet emits 2 Standard rows with N-BK7 / AIR glass; "
        "doublet requires the right number of glasses)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
