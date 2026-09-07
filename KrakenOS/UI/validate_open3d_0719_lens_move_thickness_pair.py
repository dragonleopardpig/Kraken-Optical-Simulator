"""Guard for bugs/0719 -- flag_20260905_194708 on om05a_folded_80mm: the normal FOV
solve REFUSED a lens move that had room (171.97 mm needed vs 180.47 mm station gap),
and the Force FOV bypass drew a ~150-172 mm "tube" under the Filter.

Root causes (measured, bugs/0719_lens_move_thickness_pair.md):
  * the tube = the Filter row's core Side3D drum: the 0717 force wrote a desp CANCEL on
    the glass Filter row; the core bakes a row's own decentre into its own ring only
    (AxisMove=0), so Side3D(13, 14) spanned the whole cancelled amount;
  * the refusal = slide_lens_block_along_its_leg returned None SILENTLY on a root-axis
    lens block, so the object delta fell to the Object row (5.35 mm) + a VENDOR spill row.

The fix is ONE lens-move primitive, ``translate_lens_block_along_leg(d, force=False)``:
on a live follower-walk scene the move is the THICKNESS PAIR ``rows[front-1] += d``,
``rows[rear] -= d`` (stations front..rear shift, everything else byte-identical, no
desp write on any row); a 0433-frozen desp-leg scene still delegates to the tested
slide. The gate is the PHYSICAL along-leg AABB clearance to the fold mirror's body
(the station gap only as the hard cap); force applies the same pair, capped at the leg
gap so no thickness ever goes negative (bugs/0564 would raid the vendor prism gaps).
The image side after a root-axis lens move never moves vendor hardware (camera/sensor)
-- the focus residual is reported (status + HUD, a NON-banner stash) with ok=True.

Checks (all display-free; pure-function tests on the primitive with a stub editor):
  A  the pair: only rows[front-1]/rows[rear] change, stations front..rear shift by d,
     every other station invariant, no desp on any row, no vendor row's pose touched.
  B  the gate: |d| <= room_phys -> dict (room/clearance/obstacle); |d| > room_phys ->
     None with _lens_move_refusal naming the obstacle + _lens_move_room_mm (physical),
     NOTHING written.
  C  force: the pair regardless of room (penetration_mm negative), capped at the leg
     gap (rows[front-1].thickness >= 0 always, capped flag + capped_mm), no desp.
  D  dispatch: a folded desp-leg plan routes to slide_lens_block_along_its_leg.
  E  source pins: the mover delegates (no desp writes); _apply_conjugate_pair moves the
     object side through the primitive, stashes the refusal with the physical room,
     and after a pair move reports the focus residual (never the ':1668' refusal);
     fov_solve clears the residual stash and gates the field-fill refinement.
  F  the image-side vendor lock: camera STEP / downstream vendor row -> locked; clean -> ''.
  G  formatters: forced capped line; focus-residual HUD lines; the banner formatter does
     not read the residual stash.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0719_lens_move_thickness_pair
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _om05a_like_rows():
    """The om05a row skeleton (thickness / desp / vendor flags as loaded, bugs/0719 tables)."""
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def row(name, thickness, *, vendor=False, glass="AIR", desp=(0.0, 0.0, 0.0), tilt=(0.0, 0.0, 0.0),
            diameter=25.0, surface="Standard"):
        r = SurfaceRow(name=name, thickness=float(thickness), glass=glass, diameter=diameter, surface=surface)
        r.desp_x, r.desp_y, r.desp_z = (float(v) for v in desp)
        r.tilt_x, r.tilt_y, r.tilt_z = (float(v) for v in tilt)
        if vendor:
            r.advanced = {"Solid_3d_stl": "/nonexistent/vendor.stl",
                          "StepOverlayPromotion": {"center_world": [0.0, 0.0, 0.0]}}
        return r

    return [
        row("Object", 5.35, surface="Object"),
        row("First RA mirror A", 10.5, vendor=True, desp=(0.0, 0.42, 9.0), tilt=(0.0, 90.0, 0.0)),
        row("to BS", 20.0),
        row("BS cube A", 12.0, vendor=True, desp=(0.0, 20.0, -5.0)),
        row("to centre", 15.0),
        row("Centre RA mirror A", 11.0, vendor=True, desp=(0.0, 30.0, -10.0)),
        row("to mirror 1", 21.08),
        row("RA mirror 1 (50 mm)", 180.47, vendor=True, desp=(0.0, 52.8, -119.93), tilt=(0.0, 90.0, 0.0),
            diameter=77.0),
        row("Front Optical Vertex Datum", 11.861, desp=(-6.08, 0.0, -0.3885)),
        row("Blackbox Group 1", 9.734),
        row("Aperture Stop", 9.734, surface="Aperture"),
        row("Blackbox Group 2", 11.861),
        row("Rear Optical Vertex Datum", 17.93),
        row("Filter 48-926", 1.0, glass="N-BK7", diameter=50.8),
        row("to camera (unfolded RA mirror 2)", 31.11),
        row("RA mirror 2 (40 mm)", 45.13, vendor=True, desp=(272.6827, 52.75, -395.3344)),
        row("First RA mirror B", 10.0, vendor=True, desp=(300.0, 0.4, -400.0)),
        row("BS cube B", 12.0, vendor=True, desp=(300.0, 20.0, -410.0)),
        row("Centre RA mirror B", 11.0, vendor=True, desp=(300.0, 30.0, -420.0)),
        row("BS cube A (far half)", 12.0, vendor=True, desp=(0.0, 20.0, -5.0)),
        row("BS cube B (far half)", 12.0, vendor=True, desp=(300.0, 20.0, -410.0)),
        row("LED panel A", 10.0, vendor=True, desp=(0.0, 60.0, 0.0)),
        row("LED panel B", 19.6, vendor=True, desp=(300.0, 60.0, -400.0)),
        row("Image", 0.0, surface="Image"),
    ]


def _snapshot(rows):
    return [
        (float(r.thickness), float(r.desp_x), float(r.desp_y), float(r.desp_z),
         float(r.tilt_x), float(r.tilt_y), float(r.tilt_z))
        for r in rows
    ]


def _stations(rows):
    out, z = [0.0], 0.0
    for r in rows[:-1]:
        z += float(r.thickness)
        out.append(z)
    return out


def _make_stub(rows, *, folded=False, plan_direction=(0.0, 0.0, 1.0),
               lens_bounds=(0.0, 47.35, 0.0, 46.04, 185.656, 233.008),
               obstacle_bounds=(-25.0, 25.0, 27.8, 77.964, -25.0, 25.0),
               downstream_bounds=(-20.0, 20.0, 32.586, 72.75, 252.117, 293.085),
               obstacle_bounds_by_row=None, camera_step=None):
    """A stub editor built on the REAL mixins (the primitive's own arithmetic runs); only the
    scene-derived inputs are pinned: a root-axis (or folded) slide plan, no fold transform
    (leg unit = +Z), the lens STEP AABB and the obstacle AABB laid out along Z so the room
    matches the om05a numbers: lens body low edge 185.656, mirror body high edge 25.0 ->
    physical room 158.656 mm; station gap 180.47 mm. Downstream vendor rows get RA mirror 2's
    measured box (low edge 252.117) so a positive move measures against it."""
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    class _Stub(ScenePlacementMixin, LayoutTableWorkbenchMixin):
        def __init__(self):
            self.rows = rows
            self.headless = True
            self.debug: list[str] = []
            self.slide_calls: list[tuple] = []
            self.imported_camera_step_path = camera_step

        def _row_z_positions(self):
            return _stations(self.rows)

        def _lens_leg_slide_plan(self):
            front, rear = self._imaging_lens_block_indices()
            return (list(range(int(front), int(rear) + 1)), np.asarray(plan_direction, dtype=float), bool(folded))

        def _optical_axis_fold_world_transform_for_row(self, row_index):
            return None

        def _transformed_imported_step_mesh_for_label(self, label):
            if str(label) == "lens" and lens_bounds is not None:
                return SimpleNamespace(bounds=tuple(lens_bounds))
            return None

        def _solid_row_world_aabb(self, index):
            adv = self.rows[int(index)].advanced if isinstance(self.rows[int(index)].advanced, dict) else {}
            if not adv.get("Solid_3d_stl"):
                return None
            if obstacle_bounds_by_row and int(index) in obstacle_bounds_by_row:
                return tuple(obstacle_bounds_by_row[int(index)])
            front, rear = self._imaging_lens_block_indices()
            if int(index) < int(front):
                return tuple(obstacle_bounds) if obstacle_bounds is not None else None
            return tuple(downstream_bounds) if downstream_bounds is not None else None

        def _invalidate_preview_scene_trace(self, reason=""):
            pass

        def append_debug(self, message):
            self.debug.append(str(message))

        def slide_lens_block_along_its_leg(self, slide, *, force=False):
            self.slide_calls.append((float(slide), bool(force)))
            self._lens_leg_slide_refusal = ""
            self._lens_leg_slide_shortfall = 0.0
            return {"slide": float(slide), "members": [8, 9, 10, 11, 12], "direction": (0.0, 0.0, 1.0),
                    "upstream_row": 7, "downstream_row": 12}

        def _step_path_for_label(self, label):
            return self.imported_camera_step_path if str(label) == "camera" else None

    return _Stub()


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    vendor_rows = [i for i, r in enumerate(_om05a_like_rows())
                   if isinstance(r.advanced, dict) and r.advanced.get("Solid_3d_stl")]

    # ------------------------------------------------------------------ A: the pair
    rows = _om05a_like_rows()
    stub = _make_stub(rows)
    front, rear = stub._imaging_lens_block_indices()
    ok(front == 8 and rear == 12, f"A0: the om05a-like block is rows 8..12 (got {front}, {rear})")
    before = _snapshot(rows)
    st_before = _stations(rows)
    d = -150.5
    result = stub.translate_lens_block_along_leg(d)
    after = _snapshot(rows)
    st_after = _stations(rows)
    ok(isinstance(result, dict) and result.get("mode") == "thickness_pair" and result.get("rows") == [7, 12],
       f"A1: a fitting move returns the pair dict on rows [7, 12] ({result and result.get('mode')})")
    ok(abs(float(rows[7].thickness) - (180.47 + d)) < 1e-9 and abs(float(rows[12].thickness) - (17.93 - d)) < 1e-9,
       f"A2: rows[7] 180.47 -> {float(rows[7].thickness):.4f}, rows[12] 17.93 -> {float(rows[12].thickness):.4f}")
    changed = [i for i, (b, a) in enumerate(zip(before, after)) if b != a]
    ok(changed == [7, 12], f"A3: only rows 7 and 12 changed (changed {changed})")
    desp_same = all(b[1:] == a[1:] for b, a in zip(before, after))
    ok(desp_same, "A4: no desp / tilt changed on ANY row (no cancel row, no decentre write)")
    shifted = [i for i in range(len(rows)) if abs((st_after[i] - st_before[i]) - d) < 1e-9]
    invariant = [i for i in range(len(rows)) if abs(st_after[i] - st_before[i]) < 1e-9]
    ok(shifted == [8, 9, 10, 11, 12] and invariant == [i for i in range(len(rows)) if i not in (8, 9, 10, 11, 12)],
       f"A5: stations 8..12 shift by d, every other station invariant (shifted {shifted})")
    ok(all(before[i][1:] == after[i][1:] for i in vendor_rows)
       and all(before[i][0] == after[i][0] for i in vendor_rows if i != 7),
       "A6: every vendor row's pose (desp/tilt) is byte-identical; only row 7's LEG gap changed")
    ok(abs((float(rows[7].thickness) + float(rows[12].thickness)) - (180.47 + 17.93)) < 1e-9,
       "A7: rows[7].thickness + rows[12].thickness is invariant (station 13 fixed -> no Filter drum)")
    ok(bool(getattr(stub, "_fold_carry_pending_rebuild", False)),
       "A8: the move arms the 2D-stale gate (_fold_carry_pending_rebuild)")
    ok(abs(float(result["room_mm"]) - 158.656) < 1e-6 and abs(float(result["clearance_mm"]) - (158.656 - 150.5)) < 1e-6
       and result["obstacle"] == "RA mirror 1 (50 mm)" and result["capped"] is False,
       f"A9: room is PHYSICAL 158.656 mm (lens body 185.656 - mirror body 25.0 - 2.0), clearance "
       f"{float(result['clearance_mm']):.3f}, obstacle {result['obstacle']}")

    # ------------------------------------------------------------------ B: the gate
    rows = _om05a_like_rows()
    stub = _make_stub(rows)
    before = _snapshot(rows)
    refused = stub.translate_lens_block_along_leg(-171.966)
    ok(refused is None and _snapshot(rows) == before,
       "B1: |d| 171.966 > room_phys 158.656 -> None and NOTHING written (the station gap 180.47 alone "
       "would have said 'fits' -- the body overlapped the mirror by 11.3 mm)")
    ok("RA mirror 1 (50 mm)" in str(stub._lens_move_refusal) and abs(float(stub._lens_move_room_mm) - 158.656) < 1e-6,
       f"B2: the refusal names the obstacle and stashes the physical room ({stub._lens_move_room_mm})")
    fits = stub.translate_lens_block_along_leg(-158.0)
    ok(isinstance(fits, dict) and stub._lens_move_refusal == "" and abs(float(fits["clearance_mm"]) - 0.656) < 1e-6,
       "B3: a move inside the physical room applies and clears the refusal channel")
    # no obstacle upstream -> only the gap cap constrains (room_phys None)
    rows = _om05a_like_rows()
    for i in (1, 3, 5, 7):
        rows[i].advanced = {}
    stub = _make_stub(rows)
    free = stub.translate_lens_block_along_leg(-100.0)
    ok(isinstance(free, dict) and free.get("room_mm") is None and abs(float(rows[7].thickness) - 80.47) < 1e-9,
       "B4: with no vendor solid upstream the gap cap alone applies (room_mm None)")
    over = stub.translate_lens_block_along_leg(-100.0)
    ok(over is None and "negative" in str(stub._lens_move_refusal),
       "B5: a move past the leg gap is refused (the gap would go negative), nothing written")

    # ------------------------------------------------------------------ C: force
    rows = _om05a_like_rows()
    stub = _make_stub(rows)
    forced = stub.translate_lens_block_along_leg(-171.966, force=True)
    ok(isinstance(forced, dict) and abs(float(rows[7].thickness) - (180.47 - 171.966)) < 1e-9
       and forced["capped"] is False and float(forced["penetration_mm"]) < 0.0
       and abs(float(forced["penetration_mm"]) - (158.656 - 171.966)) < 1e-6,
       f"C1: force applies the pair past the physical room; penetration {float(forced['penetration_mm']):.3f} mm "
       f"(negative = the barrel is inside the mirror body), rows[7] -> {float(rows[7].thickness):.4f}")
    ok(all(b[1:] == a[1:] for b, a in zip(before, _snapshot(rows))), "C2: force writes no desp on any row")
    rows = _om05a_like_rows()
    stub = _make_stub(rows)
    capped = stub.translate_lens_block_along_leg(-250.0, force=True)
    ok(isinstance(capped, dict) and capped["capped"] is True
       and abs(float(capped["distance"]) - (180.47 - 1e-3)) < 1e-9
       and abs(float(capped["capped_mm"]) - (250.0 - (180.47 - 1e-3))) < 1e-9
       and float(rows[7].thickness) >= 0.0 and abs(float(rows[7].thickness) - 1e-3) < 1e-9,
       f"C3: a request beyond the leg gap is CAPPED at the station (drawn {float(capped['distance']):.4f} of "
       f"250, rows[7] -> {float(rows[7].thickness):.4g} >= 0)")
    ok(min(float(r.thickness) for r in rows[1:-1]) >= 0.0,
       "C4: every gap stays >= 0 -- the bugs/0564 normaliser has nothing to zero (no vendor-gap raid)")
    ok(abs(float(rows[7].thickness) + float(rows[12].thickness) - (180.47 + 17.93)) < 1e-9,
       "C5: the capped pair still keeps station 13 invariant")
    rows = _om05a_like_rows()
    stub = _make_stub(rows)
    forward = stub.translate_lens_block_along_leg(+10.0)
    ok(isinstance(forward, dict) and abs(float(rows[12].thickness) - 7.93) < 1e-9
       and abs(float(rows[7].thickness) - 190.47) < 1e-9 and forward["obstacle"] == "RA mirror 2 (40 mm)",
       "C6: a positive d (away from the object) shrinks the REAR gap and measures the downstream solid")
    too_far = stub.translate_lens_block_along_leg(+10.0)
    ok(too_far is None and "negative" in str(stub._lens_move_refusal),
       "C7: ... and refuses when the rear gap would go negative")

    # ------------------------------------------------------------------ D: dispatch
    rows = _om05a_like_rows()
    stub = _make_stub(rows, folded=True)
    before = _snapshot(rows)
    slid = stub.translate_lens_block_along_leg(-30.0, force=True)
    ok(isinstance(slid, dict) and slid.get("mode") == "slide" and stub.slide_calls == [(-30.0, True)]
       and _snapshot(rows) == before,
       f"D1: a folded desp-leg plan delegates to slide_lens_block_along_its_leg (force threaded) "
       f"and the pair is NOT written (calls {stub.slide_calls})")

    # ------------------------------------------------------------------ E: source pins
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    desp_write = re.compile(r"\.desp_[xyz]\s*=")
    mover_src = inspect.getsource(ScenePlacementMixin.force_translate_lens_toward_object)
    primitive_src = inspect.getsource(ScenePlacementMixin.translate_lens_block_along_leg)
    ok("translate_lens_block_along_leg(" in mover_src and "force=True" in mover_src
       and desp_write.search(mover_src) is None and desp_write.search(primitive_src) is None,
       "E1: force_translate_lens_toward_object delegates to the primitive; no desp writes remain anywhere "
       "in the lens-move path (the desp cancel on the glass Filter row built the drum)")
    apply_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(apply_src.count("translate_lens_block_along_leg(") >= 2
       and "slide_lens_block_along_its_leg(" not in apply_src,
       "E2: _apply_conjugate_pair books the object side through the primitive (first try AND the "
       "post-recruitment retry), never the bare slide")
    ok("_lens_move_refusal" in apply_src and "_lens_move_room_mm" in apply_src
       and "leg_room_mm" in apply_src and "lens_block_present" in apply_src,
       "E3: the refusal stash reads the primitive's refusal + PHYSICAL room; with a lens block present the "
       "object delta is never booked into the object gap")
    residual_at = apply_src.find("_fov_solve_focus_residual_info = {")
    refusal_at = apply_src.find("the object or image leg would go negative")
    ok(0 < residual_at < refusal_at and "focus residual" in apply_src
       and "lens_moved_as_pair" in apply_src and "_image_write_locked_by_vendor_hardware(" in apply_src,
       "E4: after a pair move the image side reports the focus residual (ok=True) BEFORE the 'leg would go "
       "negative' refusal can fire -- a refusal never happens after the lens moved")
    ok("snap_detector_to_image_plane" not in apply_src and "_preview_trace_deferred_until_requested = True" in apply_src,
       "E5: the 0718 force short-circuit contract is intact (deferred trace, no best-focus snap)")
    solve_src = inspect.getsource(QuickEstimationService.fov_solve)
    ok("self.editor._fov_solve_focus_residual_info = None" in solve_src
       and "_refine_folded_field_fill" in solve_src
       and solve_src.find('_fov_solve_focus_residual_info")') < solve_src.find("msg += self._refine_folded_field_fill"),
       "E6: fov_solve clears the residual stash at entry and gates the real-ray field-fill refinement on it "
       "(a defocused sensor plane is not a ruler for the WD)")

    # ------------------------------------------------------------------ F: the vendor lock
    qe_rows = _om05a_like_rows()
    qe = QuickEstimationService(SimpleNamespace(editor=_make_stub(qe_rows, camera_step="/x/camera.step")))
    ok("camera" in qe._image_write_locked_by_vendor_hardware(qe_rows, 22),
       "F1: a glued camera STEP locks the image write (the sensor carries the vendor body)")
    qe = QuickEstimationService(SimpleNamespace(editor=_make_stub(qe_rows, camera_step=None)))
    ok("vendor hardware" in qe._image_write_locked_by_vendor_hardware(qe_rows, 12),
       "F2: a vendor solid downstream of the image gap row locks the write")
    ok(qe._image_write_locked_by_vendor_hardware(qe_rows, 22) == "",
       "F3: no camera STEP and no vendor row past the gap -> the write is free (classic refocus)")

    # ------------------------------------------------------------------ G: formatters
    from KrakenOS.UI.services import system_info_hud as hud

    capped_text = "\n".join(hud.format_solve_refusal_lines(
        {"forced_penetration_mm": -13.3, "forced_obstacle": "RA mirror 1 (50 mm)",
         "forced_capped_mm": 250.0, "forced_drawn_mm": 180.469}))
    ok("PENETRATES RA mirror 1 (50 mm) by 13.3 mm" in capped_text and "capped at the fold mirror station" in capped_text
       and "250" in capped_text and "180.5" in capped_text,
       "G1: the banner renders the penetration AND the capped line with both numbers")
    clear_text = "\n".join(hud.format_solve_refusal_lines(
        {"forced_penetration_mm": 8.16, "forced_obstacle": "RA mirror 1 (50 mm)"}))
    ok("clearance to RA mirror 1 (50 mm) body" in clear_text, "G2: the clearance line names the obstacle BODY")
    residual_lines = hud.format_focus_residual_lines({"image_delta_mm": -98.6, "lens_move_mm": -150.5})
    residual_text = "\n".join(residual_lines)
    ok("shortened by 98.6 mm" in residual_text and "-150.5" in residual_text and "Trace Now" in residual_text
       and "SOLVE REFUSED" not in residual_text and hud.format_focus_residual_lines(None) == [],
       "G3: the HUD residual lines carry the track mismatch + the lens move, and are not a refusal")
    hud_src = inspect.getsource(hud.system_info_hud_text)
    banner_src = inspect.getsource(hud.format_solve_refusal_lines)
    ok("_fov_solve_focus_residual_info" in hud_src and "_fov_solve_focus_residual_info" not in banner_src,
       "G4: the HUD reads the residual stash; the SOLVE-REFUSED banner formatter never does")
    penta = Path(__file__).with_name("validate_open3d_penta_telescope_comprehensive.py")
    try:
        penta_src = penta.read_text(encoding="utf-8")
    except Exception:
        penta_src = ""
    ok("phase_518_lens_move_thickness_pair" in penta_src
       and penta_src.count("phase_518_lens_move_thickness_pair") >= 2,
       "G5: registered as penta phase 518 (definition + phases list)")

    # ------------------------------------------------------------------ H: the Phase-2 judge's must-fixes
    # The adversarial review refused to ship 0719 until these five were fixed; each is pinned.
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService as _QES
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin as _SPM

    short_text = "\n".join(hud.format_solve_refusal_lines(
        {"lens_move_needed_mm": -171.966, "leg_room_mm": 158.16}))
    ok("short by 13.8" in short_text and "short by -" not in short_text,
       "H1: the refusal shortfall is |need| - room (the signed form printed 'short by -333.5')")

    apply_h = inspect.getsource(_QES._apply_conjugate_pair)
    force_block = apply_h.split("if force:", 1)[-1][:4000]
    ok("Force FOV refused:" in apply_h and "_lens_move_refusal" in force_block
       and "_lens_move_room_mm" in force_block,
       "H2: a refused FORCE stashes the primitive's reason + physical room for the banner "
       "(no fixed 'no imaging-lens block' text with no numbers)")

    stub_f = _make_stub(_om05a_like_rows(), folded=True)
    slid_h = stub_f.translate_lens_block_along_leg(-30.0, force=True)
    slid_ok = isinstance(slid_h, dict)
    ok(slid_ok and slid_h.get("mode") == "slide" and slid_h.get("room_mm") is not None
       and abs(float(slid_h["room_mm"]) - 158.656) < 1e-6
       and slid_h.get("obstacle") == "RA mirror 1 (50 mm)"
       and abs(float(slid_h["penetration_mm"]) - (158.656 - 30.0)) < 1e-6,
       "H3: the frozen-leg (slide) branch reports the physical room + obstacle for a TOWARD-object "
       f"move too (room {slid_h.get('room_mm') if slid_ok else slid_h}, "
       f"obstacle {slid_h.get('obstacle') if slid_ok else None})")

    aabb_src = inspect.getsource(_SPM._solid_row_world_aabb)
    i_stl = aabb_src.find("_solid_row_stl_local_bounds(")
    i_meta = aabb_src.find("_promoted_solid_world_bounds(")
    ok(0 <= i_stl < i_meta,
       "H4: _solid_row_world_aabb poses the STL corners FIRST; promotion-metadata bounds are the fallback")

    rows_p = _om05a_like_rows()
    rows_p[10].advanced = {"Solid_3d_stl": "/nonexistent/parked.stl",
                           "StepOverlayPromotion": {"center_world": [0.0, 0.0, 0.0]}}
    stub_p = _make_stub(rows_p)
    before_p = _snapshot(rows_p)
    parked = stub_p.translate_lens_block_along_leg(-30.0)
    parked_force = stub_p.translate_lens_block_along_leg(-30.0, force=True)
    ok(parked is None and parked_force is None
       and "inside the lens block" in str(stub_p._lens_move_refusal)
       and _snapshot(rows_p) == before_p,
       "H5: a CAD solid parked inside the block refuses the pair (force too) and writes nothing "
       f"({str(stub_p._lens_move_refusal)[:72]})")

    room_text_h = "\n".join(hud.format_solve_refusal_lines(
        {"forced_penetration_mm": -13.8, "forced_obstacle": "RA mirror 1 (50 mm)", "forced_room_mm": 158.16}))
    ok("158.2 mm of physical room" in room_text_h and "PENETRATES RA mirror 1 (50 mm) by 13.8 mm" in room_text_h,
       "H6: the FORCED line renders the stashed physical room next to the penetration")

    # H7 (must-fix 3a): a frozen leg that is NOT +Z. Boxes laid out along X with the plan
    # direction +X and NO fold transform (the 0433-frozen shape): the room must come out along
    # the plan direction (185.656 - 25 - 2 = 158.656); the +Z fallback would give 0 - 25 - 2 = -27.
    stub_x = _make_stub(_om05a_like_rows(), folded=True, plan_direction=(1.0, 0.0, 0.0),
                        lens_bounds=(185.656, 233.008, 0.0, 46.04, 0.0, 47.35),
                        obstacle_bounds=(-25.0, 25.0, 27.8, 77.964, -25.0, 25.0))
    slid_x = stub_x.translate_lens_block_along_leg(-30.0, force=True)
    x_ok = isinstance(slid_x, dict) and slid_x.get("room_mm") is not None
    ok(x_ok and abs(float(slid_x["room_mm"]) - 158.656) < 1e-6
       and abs(float(slid_x["penetration_mm"]) - 128.656) < 1e-6
       and slid_x.get("obstacle") == "RA mirror 1 (50 mm)",
       "H7: on a +X frozen leg the room is measured along the PLAN direction, not the +Z fallback "
       f"(room {slid_x.get('room_mm') if isinstance(slid_x, dict) else slid_x}; +Z would give -27)")
    # H8 (must-fix 3c): the slide branch measures the room BEFORE the composite moves the rows.
    prim_body = inspect.getsource(_SPM.translate_lens_block_along_leg).split('"""', 2)[-1]
    i_room = prim_body.find("_lens_block_physical_room_mm(")
    i_slide = prim_body.find("self.slide_lens_block_along_its_leg(")
    ok(0 <= i_room < i_slide,
       "H8: the room is measured BEFORE slide_lens_block_along_its_leg moves the rows (no double charge)")
    # H9 (must-fix 3d): a forced move with NO obstacle body still renders a FORCED line.
    none_text = "\n".join(hud.format_solve_refusal_lines(
        {"forced_moved_mm": 5.0, "forced_station_room_mm": 265.668,
         "reason": "FORCED solve applied -- inspect the 3D overlap"}))
    ok("FORCED: applied; moved 5 mm" in none_text and "no obstacle body" in none_text
       and "265.7" in none_text and "right-click" not in none_text,
       "H9: a forced move that finds no obstacle body reports the move + leg gap, never the Force hint")

    # H10/H11 (judge pin gap): the TRANSVERSE filter itself, not a tie-break. A bar whose box
    # projects CLOSER along the leg (z-hi 40 > the mirror's 25) but is transversely disjoint
    # from the lens (y 60..80 vs lens y 0..46) must be rejected so RA mirror 1 wins; the same
    # bar overlapping the lens transversely (y 10..20) must become the obstacle.
    bar_far = (-30.0, 30.0, 60.0, 80.0, -25.0, 40.0)
    stub_t = _make_stub(_om05a_like_rows(), obstacle_bounds_by_row={5: bar_far})
    info_t = stub_t._lens_block_physical_room_mm(8, 12, -1.0)
    ok(info_t.get("obstacle") == "RA mirror 1 (50 mm)" and info_t.get("room_phys") is not None
       and abs(float(info_t["room_phys"]) - 158.656) < 1e-6,
       "H10: a closer-projecting but transversely DISJOINT bar is rejected; RA mirror 1 wins "
       f"(obstacle {info_t.get('obstacle')}, room {info_t.get('room_phys')})")
    bar_near = (-30.0, 30.0, 10.0, 20.0, -25.0, 40.0)
    stub_u = _make_stub(_om05a_like_rows(), obstacle_bounds_by_row={5: bar_near})
    info_u = stub_u._lens_block_physical_room_mm(8, 12, -1.0)
    ok(info_u.get("obstacle") == "Centre RA mirror A" and info_u.get("room_phys") is not None
       and abs(float(info_u["room_phys"]) - 143.656) < 1e-6,
       "H11: the same bar overlapping the lens transversely IS the obstacle "
       f"(obstacle {info_u.get('obstacle')}, room {info_u.get('room_phys')})")
    # H12: a frozen-leg caller with NO lens mesh names the solid and reports 'unmeasured',
    # and the banner says so instead of "no obstacle body found".
    stub_nm = _make_stub(_om05a_like_rows(), folded=True, lens_bounds=None)
    info_nm = stub_nm._lens_block_physical_room_mm(8, 12, -1.0, leg_unit=(0.0, 0.0, 1.0))
    nm_text = "\n".join(hud.format_solve_refusal_lines(
        {"forced_moved_mm": 5.0, "forced_room_method": "unmeasured",
         "forced_obstacle": "RA mirror 1 (50 mm)", "forced_station_room_mm": 180.47}))
    ok(info_nm.get("method") == "unmeasured" and info_nm.get("obstacle") == "RA mirror 1 (50 mm)"
       and info_nm.get("room_phys") is None and "NOT measurable" in nm_text
       and "no obstacle body" not in nm_text,
       f"H12: no lens mesh on a frozen leg -> 'unmeasured' + the obstacle named; the banner says "
       f"NOT measurable, never 'no obstacle body found' (method {info_nm.get('method')})")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0719 lens-move thickness-pair validation PASSED")
        return 0
    print("0719 lens-move thickness-pair validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
