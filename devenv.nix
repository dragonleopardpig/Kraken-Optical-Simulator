{ pkgs, lib, ... }:

let
  pkgsNoCuda = import pkgs.path {
    inherit (pkgs) system;
    config = (pkgs.config or { }) // {
      cudaSupport = false;
    };
  };
  vtkPackage = pkgsNoCuda.python313Packages.vtk;
  vtkTkLibDir = "${vtkPackage}/lib";
  runtimeLibs = with pkgs; [
    stdenv.cc.cc.lib
    zlib
    glib
    libGL
    fontconfig
    freetype
    dbus
    wayland
    libxkbcommon
    xorg.libX11
    xorg.libXcursor
    xorg.libXext
    xorg.libXfixes
    xorg.libXi
    xorg.libXrandr
    xorg.libXtst
    xorg.libXrender
    xorg.libxcb
  ];
  bootstrapVenv = ''
    VENV_DIR="$PWD/.devenv/state/venv"
    PYTHON_PATH_FILE="$PWD/.devenv/state/kraken-python.path"
    CURRENT_PYTHON="$(readlink -f "$(command -v python)")"

    if [ ! -x "$VENV_DIR/bin/python" ] || [ ! -f "$PYTHON_PATH_FILE" ] || [ "$(cat "$PYTHON_PATH_FILE" 2>/dev/null)" != "$CURRENT_PYTHON" ]; then
      rm -rf "$VENV_DIR"
      python -m venv --system-site-packages "$VENV_DIR"
      mkdir -p "$(dirname "$PYTHON_PATH_FILE")"
      printf '%s\n' "$CURRENT_PYTHON" > "$PYTHON_PATH_FILE"
      rm -f "$PWD/.devenv/state/kraken-requirements.hash"
    fi

    if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
      "$VENV_DIR/bin/python" -m ensurepip --upgrade
    fi
  '';
  installCoreDeps = ''
    KRAKEN_REQ_HASH="krakenos-core-v19-nix-vtk-tk"
    REQ_HASH_FILE="$PWD/.devenv/state/kraken-requirements.hash"

    "$VENV_DIR/bin/python" -m pip install --upgrade pip "setuptools<82" wheel
    "$VENV_DIR/bin/python" -m pip install \
      -e . \
      numpy scipy matplotlib pandas pyvista \
      PyVTK csv342 ipython ipykernel pyzmq \
      packaging setuptools basedpyright ruff PyQt5 sip \
      cloudpickle pybind11
    # Keep VTK supplied by nixpkgs: the pip VTK wheel omits
    # libvtkRenderingTk.so, which is required by embedded VTK/Tk widgets.
    "$VENV_DIR/bin/python" -m pip uninstall -y vtk >/dev/null 2>&1 || true
    "$VENV_DIR/bin/python" -m pip install -r docs/requirements.txt
    printf '%s\n' "$KRAKEN_REQ_HASH" > "$REQ_HASH_FILE"
  '';
in
{
  env = {
    GREET = "KrakenOS devenv";
    KRAKEN_VTK_TK_LIB_DIR = vtkTkLibDir;
    LD_LIBRARY_PATH = (lib.makeLibraryPath (runtimeLibs ++ [ vtkPackage ])) + ":/run/opengl-driver/lib:/run/opengl-driver-32/lib";
  };

  languages.python = {
    enable = true;
    package = pkgs.python313.withPackages (ps: [
      ps.tkinter
      vtkPackage
      ps.pythonocc-core
      ps.trimesh
      ps.meshio
      ps.sphinx
      ps.sphinx-rtd-theme
    ]);
    uv.enable = true;
  };

  packages = with pkgs; [
    git
    cmake
    ninja
    pkg-config
    gcc
    boost
    tbb
    gmsh
  ] ++ runtimeLibs;

  enterShell = ''
    ${bootstrapVenv}

    export PATH="$VENV_DIR/bin:$PATH"

    export MPLCONFIGDIR="$PWD/.devenv/state/matplotlib"
    mkdir -p "$MPLCONFIGDIR"

    if [ -n "''${WAYLAND_DISPLAY:-}" ] || [ -n "''${DISPLAY:-}" ]; then
      export MPLBACKEND=qtagg
    fi

    # Do not inject project-local pagmo2 into LD_LIBRARY_PATH here: VTK's
    # OpenTURNS module must load the ABI-matched pagmo from its Nix closure.

    # Add CUDA wheel shared libraries (CuPy/Torch) into runtime search path.
    for nvidia_lib_dir in "$VENV_DIR"/lib/python*/site-packages/nvidia/*/lib; do
      if [ -d "$nvidia_lib_dir" ]; then
        export LD_LIBRARY_PATH="$nvidia_lib_dir:$LD_LIBRARY_PATH"
      fi
    done

    if ! "$VENV_DIR/bin/python" -c 'import numpy, scipy, matplotlib, pyvista, vtk' >/dev/null 2>&1; then
      echo "KrakenOS Python deps are not installed in $VENV_DIR."
      echo "Run: kraken-install"
    fi

    echo "$GREET"
    "$VENV_DIR/bin/python" --version
  '';

  scripts.kraken-install.exec = ''
    ${bootstrapVenv}
    ${installCoreDeps}
  '';

  scripts.kraken-install-notebooks.exec = ''
    ${bootstrapVenv}
    ${installCoreDeps}
    "$VENV_DIR/bin/python" -m pip install jupyter jupyterlab
  '';

  scripts.kraken-install-docs.exec = ''
    ${bootstrapVenv}
    "$VENV_DIR/bin/python" -m pip install -r docs/requirements.txt
  '';

  scripts.kraken-vtk-tk-check.exec = ''
    ${bootstrapVenv}
    "$VENV_DIR/bin/python" - <<'PY'
    from pathlib import Path
    import os
    import vtk
    import vtkmodules

    lib_dir = Path(os.environ["KRAKEN_VTK_TK_LIB_DIR"])
    tk_lib = lib_dir / "libvtkRenderingTk.so"
    print("VTK version:", vtk.vtkVersion.GetVTKVersion())
    print("VTK module:", Path(vtkmodules.__file__).resolve())
    print("KRAKEN_VTK_TK_LIB_DIR:", lib_dir)
    print("libvtkRenderingTk.so:", tk_lib)
    if not tk_lib.exists():
      raise SystemExit("libvtkRenderingTk.so not found")
    from KrakenOS.UI import layout_editor
    layout_editor._load_3d_backends()
    print("vtkTkRenderWindowInteractor:", "available" if layout_editor.vtkTkRenderWindowInteractor else "unavailable")
    print("reason:", getattr(layout_editor, "_VTK_TK_UNAVAILABLE_REASON", "") or "-")
    if layout_editor.vtkTkRenderWindowInteractor is None:
      raise SystemExit(1)
    PY
  '';

  scripts.kraken-install-gpu.exec = ''
    ${bootstrapVenv}
    ${installCoreDeps}
    "$VENV_DIR/bin/python" -m pip install cupy-cuda12x || true
    "$VENV_DIR/bin/python" -m pip install nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cufft-cu12 || true
    "$VENV_DIR/bin/python" -m pip install torch || true
  '';
}
