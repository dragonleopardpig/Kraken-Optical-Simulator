"""Inspection Part -- a 3D rectangular object at the object plane with six blow-out
optical axes (bugs/0661, user feature 2026-08-27: "I want to realize a 3D object
instead of existing 2D object plane. Then blow out 6 optical axis for user to place
lens and cameras.")

Model (phase 1): the part is a W x H x D box whose ACTIVE face coincides with the
scene's object plane -- face centre at the object point, outward normal along the
station's optical axis (object -> lens). The box extends behind the object plane.
Every face gets a dashed blow-out axis from its centre along its outward normal, so
the user sees where the other five stations' cameras would sit, and "Inspect this
face" re-targets the current chain onto another face. Multi-station composition
(six chains in one view) is phase 2 -- see docs/inspection_cell_multi_station.md.

Pure geometry lives here (guarded display-free); the Tk dialog at the bottom.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

FACE_ORDER: tuple[str, ...] = ("front", "back", "left", "right", "top", "bottom")

# Right-handed local face frames (p x q == n): outward normal n, in-plane axes (p, q),
# the (width, height) dims the face shows, and which box extent lies behind it.
_FACE_DEFS: dict[str, dict[str, Any]] = {
    "front": {"n": (0, 0, 1), "p": (1, 0, 0), "q": (0, 1, 0), "dims": ("width", "height"), "extent": "depth"},
    "back": {"n": (0, 0, -1), "p": (-1, 0, 0), "q": (0, 1, 0), "dims": ("width", "height"), "extent": "depth"},
    "right": {"n": (1, 0, 0), "p": (0, 0, -1), "q": (0, 1, 0), "dims": ("depth", "height"), "extent": "width"},
    "left": {"n": (-1, 0, 0), "p": (0, 0, 1), "q": (0, 1, 0), "dims": ("depth", "height"), "extent": "width"},
    "top": {"n": (0, 1, 0), "p": (1, 0, 0), "q": (0, 0, -1), "dims": ("width", "depth"), "extent": "height"},
    "bottom": {"n": (0, -1, 0), "p": (1, 0, 0), "q": (0, 0, 1), "dims": ("width", "depth"), "extent": "height"},
}

DEFAULT_SPEC: dict[str, Any] = {
    "enabled": False,
    "width_mm": 60.0,
    "height_mm": 40.0,
    "depth_mm": 20.0,
    "active_face": "front",
    "axis_reach_mm": 0.0,  # 0 = auto (2.5 x the largest dimension, min 80 mm)
    # bugs/0666: an optional STEP of the REAL part. Its native bounding box supplies
    # W x H x D (x -> W, y -> H, z -> D, front = +z) so the six-face model is unchanged,
    # and the real mesh is drawn in place of the box. Portable: relative to the project
    # root when inside it.
    "step_path": "",
}

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def normalize_inspection_part_spec(spec: Any) -> dict[str, Any]:
    """Coerce a persisted / typed spec into the canonical dict (never raises)."""
    out = dict(DEFAULT_SPEC)
    if not isinstance(spec, dict):
        return out
    out["enabled"] = bool(spec.get("enabled", False))
    for key in ("width_mm", "height_mm", "depth_mm", "axis_reach_mm"):
        try:
            value = float(spec.get(key, out[key]))
        except (TypeError, ValueError):
            value = float(out[key])
        if not math.isfinite(value) or value < 0.0:
            value = float(out[key])
        out[key] = value
    for key in ("width_mm", "height_mm", "depth_mm"):
        if out[key] <= 1e-6:
            out[key] = float(DEFAULT_SPEC[key])
    face = str(spec.get("active_face", "front") or "front").strip().lower()
    out["active_face"] = face if face in _FACE_DEFS else "front"
    out["step_path"] = portable_part_step_text(spec.get("step_path", ""))
    return out


def portable_part_step_text(value: Any) -> str:
    """The part STEP path as stored: project-relative when inside the project."""
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "null"}:
        return ""
    path = Path(text).expanduser()
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve(strict=False).relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return str(path)


def resolve_part_step_path(spec: dict[str, Any]) -> Path | None:
    """Absolute path of the part STEP, or None when the part is the plain box."""
    text = str((spec or {}).get("step_path", "") or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path if path.exists() else None


def part_frame(spec: dict[str, Any], object_point, object_axis) -> tuple[np.ndarray, np.ndarray]:
    """(R, centre): world = R @ local + centre for the part's own frame (local x = W,
    y = H, z = D, front = +z), given the ACTIVE face's pose on the object plane."""
    spec = normalize_inspection_part_spec(spec)
    active = spec["active_face"]
    O = np.asarray(object_point, dtype=float).reshape(3)
    a = _unit(object_axis)
    u, v = plane_basis(a)
    d_active = _FACE_DEFS[active]
    local = np.column_stack([d_active["p"], d_active["q"], d_active["n"]]).astype(float)
    world = np.column_stack([u, v, a])
    R = world @ local.T
    half = {"width": 0.5 * spec["width_mm"], "height": 0.5 * spec["height_mm"], "depth": 0.5 * spec["depth_mm"]}
    center = O - a * half[d_active["extent"]]
    return R, center


