from __future__ import annotations

import numpy as np


OPTICAL_SOLID_FACES_ADVANCED_ATTR = "OpticalSolidFaces"
OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER = "Beam Splitter"
OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y = "Left + Up (reflect +Y)"
OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_NEG_Y = "Left + Down (reflect -Y)"
OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES = (
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_NEG_Y,
)
OPTICAL_SOLID_FACE_ROLE_DEFAULT = "Unassigned"
OPTICAL_SOLID_FACE_ROLE_VALUES = (
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    "Input",
    "Output",
    "TIR",
    "Mirror",
    "Beam Splitter",
    "Absorber/Mechanical",
)
OPTICAL_SOLID_FACE_SIDE_DEFAULT = "Auto"
OPTICAL_SOLID_FACE_SIDE_VALUES = (
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    "Left",
    "Right",
    "Up",
    "Down",
    "Front",
    "Back",
)
OPTICAL_SOLID_FACE_FUNCTION_DEFAULT = OPTICAL_SOLID_FACE_ROLE_DEFAULT
OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT = "Transmit/Port"
OPTICAL_SOLID_FACE_FUNCTION_VALUES = (
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    "Mirror",
    "TIR",
    "Beam Splitter",
    "Absorber/Mechanical",
)
OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT = "Auto side labels"
OPTICAL_SOLID_FACE_FIT_ROLL_NONE = "No roll constraint"
OPTICAL_SOLID_FACE_FIT_ROLL_VALUES = (
    OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
    OPTICAL_SOLID_FACE_FIT_ROLL_NONE,
)
OPTICAL_SOLID_FACE_ROLE_COLORS = {
    OPTICAL_SOLID_FACE_ROLE_DEFAULT: (0.42, 0.45, 0.50),
    "Input": (0.08, 0.62, 0.24),
    "Output": (0.08, 0.36, 0.88),
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT: (0.08, 0.36, 0.88),
    "TIR": (0.95, 0.55, 0.12),
    "Mirror": (0.66, 0.70, 0.76),
    "Beam Splitter": (0.88, 0.18, 0.22),
    "Absorber/Mechanical": (0.12, 0.14, 0.18),
}
OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES = (OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER,)
OPTICAL_SOLID_VIRTUAL_PLANE_KIND_COLORS = {
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER: (0.88, 0.18, 0.22),
}


def normalize_optical_solid_face_side(value: object) -> str:
    side = str(value or OPTICAL_SOLID_FACE_SIDE_DEFAULT).strip()
    return side if side in OPTICAL_SOLID_FACE_SIDE_VALUES else OPTICAL_SOLID_FACE_SIDE_DEFAULT


def normalize_optical_solid_face_function(value: object, *, legacy_role: object = None) -> str:
    function = str(value or "").strip()
    if function in OPTICAL_SOLID_FACE_FUNCTION_VALUES:
        return function
    role = str(legacy_role or "").strip()
    if role in {"Input", "Output"}:
        return OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
    if role in {"Mirror", "TIR", "Beam Splitter", "Absorber/Mechanical"}:
        return role
    return OPTICAL_SOLID_FACE_FUNCTION_DEFAULT


def legacy_role_from_optical_solid_face_function(function: object) -> str:
    normalized = normalize_optical_solid_face_function(function)
    if normalized == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT:
        return "Output"
    return normalized


def normalize_optical_solid_virtual_plane_kind(value: object) -> str:
    kind = str(value or OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER).strip()
    return kind if kind in OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES else OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER


def normalize_optical_solid_virtual_plane_diagonal(value: object) -> str:
    diagonal = str(value or OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y).strip()
    return (
        diagonal
        if diagonal in OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES
        else OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y
    )


def optical_solid_virtual_plane_color(kind: object) -> tuple[float, float, float]:
    return OPTICAL_SOLID_VIRTUAL_PLANE_KIND_COLORS.get(
        normalize_optical_solid_virtual_plane_kind(kind),
        OPTICAL_SOLID_VIRTUAL_PLANE_KIND_COLORS[OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER],
    )


