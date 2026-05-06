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
- **Preset library** — ships with 38 loadable starter and diagnostic layouts loaded
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
  aspheres/Zernikes/safe custom sag presets/UDA/masks/CAD-STL paths, Advanced
  Surface editing, grating row additional settings, and measured error-map
  import.
- **Catalog import** — Edmund/Thorlabs-style stock lens catalogs, KrakenOS AGF
  glass browser, enhanced Zemax `.zmx` import preservation, recursive
  `attachment/zemax` example menu loading, and machine-vision presets.
- **Component table workflow** — the `Insert` menu splices common components,
  stock lenses, CAD/STL solids, and path-local optics below the table selection
  without overwriting source/field/pupil settings; the surface right-click menu
  exposes grouped convert/insert/shape/material/coating/geometry/element/
  diagnostics/advanced actions; uncommon row-shape fields such as conic `k`
  and `Axicon` live in `Advanced... -> Shape Params` while staying trace/export
  and optimizer compatible; optimization variables use a cell-local `V` marker
  instead of a whole-row color or star suffix; `Ctrl-C`/`Ctrl-V` copy and paste
  selected surfaces or grouped elements.
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

Thirty-eight loadable file-backed starter, catalog, and diagnostic layouts,
each a Python module exporting `TITLE`, `SETTINGS`, and `SURFACES` dicts:

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
| `beam_splitter_50_50_example.py` | Deterministic finite-plate Beam Splitter workflow with transmitted/reflected branches |
| `nonseq_scene_graph_example.py` | Non-sequential scene graph, grouped elements, SourceRnd source, and target selection |
| `branch_tree_diagnostics_example.py` | Non-sequential branch tree inspection and CSV export |
| `surface_shape_builder_example.py` | Shape Builder workflow for aspheres, safe custom sag, UDA, masks, and CAD/STL paths |
| `weighted_sourcernd_example.py` | `SourceRnd.fun` angular weighting through the Source panel |
| `gaussian_beam_abcd_example.py` | q-parameter Gaussian beam report starter layout |
| `wide_field_*_example.py` | Wide-field spot, PSF, illumination, and wavefront maps |
| `atmospheric_*_example.py` | Atmospheric dispersion and current-optics image residuals |
| `wavefront_*_example.py` | Zernike fit, Wavefront Function 3D OPD surface, wrapped phase, interferogram, and slope plots |
| `Examp_Zemax_Wavefront_Map_Import.py` | Standalone Zemax Wavefront Map text import and normalized-pupil sampling example |
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
| `KrakenOS/UI/zemax_wavefront.py` | Parse Zemax Wavefront Map text exports and sample them on KrakenOS normalized pupil coordinates for WFront comparison. |
| `python -m KrakenOS.UI.validate_zemax_wavefront_import` | Validate UTF-16 Zemax-like parsing, wavelength headers, sampling, orientation selection, and residual comparison. |

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
- **`Examp_Gaussian_Laser_Modes.py`** — astigmatic/elliptical Gaussian source
  helper and ABCD cavity eigenmode example.
- **`Examp_Beam_Splitter_50_50.py`** — direct API example for deterministic
  finite-plate beam-splitter branches and saved `BeamSplitter` metadata.

---

## 12. Phase 5 Core Exposure Status

Phase 1 through Phase 5 are complete at their planned UI/core-exposure scope.
The key result is that the UI now exposes the KrakenOS-specific "gems" that
were previously hidden in scripts or core attributes:

