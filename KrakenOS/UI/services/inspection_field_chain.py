"""bugs/0828: one dialog showing the DERIVATION, because an orphan number is the bug.

Three numbers confused the user in one session, and every one of them was correct:

* the device stayed 20 mm after typing 50x50 -- because the field they typed was the
  Required FOV, and the dialog never said which of its two numbers they were editing;
* the scene drew ``FOV 21.0x8.3`` while the banner said ``delivering 21 x 21`` -- two
  different quantities (per-FACE field vs whole-sensor field) with the same word on them;
* a swap pre-filled ``59.3284`` -- the object field that would exactly fill the sensor at
  the magnification right after the swap (23.04 mm sensor / |m| 0.3883), stated nowhere.

None of these is an arithmetic error. Each is a number shown without its parent. So the
fix is not another field: it is that every line names what it was derived FROM.

The chain, on the folded om05a bench the user actually runs:

    Part          20 x 20 x 1 mm                  (what you set)
    Inspecting    front face  ->  20 x 1 mm       (which face the OPTICS can reach)
    Required FOV  21 x 1.05 mm                    (face + 5% alignment margin)
    Delivered     21 x 8.3 mm  per face           (what the geometry actually gives)

The height is 1 mm because the inspected face is a 1 mm EDGE. On that bench a centre
prism and two RA mirrors fold sideways into the lens, so the optical path can only ever
reach an edge face -- the 20x20 top and bottom are unreachable by construction. The chain
makes that legible instead of leaving 8.3 looking like a defect.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The alignment margin a face-derived FOV carries, matching
#: ``solve_fov_to_inspection_face``: the face plus 5% for positioning error.
FACE_FOV_MARGIN: float = 1.05


@dataclass(frozen=True)
class ChainRow:
    """One line of the derivation. ``derived_from`` is the whole point."""

    label: str
    value: str
    derived_from: str = ""
    editable: bool = False

    def text(self) -> str:
        return f"{self.label}: {self.value}" + (f"  ({self.derived_from})" if self.derived_from else "")


def _fmt(w, h=None) -> str:
    if h is None:
        return f"{float(w):g} mm"
    return f"{float(w):g} x {float(h):g} mm"


def field_chain(spec, *, face_dims_fn, required_fov=None, sensor_wh=None,
                magnification=None, measured_face_wh=None) -> list[ChainRow]:
    """The derivation, top to bottom. Each row states what produced it.

    ``required_fov`` is the user's own number when they typed one -- it then becomes
    authoritative and the margin drops out, exactly as ``solve_fov_to_inspection_face``
    treats it.

    ``measured_face_wh`` is the field ONE face actually receives, and it must be MEASURED
    and passed in -- it cannot be computed here. ``sensor / |m|`` is the WHOLE-SENSOR
    field, and on a split-field bench no single face receives it. The first draft of this
    module computed the per-face row from ``sensor / |m|`` and labelled it "per face",
    reproducing exactly the defect it exists to prevent. Two rows, two provenances, never
    one number wearing both labels.
    """
    rows: list[ChainRow] = []
    face = str(spec.get("active_face", "") or "?")
    rows.append(ChainRow(
        "Part",
        f"{float(spec.get('width_mm', 0)):g} x {float(spec.get('depth_mm', 0)):g} "
        f"x {float(spec.get('height_mm', 0)):g} mm",
        "length x width x thickness, as you set it",
        editable=True,
    ))

    # bugs/0768 settled that the inspected face is NEVER a choice here: the split field
    # images the FRONT face and its mirror image on the BACK, L x T, W apart. So this row
    # states what the bench does, it does not offer a selection -- re-adding a face
    # dropdown would undo a control the user had removed on purpose.
    fw, fh = face_dims_fn(spec, face)
    rows.append(ChainRow(
        "Inspected faces",
        f"2 x (L x T) = {_fmt(fw, fh)}",
        "front + its mirror on the back, W apart; the fold turns sideways,\n so L x W top/bottom are unreachable",
    ))

    if required_fov is not None:
        try:
            rw = rh = float(required_fov)
            rows.append(ChainRow("Required FOV", _fmt(rw, rh),
                                 "your number -- authoritative, no margin added", editable=True))
        except (TypeError, ValueError):
            required_fov = None
    if required_fov is None:
        rows.append(ChainRow(
            "Required FOV",
            _fmt(fw * FACE_FOV_MARGIN, fh * FACE_FOV_MARGIN),
            f"the inspected face + {(FACE_FOV_MARGIN - 1) * 100:g}% alignment margin",
            editable=True,
        ))

    if sensor_wh and magnification:
        try:
            m = abs(float(magnification))
            sw, sh = (float(v) for v in sensor_wh)
            if m > 1e-9:
                rows.append(ChainRow(
                    "Across the sensor",
                    _fmt(sw / m, sh / m),
                    f"sensor {_fmt(sw, sh)} / |m| {m:.4g}; the WHOLE sensor",
                ))
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if measured_face_wh:
        try:
            mw, mh = (float(v) for v in measured_face_wh)
            rows.append(ChainRow(
                "Reaching one face",
                _fmt(mw, mh),
                "MEASURED from traced coverage; each face gets a\n strip of the sensor, not all of it",
            ))
        except (TypeError, ValueError):
            pass
    return rows


def chain_text(rows) -> str:
    return "\n".join(r.text() for r in rows)


def explain_prefill(sensor_wh, magnification) -> str:
    """Where a pre-filled object field came from -- the user's 59.3284.

    Not sqrt(2) times anything: it is the object field that exactly fills the sensor at
    the magnification in force right now, which after a swap is the NEW lens's.
    """
    try:
        m = abs(float(magnification))
        sw, sh = (float(v) for v in sensor_wh)
    except (TypeError, ValueError):
        return ""
    if m <= 1e-9:
        return ""
    return (f"pre-filled from sensor {_fmt(sw, sh)} / |m| {m:.4g} = "
            f"{_fmt(sw / m, sh / m)} -- the field that exactly fills the sensor as the "
            f"scene stands; type your own to override it")


# ---------------------------------------------------------------------------
# The illustration (user's request): show WHICH FACE is being inspected, and
# which faces the optics can never reach.
#
# On the folded om05a bench a centre prism and two RA mirrors fold sideways into
# the lens, so the path only ever reaches an EDGE face -- the 20x20 top and
# bottom are unreachable by construction, whatever the dialog offers. The user
# put it plainly: "it can never image the top face 20x20 (and the bottom face as
# well). The ray tracing physics should have told you all this."
#
# So the picture does not merely highlight the active face: it greys out the ones
# no dialog choice could ever make work. Geometry is pure here and Tk-free, so it
# is testable and the renderer stays a thin drawing loop.
# ---------------------------------------------------------------------------

#: Unit-cube corners, (x=length, y=width, z=thickness), each in [-0.5, +0.5].
_CUBE = {
    "front":  ((-.5, -.5, -.5), (+.5, -.5, -.5), (+.5, -.5, +.5), (-.5, -.5, +.5)),
    "back":   ((-.5, +.5, -.5), (+.5, +.5, -.5), (+.5, +.5, +.5), (-.5, +.5, +.5)),
    "left":   ((-.5, -.5, -.5), (-.5, +.5, -.5), (-.5, +.5, +.5), (-.5, -.5, +.5)),
    "right":  ((+.5, -.5, -.5), (+.5, +.5, -.5), (+.5, +.5, +.5), (+.5, -.5, +.5)),
    "top":    ((-.5, -.5, +.5), (+.5, -.5, +.5), (+.5, +.5, +.5), (-.5, +.5, +.5)),
    "bottom": ((-.5, -.5, -.5), (+.5, -.5, -.5), (+.5, +.5, -.5), (-.5, +.5, -.5)),
}


def face_polygons(spec, *, width_px: int = 200, height_px: int = 150,
                  margin_px: int = 18) -> "dict[str, list[tuple[float, float]]]":
    """Isometric outline of the part, per face, in canvas pixels.

    Scaled to the part's REAL proportions, so a 20 x 20 x 1 device draws as the thin
    wafer it is -- which is itself the explanation for a 1 mm field, visible at a glance
    rather than deduced from a number.
    """
    L = max(float(spec.get("width_mm", 1) or 1), 1e-6)
    W = max(float(spec.get("depth_mm", 1) or 1), 1e-6)
    T = max(float(spec.get("height_mm", 1) or 1), 1e-6)
    scale = max(L, W, T)
    lx, wy, tz = L / scale, W / scale, T / scale

    def project(p):
        x, y, z = p[0] * lx, p[1] * wy, p[2] * tz
        return (x - y) * 0.866, (x + y) * 0.5 - z

    pts = [project(c) for face in _CUBE.values() for c in face]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    span_x = max(max(xs) - min(xs), 1e-9); span_y = max(max(ys) - min(ys), 1e-9)
    k = min((width_px - 2 * margin_px) / span_x, (height_px - 2 * margin_px) / span_y)
    ox = width_px / 2 - (min(xs) + max(xs)) / 2 * k
    oy = height_px / 2 + (min(ys) + max(ys)) / 2 * k

    out = {}
    for name, corners in _CUBE.items():
        out[name] = [(project(c)[0] * k + ox, oy - project(c)[1] * k) for c in corners]
    return out


def inspected_faces(spec, *, folded: bool) -> "tuple[str, ...]":
    """The faces the bench images -- a STATEMENT, not a choice (bugs/0768).

    A split field images the front face and its mirror on the back, so both are lit in the
    illustration. An unfolded bench images the single active face.
    """
    return ("front", "back") if folded else (str(spec.get("active_face", "front") or "front"),)


def unreachable_faces(spec, *, folded: bool) -> "tuple[str, ...]":
    """Faces the optical path can NEVER image, whatever the dialog offers.

    On a folded bench the fold turns sideways into the lens, so top and bottom are out
    by construction. Offering them as choices is how a user ends up inspecting a face
    the machine cannot see. Returns () when the geometry imposes no such limit.
    """
    return ("top", "bottom") if folded else ()


def face_summary(spec, face, *, face_dims_fn, folded: bool) -> str:
    """One line under the picture: what this face is, and whether it is even possible."""
    w, h = face_dims_fn(spec, face)
    if face in unreachable_faces(spec, folded=folded):
        return (f"{face} face {_fmt(w, h)} -- NOT imageable on this bench: the fold turns "
                f"sideways into the lens, so only edge faces are reachable")
    return f"{face} face {_fmt(w, h)} -- inspected"
