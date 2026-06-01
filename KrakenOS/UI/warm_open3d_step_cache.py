"""Build Open 3D STEP display caches outside the Tk UI process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time


class _StepCacheWarmupLoader:
    def __init__(self) -> None:
        from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

        class Loader(LayoutPolylineDisplayMixin):
            def __init__(self) -> None:
                self._external_cad_mesh_cache = {}
                self.messages: list[str] = []

            def append_debug(self, message: str) -> None:
                if message:
                    self.messages.append(str(message))

        self._loader = Loader()

    @property
    def messages(self) -> list[str]:
        return list(getattr(self._loader, "messages", []) or [])

    def warm(self, path: Path, *, largest_component: bool, warm_axis: bool) -> dict[str, object]:
        start = time.perf_counter()
        mesh = self._loader._load_step_mesh(path, largest_component=bool(largest_component))
        axis = None
        axis_start = time.perf_counter()
        if bool(warm_axis):
            try:
                axis = self._loader._step_primary_cylinder_axis(path)
            except Exception:
                axis = None
        return {
            "path": str(path),
            "largest_component": bool(largest_component),
            "points": int(getattr(mesh, "n_points", 0)),
            "cells": int(getattr(mesh, "n_cells", 0)),
            "axis_cached": axis is not None,
            "axis_duration_s": round(float(time.perf_counter() - axis_start), 3),
            "duration_s": round(float(time.perf_counter() - start), 3),
        }


def _parse_spec(raw: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON spec: {exc}") from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("spec must be a JSON object")
    path = Path(str(value.get("path", "") or "")).expanduser()
    if not path.exists():
        raise argparse.ArgumentTypeError(f"STEP path does not exist: {path}")
    return {
        "label": str(value.get("label", "") or ""),
        "path": path,
        "largest_component": bool(value.get("largest_component", False)),
        "warm_axis": bool(value.get("warm_axis", str(value.get("label", "") or "").strip().lower() == "lens")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", action="append", default=[], type=_parse_spec)
    args = parser.parse_args(argv)
    loader = _StepCacheWarmupLoader()
    results: list[dict[str, object]] = []
    errors: list[str] = []
    for spec in list(args.spec or []):
        path = Path(spec["path"])
        label = str(spec.get("label", "") or path.stem)
        try:
            result = loader.warm(
                path,
                largest_component=bool(spec.get("largest_component", False)),
                warm_axis=bool(spec.get("warm_axis", False)),
            )
            result["label"] = label
            results.append(result)
        except Exception as exc:
            errors.append(f"{label}:{path.name}: {exc}")
    summary = {
        "ok": not errors,
        "results": results,
        "errors": errors,
        "messages": loader.messages[-12:],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
