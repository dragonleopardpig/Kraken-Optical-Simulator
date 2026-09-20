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
    KRAKEN_REQ_HASH="krakenos-core-v24-shapely"
    REQ_HASH_FILE="$PWD/.devenv/state/kraken-requirements.hash"

    "$VENV_DIR/bin/python" -m pip install --upgrade pip "setuptools<82" wheel
    "$VENV_DIR/bin/python" -m pip install \
      -e . \
      numpy scipy matplotlib pandas pyvista \
      PyVTK csv342 ipython ipykernel pyzmq \
      packaging setuptools basedpyright ruff PyQt5 sip \
      cloudpickle pybind11 pygmo pdfplumber \
      rapidocr-onnxruntime shapely
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
    # bugs/0787 datasheet OCR, for sheets that print their spec table as a picture. bugs/0788
    # prefers the in-process rapidocr engine added above; these stay as the fallback for a
    # checkout that has not installed it.
    poppler-utils      # pdftoppm -- renders at 300 dpi, which is what keeps "110+-2" readable
    tesseract
    # A vendor DWG carries its spec table as TEXT entities with coordinates, so a label pairs
    # with its value by GEOMETRY. dwgread -O JSON reads them; see bugs/0788's closing note.
    libredwg
  ] ++ runtimeLibs;

  enterShell = ''
    ${bootstrapVenv}

    export PATH="$VENV_DIR/bin:$PATH"

    export MPLCONFIGDIR="$PWD/.devenv/state/matplotlib"
    mkdir -p "$MPLCONFIGDIR"

    if [ -n "''${WAYLAND_DISPLAY:-}" ] || [ -n "''${DISPLAY:-}" ]; then
      export MPLBACKEND=qtagg
    fi

    # HiDPI: the editor scales itself (KRAKEN_UI_SCALE) because Tk runs on
    # XWayland, which the compositor would otherwise upscale and blur.  Follow
    # the focused monitor's scale when the compositor can tell us; an explicit
    # value in the environment always wins.  (`direnv reload` after changing
    # the monitor scale.)
    if [ -z "''${KRAKEN_UI_SCALE:-}" ] && command -v hyprctl >/dev/null 2>&1; then
      kraken_ui_scale="$(hyprctl monitors -j 2>/dev/null | "$VENV_DIR/bin/python" -c '
import json, sys
try:
    monitors = json.load(sys.stdin)
except Exception:
    sys.exit(0)
focused = [m for m in monitors if m.get("focused")] or monitors
if focused:
    print(focused[0].get("scale", 1))
' 2>/dev/null)"
      if [ -n "$kraken_ui_scale" ] && [ "$kraken_ui_scale" != "1" ] && [ "$kraken_ui_scale" != "1.0" ]; then
        export KRAKEN_UI_SCALE="$kraken_ui_scale"
      fi
      unset kraken_ui_scale
    fi

    # Do not inject project-local pagmo2 into LD_LIBRARY_PATH here: VTK's
    # OpenTURNS module must load the ABI-matched pagmo from its Nix closure.

    # Add CUDA wheel shared libraries (CuPy/Torch) into runtime search path.
    for nvidia_lib_dir in "$VENV_DIR"/lib/python*/site-packages/nvidia/*/lib; do
      if [ -d "$nvidia_lib_dir" ]; then
        export LD_LIBRARY_PATH="$nvidia_lib_dir:$LD_LIBRARY_PATH"
      fi
    done

    if ! "$VENV_DIR/bin/python" -c 'import numpy, scipy, matplotlib, pyvista, vtk, pygmo' >/dev/null 2>&1; then
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