| KrakenOS core capability | Current UI status |
|--------------------------|-------------------|
| Exact sequential tracing | First-class layout/editor workflow |
| Non-sequential tracing | First-class at KrakenOS ordered scene-list scope, with `NsTraceLoop`, `NsLimit`, target surface, scene graph, branch tree, and ray/hit diagnostics |
| Coatings, polarization, and beam-splitter metadata | First-class analysis, metal CSV loading, per-surface summaries, Fresnel arrays in Ray Inspector, and a Beam Splitter row that spawns deterministic transmitted/reflected branches while retaining coating fallback data |
| SourceRnd and pupil models | First-class source/pupil controls including weighted SourceRnd, chief ray, r/theta, random disk, hexapolar, square, and fan patterns |
| Shape/custom surfaces | Shape Builder for asphere/Zernike/safe `ExtraData`/UDA/masks/CAD-STL paths, plus Advanced Surface preservation |
| Error maps | Import/clear/validate workflow and Phase 2 reporting |
| Glass/catalogs/Zemax | AGF glass browser, stock lens import, and enhanced `.zmx` preservation of conics/aspheres/coatings/fallback `n/V` data |
| Wavefront/Zernike/Seidel/paraxial | Plots, reports, CSV exports, matrix-chain diagnostics, and Zemax Wavefront Map residual comparison |
| Native optimization variables | UI marks bridge to native `surf.Var`/`VarBounds` for supported variables |

Manual cross-check: `docs/source/ui/phase5_manual_crosscheck.rst` maps the 2021
provisional manual topics to current Phase 5 UI coverage. No active Phase 1-5
blocker remains in that cross-check.

---

## 13. Phase 6 Non-Sequential-First Direction

The next roadmap track is documented in
`KRAKEN_UI_NONSEQUENTIAL_ARCHITECTURE.md`.

The intended architecture is:

- the UI is a KrakenOS scene/object editor;
- physical sources, beam splitters, detectors, tilted/folded optics, STL
  solids, masks, and path metadata are scene objects or scene metadata;
- exact sequential tracing remains supported, but it is the axial
  ordered-surface special case;
- KrakenOS-native state should be inspectable through the Scene Graph, Ray
  Inspector, Trace Path Inspector, reports, or CSV exports.

Current Phase 6 scope:

- the Display panel labels the selector as `Scene trace`;
- `Auto` now resolves to KrakenOS `NsTraceLoop` for physical sources, beam
  splitters, CAD/STL optical solids, off-axis/tilted geometry, target surfaces, and
  probabilistic non-sequential coating requests;
- the status bar shows the resolved scene trace badge, for example
  `Scene: Auto -> Non-Sequential Preview`;
- `File -> Import Optical CAD/STL Solid...` inserts a native `Solid_3d_stl` row
  with editable Material, Thickness, AxisMove, Tilt, and Decenter controls for
  arbitrary closed prism/solid meshes. STL is used directly; STEP/STP/IGES/IGS
  vendor CAD is meshed with `gmsh` into a cached STL, and the original CAD path
  is preserved as `OpticalSolidSourcePath`;
- `Actions -> Inspect Optical CAD/STL Solids` checks file-backed mesh rows for
  scale, topology, signed volume, and likely face winding before users trust
  arbitrary-prism ray steering;
- `Actions -> 3D Place/Orient Selected CAD/STL Solid` opens the current 3D view
  in placement mode for the selected solid row, including the legacy PyVista
  fallback. Users can rotate the mesh while watching it in 3D, fit mesh-local
  `+Z`, `+X`, or `+Y` onto layout `+Z`, centre X/Y, place the front face on the
  row plane, then close the 3D view or press `Done -> 2D` so the row
  `Tilt*`/`Desp*` values drive the 2D layout;
- vendor cube beam-splitter CAD, such as Edmund 68551 STEP/IGES, is useful for
  outer cube boundary/placement but is not by itself a full splitter optical
  prescription. Keep or insert a table `Beam Splitter` surface for the internal
  45 degree coating/path physics;
- tilted CAD/STL solids use the row `Glass` value for non-sequential entry/exit
  media even when the hit chooser reports a neighbouring AIR side. This keeps a
  dispersion-prism pose from tracing as `n=1 -> 1`;
- ordinary non-sequential traces now retain a terminal escape segment, making it
  visible when a prism sends rays away from the axial Image instead of implying
  that they stopped inside the STL;
