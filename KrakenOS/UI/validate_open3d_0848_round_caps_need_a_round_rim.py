"""Display-free guard: synthetic round end-caps are only made for a body whose rim IS round, and
a hover line never says "face face" (bugs/0848).

The day-1 ghost: hovering om05a's housing drew a flat 75 x 156 mm outline through it, labelled
"OPTICAL STEP outer +axis face face". Neither "outer +axis face" nor the plane is a STEP face:
open3d_round_lens_pick synthesises two end-caps for any body tagged round-lens-like, and the tag
(`_mesh_round_lens_axis`) is a second-moment test -- two similar spreads and one thin one -- that
a BOX passes. Measured across eight scenes, every body it tagged was a false positive: the om05a
prism assembly (rim radius varies 52% with azimuth), a Pyrite45 camera (58%), a Basler
telecentric barrel (98%); no real vendor lens barrel was tagged at all. A disc varies by
tessellation noise.

  B  a 100 x 80 x 30 box: CONTROL -- the round-lens test tags it; the real pick, driven through a
     fake inspector, synthesised an "outer +axis face" for it before and synthesises none now
  C  a round cylinder still gets its "outer +axis face" cap (the feature is kept for round bodies)
  M  the rim metric: 0 for a circle, 0.29 for a square, None when too sparse to judge
  R  the real prism assembly is measured not round (SKIP if not checked out)
  L  hover lines: "outer +axis face" is not followed by another "face"
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _fake_inspector(mesh):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K

    actor = SimpleNamespace(
        _kraken_round_lens_like_step_body=True,
        GetVisibility=lambda: True,
        GetProperty=lambda: SimpleNamespace(GetOpacity=lambda: 1.0),
        GetMapper=lambda: SimpleNamespace(GetInput=lambda: mesh),
    )
    editor = SimpleNamespace(
        _step_overlay_face_metadata=lambda _label: {"faces": []},
        _transformed_imported_step_mesh_for_label=lambda _label: mesh,
    )
    return SimpleNamespace(
        editor=editor,
        _step_label_is_round_lens_like=lambda _label: True,
        # looking straight down the body's thin axis at its +z end
        _display_pick_ray=lambda _xy: (np.array([0.0, 0.0, 200.0]), np.array([0.0, 0.0, -1.0])),
        _step_actor_map={"optical": ["actor:1"]},
        _actor_step_rotate_map={},
        _actor_step_rotate_visual_keys=set(),
        _actor_by_key={"actor:1": actor},
        _mesh_round_lens_axis=K._mesh_round_lens_axis,
        _normalized_vector=K._normalized_vector,
        _planar_outline_from_points=K._planar_outline_from_points,
    )


def run_checks() -> tuple[bool, list[str]]:
    import pyvista as pv
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K
    from KrakenOS.UI.services import open3d_round_lens_pick as pick
    from KrakenOS.UI.services.open3d_interaction import _face_note_text

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- B: a box --------------------------------------------------------------------------------
    box = pv.Box(bounds=(-50.0, 50.0, -40.0, 40.0, -15.0, 15.0), level=4).triangulate()
    tagged = K._mesh_round_lens_axis(box) is not None
    real_gate = pick.rim_is_round
    pick.rim_is_round = lambda *_a, **_k: True
    try:
        before = pick.round_lens_feature_for_display_xy(_fake_inspector(box), "optical", (0, 0))
    finally:
        pick.rim_is_round = real_gate
    after = pick.round_lens_feature_for_display_xy(_fake_inspector(box), "optical", (0, 0))
    ok(tagged and isinstance(before, dict) and before.get("face_id") == "outer +axis face",
       f"B1: CONTROL -- a 100 x 80 x 30 box passes the round-lens test and, without the rim gate, "
       f"the real pick synthesises {before.get('face_id') if isinstance(before, dict) else before!r} for it")
    ok(after is None,
       f"B2: with the gate the box gets NO synthetic cap ({after!r}) -- its real faces stay pickable")

    # ---- C: a round body keeps the feature -------------------------------------------------------
    lens = pv.Cylinder(center=(0, 0, 0), direction=(0, 0, 1), radius=12.5, height=4.0, resolution=96).triangulate()
    cap = pick.round_lens_feature_for_display_xy(_fake_inspector(lens), "optical", (0, 0))
    # which end is "+axis" follows the sign SVD picks; the claim is that a round body keeps a cap
    ok(isinstance(cap, dict) and cap.get("face_id") in ("outer +axis face", "outer -axis face"),
       f"C: a round cylinder still gets its synthetic cap ({cap.get('face_id') if isinstance(cap, dict) else cap!r}) "
       f"-- the feature is kept for bodies that are round")

    # ---- M: the metric ---------------------------------------------------------------------------
    t = np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False)
    circle = np.c_[10.0 * np.cos(t), 10.0 * np.sin(t), np.zeros_like(t)]
    square = np.c_[np.clip(14.2 * np.cos(t), -10, 10), np.clip(14.2 * np.sin(t), -10, 10), np.zeros_like(t)]
    z = np.array([0.0, 0.0, 1.0])
    v_circle = pick.rim_radius_variation(circle, np.zeros(3), z)
    v_square = pick.rim_radius_variation(square, np.zeros(3), z)
    ok(v_circle is not None and v_circle < 0.01 and v_square is not None and abs(v_square - (1 - 1 / np.sqrt(2))) < 0.03
       and pick.rim_radius_variation(circle[:5], np.zeros(3), z) is None,
       f"M: circle {v_circle:.3f}, square {v_square:.3f} (1 - 1/sqrt 2 = 0.293), a 5-point cloud is "
       f"not judged -- threshold {pick.ROUND_RIM_MAX_VARIATION}")

    # ---- R: the real prism assembly -----------------------------------------------------------
    scene = Path("attachment/om05a_folded.py")
    if not (scene.exists() and Path("attachment/om05a_components/prism_assembly_chunk_armA.step").exists()):
        notes.append("= R: SKIP -- the om05a prism assembly is not checked out here")
    else:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        try:
            app.layout_files["s"] = scene
            app.load_layout_by_name("s")
            mesh = app._transformed_imported_step_mesh_for_label("optical")
            hit = K._mesh_round_lens_axis(mesh)
            variation = pick.rim_radius_variation(hit[2], hit[0], hit[1]) if hit is not None else None
            ok(hit is not None and variation is not None and variation > 0.4 and not pick.rim_is_round(hit[2], hit[0], hit[1]),
               f"R: the om05a prism assembly still passes the second-moment test (the tag is unchanged "
               f"-- it also suppresses dense select edges) but its rim varies {100 * (variation or 0):.0f}% "
               f"with azimuth, so no synthetic cap is made for it")
        finally:
            app.destroy()

    # ---- L: the hover line -----------------------------------------------------------------------
    ok(_face_note_text("outer +axis face") == " outer +axis face"
       and _face_note_text("S006/F005") == " S006/F005 face"
       and _face_note_text("") == " face" and _face_note_text("face") == " face",
       "L: 'outer +axis face' is not followed by another 'face'; a real face id still is")

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
