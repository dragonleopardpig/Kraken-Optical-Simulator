# `nonseq-display-refactor` Branch

This branch extends upstream KrakenOS with a substantial set of new features,
performance improvements, and bug fixes.  The sections below summarise every
major change relative to `main`.

---

## 1. Interactive Layout Editor (`KrakenOS/UI/layout_editor.py`)

A full-featured, tkinter-based graphical layout editor (~26 000 lines) that
brings a Zemax-style desktop workflow to KrakenOS:

- **Surface table** — spreadsheet-style grid for editing radii, thicknesses,
  diameters, glasses, and surface types.  Supports undo/redo.
- **Live 2-D layout plot** — embedded matplotlib canvas with traced ray fans,
  surface curves, and labels; refreshed explicitly via `Update` so expensive
  analysis does not rerun on every cell edit.
- **Preset library** — ships with 37 starter and diagnostic layouts loaded
  from `KrakenOS/common_optical_layouts/`.
- **Analysis panes** — spot diagrams, polychromatic RMS spot size, wide-field
  maps, PSF, MTF, illumination, atmospheric residuals, wavefront/Zernike
  diagnostics, field curvature/distortion, lateral color, polarization, and
  Seidel sums, with heavy computations running in background workers.
- **Optimisation integration** — built-in merit function editor with operand
  and variable pickers, bounds, and parallel SciPy / pygmo backends.
- **Folded system support** — mirrors are displayed with correct AxisMove=2
  geometry; the editor handles coordinate breaks transparently.
- **Non-sequential diagnostics** — explicit KrakenOS `NsTraceLoop()` preview,
  target-surface controls, `NsLimit`, probabilistic coating splits,
  non-sequential scene graph inspection, branch-tree inspection, and per-hit
  ray CSV export.
- **Shape / advanced surface workflows** — guided Shape Builder for
  aspheres/Zernikes/safe custom sag presets/UDA/masks/STL paths, Advanced
  Surface editing, grating row additional settings, and measured error-map
  import.
- **Catalog import** — Edmund/Thorlabs-style stock lens catalogs, KrakenOS AGF
  glass browser, enhanced Zemax `.zmx` import preservation, and machine-vision
  presets.
- **CAD overlay** — load a STEP file outline alongside the optical layout for
  mechanical-fit checks (see `tools/cad_*` helpers).
- **Snapshot export** — render the current layout to a standalone PNG.
- **State persistence and docs** — the editor saves/restores session state;
  provisional manual content has been converted to Sphinx source under
  `docs/source`.

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

## 3. Optional GPU / Vectorised Ray Tracing (`KrakenOS/gpu_backend.py`, `KrakenSys.py`)

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
- **`PSFCalc` / wavefront refactor** — the PSF and diffraction MTF pipeline
  was streamlined and can optionally use the GPU for FFT-heavy work.  CPU
  fallback remains the default safe path when CUDA/CuPy initialisation fails.

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

Thirty-seven file-backed starter, catalog, and diagnostic layouts, each a Python
module exporting `TITLE`, `SETTINGS`, and `SURFACES` dicts:

| Layout | Description |
|--------|-------------|
| `single_lens.py` | Plano-convex singlet |
| `doublet_lens.py` | Cemented achromatic doublet |
| `double_gauss_lens.py` | 6-element Double Gauss f/2.8 |
| `flat_mirror_45_deg.py` | 45-degree flat fold mirror |
| `double_mirror_fold.py` | Two-mirror periscope fold |
| `ideal_2f_lens.py` | Ideal thin lens at 2f conjugate |
| `machine_vision_150mm_measured.py` | 150 mm f/5.6 1X lens (measured radii) |
| `machine_vision_150mm_datasheet_1x.py` | 150 mm f/5.6 1X lens (datasheet first-order surrogate) |
| `machine_vision_150mm_datasheet_0_5x.py` | 150 mm lens at 0.5X configuration (first-order surrogate) |
| `coating_polarization_example.py` | Fold mirror and coating/polarization analysis workflow |
| `nonseq_scene_graph_example.py` | Non-sequential scene graph, grouped elements, SourceRnd source, and target selection |
| `branch_tree_diagnostics_example.py` | Non-sequential branch tree inspection and CSV export |
| `surface_shape_builder_example.py` | Shape Builder workflow for aspheres, safe custom sag, UDA, masks, and STL paths |
| `weighted_sourcernd_example.py` | `SourceRnd.fun` angular weighting through the Source panel |
| `gaussian_beam_abcd_example.py` | q-parameter Gaussian beam report starter layout |
| `wide_field_*_example.py` | Wide-field spot, PSF, illumination, and wavefront maps |
| `atmospheric_*_example.py` | Atmospheric dispersion and current-optics image residuals |
| `wavefront_*_example.py` | Zernike fit, wrapped phase, interferogram, and slope plots |
| `native_variable_breadth_example.py` | Broader native `surf.Var` optimization-variable coverage |
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