- saved layouts can declare multiple physical scene sources through
  `SETTINGS["scene_sources"]`; each source traces as an independent emitter,
  renders as a 2D source marker, appears in the Non-Sequential Scene Graph, and
  stamps its own `SOURCE_ID`/`SOURCE_NAME` onto raykeeper records;
- `Actions -> Scene Source Manager...` and the Source-panel manager button edit
  those explicit scene sources, including source row order, without converting
  emitters into KrakenOS surface rows;
- beam-splitter path-component placement is available from the splitter row
  context menu. `Add component to transmitted/reflected path...` creates
  detector plane, aperture stop, thin lens, refractive surface, or mirror rows
  with computed global Tilt/Decenter plus preserved `Element` path metadata.
  The older detector shortcuts call the same helper;
- `KrakenOS/Examples/Examp_Phase6_Path_Component_Placement.py` demonstrates
  the path-placement helper headlessly, and
  `python -m KrakenOS.UI.validate_phase6_path_workbench` validates row pose and
  metadata for all supported single-row path components;
- `python -m KrakenOS.UI.validate_compact_shape_fields` validates that compact
  table columns still preserve KrakenOS conic/Axicon tracing and conic
  optimization support;
- explicit `Sequential` remains available for conventional ordered-surface
  lens design and regression comparison.

STL prism regression:

```bash
python -m KrakenOS.UI.validate_stl_prism_media
python -m KrakenOS.UI.validate_phase6_path_workbench
python -m KrakenOS.UI.validate_phase6_complete
```

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

## Next Work: Post-Phase-6 Propagation Refinement

Gaussian beam / laser propagation Tier A/B is implemented, deterministic beam
splitter branches are implemented, Phase 6 path-component placement is in
place, and the Phase 6 closure suite is available as
`python -m KrakenOS.UI.validate_phase6_complete`. The remaining work is
post-Phase-6 propagation refinement: folded/non-sequential Gaussian propagation
and full diffraction-style coherent recombination.

| Feature | Readiness | Why |
|---------|-----------|-----|
| Gaussian beam / laser propagation, Tier A/B | Implemented in this branch | `KrakenOS/GaussianBeam.py` consumes `ParaxMatrices()`; the UI has Gaussian waist or datasheet diameter/divergence input, a Gaussian source model, 2-D q-envelope overlay, report table, CSV export, cavity eigenmode seeding, and Python helpers for two-axis astigmatic/elliptical beams. |
| Beam splitter UI, metadata, and deterministic ray forking | Implemented in this branch | The surface table has a `Beam Splitter` type, right-click settings, validation, saved `BeamSplitter` metadata, generated coating fallback, deterministic `NsTrace` child paths, internal branch metadata in `raykeeper`, a finite-plate UI preset, a direct API example, and Sphinx docs. |
| Beam splitter Phase 2 source/path workflow | Complete at traced-path workbench scope | `BEAM_SPLITTER_PHASE2_PLAN.md` defines source-driven bundles, hidden irrelevant sequential inputs, path-aware element metadata, placement helpers for transmitted/reflected paths, path-aware analysis, and validation examples. Source authority now has physical origin/direction (`Source X/Y/Z`, `Source L/M/N`), collimated disk and Gaussian bundles, launch metadata in ray records, path labels, physical-path workflows, splitter-origin and traced-`BRANCH_PATH` component insertion for detector/aperture/thin-lens/refractive-surface/mirror rows, exact `branch_path` element metadata for nested splitter paths, `Actions -> Path Throughput Report` for path-power audits, path-filtered Spot/RMS/PSF/MTF detector-hit diagnostics and PSF/MTF CSV export, `DetMap` detector-plane power binning/CSV export, first `CohDet` ray-binned coherent detector sums plus CSV export, fixed detector-bin sampling, coating-table-derived deterministic split powers, Fresnel P/S-weighted deterministic split powers, branch-level Jones P/S and global polarization-vector metadata, and `KrakenOS.UI.validate_branch_analysis` plus `KrakenOS.UI.validate_phase6_path_workbench` regression checks alongside the `Analysis path` selector. |
| Coherent detector / Michelson analysis | Implemented at Phase 6 ray-bin scope | `Michelson Interferometer (Interferogram)` validates return paths, second splitter encounters, branch ancestry, OPD/phase metadata, detector-bin coherent field accumulation, and CSV export. The preset now uses an Edmund Optics 68551-sized 25 mm cube-beam-splitter primitive with non-refracting cube reference faces plus an internal `Beam Splitter` row for the optical prescription. Full diffraction propagation and Gaussian mode-overlap remain post-Phase-6 work. |
| Full field FFT propagation | Later | Useful for clipping, higher-order modes, and interference, but it should not block the lightweight Gaussian q-parameter feature. |

