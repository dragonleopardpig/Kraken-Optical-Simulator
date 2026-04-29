{ pkgs, lib, ... }:

let
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
    KRAKEN_REQ_HASH="krakenos-core-v17"
    REQ_HASH_FILE="$PWD/.devenv/state/kraken-requirements.hash"

    "$VENV_DIR/bin/python" -m pip install --upgrade pip "setuptools<82" wheel
    "$VENV_DIR/bin/python" -m pip install \
      -e . \
      numpy scipy matplotlib pandas pyvista vtk \
      PyVTK csv342 ipython ipykernel pyzmq \
      packaging setuptools basedpyright ruff PyQt5 sip \
      cloudpickle pybind11
    printf '%s\n' "$KRAKEN_REQ_HASH" > "$REQ_HASH_FILE"
  '';
in
{
  env = {
    GREET = "KrakenOS devenv";
    LD_LIBRARY_PATH = (lib.makeLibraryPath runtimeLibs) + ":/run/opengl-driver/lib:/run/opengl-driver-32/lib";
  };

  languages.python = {
    enable = true;
    package = pkgs.python313.withPackages (ps: [
      ps.tkinter
      ps.pythonocc-core
      ps.trimesh
      ps.meshio
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

    export MPLCONFIGDIR="$PWD/.devenv/state/matplotlib"
    mkdir -p "$MPLCONFIGDIR"

    if [ -n "''${WAYLAND_DISPLAY:-}" ] || [ -n "''${DISPLAY:-}" ]; then
      export MPLBACKEND=qtagg
    fi

    if [ -d /home/thinky/Projects/pagmo2/_install/lib64 ]; then
      export LD_LIBRARY_PATH="/home/thinky/Projects/pagmo2/_install/lib64:$LD_LIBRARY_PATH"
    fi

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

  scripts.kraken-install-gpu.exec = ''
    ${bootstrapVenv}
    ${installCoreDeps}
    "$VENV_DIR/bin/python" -m pip install cupy-cuda12x || true
    "$VENV_DIR/bin/python" -m pip install nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cufft-cu12 || true
    "$VENV_DIR/bin/python" -m pip install torch || true
  '';
}
