# KrakenOS GPU Acceleration

GPU-accelerated compute paths for KrakenOS using CuPy, with automatic
fallback to NumPy when no CUDA GPU is available.

## Quick Start

```python
import KrakenOS as Kos

print("GPU available:", Kos.HAS_GPU)

# BatchTraceLoop is a drop-in replacement for TraceLoop
Kos.BatchTraceLoop(x, y, z, L, M, N, wavelength, rays_container)

# PSF/MTF functions automatically use GPU when available
I = Kos.psf4mtf(COEF, Focal, Diameter, Wave, pixels=2048)
```

Run the stress test to verify GPU utilisation:

```bash
python GPU_test.py          # single run
python GPU_test.py --loop   # repeat indefinitely (watch in btop)
```

## Architecture

### `KrakenOS/gpu_backend.py` — Backend Abstraction

Provides a unified array namespace that resolves to CuPy or NumPy:

| Symbol     | Description                                       |
|------------|---------------------------------------------------|
| `xp`       | Array module — `cupy` on GPU, `numpy` on CPU      |
| `HAS_GPU`  | `True` if a CUDA GPU is available                 |
| `to_gpu()` | Move a numpy array to the GPU (no-op without GPU) |
| `to_cpu()` | Ensure array is plain numpy on host               |
| `get_xp()` | Return the array module that owns a given array   |

On NixOS, the module automatically discovers and pre-loads CUDA driver
and toolkit libraries from `/run/opengl-driver/lib` and the Nix store
`system-path`, since these are not on the default linker path.

Usage in KrakenOS modules:

```python
from .gpu_backend import xp, to_cpu, to_gpu

# Use xp instead of np for compute
result = xp.fft.fft2(data)

# Convert back to numpy before matplotlib
plt.imshow(to_cpu(result))
```

## What Changed

### Phase 1: Drop-in FFT & Linear Algebra (GPU-accelerated)

#### `KrakenOS/PSFCalc.py`

All compute operations in `psf4mtf()`, `psf()`, `PsfPlus()`, and
`calculate_mtf()` now use `xp` instead of `np`:

- `xp.meshgrid`, `xp.sqrt`, `xp.exp` — pupil grid creation
- `xp.fft.fft2`, `xp.fft.fftshift` — Fourier transforms (cuFFT on GPU)
- `xp.abs`, `xp.sum` — intensity calculation

Results are converted to numpy via `to_cpu()` before matplotlib plotting.

**Speedup**: 10–50x on large arrays (2048x2048 and above).

#### `KrakenOS/WavefrontFit.py`

Two improvements:

1. **`Wavefront_Zernike_Phase()`** — uses `xp` for GPU-accelerated
   wavefront map generation. The Zernike polynomial evaluation
   (`zernike_polynomials`) operates on the full pupil grid at once,
   which maps well to GPU parallelism.

2. **`System_Matrix_Zernikes()`** — vectorised. The original had a
   double Python loop `for h in range(Tp): for n in range(n_NA):`
   evaluating one Zernike term at one point per iteration. Now
   evaluates each Zernike term across ALL pupil points in one call,
   reducing from O(Tp × n_NA) Python iterations to O(n_NA).

3. **`Zernike_Fitting()`** — replaced explicit normal equations
   `(A^T A)^{-1} A^T b` with `np.linalg.lstsq()`, which is faster
   and numerically more stable.

### Phase 2: Vectorised Ray Tracing

The existing `TraceLoop` traces rays one at a time in a Python loop.
The new `BatchTraceLoop` processes all N rays through each surface
simultaneously using vectorised array operations.

#### `KrakenOS/HitOnSurf.py` — Batch Intersection Solver

- **`BatchSolveHit(Px1, Py1, Pz1, L, M, N, j)`**: Vectorised
  Newton-Raphson ray–surface intersection for N rays simultaneously.
  Concatenates 3N surface evaluations into a single `SurfaceShape()`
  call per iteration. Convergence is tracked per-ray with masking.

