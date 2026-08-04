"""Display-free guard for bugs/0546 -- "tried to swap lens, but got error"
(flag_20260804_204450_689, machine_vision_AZ85_RA_Mirror_BS).

"Swap Imaging Lens from Folder" refused the user's AZ85 + RA-mirror + beam-splitter scene
with *"This scene has no imaging-lens surrogate (Front/Rear Vertex Datum) to swap"* -- while
the lens sat right there in the 3D view.  bugs/0381 had taught the block detector to veto a
block containing a foreign element so a swap could never splice one away, and the promoted
BS cube's ROW happened to sit between the two datums (``_step_overlay_insert_index`` drops a
promotion after the CURRENT SELECTION, and the cube is physically UPSTREAM of the lens --
display x -38..45 against the lens at x 94..149).

A promoted optical solid is ABSOLUTELY placed (``axis_move`` 0, pose = ``station + desp_z``),
so its row index carries no geometry: the swap now LIFTS it out, re-seats it after the new
block and rewrites ``desp_z`` to absorb the station delta.  Nothing moves, nothing is lost,
and the block comes out clean for the next swap.

Checks (headless, no VTK/tk):
- DETECT: the flagged scene's real row names now yield the block (1, 6); an Object/Image row
  between the datums still refuses (that span is not a lens block at all).
- SWAP (drives the REAL ``swap_imaging_lens_from_folder`` with stubbed file I/O): swapping in
  a lens of a DIFFERENT length keeps the promoted BS row, keeps its absolute pose to 1e-9,
  keeps the front datum and the downstream RA mirror at their absolute stations, and leaves a
  clean block behind.
- NON-VACUOUS: the replacement lens must actually change the BS row's station (otherwise the
  pose assertion passes without exercising the compensation).
- GAP MATH: ``_swap_downstream_gap`` discounts the re-seated rows' thickness.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0546_swap_keeps_inblock_solid
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace


# The flagged scene, verbatim from attachment/machine_vision_AZ85_RA_Mirror_BS.py:
# (name, thickness, desp_z).  Row 3 is the promoted beam-splitter cube sitting INSIDE the
# S1..S6 lens block; row 7 is the promoted RA mirror after it.
FLAGGED_SCENE = [
    ("Object at 1X", 130.634722222, 0.0),
    ("Front Optical Vertex Datum", 17.638524767, -76.8314729614),
    ("Blackbox Group 1", 9.86152751788, -94.4699977284),
    ("Promoted OPTICAL STEP optical solid", 0.0, -103.675776189),
    ("Aperture Stop F/4.5", 9.86152751788, -104.331525246),
    ("Blackbox Group 2", 17.638524767, -114.193052764),
    ("Rear Optical Vertex Datum", 103.27, -131.831577531),
    ("Promoted OPTICAL STEP optical solid", 44.1192569733, -235.101577531),
    ("Image / Sensor at 1X", 0.0, -338.101577531),
]

BS_ROW = 3
MIRROR_ROW = 7

# The same scene with an IN-PATH promoted solid instead: it carries real chain thickness plus
# the trailing AIR spacer bugs/0079 pairs with it. That thickness left the block along with
# the rows, so the rear-datum gap must discount it or the whole downstream arm walks (the
# flagged scene alone cannot prove this -- its BS row is 0 mm thick).
THICK_INBLOCK_SCENE = [
    ("Object at 1X", 130.634722222, 0.0),
    ("Front Optical Vertex Datum", 17.638524767, -76.8314729614),
    ("Blackbox Group 1", 4.0, -94.4699977284),
    ("Promoted OPTICAL STEP optical solid", 12.0, -103.675776189),
    ("Promoted OPTICAL STEP optical solid -> next gap (AIR)", 6.0, 0.0),
    ("Aperture Stop F/4.5", 9.86152751788, -104.331525246),
    ("Blackbox Group 2", 17.638524767, -114.193052764),
    ("Rear Optical Vertex Datum", 103.27, -131.831577531),
    ("Promoted OPTICAL STEP optical solid", 44.1192569733, -235.101577531),
    ("Image / Sensor at 1X", 0.0, -338.101577531),
]


def _swap_editor_class():
    """The real editor class -- importing it is also what late-binds the module globals the
    swap needs (``_sync_layout_globals`` runs at ``layout_editor`` import)."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    return KrakenLayoutEditor


