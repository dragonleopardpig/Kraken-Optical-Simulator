"""bugs/0511 repro -- replay the recorded gestures headless and inspect both symptoms.

Session net gestures (recording_20260802_195054): LED station -36.9, RA mirror row -22.5,
then the lens: HEALTHY at +5 (center ~124.4) vs BROKEN at +24.2 (center ~143.6).
Per config: branch-detector entities (center + focus_source), the imaging leaf's
transverse RMS at the FIT focus vs at the reached IMAGE (the 0511 discriminator),
and the DetectorCoverageOverlayService actors (object-plane presence).

Run:
    timeout 900 xvfb-run -a .devenv/state/venv/bin/python -u bugs/probe_0511_lens_near_mirror.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services import branch_detectors as bd
from KrakenOS.UI.services import optical_axis_tree as tree_mod

CAPTURED: list[tuple] = []
_orig_derive = bd.derive_branch_detectors


def _spy(ray_paths, existing_targets=None, **kw):
    out = _orig_derive(ray_paths, existing_targets, **kw)
    CAPTURED.append((list(ray_paths or []), list(existing_targets or []), list(out)))
    return out


bd.derive_branch_detectors = _spy


def _path_reaches(p) -> bool:
    if bool(getattr(p, "reaches_image", False)):
        return True
    try:
        return bd.ray_path_terminal_status_from_events(p) == "hit_detector"
    except Exception:
        return False


def _rms_at_plane(origins, directions, point, normal) -> float:
    pts = []
    n = np.asarray(normal, float).reshape(3)
    P = np.asarray(point, float).reshape(3)
    for o, d in zip(origins, directions):
        denom = float(np.dot(d, n))
        if abs(denom) < 1e-9:
            continue
        t = float(np.dot(P - o, n) / denom)
        pts.append(o + d * t)
    if len(pts) < 2:
        return float("nan")
    pts = np.asarray(pts)
    c = pts.mean(axis=0)
    return float(np.sqrt(((pts - c) ** 2).sum(axis=1).mean()))


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
        return object()


def inspect(editor, label: str) -> None:
    CAPTURED.clear()
    system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    img8 = np.asarray(tree_mod.row_world_pose(editor.rows, 8), float).reshape(-1)[:3]
    print(f"== {label}: image row 8 world=({img8[0]:.2f},{img8[1]:.2f},{img8[2]:.2f})", flush=True)
    dets = [t for t in (getattr(bundle, "targets", []) or []) if getattr(t, "is_detector", False)]
    for t in dets:
        c = np.asarray(getattr(t, "center_world"), float).reshape(3)
        meta = getattr(t, "metadata", None) or {}
        print(
            f"   det {getattr(t, 'name', '?')!s:>26} center=({c[0]:7.2f},{c[1]:6.2f},{c[2]:7.2f}) "
            f"focus_source={meta.get('focus_source')!r} seating={meta.get('camera_seating_reason')!r}",
            flush=True,
        )
    if CAPTURED:
        ray_paths, targets, derived = CAPTURED[-1]
        reached = bd._reached_image_target(targets)
        groups: dict[str, list] = {}
        for p in ray_paths:
            groups.setdefault(str(getattr(p, "branch_path", "") or ""), []).append(p)
        for det in derived:
            group = groups.get(det.branch_path) or []
            survivors = [p for p in group if _path_reaches(p)]
            use = survivors if survivors else group
            o, d = bd._exit_rays_for_group(use)
            if o.shape[0] == 0:
                continue
            md = bd._unit(d.mean(axis=0))
            focus, converged = bd._closest_approach_point(o, d)
            rms_fit = _rms_at_plane(o, d, focus, md)
            line = (
                f"   leaf {det.branch_path[:36]!s:38} n={len(group)} reach={len(survivors)} "
                f"fit=({focus[0]:.1f},{focus[1]:.1f},{focus[2]:.1f}) conv={converged} rms_fit={rms_fit:.3f}"
            )
            if reached is not None:
                ri = np.asarray(getattr(reached, "center_world"), float).reshape(3)
                rms_img = _rms_at_plane(o, d, ri, md)
                line += f" rms_at_image={rms_img:.3f} (image=({ri[0]:.1f},{ri[1]:.1f},{ri[2]:.1f}))"
            print(line, flush=True)
    from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService
    import pyvista as pv

    insp = _RecInspector(editor)
    svc = DetectorCoverageOverlayService(insp, pv_module=pv)
    n = svc.add_overlays(system, bundle)
    obj_actors = [
        a for a in insp.mesh_actors
        if a.get("bounds") and abs(a["bounds"][4]) < 8.0 and abs(a["bounds"][5]) < 8.0
    ]
    print(f"   overlays: {n} actors, object-plane(z~0) actors={len(obj_actors)}", flush=True)
    for a in obj_actors:
        print(f"     obj actor bounds={a['bounds']} color={a.get('color')}", flush=True)
    print(f"   sys_mag={editor._current_finite_paraxial_magnification()!r}", flush=True)


def main() -> None:
    editor = KrakenLayoutEditor()
    editor.layout_files["probe"] = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
    editor.load_layout_by_name("probe")
    editor.translate_step_overlay("led", (-36.9, 0.0, 0.0))
    editor.translate_scene_row_pose_vector(7, (-22.5, 0.0, 0.0))
    editor.translate_step_overlay("lens", (5.0, 0.0, 0.0))
    inspect(editor, "HEALTHY lens ~124.4")
    editor.translate_step_overlay("lens", (19.2, 0.0, 0.0))
    inspect(editor, "BROKEN lens ~143.6")


if __name__ == "__main__":
    main()