- **Finite-conjugate diffraction MTF** — the `PhaseCalc.Phase2()` path and
  UI selection logic were fixed so finite-object systems use per-pupil-ray
  source points and directions instead of a shared chief-ray direction.
- **PSFCalc refactor** — reduced code duplication, removed dead branches, and
  consolidated the Huygens and FFT paths.
- **PhaseCalc cleanup** — removed unused variables and simplified array
  indexing.

---

## 10. Example Compatibility

Example scripts under `KrakenOS/Examples/` were updated for Python 3.12+ /
3.13 compatibility where needed:

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
- **Sphinx docs** — `KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf`
  has been converted into curated Sphinx source pages in `docs/source`, with a
  Phase 5 manual cross-check.
- **`Examp_Gaussian_Beam_Propagation.py`** — direct API example for the
  q-parameter laser propagation helper.

---

## 12. Phase 5 Core Exposure Status

Phase 1 through Phase 5 are complete at their planned UI/core-exposure scope.
The key result is that the UI now exposes the KrakenOS-specific "gems" that
were previously hidden in scripts or core attributes:

| KrakenOS core capability | Current UI status |
|--------------------------|-------------------|
| Exact sequential tracing | First-class layout/editor workflow |
| Non-sequential tracing | First-class at KrakenOS ordered scene-list scope, with `NsTraceLoop`, `NsLimit`, target surface, scene graph, branch tree, and ray/hit diagnostics |
| Coatings and polarization | First-class analysis, metal CSV loading, per-surface summaries, and Fresnel arrays in Ray Inspector |
| SourceRnd and pupil models | First-class source/pupil controls including weighted SourceRnd, chief ray, r/theta, random disk, hexapolar, square, and fan patterns |
| Shape/custom surfaces | Shape Builder for asphere/Zernike/safe `ExtraData`/UDA/masks/STL paths, plus Advanced Surface preservation |
| Error maps | Import/clear/validate workflow and Phase 2 reporting |
| Glass/catalogs/Zemax | AGF glass browser, stock lens import, and enhanced `.zmx` preservation of conics/aspheres/coatings/fallback `n/V` data |
| Wavefront/Zernike/Seidel/paraxial | Plots, reports, CSV exports, and matrix-chain diagnostics |
| Native optimization variables | UI marks bridge to native `surf.Var`/`VarBounds` for supported variables |

Manual cross-check: `docs/source/ui/phase5_manual_crosscheck.rst` maps the 2021
provisional manual topics to current Phase 5 UI coverage. No active Phase 1-5
blocker remains in that cross-check.

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

---

## Next Work: Beam Splitters And Laser Propagation

The branch is now ready to start beam-splitter and laser-propagation work, but
the two features are not equally ready:

| Feature | Readiness | Why |
|---------|-----------|-----|
| Gaussian beam / laser propagation, Tier A | Implemented in this branch | `KrakenOS/GaussianBeam.py` consumes `ParaxMatrices()` and `Actions -> Gaussian Beam Report` exposes q-parameter tables with CSV export. |
| Beam splitter deterministic ray forking | Ready to design and start, but still a core engine change | UI diagnostics, scene graph, ray picking, Fresnel arrays, and branch inspectors are ready. The missing piece is a deterministic branch queue in the tracer. |
| Coherent interference / Michelson analysis | Not first | Requires deterministic beam-splitter branches and branch powers before coherent recombination is meaningful. |
| Full field FFT propagation | Later | Useful for clipping, higher-order modes, and interference, but it should not block the lightweight Gaussian q-parameter feature. |