- **`BatchSurfDer(x, y, z, j)`**: Vectorised 4th-order finite-difference
  surface normal computation. Evaluates 12N points in a single
  `SurfaceShape()` call, then computes normalised gradients.

#### `KrakenOS/PhysicsClass.py` — Batch Snell's Law

- **`batch_snell_refraction(S_batch, Nsurf_batch, n1, n2)`**: Vectorised
  Snell's law for N rays. Batch dot products, cross products, normal
  flipping, total internal reflection detection — all using array
  operations. Handles both refraction and mirror reflection (n2 = -1).

#### `KrakenOS/KrakenSys.py` — Batch Trace Engine

- **`system.BatchTrace(pSources, dCosines, WaveLength)`**: Traces N rays
  through all surfaces simultaneously. Per surface:
  1. Batch 4×4 matrix coordinate transform (world → surface-local)
  2. Batch aperture check (boolean mask)
  3. Batch Newton-Raphson intersection (`BatchSolveHit`)
  4. Batch surface normal (`BatchSurfDer`)
  5. Batch inverse transform (surface-local → world)
  6. Batch Snell's law (`batch_snell_refraction`)
  7. Per-ray result collection

- **`system._apply_batch_result(i)`**: Loads ray i's batch results into
  the standard `system` attributes so that `raykeeper.push()` works
  without modification.

#### `KrakenOS/TraceLoopTool.py` — User-Facing API

- **`BatchTraceLoop(x, y, z, L, M, N, W, Container)`**: Drop-in
  replacement for `TraceLoop`. Falls back to scalar tracing for
  fewer than 10 rays (where overhead would dominate).

## Benchmark Results

Tested on CPU (NumPy) — no GPU in CI. GPU would further accelerate
the vectorised operations.

### Ray Tracing (Batch vs Scalar)

| System                    | Rays  | Scalar  | Batch   | Speedup |
|---------------------------|-------|---------|---------|---------|
| Singlet lens (2 surfaces) | 100   | 0.047s  | 0.011s  | 4.2x    |
| Singlet lens              | 1,000 | 0.477s  | 0.102s  | 4.7x    |
| Singlet lens              | 5,000 | 2.430s  | 0.586s  | 4.1x    |
| Cooke triplet (6 surfaces)| 2,000 | 2.037s  | 0.334s  | 6.1x    |

All results match scalar trace to machine precision (~1e-15).

### PSF / FFT (GPU vs CPU)

| Grid size  | CPU (NumPy) | GPU (CuPy + cuFFT) |
|------------|-------------|---------------------|
| 512×512    | ~0.15s      | 0.081s              |
| 1024×1024  | ~0.5s       | 0.015s              |
| 2048×2048  | ~2.0s       | 0.056s              |
| 4096×4096  | ~8.0s       | 0.222s              |

### Wavefront Map Generation (GPU)

| Grid size  | 5× evaluation time |
|------------|-------------------|
| 512×512    | 0.016s            |
| 1024×1024  | 0.038s            |
| 2048×2048  | 0.113s            |

## API Compatibility

All changes are **backward-compatible**:

- Existing `TraceLoop()` is unchanged and still works
- `psf()`, `psf4mtf()`, `PsfPlus()`, `calculate_mtf()` return numpy
  arrays regardless of GPU availability
- `Wavefront_Zernike_Phase()` returns CuPy arrays when GPU is active
  (use `to_cpu()` if you need numpy)
- `BatchTraceLoop()` is a new function; does not replace `TraceLoop`
- No changes to `raykeeper`, `surf`, or `system` constructor APIs

## Dependencies

- **Required**: NumPy (already a dependency)
- **Optional**: CuPy (`pip install cupy-cuda12x` for CUDA 12.x)
  - Falls back gracefully to NumPy when CuPy is not installed
  - Falls back when no CUDA GPU is detected

## Files Modified