Folded scanner seed example:

- `Galvo F-Theta Laser Scanner` is available under Common Optical Layouts and
  `KrakenOS/Examples/Examp_Galvo_FTheta_Laser_Scanner.py`.
- It demonstrates the intended Phase 6 path-local workflow target: Gaussian
  source metadata, beam expander, 45 degree galvo fold mirror, the 50 mm
  F-theta lens transcribed from `attachment/F-theta.pdf` Figure 8, and scan plane.
- The preset uses a 1 mm / 2 mrad Gaussian source and an approximately 2x
  beam expander so the galvo/entrance-stop bundle stays compatible with the
  Figure 8 2 mm EPD.
- The extracted F-theta lens is also available as a standalone
  `F-Theta Lens 50mm Figure 8` common layout component. The source table's
  `K9` glass is mapped to bundled CDGM `H-K9L`.
- The galvo mirror `TiltX` table cell accepts scan lists such as
  `-50,-45,-40` or ranges such as `-50:-40:5`; these are displayed mirror
  slants and correspond to a conservative `-10,0,+10` degree optical scan.
  The Figure 8 full field is `-20,0,+20` degrees, entered as `-55,-45,-35`,
  because the 45 degree fold doubles mirror-slope changes.
- It remains a ray-layout proxy; validated folded Gaussian q/astigmatic state
  through tilted optics belongs to post-Phase-6 diffraction/oblique-Gaussian
  work.

### N1. Beam Splitter Surface Type

**Goal:** Add a `"Beam Splitter"` workflow that starts with a usable
deterministic reflected and transmitted child branches from one incident ray.

**Current state:**

- The UI has a `Beam Splitter` surface type and right-click settings.
- Saved layouts preserve a `BeamSplitter` dictionary and generated coating
  table. The loader also accepts earlier roadmap aliases such as `loss`,
  `transmittance`, and `max_split_depth`.
- `Beam Splitter 50/50 Example` is available under Common Optical Layouts and
  demonstrates a finite BK7 plate with a rear AIR face.
- `Michelson Interferometer (Ray Only)` is available under Common Optical
  Layouts and demonstrates source/object split, return mirrors, and the second
  splitter encounter without claiming coherent interference.
- `KrakenOS/Examples/Examp_Beam_Splitter_50_50.py` shows the direct API path.
- `KrakenOS/Examples/Examp_Beam_Splitter_Fresnel_Polarization.py` shows
  polarization-weighted Fresnel branch powers, branch Jones amplitudes, and
  global branch polarization vectors for pure P, equal P/S, and pure S inputs.
- `KrakenOS/Examples/Examp_Michelson_Interferometer.py` prints ray-only
  Michelson branch paths, powers, phase metadata, and optical path.
- `docs/source/manual/beam_splitters.rst` documents the workflow and future
  tilted/folded/non-sequential Gaussian work.
- `NsTraceLoop()` is reachable from the UI.
- Deterministic `BeamSplitter` mode records transmitted/reflected children;
  `energy_probability` remains available for legacy stochastic coating tests.
- Fresnel arrays (`RP`, `RS`, `TP`, `TS`, `TTBE`, `TT`) are visible in Ray
  Inspector, polarization analysis, and CSV export.
- Non-Sequential Scene Graph exposes source settings, grouped element nodes,
  CAD/STL rows, masks, coatings, and target selection.