### N1. Beam Splitter Surface Type

**Goal:** Add a `"Beam Splitter"` surface type that creates both reflected and
transmitted child branches from one incident ray, with user-controlled power
split and optional Fresnel/polarization-derived splitting.

**Current state after Phase 5:**

- `NsTraceLoop()` is reachable from the UI.
- `energy_probability` already exercises stochastic reflection/transmission,
  but it chooses one path rather than both.
- Fresnel arrays (`RP`, `RS`, `TP`, `TS`, `TTBE`, `TT`) are visible in Ray
  Inspector, polarization analysis, and CSV export.
- Non-Sequential Scene Graph exposes source settings, grouped element nodes,
  STL rows, masks, coatings, and target selection.
- Branch Tree Inspector displays and exports KrakenOS branch/hit records.

**Missing core work:** deterministic branch spawning. KrakenOS still needs an
engine-level queue that can carry child rays, branch IDs, parent IDs, and
branch powers through a non-sequential trace.

Suggested surface metadata:

```python
{
    "surface": "Beam Splitter",
    "name": "50/50 splitter",
    "diameter": 25.0,
    "glass": "AIR",
    "advanced": {
        "BeamSplitter": {
            "mode": "ideal",          # later: "fresnel", "plate"
            "reflectance": 0.5,
            "transmittance": 0.5,
            "loss": 0.0,
            "max_split_depth": 4,
            "min_branch_power": 1e-3,
        }
    },
}
```

Implementation slices:

1. Add `"Beam Splitter"` as a UI surface type and persist its advanced settings.
2. Add branch-power/parent metadata to the core trace result path and raykeeper.
3. Implement deterministic reflected + transmitted branch spawning in
   `KrakenSys.system.NsTrace`.
4. Route the produced child branches through existing SceneBundle, Ray
   Inspector, and Branch Tree Inspector records.
5. Add branch-filtered analysis controls so spot/PSF/MTF can use selected arms.
6. Add Fresnel/polarization modes after the ideal 50/50 mode is validated.
7. Add plate splitter and ghost-reflection behavior last.

