"""In-memory CAD scene caches for Open 3D display and picking.

This module is intentionally backend-neutral. It caches the existing STL/mesh
path today and gives the later OpenCascade/CadQuery adapter the same boundary:
document/source identity, triangle arrays, and cached face-pick artifacts.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

import numpy as np


TriangleReader = Callable[[Path], tuple[str, np.ndarray]]
OutlineBuilder = Callable[[np.ndarray], object | None]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class CadDocumentKey:
    """Stable identity for one CAD-derived mesh source."""

    path: str
    size: int
    mtime_ns: int

    @classmethod
    def from_path(cls, path: Path | str) -> "CadDocumentKey":
        resolved = Path(path).expanduser()
        try:
            stat = resolved.stat()
            return cls(
                path=str(resolved),
                size=int(getattr(stat, "st_size", 0)),
                mtime_ns=int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
            )
        except OSError:
            return cls(path=str(resolved), size=-1, mtime_ns=-1)


@dataclass(frozen=True, slots=True)
class CadTriangleArray:
    """Cached triangle view for display, hover picking, and optical adapters."""

    key: CadDocumentKey
    file_format: str
    triangles: np.ndarray

    @property
    def valid(self) -> bool:
        return (
            self.triangles.ndim == 3
            and self.triangles.shape[1:] == (3, 3)
            and self.triangles.shape[0] > 0
        )

    @property
    def all_points(self) -> np.ndarray | None:
        if not self.valid:
            return None
        return self.triangles.reshape((-1, 3))


class _BoundedOrderedCache(OrderedDict):
    """Small LRU map used to bound large vendor STEP-derived mesh artifacts."""

    def __init__(self, max_entries: int) -> None:
        super().__init__()
        self.max_entries = max(1, int(max_entries))

    def remember(self, key: object, value: T) -> T:
        if key in self:
            del self[key]
        self[key] = value
        while len(self) > self.max_entries:
            self.popitem(last=False)
        return value


class CadDocumentCache:
    """Cache CAD-derived triangle arrays by source path and file stamp."""

    def __init__(self, *, max_entries: int = 24) -> None:
        self._triangles: _BoundedOrderedCache = _BoundedOrderedCache(max_entries)

    def triangle_array(self, path: Path | str, reader: TriangleReader) -> CadTriangleArray:
        key = CadDocumentKey.from_path(path)
        cached = self._triangles.get(key)
        if isinstance(cached, CadTriangleArray):
            self._triangles.move_to_end(key)
            return cached
        file_format, triangles = reader(Path(path).expanduser())
        array = np.asarray(triangles, dtype=float)
        entry = CadTriangleArray(key=key, file_format=str(file_format or ""), triangles=array)
        return self._triangles.remember(key, entry)

    def clear_path(self, path: Path | str) -> None:
        path_text = str(Path(path).expanduser())
        for key in list(self._triangles.keys()):
            if isinstance(key, CadDocumentKey) and key.path == path_text:
                self._triangles.pop(key, None)

    def clear(self) -> None:
        self._triangles.clear()


class CadPickCache:
    """Cache face triangle slices and prebuilt highlight outlines."""

    def __init__(self, *, max_face_entries: int = 4096, max_outline_entries: int = 4096) -> None:
        self._face_triangles: _BoundedOrderedCache = _BoundedOrderedCache(max_face_entries)
        self._face_outlines: _BoundedOrderedCache = _BoundedOrderedCache(max_outline_entries)

    @staticmethod
    def face_triangle_indices(face: dict[str, object]) -> tuple[int, ...]:
        values = face.get("triangle_indices", face.get("cell_indices", ()))
        indices: list[int] = []
        if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
            for value in values:
                try:
                    index = int(value)
                except Exception:
                    continue
                if index >= 0:
                    indices.append(index)
        return tuple(indices)

    @staticmethod
    def _face_id(face: dict[str, object]) -> str:
        for key in ("component_face_id", "face_id", "label"):
            value = str(face.get(key, "") or "").strip()
            if value:
                return value
        return ""

    def _face_cache_key(self, document_key: CadDocumentKey, face: dict[str, object]) -> tuple[object, ...]:
        indices = self.face_triangle_indices(face)
        return (document_key, self._face_id(face), indices)

    def face_triangles(
        self,
        document_cache: CadDocumentCache,
        path: Path | str,
        face: dict[str, object],
        reader: TriangleReader,
    ) -> np.ndarray:
        document = document_cache.triangle_array(path, reader)
        cache_key = self._face_cache_key(document.key, face)
        cached = self._face_triangles.get(cache_key)
        if isinstance(cached, np.ndarray):
            self._face_triangles.move_to_end(cache_key)
            return cached
        if not document.valid:
            result = np.empty((0, 3, 3), dtype=float)
            return self._face_triangles.remember(cache_key, result)
        indices = [index for index in self.face_triangle_indices(face) if 0 <= index < int(document.triangles.shape[0])]
        if not indices:
            result = np.empty((0, 3, 3), dtype=float)
        else:
            result = np.asarray(document.triangles[np.asarray(indices, dtype=int)], dtype=float)
        return self._face_triangles.remember(cache_key, result)

    def face_outline(
        self,
        document_cache: CadDocumentCache,
        path: Path | str,
        face: dict[str, object],
        reader: TriangleReader,
        builder: OutlineBuilder,
    ) -> object | None:
        document = document_cache.triangle_array(path, reader)
        cache_key = self._face_cache_key(document.key, face)
        if cache_key in self._face_outlines:
            self._face_outlines.move_to_end(cache_key)
            return self._face_outlines[cache_key]
        triangles = self.face_triangles(document_cache, path, face, reader)
        outline = builder(triangles) if triangles.size else None
        return self._face_outlines.remember(cache_key, outline)

    def clear_path(self, path: Path | str) -> None:
        path_text = str(Path(path).expanduser())
        for cache in (self._face_triangles, self._face_outlines):
            for key in list(cache.keys()):
                document_key = key[0] if isinstance(key, tuple) and key else None
                if isinstance(document_key, CadDocumentKey) and document_key.path == path_text:
                    cache.pop(key, None)

    def clear(self) -> None:
        self._face_triangles.clear()
        self._face_outlines.clear()


class CadSceneCache:
    """Facade for CAD document/display/pick caches used by Open 3D."""

    def __init__(
        self,
        *,
        max_documents: int = 24,
        max_face_entries: int = 4096,
        max_outline_entries: int = 4096,
    ) -> None:
        self.documents = CadDocumentCache(max_entries=max_documents)
        self.pick = CadPickCache(max_face_entries=max_face_entries, max_outline_entries=max_outline_entries)

    def triangle_array(self, path: Path | str, reader: TriangleReader) -> CadTriangleArray:
        return self.documents.triangle_array(path, reader)

    def face_triangles(self, path: Path | str, face: dict[str, object], reader: TriangleReader) -> np.ndarray:
        return self.pick.face_triangles(self.documents, path, face, reader)

    def face_outline(
        self,
        path: Path | str,
        face: dict[str, object],
        reader: TriangleReader,
        builder: OutlineBuilder,
    ) -> object | None:
        return self.pick.face_outline(self.documents, path, face, reader, builder)

    def clear_path(self, path: Path | str) -> None:
        self.documents.clear_path(path)
        self.pick.clear_path(path)

    def clear(self) -> None:
        self.documents.clear()
        self.pick.clear()
