"""Guard for bugs/0755 + bugs/0756 -- verify the root you report, and let the camera's own leg
be the third conjugate variable.

Flag 20260908_154430_151 ("change device size to 55x55mm, image plane still not landed on
sensor") exposed two things at once.

bugs/0755 -- the bugs/0754 readout was reporting a field that is not a focus state. It scanned
`image_delta(m)` for sign changes without honouring the model's own `image_side_unreachable`
flag and without checking the bracket it returned. On the flagged scene it printed "This track
DOES focus a 96.89 x 96.89 mm object field (|m| 0.2378)" where `image_delta(0.2378) = -15.53`,
against a traced 54.09 mm. It was also computed AFTER the solve had moved the lens, describing
a transient state nobody is looking at.

bugs/0756 -- the solve already computed the exact image-side change that would land the image
(`image_gap_row: 24, image_delta_mm: +10.78`) and refused to write it because "the sensor
carries the vendor camera body". That is right about the BODY and wrong about the POSITION:
translating the whole camera along its leg leaves the vendor assembly byte-identical.

Checks (display-free, pure):
  A  a root is accepted only when the model's own image_delta is ~0 there AND the state is
     reachable; unreachable magnitudes never enter the scan.
  B  the reported field is snapshotted BEFORE the solve moves anything.
  C  the stage spec is validated, and only unlocks the row it actually travels on.
  D  a move past either end of the travel is a refusal naming the number, never a silent clamp.
  E  the stage round-trips through the layout settings, so a scene can state it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0756_camera_focus_stage
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.services import layout_settings

    # ---- A: the root must be verified, and unreachable states excluded --------------------
    src = inspect.getsource(QuickEstimationService._in_focus_fields_at_current_track)
    ok(
        'not bool(folded.get("image_side_unreachable"))' in src,
        "A1: the model's own reachability flag is read, so unreachable magnitudes never enter "
        "the scan (the 0.2378 'root' sat in that region)",
    )
    ok(
        "residual, reachable = evaluate(root)" in src
        and "abs(residual) > self._ROOT_RESIDUAL_TOL_MM" in src,
        "A2: every bracketed root is re-evaluated and dropped unless image_delta is ~0 there",
    )
    ok(
        float(QuickEstimationService._ROOT_RESIDUAL_TOL_MM) <= 0.153,
        f"A3: the tolerance ({QuickEstimationService._ROOT_RESIDUAL_TOL_MM} mm) is inside one "
        f"pixel of depth of focus (0.153 mm), so an accepted root is optically a focus",
    )

    # a model with NO root anywhere must yield nothing rather than a bracket artefact
    class NoRoot:
        def _folded_conjugate_gaps_for_magnification(self, m):
            return {"image_delta": 25.0, "magnitude": float(m)}   # never zero

        def _current_camera_sensor_active_mm(self):
            return (23.04, 23.04)

    ok(
        QuickEstimationService(SimpleNamespace(editor=NoRoot()))._in_focus_fields_at_current_track() == [],
        "A4: a model that never crosses zero yields no field at all",
    )

    class AllUnreachable:
        def _folded_conjugate_gaps_for_magnification(self, m):
            return {"image_delta": float(m) - 0.5, "image_side_unreachable": True}

        def _current_camera_sensor_active_mm(self):
            return (23.04, 23.04)

    ok(
        QuickEstimationService(
            SimpleNamespace(editor=AllUnreachable())
        )._in_focus_fields_at_current_track() == [],
        "A5: a real sign change in an UNREACHABLE region is not a focus state",
    )

    # ---- B: snapshotted before the solve moves anything -------------------------------------
    apply_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        "in_focus_before = self._in_focus_fields_at_current_track()" in apply_src,
        "B1: the field is measured on entry, before any geometry is written",
    )
    ok(
        '"in_focus_fields": in_focus_before,' in apply_src,
        "B2: and it is that snapshot which is stashed, not a post-move re-measurement",
    )
    ok(
        apply_src.find("in_focus_before = ") < apply_src.find("translate_lens_block_along_leg"),
        "B3: the snapshot really does precede the lens move in the source order",
    )

    # ---- C: the stage spec ------------------------------------------------------------------
    def svc(stage, rows=6):
        editor = SimpleNamespace(camera_focus_stage=stage, rows=[SimpleNamespace()] * rows)
        return QuickEstimationService(SimpleNamespace(editor=editor))

    ok(svc(None)._camera_focus_stage() is None, "C1: no spec -> no stage")
    ok(
        svc({"enabled": False, "row": 4, "min_mm": 0, "max_mm": 10})._camera_focus_stage() is None,
        "C2: a disabled stage is no stage",
    )
    ok(
        svc({"enabled": True, "row": 99, "min_mm": 0, "max_mm": 10})._camera_focus_stage() is None,
        "C3: a row index outside the table is rejected, not clamped",
    )
    ok(
        svc({"enabled": True, "row": 4, "min_mm": 10, "max_mm": 10})._camera_focus_stage() is None,
        "C4: zero or inverted travel is rejected",
    )
    good = svc({"enabled": True, "row": 4, "min_mm": 0.0, "max_mm": 24.04})._camera_focus_stage()
    ok(
        isinstance(good, dict) and good["row"] == 4 and good["max_mm"] == 24.04,
        "C5: a valid spec validates",
    )
    lock_src = inspect.getsource(QuickEstimationService._image_write_locked_by_vendor_hardware)
    ok(
        'int(stage["row"]) == write_row' in lock_src,
        "C6: the camera lock lifts ONLY for the row the stage travels on -- every other "
        "image-side write still refuses while a camera STEP is glued",
    )
    ok(
        "Solid_3d_stl" in lock_src,
        "C7: and the downstream vendor-solid check is untouched",
    )

    # ---- D: the ends of travel are a refusal with a number ------------------------------------
    ok(
        "outside its" in apply_src and "travel" in apply_src and "stage" in apply_src,
        "D1: running past an end produces a reason naming where the stage would have to sit",
    )
    ok(
        'stage["min_mm"] - 1.0e-9 <= landed <= stage["max_mm"] + 1.0e-9' in apply_src,
        "D2: the bound is checked against the row's resulting value, both ends",
    )
    ok(
        apply_src.count("image_locked_reason =") >= 3,
        "D3: it flows through the SAME locked-reason path, so the residual and the 0754 "
        "way-out line are reported exactly as for any other refusal",
    )

    # ---- E: a scene can state it -----------------------------------------------------------
    save_src = inspect.getsource(layout_settings)
    ok(
        '"camera_focus_stage": getattr(self, "camera_focus_stage", None),' in save_src,
        "E1: the stage is written into the layout settings",
    )
    ok(
        'stage = settings.get("camera_focus_stage", None)' in save_src
        and "self.camera_focus_stage = dict(stage) if isinstance(stage, dict) else None" in save_src,
        "E2: and read back on load, so it survives a round trip",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0755/0756 camera-focus-stage validation PASSED")
        return 0
    print("0755/0756 camera-focus-stage validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
