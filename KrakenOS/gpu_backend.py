"""
GPU acceleration backend for KrakenOS.

Provides a unified array namespace (``xp``) that resolves to CuPy when a
CUDA-capable GPU is available and falls back to NumPy otherwise.  All heavy
numerical code should ``from .gpu_backend import xp, to_gpu, to_cpu`` and use
``xp`` in place of ``np`` for array creation and math so that the same code
path runs on both CPU and GPU transparently.
"""

import os
import ctypes
import numpy as np

# ---- NixOS CUDA library discovery ------------------------------------
# On NixOS the CUDA driver and toolkit libraries live outside the default
# linker search path.  We pre-load them via ctypes with RTLD_GLOBAL so
# that CuPy can find all CUDA shared objects when it needs them.

def _preload_cuda_libs():
    """Pre-load CUDA .so files into the process with RTLD_GLOBAL."""
    lib_dirs = []

    # 1) NVIDIA driver libs (libcuda.so, libnvidia-*.so)
    drv = "/run/opengl-driver/lib"
    if os.path.isdir(drv):
        lib_dirs.append(drv)

    # 2) NixOS system-path containing CUDA toolkit (libcufft, cublas, …)
    nix_store = "/nix/store"
    if os.path.isdir(nix_store):
        for entry in os.listdir(nix_store):
            if "system-path" in entry:
                candidate = os.path.join(nix_store, entry, "lib")
                if os.path.isfile(os.path.join(candidate, "libcudart.so")):
                    lib_dirs.append(candidate)
                    break

    if not lib_dirs:
        return

    # Libraries CuPy needs, in dependency order.
    needed = [
        "libcuda.so.1",
        "libcudart.so.12",
        "libcublas.so.12",
        "libcublasLt.so.12",
        "libcufft.so.11",
        "libcurand.so.10",
        "libcusparse.so.12",
        "libcusolver.so.11",
        "libnvrtc.so.12",
    ]

    for libname in needed:
        for d in lib_dirs:
            path = os.path.join(d, libname)
            if os.path.isfile(path):
                try:
                    ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass
                break


_preload_cuda_libs()

# ---- CuPy import with fallback ---------------------------------------
try:
    import cupy as cp
    cp.cuda.runtime.getDeviceCount()
    # Functional test: exercises CUB reduction kernel compilation
    # (catches NVRTC / CUDA header incompatibilities)
    _t = cp.ones((4, 3), dtype=float)
    _v = cp.linalg.norm(_t, axis=1, keepdims=True)
    assert float(_v[0, 0]) > 0
    del _t, _v
    xp = cp
    HAS_GPU = True
except Exception:
    xp = np
    HAS_GPU = False


def to_gpu(arr):
    """Move a numpy array to the GPU.  No-op when CuPy is unavailable."""
    if HAS_GPU:
        return cp.asarray(arr)
    return arr


def to_cpu(arr):
    """Ensure *arr* is a plain numpy array on the host."""
    if HAS_GPU and isinstance(arr, cp.ndarray):
        return cp.asnumpy(arr)
    return np.asarray(arr)


def get_xp(arr):
    """Return the array module (``cupy`` or ``numpy``) that owns *arr*."""
    if HAS_GPU and isinstance(arr, cp.ndarray):
        return cp
    return np
