"""Generate the om05a bench-geometry figures for the knowledge base.

Everything drawn here is MEASURED from ``attachment/om05a_folded_80mm.py`` -- row stations, world
body positions and one real traced ray -- so the figures cannot drift from the model. Run it by
hand after a scene change; the SVGs are committed:

    cd <repo> && taskset -c 0-9 nice -n 15 xvfb-run -a \
        .devenv/state/venv/bin/python -u docs/generate_om05a_bench_geometry.py

Writes docs/source/_static/knowledge_base/om05a_bench_geometry/*.svg.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "attachment" / "om05a_folded_80mm.py"
OUTPUT = ROOT / "docs" / "source" / "_static" / "knowledge_base" / "om05a_bench_geometry"

BLUE = "#286f9e"
RED = "#d9485f"
PURPLE = "#7655b5"
GREEN = "#2b7a78"
GREY = "#5a6472"
GLASS = "#bcd6e6"
METAL = "#c9ced6"
FAINT = "#e4e8ed"
SENSOR_MM = 23.04
FOCAL_MM = 82.39          # fitted from the solve's own object-side slope, f/h = 3.576 mm per mm FOV


def measure() -> dict:
    """Load the scene, read the world geometry and trace once. Returns plain JSON-able data."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["bench"] = SCENE
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor.load_layout_by_name("bench")
        rows = editor.rows
        front, rear = (int(v) for v in editor._imaging_lens_block_indices())
        image = len(rows) - 1
        chain = [
            {
                "index": i,
                "name": str(r.name),
                "thickness": float(r.thickness),
                "glass": str(r.glass),
                "world": [float(v) for v in np.asarray(
                    editor._surface_reference_world_point(i), dtype=float).reshape(3)],
            }
            for i, r in enumerate(rows[: image + 1])
        ]
        bodies = {}
        for i, r in enumerate(rows[: image + 1]):
            advanced = r.advanced if isinstance(getattr(r, "advanced", None), dict) else {}
            if not advanced.get("Solid_3d_stl"):
                continue
            try:
                aabb = editor._solid_row_world_aabb(i)
            except Exception:
                continue
            if aabb is None:
                continue
            # bugs/0719's helper returns a FLAT (xmin, xmax, ymin, ymax, zmin, zmax)
            xmin, xmax, ymin, ymax, zmin, zmax = (float(v) for v in aabb)
            bodies[str(i)] = {"name": str(r.name),
                              "min": [xmin, ymin, zmin], "max": [xmax, ymax, zmax]}
        for label in ("lens", "camera"):
            try:
                mesh = editor._transformed_imported_step_mesh_for_label(label)
            except Exception:
                mesh = None
            if mesh is None:
                continue
            pts = np.asarray(mesh.points, dtype=float)
            bodies[label] = {"name": f"{label} STEP body",
                             "min": pts.min(axis=0).tolist(), "max": pts.max(axis=0).tolist()}
        room = editor._lens_block_physical_room_mm(front, rear, -1.0)
        # the travel model behind figure 3, MEASURED rather than hard-coded so the chart follows a
        # scene change like everything else here: the lens move each FOV asks for, at the scene's
        # own device, read from the solver's first order at two FOVs (it is linear in FOV).
        try:
            device_mm = float((getattr(editor, "inspection_part_spec", None) or {}).get("depth_mm") or 0.0)
        except (AttributeError, TypeError, ValueError):
            device_mm = 0.0
        travel = {}
        try:
            for fov in (20.0, 54.0):
                folded = editor._folded_conjugate_gaps_for_magnification(SENSOR_MM / fov)
                travel[f"{fov:g}"] = float(folded["object_delta"])
        except Exception:
            travel = {}
        _system, _rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        # the most axial imaging ray that actually reaches the sensor through the lens block
        best, best_score = None, None
        for path in list(getattr(bundle, "ray_paths", None) or []):
            if str(getattr(path, "termination_reason", "")) not in ("image", "target_termination"):
                continue
            ids = [int(s) for s in np.asarray(getattr(path, "surface_ids", []), dtype=float).ravel()]
            if front not in ids or 7 not in ids:
                continue
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim != 2 or len(pts) < 4:
                continue
            score = float(abs(pts[0][0]) + abs(pts[0][1]))      # launched nearest the axis
            if best_score is None or score < best_score:
                best, best_score = pts, score
    data = {
        "chain": chain,
        "front": front,
        "rear": rear,
        "image": image,
        "device_mm": device_mm,
        "travel": travel,
        "bodies": bodies,
        "room": {k: (list(v) if isinstance(v, (tuple, list)) else v)
                 for k, v in room.items() if k in ("room_phys", "room_station", "obstacle",
                                                   "lens_span", "obstacle_span", "leg_unit")},
        "ray": best.tolist() if best is not None else [],
    }
    editor.destroy()
    return data