def optical_solid_face_marker_label(face: dict[str, object]) -> str:
    side = normalize_optical_solid_face_side(face.get("side_2d"))
    function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
    if side != OPTICAL_SOLID_FACE_SIDE_DEFAULT and function != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
        return f"{side} {function}"
    if side != OPTICAL_SOLID_FACE_SIDE_DEFAULT:
        return side
    return function


def optical_solid_face_role_color(role: object) -> tuple[float, float, float]:
    role_text = str(role or OPTICAL_SOLID_FACE_ROLE_DEFAULT).strip()
    return OPTICAL_SOLID_FACE_ROLE_COLORS.get(role_text, OPTICAL_SOLID_FACE_ROLE_COLORS[OPTICAL_SOLID_FACE_ROLE_DEFAULT])


def float_or_default(value, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return float(default)
    return parsed if np.isfinite(parsed) else float(default)


def unit_vector_tuple(value) -> tuple[float, float, float]:
    try:
        arr = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        arr = np.asarray([0.0, 0.0, 1.0], dtype=float)
    if arr.size < 3:
        arr = np.pad(arr, (0, 3 - arr.size), mode="constant")
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12 or not np.isfinite(norm):
        arr = np.asarray([0.0, 0.0, 1.0], dtype=float)
    else:
        arr = arr / norm
    return tuple(float(v) for v in arr[:3])


def point3_tuple(value) -> tuple[float, float, float]:
    try:
        arr = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        arr = np.zeros(3, dtype=float)
    if arr.size < 3:
        arr = np.pad(arr, (0, 3 - arr.size), mode="constant")
    arr = np.where(np.isfinite(arr), arr, 0.0)
    return tuple(float(v) for v in arr[:3])


def optical_solid_face_record_from_candidate(candidate) -> dict[str, object]:
    return {
        "face_id": candidate.face_id,
        "role": OPTICAL_SOLID_FACE_ROLE_DEFAULT,
        "function": OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
        "side_2d": OPTICAL_SOLID_FACE_SIDE_DEFAULT,
        "normal": list(candidate.normal),
        "centroid": list(candidate.centroid),
        "area_mm2": float(candidate.area_mm2),
        "triangle_count": int(candidate.triangle_count),
        "plane_offset_mm": float(candidate.plane_offset_mm),
        "flip_normal": False,
        "material": "",
        "coating": "",
        "split_ratio": 0.5,
        "loss": 0.0,
        "phase_deg": 0.0,
        "clear_aperture_mm": 0.0,
        "notes": "",
    }


def normalize_optical_solid_face_record(record: dict[str, object]) -> dict[str, object]:
    role = str(record.get("role", OPTICAL_SOLID_FACE_ROLE_DEFAULT) or OPTICAL_SOLID_FACE_ROLE_DEFAULT).strip()
    if role not in OPTICAL_SOLID_FACE_ROLE_VALUES:
        role = OPTICAL_SOLID_FACE_ROLE_DEFAULT
    function = normalize_optical_solid_face_function(record.get("function"), legacy_role=role)
    role = legacy_role_from_optical_solid_face_function(function)
    return {
        "face_id": str(record.get("face_id", "") or "").strip(),
        "role": role,
        "function": function,
        "side_2d": normalize_optical_solid_face_side(record.get("side_2d", record.get("side"))),
        "normal": list(unit_vector_tuple(record.get("normal", (0.0, 0.0, 1.0)))),
        "centroid": list(point3_tuple(record.get("centroid", (0.0, 0.0, 0.0)))),
        "area_mm2": max(float_or_default(record.get("area_mm2"), 0.0), 0.0),
        "triangle_count": max(int(round(float_or_default(record.get("triangle_count"), 0.0))), 0),
        "plane_offset_mm": float_or_default(record.get("plane_offset_mm"), 0.0),
        "flip_normal": bool(record.get("flip_normal", False)),
        "material": str(record.get("material", "") or "").strip(),
        "coating": str(record.get("coating", "") or "").strip(),
        "split_ratio": float(np.clip(float_or_default(record.get("split_ratio"), 0.5), 0.0, 1.0)),
        "loss": float(np.clip(float_or_default(record.get("loss"), 0.0), 0.0, 1.0)),
        "phase_deg": float_or_default(record.get("phase_deg"), 0.0),
        "clear_aperture_mm": max(float_or_default(record.get("clear_aperture_mm"), 0.0), 0.0),
        "notes": str(record.get("notes", "") or "").strip(),
    }


def normalize_optical_solid_virtual_plane_record(record: dict[str, object]) -> dict[str, object]:
    return {
        "plane_id": str(record.get("plane_id", "") or "").strip() or "VP001",
        "kind": normalize_optical_solid_virtual_plane_kind(record.get("kind")),
        "diagonal_mode": normalize_optical_solid_virtual_plane_diagonal(record.get("diagonal_mode")),
        "point": list(point3_tuple(record.get("point", (0.0, 0.0, 0.0)))),
        "normal": list(unit_vector_tuple(record.get("normal", (0.0, 0.0, 1.0)))),
        "aperture_mm": max(float_or_default(record.get("aperture_mm"), 0.0), 0.0),
        "split_ratio": float(np.clip(float_or_default(record.get("split_ratio"), 0.5), 0.0, 1.0)),
        "loss": float(np.clip(float_or_default(record.get("loss"), 0.0), 0.0, 1.0)),
        "phase_deg": float_or_default(record.get("phase_deg"), 0.0),
        "source_sides": [
            normalize_optical_solid_face_side(item)
            for item in list(record.get("source_sides", []) or [])
            if normalize_optical_solid_face_side(item) != OPTICAL_SOLID_FACE_SIDE_DEFAULT
        ],
        "source_faces": [str(item or "").strip() for item in list(record.get("source_faces", []) or []) if str(item or "").strip()],
        "notes": str(record.get("notes", "") or "").strip(),
    }


def normalize_optical_solid_face_metadata(
    value,
    candidates: list[object] | None = None,
    *,
    source_stl: str = "",
) -> dict[str, object]:
    raw_faces = []
    raw_virtual_planes = []
    if isinstance(value, dict):
        raw_faces = list(value.get("faces", []) or [])
        raw_virtual_planes = list(value.get("virtual_planes", []) or [])
    elif isinstance(value, (list, tuple)):
        raw_faces = list(value)
    by_id: dict[str, dict[str, object]] = {}
    for item in raw_faces:
        if not isinstance(item, dict):
            continue
        normalized = normalize_optical_solid_face_record(item)
        if normalized["face_id"]:
            by_id[str(normalized["face_id"])] = normalized
    output_faces: list[dict[str, object]] = []
    if candidates:
        for candidate in candidates:
            base = optical_solid_face_record_from_candidate(candidate)
            existing = by_id.get(candidate.face_id)
            if existing is not None:
                base.update(
                    {
                        key: existing[key]
                        for key in (
                            "role",
                            "function",
                            "side_2d",
                            "flip_normal",
                            "material",
                            "coating",
                            "split_ratio",
                            "loss",
                            "phase_deg",
                            "clear_aperture_mm",
                            "notes",
                        )
                        if key in existing
                    }
                )
            output_faces.append(normalize_optical_solid_face_record(base))
    else:
        output_faces = list(by_id.values())
    output_virtual_planes: list[dict[str, object]] = []
    for item in raw_virtual_planes:
        if not isinstance(item, dict):
            continue
        output_virtual_planes.append(normalize_optical_solid_virtual_plane_record(item))
    return {
        "version": 1,
        "source_stl": str(source_stl or (value.get("source_stl", "") if isinstance(value, dict) else "")),
        "faces": output_faces,
        "virtual_planes": output_virtual_planes,
    }


def auto_assign_optical_solid_face_roles(records: list[dict[str, object]]) -> list[dict[str, object]]:
    output = [normalize_optical_solid_face_record(record) for record in records]
    for record in output:
        record["role"] = OPTICAL_SOLID_FACE_ROLE_DEFAULT
        record["function"] = OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
        record["side_2d"] = OPTICAL_SOLID_FACE_SIDE_DEFAULT
    if not output:
        return output
    centroids = np.asarray([point3_tuple(record.get("centroid", (0.0, 0.0, 0.0))) for record in output], dtype=float)
    axis_sides = (
        (2, float(np.min(centroids[:, 2])), "Left"),
        (2, float(np.max(centroids[:, 2])), "Right"),
        (1, float(np.max(centroids[:, 1])), "Up"),
        (1, float(np.min(centroids[:, 1])), "Down"),
        (0, float(np.min(centroids[:, 0])), "Front"),
        (0, float(np.max(centroids[:, 0])), "Back"),
    )
    used: set[int] = set()
    for axis, target, side in axis_sides:
        scores = [
            (abs(float(centroids[index, axis]) - target), -float(output[index].get("area_mm2", 0.0) or 0.0), index)
            for index in range(len(output))
            if index not in used
        ]
        if not scores:
            continue
        _distance, _area_score, index = min(scores)
        output[index]["side_2d"] = side
        used.add(index)
    return output


def optical_solid_face_by_side(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    side: str,
) -> dict[str, object] | None:
    target = normalize_optical_solid_face_side(side)
    if target == OPTICAL_SOLID_FACE_SIDE_DEFAULT:
        return None
    candidates = [
        normalize_optical_solid_face_record(face)
        for face in list(normalize_optical_solid_face_metadata(metadata).get("faces", []) or [])
        if isinstance(face, dict) and normalize_optical_solid_face_side(face.get("side_2d")) == target
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0))