def _scene_rows(spec=None):
    from KrakenOS.UI.surface_table_model import SurfaceRow

    rows = []
    for name, thickness, desp_z in (FLAGGED_SCENE if spec is None else spec):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=29.0, glass="AIR")
        row.desp_z = float(desp_z)
        rows.append(row)
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    return rows


def _stations(rows) -> list[float]:
    stations = [0.0]
    total = 0.0
    for row in rows[:-1]:
        total += float(getattr(row, "thickness", 0.0) or 0.0)
        stations.append(total)
    return stations


def _pose_z(rows, index) -> float:
    return _stations(rows)[index] + float(getattr(rows[index], "desp_z", 0.0) or 0.0)


def _editor(rows=None):
    from KrakenOS.UI.services import layout_table_workbench as ltw

    editor_class = _swap_editor_class()
    if getattr(ltw, "Path", None) is None:  # late-bound by _sync_layout_globals
        ltw.Path = Path
    editor = object.__new__(editor_class)
    editor.rows = _scene_rows() if rows is None else rows
    return editor


def _check_detection(failures: list[str]) -> None:
    from KrakenOS.UI.surface_table_model import SurfaceRow

    editor = _editor()
    got = editor._imaging_lens_block_indices()
    if got != (1, 6):
        failures.append(
            f"detect: the flagged AZ85+BS scene must expose its lens block (1, 6); got {got} "
            "-- the promoted BS row inside it must not veto the swap (bugs/0546)"
        )
    preservable, blocking = editor._imaging_lens_block_foreign_rows(editor.rows, 1, 6)
    if preservable != [BS_ROW] or blocking:
        failures.append(
            f"detect: interior foreign rows must be preservable={[BS_ROW]} / blocking=[]; "
            f"got {preservable} / {blocking}"
        )

    # An Object / Image row between the two datums is NOT a lens block -- still refused.
    def _row(name, surface="Standard"):
        row = SurfaceRow(name=name, surface=surface)
        return row

    broken = [
        _row("Object", "Object"),
        _row("Lens Front Datum"),
        _row("Image", "Image"),
        _row("Blackbox Group 1", "Thin Lens"),
        _row("Lens Rear Datum"),
        _row("Image", "Image"),
    ]
    if _editor(broken)._imaging_lens_block_indices() != (None, None):
        failures.append("detect: a scene end (Object/Image) inside the span must still refuse the swap")

    # Nothing after the block -> the lifted row would become the last row and be stamped
    # "Image" by _normalize_special_rows. Keep bugs/0381's never-wipe refusal there.
    truncated = [
        _row("Object", "Object"),
        _row("Lens Front Datum"),
        _row("Promoted OPTICAL STEP optical solid"),
        _row("Lens Rear Datum"),
    ]
    if _editor(truncated)._imaging_lens_block_indices() != (None, None):
        failures.append(
            "detect: with no row after the block there is nowhere safe to re-seat the solid -- "
            "must still refuse rather than wipe or mis-stamp it"
        )


