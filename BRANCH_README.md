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

---

## Future Work

The following features are planned for future development.  Each section
describes the requirement, the current state of the KrakenOS codebase relative
to it, and the design approach informed by surveying six open-source laser /
optical simulation libraries (LightPipes, beamshapy, rezonator2, simcav,
SeaRay, pyLaserPulse).

### F1. Beam Splitter Surface Type

**Requirement:** Add a `"Beam Splitter"` surface type that deterministically
produces both a reflected and a transmitted ray from a single incident ray,
with user-controlled power split (R + T + L = 1).

**Current state:** The tracer is single-branch — one ray in, one ray out.
The non-sequential mode (`NsTrace`) has a Monte Carlo `energy_probability`
flag that *stochastically* chooses reflection or transmission (never both).
Fresnel coefficient math already exists in the physics layer but is used
only for energy bookkeeping, not for ray forking.  A detailed implementation
plan exists in `BEAM_SPLITTER_IMPLEMENTATION_PLAN.org` (586 lines, 6 phases).

**Design approach:**

The core change is replacing the single-ray-per-surface paradigm with a
**branch queue** (breadth-first traversal):

```
pending_branches = deque([initial_ray])
while pending_branches:
    ray = pending_branches.popleft()
    for each surface along ray path:
        if surface is beam splitter:
            reflected = reflect(ray) with power *= R
            transmitted = refract(ray) with power *= T
            pending_branches.append(reflected)
            ray = transmitted          # continue with transmitted branch
        else:
            normal refraction / reflection
    store completed ray path
```

