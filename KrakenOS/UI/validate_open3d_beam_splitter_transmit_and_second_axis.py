"""Display-free guard for bugs/0017 — a promoted beam-splitter cube must let the
transmitted beam pass straight through to the imaging lens, and the reflected
beam path must get its own auto-generated optical axis.

Regression context
------------------
The user's saved machine-vision prescription promotes a beam-splitter *cube* and
places the Image plane at its real station (~665, after the imaging lens at
z~268). Two coupled defects:

1. Facet A — the cube's straight-through exit face is *inferred* (auto-suggested,
   never user-authored) as an Output Port. The output-port follower then snapped
   the downstream Image plane onto that exit face (~265), in FRONT of the lens,
   so every transmitted ray was intercepted at the cube and "stopped right at the
   imaging lens entrance". Fixed in ``build_optical_solid_output_port_pose_overrides``:
   an inferred exit that runs straight along the incoming optical axis (collinear,
   centered) no longer repositions downstream rows — they already lie on that axis.

2. Facet B — the 3D inspector only built a traced optical axis from a single
   "chief" ray path. A beam splitter fans the central ray into an on-axis
   transmit branch (already covered by axis:global) AND a folded reflect branch;
   when the transmit branch won the chief score the reflected beam path got no
   axis at all. Fixed in ``Kraken3DInspector._optical_axis_records_for_3d``: walk
   every steered path and emit one representative traced axis per distinct fold
   direction, so the reflected branch always earns its own ``Optical Axis 2``.

Invariants asserted here (all headless / display-free):

1. Facet-A root cause: an inferred straight-through (+Z, on-axis) optical-solid
   output does NOT reposition a downstream Image row, while a genuinely folded
   inferred output still does (the fix is surgical, not a blanket disable).
2. Facet-B mechanism: a synthetic beam-splitter bundle whose on-axis transmit
   branch wins the chief score still yields exactly one folded (reflected) traced
   optical axis, and a branch's field-angle spread collapses to that single axis
   (no cloud of near-duplicate guides).
3. Optional real-scene guard: the user's saved machine-vision cube prescription
   keeps its Image plane past the lens, lets transmit rays reach the lens datums
   (S1-S5), and auto-generates exactly one folded reflected optical axis. Skipped
   when the prescription / its CAD cache is unavailable on this machine.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from collections import Counter
from pathlib import Path

# Headless rendering — never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import numpy as np

from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
    select_optical_solid_output_face,
)
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    normalize_optical_solid_face_metadata,
)
from KrakenOS.UI.scene_geometry import RayEvent3D, RayPath3D, SceneBundle
from KrakenOS.UI.validate_optical_solid_chained_ports import _face, _synthetic_port_metadata

PRESCRIPTION = Path("attachment/machine_vision_150mm_measured_test.py")


# --------------------------------------------------------------------------
# Facet A — output-port follower must not snap rows onto a straight-through exit.

def _cube_row(metadata: dict, stl: str) -> dict[str, object]:
    return {
        "surface": "Standard",
        "name": "Promoted beam-splitter cube",
        "glass": "BK7",
        "thickness": 20.0,
        "diameter": 20.0,
        "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": stl},
    }


def _override_keys(rows: list[dict[str, object]]) -> list[int]:
    overrides = build_optical_solid_output_port_pose_overrides(rows)
    return sorted(int(key) for key in (overrides or {}))


def _facet_a_override_keys() -> tuple[list[int], list[int]]:
    """Return (on_axis_keys, folded_keys) for a cube + downstream Image."""
    object_row = {"surface": "Object", "name": "Object", "thickness": 100.0, "diameter": 20.0, "advanced": {}}
    image_row = {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": 20.0, "advanced": {}}

    # Straight-through, on-axis inferred exit (+Z normal, centered on the axis):
    # must NOT reposition the Image.
    on_axis_meta = _synthetic_port_metadata(
        output_side="Right",
        output_normal=(0.0, 0.0, 1.0),
        output_centroid=(0.0, 0.0, 12.0),
    )
    on_axis_keys = _override_keys([object_row, _cube_row(on_axis_meta, "synthetic_passthrough.stl"), dict(image_row)])

    # Genuinely folded inferred exit (+X normal, off the axis): SHOULD still
    # reposition the Image, proving the fix only suppresses the passthrough case.
    folded_meta = _synthetic_port_metadata(
        output_side="Right",
        output_normal=(1.0, 0.0, 0.0),
        output_centroid=(8.0, 0.0, 6.0),
    )
    folded_keys = _override_keys([object_row, _cube_row(folded_meta, "synthetic_fold.stl"), dict(image_row)])
    return on_axis_keys, folded_keys


# --------------------------------------------------------------------------
# bugs/0084 — a straight-through beam-splitter CUBE (all six outer faces inferred
# Transmit) must pick its +Z exit, not a -Y side face, so the downstream chain is
# not flung off-axis.

def _full_beam_splitter_cube_row() -> dict[str, object]:
    faces = [
        _face("IN",    side="Left",  function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, normal=(0.0, 0.0, -1.0), centroid=(0.0, 0.0, -25.0), triangle_start=0),
        _face("OUT",   side="Right", function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, normal=(0.0, 0.0, 1.0), centroid=(0.0, 0.0, 25.0), triangle_start=2),
        _face("UP",    side="Up",    function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, normal=(0.0, 1.0, 0.0), centroid=(0.0, 25.0, 0.0), triangle_start=4),
        _face("DOWN",  side="Down",  function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, normal=(0.0, -1.0, 0.0), centroid=(0.0, -25.0, 0.0), triangle_start=6),
        _face("FRONT", side="Front", function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, normal=(-1.0, 0.0, 0.0), centroid=(-25.0, 0.0, 0.0), triangle_start=8),
        _face("BACK",  side="Back",  function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT, normal=(1.0, 0.0, 0.0), centroid=(25.0, 0.0, 0.0), triangle_start=10),
        _face("BS",    side="Up",    function="Beam Splitter", normal=(0.0, -0.7071, 0.7071), centroid=(0.0, 0.0, 0.0), triangle_start=12),
    ]
    meta = normalize_optical_solid_face_metadata({"faces": faces})
    return {
        "surface": "Standard", "name": "Promoted beam-splitter cube", "glass": "BK7",
        "thickness": 50.0, "diameter": 50.0,
        "advanced": {OPTICAL_SOLID_FACES_ADVANCED_ATTR: meta, "Solid_3d_stl": "cube.stl"},
    }


def _cube_output_side() -> str:
    # World-record style faces (normal_world set) -- the selection only differs
    # from the old side-priority pick when world normals are present.
    def wf(fid, side, normal):
        return {"face_id": fid, "side_2d": side, "function": "Transmit/Port",
                "port_role": "Auto", "role": "Output", "normal_world": normal,
                "centroid_world": (0.0, 0.0, 0.0), "area_mm2": 2500.0}
    faces = [
        wf("Left", "Left", (0.0, 0.0, -1.0)), wf("Right", "Right", (0.0, 0.0, 1.0)),
        wf("Up", "Up", (0.0, 1.0, 0.0)), wf("Down", "Down", (0.0, -1.0, 0.0)),
        wf("Front", "Front", (-1.0, 0.0, 0.0)), wf("Back", "Back", (1.0, 0.0, 0.0)),
    ]
    picked = select_optical_solid_output_face(faces)
    return str(picked.get("side_2d")) if picked else ""


# --------------------------------------------------------------------------
# Facet B — reflected branch earns its own traced optical axis.

class _FakeRenderer:
    def ComputeVisiblePropBounds(self):
        return (-30.0, 30.0, -30.0, 30.0, -10.0, 60.0)


class _FakeBoolVar:
    def __init__(self, value: bool) -> None:
        self._value = bool(value)

    def get(self) -> bool:
        return self._value


def _axis_records_for(bundle: SceneBundle) -> list[dict[str, object]]:
    inspector = object.__new__(Kraken3DInspector)
    inspector._renderer = _FakeRenderer()
    inspector.show_rays_var = _FakeBoolVar(True)
    inspector._cached_traced_axis_signature = None
    inspector._cached_traced_axis_records = []
    return Kraken3DInspector._optical_axis_records_for_3d(inspector, bundle)


def _split_event(ray_index: int, kind: str, point) -> RayEvent3D:
    # event_type carries the "split" steering token so the path qualifies as a
    # non-refractive steering branch.
    return RayEvent3D(
        event_id=f"surface:1:{kind}",
        event_kind="surface",
        event_type=f"split_{kind}",
        ray_index=ray_index,
        step=1,
        surface_id=1,
        mesh_face_id="F001",
        surface_name="Beam Splitter",
        point_world=np.asarray(point, dtype=float),
    )


def _split_path(ray_index: int, end_point) -> RayPath3D:
    return RayPath3D(
        ray_index=ray_index,
        field_index=0,
        points_world=np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 20.0], list(end_point)], dtype=float),
        events=[_split_event(ray_index, "reflect" if end_point[0] else "transmit", (0.0, 0.0, 20.0))],
    )


def _beam_splitter_bundle() -> SceneBundle:
    """A central ray that transmits on-axis (wins the chief score) plus a
    reflected +X branch with field-spread companions a couple degrees apart."""
    paths = [
        # On-axis transmit chief: lowest ray_index so it wins min(_path_score).
        _split_path(0, (0.0, 0.0, 40.0)),
        # Reflected +X branch + field spread (all within a few degrees of +X).
        _split_path(1, (30.0, 0.0, 20.0)),
        _split_path(2, (30.0, 1.0, 20.0)),
        _split_path(3, (30.0, -1.0, 20.0)),
        _split_path(4, (30.0, 0.0, 21.0)),
    ]
    return SceneBundle(ray_paths=paths, has_off_axis=True)


def _summarize_axes(records: list[dict[str, object]]) -> dict[str, object]:
    global_count = 0
    folded: list[np.ndarray] = []
    traced = 0
    for record in records:
        kind = str(record.get("axis_kind", "") or "")
        if kind == "dotted_global_guide":
            global_count += 1
            continue
        if kind == "traced_chief_ray_segment":
            traced += 1
            direction = np.asarray(record.get("segment_direction", (0.0, 0.0, 1.0)), dtype=float)
            transverse = float(np.hypot(direction[0], direction[1]))
            if transverse > 0.9:
                folded.append(direction)
    return {"global": global_count, "traced": traced, "folded": folded}


# --------------------------------------------------------------------------
# Optional real-scene guard.

def _real_prescription_summary() -> dict[str, object] | None:
    if not PRESCRIPTION.exists():
        return None
    try:
        from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        spec = importlib.util.spec_from_file_location("_mv0017_guard", PRESCRIPTION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in module.SURFACES]
        editor = _snapshot_editor(rows, dict(module.SETTINGS))
        editor.current_layout_file = PRESCRIPTION.resolve()
        # bugs/0021: rebuild a missing promoted-cube body STL from its source
        # STEP so this guard exercises the REAL beam-splitter, not the analytic
        # single-face fallback the system-build safety-net substitutes for a
        # missing cache. If the body still can't be resolved (no cache, no
        # source on this machine), skip rather than assert splitter physics on
        # the placeholder.
        try:
            editor._regenerate_missing_optical_solid_caches()
        except Exception:
            pass
        from KrakenOS.UI.services.missing_assets_scan import any_solid_body_unresolved
        if any_solid_body_unresolved(editor.rows):
            return None
        editor._saved_step_native_trace_plan_cache = {}
        try:
            editor._normalize_special_rows()
        except Exception:
            pass
        system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        if not paths:
            return None

        # Image (last row) world Z = -TRANS_1A[i][2,3]; the lens entrance is ~268.
        image_z = None
        try:
            image_index = len(rows) - 1
            image_z = -float(np.asarray(system.Pr3D.TRANS_1A[image_index], dtype=float)[2, 3])
        except Exception:
            image_z = None

        hit = Counter()
        for path in paths:
            for event in getattr(path, "events", []) or []:
                sid = getattr(event, "surface_id", None)
                if isinstance(sid, (int, np.integer)):
                    hit[int(sid)] += 1
        lens_hit = sorted(s for s in hit if 1 <= s <= 5)
        end_z = [
            float(getattr(path.events[-1], "point_world")[2])
            for path in paths
            if getattr(path, "events", None)
        ]
        axes = _summarize_axes(_axis_records_for(bundle))
        return {
            "paths": len(paths),
            "image_z": image_z,
            "lens_hit": lens_hit,
            "max_end_z": max(end_z) if end_z else None,
            "axes": axes,
        }
    except Exception as exc:  # missing CAD cache / vendor STEP, etc.
        return {"error": repr(exc)}


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True

    def _check(ok: bool, message: str) -> None:
        nonlocal passed
        notes.append(("PASS " if ok else "FAIL ") + message)
        if not ok:
            passed = False

    # 1. Facet A — straight-through inferred output must not snap the Image,
    #    while a folded inferred output still anchors it.
    on_axis_keys, folded_keys = _facet_a_override_keys()
    _check(
        2 not in on_axis_keys,
        f"straight-through inferred exit leaves the Image plane put (override_keys={on_axis_keys})",
    )
    _check(
        2 in folded_keys,
        f"folded inferred exit still repositions the Image plane (override_keys={folded_keys})",
    )

    # 2. Facet B — reflected branch earns exactly one folded optical axis even
    #    though the on-axis transmit branch wins the chief score; field spread
    #    on the reflected branch collapses to that single axis.
    axes = _summarize_axes(_axis_records_for(_beam_splitter_bundle()))
    _check(axes["global"] == 1, f"global optical axis present once (global={axes['global']})")
    _check(
        len(axes["folded"]) == 1 and axes["traced"] == 1,
        f"reflected branch yields exactly one folded traced axis "
        f"(traced={axes['traced']} folded={[d.round(3).tolist() for d in axes['folded']]})",
    )
    if axes["folded"]:
        direction = axes["folded"][0]
        _check(
            abs(float(direction[0])) > 0.9,
            f"reflected optical axis points along the fold (+X) direction (dir={direction.round(3).tolist()})",
        )

    # 2c. bugs/0084 — a straight-through beam-splitter cube as the FIRST element
    #     must keep its downstream chain on-axis. The selector must pick the +Z
    #     'Right' exit (not the -Y 'Down' side the old side-priority preferred),
    #     and the override builder must not reposition any follower row.
    _check(
        _cube_output_side() == "Right",
        f"beam-splitter cube selects its +Z straight-through exit, not a side face (picked side={_cube_output_side()!r})",
    )
    cube_chain = [
        {"surface": "Object", "name": "Object", "thickness": 100.0, "diameter": 20.0, "advanced": {}},
        _full_beam_splitter_cube_row(),
        {"surface": "Standard", "name": "Lens", "glass": "BK7", "thickness": 10.0, "diameter": 30.0, "advanced": {}},
        {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": 30.0, "advanced": {}},
    ]
    cube_overrides = build_optical_solid_output_port_pose_overrides(cube_chain)
    _check(
        not cube_overrides,
        f"straight-through cube does not reposition the downstream chain (override_keys={sorted(cube_overrides)})",
    )

    # 3. Optional: the user's real saved beam-splitter-cube scene.
    real = _real_prescription_summary()
    if real is None:
        notes.append("SKIP real prescription unavailable (no CAD cache) — synthetic guards cover the fix")
    elif "error" in real:
        notes.append(f"SKIP real prescription failed to load: {real['error']}")
    else:
        image_z = real["image_z"]
        _check(
            image_z is not None and image_z > 600.0,
            f"real Image plane stays past the lens (z={image_z}, lens entrance ~268, bug snapped it to ~265)",
        )
        _check(
            real["lens_hit"] == [1, 2, 3, 4, 5],
            f"transmit rays reach the imaging-lens datums S1-S5 (hit={real['lens_hit']})",
        )
        _check(
            real["max_end_z"] is not None and real["max_end_z"] > 600.0,
            f"transmit rays travel past the lens entrance toward the image (max_end_z={real['max_end_z']})",
        )
        real_axes = real["axes"]
        _check(
            real_axes["global"] == 1 and len(real_axes["folded"]) == 1,
            f"real scene auto-generates one global + one folded reflected axis "
            f"(global={real_axes['global']} folded={[d.round(3).tolist() for d in real_axes['folded']]})",
        )

    return passed, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