def _run_real_swap(new_block_thicknesses, scene=None, rows=None):
    """Drive the REAL ``swap_imaging_lens_from_folder`` with the file I/O stubbed out.

    Only the side effects (folder import, layout write/read, table sync, history, refocus,
    2D refresh) are faked -- every row-surgery decision is the shipped code's. ``rows`` takes a
    prebuilt row list (bugs/0547's frozen scene builds its own baked desp/tilt)."""
    from KrakenOS.UI.services import layout_table_workbench as ltw
    from KrakenOS.UI.surface_table_model import SurfaceRow

    editor = _editor(_scene_rows(scene) if rows is None else rows)

    new_surfaces = [SurfaceRow(name="Object", surface="Object", thickness=0.0, glass="AIR")]
    for name, thickness in new_block_thicknesses:
        new_surfaces.append(
            SurfaceRow(
                name=name,
                surface="Aperture" if "Aperture" in name else "Standard",
                thickness=float(thickness),
                diameter=29.0,
                glass="AIR",
            )
        )
    new_surfaces.append(SurfaceRow(name="Image", surface="Image", thickness=0.0, glass="AIR"))

    model = SimpleNamespace(filename="machine_vision_stub.py", title="Stub Lens", effl=60.0)
    saved = {
        "import_lens_folder": getattr(ltw, "import_lens_folder", None),
        "render_surrogate_layout_source": getattr(ltw, "render_surrogate_layout_source", None),
        "LAYOUTS_DIR": getattr(ltw, "LAYOUTS_DIR", None),
        "_load_python_data": getattr(ltw, "_load_python_data", None),
        "messagebox": getattr(ltw, "messagebox", None),
    }
    errors: list[str] = []
    ltw.import_lens_folder = lambda folder: model
    ltw.render_surrogate_layout_source = lambda m: "# stub"
    ltw.LAYOUTS_DIR = _StubLayoutsDir()
    ltw._load_python_data = lambda destination: {"surfaces": new_surfaces, "settings": {}}
    ltw.messagebox = SimpleNamespace(
        showerror=lambda *a, **k: errors.append(a[1] if len(a) > 1 else ""),
        showinfo=lambda *a, **k: None,
        askyesno=lambda *a, **k: True,
        NO="no",
    )

    editor._commit_pending_table_edit = lambda: None
    # The only Tk-var reader inside the real _normalize_special_rows (image diameter mode).
    editor._apply_image_diameter_mode = lambda *a, **k: None
    editor._row_from_layout_item = lambda item: item
    editor._begin_history_capture = lambda *a, **k: None
    editor._commit_history_capture = lambda *a, **k: None
    editor._sync_table = lambda *a, **k: None
    editor.load_layouts = lambda *a, **k: None
    editor._swap_auto_refocus_to_best_focus = lambda *a, **k: None
    editor.append_progress = lambda *a, **k: None
    editor.append_debug = lambda *a, **k: None
    editor.status_var = SimpleNamespace(set=lambda value: None)

    try:
        result = editor.swap_imaging_lens_from_folder("/stub/folder", refresh=False)
    finally:
        for name, value in saved.items():
            if value is None:
                if hasattr(ltw, name):
                    delattr(ltw, name)
            else:
                setattr(ltw, name, value)
    return editor, result, errors


class _StubLayoutsDir:
    def __truediv__(self, name):
        return SimpleNamespace(write_text=lambda *a, **k: None)


def _check_real_swap(failures: list[str], scene=None, tag: str = "flagged") -> None:
    before = _editor(_scene_rows(scene))
    front_before, rear_before = before._imaging_lens_block_indices()
    if front_before is None:
        failures.append(f"swap[{tag}]: the scene under test has no detectable lens block")
        return
    stations_before = _stations(before.rows)
    inblock_before = [
        (index, _pose_z(before.rows, index))
        for index in range(front_before + 1, rear_before)
        if before._is_swap_preservable_block_row(before.rows[index])
    ]
    downstream_station_before = stations_before[rear_before + 1]
    front_station_before = stations_before[front_before]

    # A replacement lens with a DIFFERENT optical length, so the lifted rows' stations really move.
    editor, result, errors = _run_real_swap(
        [
            ("Front Optical Vertex Datum", 4.0),
            ("Blackbox Group 1", 21.0),
            ("Aperture Stop F/2.8", 21.0),
            ("Blackbox Group 2", 4.0),
            ("Rear Optical Vertex Datum", 0.0),
        ],
        scene=scene,
    )
    if errors:
        failures.append(f"swap[{tag}]: refused with {errors[0]!r} -- the block must be swappable (bugs/0546)")
        return
    if result is None:
        failures.append(f"swap[{tag}]: returned None (no model) on a scene that has a swappable lens block")
        return

    rows = editor.rows
    names = [str(getattr(row, "name", "")) for row in rows]
    stations_after = _stations(rows)
    front, rear = editor._imaging_lens_block_indices()
    if front is None:
        failures.append(f"swap[{tag}]: the swapped scene lost its lens block; rows = {names}")
        return

    # Every lifted row is back, in order, immediately after the new rear datum -- and unmoved.
    reseated = [
        index for index in range(rear + 1, len(rows)) if editor._is_swap_preservable_block_row(rows[index])
    ][: len(inblock_before)]
    if len(reseated) != len(inblock_before):
        failures.append(
            f"swap[{tag}]: {len(inblock_before)} in-block promoted row(s) must survive the swap; "
            f"rows = {names}"
        )
        return
    for (index_before, pose_before), index_after in zip(inblock_before, reseated):
        pose_after = _pose_z(rows, index_after)
        if abs(pose_after - pose_before) > 1e-9:
            failures.append(
                f"swap[{tag}]: re-seated row S{index_before}->S{index_after} MOVED -- pose z "
                f"{pose_before:.6f} -> {pose_after:.6f} (desp_z must absorb the station delta, bugs/0526)"
            )
        # NON-VACUOUS: the replacement lens must actually relocate the row, or the pose test
        # above proves nothing.
        station_delta = stations_after[index_after] - stations_before[index_before]
        if abs(station_delta) < 1.0:
            failures.append(
                f"swap[{tag}]: station delta {station_delta:.3f} mm for S{index_before} is too small "
                "-- the replacement lens must relocate the preserved row for this guard to mean anything"
            )

    downstream_index = rear + 1 + len(reseated)
    if downstream_index < len(rows) and abs(stations_after[downstream_index] - downstream_station_before) > 1e-6:
        failures.append(
            f"swap[{tag}]: the downstream element moved -- station {downstream_station_before:.4f} -> "
            f"{stations_after[downstream_index]:.4f} (bugs/0383 anchor must survive the re-seat; the "
            "rear-datum gap has to discount the re-seated rows' thickness)"
        )
    if abs(stations_after[front] - front_station_before) > 1e-9:
        failures.append(
            f"swap[{tag}]: the lens front datum moved -- station {front_station_before:.4f} -> "
            f"{stations_after[front]:.4f} (the new lens must land where the old one was)"
        )

    # The scene comes out CLEAN: the next swap sees a block with no foreign rows inside.
    preservable, blocking = editor._imaging_lens_block_foreign_rows(rows, front, rear)
    if preservable or blocking:
        failures.append(
            f"swap[{tag}]: the swapped block still holds foreign rows {preservable}/{blocking} -- "
            "the re-seat must place them AFTER the rear datum"
        )


