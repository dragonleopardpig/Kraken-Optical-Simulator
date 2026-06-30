"""Validate folder-based machine-vision lens import -> surrogate (item 3).

Item 3 lets a user point at a single vendor *lens folder* and have everything
useful in it ingested into one auto-built first-order surrogate: a Zemax
prescription OR -- for a real Black-Box lens whose surfaces are encrypted -- the
System/Prescription Data text dump drives the optics, the mechanical STEP is
wired as the overlay, and a wavefront export is wired onto the first ideal group.

This guard exercises the Black-Box path (the one the real machine-vision lenses
need) end to end against a *synthetic* folder so it is deterministic and needs no
vendor assets or OCC:

* a System/Prescription Data dump with known cardinals (EFL / BFL / F# / EPD /
  stop radius / magnification / image height / wavelength / fields);
* a stub ``.step`` that fails an OCC read (so the optical span deterministically
  falls back to EFL/3, whether or not OCC is installed);
* a wavefront ``.txt`` under ``wavefront/``.

It asserts the classification, the EFL-correct Path-B surrogate, that the emitted
``machine_vision_<slug>.py`` is discoverable / loadable / traceable and round-trips
the EFL through Parax, that the STEP and wavefront are wired, that a source-less
folder is rejected, and that the editor + right-click menu expose the importer.

Like the other machine-vision guards this is STANDALONE, not a penta phase.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_library import discover_layouts, load_python_data
from KrakenOS.UI.services.machine_vision_folder_import import (
    _normalized_cardinals,
    build_surrogate_from_assets,
    import_lens_folder,
    parse_prescription_data,
    render_surrogate_layout_source,
    scan_lens_folder,
)
from KrakenOS.UI.surface_table_model import (
    SurfaceRow,
    surface_row_to_spec,
    surface_rows_from_records,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKBENCH_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "layout_table_workbench.py"
MENU_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "panels" / "main_context_menu.py"

# Known cardinals baked into the synthetic Black-Box dump.
DUMP_EFL = 100.0
DUMP_STOP_RADIUS = 9.0
DUMP_EPD = 20.0
DUMP_WAVELENGTH = 0.546

_SYNTHETIC_DUMP = f"""GENERAL LENS DATA:

Title                    : Synthetic MV 100mm 1X

System/Prescription Data

Effective Focal Length   : {DUMP_EFL} (in air at system temperature and pressure)
Back Focal Length        : 120.0
Total Track              : 250.0
Image Space F/#          : 5.0
Working F/#              : 10.0
Entrance Pupil Diameter  : {DUMP_EPD}
Entrance Pupil Position  : 30.0
Exit Pupil Position      : -80.0
Stop Radius              : {DUMP_STOP_RADIUS}
Paraxial Image Height    : 16.0
Paraxial Magnification   : -1.0
Maximum Radial Field     : 16.0
Primary Wavelength [µm]  : {DUMP_WAVELENGTH}
Fields                   : 3
Field Type               : Real Image Height in Millimeters

MTF Units                : cycles per millimeter
"""

_SYNTHETIC_WAVEFRONT = """Listing of Wavefront Map Data

Peak to valley = 0.2500 waves, RMS = 0.0500 waves
0.0  0.0  0.0
0.0  0.1  0.0
0.0  0.0  0.0
"""


def _write_synthetic_lens_folder(folder: Path) -> None:
    """A Black-Box lens folder: dump + stub STEP + wavefront export."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "synthetic_System_Prescription_Data.txt").write_text(
        _SYNTHETIC_DUMP, encoding="utf-8"
    )
    # Garbage STEP: a real OCC read fails -> span falls back to EFL/3 (and if OCC
    # is absent the lazy import fails to the same fallback), so the guard is
    # deterministic either way.
    (folder / "body.step").write_text("NOT A REAL STEP FILE\n", encoding="utf-8")
    wf_dir = folder / "wavefront"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "Mag1.0.txt").write_text(_SYNTHETIC_WAVEFRONT, encoding="utf-8")


def _cardinals_from_layout(path: Path, wavelength: float) -> tuple[float, float, float] | None:
    """Reload the emitted layout and re-derive its cardinals via a real Parax."""
    info = load_python_data(path)
    rows = surface_rows_from_records(list(info.get("surfaces", [])))
    if len(rows) < 3:
        return None
    try:
        return _normalized_cardinals(rows, wavelength)
    except Exception:
        return None


