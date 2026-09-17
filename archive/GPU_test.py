#!/usr/bin/env python3
"""
GPU stress test for KrakenOS.

Runs progressively heavier workloads so you can watch GPU utilisation
climb in btop / nvidia-smi.  Three stages:

  1. PSF / MTF via FFT  (large 2-D arrays on GPU)
  2. Batch ray tracing   (vectorised Newton-Raphson on GPU)
  3. Repeated wavefront fitting (Zernike + lstsq)

Usage:
    python GPU_test.py          # run all stages
    python GPU_test.py --loop   # repeat indefinitely (Ctrl-C to stop)
"""

import sys
import time
import numpy as np
import KrakenOS as Kos

SEPARATOR = "=" * 70


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_cooke_triplet():
    """Six-surface Cooke triplet – a realistic multi-element lens."""
    P_Obj = Kos.surf(); P_Obj.Thickness = 100; P_Obj.Glass = "AIR"; P_Obj.Diameter = 40
    S1 = Kos.surf(); S1.Rc = 28.0;  S1.Thickness = 4.0; S1.Glass = "BK7"; S1.Diameter = 20; S1.k = -0.5
    S2 = Kos.surf(); S2.Rc = -120.0; S2.Thickness = 2.0; S2.Glass = "AIR"; S2.Diameter = 20
    S3 = Kos.surf(); S3.Rc = -28.0; S3.Thickness = 1.5; S3.Glass = "F2";  S3.Diameter = 12
    S4 = Kos.surf(); S4.Rc = 28.0;  S4.Thickness = 2.0; S4.Glass = "AIR"; S4.Diameter = 12
    S5 = Kos.surf(); S5.Rc = 80.0;  S5.Thickness = 4.0; S5.Glass = "BK7"; S5.Diameter = 20
    S6 = Kos.surf(); S6.Rc = -40.0; S6.Thickness = 40.0; S6.Glass = "AIR"; S6.Diameter = 20
    P_Ima = Kos.surf(); P_Ima.Thickness = 0; P_Ima.Glass = "AIR"; P_Ima.Diameter = 50
    return Kos.system([P_Obj, S1, S2, S3, S4, S5, S6, P_Ima], Kos.Setup())


def build_double_gauss():
    """Eight-surface Double-Gauss – more surfaces, heavier compute."""
    P_Obj = Kos.surf(); P_Obj.Thickness = 200; P_Obj.Glass = "AIR"; P_Obj.Diameter = 60
    S1 = Kos.surf(); S1.Rc = 60.0;   S1.Thickness = 8.0; S1.Glass = "BK7"; S1.Diameter = 40
    S2 = Kos.surf(); S2.Rc = 200.0;  S2.Thickness = 1.0; S2.Glass = "AIR"; S2.Diameter = 40
    S3 = Kos.surf(); S3.Rc = 40.0;   S3.Thickness = 6.0; S3.Glass = "BK7"; S3.Diameter = 30
    S4 = Kos.surf(); S4.Rc = -80.0;  S4.Thickness = 2.0; S4.Glass = "F2";  S4.Diameter = 30
    S5 = Kos.surf(); S5.Rc = 30.0;   S5.Thickness = 10.0; S5.Glass = "AIR"; S5.Diameter = 20  # stop
    S6 = Kos.surf(); S6.Rc = -30.0;  S6.Thickness = 2.0; S6.Glass = "F2";  S6.Diameter = 30
    S7 = Kos.surf(); S7.Rc = 80.0;   S7.Thickness = 6.0; S7.Glass = "BK7"; S7.Diameter = 30
    S8 = Kos.surf(); S8.Rc = -40.0;  S8.Thickness = 1.0; S8.Glass = "AIR"; S8.Diameter = 40
    S9 = Kos.surf(); S9.Rc = -200.0; S9.Thickness = 8.0; S9.Glass = "BK7"; S9.Diameter = 40
    S10 = Kos.surf(); S10.Rc = -60.0; S10.Thickness = 80.0; S10.Glass = "AIR"; S10.Diameter = 40
    P_Ima = Kos.surf(); P_Ima.Thickness = 0; P_Ima.Glass = "AIR"; P_Ima.Diameter = 80
    return Kos.system([P_Obj, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, P_Ima], Kos.Setup())


# ---------------------------------------------------------------------------
# Stage 1: PSF / MTF — GPU FFT stress
# ---------------------------------------------------------------------------

def stage_psf_fft():
    print(SEPARATOR)
    print("STAGE 1: PSF / MTF via GPU FFT")
    print(SEPARATOR)

    # Zernike coefficients with several aberration terms
    COEF = np.zeros(36)
    COEF[4] = 0.3   # defocus
    COEF[5] = 0.1   # astigmatism
    COEF[8] = 0.15   # coma
    COEF[12] = 0.05  # spherical
    COEF[24] = 0.02  # higher-order

    for pixels in [512, 1024, 2048, 4096]:
        t0 = time.perf_counter()
        I = Kos.psf4mtf(COEF, 100.0, 25.0, 0.55, pixels=pixels, PupilSample=4)
        dt = time.perf_counter() - t0
        print(f"  PSF {pixels}x{pixels}: {dt:.3f}s  (peak={I.max():.4f})")

    # Repeated MTF computations to sustain GPU load
    print("  Running 20x MTF at 2048x2048 ...")
    t0 = time.perf_counter()
    for _ in range(20):
        mtf = Kos.calculate_mtf(COEF, 100.0, 25.0, 0.55, pixels=2048, PupilSample=4)
    dt = time.perf_counter() - t0
    print(f"  20x MTF 2048x2048: {dt:.3f}s total ({dt/20:.3f}s each)")
    print()


