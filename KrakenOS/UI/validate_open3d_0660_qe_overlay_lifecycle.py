"""Guard for bugs/0660 -- the Quick-Estimation FOV discs are owned, killable, and
never accumulate.

The user's five-flag repro (2026-08-27 15:47-48: fresh load -> changed FOV ->
"toggle Refs off. Still shwoing." -> Det off -> rays off) plus "swapped to
telecentric lens, 2 big circles": the un-killable big green circle(s) were the
QUICK-ESTIMATION overlay -- the FOV dialog's pick-disc + outline (+ previous-FOV
ghost). Three defects, all fixed and pinned here:

  1. Opening the FOV dialog silently ENABLES QE mode and the only off switch was
     the Left Panel's "Quick Estimation" checkbox -- nowhere near the Overlays menu
     the user sweeps. -> "FOV planes (QE)" now sits in the Overlays menu.
  2. `_toggle_quick_estimation` never refreshed the scene, so toggling OFF left the
     discs until some unrelated rebuild. -> it refreshes now.
  3. The overlay service did not own its actors: generations added by solve/readout
     paths outside the tracked scene rebuild lingered forever (the "2 big circles"
     = current + a stale generation). -> the service tracks every actor and wipes
     the previous set at the TOP of every add_overlays call, disabled path included.

Diagnosis scar (recorded in bugs/0659+0660): the Refs reference disc, the Det
coverage fill, and the QE pick disc are all the SAME green at the same plane --
three actors from three different toggles. Identify by OPACITY (Refs disc 0.1 /
Det fill 0.08 / QE pick 0.10 + outline 1.0) before blaming a toggle.

Checks:
  A  REAL SCENE (skip-if-absent, Tk/Xvfb): the user's sequence -- QE on + solve;
     Refs off leaves QE (independent, as designed); Det off kills the coverage
     pair; "FOV planes (QE)" off leaves the object plane EMPTY. Plus accumulation:
     two extra refreshes must not grow the z=0 actor count.
  B  WIRING: the Overlays menu carries the QE toggle; the toggle refreshes; the
     service clears at the top of add_overlays and tracks every actor.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0660_qe_overlay_lifecycle
"""

from __future__ import annotations

import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"


def _z0_actors(insp) -> list:
    found = []
    props = insp._renderer.GetViewProps()
    props.InitTraversal()
    while True:
        p = props.GetNextProp()
        if p is None:
            break
        try:
            if not p.GetVisibility():
                continue
            b = p.GetBounds()
            op = p.GetProperty().GetOpacity() if hasattr(p, "GetProperty") else None
        except Exception:
            continue
        if b and abs(b[4]) < 1e-6 and abs(b[5]) < 1e-6 and 5.0 < b[1] < 60.0 and (op or 0) > 0.01:
            found.append((round(b[1], 1), round(op, 2)))
    return found


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: A: the Basler_Telecentric scene is not in this checkout")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["_0660"] = SCENE
        editor.load_layout_by_name("_0660")
        insp = _open_3d_inspector(editor)
        insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        insp.quick_estimation_var.set(True)
        qe = insp._quick_estimation_service()
        qe.fov_solve("object", "thickness", 55.0, 55.0)
        insp.refresh_from_editor(force_retrace=True)
        _settle(insp)
        with_qe = _z0_actors(insp)
        ok(len(with_qe) >= 2, f"A1: QE on + solve draws its discs ({with_qe})")
        before_count = len(with_qe)
        insp._on_scene_visibility_changed()
        _settle(insp)
        insp._on_scene_visibility_changed()
        _settle(insp)
        ok(
            len(_z0_actors(insp)) <= before_count,
            f"A2 (accumulation): repeated refreshes do not grow the disc count "
            f"({len(_z0_actors(insp))} vs {before_count}; the flagged scene carried a "
            f"stale generation)",
        )
        insp.show_reference_surfaces_var.set(False)
        insp._on_scene_visibility_changed()
        _settle(insp)
        ok(
            len(_z0_actors(insp)) >= 2,
            "A3: Refs off leaves the QE discs (independent toggles, as designed)",
        )
        insp.show_detector_overlays_var.set(False)
        insp._on_scene_visibility_changed()
        _settle(insp)
        mid = _z0_actors(insp)
        insp.quick_estimation_var.set(False)
        insp._toggle_quick_estimation()
        _settle(insp)
        end = _z0_actors(insp)
        ok(
            len(end) < len(mid) and not end,
            f"A4 (the recurrence): 'FOV planes (QE)' off leaves the object plane EMPTY "
            f"({mid} -> {end}; the flagged discs survived every toggle)",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI import open3d_inspector as oi
    from KrakenOS.UI.panels import open3d_top_controls as tc
    from KrakenOS.UI.services import quick_estimation_overlay as qeo

    menu_src = inspect.getsource(tc)
    ok(
        "FOV planes (QE)" in menu_src and "quick_estimation_var" in menu_src,
        "B1: the Overlays menu carries the QE toggle (the Left Panel was the only "
        "switch before)",
    )
    toggle_src = inspect.getsource(oi.Open3DInspector._toggle_quick_estimation) if hasattr(
        oi, "Open3DInspector"
    ) else ""
    if not toggle_src:
        for cls in vars(oi).values():
            if isinstance(cls, type) and "_toggle_quick_estimation" in vars(cls):
                toggle_src = inspect.getsource(getattr(cls, "_toggle_quick_estimation"))
                break
    ok(
        "_on_scene_visibility_changed" in toggle_src,
        "B2: toggling QE refreshes the scene (off used to leave the discs forever)",
    )
    add_src = inspect.getsource(qeo.QuickEstimationOverlayService.add_overlays)
    ok(
        "self.clear()" in add_src.split("is_enabled")[0],
        "B3: add_overlays wipes the previous generation BEFORE the enabled gate",
    )
    svc_src = inspect.getsource(qeo.QuickEstimationOverlayService)
    ok(
        "_tracked" in svc_src and "def clear" in svc_src and svc_src.count("self._track(") >= 3,
        "B4: the service owns every actor it adds (line, dashed, pick disc)",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_real_scene), ("B", _check_wiring)):
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
        print("QE-overlay-lifecycle validation passed.")
        return 0
    print("QE-overlay-lifecycle validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
