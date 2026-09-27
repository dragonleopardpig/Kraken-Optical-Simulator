"""Run a display-backed validator in its own process, for the penta harness (bugs/0914).

Some validators open their OWN editor and 3D inspector. The penta harness owns the single
embedded inspector of its process, and a second one cannot open beside it (bugs/0661), so such
a validator is gated by running its ``__main__`` in a child process and reporting the outcome.
The child inherits the environment, so a gate run inside ``devenv shell`` keeps its Nix binaries.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_module_isolated(module_name: str, *, timeout: float = 1500.0) -> "tuple[bool, list[str]]":
    """``(passed, notes)`` for ``python -m module_name``: passed is exit status 0. Info notes
    carry "=" (the harness counts the rest as failures); a failure adds the output's last lines."""
    try:
        proc = subprocess.run([sys.executable, "-m", module_name], capture_output=True, text=True,
                              timeout=timeout, env=dict(os.environ), cwd=str(PROJECT_ROOT))
    except subprocess.TimeoutExpired:
        return False, [f"{module_name} timed out after {timeout:g} s"]
    lines = [line for line in (proc.stdout + "\n" + proc.stderr).splitlines()
             if line.strip() and "obbTree" not in line and "vtkOBBTree" not in line
             and "val = self.func" not in line]
    if proc.returncode == 0:
        return True, [f"{module_name} = passed in its own process"]
    return False, [f"{module_name} exited {proc.returncode}"] + lines[-6:]
