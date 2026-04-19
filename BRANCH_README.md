# `nonseq-display-refactor` Branch

This branch extends upstream KrakenOS with a substantial set of new features,
performance improvements, and bug fixes.  The sections below summarise every
major change relative to `main`.

---

## 1. Interactive Layout Editor (`KrakenOS/UI/layout_editor.py`)

A full-featured, tkinter-based graphical layout editor (~12 800 lines) that
brings a Zemax-style desktop workflow to KrakenOS:

- **Surface table** — spreadsheet-style grid for editing radii, thicknesses,
  diameters, glasses, and surface types.  Supports undo/redo.
- **Live 2-D layout plot** — embedded matplotlib canvas with traced ray fans,
  surface curves, and labels; updates automatically on table edits.
- **Preset library** — ships with 10 starter layouts (see below) that can be
  loaded from `KrakenOS/common_optical_layouts/`.
- **Analysis panes** — spot diagrams, polychromatic RMS spot size, MTF
  (geometric and diffraction-based), wavefront error, and Seidel sums, all
  computed in background workers.
- **Optimisation integration** — built-in merit function editor with operand
  and variable pickers, bounds, and parallel SciPy / pygmo backends.
- **Folded system support** — mirrors are displayed with correct AxisMove=2
  geometry; the editor handles coordinate breaks transparently.
- **CAD overlay** — load a STEP file outline alongside the optical layout for
  mechanical-fit checks (see `tools/cad_*` helpers).
- **Snapshot export** — render the current layout to a standalone PNG.
- **State persistence** — the editor saves and restores session state (last
  file, column widths, field settings) across launches.

---

## 2. Scene-Bundle Display Pipeline (`KrakenOS/UI/`)

The 2-D layout rendering was refactored from a monolithic function into a
clean three-stage pipeline with no cross-dependencies on VTK or tkinter:

| Module               | Responsibility |
|----------------------|----------------|
| `scene_geometry.py`  | Pure dataclasses (`SurfaceCurve3D`, `RayPath3D`, `PlaneMarker`, `SceneBundle`, `ProjectedScene2D`) — no rendering code. |
| `scene_builder.py`   | Converts KrakenOS tracing results and surface descriptions into a `SceneBundle`.  No matplotlib dependency. |
| `scene_projector.py` | Projects world-space 3-D geometry to 2-D display coordinates. |
| `scene_renderer_2d.py` | Renders a `ProjectedScene2D` onto a matplotlib `Axes`. |

Benefits:
- Each stage is independently testable.
- Renderers other than matplotlib (e.g. SVG, WebGL) can consume the same
  `SceneBundle` without touching builder logic.
- Folded (mirror) systems and off-axis layouts are handled correctly via the
  `AxisMove=2` coordinate transforms extracted from `TRANS_2A`.

---

## 3. GPU-Accelerated Ray Tracing (`KrakenOS/gpu_backend.py`, `KrakenSys.py`)

- **`gpu_backend.py`** — provides a unified array namespace (`xp`) that
  resolves to CuPy when a CUDA GPU is available and falls back to NumPy
  transparently.  Includes NixOS-specific CUDA library pre-loading.
- **`system.BatchTrace()`** — new method on `KrakenSys.system` that traces N
  rays simultaneously.  Coordinate transforms, Newton-Raphson intersection,
  surface normals, and Snell's law all run on `xp`.  Per-ray results are
  transferred to CPU for storage.
- **`raykeeper.batch_push()`** — bulk result ingestion that bypasses the
  per-ray `push()` round-trip, eliminating ~60 attribute accesses per ray.
- **`PhysicsClass.batch_snell_refraction()`** — vectorised Snell's law for
  the GPU path.
- **`HitOnSurf` GPU path** — surface intersection solver uses `xp` arrays.
- **`PSFCalc` refactor** — the PSF and diffraction MTF pipeline was
  streamlined and can optionally use the GPU for FFT-heavy work.

---

## 4. Optimisation Framework (`KrakenOS/Optimization/`)

A new `KrakenOS.Optimization` package that plugs directly into the layout
editor or can be used standalone:

| File            | Purpose |
|-----------------|---------|
| `variables.py`  | `OpticalVariable` — wraps surface index + attribute name + bounds. |
| `operands.py`   | Concrete operands: `SpotRMSOperand`, `EffectiveFocalLengthOperand`, `MagnificationOperand`, `MTFAtFrequencyOperand`, `WavefrontRMSOperand`, `EntrancePupilPositionOperand`, `ExitPupilPositionOperand`, `ThicknessPenaltyOperand`, `InvalidTracePenaltyOperand`. |
| `merit.py`      | `MeritFunction` — weighted sum of operand results → scalar cost. |
| `evaluator.py`  | `MeritEvaluator` — rebuilds the KrakenOS system from a surface spec list, evaluates the merit function, and supports multiprocess parallel workers. |
| `specs.py`      | `OPERAND_REGISTRY` / `VARIABLE_REGISTRY` — declarative specs used by the editor UI to offer drop-down pickers. |
| `adapters/`     | `pygmo2_adapter.py` — wraps the evaluator as a pygmo2 UDP problem for global optimisation. |