Guards to prevent combinatorial explosion:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_split_depth` | 4 | Maximum recursive splits per original ray |
| `max_total_branches` | 256 | Hard cap on total ray instances |
| `min_branch_power` | 1e-3 | Discard branches below this threshold |

**Surface metadata:**

```python
{
    "surface": "Beam Splitter",
    "rc": 0.0,                    # can be curved
    "diameter": 25.0,
    "glass": "AIR",
    "beam_splitter": {
        "mode": "ideal",          # later: "fresnel", "plate"
        "reflectance": 0.5,
        "transmittance": 0.5,
        "loss": 0.0,
        "analysis_branch": "transmit",
    },
}
```

**Phased implementation:**

1. UI surface type and persistence (editor table, file I/O).
2. Deterministic branch engine in `KrakenSys.py` (the hard part).
3. 2-D / 3-D rendering of multi-branch ray trees.
4. Branch-filtered analysis (select which arm(s) contribute to spot / MTF).
5. Fresnel / polarisation modes (wavelength-dependent R/T).
6. Plate splitter model with thickness and ghost reflections.

**Reference projects:** LightPipes' `BeamMix(F1, F2)` demonstrates the
field-fork-and-recombine pattern.  SeaRay's volume/surface architecture
shows how to dispatch different propagation kernels per branch.

---

### F2. Gaussian Beam / Laser Source Propagation

**Requirement:** Model Gaussian (TEM₀₀) and higher-order (Hermite-Gauss,
Laguerre-Gauss) laser beams with proper beam waist evolution, divergence,
Rayleigh range, and M² beam quality tracking.

**Current state:** KrakenOS is a geometric ray tracer.  `system.Parax()`
computes cardinal points but does not expose surface-by-surface ABCD
matrices or carry a complex beam parameter.  The existing `SourceRnd` class
can sample rays from a Gaussian angular/spatial distribution, which gives
correct geometric spot diagrams but cannot model diffraction-limited
focusing, beam waist evolution, or M².

**Design approach — two tiers:**

#### Tier A: ABCD / q-parameter tracker (lightweight, paraxial)

Add a `GaussianBeam` class that propagates the complex beam parameter
`q = z + i·z_R` through each surface using 2×2 ABCD matrices:

```
q_out = (A·q_in + B) / (C·q_in + D)
```

From `q`, extract at every surface:

- Beam radius: `w(z) = sqrt(-λ / (π · Im(1/q)))`
- Wavefront curvature: `R(z) = 1 / Re(1/q)`
- Far-field divergence: `θ = λ / (π·w₀)`

ABCD matrices for each element type:

| Element | Matrix |
|---------|--------|
| Free space (thickness *d*, index *n*) | `[1, d/n; 0, 1]` |
| Spherical interface (R, n₁→n₂) | `[1, 0; (n₁-n₂)/(n₂·R), n₁/n₂]` |
| Thin lens (focal length *f*) | `[1, 0; -1/f, 1]` |
| Mirror (radius *R*) | `[1, 0; -2/R, 1]` |

The beam envelope `w(z)` is overlaid on the 2-D layout as a shaded
region, giving an immediate visual of waist location and divergence.

Tangential and sagittal planes are tracked separately for astigmatic
systems (tilted mirrors, Brewster surfaces).

**Reference projects:**
- **rezonator2** — mature C++ implementation: `BeamCalculator`,
  `RoundTripCalculator`, caustic functions, stability maps, T/S plane
  separation.  The most complete reference for cavity / resonator design.
- **simcav** — clean Python ABCD library (`simcav_ABCD.py`) with
  constraint-based cavity solver.  Directly portable code.

#### Tier B: Full field propagation (wave-optics, when paraxial breaks down)

For cases where the q-parameter approximation fails (hard aperture clipping,
non-Gaussian profiles, partial coherence), fall back to LightPipes-style
FFT propagation:

- Represent the beam as a complex NxN field grid (`Field` object).
- Propagate between surfaces using Fresnel diffraction (angular spectrum
  method or convolution).
- Apply lens/mirror phase screens at each surface.
- Extract intensity, phase, beam quality metrics (D4σ, Strehl, M²).

**Reference projects:**
- **LightPipes** — `Fresnel()`, `Forward()`, `ABCD()` propagators;
  `GaussBeam()`, `GaussHermite()`, `GaussLaguerre()` source functions;
  `D4sigma()`, `Strehl()`, `Centroid()` diagnostics.
- **SeaRay** — paraxial kernel does split-step Fourier propagation of the
  full envelope; handles non-Gaussian beams and aperture clipping.

**Phased implementation:**

1. Extract surface-by-surface ABCD matrices from existing `Parax()` data.
2. Implement `GaussianBeam` class with q-parameter propagation.
3. Add beam envelope overlay to 2-D layout display.
4. Add T/S plane separation for astigmatic systems.
5. (Optional) LightPipes-style `Field` propagation for full wave-optics.

---

### F3. Illumination Source Surface Type

**Requirement:** Add a `"Source"` or `"Illumination"` surface type to the
layout editor that defines spatially and angularly extended light sources
with configurable radiance distributions (Lambertian, Gaussian, custom
function), replacing the current uniform entrance-pupil fill.

**Current state:** The `SourceRnd` class in `SourceRand.py` already
generates ray fans with user-defined angular distributions and spatial
shapes (circular, square).  Example distributions include solar limb
darkening, Gaussian (atmospheric seeing), sinc (diffraction), etc.
However, `SourceRnd` is a standalone utility — it is not integrated into
the layout editor, which always launches rays from a uniform pupil grid.

**Design approach:**

1. Add `"Source"` to the `SURFACE_TYPES` tuple in `layout_editor.py`.
2. Expose UI fields for:
   - Angular distribution: Lambertian, Gaussian (σ), cosine-power,
     user-defined `f(θ)`.
   - Spatial extent: circular (radius), rectangular (w × h), point.
   - Ray count and wavelength spectrum.
   - Radiance (W·sr⁻¹·m⁻²) for radiometric calculations.
3. In the editor's trace loop, detect source surfaces and delegate ray
   generation to `SourceRnd` instead of the default pupil grid.
4. Add an irradiance accumulator at the image surface: bin arriving rays
   by position and sum their power contributions to produce an
   irradiance map (W·m⁻²).

**Source type library** (pre-configured distributions):

| Source | Distribution | Typical use |
|--------|-------------|-------------|
| Point source | Delta spatial, isotropic angular | Resolution testing |
| Lambertian | Uniform spatial, cos(θ) angular | LED, diffuse emitter |
| Gaussian | Gaussian spatial + angular | Laser / fiber output |
| Collimated | Uniform spatial, zero angular | Distant star, laser |
| Blackbody | Planckian spectrum weighting | Thermal radiometry |
| Custom | User `f(θ, φ, x, y)` | Application-specific |

**Reference projects:**
- **LightPipes** — `GaussBeam()`, `GaussHermite()`, `GaussLaguerre()`,
  `PointSource()`, `AiryBeam()` source functions with proper phase and
  amplitude initialisation.
- **pyLaserPulse** — component catalog with pre-configured real-world
  sources (pump diodes, seed lasers, ASE) including spectral/temporal
  profiles.

---

### F4. Coherent Interference Analysis (Michelson Interferometer)

**Requirement:** Given a beam splitter (F1) and multiple optical arms,
compute coherent recombination at a detector to produce interference fringe
patterns.  Target demonstration: a Michelson interferometer with tuneable
OPD, producing classic cos² fringes and — with a tilted mirror — spatial
fringe patterns.

**Current state:** KrakenOS tracks optical path length per ray (`system.OP`,
`system.TOP`, `system.TOP_S`).  The `PhaseCalc` module computes wavefront
phase maps and Zernike coefficients at the exit pupil.  The `PSFCalc`
module computes diffraction PSF via Huygens wavelets.  All infrastructure
for OPL-aware ray tracing exists — what is missing is:

1. A beam splitter that forks rays into two arms (prerequisite: F1).
2. A **coherent detector** that sums complex amplitudes from all branches
   arriving at the same detector pixel.

**Physics:**

At each detector pixel (x, y), the total electric field is the coherent
sum over all arriving ray branches:

```
E(x,y) = Σ_branches  sqrt(P_branch) · exp(i · 2π/λ · OPL_branch)
                      · exp(i · 2π/λ · (l·x + m·y))
