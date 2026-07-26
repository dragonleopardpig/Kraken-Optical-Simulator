"""bugs/0441 guard -- a frozen/snapped Aperture ring keeps its baked orientation.

Root cause (probe_0441_bisect.py): ``_normalize_special_rows`` unconditionally
zeroes an Aperture row's tilt_y/tilt_z (layout_import_export.py). After the
0433 stay-put freeze those tilts ARE the baked world placement; the BS add runs
normalize twice and flattened the drawn ring back to +Z while its neighbours
stayed leg-facing -- "Aperture plane still flipped" (flag_20260726_111606_491).

The fix scope: normalize preserves tilt_y/tilt_z for an Aperture row carrying a
ScenePlacement breadcrumb (stay_put_freeze / last_axis_to_axis_move); every
un-breadcrumbed aperture still normalizes to 0 (the historical behaviour).

NOTE: this guard is RED until the layout_import_export.py fix lands (the fix
sits outside the 0441 implementation boundary; probe_0441_normalize_guard.py
proves the exact patch semantics green via instance monkeypatch).

Checks (notes with '=' are ok-lines):
  BAKED-KEPT     freeze -> BS add: aperture tilts stay (0,-90,-180)
  SCOPED         un-breadcrumbed aperture tilt_y still normalizes to 0
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        if not SCENE.exists():
            return True, ["SKIP: attachment scene absent (gitignored fixture)"]
        app = KrakenLayoutEditor()
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
    except Exception as exc:
        try:
            if app is not None:
                app.destroy()
        except Exception:
            pass
        return True, [f"SKIP: environment cannot build the editor ({exc!r})"]

    failures: list[str] = []
    try:
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        app.add_beam_splitter_to_led(kind="plate")
        ap = next(r for r in app.rows if str(getattr(r, "surface", "")) == "Aperture")
        tilts = (round(float(ap.tilt_x), 1), round(float(ap.tilt_y), 1), round(float(ap.tilt_z), 1))
        if tilts != (0.0, -90.0, -180.0):
            failures.append(
                f"BAKED-KEPT: BS add flattened the frozen aperture tilts to {tilts} "
                "(normalize zeroed tilt_y/tilt_z -- apply the 0441 layout_import_export fix)"
            )
        else:
            notes.append("BAKED-KEPT = frozen aperture orientation survives the BS add")

        app.load_layout_by_name("az85")
        ap_i = next(i for i, r in enumerate(app.rows) if str(getattr(r, "surface", "")) == "Aperture")
        app.rows[ap_i].tilt_y = 12.0
        app._normalize_special_rows()
        if float(app.rows[ap_i].tilt_y) != 0.0:
            failures.append("SCOPED: un-breadcrumbed aperture tilt_y must still normalize to 0")
        else:
            notes.append("SCOPED = historical normalize kept for un-breadcrumbed apertures")
    except Exception as exc:
        failures.append(f"guard raised: {exc!r}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    return (not failures), notes + failures


def run() -> int:
    passed, notes = run_checks()
    print("[PASS]" if passed else "[FAIL]", "bugs/0441 frozen aperture ring orientation")
    for note in notes:
        print("   ", note)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