def step_bounds_dims(mesh) -> tuple[float, float, float] | None:
    """(W, H, D) from a part mesh's native bounding box (x, y, z extents)."""
    try:
        pts = np.asarray(mesh.points, dtype=float)
    except Exception:
        return None
    if pts.ndim != 2 or pts.shape[0] == 0:
        return None
    ext = pts.max(axis=0) - pts.min(axis=0)
    if not np.all(np.isfinite(ext)) or np.any(ext <= 1e-9):
        return None
    return float(ext[0]), float(ext[1]), float(ext[2])


def apply_step_bounds(spec: dict[str, Any], mesh) -> dict[str, Any]:
    """Size the part from its STEP mesh (native AABB); the spec is returned normalized."""
    out = normalize_inspection_part_spec(spec)
    dims = step_bounds_dims(mesh)
    if dims is not None:
        out["width_mm"], out["height_mm"], out["depth_mm"] = (round(v, 4) for v in dims)
    return out


def part_mesh_world(mesh, spec: dict[str, Any], object_point, object_axis):
    """A copy of the part mesh placed in the world: native AABB centre -> the part
    centre, native axes -> the part frame (so the STEP's +z face is the Front face)."""
    R, center = part_frame(spec, object_point, object_axis)
    out = mesh.copy(deep=True)
    pts = np.asarray(out.points, dtype=float)
    c0 = 0.5 * (pts.min(axis=0) + pts.max(axis=0))
    out.points = (R @ (pts - c0).T).T + center
    return out


def face_dims(spec: dict[str, Any], face: str) -> tuple[float, float]:
    """(width, height) the given face presents, in mm."""
    d = _FACE_DEFS[face]
    return float(spec[d["dims"][0] + "_mm"]), float(spec[d["dims"][1] + "_mm"])


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float).reshape(3)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.array([0.0, 0.0, 1.0])


def plane_basis(axis) -> tuple[np.ndarray, np.ndarray]:
    """In-plane (u, v) for a plane normal: u = world-horizontal (width), v = up-ish
    (height), so a W x H face reads landscape in a y-up view."""
    a = _unit(axis)
    up = np.array([0.0, 1.0, 0.0]) if abs(a[1]) < 0.9 else np.array([0.0, 0.0, 1.0])
    u = np.cross(up, a)
    nu = float(np.linalg.norm(u))
    u = u / nu if nu > 1e-9 else np.array([1.0, 0.0, 0.0])
    v = np.cross(a, u)
    return u, v