```

where `l, m` are direction cosines and `OPL_branch` is the total optical
path from source to detector for that branch.

The observed intensity is:

```
I(x,y) = |E(x,y)|²
```

For two branches with powers P₁, P₂ and OPL difference ΔOPL:

```
I = P₁ + P₂ + 2·sqrt(P₁·P₂)·cos(2π/λ · ΔOPL)
```

This naturally produces:
- **Temporal fringes** (uniform tilt, varying OPD → bright/dark cycles).
- **Spatial fringes** (tilted mirror → linear fringe pattern across detector).
- **Ring fringes** (spherical wavefront mismatch → Newton's rings).

**Design approach:**

```
              Source
                │
          Beam Splitter (F1)
           ╱          ╲
       Arm 1          Arm 2
      (mirror)       (mirror)
           ╲          ╱
          Beam Splitter (recombine)
                │
        Coherent Detector
           I = |E₁+E₂|²
```

Implementation components:

1. **`CoherentDetector`** class (new):
   - NxN pixel grid at the image surface.
   - For each arriving ray: compute complex amplitude
     `A = sqrt(P) · exp(i·2π/λ · OPL)`.
   - Accumulate amplitudes per pixel (coherent sum).
   - Output: intensity map `I = |Σ A|²`, phase map `φ = arg(Σ A)`.

2. **Branch-aware `raykeeper`**:
   - Each stored ray carries a `branch_id` and `branch_power`.
   - The detector groups rays by pixel position and sums amplitudes
     across all branches.

3. **Detector grid binning**:
   - Rays land at continuous (x, y) positions on the detector.
   - Bin into detector pixels using nearest-neighbour or Gaussian
     splat weighting.
   - Grid resolution set by user (e.g. 256×256 or 512×512).

**Validation targets:**

| Configuration | Expected pattern |
|---------------|-----------------|
| Michelson, plane mirrors, on-axis | Uniform intensity modulated by OPD scan |
| Michelson, one mirror tilted | Linear spatial fringes, period = λ/sin(tilt) |
| Mach-Zehnder, path difference | Uniform fringes across detector |
| Fabry-Perot (two partial mirrors) | Airy function ring pattern |
| Young's double slit | cos²-modulated sinc² envelope |

**Reference projects:**
- **LightPipes** — the direct template.  Its `BeamMix(F1, F2)` coherently
  superposes two field arrays; `Intensity(F)` extracts |E|².  A Michelson
  interferometer is ~10 lines of LightPipes code:
  ```python
  F = Begin(size, wavelength, N)
  F1, F2 = BeamMix(F, F)          # split
  F1 = Fresnel(arm1_length, F1)   # propagate arm 1
  F2 = Fresnel(arm2_length, F2)   # propagate arm 2
  F = BeamMix(F1, F2)             # recombine
  I = Intensity(F)                # fringe pattern
  ```
- **SeaRay** — its paraxial kernel propagates the full complex envelope,
  so interference is automatic when two beams overlap on the same grid.

**Prerequisites:** F1 (beam splitter) must be implemented first.  F2
(Gaussian beam) is recommended but not strictly required — interference
works with any coherent source.

---

### Recommended Implementation Order

```
F3 (Illumination Source)     ← self-contained, no prerequisites
  │