- Trace Path Inspector displays and exports KrakenOS branch/hit records.

**Implemented core work:** `KrakenSys.system.NsTrace` now has an engine-level
queue for deterministic splitter children, and `raykeeper` stores branch IDs,
parent IDs, powers, phase metadata, labels, and source-ray identity.

Suggested surface metadata:

```python
{
    "surface": "Beam Splitter",
    "name": "50/50 coated front face",
    "diameter": 25.0,
    "thickness": 3.0,
    "glass": "BK7",
    "advanced": {
        "BeamSplitter": {
            "split_mode": "Deterministic paths",
            "reflectance": 0.5,
            "absorption": 0.0,
            "transmit_phase_deg": 0.0,
            "reflect_phase_deg": 180.0,
            "max_branch_depth": 8,
            "min_branch_power": 1e-3,
        }
    },
}
```

Implementation slices:

1. Done: add `"Beam Splitter"` as a UI surface type and persist its advanced
   settings.
2. Done: map splitter settings to a flat coating table so the current
   non-sequential `energy_probability` mode can choose reflected/transmitted
   paths stochastically.
3. Done: add branch-power/parent metadata to the core trace result path and
   raykeeper.
4. Done: implement deterministic reflected + transmitted branch spawning in
   `KrakenSys.system.NsTrace`.
5. Done: route the produced child branches through existing SceneBundle, Ray
   Inspector, and Trace Path Inspector records.
6. Done: add finite plate setup using front substrate glass/thickness plus a
   following rear AIR face.
7. Done: add path-filtered analysis controls and PSF/MTF CSV export so
   spot/PSF/MTF can use selected paths.
8. Done: add deterministic coating-table split mode so branch power follows
   coating R/A interpolation by wavelength and incidence angle.
9. Done: add scalar Fresnel P/S split mode so branch power follows KrakenOS
   core `RP`/`RS`/`TP`/`TS` coefficients weighted by
   `polarization_p_fraction`.
10. Done: carry normalized `BRANCH_JONES_P`/`BRANCH_JONES_S` plus
    `BRANCH_POLARIZATION_XYZ` and use the global vector in `CohDet`.
11. Done: add simple deterministic splitter retardance controls through
    `transmit_s_phase_deg` and `reflect_s_phase_deg`.
12. Later: add full coating-stack vector behavior, birefringence, and coherent
    ghost/interference behavior after the branch-power modes are validated.