| File | Changes |
|------|---------|
| `KrakenOS/gpu_backend.py` | **New** — GPU/CPU abstraction layer with CUB kernel smoke test |
| `KrakenOS/PSFCalc.py` | `np` → `xp` for FFT and array math |
| `KrakenOS/WavefrontFit.py` | GPU wavefront, vectorised Zernike matrix, lstsq |
| `KrakenOS/HitOnSurf.py` | `BatchSolveHit()`, `BatchSurfDer()` — now using `xp` for GPU |
| `KrakenOS/PhysicsClass.py` | `batch_snell_refraction()` — now using `xp` for GPU |
| `KrakenOS/KrakenSys.py` | `BatchTrace()` — full GPU pipeline (transforms, intersection, Snell) |
| `KrakenOS/TraceLoopTool.py` | `BatchTraceLoop()` — now uses `batch_push()` |
| `KrakenOS/RayKeeper.py` | `batch_push()` — bulk result storage bypassing System intermediary |
| `KrakenOS/SurfTools.py` | `SurfaceShape()` — xp-aware zero-fill for flattened surfaces |
| `KrakenOS/MathShapesClass.py` | `error_map__surf.calculate()` — CPU fallback for `griddata` |
| `KrakenOS/Optimization/evaluator.py` | `TraceLoop` → `BatchTraceLoop` in merit function evaluation |
| `KrakenOS/__init__.py` | Export `HAS_GPU` |
| `GPU_test.py` | **New** — GPU stress test (3 stages) |

### Phase 3: Full GPU Pipeline & Optimization

#### `KrakenOS/gpu_backend.py` — Improved Detection

The CuPy smoke test now exercises CUB reduction kernel compilation
(the same code path used by `xp.linalg.norm()`), catching NVRTC
header incompatibilities that simple element-wise tests miss.

#### `KrakenOS/HitOnSurf.py` — GPU Newton-Raphson

`BatchSolveHit()` and `BatchSurfDer()` now use `xp` for all solver
math (concatenation, convergence checks, Newton step).  Surface
function evaluations transparently dispatch to CuPy via NumPy's
`__array_function__` protocol — no changes needed to individual
surface classes (conic, aspheric, Zernike).

#### `KrakenOS/PhysicsClass.py` — GPU Snell's Law

`batch_snell_refraction()` uses `xp` for all dot products, cross
products, normal flipping, TIR detection, and vector refraction.

#### `KrakenOS/KrakenSys.py` — GPU Coordinate Transforms

`BatchTrace()` converts 4×4 transform matrices to `xp` arrays and
runs all homogeneous coordinate transforms, aperture checks, and
state updates on GPU.  Results are bulk-transferred to CPU once per
surface (not per ray) for storage.

#### `KrakenOS/RayKeeper.py` — `batch_push()`

New method that reads batch results directly from the per-ray dicts
produced by `BatchTrace()`, bypassing the `_apply_batch_result()` →
`push()` round-trip that required setting and reading ~30 System
attributes per ray.

#### `KrakenOS/MathShapesClass.py` — Error Map CPU Fallback

`error_map__surf.calculate()` detects CuPy arrays and transparently
transfers to CPU for `scipy.interpolate.griddata`, then moves the
result back to GPU.  Non-error-map surfaces work natively on GPU.

#### `KrakenOS/Optimization/evaluator.py` — BatchTraceLoop Integration

`_spot_rms()`, `_mtf_at_frequency()` (single-threaded path), and
`_trace_mtf_chunk()` (multi-process path) now use `BatchTraceLoop`
instead of scalar `TraceLoop`, giving the optimizer the same
vectorised speedups available to user code.

## Future Work

- Columnar storage in `raykeeper` — replace per-ray list-of-dicts with
  pre-allocated 2D arrays to eliminate the remaining O(N) Python loop
  in `batch_push()` and enable direct GPU↔raykeeper data flow
- GPU-resident optimization — keep ray data on GPU across consecutive
  merit function evaluations (avoid repeated host↔device transfers)
- Batch non-sequential trace (`BatchNsTrace`) for scattering/stray-light
  analysis