Guardrails:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_split_depth` | 4 | Maximum recursive splits per original ray |
| `max_total_branches` | 256 | Hard cap on total ray instances |
| `min_branch_power` | 1e-3 | Discard branches below this threshold |

Best reference: Raypier remains the strongest implementation reference for
deterministic child-ray creation. LightPipes becomes relevant only after
branches exist and coherent field recombination is needed.

### N2. Gaussian Beam / Laser Propagation

**Goal:** Add laser propagation for Gaussian beams using the complex beam
parameter `q`, with beam radius, waist, divergence, Rayleigh range, wavefront
curvature, M², and optional tangential/sagittal separation.

**Readiness:** Tier A is implemented in this branch. Earlier notes said
KrakenOS did not expose surface-by-surface ABCD matrices; that is no longer
true. Phase 5 added `Actions -> Paraxial Matrix Report`, backed by
`system.ParaxMatrices()`, and the Gaussian beam tracker now consumes the same
matrix chain.

Tier A design:

```text
q_out = (A*q_in + B) / (C*q_in + D)
w(z)  = sqrt(-lambda / (pi * Im(1/q)))
R(z)  = 1 / Re(1/q)
```

Implementation slices:

1. Done: `KrakenOS/GaussianBeam.py` adds dataclasses for input waist,
   wavelength, M², and optional input refractive index.
2. Done: `propagate_gaussian_beam()` consumes `ParaxMatrices()` operations and
   propagates `q` at every surface/refraction/translation step.
3. Done: the returned table includes beam radius, wavefront curvature, Gouy
   phase, waist location, Rayleigh range, divergence, and stability flags.
4. Done: `Actions -> Gaussian Beam Report` provides a UI table and CSV export.
5. Next: overlay the beam envelope on the 2-D layout.
6. Next: add tangential/sagittal separation and cavity round-trip/eigenmode
   solving after single-pass propagation has been exercised.

References:

- `~/Projects/GaussianBeam`: best single reference for q-parameter mechanics,
  M², astigmatic beams, cavity eigenmodes, waist fitting, and overlap integral.
- `rezonator2`: strong reference for caustics, stability maps, and T/S
  separation.
- `simcav`: lightweight Python ABCD reference.

### N3. Illumination Source Workflow

This is mostly done for the Phase 5 scope. The UI already exposes:

- random circle, square, line, and point-cone sources
- source origin, radius, cone angle, ray count, seed, and power
- `SourceRnd.fun` angular weighting presets: uniform solid angle,
  cosine-weighted, Gaussian center, and edge-weighted
- source throughput and illumination maps

Remaining optional refinement: add a physical `"Source"` row type if users need
sources to move/reorder as table elements rather than live in the Source panel.
This is a UI ergonomics feature, not a blocker for laser propagation.

### N4. Coherent Detector / Interference

**Goal:** Given deterministic beam-splitter branches, compute coherent
recombination at a detector:

```text
E(x,y) = sum(sqrt(P_branch) * exp(i * 2*pi/lambda * OPL_branch))
I(x,y) = |E(x,y)|^2
```

Prerequisites:

1. Beam-splitter branch powers and parent/child IDs from N1.
2. A detector grid that bins arriving ray branches by pixel.
3. Optional Gaussian q/field information from N2 if mode overlap or realistic
   laser beam sizes are required.

Validation targets:

| Configuration | Expected pattern |
|---------------|------------------|
| Michelson, plane mirrors, on-axis | Uniform intensity modulated by OPD scan |
| Michelson, one mirror tilted | Linear spatial fringes |
| Mach-Zehnder | Two-arm recombination with OPD-dependent contrast |
| Fabry-Perot | Airy-like transmission/ring behavior |

### Recommended Implementation Order

```text
N2a GaussianBeam q-parameter report     <- smallest, ready now
N2b Gaussian beam 2-D envelope overlay  <- uses N2a results
N1a Beam Splitter UI + persistence      <- small setup step
N1b Deterministic branch queue          <- core engine change
N1c Branch-filtered analysis            <- uses existing inspectors
N4  Coherent detector / Michelson demo  <- requires N1 branch powers
N2c Full field propagation              <- optional wave-optics tier
```

Practical recommendation: implement `GaussianBeam` first, then beam splitter.
Gaussian propagation now has the cleanest foundation because the ABCD matrix
chain exists. Beam splitter is also ready to start, but it should be planned as
a core tracer change rather than a UI-only feature.

### Reference Projects Surveyed

| Project | Key contribution to the next phase |
|---------|------------------------------------|
| Raypier (`~/Projects/raypier_optics`) | Deterministic non-sequential branch spawning, beam-splitter cubes, polarization-aware tracing, Gaussian/gausslet E-field evaluation, VTK display patterns |
| LightPipes | Coherent field representation, Fresnel/ABCD propagation, Gaussian/Hermite/Laguerre sources, interference recombination |
| `~/Projects/GaussianBeam` | q-parameter implementation, M², T/S beams, cavity eigenmode solving, waist fitting, overlap integral |
| rezonator2 | ABCD/q propagation, stability maps, caustics, tangential/sagittal separation |
| simcav | Lightweight Python ABCD and cavity constraints |
| SeaRay | Mixed ray/paraxial/field architecture and accelerator-aware kernel dispatch |
| pyLaserPulse | Source/spectral model inspiration, not a free-space layout engine |
| Optiland | GUI ergonomics, analysis coverage, optimization workflow, backend separation |

Notes:

- `raypier_optics` is GPL-licensed like KrakenOS, so it is safer to consult or
  port from than AGPL sources, subject to normal attribution and compatibility
  checks.
- LightPipes is the right conceptual model for coherent fields, but it does not
  replace the need for KrakenOS branch spawning.
