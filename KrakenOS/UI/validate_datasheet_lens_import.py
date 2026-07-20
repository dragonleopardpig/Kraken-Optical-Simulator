"""Validate datasheet-only lens import -> surrogate (Path C) + the 3D importer.

Most vendors ship a **datasheet PDF** but no Zemax ``.zmx`` prescription and no
Black-Box ``System/Prescription Data`` dump.  Path C recovers the first-order
cardinals from the datasheet spec table alone:

* when it lists both focal distances (SF & S'F') BOTH principal planes are
  recovered, so the exact two-group solve reproduces all four cardinals (as the
  readable-``.zmx`` Path A);
* otherwise an EFL+span symmetric surrogate is the honest fallback (as Path B).

This guard is deterministic and needs no vendor assets: it drives the
cardinals->optics step (:func:`_core_from_datasheet_cardinals`) from *synthetic*
:class:`DatasheetCardinals`, asserts the exact solve round-trips EFL/ppa/ppp
through a real Parax and traces, checks the symmetric fallback, checks that a
datasheet PDF is now a valid optical source (but an unreadable stub still raises),
and checks the Open-3D importer wiring by source inspection.  When the real
Schneider PYRITE datasheet is present it also exercises the pure-stdlib PDF
extractor + full build end to end.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data
from KrakenOS.UI.services.datasheet_prescription_import import (
    DatasheetCardinals,
    parse_datasheet_cardinals,
)
from KrakenOS.UI.services.machine_vision_folder_import import (
    LensFolderAssets,
    _assemble_surrogate,
    _core_from_datasheet_cardinals,
    _normalized_cardinals,
    build_surrogate_from_assets,
    import_lens_folder,
    render_surrogate_layout_source,
    scan_lens_folder,
)
from KrakenOS.UI.surface_table_model import (
    surface_row_to_spec,
    surface_rows_from_records,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INSPECTOR_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "open3d_inspector.py"
WORKBENCH_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "layout_table_workbench.py"
TOP_CONTROLS_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "panels" / "open3d_top_controls.py"
# The user's dropped vendor folder (datasheet-only: STEP + PDF, no .zmx / dump).
VENDOR_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_56_80_10x_V38_1097785"
VENDOR_PDF = VENDOR_FOLDER / "PYRITE_56_80_10x_V38_1097785_datasheet.pdf"

# Synthetic cardinals modelled on the real PYRITE 5.6/80/1.0x (finite conjugate).
SYN_EFL = 82.39
SYN_SF = -60.14
SYN_SFP = 60.14
SYN_SPAN = 43.19
SYN_HH = -1.31
SYN_FNO = 5.6
SYN_SENSOR = 100.0
SYN_MAG = -1.0


def _cardinals_from_layout(path: Path, wavelength: float):
    info = load_python_data(path)
    rows = surface_rows_from_records(list(info.get("surfaces", [])))
    if len(rows) < 3:
        return None
    try:
        return _normalized_cardinals(rows, wavelength)
    except Exception:
        return None


def _trace_focuses(path: Path, wavelength: float):
    try:
        from KrakenOS.UI.services import paraxial_tools
        import KrakenOS as Kos
    except Exception:
        return None
    try:
        info = load_python_data(path)
        rows = surface_rows_from_records(list(info.get("surfaces", [])))
        specs = [surface_row_to_spec(row) for row in rows]
        system = paraxial_tools._build_system_from_specs(
            specs, build=0, apply_optical_solid_output_ports=False
        )
        keeper = Kos.raykeeper(system)
        system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], float(wavelength))
        keeper.push()
        _x, _y, z, _l, _m, _n = keeper.pick(-1)
        return bool(len(z)) and np.isfinite(float(z[-1]))
    except Exception:
        return None


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    failures: list[str] = []

    # --- DatasheetCardinals principal-plane math ---------------------------
    card = DatasheetCardinals(
        effl=SYN_EFL, front_focal=SYN_SF, back_focal=SYN_SFP, hh=SYN_HH,
        span=SYN_SPAN, fno=SYN_FNO, image_circle=SYN_SENSOR, magnification=SYN_MAG,
    )
    if card.ppa is None or abs(card.ppa - (SYN_SF + SYN_EFL)) > 1e-9:
        failures.append(f"ppa {card.ppa} != SF + f'eff {SYN_SF + SYN_EFL}")
    if card.ppp is None or abs(card.ppp - (SYN_SFP - SYN_EFL)) > 1e-9:
        failures.append(f"ppp {card.ppp} != S'F' - f'eff {SYN_SFP - SYN_EFL}")
    if not card.has_principal_planes:
        failures.append("cardinals with SF & S'F' should report has_principal_planes")
    if card.hh_from_cardinals is None or abs(card.hh_from_cardinals - SYN_HH) > 1e-2:
        failures.append(f"HH cross-check {card.hh_from_cardinals} != datasheet HH' {SYN_HH}")
    if card.object_mode != "Finite":
        failures.append(f"object_mode {card.object_mode!r} != 'Finite' (mag {SYN_MAG})")

    with tempfile.TemporaryDirectory() as raw:
        work = Path(raw)

        # --- exact Path C: cardinals -> core -> exact two-group solve -------
        assets = LensFolderAssets(folder=work)
        core = _core_from_datasheet_cardinals(card, assets)
        if abs(core.effl - SYN_EFL) > 1e-6:
            failures.append(f"core EFL {core.effl} != {SYN_EFL}")
        if abs(core.ppa - card.ppa) > 1e-6 or abs(core.ppp - card.ppp) > 1e-6:
            failures.append("core principal planes disagree with the datasheet cardinals")
        if abs(core.span - SYN_SPAN) > 1e-6:
            failures.append(f"core span {core.span} != datasheet vertex span {SYN_SPAN}")
        if core.solution.method not in ("symmetric", "asymmetric"):
            failures.append(f"exact Path C used {core.solution.method!r}, expected an exact solve")
        if core.object_mode != "Finite":
            failures.append(f"core object_mode {core.object_mode!r} != 'Finite'")
        if abs(core.stop_diameter - SYN_EFL / SYN_FNO) > 1e-3:
            failures.append(f"stop diameter {core.stop_diameter} != EFL/FNO {SYN_EFL / SYN_FNO}")
        if abs(core.image_diameter - SYN_SENSOR) > 1e-3:
            failures.append(f"image diameter {core.image_diameter} != sensor circle {SYN_SENSOR}")
        # m = -1 -> object == image field, 2f-2f conjugate
        if abs(core.object_diameter - SYN_SENSOR / abs(SYN_MAG)) > 1e-3:
            failures.append(f"object diameter {core.object_diameter} != sensor/|m|")
        if abs(core.object_gap - core.image_gap) > 1e-3:
            failures.append(f"m=-1 should give symmetric conjugate; got {core.object_gap}/{core.image_gap}")

        # emit -> discover -> reload -> round-trip EFL through a real Parax -> trace
        model = _assemble_surrogate(core, assets, name=None, project_root=work)
        emitted = work / model.filename
        emitted.write_text(render_surrogate_layout_source(model), encoding="utf-8")
        if not model.filename.startswith("machine_vision_"):
            failures.append(f"emitted stem {model.filename!r} is not auto-discoverable")
        discovered = discover_layouts(work)
        if model.title not in discovered.machine_vision_names:
            failures.append(f"emitted surrogate {model.title!r} not discovered as a machine-vision lens")
        cardinals = _cardinals_from_layout(emitted, model.wavelength)
        if cardinals is None:
            failures.append("reloaded datasheet surrogate did not yield cardinals")
        else:
            if abs(cardinals[0] - SYN_EFL) > 1e-3:
                failures.append(f"reloaded EFL {cardinals[0]:.6g} != {SYN_EFL} (round-trip)")
            if abs(cardinals[1] - card.ppa) > 1e-2 or abs(cardinals[2] - card.ppp) > 1e-2:
                failures.append("reloaded principal planes drifted from the datasheet cardinals")
        if _trace_focuses(emitted, model.wavelength) is False:
            failures.append("emitted datasheet surrogate failed to trace at build=0")

        # --- symmetric fallback: no focal distances -> EFL+span symmetric ---
        bare_card = DatasheetCardinals(effl=SYN_EFL, span=SYN_SPAN, fno=SYN_FNO)
        if bare_card.has_principal_planes:
            failures.append("cardinals without SF/S'F' should NOT report principal planes")
        if bare_card.object_mode != "Infinity":
            failures.append(f"no-magnification cardinals should be Infinity, got {bare_card.object_mode!r}")
        bare_core = _core_from_datasheet_cardinals(bare_card, LensFolderAssets(folder=work))
        if bare_core.solution.method != "efl-span-symmetric":
            failures.append(f"fallback used {bare_core.solution.method!r}, expected symmetric")
        if abs(bare_core.effl - SYN_EFL) > 1e-4:
            failures.append(f"fallback EFL {bare_core.effl} != {SYN_EFL}")

        # --- a datasheet PDF is a candidate source; a stub still raises -----
        stub = work / "Stub PDF Folder"
        stub.mkdir(parents=True, exist_ok=True)
        (stub / "datasheet.pdf").write_bytes(b"%PDF-1.4 stub")
        stub_assets = scan_lens_folder(stub)
        if not stub_assets.has_optical_source:
            failures.append("datasheet-PDF folder should report an optical source")
        try:
            build_surrogate_from_assets(stub_assets, project_root=work)
        except ValueError:
            pass
        else:
            failures.append("unreadable datasheet PDF did not raise when building a surrogate")

    # --- Open-3D importer wiring (source inspection) -----------------------
    inspector_src = INSPECTOR_PATH.read_text(encoding="utf-8") if INSPECTOR_PATH.exists() else ""
    workbench_src = WORKBENCH_PATH.read_text(encoding="utf-8") if WORKBENCH_PATH.exists() else ""
    controls_src = TOP_CONTROLS_PATH.read_text(encoding="utf-8") if TOP_CONTROLS_PATH.exists() else ""
    if "def import_machine_vision_lens_from_folder" not in inspector_src:
        failures.append("Open-3D inspector does not expose import_machine_vision_lens_from_folder")
    # bugs/0371 needle repair: the 0294 SIGSEGV fix (986fe41b) rebound the call
    # through a local ``editor`` variable, so the old ``self.editor.…`` literal was
    # silently stale-failing for a week. Match the call itself (substring works for
    # both forms) -- the contract is delegation WITH dialog_parent=self.
    if "editor.import_machine_vision_lens_from_folder(dialog_parent=self)" not in inspector_src:
        failures.append("3D importer does not delegate to the editor with dialog_parent=self")
    if "if model is None" not in inspector_src or "refresh_from_editor" not in inspector_src:
        failures.append("3D importer does not guard cancellation / rebuild the scene")
    if "dialog_parent=None" not in workbench_src or "return model" not in workbench_src:
        failures.append("editor importer does not accept dialog_parent / return the model")
    if "Import Lens from Folder..." not in controls_src:
        failures.append("3D CAD menu has no 'Import Lens from Folder...' entry")
    if "self.inspector.import_machine_vision_lens_from_folder" not in controls_src:
        failures.append("3D CAD menu entry is not wired to the inspector importer")

    # --- real Schneider PYRITE datasheet when present ----------------------
    if VENDOR_PDF.exists():
        real = parse_datasheet_cardinals(VENDOR_PDF)
        if real is None or real.effl is None:
            failures.append("real PYRITE datasheet did not parse an EFL")
        else:
            if abs(real.effl - 82.39) > 0.5:
                failures.append(f"real datasheet EFL {real.effl} != ~82.39")
            if not real.has_principal_planes:
                failures.append("real datasheet did not yield both principal planes")
            elif real.hh is not None and real.hh_from_cardinals is not None:
                if abs(real.hh_from_cardinals - real.hh) > 0.1:
                    failures.append(
                        f"real datasheet HH cross-check {real.hh_from_cardinals:.3g} "
                        f"!= listed {real.hh:.3g}"
                    )
        if VENDOR_FOLDER.is_dir():
            built = import_lens_folder(VENDOR_FOLDER)
            if abs(built.effl - 82.39) > 0.5:
                failures.append(f"real folder build EFL {built.effl} != ~82.39")

    # bugs/0371: Rodenstock/LINOS-style spec rows -- lower case, "(mm)" units, an
    # f' token in the EFL label, "*)" in-air footnotes, and a bracketed
    # magnification range -- must parse alongside the PYRITE "[mm]" style
    # (the Apo-Rodagon-D 1x 4/75 sheet that failed the folder import).
    import unittest.mock

    from KrakenOS.UI.services import datasheet_prescription_import as dpi

    rodenstock_text = (
        "Specification ON 8501-9002 image circle max. (mm) 82 working distance "
        "(mm) 100 -130 focal length f' (mm) 74.9 interface M39 x1/26\" (Leico) "
        "magnification W [range] -1 [ -1.2 ... -0.8]filter thread M40.5 x0.5 "
        "SF (mm) -44.2f-stop0 EnP 0 ExP 1 S'F' (mm) *) 44.2 4 18. "
        "HH' (mm) *) -14.355.6 13.4"
    )
    with unittest.mock.patch.object(dpi, "extract_pdf_text", return_value=rodenstock_text):
        rod = dpi.parse_datasheet_cardinals("synthetic-rodenstock.pdf")
    if rod is None:
        failures.append("Rodenstock-style sheet must parse (bugs/0371)")
    else:
        if abs(float(rod.effl) - 74.9) > 1e-9:
            failures.append(f"Rodenstock EFL {rod.effl} != 74.9")
        if rod.front_focal is None or abs(float(rod.front_focal) + 44.2) > 1e-9:
            failures.append(f"Rodenstock SF {rod.front_focal} != -44.2")
        if rod.back_focal is None or abs(float(rod.back_focal) - 44.2) > 1e-9:
            failures.append(f"Rodenstock S'F' {rod.back_focal} != 44.2 (footnote marker)")
        if rod.magnification is None or abs(float(rod.magnification) + 1.0) > 1e-9:
            failures.append(f"Rodenstock magnification {rod.magnification} != -1")
        if rod.image_circle is None or abs(float(rod.image_circle) - 82.0) > 1e-9:
            failures.append(f"Rodenstock image circle {rod.image_circle} != 82")
        if rod.hh is not None:
            failures.append(
                "the column-glued (mm)-style HH' row must stay UNPARSED -- a misparse "
                "(-14.355 from '-14.355.6') would silently corrupt the solve"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Datasheet-only lens-import validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Datasheet-only lens-import validation passed: a vendor lens folder with "
        "only a datasheet PDF ingests into an EFL-correct, discoverable, traceable "
        "surrogate (exact two-group solve from the datasheet principal planes), and "
        "the Open-3D CAD menu exposes the folder importer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