# ---------------------------------------------------------------------------
# Stage 2: Batch ray tracing — vectorised Newton-Raphson
# ---------------------------------------------------------------------------

def stage_batch_raytrace():
    print(SEPARATOR)
    print("STAGE 2: Batch Ray Tracing (vectorised)")
    print(SEPARATOR)

    Sys = build_cooke_triplet()

    for n_rays in [1000, 5000, 10000, 50000]:
        # Hexapolar-ish pupil fill
        r = np.sqrt(np.random.uniform(0, 1, n_rays)) * 8.0
        theta = np.random.uniform(0, 2 * np.pi, n_rays)
        x = np.zeros(n_rays)
        y = r * np.cos(theta)
        z = np.zeros(n_rays)
        L = np.zeros(n_rays)
        M = np.zeros(n_rays)
        N = np.ones(n_rays)

        Rays = Kos.raykeeper(Sys)
        t0 = time.perf_counter()
        Kos.BatchTraceLoop(x, y, z, L, M, N, 0.55, Rays)
        dt = time.perf_counter() - t0

        X_img, Y_img, *_ = Rays.pick(-1)
        print(f"  {n_rays:6d} rays -> {len(X_img):6d} valid: {dt:.3f}s  ({n_rays/dt:.0f} rays/s)")

    # Double Gauss — more surfaces
    print("\n  Double-Gauss (10 optical surfaces):")
    Sys2 = build_double_gauss()

    for n_rays in [1000, 5000, 20000]:
        r = np.sqrt(np.random.uniform(0, 1, n_rays)) * 12.0
        theta = np.random.uniform(0, 2 * np.pi, n_rays)
        x = np.zeros(n_rays)
        y = r * np.cos(theta)
        z = np.zeros(n_rays)
        L = np.zeros(n_rays)
        M = np.zeros(n_rays)
        N = np.ones(n_rays)

        Rays = Kos.raykeeper(Sys2)
        t0 = time.perf_counter()
        Kos.BatchTraceLoop(x, y, z, L, M, N, 0.55, Rays)
        dt = time.perf_counter() - t0

        X_img, Y_img, *_ = Rays.pick(-1)
        print(f"  {n_rays:6d} rays -> {len(X_img):6d} valid: {dt:.3f}s  ({n_rays/dt:.0f} rays/s)")
    print()


# ---------------------------------------------------------------------------
# Stage 3: Wavefront fitting — repeated Zernike decomposition
# ---------------------------------------------------------------------------

def stage_wavefront():
    print(SEPARATOR)
    print("STAGE 3: Wavefront Fitting (Zernike)")
    print(SEPARATOR)

    from KrakenOS.WavefrontFit import Zernike_Fitting, Wavefront_Zernike_Phase

    # Generate a large pupil grid
    for n_pts in [500, 2000, 5000]:
        x1 = np.random.uniform(-0.95, 0.95, n_pts)
        y1 = np.random.uniform(-0.95, 0.95, n_pts)
        # Simulate a wavefront with known aberrations
        COEF_true = np.zeros(36)
        COEF_true[4] = 0.5
        COEF_true[8] = 0.2
        COEF_true[12] = 0.1
        p = np.sqrt(x1**2 + y1**2)
        mask = p <= 1.0
        x1, y1 = x1[mask], y1[mask]
        Z1 = Wavefront_Zernike_Phase(x1, y1, COEF_true)
        from KrakenOS.gpu_backend import to_cpu
        Z1 = to_cpu(Z1)  # ensure numpy for Zernike_Fitting

        Arr = np.ones(36)

        t0 = time.perf_counter()
        for _ in range(10):
            SA, ZZ, rms_c, rms_cent, err = Zernike_Fitting(x1, y1, Z1, Arr.copy())
        dt = time.perf_counter() - t0
        print(f"  {len(x1):5d} pts, 36 terms, 10x fit: {dt:.3f}s  (fit err={err:.2e})")

    # Large-grid PSF wavefront (GPU path for Wavefront_Zernike_Phase)
    print("\n  GPU wavefront map generation:")
    COEF = np.zeros(36)
    COEF[4] = 0.5; COEF[8] = 0.2; COEF[12] = 0.1

    for grid in [512, 1024, 2048]:
        xy = np.linspace(-1, 1, grid)
        X, Y = np.meshgrid(xy, xy)
        t0 = time.perf_counter()
        for _ in range(5):
            W = Wavefront_Zernike_Phase(X, Y, COEF)
        dt = time.perf_counter() - t0
        print(f"  {grid}x{grid} wavefront, 5x: {dt:.3f}s")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\nKrakenOS GPU Stress Test")
    print(f"GPU available: {Kos.HAS_GPU}")
    if Kos.HAS_GPU:
        from KrakenOS.gpu_backend import xp
        dev = xp.cuda.Device(0)
        mem = dev.mem_info
        print(f"GPU memory: {mem[1] / 1e9:.1f} GB total, {mem[0] / 1e9:.1f} GB free")
    print()

    loop = "--loop" in sys.argv

    iteration = 0
    while True:
        iteration += 1
        if loop:
            print(f"\n{'#' * 70}")
            print(f"# ITERATION {iteration}")
            print(f"{'#' * 70}\n")

        t_total = time.perf_counter()

        stage_psf_fft()
        stage_batch_raytrace()
        stage_wavefront()

        dt_total = time.perf_counter() - t_total
        print(SEPARATOR)
        print(f"TOTAL TIME: {dt_total:.1f}s")
        print(SEPARATOR)

        if not loop:
            break

    print("\nDone.")


if __name__ == "__main__":
    main()