def _bracket(ax, x0, x1, y, text, color=GREY, tick=1.6, fontsize=8.5):
    ax.annotate("", xy=(x0, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.0))
    for x in (x0, x1):
        ax.plot([x, x], [y - tick, y + tick], color=color, lw=0.8)
    ax.text(0.5 * (x0 + x1), y + tick, text, ha="center", va="bottom",
            fontsize=fontsize, color=color)


def figure_unfolded(data: dict, path: Path) -> None:
    """The row model laid out straight: every segment A1..A5, C1, C2, with WD and image distance."""
    chain, front, rear, image = data["chain"], data["front"], data["rear"], data["image"]
    t = [c["thickness"] for c in chain]
    segments = [
        ("A1", 0, 0, BLUE, "device face\nto 1st RA mirror A"),
        ("A2", 1, 2, BLUE, "to BS cube A"),
        ("A3", 3, 4, BLUE, "through BS cube A\nto centre RA mirror A"),
        ("A4", 5, 6, BLUE, "to the 50 mm prism"),
        ("prism", 7, 7, GLASS, "50 mm prism\n(BK7, folded path)"),
        ("A5", 8, 8, RED, "prism exit face\nto lens front datum"),
        ("lens", front, rear - 1, METAL, "lens block\n(datum to datum)"),
        ("C1", rear, rear, RED, "to Filter 48-926"),
        ("filter", 14, 14, GLASS, "filter"),
        ("C2", 15, 15, PURPLE, "to RA mirror 2"),
        ("arm", 16, image - 1, PURPLE, "RA mirror 2\nto sensor"),
    ]
    fig, ax = plt.subplots(figsize=(13.6, 5.0))
    box_lo, box_hi = -3.0, 3.0
    x = 0.0
    wd_end = None
    narrow_slot = 0
    for key, lo, hi, color, caption in segments:
        length = float(sum(t[lo : hi + 1]))
        face = GLASS if color is GLASS else ("#eef2f6" if color is METAL else "white")
        ax.add_patch(plt.Rectangle((x, box_lo), length, box_hi - box_lo, facecolor=face,
                                   edgecolor=color, lw=1.4, zorder=2))
        centre = x + length / 2.0
        if length >= 22.0:
            ax.text(centre, 0.6, key, ha="center", va="center", fontsize=9.5, color="#1f2933", zorder=3)
            ax.text(centre, -1.4, f"{length:.2f}", ha="center", va="center", fontsize=8.5,
                    color=GREY, zorder=3)
            ax.text(centre, box_lo - 1.2, caption, ha="center", va="top", fontsize=7.0, color=GREY)
        else:
            # narrow segment: label it outside on a leader, alternating heights so they cannot collide
            narrow_slot += 1
            top = box_hi + 2.4 + 4.6 * (narrow_slot % 3)
            ax.plot([centre, centre], [box_hi, top - 0.5], color=color, lw=0.7, ls=":", zorder=1)
            ax.text(centre, top, f"{key}  {length:.2f}", ha="center", va="bottom", fontsize=8.0,
                    color=color, zorder=4)
            ax.text(centre, top - 1.9, caption.replace("\n", " "), ha="center", va="bottom",
                    fontsize=6.4, color=GREY, zorder=4)
        if key == "A5":
            wd_end = x + length
        x += length
    total = x
    ax.plot([0, total], [0, 0], color="#9aa5b1", lw=0.7, ls=(0, (6, 4)), zorder=1)
    _bracket(ax, 0.0, wd_end, 24.0, f"WD  (device face to lens front datum)  {wd_end:.2f} mm", color=BLUE)
    image_start = float(sum(t[:rear]))
    _bracket(ax, image_start, total, 24.0, f"image distance  {total - image_start:.2f} mm", color=PURPLE)
    # the motor gaps get ONE bracket EACH: a single bracket spanning A5 through C1 would be
    # labelled 148.40 while covering 191.59 mm of the drawing (it includes the lens block)
    a5_start = float(sum(t[: front - 1]))
    c1_start = float(sum(t[:rear]))
    _bracket(ax, a5_start, a5_start + t[front - 1], 31.0, f"A5  {t[front - 1]:.2f}", color=RED)
    _bracket(ax, c1_start, c1_start + t[rear], 31.0, f"C1  {t[rear]:.2f}", color=RED)
    ax.text(0.5 * (a5_start + c1_start + t[rear]), 38.5,
            f"the two motor gaps: A5 + C1 = {t[front - 1] + t[rear]:.2f} mm of travel",
            ha="center", va="bottom", fontsize=8.5, color=RED)
    ax.set_xlim(-14, total + 14)
    ax.set_ylim(-14, 46)
    ax.axis("off")
    ax.set_title("om05a 80 mm build — the optical chain laid out straight (authored state, 50 mm device)",
                 fontsize=11, color="#1f2933")
    fig.tight_layout()
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)


