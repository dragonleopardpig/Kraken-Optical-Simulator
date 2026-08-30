"""Cell-level solve (bugs/0665, phase 3 of the multi-station cell): from the part's
dimensions and a defect-size target, choose a camera + lens per face from the
registered cameras and the lens catalog, then BUILD each station layout with the
folder importers -- a new cell starts from numbers instead of six hand-built layouts.

Per face the requirement is: field = the face's dims + margin (oriented landscape so
the longer side maps to the sensor width), object-space resolution = defect size /
pixels-per-defect, a minimum working distance. The catalog matcher (bugs/0634) tests
every registered camera x catalog lens; opposite faces share one station design.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from KrakenOS.UI.services.inspection_part import FACE_ORDER, face_dims, normalize_inspection_part_spec

FACE_PAIRS: tuple[tuple[str, str], ...] = (("front", "back"), ("left", "right"), ("top", "bottom"))


@dataclass
class FaceRequirement:
    face: str
    fov_w_mm: float          # landscape: the longer face side (+ margin)
    fov_h_mm: float
    rotated: bool            # the face's width/height were swapped to read landscape
    resolution_um_per_px: float
    wd_min_mm: float | None


@dataclass
class StationChoice:
    face: str
    requirement: FaceRequirement
    camera: str
    camera_folder: str | None
    lens: str
    lens_folder: str | None
    magnification: float
    working_distance_mm: float | None
    delivered_fov_mm: tuple[float, float]
    resolution_um_per_px: float
    passes: bool
    reasons: tuple[str, ...]


def face_requirements(
    part_spec: dict[str, Any],
    defect_mm: float,
    *,
    px_per_defect: float = 3.0,
    margin: float = 0.05,
    wd_min_mm: float | None = None,
) -> dict[str, FaceRequirement]:
    """One requirement per face. Resolution = defect / px-per-defect (um/px)."""
    spec = normalize_inspection_part_spec(part_spec)
    defect = float(defect_mm)
    ppd = max(float(px_per_defect), 1.0)
    if not (defect > 0.0):
        raise ValueError("defect size must be positive")
    resolution = 1000.0 * defect / ppd
    out: dict[str, FaceRequirement] = {}
    for face in FACE_ORDER:
        w, h = face_dims(spec, face)
        rotated = h > w
        fw, fh = (h, w) if rotated else (w, h)
        out[face] = FaceRequirement(
            face=face,
            fov_w_mm=fw * (1.0 + margin),
            fov_h_mm=fh * (1.0 + margin),
            rotated=rotated,
            resolution_um_per_px=resolution,
            wd_min_mm=(float(wd_min_mm) if wd_min_mm and float(wd_min_mm) > 0 else None),
        )
    return out


def _is_fixed_magnification(lens) -> bool:
    return (
        lens.mag_min is not None and lens.mag_max is not None
        and abs(float(lens.mag_max) - float(lens.mag_min)) < 1e-9
    )


def _evaluate(req: FaceRequirement, cam, lens):
    """Height-aware match: m = min(sensor_w/fov_w, sensor_h/fov_h) so BOTH face sides fit;
    the matcher then judges resolution / lens range / WD / image circle at the field the
    camera actually sees (sensor / m).

    A FIXED-magnification lens (telecentric) is judged at ITS OWN m: its field
    sensor/m must cover the face (m <= the required m) -- the catalog matcher's
    "required m inside the band" test wrongly rejects a 0.75x lens whose 11.3 x 9.4 mm
    field covers a 10.5 x 8.4 mm face."""
    from KrakenOS.UI.services.system_matcher import MatchRequirement, match_combination

    m_req = min(cam.sensor_w_mm / req.fov_w_mm, cam.sensor_h_mm / req.fov_h_mm)
    if not (m_req > 1e-9):
        return None, None, None
    fixed = _is_fixed_magnification(lens)
    m = float(lens.mag_max) if fixed else m_req
    if not (m > 1e-9):
        return None, None, None
    delivered = (cam.sensor_w_mm / m, cam.sensor_h_mm / m)
    mreq = MatchRequirement(
        fov_w_mm=delivered[0], fov_h_mm=delivered[1],
        resolution_um_per_px=req.resolution_um_per_px, wd_min_mm=req.wd_min_mm,
    )
    result = match_combination(mreq, cam, lens)
    if fixed and (delivered[0] < req.fov_w_mm - 1e-9 or delivered[1] < req.fov_h_mm - 1e-9):
        # the fixed field is smaller than the face: a hard miss the matcher cannot see
        result = type(result)(**{
            **result.__dict__,
            "magnification_ok": False,
            "passes": False,
            "reasons": tuple(result.reasons) + (
                f"fixed {m:.3g}x field {delivered[0]:.1f} x {delivered[1]:.1f} mm < face "
                f"{req.fov_w_mm:.1f} x {req.fov_h_mm:.1f} mm",
            ),
        })
    pitch_um = 1000.0 * cam.sensor_w_mm / cam.pixels_w
    return result, delivered, pitch_um / m


def choose_station(
    req: FaceRequirement, cameras, lenses, *, prefer_fixed_magnification: bool = True
) -> StationChoice | None:
    """The best camera x lens for one face: passing first; then (by default) a
    FIXED-magnification lens over a variable one -- a defect-inspection cell wants the
    telecentric's constant scale and no perspective when one fits; then fewest
    failures, then the largest working-distance margin (the matcher's own ranking)."""
    candidates = []
    for cam in cameras:
        for lens in lenses:
            result, delivered, res = _evaluate(req, cam, lens)
            if result is None:
                continue
            wd_margin = (result.working_distance_mm or 0.0) - (req.wd_min_mm or 0.0)
            fixed_rank = (0 if _is_fixed_magnification(lens) else 1) if prefer_fixed_magnification else 0
            candidates.append((
                (0 if result.passes else 1, fixed_rank, len(result.reasons), -wd_margin),
                StationChoice(
                    face=req.face, requirement=req, camera=cam.name, camera_folder=cam.folder,
                    lens=lens.name, lens_folder=lens.folder, magnification=result.magnification,
                    working_distance_mm=result.working_distance_mm, delivered_fov_mm=delivered,
                    resolution_um_per_px=res, passes=result.passes, reasons=result.reasons,
                ),
            ))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def solve_cell_stations(
    part_spec: dict[str, Any],
    defect_mm: float,
    *,
    px_per_defect: float = 3.0,
    margin: float = 0.05,
    wd_min_mm: float | None = None,
    cameras=None,
    lenses=None,
    prefer_fixed_magnification: bool = True,
) -> dict[str, StationChoice | None]:
    """Face -> best station choice (opposite faces share one, they have the same dims)."""
    from KrakenOS.UI.services.system_matcher import enumerate_cameras, enumerate_lenses

    cams = list(cameras) if cameras is not None else enumerate_cameras()
    lns = list(lenses) if lenses is not None else enumerate_lenses()
    reqs = face_requirements(part_spec, defect_mm, px_per_defect=px_per_defect, margin=margin, wd_min_mm=wd_min_mm)
    out: dict[str, StationChoice | None] = {}
    for a, b in FACE_PAIRS:
        choice = choose_station(reqs[a], cams, lns, prefer_fixed_magnification=prefer_fixed_magnification)
        out[a] = choice
        if choice is None:
            out[b] = None
        else:
            twin = StationChoice(**{**choice.__dict__, "face": b, "requirement": reqs[b]})
            out[b] = twin
    return out


def choice_summary(choices: dict[str, StationChoice | None]) -> str:
    lines = []
    for face in FACE_ORDER:
        c = choices.get(face)
        if c is None:
            lines.append(f"{face:6}: no camera x lens candidate")
            continue
        fw, fh = c.delivered_fov_mm
        wd = f"{c.working_distance_mm:.0f} mm WD" if c.working_distance_mm else "WD n/a"
        flag = "OK" if c.passes else "NO FIT: " + "; ".join(c.reasons)
        lines.append(
            f"{face:6}: {c.camera} + {c.lens} -- m {c.magnification:.3f}, field {fw:.1f} x {fh:.1f} mm, "
            f"{c.resolution_um_per_px:.1f} um/px, {wd} [{flag}]"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------------
# Building the station layouts
# ---------------------------------------------------------------------------------
def build_station_layout(choice: StationChoice, part_spec: dict[str, Any], out_path: str | Path) -> dict[str, Any]:
    """Headless: import the chosen lens + camera folders, enable the part on the face,
    set the field (fixed-magnification lenses are already mounted at their working
    distance by the bugs/0656 law; variable lenses solve the FOV to the face +5%),
    and save the layout."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    if not choice.lens_folder or not Path(choice.lens_folder).exists():
        raise FileNotFoundError(f"{choice.face}: lens folder unknown for {choice.lens}")
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    report: dict[str, Any] = {"face": choice.face, "layout": str(out_path)}
    try:
        model = editor.import_machine_vision_lens_from_folder(str(choice.lens_folder))
        report["lens_effl"] = getattr(model, "effl", None)
        if choice.camera_folder and Path(choice.camera_folder).exists():
            imported = editor.import_vendor_camera_from_folder(str(choice.camera_folder), refresh_open_3d=False)
            report["camera"] = getattr(imported, "name", None)
        else:
            report["camera"] = None
            report.setdefault("notes", []).append("camera folder unknown -- sensor not coupled")
        spec = normalize_inspection_part_spec(part_spec)
        spec["enabled"] = True
        spec["active_face"] = choice.face
        editor.set_inspection_part_spec(spec)
        reg = None
        try:
            reg = editor._lens_datasheet_wd_registration()
        except Exception:
            reg = None
        if reg and reg.get("fixed_magnification"):
            report["mode"] = "fixed-magnification (mount law)"
            report["wd_mismatch"] = reg.get("mismatch")
        else:
            solved, msg = editor.solve_fov_to_inspection_face()
            report["mode"] = "solved FOV to face" if solved else "FOV solve refused"
            report["solve_message"] = str(msg)[:160]
        editor._write_layout_file(Path(out_path))
        report["rows"] = len(editor.rows)
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return report


def solve_and_build_cell(
    part_spec: dict[str, Any],
    defect_mm: float,
    out_dir: str | Path,
    *,
    px_per_defect: float = 3.0,
    margin: float = 0.05,
    wd_min_mm: float | None = None,
    name: str = "cell",
    progress=None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Solve every face, build one layout per opposite-face pair, write the cell file.
    Returns (cell spec, report)."""
    from KrakenOS.UI.services.inspection_cell import normalize_cell_spec, save_cell

    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    choices = solve_cell_stations(part_spec, defect_mm, px_per_defect=px_per_defect, margin=margin, wd_min_mm=wd_min_mm)
    stations: dict[str, dict[str, Any]] = {}
    report: dict[str, Any] = {"choices": choices, "built": [], "errors": []}
    for a, b in FACE_PAIRS:
        choice = choices.get(a)
        if choice is None:
            report["errors"].append(f"{a}/{b}: no candidate")
            continue
        if not choice.passes:
            report["errors"].append(f"{a}/{b}: best candidate does not fit ({'; '.join(choice.reasons)}) -- built anyway for inspection")
        layout = out / f"{name}_{a}.py"
        if progress:
            try:
                progress(f"building {a}/{b} station: {choice.camera} + {choice.lens}")
            except Exception:
                pass
        try:
            built = build_station_layout(choice, part_spec, layout)
            report["built"].append(built)
            stations[a] = {"layout": str(layout), "enabled": True}
            stations[b] = {"layout": str(layout), "enabled": True}
        except Exception as exc:
            report["errors"].append(f"{a}/{b}: build failed: {exc}")
    cell = normalize_cell_spec({"part": dict(normalize_inspection_part_spec(part_spec), enabled=True), "stations": stations})
    cell_path = save_cell(out / name, cell)
    report["cell_path"] = str(cell_path)
    return cell, report
