"""Guard: a parametric beam splitter can be RESIZED numerically in place (bugs/0423).

Flag flag_20260723_115239: "Can we have a way to resize optical component by ... input the numerical
value to the particular dimension?" The one-click "Add Beam Splitter to LED" builds a PARAMETRIC solid
(cube side / plate w x h x t x tilt). 0423 adds "Resize Beam Splitter..." -- a numerical dialog that
regenerates the solid at new dimensions and replaces it IN PLACE (pose preserved by
replace_promoted_optical_solid_step; the parametric solid is origin-centred).

Checks
------
* PERSIST      -- add_beam_splitter_to_led stores the recipe (beam_splitter_kind + beam_splitter_params)
  in the promotion dict, so the resize can read + pre-fill it.
* RESIZE-INFO  -- beam_splitter_resize_info returns (kind, params) for a BS row, None otherwise.
* RESIZE-WIRING -- resize_beam_splitter regenerates via generate_beam_splitter + replaces in place via
  replace_promoted_optical_solid_step + re-marks the row as a beam splitter.
* MENU         -- the element right-click menu offers "Resize Beam Splitter..." gated on
  beam_splitter_resize_info (only on a parametric BS), wired to open_resize_beam_splitter_dialog.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bs_resize

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _check_persist(failures, notes):
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    src = inspect.getsource(ScenePlacementMixin.add_beam_splitter_to_led)
    for token in ('promotion["beam_splitter_kind"] = kind', 'promotion["beam_splitter_params"] = dict(bs_params)'):
        if token not in src:
            failures.append(f"PERSIST: add_beam_splitter_to_led must store the recipe ({token!r})")
    if not [f for f in failures if f.startswith("PERSIST")]:
        notes.append("persist = add_beam_splitter_to_led stores kind + params in the promotion dict")


def _check_resize_info(failures, notes):
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    class _Row:
        def __init__(self, advanced):
            self.advanced = advanced

    class _Shim(ScenePlacementMixin):
        def __init__(self, rows):
            self.rows = rows

    bs = _Row({"StepOverlayPromotion": {"beam_splitter": True, "beam_splitter_kind": "plate",
                                        "beam_splitter_params": {"width_mm": 50.0, "height_mm": 50.0,
                                                                 "thickness_mm": 2.0, "tilt_deg": 45.0}}})
    cube = _Row({"StepOverlayPromotion": {"beam_splitter": True, "beam_splitter_kind": "cube",
                                          "beam_splitter_params": {"side_mm": 25.0}}})
    non = _Row({"StepOverlayPromotion": {}})  # promoted but not a BS
    plain = _Row({})
    shim = _Shim([bs, cube, non, plain])
    if shim.beam_splitter_resize_info(0) != ("plate", {"width_mm": 50.0, "height_mm": 50.0, "thickness_mm": 2.0, "tilt_deg": 45.0}):
        failures.append("RESIZE-INFO: a plate BS row must return its ('plate', params)")
    if shim.beam_splitter_resize_info(1) != ("cube", {"side_mm": 25.0}):
        failures.append("RESIZE-INFO: a cube BS row must return its ('cube', params)")
    for idx, label in ((2, "non-BS promoted"), (3, "plain"), (9, "out-of-range")):
        if shim.beam_splitter_resize_info(idx) is not None:
            failures.append(f"RESIZE-INFO: a {label} row must return None")
    # the stored param shapes must be what the factory expects
    from KrakenOS.UI.services.beam_splitter_factory import _normalize_cube_params, _normalize_plate_params
    _normalize_cube_params(25.0)
    _normalize_plate_params(50.0, 50.0, 2.0, 45.0)
    if not [f for f in failures if f.startswith("RESIZE-INFO")]:
        notes.append("resize-info = BS rows return (kind, params); others None; params fit the factory")


def _check_resize_wiring(failures, notes):
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    src = inspect.getsource(ScenePlacementMixin.resize_beam_splitter)
    need = {
        "regenerate": "generate_beam_splitter(kind, **params)",
        "replace in place": "replace_promoted_optical_solid_step(",
        "re-mark the BS": 'promo["beam_splitter"] = True',
    }
    missing = [label for label, token in need.items() if token not in src]
    if missing:
        failures.append("RESIZE-WIRING: resize_beam_splitter is missing " + ", ".join(missing))
    else:
        notes.append("resize-wiring = regenerate + replace-in-place + re-mark the beam splitter")


def _check_menu(failures, notes):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    src = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    if 'label="Resize Beam Splitter..."' not in src:
        failures.append('MENU: the element menu must offer "Resize Beam Splitter..."')
    if "beam_splitter_resize_info(row_index)" not in src:
        failures.append("MENU: the resize item must be gated on beam_splitter_resize_info (parametric BS only)")
    if "open_resize_beam_splitter_dialog(idx)" not in src:
        failures.append("MENU: the resize item must open the numerical resize dialog")
    if not [f for f in failures if f.startswith("MENU")]:
        notes.append('menu = "Resize Beam Splitter..." gated on a parametric BS, opens the numerical dialog')


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_persist, _check_resize_info, _check_resize_wiring, _check_menu):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_bs_resize (bugs/0423) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll BS-resize checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
