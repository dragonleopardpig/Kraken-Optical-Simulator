"""Guard for bugs/0781 -- one Solve FOV may not trace the same scene twice.

User: *"after clicking apply + solve FOV, it takes ages to trace."*

Profiled on attachment/om05a_folded_80mm.py (21x21x1 device, default FOV, the 3D window open):
Apply took 40.4 s (one display trace) and Solve FOV 237.8 s, of which 163.6 s went to four full
ray traces -- every one a focus measurement:

    #1  43.3 s  _finish_solve_on_traced_focus: the residual before the snap      (bugs/0490)
    #2  36.6 s  snap_detector_to_image_plane: the defocus before its write       (bugs/0764)
    #3  43.3 s  snap_detector_to_image_plane: the defocus after its write        (bugs/0764)
    #4  40.4 s  _finish_solve_on_traced_focus: the residual after the snap       (bugs/0490)

An independent read-only review (six agents, each lens re-checked by a second) found that #2
re-traces the scene #1 had just traced -- nothing the trace reads is written between them -- and
that on the path om05a took (the snap wrote, measured worse, and restored the snapshot) #4 traces
it a third time. #3 is the only measurement of the trial write and has to stay.

The fix hands a measured value forward only while a content fingerprint of the trace's inputs is
unchanged, and falls back to measuring whenever it is not. The fingerprint is over-inclusive on
purpose: an extra input can only cost a cache hit, never produce a stale reading.

Checks (display-free; the REAL QuickEstimationService._finish_solve_on_traced_focus and the REAL
ScenePlacementMixin.snap_detector_to_image_plane, on a stub host whose traced measure counts its
calls and writes the same focus stashes a real trace writes):
  A  the fingerprint: stable; changes with rows, STEP offsets, scene sources and learned fold
     state; blind to trace OUTPUTS (image strips, the focus readout); never mutates the live
     bands; None when a re-trace would not reproduce the value;
  B  revert path: 2 traces, not 4; the reported residual is #1's; after the revert the focus
     readout describes the restored scene, not the rejected trial write;
  C  kept path: 2 traces, not 4; the reported residual is #3's;
  D  any fingerprint change between the measurements falls back to measuring (4 traces);
  E  a stand-alone snap (right-click, lens swap) still measures before AND after, and no one-shot
     value outlives the finisher;
  F  the bugs/0764 guard still reverts a write that measured worse.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0781_solve_does_not_retrace_an_unchanged_scene
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np


class _Row:
    def __init__(self, surface: str, name: str, thickness: float):
        self.surface = surface
        self.name = name
        self.thickness = float(thickness)
        self.desp_x = 0.0
        self.desp_y = 0.0
        self.desp_z = 0.0
        self.glass = "AIR"


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _host_class():
    import KrakenOS.UI.services.paraxial_tools as pt
    import KrakenOS.UI.services.scene_placement_commands as spc

    pt.__dict__.setdefault("np", np)
    spc.__dict__.setdefault("np", np)

    class Host(spc.ScenePlacementMixin, pt.ParaxialToolsMixin):
        headless = True

        def __init__(self, *, focus_gap: float, paraxial_delta: float):
            self.rows = [
                _Row("Object", "Object", 10.0),
                _Row("Standard", "lens", 50.0),
                _Row("Standard", "image gap", 100.0),
                _Row("Image", "Image", 0.0),
            ]
            # the gap (rows[-2].thickness) at which the rays waist, and the paraxial guess's error
            self.focus_gap = float(focus_gap)
            self.paraxial_delta = float(paraxial_delta)
            self.status_var = _Var()
            self.layout_object_fov_bands = [{"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]}]
            self.layout_scene_source_specs = [{"source_x": 0.0}]
            self._folded_m_correction_state = None
            self._folded_field_center_state = None
            self.energy_probability = False
            self.traces = 0

        # the traced measure: counted, and writing what a real bundle build writes
        def _traced_bundle_best_focus_shift(self):
            self.traces += 1
            gap = float(self.rows[-2].thickness)
            self._focused_image_plane_info = {"offset_mm": self.focus_gap - gap, "traced_gap": gap}
            self._last_scene_bundle = ("bundle", gap)
            self.layout_object_fov_bands[0]["image_strip"] = {"traced_gap": gap}
            return float(self.focus_gap - gap)

        def _build_preview_system_rays_bundle(self, **_kwargs):
            raise AssertionError("the stub measures through _traced_bundle_best_focus_shift only")

        def _collect_layout_settings(self):
            return {
                "object_fov_bands": self.layout_object_fov_bands,
                "scene_sources": self.layout_scene_source_specs,
                "nonseq_energy_probability": bool(self.energy_probability),
            }

        def _folded_image_conjugate_split(self):
            return {}

        def _paraxial_image_plane_z(self):
            return sum(float(r.thickness) for r in self.rows[:-1]) + self.paraxial_delta

        def glued_illumination_unit_world_poses(self):
            return {}

        def restore_glued_illumination_unit_world_poses(self, _poses):
            return None

        def apply_image_distance_frozen_aware(self, target_gap):
            self.rows[-2].thickness = float(target_gap)
            return True

        def _invalidate_preview_scene_trace(self):
            return None

        def _set_step_placement_offset_xyz(self, label, value):
            setattr(self, f"{label}_step_placement_offset_xyz", value)

    return Host


def _finish(host):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    service = QuickEstimationService(SimpleNamespace(editor=host))
    service._axis_section_pins = lambda: {}
    return service._finish_solve_on_traced_focus()


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    Host = _host_class()
    # the snap's collision resolver reads camera geometry a stub has no business carrying
    original_resolver = QuickEstimationService._resolve_image_gap_collision
    QuickEstimationService._resolve_image_gap_collision = lambda self, image_distance: None
    try:
        # ---- A: the fingerprint ------------------------------------------------------------------
        host = Host(focus_gap=100.0945, paraxial_delta=5.88)
        if not hasattr(host, "_traced_focus_state_fingerprint"):
            ok(False, "A0: ParaxialToolsMixin._traced_focus_state_fingerprint exists")
        else:
            fp0 = host._traced_focus_state_fingerprint()
            ok(isinstance(fp0, str) and fp0 == host._traced_focus_state_fingerprint(),
               "A1: the fingerprint is a stable string on an unchanged scene")
            host.rows[-2].thickness += 1.0
            ok(host._traced_focus_state_fingerprint() != fp0, "A2: a row thickness changes it")
            host.rows[-2].thickness -= 1.0
            ok(host._traced_focus_state_fingerprint() == fp0, "A3: and restoring it restores the fingerprint")
            host.rows[1].desp_z = 0.5
            ok(host._traced_focus_state_fingerprint() != fp0, "A4: a row placement (desp) changes it")
            host.rows[1].desp_z = 0.0
            host.camera_step_placement_offset_xyz = (0.0, 1.0, 0.0)
            ok(host._traced_focus_state_fingerprint() != fp0, "A5: a STEP placement offset changes it")
            host.camera_step_placement_offset_xyz = None
            host.layout_scene_source_specs[0]["source_x"] = 1.0
            ok(host._traced_focus_state_fingerprint() != fp0, "A6: a scene source spec changes it")
            host.layout_scene_source_specs[0]["source_x"] = 0.0
            host._folded_m_correction_state = {"factor": 1.01}
            ok(host._traced_focus_state_fingerprint() != fp0, "A7: the learned fold correction changes it")
            host._folded_m_correction_state = None
            ok(host._traced_focus_state_fingerprint() == fp0, "A8: back to the starting scene, back to the starting fingerprint")
            host.layout_object_fov_bands[0]["image_strip"] = {"traced_gap": 123.0}
            host._focused_image_plane_info = {"offset_mm": 9.9}
            ok(host._traced_focus_state_fingerprint() == fp0,
               "A9: trace OUTPUTS (image strip, focus readout) do not change it -- the trace writes them")
            ok("image_strip" in host.layout_object_fov_bands[0],
               "A10: computing it never strips the live bands (it fingerprints a copy)")
            host.energy_probability = True
            ok(host._traced_focus_state_fingerprint() is None,
               "A11: with energy probability on the tracer draws unseeded random numbers -- no fingerprint, no reuse")
            host.energy_probability = False
            host._folded_m_relearn_pending = True
            ok(host._traced_focus_state_fingerprint() is None,
               "A12: a pending fold relearn can re-trace and rewrite the launch mid-build -- no reuse")
            host._folded_m_relearn_pending = False

        # ---- B: revert path ------------------------------------------------------------------------
        host = Host(focus_gap=100.0945, paraxial_delta=5.88)
        message = _finish(host)
        ok(host.traces == 2,
           f"B1: a snap that writes, measures worse and reverts costs 2 traces, not 4 (got {host.traces})")
        ok("already at the traced focus" in message and "+0.0945" in message,
           f"B2: and the solve reports the residual measured before the snap ({message.strip()!r})")
        ok(abs(host.rows[-2].thickness - 100.0) < 1e-12, "B3: the rejected write is reverted (bugs/0764 intact)")
        info = getattr(host, "_focused_image_plane_info", None) or {}
        strip = (host.layout_object_fov_bands[0].get("image_strip") or {})
        ok(info.get("traced_gap") == 100.0 and strip.get("traced_gap") == 100.0
           and getattr(host, "_last_scene_bundle", None) == ("bundle", 100.0),
           f"B4: the focus readout, image strip and last bundle describe the RESTORED scene, not the "
           f"rejected trial write (the next solve's 'already delivered' reads them) -- got {info}, {strip}")

        # ---- C: kept path -----------------------------------------------------------------------------
        host = Host(focus_gap=103.0, paraxial_delta=3.0)
        message = _finish(host)
        ok(host.traces == 2,
           f"C1: a snap that writes and keeps an improvement costs 2 traces, not 4 (got {host.traces})")
        ok(abs(host.rows[-2].thickness - 103.0) < 1e-9 and "+3 -> +0" in message.replace("+0.0", "+0"),
           f"C2: the write is kept and the reported residual is the one measured after it ({message.strip()!r})")

        # ---- D: a state change between measurements falls back ------------------------------------------
        class Drifting(Host):
            def glued_illumination_unit_world_poses(self):
                self.layout_scene_source_specs[0]["source_x"] += 1.0   # e.g. a face-bound source resync
                return {}

        host = Drifting(focus_gap=100.0945, paraxial_delta=5.88)
        message = _finish(host)
        ok(host.traces == 3,
           f"D1: when a trace input changes before the snap measures, the finisher's value is refused "
           f"and the snap measures for itself; the revert then reuses the SNAP's own measurement of "
           f"the restored scene -- 3 traces, never the stale 2 (got {host.traces})")
        ok("already at the traced focus" in message, "D2: and the outcome is the same as before the fix")

        # ---- E: stand-alone snap ----------------------------------------------------------------------------
        host = Host(focus_gap=100.0945, paraxial_delta=5.88)
        host.snap_detector_to_image_plane()
        ok(host.traces == 2,
           f"E1: a snap called on its own (right-click, lens swap) still measures before AND after (got {host.traces})")
        host = Host(focus_gap=100.0945, paraxial_delta=5.88)
        _finish(host)
        ok(getattr(host, "_snap_premeasured_focus", None) is None,
           "E2: the finisher's one-shot value does not outlive it -- a later stand-alone snap measures for itself")

        # ---- F: the 0764 guard still reverts -----------------------------------------------------------------
        host = Host(focus_gap=100.0945, paraxial_delta=5.88)
        _finish(host)
        ok(abs(host.rows[-2].thickness - 100.0) < 1e-12 and bool(getattr(host, "_snap_detector_refusal", "")),
           "F1: a worse write is still reverted and the refusal still reaches the caller")
    finally:
        QuickEstimationService._resolve_image_gap_collision = original_resolver

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0781 solve-does-not-retrace-an-unchanged-scene validation PASSED")
        return 0
    print("0781 solve-does-not-retrace-an-unchanged-scene validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