F2a (Gaussian beam / ABCD)   ← self-contained, small
  │
F1 (Beam Splitter)           ← engine refactor, medium-large
  │
F2b (Full field propagation) ← benefits from F1 for split-field cases
  │
F4 (Interference Analysis)   ← requires F1, benefits from F2b
```

This order builds capability incrementally: each feature is usable on its
own, and later features compose naturally with earlier ones.

### Proposed Architecture

```
                KrakenOS Core (geometric ray tracing)
                            │
            ┌───────────────┼───────────────┐
            │               │               │
       GaussianBeam    BeamSplitter    CoherentField
       (ABCD / q)      (ray fork)     (NxN complex)
            │               │               │
            │          ┌────┴────┐          │
            │       Branch A  Branch B      │
            │          │         │          │
            └──────────┴────┬────┘──────────┘
                            │
                    CoherentDetector
                   (amplitude sum → I)
```

- **GaussianBeam** — lightweight q-parameter tracker alongside ray trace;
  overlays beam envelope `w(z)` on 2-D layout.
- **BeamSplitter** — ray forking engine with branch queue and power
  tracking.
- **CoherentField** — optional NxN complex field for wave-optics accuracy;
  interchangeable with ray-based OPL tracking.
- **CoherentDetector** — sums complex amplitudes from all branches on a
  pixel grid to produce intensity and phase maps.

The Gaussian beam mode and the coherent field mode coexist: use
q-parameter for quick cavity design, switch to full field propagation for
interference/diffraction analysis.

### Reference Projects Surveyed

| Project | Language | Key contribution to this design |
|---------|----------|-------------------------------|
| [LightPipes](https://github.com/opticspy/lightpipes) | Python | Field class, `BeamMix`, Fresnel/ABCD propagators, interference pattern generation |
| [beamshapy](https://github.com/music-felong/beamshapy) | Python | Gerchberg-Saxton phase mask optimisation, FFT-based Fourier optics pipeline |
| [rezonator2](https://github.com/orion-project/rezonator2) | C++/Qt6 | ABCD matrices, q-parameter, cavity stability maps, T/S plane separation, caustic functions |
| [simcav](https://github.com/aewallin/simcav) | Python | Clean ABCD matrix library, constraint-based cavity solver, beam waist tracking |
| [SeaRay](https://github.com/USNavalResearchLaboratory/SeaRay) | Python/OpenCL | Multi-kernel propagation (ray + paraxial + UPPE), volume/surface architecture, GPU acceleration |
| [pyLaserPulse](https://github.com/jsfeehan/pyLaserPulse) | Python | GNLSE solver, component catalog, fiber amplifier modelling, spectral/temporal source definitions |