def optical_solid_virtual_plane_center_from_faces(faces: list[dict[str, object]]) -> np.ndarray:
    centers: list[np.ndarray] = []
    for lhs, rhs in (("Left", "Right"), ("Up", "Down"), ("Front", "Back")):
        left = next((face for face in faces if normalize_optical_solid_face_side(face.get("side_2d")) == lhs), None)
        right = next((face for face in faces if normalize_optical_solid_face_side(face.get("side_2d")) == rhs), None)
        if left is not None and right is not None:
            centers.append(
                0.5
                * (
                    np.asarray(point3_tuple(left.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                    + np.asarray(point3_tuple(right.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                )
            )
    if centers:
        return np.nanmean(np.vstack(centers), axis=0)
    if faces:
        return np.nanmean(
            np.vstack([np.asarray(point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float) for face in faces]),
            axis=0,
        )
    return np.zeros(3, dtype=float)


def build_optical_solid_cube_splitter_virtual_plane(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    diagonal_mode: str = OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    split_ratio: float = 0.5,
    loss: float = 0.0,
    phase_deg: float = 0.0,
    aperture_mm: float = 0.0,
    notes: str = "",
    plane_id: str = "VP001",
) -> dict[str, object]:
    normalized = normalize_optical_solid_face_metadata(metadata)
    faces = [normalize_optical_solid_face_record(face) for face in list(normalized.get("faces", []) or []) if isinstance(face, dict)]
    side_map = {
        side: optical_solid_face_by_side(normalized, side)
        for side in ("Left", "Right", "Up", "Down", "Front", "Back")
    }
    required = ("Left", "Right", "Up", "Down")
    missing = [side for side in required if side_map.get(side) is None]
    if missing:
        raise ValueError(
            "Cube splitter virtual plane needs labeled Left/Right/Up/Down faces first; missing: "
            + ", ".join(missing)
        )
    diagonal = normalize_optical_solid_virtual_plane_diagonal(diagonal_mode)
    pair = ("Left", "Up") if diagonal == OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y else ("Left", "Down")
    pair_faces = [side_map[pair[0]], side_map[pair[1]]]
    normal = np.zeros(3, dtype=float)
    source_faces: list[str] = []
    for face in pair_faces:
        if face is None:
            continue
        normal += np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
        source_faces.append(str(face.get("face_id", "") or "").strip())
    norm = float(np.linalg.norm(normal))
    if norm <= 1e-12 or not np.isfinite(norm):
        raise ValueError("Could not derive a finite cube splitter plane normal from the labeled faces.")
    normal = normal / norm
    center = optical_solid_virtual_plane_center_from_faces([face for face in side_map.values() if isinstance(face, dict)])
    if aperture_mm <= 0.0:
        left = side_map["Left"]
        right = side_map["Right"]
        up = side_map["Up"]
        down = side_map["Down"]
        yz_span = min(
            float(
                np.linalg.norm(
                    np.asarray(point3_tuple(right.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                    - np.asarray(point3_tuple(left.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                )
            )
            if left is not None and right is not None
            else 0.0,
            float(
                np.linalg.norm(
                    np.asarray(point3_tuple(up.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                    - np.asarray(point3_tuple(down.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
                )
            )
            if up is not None and down is not None
            else 0.0,
        )
        aperture_mm = max(yz_span * np.sqrt(2.0), 1e-6)
    return normalize_optical_solid_virtual_plane_record(
        {
            "plane_id": plane_id,
            "kind": OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER,
            "diagonal_mode": diagonal,
            "point": list(center[:3]),
            "normal": list(normal[:3]),
            "aperture_mm": aperture_mm,
            "split_ratio": split_ratio,
            "loss": loss,
            "phase_deg": phase_deg,
            "source_sides": list(pair),
            "source_faces": source_faces,
            "notes": notes,
        }
    )


def optical_solid_has_virtual_splitter_plane(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...]
) -> bool:
    normalized = normalize_optical_solid_face_metadata(metadata)
    return any(
        normalize_optical_solid_virtual_plane_kind(plane.get("kind")) == OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER
        for plane in list(normalized.get("virtual_planes", []) or [])
        if isinstance(plane, dict)
    )


def optical_solid_faces_summary_text(
    row_index: int,
    row_name: str,
    row_surface: str,
    metadata: dict[str, object],
) -> str:
    normalized = normalize_optical_solid_face_metadata(metadata)
    faces = list(normalized.get("faces", []) or [])
    virtual_planes = [
        normalize_optical_solid_virtual_plane_record(plane)
        for plane in list(normalized.get("virtual_planes", []) or [])
        if isinstance(plane, dict)
    ]
    assigned = [
        face
        for face in faces
        if normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
        or normalize_optical_solid_face_side(face.get("side_2d")) != OPTICAL_SOLID_FACE_SIDE_DEFAULT
    ]
    lines = [f"S{row_index}: {row_name or row_surface}", f"Assigned optical faces: {len(assigned)}/{len(faces)}"]
    for face in assigned:
        lines.append(
            "{face_id}: side={side}, function={function}, normal=({nx:.4g},{ny:.4g},{nz:.4g}), centroid=({cx:.4g},{cy:.4g},{cz:.4g}), split={split:.4g}".format(
                face_id=face.get("face_id", ""),
                side=normalize_optical_solid_face_side(face.get("side_2d")),
                function=normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role")),
                nx=float(face.get("normal", [0, 0, 1])[0]),
                ny=float(face.get("normal", [0, 0, 1])[1]),
                nz=float(face.get("normal", [0, 0, 1])[2]),
                cx=float(face.get("centroid", [0, 0, 0])[0]),
                cy=float(face.get("centroid", [0, 0, 0])[1]),
                cz=float(face.get("centroid", [0, 0, 0])[2]),
                split=float(face.get("split_ratio", 0.5)),
            )
        )
    lines.append(f"Virtual internal planes: {len(virtual_planes)}")
    for plane in virtual_planes:
        lines.append(
            "{plane_id}: kind={kind}, diagonal={diagonal}, point=({px:.4g},{py:.4g},{pz:.4g}), normal=({nx:.4g},{ny:.4g},{nz:.4g}), aperture={aperture:.4g}, split={split:.4g}".format(
                plane_id=plane.get("plane_id", ""),
                kind=normalize_optical_solid_virtual_plane_kind(plane.get("kind")),
                diagonal=normalize_optical_solid_virtual_plane_diagonal(plane.get("diagonal_mode")),
                px=float(plane.get("point", [0, 0, 0])[0]),
                py=float(plane.get("point", [0, 0, 0])[1]),
                pz=float(plane.get("point", [0, 0, 0])[2]),
                nx=float(plane.get("normal", [0, 0, 1])[0]),
                ny=float(plane.get("normal", [0, 0, 1])[1]),
                nz=float(plane.get("normal", [0, 0, 1])[2]),
                aperture=float(plane.get("aperture_mm", 0.0)),
                split=float(plane.get("split_ratio", 0.5)),
            )
        )
    return "\n".join(lines)
