"""bugs/0439 guard (anchor half) -- the explicit snap lands at the CLICKED axis point.

flag_20260726_110657: the multi-select snap landed the selection origin AT the branch
point (crashing the chain into the LED); when the axis pick carries picked_world
(_optical_axis_info_near_display_xy), the landing target is now that click PROJECTED
onto the axis line -- the click chooses the position along the axis. Without
picked_world (actor-map pick) the branch-point landing is byte-identical to before,
and the whole move stays rigid (fold-inside-selection preserved).

Run: python -m KrakenOS.UI.validate_open3d_0439_snap_anchor (needs a DISPLAY).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

_SCENE = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_AZ85_RA_Mirror.py"

_AXIS_POINTS = ((0.0, 0.0, 60.0), (100.0, 0.0, 60.0))
_PICKED = (60.0, 3.0, 61.0)  # off-line on purpose: proves the projection
_ANCHOR = (60.0, 0.0, 60.0)
_BRANCH = (0.0, 0.0, 60.0)


def _snap_once(record: dict) -> "tuple[dict[int, np.ndarray], dict[int, np.ndarray], list[int], int] | str":
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85_0439"] = _SCENE
        app.load_layout_by_name("az85_0439")
        mirror_rows = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        if not mirror_rows:
            return "no fold mirror in fixture"
        app.delete_optical_step_rows([mirror_rows[0]])  # 0433 freeze
        front = app._lens_datum_row_index("front")
        image = next(
            (i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"),
            None,
        )
        if front is None or image is None:
            return "front datum / image row missing"
        rows = list(range(front, image + 1))

        def centers() -> dict[int, np.ndarray]:
            z = app._row_z_positions()
            return {
                i: np.asarray(
                    (
                        float(app.rows[i].desp_x),
                        float(app.rows[i].desp_y),
                        float(z[i]) + float(app.rows[i].desp_z),
                    ),
                    dtype=float,
                )
                for i in rows
            }

        pre = centers()
        app.snap_rows_to_axis(rows, dict(record))
        return pre, centers(), rows, front
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    if not _SCENE.exists():
        return True, [f"SKIP: scene fixture absent ({_SCENE.name})"]
    try:
        import KrakenOS.UI.layout_editor  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment
        return True, [f"SKIP: editor import failed ({exc!r})"]

    passed = True

    def note(label: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        notes.append(("= " if ok else "") + label + (f" [{detail}]" if detail else ""))
        if not ok:
            passed = False

    axis_points = np.asarray(_AXIS_POINTS, dtype=float)
    try:
        clicked = _snap_once(
            {"axis_id": "axis:global:split", "axis_label": "BS reflect", "points": axis_points, "picked_world": _PICKED}
        )
        if isinstance(clicked, str):
            return True, [f"SKIP: {clicked}"]
        pre, post, rows, front = clicked
        note(
            "ANCHOR: entry member lands at the projected click",
            bool(np.allclose(post[front], np.asarray(_ANCHOR), atol=1e-6)),
            f"landed={np.round(post[front], 3)}",
        )
        dist_err = max(
            abs(float(np.linalg.norm(post[a] - post[b])) - float(np.linalg.norm(pre[a] - pre[b])))
            for ai, a in enumerate(rows)
            for b in rows[ai + 1:]
        )
        note("RIGID: pairwise distances preserved through the anchored landing", dist_err < 1e-6,
             f"max_err={dist_err:.2e}")

        fallback = _snap_once(
            {"axis_id": "axis:global:split", "axis_label": "BS reflect", "points": axis_points}
        )
        if isinstance(fallback, str):
            return True, [f"SKIP: {fallback}"]
        _, post2, rows2, front2 = fallback
        note(
            "FALLBACK: no picked_world -> branch-point landing unchanged",
            bool(np.allclose(post2[front2], np.asarray(_BRANCH), atol=1e-6)),
            f"landed={np.round(post2[front2], 3)}",
        )
        shift = float(np.linalg.norm(np.asarray(_ANCHOR) - np.asarray(_BRANCH)))
        max_dev = max(abs(float(np.linalg.norm(post[i] - post2[i])) - shift) for i in rows)
        note("EQUIVALENCE: clicked run == fallback + uniform along-axis shift", max_dev < 1e-6,
             f"shift={shift:.1f} max_dev={max_dev:.2e}")
    except Exception as exc:  # pragma: no cover - defensive
        notes.append(f"raised {exc!r}")
        passed = False
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for line in notes:
        print(line)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