def face_frames(spec: dict[str, Any], object_point, object_axis) -> dict[str, dict[str, Any]]:
    """World frames of all six faces given the ACTIVE face's pose.

    ``object_point`` is the object-plane centre; ``object_axis`` the outward direction of
    that plane (object -> lens). The active face is placed there; the rest follow by the
    box's rigid frame. Returns face -> {center, normal, u, v, width, height}.
    """
    spec = normalize_inspection_part_spec(spec)
    active = spec["active_face"]
    O = np.asarray(object_point, dtype=float).reshape(3)
    a = _unit(object_axis)
    u, v = plane_basis(a)
    # world = R @ local, with R mapping the active face's (p, q, n) onto (u, v, a)
    d_active = _FACE_DEFS[active]
    local = np.column_stack([d_active["p"], d_active["q"], d_active["n"]]).astype(float)
    world = np.column_stack([u, v, a])
    R = world @ local.T
    half = {
        "width": 0.5 * spec["width_mm"],
        "height": 0.5 * spec["height_mm"],
        "depth": 0.5 * spec["depth_mm"],
    }
    center = O - a * half[d_active["extent"]]
    frames: dict[str, dict[str, Any]] = {}
    for face, d in _FACE_DEFS.items():
        n_w = R @ np.asarray(d["n"], dtype=float)
        p_w = R @ np.asarray(d["p"], dtype=float)
        q_w = R @ np.asarray(d["q"], dtype=float)
        w, h = face_dims(spec, face)
        frames[face] = {
            "center": center + n_w * half[d["extent"]],
            "normal": n_w,
            "u": p_w,
            "v": q_w,
            "width": w,
            "height": h,
            "active": face == active,
        }
    return frames


def box_corners(spec: dict[str, Any], object_point, object_axis) -> np.ndarray:
    """The eight world corners of the part box."""
    frames = face_frames(spec, object_point, object_axis)
    f = frames["front"]
    r = frames["right"]
    t = frames["top"]
    spec = normalize_inspection_part_spec(spec)
    # box centre = front centre - depth/2 along its normal
    center = f["center"] - f["normal"] * 0.5 * spec["depth_mm"]
    ex = r["normal"] * 0.5 * spec["width_mm"]
    ey = t["normal"] * 0.5 * spec["height_mm"]
    ez = f["normal"] * 0.5 * spec["depth_mm"]
    corners = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                corners.append(center + sx * ex + sy * ey + sz * ez)
    return np.asarray(corners, dtype=float)


def axis_reach(spec: dict[str, Any]) -> float:
    spec = normalize_inspection_part_spec(spec)
    reach = float(spec["axis_reach_mm"])
    if reach <= 1e-6:
        reach = max(80.0, 2.5 * max(spec["width_mm"], spec["height_mm"], spec["depth_mm"]))
    return reach


def axis_records(spec: dict[str, Any], object_point, object_axis) -> list[dict[str, Any]]:
    """The six blow-out axes as optical-axis records (dotted guides, pickable)."""
    frames = face_frames(spec, object_point, object_axis)
    reach = axis_reach(spec)
    records = []
    for face in FACE_ORDER:
        fr = frames[face]
        far = fr["center"] + fr["normal"] * reach
        records.append(
            {
                "axis_id": f"axis:part:{face}",
                "axis_label": f"Face {face.capitalize()} axis",
                "axis_kind": "inspection_part_face",
                "branch_path": "",
                "source_id": "",
                "ray_index": -1,
                "face": face,
                "active": bool(fr["active"]),
                "points": np.asarray((fr["center"], far), dtype=float),
            }
        )
    return records