---

## 5. Common Optical Layouts (`KrakenOS/common_optical_layouts/`)

Ten file-backed starter layouts, each a Python module exporting `TITLE`,
`SETTINGS`, and `SURFACES` dicts:

| Layout | Description |
|--------|-------------|
| `single_lens.py` | Plano-convex singlet |
| `doublet_lens.py` | Cemented achromatic doublet |
| `double_gauss_lens.py` | 6-element Double Gauss f/2.8 |
| `flat_mirror_45_deg.py` | 45-degree flat fold mirror |
| `double_mirror_fold.py` | Two-mirror periscope fold |
| `ideal_2f_lens.py` | Ideal thin lens at 2f conjugate |
| `machine_vision_150mm_measured.py` | 150 mm f/5.6 1X lens (measured radii) |
| `machine_vision_150mm_datasheet_1x.py` | 150 mm f/5.6 1X lens (datasheet, multi-element) |
| `machine_vision_150mm_datasheet_0_5x.py` | 150 mm lens at 0.5X configuration |
| `_template.py` | Skeleton for adding new presets |

---

## 6. CAD / Zemax Import Tools (`tools/`)

Command-line utilities for bridging mechanical CAD and Zemax data with
KrakenOS:

| Tool | Purpose |
|------|---------|
| `cad_inspect_step.py` | Parse a STEP file and list all solid bodies, spherical surfaces, and radii. |
| `cad_section_profile.py` | Cut a STEP solid at a given plane and export the 2-D profile. |
| `cad_detect_reference.py` | Detect datum planes, symmetry axes, and reference features in STEP geometry. |
| `cad_extract_outer_shell.py` | Extract the outer shell of a STEP assembly for overlay display. |
| `freecad_extract_edges.py` | Use FreeCAD headless to extract visible edges from a STEP model. |
| `inspect_zemax_archive.py` | Read a Zemax `.ZAR` archive, list contents, and extract the `.ZMX` prescription. |

---

## 7. Reproducible Development Environment (`devenv.nix`)

A [devenv](https://devenv.sh)-based Nix environment that provides:

- Python 3.13 with system-site-packages (`pythonocc-core`, `trimesh`,
  `meshio`, `tkinter`).
- Automatic virtualenv creation with all KrakenOS dependencies (NumPy, SciPy,
  matplotlib, PyVista, VTK, PyQt5, etc.).
- Optional GPU packages: `cupy-cuda12x`, NVIDIA CUDA runtime wheels, PyTorch.
- Correct `LD_LIBRARY_PATH` for NixOS OpenGL/CUDA driver libraries.
- `direnv` integration via `.envrc` for seamless shell activation.

---

## 8. Display & Rendering Fixes

- **`Display.py`** — positional `color` arguments changed to keyword
  arguments for PyVista 0.44+ compatibility.  Auto-selects a working
  matplotlib backend (`qtagg` > `tkagg` > `gtk3agg`) based on session type.
- **Folded layout geometry** — a long series of fixes for mirror surface
  orientation, tangent computation, and coordinate transforms when
  `AxisMove=2`:
  - Fixed `UnboundLocalError` in folded layout geometry for non-last mirrors.
  - Mirror normals now use reflection law instead of raw `TRANS_2A` local
    axes, giving correct surface line orientation.
  - `AxisMove=2` is enforced for all mirrors in runtime system builders.
- **2-D display refresh** — the refresh path was profiled and sped up by
  avoiding redundant redraws and caching projected geometry.

---

## 9. PSF & MTF Improvements

- **Finite-conjugate diffraction MTF** — the `PSFCalc` module was fixed to
  handle finite-conjugate systems correctly (the working F/# was being
  computed from the wrong pupil).
- **PSFCalc refactor** — reduced code duplication, removed dead branches, and
  consolidated the Huygens and FFT paths.
- **PhaseCalc cleanup** — removed unused variables and simplified array
  indexing.

---

## 10. Example Compatibility

All 40+ example scripts under `KrakenOS/Examples/` were updated for Python
3.12+ / 3.13 compatibility:

- Replaced deprecated `np.float`, `np.int`, `np.complex` with built-in or
  `np.float64` equivalents.
- Fixed `matplotlib.use()` calls that break under headless / Wayland sessions.
- Removed tutorial asset files that were committed by mistake.

---

## 11. Miscellaneous

- **`PupilTool.py`** — additional guard for degenerate pupil calculations.
- **`WavefrontFit.py`** — robustness fixes for edge-case Zernike fits.
- **`SurfTools.py`** / `MathShapesClass.py` — minor numerical tweaks.
- **`TraceLoopTool.py`** — helper additions for batch field-point iteration.
- **`.gitignore`** — added devenv state directories and compiled caches.

---

## Quick Start

```bash
# Enter the devenv shell (requires Nix + direnv)
cd Kraken-Optical-Simulator
direnv allow   # or: devenv shell

# Launch the layout editor
python -m KrakenOS.UI.layout_editor

# Run an example
python KrakenOS/Examples/Examp_Doublet_Lens.py

# Use the optimiser from a script
from KrakenOS.Optimization import MeritEvaluator, MeritFunction
```
