"""Guard for bugs/0819 -- the surrogate draws the vendor's glass, not its barrel.

User (flag_20260918_134600): "lens surrogate oversized." Measured on the flagged scene
`attachment/machine_vision_120mm_65M.py`: the Front/Rear Optical Vertex Datum discs were drawn at
46.0 mm and the Blackbox groups at 38.0 mm, against a PYRITE 5.6/120 STEP whose visible glass
measures 30.39 mm inside its 46 mm collar.

bugs/0703 taught the FOLDER IMPORT to size the discs from the measured glass, and it still does
(the same folder imports at 30.3906 today). What it could not do is reach a scene already built:
this one descends from `machine_vision_120mm_pyrite_datasheet_1x.py`, a July layout with 46.0 and
38.0 hard-coded, and nothing re-derives a saved scene's discs.

Checks:
  A  the refit itself, on a rows-only fake editor: it shrinks the block to the measured glass,
     never touches the aperture stop, never goes below it, never ENLARGES, and refuses with a
     reason when there is no block, no measurement, or nothing to do.
  B  the measured glass is preferred over the barrel at the new entry point (SKIP without the
     vendor STEP): 30.39 mm for the PYRITE 5.6/120, not its 46 mm collar.
  C  the user's scene now draws inside its vendor glass (SKIP when absent).
  D  the UI: the verb appears only when the discs are wider than the glass, and the command
     confirms, applies through the editor and redraws through `_apply_model_change`.

Display-free.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0819_the_surrogate_draws_the_vendor_glass

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/machine_vision_120mm_65M.py"
VENDOR_STEP = PROJECT_ROOT / "attachment/Lens/PYRITE_56_120_10x_V38_1097277/1097277_00155156_002.stp"
VENDOR_GLASS_MM = 30.3906
VENDOR_COLLAR_MM = 46.0


def _fake_editor(diameters, glass, *, stop_index=3):
    """A rows-only editor carrying the real mixin methods (the 0801 pattern)."""
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    class _Row:
        def __init__(self, surface, name, diameter):
            self.surface = surface
            self.name = name
            self.diameter = float(diameter)
            self.thickness = 1.0
            self.advanced = {}

    class _Editor(LayoutTableWorkbenchMixin):
        def __init__(self):
            self.rows = [
                _Row("Object", "Object", diameters[0]),
                _Row("Standard", "Front Optical Vertex Datum", diameters[1]),
                _Row("Thin Lens", "Blackbox Group 1", diameters[2]),
                _Row("Aperture", "Aperture Stop", diameters[3]),
                _Row("Thin Lens", "Blackbox Group 2", diameters[4]),
                _Row("Standard", "Rear Optical Vertex Datum", diameters[5]),
                _Row("Image", "Image / Sensor", diameters[6]),
            ]
            self.status_var = SimpleNamespace(set=lambda *_a: None)

        def append_debug(self, *_a, **_k):
            pass

        def lens_surrogate_glass_aperture_mm(self):
            return glass

    return _Editor()


def _check_refit(ok) -> None:
    # the flagged shape: 46 mm datums, 38 mm groups, 21.55 mm stop, 30.39 mm of glass
    editor = _fake_editor([90.0, 46.0, 38.0, 21.55, 38.0, 46.0, 90.0], VENDOR_GLASS_MM)
    applied, message = editor.refit_lens_surrogate_glass_to_step()
    drawn = [round(float(row.diameter), 4) for row in editor.rows]
    ok(
        applied and drawn[1:6] == [VENDOR_GLASS_MM, VENDOR_GLASS_MM, 21.55, VENDOR_GLASS_MM, VENDOR_GLASS_MM],
        f"A1: the block is drawn at the measured glass and the STOP is left alone ({drawn})",
    )
    ok(
        drawn[0] == 90.0 and drawn[6] == 90.0,
        "A2: the object and image rows are not part of the lens and are untouched",
    )
    applied_again, message_again = editor.refit_lens_surrogate_glass_to_step()
    ok(
        not applied_again and "already draws within" in message_again,
        f"A3: a second refit declines -- there is nothing left to do ({message_again[:52]})",
    )
    # never ENLARGE: a narrower authored disc is the user's
    narrow = _fake_editor([90.0, 12.0, 12.0, 8.0, 12.0, 12.0, 90.0], VENDOR_GLASS_MM)
    applied, _message = narrow.refit_lens_surrogate_glass_to_step()
    ok(
        not applied and [round(float(r.diameter), 4) for r in narrow.rows][1:6] == [12.0, 12.0, 8.0, 12.0, 12.0],
        "A4: discs already inside the glass are left exactly as the user drew them",
    )
    # a measurement BELOW the scene's own pupil is not the front element -- refuse it.
    # The real case (the AZ85 sweep): the ELS-85 STEP reads 14.16 mm against an 18.89 mm stop.
    bogus = _fake_editor([90.0, 29.0, 29.0, 18.8889, 27.26, 27.26, 90.0], 14.1585)
    applied, message = bogus.refit_lens_surrogate_glass_to_step()
    drawn = [round(float(row.diameter), 4) for row in bogus.rows]
    ok(
        not applied
        and "cannot be the front element" in message
        and drawn[1:6] == [29.0, 29.0, 18.8889, 27.26, 27.26],
        f"A5: a glass reading narrower than the pupil the scene passes is refused, with both "
        f"numbers, and nothing is drawn differently ({message[:60]})",
    )
    no_glass = _fake_editor([90.0, 46.0, 38.0, 21.55, 38.0, 46.0, 90.0], None)
    applied, message = no_glass.refit_lens_surrogate_glass_to_step()
    ok(
        not applied and "could not be measured" in message,
        f"A6: no measurement -> refuse with a reason, change nothing ({message[:48]})",
    )
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    class _NoBlock(LayoutTableWorkbenchMixin):
        def __init__(self):
            self.rows = []
            self.status_var = SimpleNamespace(set=lambda *_a: None)

        def append_debug(self, *_a, **_k):
            pass

        def lens_surrogate_glass_aperture_mm(self):
            return VENDOR_GLASS_MM

    applied, message = _NoBlock().refit_lens_surrogate_glass_to_step()
    ok(
        not applied and "no imaging-lens surrogate block" in message,
        f"A7: a scene with no lens block refuses with a reason ({message[:48]})",
    )


def _check_measurement(ok, skip) -> None:
    if not VENDOR_STEP.exists():
        skip("B: the PYRITE 5.6/120 STEP is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.services import machine_vision_folder_import as mvi
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    class _Editor(LayoutTableWorkbenchMixin):
        def _step_path_for_label(self, label):
            return VENDOR_STEP if str(label).strip().lower() == "lens" else None

    measured = _Editor().lens_surrogate_glass_aperture_mm()
    barrel = mvi._step_barrel_diameter(VENDOR_STEP)
    ok(
        measured is not None and abs(float(measured) - VENDOR_GLASS_MM) < 0.05,
        f"B1: the reader returns the vendor's GLASS ({measured}), not its collar ({barrel})",
    )
    ok(
        barrel is not None and abs(float(barrel) - VENDOR_COLLAR_MM) < 0.5 and float(measured) < float(barrel),
        f"B2: and that glass really is narrower than the barrel ({measured} < {barrel})",
    )


def _check_scene(ok, skip) -> None:
    if not SCENE.exists():
        skip("C: the flagged scene is not on this machine (Filen-synced)")
        return
    text = SCENE.read_text(encoding="utf-8")
    drawn = []
    for block in re.finditer(r"surfaces\.append\(\{(.*?)\}\)\n", text, re.S):
        name = re.search(r"'name': '([^']*)'", block.group(1))
        diameter = re.search(r"'diameter': ([\d.]+)", block.group(1))
        if name and diameter and ("Datum" in name.group(1) or "Group" in name.group(1)):
            drawn.append((name.group(1), float(diameter.group(1))))
    ok(
        bool(drawn) and all(value <= VENDOR_GLASS_MM + 0.01 for _n, value in drawn),
        f"C1: the flagged scene draws its surrogate inside the vendor glass ({drawn})",
    )


REFITTED_LAYOUTS = {
    # bugs/0819 sweep: shipped layouts brought onto their STEP's measured glass, with the
    # measurement each one was refitted to. The 150 mm pair is deliberately NOT here -- the
    # launch samples the drawn aperture, so refitting those two removes the vignetted strays
    # validate_open3d_clipped_vignetting_parity is built on (hit 27/45 -> 45/45).
    "machine_vision_120mm_pyrite_datasheet_1x.py": 30.3906,
    "machine_vision_120mm_pyrite_datasheet_05x.py": 30.3935,
}


def _check_shipped_layouts(ok, skip) -> None:
    """E: the swept layouts stay on their glass -- a regenerated file must not bring the
    barrel back."""
    root = PROJECT_ROOT / "KrakenOS/common_optical_layouts"
    for name, glass in sorted(REFITTED_LAYOUTS.items()):
        path = root / name
        if not path.exists():
            skip(f"E: {name} is not on this machine")
            continue
        text = path.read_text(encoding="utf-8")
        drawn = []
        for match in re.finditer(
            r"['\"]name['\"]:\s*['\"]([^'\"]*(?:Datum|Group)[^'\"]*)['\"][\s\S]{0,400}?"
            r"['\"]diameter['\"]:\s*([\d.]+)",
            text,
        ):
            drawn.append((match.group(1), float(match.group(2))))
        ok(
            bool(drawn) and all(value <= glass + 0.01 for _n, value in drawn),
            f"E-{name}: every datum/group disc is drawn at the vendor glass "
            f"({glass:.4g} mm; found {sorted({round(v, 4) for _n, v in drawn})})",
        )


def _check_ui(ok) -> None:
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    class _Menu:
        def __init__(self):
            self.labels = []

        def add_command(self, label=None, command=None, **_k):
            self.labels.append(str(label))

    def _labels(widest, glass):
        rows = [
            SimpleNamespace(surface="Standard", name="Front Optical Vertex Datum", diameter=widest),
            SimpleNamespace(surface="Aperture", name="Aperture Stop", diameter=21.55),
            SimpleNamespace(surface="Standard", name="Rear Optical Vertex Datum", diameter=widest),
        ]
        service = SimpleNamespace(
            editor=SimpleNamespace(
                rows=rows,
                lens_surrogate_glass_aperture_mm=lambda: glass,
                _imaging_lens_block_indices=lambda: (0, 2),
            )
        )
        bound = Open3DFaceAssignmentService._append_lens_glass_refit_action.__get__(
            service, type(service)
        )
        menu = _Menu()
        bound(menu)
        return menu.labels

    wide = _labels(VENDOR_COLLAR_MM, VENDOR_GLASS_MM)
    ok(
        len(wide) == 1 and "Refit Surrogate Glass" in wide[0] and "30.39" in wide[0] and "46" in wide[0],
        f"D1: an oversized surrogate is offered the refit, with both numbers ({wide})",
    )
    ok(
        _labels(VENDOR_GLASS_MM, VENDOR_GLASS_MM) == [],
        "D2: a surrogate already at the glass is offered nothing",
    )
    ok(
        _labels(29.0, 14.1585) == [],
        "D2b: nor is one whose STEP reads narrower than the scene's own pupil -- the command "
        "would refuse it, so the verb is not offered",
    )
    src = inspect.getsource(Open3DFaceAssignmentService._refit_lens_glass_from_context)
    ok(
        "askyesno" in src
        and "refit_lens_surrogate_glass_to_step" in src
        and "_apply_model_change()" in src,
        "D3: the command confirms, applies through the editor, and redraws through the "
        "model-change chokepoint",
    )
    menu_src = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    ok(
        "_append_lens_glass_refit_action(menu)" in menu_src,
        "D4: the lens STEP's right-click offers it",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    _check_refit(ok)
    _check_measurement(ok, skip)
    _check_scene(ok, skip)
    _check_shipped_layouts(ok, skip)
    _check_ui(ok)

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D surrogate-glass validation passed.")
        return 0
    print("Open 3D surrogate-glass validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