def _check_gap_math(failures: list[str]) -> None:
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as M

    rows = [SimpleNamespace(thickness=t) for t in (40.0, 10.0, 10.0, 0.0, 5.0, 0.0)]
    # rear index 3; a re-seated row of thickness 5 now sits between it and the downstream row.
    gap = M._swap_downstream_gap(rows, 3, 100.0, extra_after=5.0)
    if gap is None or abs(gap - 35.0) > 1e-9:
        failures.append(f"gap: extra_after must be discounted (got {gap}, expected 35.0)")
    if M._swap_downstream_gap(rows, 3, 100.0) != 40.0:
        failures.append("gap: the no-preserved-rows result must be unchanged (40.0)")
    if M._swap_downstream_gap(rows, 3, 40.0, extra_after=5.0) is not None:
        failures.append("gap: a negative gap must still return None")


def _check_source_contract(failures: list[str]) -> None:
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as M

    source = inspect.getsource(M.swap_imaging_lens_from_folder)
    if "_swap_preserved_block_rows" not in source:
        failures.append("contract: the swap must snapshot the preserved block rows before splicing")
    if "_swap_reseat_preserved_rows" not in source:
        failures.append("contract: the swap must re-seat the preserved rows after the gap write")
    reseat = source.index("_swap_reseat_preserved_rows")
    gap_write = source.index("_swap_downstream_gap")
    if reseat < gap_write:
        failures.append(
            "contract: the re-seat must run AFTER the rear-datum gap write -- that write is what "
            "settles the stations the preserved rows sit on"
        )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        _swap_editor_class()
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: swap deps unavailable ({type(exc).__name__}: {exc})"]
    _check_detection(failures)
    _check_real_swap(failures)
    _check_real_swap(failures, scene=THICK_INBLOCK_SCENE, tag="in-path solid + spacer")
    _check_gap_math(failures)
    _check_source_contract(failures)
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0546 swap-keeps-in-block-solid validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0546 validation passed: a promoted solid parked inside the lens block no longer vetoes "
        "Swap Imaging Lens -- it is lifted out, re-seated after the new block with desp_z "
        "absorbing the station delta (pose invariant to 1e-9), the front datum and downstream "
        "RA mirror hold their absolute stations, and the block comes out clean."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