# ---------------------------------------------------------------------------------
# Tk dialog
# ---------------------------------------------------------------------------------
def open_inspection_part_dialog(editor):
    """Modeless dialog: enable the part, size it, pick the inspected face, solve the
    FOV to that face."""
    import tkinter as tk
    from tkinter import ttk

    parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
    dialog = tk.Toplevel(parent)
    dialog.title("Inspection Part (3D object)")
    try:
        dialog.transient(parent)
    except Exception:
        pass
    spec = normalize_inspection_part_spec(getattr(editor, "inspection_part_spec", None))
    enabled_var = tk.BooleanVar(value=bool(spec["enabled"]))
    w_var = tk.StringVar(value=f"{spec['width_mm']:g}")
    h_var = tk.StringVar(value=f"{spec['height_mm']:g}")
    d_var = tk.StringVar(value=f"{spec['depth_mm']:g}")
    reach_var = tk.StringVar(value=f"{spec['axis_reach_mm']:g}")
    face_var = tk.StringVar(value=spec["active_face"])
    step_var = tk.StringVar(value=str(spec.get("step_path", "") or ""))
    status_var = tk.StringVar(value="")

    body = ttk.Frame(dialog, padding=12)
    body.grid(row=0, column=0, sticky="nsew")
    ttk.Checkbutton(body, text="Show the 3D part at the object plane", variable=enabled_var).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )
    for r, (label, var) in enumerate(
        (("Width W (mm)", w_var), ("Height H (mm)", h_var), ("Depth D (mm)", d_var),
         ("Axis reach (mm, 0 = auto)", reach_var)),
        start=1,
    ):
        ttk.Label(body, text=label).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(body, textvariable=var, width=12).grid(row=r, column=1, sticky="w", pady=2)
    # bugs/0666: the real part's STEP -- bounds size the box, the mesh replaces it.
    ttk.Label(body, text="Part STEP (optional)").grid(row=9, column=0, sticky="w", pady=(6, 2))
    step_row = ttk.Frame(body)
    step_row.grid(row=9, column=1, sticky="w", pady=(6, 2))
    ttk.Entry(step_row, textvariable=step_var, width=34).grid(row=0, column=0)

    def _browse_step():
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Part STEP", filetypes=[("STEP", "*.step *.stp *.STEP *.STP"), ("All files", "*")], parent=dialog,
        )
        if not path:
            return
        step_var.set(path)
        try:
            mesh = editor._load_step_mesh(Path(path), largest_component=False)
            sized = apply_step_bounds({"width_mm": w_var.get(), "height_mm": h_var.get(), "depth_mm": d_var.get()}, mesh)
            w_var.set(f"{sized['width_mm']:g}"); h_var.set(f"{sized['height_mm']:g}"); d_var.set(f"{sized['depth_mm']:g}")
            enabled_var.set(True)
            status_var.set(f"Dims from the STEP bounds: {sized['width_mm']:g} x {sized['height_mm']:g} x {sized['depth_mm']:g} mm (x=W, y=H, z=D; +z = Front)")
        except Exception as exc:
            status_var.set(f"Part STEP set, but its bounds could not be read: {exc}")

    ttk.Button(step_row, text="Browse...", command=_browse_step).grid(row=0, column=1, padx=(4, 0))
    ttk.Label(body, text="Inspected face (on the object plane)").grid(row=5, column=0, sticky="w", pady=(8, 2))
    ttk.Combobox(body, textvariable=face_var, values=list(FACE_ORDER), state="readonly", width=10).grid(
        row=5, column=1, sticky="w", pady=(8, 2)
    )
    ttk.Label(
        body,
        text="Front/Back show W x H, Left/Right show D x H, Top/Bottom show W x D.\n"
             "Each face gets a dashed blow-out axis for its own camera station.",
        justify="left",
    ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 8))

    def _read() -> dict[str, Any]:
        raw = {
            "enabled": bool(enabled_var.get()),
            "width_mm": w_var.get(),
            "height_mm": h_var.get(),
            "depth_mm": d_var.get(),
            "axis_reach_mm": reach_var.get(),
            "active_face": face_var.get(),
            "step_path": step_var.get(),
        }
        return normalize_inspection_part_spec(raw)

    def _apply():
        editor.set_inspection_part_spec(_read())
        w, h = face_dims(editor.inspection_part_spec, editor.inspection_part_spec["active_face"])
        status_var.set(f"Applied. Inspected face {face_var.get()}: {w:g} x {h:g} mm.")

    def _solve():
        editor.set_inspection_part_spec(_read())
        ok, msg = editor.solve_fov_to_inspection_face()
        status_var.set(msg)

    buttons = ttk.Frame(body)
    buttons.grid(row=7, column=0, columnspan=2, sticky="w")
    ttk.Button(buttons, text="Apply", command=_apply).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(buttons, text="Apply + Solve FOV to this face", command=_solve).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(buttons, text="Close", command=dialog.destroy).grid(row=0, column=2)
    ttk.Label(body, textvariable=status_var, wraplength=420, justify="left").grid(
        row=8, column=0, columnspan=2, sticky="w", pady=(8, 0)
    )
    try:
        editor._show_centered_dialog(dialog)
    except Exception:
        pass
    return dialog
