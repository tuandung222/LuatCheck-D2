"""Vector store backends (all optional dependencies are imported lazily)."""
from __future__ import annotations

import importlib
import importlib.util
from typing import Any, Dict, Optional

from ..errors import BackendUnavailableError, ConfigError
from .base import VectorStore
from .faiss_store import FAISS_TORCH_CONFLICT

# backend name -> (module, class, pip package, import name)
BACKENDS: Dict[str, tuple] = {
    "numpy": ("numpy_flat", "NumpyFlatStore", "numpy", "numpy"),
    "faiss": ("faiss_store", "FaissStore", "faiss-cpu", "faiss"),
    "sqlite_vec": ("sqlite_vec_store", "SqliteVecStore", "sqlite-vec", "sqlite_vec"),
    "lancedb": ("lancedb_store", "LanceDBStore", "lancedb", "lancedb"),
    "qdrant": ("qdrant_store", "QdrantStore", "qdrant-client", "qdrant_client"),
    "chroma": ("chroma_store", "ChromaStore", "chromadb", "chromadb"),
}
_ALIASES = {"flat": "numpy", "numpy_flat": "numpy", "faiss_flat": "faiss", "faiss-cpu": "faiss", "sqlite-vec": "sqlite_vec",
            "sqlitevec": "sqlite_vec", "lance": "lancedb", "chromadb": "chroma", "qdrant-client": "qdrant"}


def canonical_backend(name: str) -> str:
    key = _ALIASES.get(name, name)
    if key not in BACKENDS:
        raise ConfigError(f"unknown vector store backend {name!r}; choose one of {sorted(BACKENDS)}")
    return key


def get_store_class(backend: str) -> type:
    key = canonical_backend(backend)
    module, cls, package, import_name = BACKENDS[key]
    if importlib.util.find_spec(import_name) is None:  # presence check only: importing faiss here could poison a torch process
        raise BackendUnavailableError(
            f"vector store backend {key!r} needs the {package!r} package: uv pip install --python .venv/bin/python {package}"
        )
    return getattr(importlib.import_module(f"{__name__}.{module}"), cls)


def open_store(backend: str, path: Optional[str], collection: str, dim: Optional[int] = None, metric: str = "cosine",
               mode: str = "open_or_create", **params: Any) -> VectorStore:
    """Create/open a vector store by backend name. Raises BackendUnavailableError if its package is missing."""
    return get_store_class(backend).open(path, collection, dim, metric, mode, **params)


def backend_status() -> Dict[str, Dict[str, Any]]:
    """Availability of each backend on this machine: {backend: {available, version | reason}}.

    FAISS is only checked for presence (importing it can break a process that uses torch, see faiss_store.py);
    its entry carries `usable_with_torch: False`.
    """
    import importlib.metadata
    import sys
    out: Dict[str, Dict[str, Any]] = {}
    for name, (_, _, package, import_name) in BACKENDS.items():
        entry: Dict[str, Any] = {"package": package}
        try:
            if importlib.util.find_spec(import_name) is None:
                raise ImportError(f"No module named {import_name!r}")
            if name != "faiss":
                importlib.import_module(import_name)  # real import: catches broken native extensions
            try:
                entry["version"] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                entry["version"] = None
            entry["available"] = True
        except Exception as exc:  # ImportError or a native-load failure
            entry.update(available=False, reason=f"{type(exc).__name__}: {exc}")
        if name == "faiss":
            entry["usable_with_torch"] = False
            entry["note"] = FAISS_TORCH_CONFLICT
            entry["torch_loaded_in_this_process"] = "torch" in sys.modules
        out[name] = entry
    return out


__all__ = ["VectorStore", "FAISS_TORCH_CONFLICT", "BACKENDS", "open_store", "get_store_class", "backend_status", "canonical_backend"]