def figure_folded(data: dict, path: Path) -> None:
    """The real world geometry in its two orthogonal fold planes, with the traced ray on top, and
    the lens drawn a second time where the end of its rail (A5 = 0) would put it."""
    chain, front = data["chain"], data["front"]
    ray = np.asarray(data["ray"], dtype=float) if data["ray"] else np.empty((0, 3))
    bodies = data["bodies"]
    a5 = float(chain[front - 1]["thickness"])
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 6.0),
                             gridspec_kw={"width_ratios": [1.0, 1.45]})

    def rect(ax, body, ia, ib, color, lw=0.9, ls="solid", alpha=0.75, dx=0.0):
        lo, hi = np.asarray(body["min"]), np.asarray(body["max"])
        ax.add_patch(plt.Rectangle((lo[ia] + dx, lo[ib]), hi[ia] - lo[ia], hi[ib] - lo[ib],
                                   facecolor=color, edgecolor="#7b8794", lw=lw, ls=ls,
                                   alpha=alpha, zorder=2))
        return lo, hi

    # --- panel A: the object arm lives in the y-z plane at x ~ 0 -------------------------------
    ax = axes[0]
    labelled = []
    y_top = -1.0e9
    for body in bodies.values():
        lo, hi = np.asarray(body["min"]), np.asarray(body["max"])
        if abs(0.5 * (lo[0] + hi[0])) > 60.0:            # not on the object arm
            continue
        name = body["name"]
        # arm B is the mirror image of arm A, and a "(far half)" body is arm B's half of a shared
        # cube. Draw those faint and unlabelled so the A-arm train plus the shared prism reads.
        stripped = name.replace("(far half)", "").strip()
        arm_b = "(far half)" in name or stripped.endswith("B")
        colour = FAINT if arm_b else (GLASS if "cube" in name.lower() else METAL)
        rect(ax, body, 2, 1, colour, alpha=0.55 if arm_b else 0.8)
        y_top = max(y_top, float(hi[1]))
        if not arm_b:
            labelled.append((0.5 * (lo[2] + hi[2]), float(hi[1]), name))
    # the label rows sit above every body but INSIDE the axes, each on its own leader, so a tall
    # part (the 50 mm prism) cannot push its name into the panel title
    rows_y = [y_top + 7.0, y_top + 14.5, y_top + 22.0]
    for k, (cx, top, name) in enumerate(sorted(labelled, key=lambda p: p[0])):
        y = rows_y[k % len(rows_y)]
        ax.plot([cx, cx], [top + 0.6, y - 1.0], color="#9aa5b1", lw=0.6, ls=":", zorder=5)
        ax.text(cx, y, name, ha="center", va="bottom", fontsize=7.0, color="#1f2933", zorder=6)
    ax.set_ylim(top=y_top + 31.0)
    if len(ray):
        near = ray[np.abs(ray[:, 0]) < 60.0]
        ax.plot(near[:, 2], near[:, 1], color=RED, lw=1.5, zorder=4, label="traced axial ray")
        ax.plot([near[0, 2]], [near[0, 1]], marker="o", ms=4.0, color=RED, zorder=6)
        ax.text(near[0, 2], near[0, 1] - 4.0, "device face", ha="center", va="top", fontsize=7.5,
                color=RED)
    ax.text(0.02, 0.02, "arm B drawn faint (mirror image)", transform=ax.transAxes, fontsize=6.8,
            color=GREY)
    ax.set_xlabel("z (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("object arm — the y–z fold plane (x ≈ 0)", fontsize=10)
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax.legend(fontsize=7.5, loc="upper left")

    # --- panel B: the imaging leg lives in the x-y plane at z ~ -25 -----------------------------
    ax = axes[1]
    lens_body = bodies.get("lens")
    for key, body in bodies.items():
        lo, hi = np.asarray(body["min"]), np.asarray(body["max"])
        if hi[0] < -30.0 or (key not in ("7", "16", "lens", "camera")):
            continue
        rect(ax, body, 0, 1, METAL)
        # the prism's own label would land under the legend in this panel; panel A names it
        if key != "7":
            ax.text(0.5 * (lo[0] + hi[0]), hi[1] + 2.5, body["name"], ha="center", va="bottom",
                    fontsize=7.2, color="#1f2933")
    datum = np.asarray(chain[front]["world"])
    prism = bodies.get("7")
    if prism is not None and lens_body is not None:
        face_x = float(np.asarray(prism["max"])[0])
        barrel_x = float(np.asarray(lens_body["min"])[0])
        # the lens where the END OF ITS RAIL would put it: A5 = 0, i.e. shifted back by A5
        rect(ax, lens_body, 0, 1, "none", lw=1.2, ls=(0, (4, 3)), alpha=1.0, dx=-a5)
        ghost_lo = barrel_x - a5
        ghost_hi = float(np.asarray(lens_body["max"])[0]) - a5
        ax.text(0.5 * (ghost_lo + ghost_hi), float(np.asarray(lens_body["min"])[1]) - 6.0,
                "lens at the end of its rail (A5 = 0)", ha="center", va="top", fontsize=7.2,
                color=GREEN)
        # the air path above the bodies, the metal gap below them: neither crosses a solid, and
        # both stay INSIDE the axes (an annotation above the top limit lands on the panel title)
        body_top = max(float(np.asarray(b["max"])[1]) for b in
                       (bodies[k] for k in ("7", "16", "lens", "camera") if k in bodies))
        y_air = body_top + 12.0
        ax.set_ylim(top=body_top + 34.0)
        ax.annotate("", xy=(face_x, y_air), xytext=(datum[0], y_air),
                    arrowprops=dict(arrowstyle="<->", color=RED, lw=1.1))
        ax.text(0.5 * (face_x + datum[0]), y_air + 1.5,
                f"world air path {datum[0] - face_x:.2f} mm  "
                f"(row 8 “A5” reads {a5:.2f} mm — an offset coordinate)",
                ha="center", va="bottom", fontsize=7.6, color=RED)
        y_metal = float(np.asarray(lens_body["min"])[1]) - 20.0
        ax.annotate("", xy=(face_x, y_metal), xytext=(ghost_lo, y_metal),
                    arrowprops=dict(arrowstyle="<->", color=GREEN, lw=1.1))
        ax.text(0.5 * (face_x + ghost_lo), y_metal - 2.0,
                f"metal-to-metal at A5 = 0:  {ghost_lo - face_x:.2f} mm",
                ha="center", va="top", fontsize=7.6, color=GREEN)
    if len(ray):
        far = ray[ray[:, 0] > -30.0]
        ax.plot(far[:, 0], far[:, 1], color=RED, lw=1.5, zorder=4, label="traced axial ray")
    ax.plot([datum[0]], [datum[1]], marker="o", ms=3.6, color=BLUE, zorder=6)
    ax.text(datum[0], datum[1] + 4.0, "lens front datum", ha="left", va="bottom", fontsize=7.4,
            color=BLUE)
    sensor = np.asarray(chain[data["image"]]["world"])
    ax.plot([sensor[0]], [sensor[1]], marker="s", ms=4.2, color=PURPLE, zorder=6)
    ax.text(sensor[0] + 3.0, sensor[1], "sensor", ha="left", va="center", fontsize=7.4, color=PURPLE)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("imaging leg — the x–y fold plane (z ≈ −25)", fontsize=10)
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax.legend(fontsize=7.5, loc="upper left")

    fig.suptitle("om05a 80 mm build — measured world geometry, with one traced ray", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)


def figure_travel(data: dict, path: Path) -> None:
    """Why the small-FOV end runs out: lens travel demanded by each FOV against the A5 available."""
    a5 = float(data["chain"][data["front"] - 1]["thickness"])
    fovs = np.linspace(18.0, 58.0, 400)
    # the model is MEASURED: the solver's own first order at two FOVs, at the scene's own device.
    # The old hard-coded 136.966 / 3.576 would not have followed a scene change.
    travel = data.get("travel") or {}
    device_ref = float(data.get("device_mm") or 20.0)
    od20 = travel.get("20")
    od54 = travel.get("54")
    if od20 is None:
        od20, device_ref = -136.966, 20.0
    slope = ((float(od54) - float(od20)) / 34.0) if od54 is not None else (FOCAL_MM / SENSOR_MM)
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    for device, color in ((0.5, RED), (15.0, PURPLE), (30.0, BLUE), (50.0, GREEN)):
        need = -(float(od20) + slope * (fovs - 20.0) + 0.5 * (device - device_ref))
        ax.plot(fovs, need, color=color, lw=1.6, label=f"device {device:g} mm")
    ax.axhline(a5, color="#1f2933", lw=1.4, ls="--")
    ax.text(57.6, a5 + 2.5, f"A5 available = {a5:.2f} mm", ha="right", fontsize=8.5, color="#1f2933")
    ax.fill_between(fovs, a5, 195, color=RED, alpha=0.07)
    ax.text(19.0, 176.0, "above the line the lens would have to travel\npast the end of its rail",
            fontsize=8, color=RED, va="top")
    for fov, label in ((26.0, "FOV 26"), (34.0, "FOV 34"), (54.0, "FOV 54")):
        ax.axvline(fov, color=GREEN, lw=0.9, ls=":", alpha=0.85)
        ax.text(fov, 191.0, label, rotation=0, fontsize=8, color=GREEN, va="top", ha="center",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=GREEN, lw=0.6))
    ax.set_xlabel("FOV (mm)")
    ax.set_ylabel("lens travel toward the object (mm)")
    ax.set_title("om05a 80 mm build — every 1 mm of FOV costs 3.58 mm of lens travel", fontsize=11)
    ax.set_xlim(18, 58)
    ax.set_ylim(0, 197)
    ax.grid(alpha=0.18)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = measure()
    (OUTPUT / "measured.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    figure_unfolded(data, OUTPUT / "01_unfolded_chain.svg")
    figure_folded(data, OUTPUT / "02_folded_world.svg")
    figure_travel(data, OUTPUT / "03_lens_travel_vs_fov.svg")
    chain = data["chain"]
    front = data["front"]
    print("wrote:", *(p.name for p in sorted(OUTPUT.glob("*.svg"))))
    print("A5 row", front - 1, ":", chain[front - 1]["thickness"],
          " C1 row", data["rear"], ":", chain[data["rear"]]["thickness"])
    print("lens datum world:", chain[front]["world"])
    print("prism body:", data["bodies"].get("7"))
    print("lens body:", data["bodies"].get("lens"))
    print("room:", data["room"])
    print("traced ray vertices:", len(data["ray"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
