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
OPTICAL_SOLID_FACE_PORT_DEFAULT = "Auto"
OPTICAL_SOLID_FACE_PORT_INPUT = "Input Port"
OPTICAL_SOLID_FACE_PORT_OUTPUT = "Output Port"
OPTICAL_SOLID_FACE_PORT_INTERACTION = "Interaction Surface"
OPTICAL_SOLID_FACE_PORT_VALUES = (
    OPTICAL_SOLID_FACE_PORT_DEFAULT,
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
)
OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT = "Auto side labels"
OPTICAL_SOLID_FACE_FIT_ROLL_NONE = "No roll constraint"
OPTICAL_SOLID_FACE_FIT_ROLL_VALUES = (
    OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
    OPTICAL_SOLID_FACE_FIT_ROLL_NONE,
)
OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT = "Auto"
OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES = (
    OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT,
    "+Y normal",
    "-Y normal",
    "+Z normal",
    "-Z normal",
    "+X normal",
    "-X normal",
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


def normalize_optical_solid_face_port_role(value: object) -> str:
    role = str(value or OPTICAL_SOLID_FACE_PORT_DEFAULT).strip()
    return role if role in OPTICAL_SOLID_FACE_PORT_VALUES else OPTICAL_SOLID_FACE_PORT_DEFAULT


def normalize_optical_solid_face_fit_reference(value: object) -> str:
    reference = str(value or OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT).strip()
    return reference if reference in OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES else OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT


def optical_solid_face_fit_reference_axis(value: object) -> np.ndarray | None:
    reference = normalize_optical_solid_face_fit_reference(value)
    axes = {
        "+Y normal": np.asarray((0.0, 1.0, 0.0), dtype=float),
        "-Y normal": np.asarray((0.0, -1.0, 0.0), dtype=float),
        "+Z normal": np.asarray((0.0, 0.0, 1.0), dtype=float),
        "-Z normal": np.asarray((0.0, 0.0, -1.0), dtype=float),
        "+X normal": np.asarray((1.0, 0.0, 0.0), dtype=float),
        "-X normal": np.asarray((-1.0, 0.0, 0.0), dtype=float),
    }
    return axes.get(reference)


def infer_optical_solid_face_port_role(
    *,
    function: object,
    side: object,
    legacy_role: object = None,
) -> str:
    normalized_function = normalize_optical_solid_face_function(function, legacy_role=legacy_role)
    normalized_side = normalize_optical_solid_face_side(side)
    if normalized_function == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT:
        return OPTICAL_SOLID_FACE_PORT_INPUT if normalized_side == "Left" else OPTICAL_SOLID_FACE_PORT_OUTPUT
    legacy = str(legacy_role or "").strip()
    if legacy == "Input":
        return OPTICAL_SOLID_FACE_PORT_INPUT
    if legacy == "Output" and normalized_side == OPTICAL_SOLID_FACE_SIDE_DEFAULT:
        return OPTICAL_SOLID_FACE_PORT_OUTPUT
    if normalized_function in {"Mirror", "TIR", "Beam Splitter", "Absorber/Mechanical"}:
        return OPTICAL_SOLID_FACE_PORT_INTERACTION
    return OPTICAL_SOLID_FACE_PORT_DEFAULT


def optical_solid_face_port_role(face: dict[str, object]) -> str:
    explicit = normalize_optical_solid_face_port_role(face.get("port_role", face.get("port")))
    if explicit != OPTICAL_SOLID_FACE_PORT_DEFAULT:
        return explicit
    return infer_optical_solid_face_port_role(
        function=face.get("function"),
        side=face.get("side_2d", face.get("side")),
        legacy_role=face.get("role"),
    )


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
    port_role = optical_solid_face_port_role(face)
    port_text = "" if port_role == OPTICAL_SOLID_FACE_PORT_DEFAULT else port_role.replace(" Port", "").replace(" Surface", "")
    if side != OPTICAL_SOLID_FACE_SIDE_DEFAULT and function != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
        label = f"{side} {function}"
        return f"{label} [{port_text}]" if port_text else label
    if side != OPTICAL_SOLID_FACE_SIDE_DEFAULT:
        return f"{side} [{port_text}]" if port_text else side
    if function != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
        return f"{function} [{port_text}]" if port_text else function
    return port_text or function


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
        "port_role": OPTICAL_SOLID_FACE_PORT_DEFAULT,
        "fit_reference": OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT,
        "flip_normal": False,
        "material": "",
        "coating": "",
        "split_ratio": 0.5,
        "loss": 0.0,
        "phase_deg": 0.0,
        "clear_aperture_mm": 0.0,
        "input_offset_u_mm": 0.0,
        "input_offset_v_mm": 0.0,
        "notes": "",
    }