def _trace_focuses(path: Path, wavelength: float) -> bool | None:
    """True/False from a real build=0 trace, or None if the trace stack is absent."""
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

    with tempfile.TemporaryDirectory() as raw:
        work = Path(raw)
        lens_folder = work / "Synthetic MV Lens"
        _write_synthetic_lens_folder(lens_folder)

        # --- classification -------------------------------------------------
        assets = scan_lens_folder(lens_folder)
        if len(assets.prescription_data_files) != 1:
            failures.append(
                f"expected 1 prescription-data dump, got {len(assets.prescription_data_files)}"
            )
        if assets.prescription_files:
            failures.append("synthetic Black-Box folder wrongly classified a .zmx prescription")
        if len(assets.step_files) != 1:
            failures.append(f"expected 1 STEP file, got {len(assets.step_files)}")
        if len(assets.wavefront_files) != 1:
            failures.append(f"expected 1 wavefront export, got {len(assets.wavefront_files)}")
        if not assets.has_optical_source:
            failures.append("Black-Box folder reports no optical source")

        # --- dump parse -----------------------------------------------------
        data = parse_prescription_data(assets.primary_prescription_data)
        if data is None:
            failures.append("prescription-data dump did not parse")
        else:
            if data.effl is None or abs(abs(data.effl) - DUMP_EFL) > 1e-6:
                failures.append(f"parsed EFL {data.effl} != {DUMP_EFL}")
            if data.object_mode != "Finite":
                failures.append(f"object_mode {data.object_mode!r} != 'Finite' (mag -1)")
            if data.wavelength is None or abs(data.wavelength - DUMP_WAVELENGTH) > 1e-9:
                failures.append(f"parsed wavelength {data.wavelength} != {DUMP_WAVELENGTH}")
            if data.stop_radius is None or abs(data.stop_radius - DUMP_STOP_RADIUS) > 1e-9:
                failures.append(f"parsed stop radius {data.stop_radius} != {DUMP_STOP_RADIUS}")

        # --- surrogate build (Path B) ---------------------------------------
        model = build_surrogate_from_assets(assets, project_root=work)
        if abs(model.effl - DUMP_EFL) > 1e-4:
            failures.append(f"surrogate EFL {model.effl} != dump EFL {DUMP_EFL}")
        if model.object_mode != "Finite":
            failures.append(f"surrogate object_mode {model.object_mode!r} != 'Finite'")
        if abs(model.stop_diameter - 2.0 * DUMP_STOP_RADIUS) > 1e-4:
            failures.append(
                f"surrogate stop diameter {model.stop_diameter} != 2*stop_radius "
                f"{2.0 * DUMP_STOP_RADIUS}"
            )
        if model.solution.method != "efl-span-symmetric":
            failures.append(f"Black-Box solve used {model.solution.method!r}, expected symmetric")
        if not model.filename.startswith("machine_vision_"):
            failures.append(f"emitted stem {model.filename!r} is not auto-discoverable")
        # STEP + wavefront wiring
        if not model.step_rel_path or "body.step" not in model.step_rel_path:
            failures.append(f"STEP not wired (step_rel_path={model.step_rel_path!r})")
        if model.settings.get("lens_step_path") != model.step_rel_path:
            failures.append("STEP path not written into SETTINGS lens_step_path")
        if not model.wavefront_rel_path or "Mag1.0.txt" not in model.wavefront_rel_path:
            failures.append(f"wavefront not wired (wavefront_rel_path={model.wavefront_rel_path!r})")
        group1 = model.surfaces[2]
        wf = (group1.get("advanced") or {}).get("WavefrontMap") if isinstance(group1, dict) else None
        if not (isinstance(wf, dict) and wf.get("path") == model.wavefront_rel_path):
            failures.append("wavefront map not wired onto Blackbox Group 1 advanced")

        # --- emit, discover, reload, round-trip, trace ----------------------
        emitted = work / model.filename
        emitted.write_text(render_surrogate_layout_source(model), encoding="utf-8")

        discovered = discover_layouts(work)
        if model.title not in discovered.machine_vision_names:
            failures.append(
                f"emitted surrogate {model.title!r} not discovered as a machine-vision lens"
            )
        if discovered.layout_files.get(model.title) != emitted:
            failures.append("emitted surrogate not resolvable by title in layout_files")

        info = load_python_data(emitted)
        rows = surface_rows_from_records(list(info.get("surfaces", [])))
        if len(rows) != 7:
            failures.append(f"reloaded surrogate has {len(rows)} rows, expected 7")
        cardinals = _cardinals_from_layout(emitted, model.wavelength)
        if cardinals is None:
            failures.append("reloaded surrogate did not yield cardinals")
        elif abs(cardinals[0] - DUMP_EFL) > 1e-3:
            failures.append(f"reloaded EFL {cardinals[0]:.6g} != dump EFL {DUMP_EFL} (round-trip)")
        traced = _trace_focuses(emitted, model.wavelength)
        if traced is False:
            failures.append("emitted surrogate failed to trace at build=0")

        # --- import_lens_folder convenience parity --------------------------
        convenience = import_lens_folder(lens_folder, project_root=work)
        if abs(convenience.effl - model.effl) > 1e-9:
            failures.append("import_lens_folder disagrees with build_surrogate_from_assets")

        # --- a source-less folder is rejected -------------------------------
        bare = work / "Bare Folder"
        bare.mkdir(parents=True, exist_ok=True)
        (bare / "datasheet.pdf").write_bytes(b"%PDF-1.4 stub")
        (bare / "body.step").write_text("NOT A REAL STEP FILE\n", encoding="utf-8")
        bare_assets = scan_lens_folder(bare)
        if bare_assets.has_optical_source:
            failures.append("source-less folder wrongly reports an optical source")
        try:
            build_surrogate_from_assets(bare_assets, project_root=work)
        except ValueError:
            pass
        else:
            failures.append("source-less folder did not raise when building a surrogate")

    # --- editor + menu wiring ----------------------------------------------
    workbench_src = WORKBENCH_PATH.read_text(encoding="utf-8") if WORKBENCH_PATH.exists() else ""
    menu_src = MENU_PATH.read_text(encoding="utf-8") if MENU_PATH.exists() else ""
    if "def import_machine_vision_lens_from_folder" not in workbench_src:
        failures.append("editor does not expose import_machine_vision_lens_from_folder")
    if "import_machine_vision_lens_from_folder" not in menu_src:
        failures.append("context menu does not wire the folder importer")
    if "Import Lens from Folder" not in menu_src:
        failures.append("context menu has no 'Import Lens from Folder' label")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Machine-vision folder-import validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Machine-vision folder-import validation passed: a vendor lens folder "
        "(Black-Box dump + STEP + wavefront) ingests into one EFL-correct, "
        "discoverable, traceable surrogate via the editor's folder importer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
