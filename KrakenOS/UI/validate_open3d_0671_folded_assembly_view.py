"""Guard for bugs/0671 -- the Folded Assembly View: the verified straight trace
re-arranged into the real CAD world by per-arm sequences of plane reflections.

Generalises the two-arm display-fold (one +Y fold) to an ordered list of fold
planes per arm, driven by DATA persisted in the layout (``display_fold_spec``).
The om05a spec is the test vector: five 45-degree folds per arm (outer prism,
lower prism, centre prism, RA mirror 1, RA mirror 2 -- the last two shared).

Checks:
  A  FOLD ENGINE (pure): folding each arm's axis yields EXACTLY the derived
     direction sequence (A: +z,-y,-z,-y,+x,+y / B: -z,-y,+z,-y,+x,+y); every fold
     vertex lands within a small box around its component; the fold is an ISOMETRY
     (chain length preserved); the aperture filter drops a start outside the
     device face (the 54 mm FOV fields the 10.5 mm prisms cannot carry).
  B  SCENE (skip-if-absent): the om05a layout persists the spec (2 arms, 5 folds
     each, body STEP); the composer folds real traced rays for BOTH arms, draws
     the assembly body, and lands the folded sensor inside the camera column.
  C  WIRING: the Actions menu offers the view; the editor verb exists; the
     settings round-trip carries ``display_fold_spec``.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0671_folded_assembly_view
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_two_side.py"

R = 0.7071067811865476
ARM_A = {
    "origin": [-89.3, 160.95, 30.4], "u": [1, 0, 0], "v": [0, 1, 0], "n": [0, 0, 1],
    "y_center": 5.5, "y_range": [0.5, 1e9], "aperture_half": 5.0,
    "folds": [
        {"point": [-89.3, 160.95, 35.75], "normal": [0, R, R]},
        {"point": [-89.3, 149.30, 35.75], "normal": [0, R, -R]},
        {"point": [-89.3, 149.30, 6.00], "normal": [0, R, -R]},
        {"point": [-89.3, 108.15, 1.50], "normal": [R, R, 0]},
        {"point": [183.4, 108.20, 1.50], "normal": [R, -R, 0]},
    ],
}
ARM_B = {
    "origin": [-89.3, 160.95, -27.4], "u": [1, 0, 0], "v": [0, 1, 0], "n": [0, 0, -1],
    "y_center": -5.5, "y_range": [-1e9, -0.5], "aperture_half": 5.0,
    "folds": [
        {"point": [-89.3, 160.95, -32.75], "normal": [0, R, -R]},
        {"point": [-89.3, 149.30, -32.75], "normal": [0, R, R]},
        {"point": [-89.3, 149.30, -2.00], "normal": [0, R, R]},
        {"point": [-89.3, 108.15, 1.50], "normal": [R, R, 0]},
        {"point": [183.4, 108.20, 1.50], "normal": [R, -R, 0]},
    ],
}


def _axis_polyline(z_end: float, y: float, samples: int = 400) -> np.ndarray:
    z = np.linspace(0.0, z_end, samples)
    return np.column_stack([np.zeros_like(z), np.full_like(z, y), z])


def _check_engine(ok, notes) -> None:
    from KrakenOS.UI.services.folded_display_compose import arm_for_start_y, fold_polyline

    z_end = 420.0
    want = {
        "A": [(0, 0, 1), (0, -1, 0), (0, 0, -1), (0, -1, 0), (1, 0, 0), (0, 1, 0)],
        "B": [(0, 0, -1), (0, -1, 0), (0, 0, 1), (0, -1, 0), (1, 0, 0), (0, 1, 0)],
    }
    for label, arm in (("A", ARM_A), ("B", ARM_B)):
        chain = _axis_polyline(z_end, float(arm["y_center"]))
        world = fold_polyline(chain, arm)
        segs = np.diff(world, axis=0)
        lens = np.linalg.norm(segs, axis=1)
        keep = lens > 1e-9
        dirs = segs[keep] / lens[keep][:, None]
        seq: list[tuple[int, int, int]] = []
        for d in dirs:
            key = tuple(int(round(c)) for c in d)
            if not seq or key != seq[-1]:
                seq.append(key)
        ok(
            seq == want[label],
            f"A1({label}): the fold sequence is exact ({seq})",
        )
        chain_len = float(np.linalg.norm(np.diff(chain, axis=0), axis=1).sum())
        fold_len = float(lens.sum())
        ok(
            abs(chain_len - fold_len) < 1e-6,
            f"A2({label}): the fold is an ISOMETRY (chain {chain_len:.3f} == folded {fold_len:.3f} mm)",
        )
        corners = [i for i in range(1, len(world) - 1)
                   if np.linalg.norm(np.cross(world[i] - world[i - 1], world[i + 1] - world[i])) > 1e-6]
        boxes = [np.asarray(f["point"], dtype=float) for f in arm["folds"]]
        landed = 0
        for c in corners:
            if any(np.all(np.abs(world[c] - b) < 12.0) for b in boxes):
                landed += 1
        ok(
            landed >= 5,
            f"A3({label}): every fold vertex lands at its component ({landed}/5 within 12 mm)",
        )
    spec = {"arms": [ARM_A, ARM_B]}
    ok(
        arm_for_start_y(spec, 5.5) is ARM_A and arm_for_start_y(spec, -5.5) is ARM_B
        and arm_for_start_y(spec, 13.4) is None and arm_for_start_y(spec, 0.0) is None,
        "A4: the aperture filter keeps face rays and drops fields the prisms cannot carry",
    )


def _check_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: B: the om05a scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.folded_display_compose import compose_folded_assembly_plotter

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["om"] = SCENE
        editor.load_layout_by_name("om")
        spec = getattr(editor, "display_fold_spec", None)
        ok(
            isinstance(spec, dict) and len(spec.get("arms") or []) == 2
            and all(len(a.get("folds") or []) == 5 for a in spec["arms"])
            and "om05a" in str(spec.get("body_step", "")),
            "B1: the scene persists the fold spec (2 arms x 5 folds + the assembly body)",
        )
        plotter, report = compose_folded_assembly_plotter(editor, off_screen=True)
        try:
            centre = np.asarray(report.get("sensor_center") or [0, 0, 0], dtype=float)
            ok(
                report["rays"] > 100 and len(report["arms"]) == 2 and all(n > 40 for n in report["arms"])
                and report.get("body") is True,
                f"B2: both arms fold real traced rays through the assembly body "
                f"({report['arms']} rays, {report['dropped']} out-of-aperture dropped)",
            )
            ok(
                abs(centre[0] - 183.4) < 2.0 and 140.0 < centre[1] < 190.0 and abs(centre[2]) < 15.0,
                f"B3: the folded sensor lands inside the camera column ({np.round(centre, 2).tolist()})",
            )
        finally:
            try:
                plotter.close()
            except Exception:
                pass
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.panels import main_window as mw
    from KrakenOS.UI.services import layout_settings as ls
    from KrakenOS.UI.services import layout_table_workbench as wb

    ok("Folded Assembly View..." in inspect.getsource(mw), "C1: the Actions menu offers the view")
    ok(
        any("open_folded_assembly_view" in vars(c) for c in vars(wb).values() if isinstance(c, type)),
        "C2: the editor verb exists",
    )
    src = inspect.getsource(ls)
    ok(src.count("display_fold_spec") >= 2, "C3: the settings round-trip carries display_fold_spec")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_engine), ("B", _check_scene), ("C", _check_wiring)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Folded-assembly-view validation passed.")
        return 0
    print("Folded-assembly-view validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