Guardrails:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_branch_depth` | 8 | Maximum recursive splits per original ray |
| `max_total_branches` | 256 | Hard cap on total ray instances |
| `min_branch_power` | 1e-3 | Discard branches below this threshold |

Best reference: Raypier remains the strongest implementation reference for
deterministic child-ray creation. LightPipes becomes relevant only after
branches exist and coherent field recombination is needed.

The next implementation plan is documented in `BEAM_SPLITTER_PHASE2_PLAN.md`.
It keeps one scene table, adds source-driven ray bundles, assigns elements to
logical paths, and delays coherent interference until branch phase and OPL are
validated.

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
4. Done: Source panel `Gaussian beam` traces a representative 2-D disk ray
   bundle and overlays the 1/e^2 q-envelope in the 2-D layout.
5. Done: `Diameter + divergence` input back-calculates waist radius and waist
   location from manufacturer-style beam specifications.
6. Done: `Actions -> Gaussian Beam Report` provides a UI table and CSV export.
7. Done: Source/field/object/pupil controls that do not apply to the selected
   source mode are hidden while preserving their saved values.
8. Done: Python API for two-axis tangential/sagittal Gaussian beam propagation
   supports elliptical laser sources on the current centered ABCD path.
9. Done: Gaussian cavity eigenmode solver computes a self-consistent q mode
   from an ABCD round-trip matrix; the UI Gaussian Beam Report can seed itself
   from that eigenmode.
10. Later: add clipping/throughput estimates, higher-order mode/FFT
    propagation, and fully oblique astigmatic matrices on top of the
    deterministic non-sequential branch records.

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
- layout-defined multi-source scenes through `SETTINGS["scene_sources"]`, with
  `Multi-Source Illumination Example`,
  `KrakenOS/Examples/Examp_Multi_Source_Illumination.py`, and
  `python -m KrakenOS.UI.validate_multi_scene_sources`
- a documented source-row contract validated by
  `python -m KrakenOS.UI.validate_scene_source_row_contract`: physical
  `Illumination Source` entries are scene rows, not KrakenOS `surf` rows
- a source-aware `SceneRowMapping` bridge validated by
  `python -m KrakenOS.UI.validate_scene_row_mapping`; it preserves KrakenOS
  trace-surface indices while representing source-visible scene rows
- source-first row order for illumination workflows via
  `scene_row_order="before_object"`; the right-angle beam-splitter illumination
  layout uses this to model Source 1 before Object in the scene table
- `Actions -> Scene Source Manager...` adds, edits, deletes, duplicates, and
  reorders explicit physical emitters while preserving surface indices
- the main editable table renders physical sources as non-surface
  `Illumination Source` rows with source model/ray count while skipping them
  during prescription read-back; double-click or right-click a source row to
  open the manager
- Non-Sequential Scene Graph now has a `Scene row order` node plus scene row,
  table row, trace surface, and source ID columns so the mapping is inspectable
  alongside the visible table rows

Remaining optional refinement: direct in-cell editing of source-row fields in the
main table. The current safe workflow keeps source rows non-surface rows and
edits their parameters through Scene Source Manager.

### N4. Future Tilted/Folded/Non-Sequential Gaussian Optics

This should build on deterministic beam-splitter branches. The required state
model is per branch, not per surface list:

- local hit frame from incident direction, surface normal, and tangent basis
- separate tangential/sagittal ABCD updates for oblique astigmatism
- branch power, phase, optical path length, and cumulative coating/bulk loss
- branch pruning by `min_branch_power` and `max_branch_depth`
- coherent detector/recombination only after branch phase is trustworthy

Until that exists, Gaussian Beam Report remains a centered-paraxial laser tool.
It is correct for beam expanders and centered refractive systems, but it should
not be advertised as a Michelson/interferometer or tilted plate-splitter field
propagation engine.

### N5. Coherent Detector / Interference

**Goal:** Given deterministic beam-splitter branches, compute coherent
recombination at a detector:

```text
E(x,y) = sum(sqrt(P_branch) * exp(i * 2*pi/lambda * OPL_branch))
I(x,y) = |E(x,y)|^2
```

**Current state:** Phase 6 implements geometric coherent detector binning as
`CohDet`, `Michelson Interferometer (Interferogram)`, and
`KrakenOS/Examples/Examp_Michelson_Interferometer.py`. It validates
source/object split, two return paths, branch ancestry through the second
splitter encounter, power metadata, phase metadata, optical path output, and
detector-bin coherent field accumulation/export. It is not a diffraction or
Gaussian mode-overlap propagator.

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
| Mach-Zehnder | Two-path recombination with OPD-dependent contrast |
| Fabry-Perot | Airy-like transmission/ring behavior |

### Recommended Implementation Order

```text
N2a GaussianBeam q-parameter report     <- done
N2b Gaussian beam 2-D envelope overlay  <- done
N2c Astigmatic/cavity laser helpers     <- done
N1a Beam Splitter UI + persistence      <- done
N1b Deterministic branch queue          <- done
N1c Path-filtered analysis              <- throughput + Spot/RMS/PSF/MTF + DetMap + CohDet first slices done
N4  Folded/non-sequential Gaussian q    <- requires N1 branch state
N5a Ray-only Michelson geometry         <- done
N5b Coherent detector / Michelson demo  <- done at ray-bin scope
N6  Full field propagation              <- optional wave-optics tier
```

Practical recommendation: implement folded/non-sequential Gaussian `q` state
next if interferometer/laser work becomes the priority. The Beam Splitter UI
and deterministic branch records are now available, and Gaussian propagation
already has the centered ABCD foundation.

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
