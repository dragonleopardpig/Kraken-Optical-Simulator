#!/usr/bin/env python3
"""Instrument DetectorCoverageOverlayService.add_overlays against the REAL traced
scene bundle of the USER's topology and record every actor it creates (no rendering),
to find why the object plane is missing after the BS cube is promoted.

User's scene (flag_20260622_071429_544): MV 150mm 1X with a 50mm beam-splitter cube
BEFORE the single lens. The TRANSMIT arm goes through the 150 lens to the camera; the
REFLECT arm is BARE (no lens / no aperture) -> a single imaging arm. So this is NOT a
two-arm imaging fold (`_imaging_branch_leaves` needs >=2 arms each with an Aperture);
the detectors are ray-tree branch detectors with NO `two_arm_magnification` metadata,
so the object-FOV magnification must come from `_current_finite_paraxial_magnification()`
on the whole branched beam-splitter scene.

Run: .devenv/state/venv/bin/python bugs/diag_object_plane_overlays.py
"""
from __future__ import annotations

import contextlib
import io

import numpy as np

from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic paths", "reflectance": 0.5, "absorption": 0.0,
    "transmit_phase_deg": 0.0, "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3, "max_branch_depth": 8,
}


def _user_specs():
    """MV 150 1X + a 50mm beam-splitter cube before the single lens (reflect arm bare)."""
    s = [dict(x) for x in SURFACES]
    object_to_bs = 176.43
    s[0] = dict(s[0], thickness=object_to_bs)
    splitter = {
        "element": "Splitter", "surface": "Beam Splitter", "name": "50 mm cube splitter",
        "rc": 0.0, "k": 0.0, "thickness": 275.0 - object_to_bs, "diameter": 50.0,
        "tilt_x": 45.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0, "axis_move": 0.0, "glass": "AIR",
        "advanced": {"BeamSplitter": BEAM_SPLITTER_SETTINGS,
                     "Element": {"element_name": "50 mm cube splitter", "branch_selector": ""}},
    }
    return [s[0], splitter] + s[1:]


class _RecInspector:
    def __init__(self, editor):
        self.editor = editor
        self.mesh_actors = []
        self.view_props = []

    def _add_mesh_actor(self, mesh, **kw):
        try:
            bounds = tuple(round(float(b), 2) for b in mesh.bounds)
        except Exception:
            bounds = None
        self.mesh_actors.append({"bounds": bounds, **kw})
        return object()

    def _add_renderer_view_prop(self, actor):
        try:
            pos = tuple(round(float(v), 2) for v in actor.GetPosition())
            text = actor.GetInput()
        except Exception:
            pos, text = None, None
        self.view_props.append({"pos": pos, "text": text})
        return object()


def main() -> int:
    rows = [KrakenLayoutEditor._row_from_layout_item(dict(s)) for s in _user_specs()]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"

    settings = dict(SETTINGS)
    settings["trace_mode"] = "Non-Sequential Preview"

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        editor = _snapshot_editor(rows, settings)
        editor.branch_detector_camera_assignments = {}
        editor.show_detector_overlays_var = type(editor.object_mode_var)("1")
        leaves = editor._imaging_branch_leaves()
        sys_mag = editor._current_finite_paraxial_magnification()
        system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)

        from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService
        import pyvista as pv
        insp = _RecInspector(editor)
        svc = DetectorCoverageOverlayService(insp, pv_module=pv)
        n = svc.add_overlays(system, bundle)

    print(f"imaging leaves (need >=2 for two-arm fold) = {sorted(leaves)} (n={len(leaves)})")
    print(f"_current_finite_paraxial_magnification() = {sys_mag!r}")
    dets = [t for t in (getattr(bundle, "targets", []) or []) if getattr(t, "is_detector", False)]
    print(f"detectors in bundle: {len(dets)}")
    for t in dets:
        c = np.asarray(getattr(t, "center_world"), float).reshape(3)
        meta = getattr(t, "metadata", None) or {}
        print(f"  {getattr(t,'name','?'):>26} center={tuple(round(float(v),1) for v in c)}  "
              f"two_arm_mag={meta.get('two_arm_magnification')!r}")
    print(f"\nadd_overlays created {n} actors  ({len(insp.mesh_actors)} mesh, {len(insp.view_props)} labels)")
    obj_actors = [a for a in insp.mesh_actors if a.get("bounds") and abs(a["bounds"][4]) < 5 and abs(a["bounds"][5]) < 5]
    print(f"actors at the OBJECT PLANE (z~0): {len(obj_actors)}")
    for a in insp.mesh_actors:
        b = a.get("bounds")
        tag = "  <-- OBJECT PLANE" if (b and abs(b[4]) < 5 and abs(b[5]) < 5) else ""
        print(f"  color={a.get('color')} opacity={a.get('opacity')} bounds={b}{tag}")
    print("\nlabels:")
    for p in insp.view_props:
        print(f"  {p['pos']}  {p['text']!r}")
    print()
    if not obj_actors:
        print("BUG REPRODUCED: no object-plane actor drawn (object FOV suppressed, mag is None).")
    else:
        print("Object plane IS drawn here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