def normalize_optical_solid_face_record(record: dict[str, object]) -> dict[str, object]:
    role = str(record.get("role", OPTICAL_SOLID_FACE_ROLE_DEFAULT) or OPTICAL_SOLID_FACE_ROLE_DEFAULT).strip()
    if role not in OPTICAL_SOLID_FACE_ROLE_VALUES:
        role = OPTICAL_SOLID_FACE_ROLE_DEFAULT
    function = normalize_optical_solid_face_function(record.get("function"), legacy_role=role)
    side = normalize_optical_solid_face_side(record.get("side_2d", record.get("side")))
    port_role = normalize_optical_solid_face_port_role(record.get("port_role", record.get("port")))
    fit_reference = normalize_optical_solid_face_fit_reference(record.get("fit_reference", record.get("reference_axis")))
    if port_role == OPTICAL_SOLID_FACE_PORT_DEFAULT:
        port_role = infer_optical_solid_face_port_role(function=function, side=side, legacy_role=role)
    role = legacy_role_from_optical_solid_face_function(function)
    return {
        "face_id": str(record.get("face_id", "") or "").strip(),
        "role": role,
        "function": function,
        "side_2d": side,
        "port_role": port_role,
        "fit_reference": fit_reference,
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
        "input_offset_u_mm": float_or_default(
            record.get("input_offset_u_mm", record.get("input_snap_u_mm")),
            0.0,
        ),
        "input_offset_v_mm": float_or_default(
            record.get("input_offset_v_mm", record.get("input_snap_v_mm")),
            0.0,
        ),
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
                            "port_role",
                            "fit_reference",
                            "flip_normal",
                            "material",
                            "coating",
                            "split_ratio",
                            "loss",
                            "phase_deg",
                            "clear_aperture_mm",
                            "input_offset_u_mm",
                            "input_offset_v_mm",
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


def optical_solid_face_by_port_role(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    port_role: str,
) -> dict[str, object] | None:
    target = normalize_optical_solid_face_port_role(port_role)
    if target == OPTICAL_SOLID_FACE_PORT_DEFAULT:
        return None
    candidates = [
        normalize_optical_solid_face_record(face)
        for face in list(normalize_optical_solid_face_metadata(metadata).get("faces", []) or [])
        if isinstance(face, dict) and optical_solid_face_port_role(face) == target
    ]
    if not candidates:
        return None
    return max(candidates, key=optical_solid_face_fit_priority)


def optical_solid_input_anchor_face(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
) -> dict[str, object] | None:
    input_face = optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT)
    if input_face is not None:
        return input_face
    left_face = optical_solid_face_by_side(metadata, "Left")
    if left_face is not None:
        return left_face
    return select_optical_solid_anchor_face(metadata)


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
        or normalize_optical_solid_face_fit_reference(face.get("fit_reference")) != OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT
    ]
    lines = [f"S{row_index}: {row_name or row_surface}", f"Assigned optical faces: {len(assigned)}/{len(faces)}"]
    for face in assigned:
        snap_u, snap_v = optical_solid_face_input_snap_offsets(face)
        lines.append(
            "{face_id}: side={side}, function={function}, port={port}, fit_ref={fit_ref}, normal=({nx:.4g},{ny:.4g},{nz:.4g}), centroid=({cx:.4g},{cy:.4g},{cz:.4g}), snap_uv=({snap_u:.4g},{snap_v:.4g}), split={split:.4g}".format(
                face_id=face.get("face_id", ""),
                side=normalize_optical_solid_face_side(face.get("side_2d")),
                function=normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role")),
                port=optical_solid_face_port_role(face),
                fit_ref=normalize_optical_solid_face_fit_reference(face.get("fit_reference")),
                nx=float(face.get("normal", [0, 0, 1])[0]),
                ny=float(face.get("normal", [0, 0, 1])[1]),
                nz=float(face.get("normal", [0, 0, 1])[2]),
                cx=float(face.get("centroid", [0, 0, 0])[0]),
                cy=float(face.get("centroid", [0, 0, 0])[1]),
                cz=float(face.get("centroid", [0, 0, 0])[2]),
                snap_u=float(snap_u),
                snap_v=float(snap_v),
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


def rotation_matrix_from_kraken_tilts(tilt_x: float, tilt_y: float, tilt_z: float) -> np.ndarray:
    tx = np.deg2rad(float(tilt_x))
    ty = np.deg2rad(float(tilt_y))
    tz = np.deg2rad(float(tilt_z))
    rx = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, np.cos(tx), -np.sin(tx)],
            [0.0, np.sin(tx), np.cos(tx)],
        ],
        dtype=float,
    )
    ry = np.array(
        [
            [np.cos(ty), 0.0, np.sin(ty)],
            [0.0, 1.0, 0.0],
            [-np.sin(ty), 0.0, np.cos(ty)],
        ],
        dtype=float,
    )
    rz = np.array(
        [
            [np.cos(-tz), -np.sin(-tz), 0.0],
            [np.sin(-tz), np.cos(-tz), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    return rz @ ry @ rx


def kraken_tilts_from_rotation_matrix(rotation) -> tuple[float, float, float]:
    matrix = np.asarray(rotation, dtype=float).reshape((3, 3))
    tilt_y = float(np.arcsin(np.clip(-float(matrix[2, 0]), -1.0, 1.0)))
    cos_y = float(np.cos(tilt_y))
    if abs(cos_y) > 1e-10:
        tilt_x = float(np.arctan2(float(matrix[2, 1]), float(matrix[2, 2])))
        z_alpha = float(np.arctan2(float(matrix[1, 0]), float(matrix[0, 0])))
    else:
        tilt_x = 0.0
        z_alpha = float(np.arctan2(-float(matrix[0, 1]), float(matrix[1, 1])))
    return (
        float(np.rad2deg(tilt_x)),
        float(np.rad2deg(tilt_y)),
        float(-np.rad2deg(z_alpha)),
    )


def rotation_matrix_about_axis(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    unit = np.asarray(axis, dtype=float).reshape(3)
    norm = float(np.linalg.norm(unit))
    if norm <= 1e-12:
        return np.eye(3, dtype=float)
    unit = unit / norm
    x, y, z = (float(value) for value in unit)
    c = float(np.cos(angle_rad))
    s = float(np.sin(angle_rad))
    v = 1.0 - c
    return np.asarray(
        [
            [x * x * v + c, x * y * v - z * s, x * z * v + y * s],
            [y * x * v + z * s, y * y * v + c, y * z * v - x * s],
            [z * x * v - y * s, z * y * v + x * s, z * z * v + c],
        ],
        dtype=float,
    )


def rotation_matrix_aligning_vectors(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    src = np.asarray(source, dtype=float).reshape(3)
    dst = np.asarray(target, dtype=float).reshape(3)
    src_norm = float(np.linalg.norm(src))
    dst_norm = float(np.linalg.norm(dst))
    if src_norm <= 1e-12 or dst_norm <= 1e-12:
        return np.eye(3, dtype=float)
    src = src / src_norm
    dst = dst / dst_norm
    cross = np.cross(src, dst)
    cross_norm = float(np.linalg.norm(cross))
    dot = float(np.clip(np.dot(src, dst), -1.0, 1.0))
    if cross_norm <= 1e-12:
        if dot > 0.0:
            return np.eye(3, dtype=float)
        trial = np.cross(src, np.asarray((0.0, 1.0, 0.0), dtype=float))
        if float(np.linalg.norm(trial)) <= 1e-12:
            trial = np.cross(src, np.asarray((1.0, 0.0, 0.0), dtype=float))
        return rotation_matrix_about_axis(trial, np.pi)
    axis = cross / cross_norm
    angle = float(np.arctan2(cross_norm, dot))
    return rotation_matrix_about_axis(axis, angle)


def optical_solid_face_local_normal(face: dict[str, object]) -> np.ndarray:
    normal = np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
    if bool(face.get("flip_normal", False)):
        normal = -normal
    norm = float(np.linalg.norm(normal))
    if norm <= 1e-12:
        return np.asarray((0.0, 0.0, 1.0), dtype=float)
    return normal / norm


def optical_solid_face_input_snap_offsets(face: dict[str, object]) -> tuple[float, float]:
    return (
        float_or_default(face.get("input_offset_u_mm", face.get("input_snap_u_mm")), 0.0),
        float_or_default(face.get("input_offset_v_mm", face.get("input_snap_v_mm")), 0.0),
    )


def optical_solid_face_plane_basis(face: dict[str, object]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    normal = optical_solid_face_local_normal(face)
    reference_candidates = (
        np.asarray((0.0, 0.0, 1.0), dtype=float),
        np.asarray((0.0, 1.0, 0.0), dtype=float),
        np.asarray((1.0, 0.0, 0.0), dtype=float),
    )
    u_axis = None
    for reference in reference_candidates:
        projected = reference - normal * float(np.dot(reference, normal))
        norm = float(np.linalg.norm(projected))
        if norm > 1e-9 and np.isfinite(norm):
            u_axis = projected / norm
            break
    if u_axis is None:
        fallback = np.cross(normal, np.asarray((1.0, 0.0, 0.0), dtype=float))
        if float(np.linalg.norm(fallback)) <= 1e-9:
            fallback = np.cross(normal, np.asarray((0.0, 1.0, 0.0), dtype=float))
        fallback_norm = float(np.linalg.norm(fallback))
        if fallback_norm <= 1e-12 or not np.isfinite(fallback_norm):
            u_axis = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            u_axis = fallback / fallback_norm
    v_axis = np.cross(normal, u_axis)
    v_norm = float(np.linalg.norm(v_axis))
    if v_norm <= 1e-12 or not np.isfinite(v_norm):
        v_axis = np.asarray((0.0, 1.0, 0.0), dtype=float)
    else:
        v_axis = v_axis / v_norm
    return np.asarray(u_axis, dtype=float), np.asarray(v_axis, dtype=float), np.asarray(normal, dtype=float)


def optical_solid_face_local_anchor_point(face: dict[str, object]) -> np.ndarray:
    centroid = np.asarray(point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
    u_offset, v_offset = optical_solid_face_input_snap_offsets(face)
    if abs(float(u_offset)) <= 1e-12 and abs(float(v_offset)) <= 1e-12:
        return centroid
    u_axis, v_axis, _normal = optical_solid_face_plane_basis(face)
    return centroid + (u_axis * float(u_offset)) + (v_axis * float(v_offset))


def optical_solid_face_project_world_point_to_uv(
    face: dict[str, object],
    point_world,
) -> tuple[float, float, np.ndarray]:
    centroid_world = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
    normal_world = np.asarray(face.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
    u_axis_world = np.asarray(face.get("u_axis_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
    v_axis_world = np.asarray(face.get("v_axis_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
    point = np.asarray(point_world, dtype=float).reshape(3)
    if not (
        np.all(np.isfinite(centroid_world))
        and np.all(np.isfinite(normal_world))
        and np.all(np.isfinite(u_axis_world))
        and np.all(np.isfinite(v_axis_world))
        and np.all(np.isfinite(point))
    ):
        raise ValueError("World face records or picked point are not finite.")
    normal_world = normal_world / max(float(np.linalg.norm(normal_world)), 1e-12)
    u_axis_world = u_axis_world / max(float(np.linalg.norm(u_axis_world)), 1e-12)
    v_axis_world = v_axis_world / max(float(np.linalg.norm(v_axis_world)), 1e-12)
    projected = point - normal_world * float(np.dot(point - centroid_world, normal_world))
    delta = projected - centroid_world
    u_value = float(np.dot(delta, u_axis_world))
    v_value = float(np.dot(delta, v_axis_world))
    return u_value, v_value, np.asarray(projected, dtype=float)


def optical_solid_face_fit_priority(face: dict[str, object]) -> tuple[float, float, float, float]:
    function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
    side = normalize_optical_solid_face_side(face.get("side_2d"))
    port_role = optical_solid_face_port_role(face)
    priority_map = {
        OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT: 5.0,
        "Beam Splitter": 4.0,
        "Mirror": 3.0,
        "TIR": 2.0,
        OPTICAL_SOLID_FACE_FUNCTION_DEFAULT: 1.0,
        "Absorber/Mechanical": 0.0,
    }
    port_priority = {
        OPTICAL_SOLID_FACE_PORT_INPUT: 3.0,
        OPTICAL_SOLID_FACE_PORT_OUTPUT: 2.0,
        OPTICAL_SOLID_FACE_PORT_INTERACTION: 1.0,
        OPTICAL_SOLID_FACE_PORT_DEFAULT: 0.0,
    }
    return (
        float(port_priority.get(port_role, 0.0)),
        float(priority_map.get(function, 0.0)),
        1.0 if side != OPTICAL_SOLID_FACE_SIDE_DEFAULT else 0.0,
        float(face.get("area_mm2", 0.0) or 0.0),
    )


def select_optical_solid_anchor_face(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    face_id: str = "",
) -> dict[str, object] | None:
    normalized = normalize_optical_solid_face_metadata(metadata)
    faces = [face for face in list(normalized.get("faces", []) or []) if isinstance(face, dict)]
    requested = str(face_id or "").strip()
    if requested:
        for face in faces:
            if str(face.get("face_id", "") or "").strip() == requested:
                return normalize_optical_solid_face_record(face)
    assigned = [
        normalize_optical_solid_face_record(face)
        for face in faces
        if normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role")) != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
        or normalize_optical_solid_face_side(face.get("side_2d")) != OPTICAL_SOLID_FACE_SIDE_DEFAULT
    ]
    pool = assigned or [normalize_optical_solid_face_record(face) for face in faces]
    if not pool:
        return None
    return max(pool, key=optical_solid_face_fit_priority)


def select_optical_solid_roll_reference_face(
    metadata: dict[str, object],
    anchor_face_id: str,
) -> tuple[dict[str, object], str] | None:
    faces = [
        normalize_optical_solid_face_record(face)
        for face in list(normalize_optical_solid_face_metadata(metadata).get("faces", []) or [])
        if isinstance(face, dict)
    ]
    explicit: list[tuple[dict[str, object], str]] = []
    for face in faces:
        if str(face.get("face_id", "") or "").strip() == anchor_face_id:
            continue
        reference = normalize_optical_solid_face_fit_reference(face.get("fit_reference"))
        if reference != OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT:
            explicit.append((face, reference))
    if explicit:
        priority = {"+Y normal": 6.0, "-Y normal": 5.0, "+Z normal": 4.0, "-Z normal": 3.0, "+X normal": 2.0, "-X normal": 1.0}
        return max(explicit, key=lambda item: (float(priority.get(item[1], 0.0)), float(item[0].get("area_mm2", 0.0) or 0.0)))
    desired_sides = ("Up", "Down", "Front", "Back")
    for side in desired_sides:
        candidates = [
            face
            for face in faces
            if str(face.get("face_id", "") or "").strip() != anchor_face_id
            and normalize_optical_solid_face_side(face.get("side_2d")) == side
        ]
        if candidates:
            return max(candidates, key=lambda face: float(face.get("area_mm2", 0.0) or 0.0)), side
    return None


def solve_optical_solid_face_fit(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    face_id: str = "",
    target_normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
    target_point: tuple[float, float, float] = (0.0, 0.0, 0.0),
    roll_mode: str = OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
) -> dict[str, object] | None:
    normalized = normalize_optical_solid_face_metadata(metadata)
    anchor = select_optical_solid_anchor_face(normalized, face_id=face_id)
    if anchor is None:
        return None
    target = np.asarray(target_normal, dtype=float).reshape(3)
    target_anchor = np.asarray(target_point, dtype=float).reshape(3)
    target_norm = float(np.linalg.norm(target))
    if target_norm <= 1e-12 or not np.all(np.isfinite(target_anchor)):
        raise ValueError("Target normal and target point must be finite, with a non-zero normal.")
    target = target / target_norm
    anchor_normal = optical_solid_face_local_normal(anchor)
    anchor_local_point = optical_solid_face_local_anchor_point(anchor)
    rotation = rotation_matrix_aligning_vectors(anchor_normal, target)
    roll_side = ""
    if str(roll_mode or OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT).strip() == OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT:
        guide = select_optical_solid_roll_reference_face(normalized, str(anchor.get("face_id", "") or "").strip())
        if guide is not None:
            guide_face, side = guide
            desired_axes = {
                "Up": np.asarray((0.0, 1.0, 0.0), dtype=float),
                "Down": np.asarray((0.0, -1.0, 0.0), dtype=float),
                "Front": np.asarray((-1.0, 0.0, 0.0), dtype=float),
                "Back": np.asarray((1.0, 0.0, 0.0), dtype=float),
            }
            desired = optical_solid_face_fit_reference_axis(side)
            if desired is None:
                desired = desired_axes.get(side)
            if desired is not None:
                guide_world = rotation @ optical_solid_face_local_normal(guide_face)
                guide_proj = guide_world - target * float(np.dot(guide_world, target))
                desired_proj = desired - target * float(np.dot(desired, target))
                guide_norm = float(np.linalg.norm(guide_proj))
                desired_norm = float(np.linalg.norm(desired_proj))
                if guide_norm > 1e-9 and desired_norm > 1e-9:
                    guide_proj = guide_proj / guide_norm
                    desired_proj = desired_proj / desired_norm
                    angle = float(
                        np.arctan2(
                            float(np.dot(target, np.cross(guide_proj, desired_proj))),
                            float(np.clip(np.dot(guide_proj, desired_proj), -1.0, 1.0)),
                        )
                    )
                    rotation = rotation_matrix_about_axis(target, angle) @ rotation
                    roll_side = side
    tilts = kraken_tilts_from_rotation_matrix(rotation)
    anchor_world = anchor_local_point @ rotation.T
    desp_vector = target_anchor - anchor_world
    desp = (float(desp_vector[0]), float(desp_vector[1]), float(desp_vector[2]))
    return {
        "face_id": str(anchor.get("face_id", "") or "").strip(),
        "label": optical_solid_face_marker_label(anchor),
        "tilts": tuple(float(value) for value in tilts),
        "desp": tuple(float(value) for value in desp),
        "rotation": rotation,
        "roll_side": roll_side,
        "target_normal": tuple(float(value) for value in target),
        "target_point": tuple(float(value) for value in target_anchor),
        "anchor_local_point": tuple(float(value) for value in anchor_local_point),
        "input_offset_u_mm": float(optical_solid_face_input_snap_offsets(anchor)[0]),
        "input_offset_v_mm": float(optical_solid_face_input_snap_offsets(anchor)[1]),
    }


def solve_optical_solid_left_input_pose(
    metadata: dict[str, object] | list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    target_point: tuple[float, float, float] = (0.0, 0.0, 0.0),
    roll_mode: str = OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
) -> dict[str, object] | None:
    """Solve row pose from side labels using Left as the input face.

    Layout rays normally travel along +Z. The entrance face outward normal
    points back toward incoming space, so a correctly oriented Left/input face
    has normal -Z, not +Z.
    """
    normalized = normalize_optical_solid_face_metadata(metadata)
    input_face = optical_solid_input_anchor_face(normalized)
    if input_face is None:
        return None
    face_id = str(input_face.get("face_id", "") or "").strip()
    return solve_optical_solid_face_fit(
        normalized,
        face_id=face_id,
        target_normal=(0.0, 0.0, -1.0),
        target_point=target_point,
        roll_mode=roll_mode,
    )


def _row_face_metadata(row: object) -> dict[str, object]:
    advanced = getattr(row, "advanced", {})
    if not isinstance(advanced, dict):
        advanced = {}
    return normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))


def _row_rotation_and_offset(row: object, z_station: float) -> tuple[np.ndarray, np.ndarray]:
    rotation = rotation_matrix_from_kraken_tilts(
        float(getattr(row, "tilt_x", 0.0)),
        float(getattr(row, "tilt_y", 0.0)),
        float(getattr(row, "tilt_z", 0.0)),
    )
    offset = np.asarray(
        [
            float(getattr(row, "desp_x", 0.0)),
            float(getattr(row, "desp_y", 0.0)),
            float(z_station) + float(getattr(row, "desp_z", 0.0)),
        ],
        dtype=float,
    )
    return rotation, offset


def optical_solid_face_world_records(
    row: object,
    z_station: float,
    *,
    assigned_only: bool = True,
) -> list[dict[str, object]]:
    metadata = _row_face_metadata(row)
    rotation, offset = _row_rotation_and_offset(row, z_station)
    world_faces: list[dict[str, object]] = []
    for face in list(metadata.get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        role = legacy_role_from_optical_solid_face_function(face.get("function", face.get("role")))
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        side = normalize_optical_solid_face_side(face.get("side_2d"))
        if (
            assigned_only
            and role == OPTICAL_SOLID_FACE_ROLE_DEFAULT
            and function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
            and side == OPTICAL_SOLID_FACE_SIDE_DEFAULT
        ):
            continue
        centroid_local = np.asarray(point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
        anchor_local = optical_solid_face_local_anchor_point(face)
        normal_local = np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
        if bool(face.get("flip_normal", False)):
            normal_local = -normal_local
        centroid_world = centroid_local @ rotation.T + offset
        anchor_world = anchor_local @ rotation.T + offset
        normal_world = np.asarray(unit_vector_tuple(normal_local @ rotation.T), dtype=float)
        u_axis_local, v_axis_local, _normal_axis_local = optical_solid_face_plane_basis(face)
        u_axis_world = np.asarray(unit_vector_tuple(u_axis_local @ rotation.T), dtype=float)
        v_axis_world = np.asarray(unit_vector_tuple(v_axis_local @ rotation.T), dtype=float)
        if not (
            np.all(np.isfinite(centroid_world))
            and np.all(np.isfinite(anchor_world))
            and np.all(np.isfinite(normal_world))
        ):
            continue
        world_face = dict(face)
        world_face["role"] = role
        world_face["function"] = function
        world_face["side_2d"] = side
        world_face["centroid_world"] = tuple(float(v) for v in centroid_world[:3])
        world_face["anchor_world"] = tuple(float(v) for v in anchor_world[:3])
        world_face["normal_world"] = tuple(float(v) for v in normal_world[:3])
        world_face["u_axis_world"] = tuple(float(v) for v in u_axis_world[:3])
        world_face["v_axis_world"] = tuple(float(v) for v in v_axis_world[:3])
        world_faces.append(world_face)
    return world_faces


def optical_solid_virtual_plane_world_records(
    row: object,
    z_station: float,
    *,
    assigned_only: bool = True,
) -> list[dict[str, object]]:
    metadata = _row_face_metadata(row)
    rotation, offset = _row_rotation_and_offset(row, z_station)
    world_planes: list[dict[str, object]] = []
    for plane in list(metadata.get("virtual_planes", []) or []):
        if not isinstance(plane, dict):
            continue
        normalized = normalize_optical_solid_virtual_plane_record(plane)
        if assigned_only and normalize_optical_solid_virtual_plane_kind(normalized.get("kind")) not in OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES:
            continue
        point_local = np.asarray(point3_tuple(normalized.get("point", (0.0, 0.0, 0.0))), dtype=float)
        normal_local = np.asarray(unit_vector_tuple(normalized.get("normal", (0.0, 0.0, 1.0))), dtype=float)
        point_world = point_local @ rotation.T + offset
        normal_world = np.asarray(unit_vector_tuple(normal_local @ rotation.T), dtype=float)
        if not (np.all(np.isfinite(point_world)) and np.all(np.isfinite(normal_world))):
            continue
        world_plane = dict(normalized)
        world_plane["point_world"] = tuple(float(v) for v in point_world[:3])
        world_plane["normal_world"] = tuple(float(v) for v in normal_world[:3])
        world_planes.append(world_plane)
    return world_planes


def optical_solid_face_effective_radius_mm(face: dict[str, object]) -> float:
    clear_aperture = max(float_or_default(face.get("clear_aperture_mm"), 0.0), 0.0)
    if clear_aperture > 0.0:
        return max(clear_aperture * 0.5, 1e-6)
    area = max(float_or_default(face.get("area_mm2"), 0.0), 1e-9)
    return max(float(np.sqrt(area / np.pi)), 1e-6)


def match_optical_solid_world_face(
    world_faces: list[dict[str, object]],
    point_world,
    normal_world=None,
) -> dict[str, object] | None:
    if not world_faces:
        return None
    point = np.asarray(point_world, dtype=float).reshape(3)
    if not np.all(np.isfinite(point)):
        return None
    hit_normal = None
    if normal_world is not None:
        try:
            hit_normal = np.asarray(unit_vector_tuple(normal_world), dtype=float).reshape(3)
        except Exception:
            hit_normal = None
    best_record: dict[str, object] | None = None
    best_score: tuple[float, float, float] | None = None
    for face in world_faces:
        centroid = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
        normal = np.asarray(face.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
        if not (np.all(np.isfinite(centroid)) and np.all(np.isfinite(normal))):
            continue
        delta = point - centroid
        along = float(np.dot(delta, normal))
        lateral = float(np.linalg.norm(delta - normal * along))
        if hit_normal is not None and np.all(np.isfinite(hit_normal)):
            alignment = float(np.clip(np.dot(hit_normal, normal), -1.0, 1.0))
            alignment_penalty = 1.0 - alignment
        else:
            alignment = float("nan")
            alignment_penalty = 0.5
        radius = optical_solid_face_effective_radius_mm(face)
        score = (
            abs(along),
            alignment_penalty,
            lateral / radius,
        )
        if best_score is None or score < best_score:
            matched = dict(face)
            matched["plane_distance_mm"] = abs(along)
            matched["lateral_distance_mm"] = lateral
            matched["normal_alignment"] = alignment
            matched["face_radius_mm"] = radius
            best_record = matched
            best_score = score
    return best_record


def optical_solid_plane_basis(normal_world) -> tuple[np.ndarray, np.ndarray]:
    normal = np.asarray(unit_vector_tuple(normal_world), dtype=float).reshape(3)
    ref = np.asarray((0.0, 0.0, 1.0), dtype=float) if abs(float(normal[2])) < 0.9 else np.asarray((0.0, 1.0, 0.0), dtype=float)
    u_axis = np.cross(normal, ref)
    u_norm = float(np.linalg.norm(u_axis))
    if u_norm <= 1e-12:
        ref = np.asarray((1.0, 0.0, 0.0), dtype=float)
        u_axis = np.cross(normal, ref)
        u_norm = float(np.linalg.norm(u_axis))
    if u_norm <= 1e-12:
        return np.asarray((1.0, 0.0, 0.0), dtype=float), np.asarray((0.0, 1.0, 0.0), dtype=float)
    u_axis = u_axis / u_norm
    v_axis = np.cross(normal, u_axis)
    v_norm = float(np.linalg.norm(v_axis))
    if v_norm <= 1e-12:
        return u_axis, np.asarray((0.0, 1.0, 0.0), dtype=float)
    return u_axis, v_axis / v_norm


def closest_polyline_point(points: np.ndarray, target: np.ndarray) -> np.ndarray:
    point_array = np.asarray(points, dtype=float)
    target_point = np.asarray(target, dtype=float).reshape(3)
    best_point = np.asarray(point_array[0], dtype=float)
    best_distance = float("inf")
    for start, end in zip(point_array[:-1], point_array[1:]):
        start = np.asarray(start, dtype=float)
        end = np.asarray(end, dtype=float)
        segment = end - start
        denom = float(np.dot(segment, segment))
        if denom <= 1e-18:
            candidate = start
        else:
            t = float(np.dot(target_point - start, segment) / denom)
            t = min(max(t, 0.0), 1.0)
            candidate = start + segment * t
        distance = float(np.linalg.norm(candidate - target_point))
        if distance < best_distance:
            best_distance = distance
            best_point = candidate
    return best_point


def closest_polyline_point_and_direction(points: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    point_array = np.asarray(points, dtype=float)
    target_point = np.asarray(target, dtype=float).reshape(3)
    best_point = np.asarray(point_array[0], dtype=float)
    best_direction = np.asarray(point_array[-1] - point_array[0], dtype=float)
    best_distance = float("inf")
    for start, end in zip(point_array[:-1], point_array[1:]):
        start = np.asarray(start, dtype=float)
        end = np.asarray(end, dtype=float)
        segment = end - start
        denom = float(np.dot(segment, segment))
        if denom <= 1e-18:
            candidate = start
            direction = best_direction
        else:
            t = float(np.dot(target_point - start, segment) / denom)
            t = min(max(t, 0.0), 1.0)
            candidate = start + segment * t
            direction = segment
        distance = float(np.linalg.norm(candidate - target_point))
        if distance < best_distance:
            best_distance = distance
            best_point = candidate
            best_direction = np.asarray(direction, dtype=float)
    norm = float(np.linalg.norm(best_direction))
    if norm <= 1e-12:
        best_direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
    else:
        best_direction = best_direction / norm
    return best_point, best_direction


def ray_point_and_direction_on_surface_plane(
    points: np.ndarray,
    origin: np.ndarray,
    normal: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    point_array = np.asarray(points, dtype=float)
    plane_origin = np.asarray(origin, dtype=float).reshape(3)
    plane_normal = np.asarray(normal, dtype=float).reshape(3)
    best_point: np.ndarray | None = None
    best_direction: np.ndarray | None = None
    best_distance = float("inf")
    for start, end in zip(point_array[:-1], point_array[1:]):
        start = np.asarray(start, dtype=float)
        end = np.asarray(end, dtype=float)
        segment = end - start
        denom = float(np.dot(segment, plane_normal))
        if abs(denom) <= 1e-12:
            continue
        t = -float(np.dot(start - plane_origin, plane_normal)) / denom
        if -1e-9 <= t <= 1.0 + 1e-9:
            t = min(max(t, 0.0), 1.0)
            candidate = start + segment * t
            distance = float(np.linalg.norm(candidate - plane_origin))
            if distance < best_distance:
                best_distance = distance
                best_point = candidate
                best_direction = np.asarray(segment, dtype=float)
    if best_point is not None:
        direction = np.asarray(best_direction, dtype=float)
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-12:
            direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            direction = direction / norm
        return best_point, direction
    closest, direction = closest_polyline_point_and_direction(point_array, plane_origin)
    return closest - plane_normal * float(np.dot(closest - plane_origin, plane_normal)), direction


def ray_point_on_surface_plane(points: np.ndarray, origin: np.ndarray, normal: np.ndarray) -> np.ndarray:
    point, _direction = ray_point_and_direction_on_surface_plane(points, origin, normal)
    return point


def optical_solid_face_snap_anchor(
    row: object,
    z_station: float,
    ray_points: np.ndarray,
) -> dict[str, object] | None:
    face_records = optical_solid_face_world_records(row, z_station, assigned_only=True)
    if not face_records:
        return None
    priority_map = {
        OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT: 5,
        "Beam Splitter": 4,
        "Mirror": 3,
        "TIR": 2,
        OPTICAL_SOLID_FACE_FUNCTION_DEFAULT: 1,
    }
    best: tuple[tuple[float, float, float, float, float], dict[str, object]] | None = None
    for face in face_records:
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        if function == "Absorber/Mechanical":
            continue
        anchor = np.asarray(face.get("anchor_world", face.get("centroid_world", (0.0, 0.0, 0.0))), dtype=float)
        normal = np.asarray(face.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)
        if anchor.size < 3 or normal.size < 3 or not (np.all(np.isfinite(anchor[:3])) and np.all(np.isfinite(normal[:3]))):
            continue
        target, ray_direction = ray_point_and_direction_on_surface_plane(ray_points, anchor[:3], normal[:3])
        distance = float(np.linalg.norm(target - anchor[:3]))
        facing = float(-np.dot(normal[:3], ray_direction[:3]))
        score = (
            float(priority_map.get(function, 0)),
            float(1.0 if normalize_optical_solid_face_side(face.get("side_2d")) != OPTICAL_SOLID_FACE_SIDE_DEFAULT else 0.0),
            facing,
            -distance,
            float(face.get("area_mm2", 0.0) or 0.0),
        )
        payload = dict(face)
        payload["target_world"] = tuple(float(value) for value in target[:3])
        payload["ray_direction_world"] = tuple(float(value) for value in ray_direction[:3])
        payload["facing_score"] = facing
        payload["distance_to_ray_mm"] = distance
        payload["label"] = optical_solid_face_marker_label(face)
        if best is None or score > best[0]:
            best = (score, payload)
    return None if best is None else best[1]


def optical_solid_virtual_plane_segment_events(
    world_planes: list[dict[str, object]],
    start_point_world,
    end_point_world,
    *,
    tolerance_mm: float = 1e-6,
) -> list[dict[str, object]]:
    start = np.asarray(start_point_world, dtype=float).reshape(3)
    end = np.asarray(end_point_world, dtype=float).reshape(3)
    direction = end - start
    if not (np.all(np.isfinite(start)) and np.all(np.isfinite(end))):
        return []
    if float(np.linalg.norm(direction)) <= tolerance_mm:
        return []
    events: list[dict[str, object]] = []
    for plane in world_planes:
        point = np.asarray(plane.get("point_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
        normal = np.asarray(plane.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(3)
        if not (np.all(np.isfinite(point)) and np.all(np.isfinite(normal))):
            continue
        d0 = float(np.dot(start - point, normal))
        d1 = float(np.dot(end - point, normal))
        if abs(d0) <= tolerance_mm and abs(d1) <= tolerance_mm:
            t = 0.5
        else:
            denominator = d0 - d1
            if abs(denominator) <= 1e-12:
                continue
            t = d0 / denominator
            if not (tolerance_mm < t < 1.0 - tolerance_mm):
                continue
        crossing = start + direction * float(t)
        aperture = max(float_or_default(plane.get("aperture_mm"), 0.0), 0.0)
        if aperture > 0.0:
            u_axis, v_axis = optical_solid_plane_basis(normal)
            delta = crossing - point
            du = float(np.dot(delta, u_axis))
            dv = float(np.dot(delta, v_axis))
            half = aperture * 0.5 + tolerance_mm
            if max(abs(du), abs(dv)) > half:
                continue
        event = dict(plane)
        event["kind"] = "virtual_plane"
        event["crossing_t"] = float(t)
        event["crossing_point_world"] = tuple(float(value) for value in crossing[:3])
        events.append(event)
    events.sort(key=lambda item: float(item.get("crossing_t", 0.5)))
    return events


def optical_solid_trace_sequence_records(
    row: object,
    z_station: float,
    hit_points_world,
    hit_normals_world=None,
    *,
    assigned_only: bool = True,
    include_virtual_planes: bool = True,
) -> list[dict[str, object]]:
    points = np.asarray(hit_points_world, dtype=float)
    if points.ndim == 1 and points.size == 3:
        points = points.reshape(1, 3)
    if points.ndim != 2 or points.shape[1] < 3 or points.shape[0] == 0:
        return []
    if hit_normals_world is None:
        normals = np.empty((0, 3), dtype=float)
    else:
        normals = np.asarray(hit_normals_world, dtype=float)
        if normals.ndim == 1 and normals.size == 3:
            normals = normals.reshape(1, 3)
        if normals.ndim != 2 or normals.shape[1] < 3:
            normals = np.empty((0, 3), dtype=float)
    world_faces = optical_solid_face_world_records(row, z_station, assigned_only=assigned_only)
    world_planes = optical_solid_virtual_plane_world_records(row, z_station, assigned_only=assigned_only) if include_virtual_planes else []
    sequence: list[dict[str, object]] = []
    for hit_index in range(points.shape[0]):
        point = np.asarray(points[hit_index, :3], dtype=float)
        normal = np.asarray(normals[hit_index, :3], dtype=float) if hit_index < normals.shape[0] else None
        matched_face = match_optical_solid_world_face(world_faces, point, normal)
        event = {
            "kind": "face_hit",
            "sequence_position": float(hit_index),
            "hit_index": int(hit_index),
            "point_world": tuple(float(value) for value in point[:3]),
            "normal_world": (
                tuple(float(value) for value in np.asarray(normal, dtype=float)[:3])
                if normal is not None and np.all(np.isfinite(np.asarray(normal, dtype=float)[:3]))
                else ()
            ),
        }
        if matched_face is not None:
            event.update(
                {
                    "face_id": str(matched_face.get("face_id", "") or ""),
                    "side_2d": normalize_optical_solid_face_side(matched_face.get("side_2d")),
                    "function": normalize_optical_solid_face_function(matched_face.get("function"), legacy_role=matched_face.get("role")),
                    "label": optical_solid_face_marker_label(matched_face),
                    "plane_distance_mm": float(matched_face.get("plane_distance_mm", float("nan"))),
                    "lateral_distance_mm": float(matched_face.get("lateral_distance_mm", float("nan"))),
                    "normal_alignment": float(matched_face.get("normal_alignment", float("nan"))),
                }
            )
        sequence.append(event)
        if include_virtual_planes and hit_index + 1 < points.shape[0]:
            end_point = np.asarray(points[hit_index + 1, :3], dtype=float)
            for plane_event in optical_solid_virtual_plane_segment_events(world_planes, point, end_point):
                sequence.append(
                    {
                        "kind": "virtual_plane",
                        "sequence_position": float(hit_index) + float(plane_event.get("crossing_t", 0.5)),
                        "after_hit_index": int(hit_index),
                        "plane_id": str(plane_event.get("plane_id", "") or ""),
                        "plane_kind": normalize_optical_solid_virtual_plane_kind(plane_event.get("kind")),
                        "diagonal_mode": normalize_optical_solid_virtual_plane_diagonal(plane_event.get("diagonal_mode")),
                        "crossing_point_world": tuple(float(value) for value in np.asarray(plane_event.get("crossing_point_world", (0.0, 0.0, 0.0)), dtype=float)[:3]),
                        "normal_world": tuple(float(value) for value in np.asarray(plane_event.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)[:3]),
                        "split_ratio": float(np.clip(float_or_default(plane_event.get("split_ratio"), 0.5), 0.0, 1.0)),
                        "loss": float(np.clip(float_or_default(plane_event.get("loss"), 0.0), 0.0, 1.0)),
                        "phase_deg": float_or_default(plane_event.get("phase_deg"), 0.0),
                    }
                )
    sequence.sort(key=lambda item: float(item.get("sequence_position", 0.0)))
    return sequence
