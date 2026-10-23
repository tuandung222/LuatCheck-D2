"""ModelManager: one shared, lazily loaded, budgeted instance per model component.

The application wiring (agent loop, search tool, verification pipeline) obtains rerankers and NLI backends from a
``ModelManager`` instead of building them directly:

* one shared instance per (kind, backend, model, device, dtype, base_url, max_length): two agents (or a reranker
  and a later benchmark task) that configure the same model use the same loaded weights;
* lazy: building a handle loads nothing; the weights are loaded by the first ``use()``;
* ``idle_unload_seconds``: a model unused for that long is unloaded by ``sweep()``, which runs on every access
  (``use()``) and, optionally, from a background timer thread (``start_idle_timer``). The timer only calls
  ``sweep()``; it never runs inference. A model in use is never unloaded;
* ``max_resident_gb``: before a load, least-recently-used idle models are unloaded until the estimated resident
  total plus the new model fits; if it cannot fit (or the model alone is larger than the budget) a
  ``ModelBudgetError`` is raised instead of loading;
* ``min_free_gb``: a load is refused when available system memory is below the floor;
* every failure is a ``ModelComponentError`` (kind ``memory_budget`` for the two budget checks); nothing falls
  back to another model or to a substitute score (AGENTS.md).

Estimates are sizes of the weights as they will be held (safetensors headers of the locally cached snapshot x the
requested dtype width), not measurements; after a load the measured RSS + accelerator delta is recorded next to
the estimate (``info()['measured_gb']``) and the larger of the two is used for the budget. Remote backends
(``qev_http``, ``llamacpp_http``) hold no local weights and cost nothing.
"""
from __future__ import annotations

import contextlib
import json
import os
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from src.model_runtime import ModelComponentError

__all__ = ["ModelBudgetError", "ManagedModel", "ModelManager", "available_memory_gb", "estimate_weights_gb"]

_DTYPE_BYTES = {"float32": 4, "fp32": 4, "float16": 2, "fp16": 2, "bfloat16": 2, "bf16": 2}
_ST_BYTES = {"F32": 4, "F16": 2, "BF16": 2, "F64": 8, "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1}
_GB = 1024.0 ** 3


class ModelBudgetError(ModelComponentError):
    """A load was refused because it would exceed the resident budget or the free-memory floor."""

    def __init__(self, message: str):
        super().__init__(message, kind="memory_budget")


# --------------------------------------------------------------------------- #
# Memory helpers
# --------------------------------------------------------------------------- #

def available_memory_gb() -> float:
    """Memory the OS can hand out without swapping (macOS: free + inactive + speculative + purgeable pages)."""
    if sys.platform == "darwin":
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, check=True).stdout
        page = 4096
        pages: Dict[str, int] = {}
        for line in out.splitlines():
            if "page size of" in line:
                page = int(line.split("page size of")[1].split()[0])
            elif ":" in line:
                key, _, value = line.partition(":")
                value = value.strip().rstrip(".")
                if value.isdigit():
                    pages[key.strip()] = int(value)
        usable = sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"))
        return usable * page / _GB
    with open("/proc/meminfo", encoding="utf-8") as handle:  # Linux
        for line in handle:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024.0 * 1024.0)
    raise ModelComponentError("cannot determine available memory on this platform", kind="config_error")


def _process_footprint_gb() -> float:
    """RSS of this process plus the Metal allocation (RSS alone under-reports MPS weights)."""
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True, check=False)
    rss = int(out.stdout.strip() or 0) / (1024.0 * 1024.0)
    mps = 0.0
    torch = sys.modules.get("torch")
    if torch is not None and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        mps = torch.mps.current_allocated_memory() / _GB
    return rss + mps


def estimate_weights_gb(model: str, dtype: Optional[str], default_gb: float, local_files_only: bool = True
                        ) -> Tuple[float, str]:
    """(GB, source). Parameter count from the safetensors headers of the cached snapshot x requested dtype width."""
    width = _DTYPE_BYTES.get((dtype or "float32").lower())
    if width is None:
        raise ModelComponentError(f"unknown dtype {dtype!r}; use float32|float16|bfloat16", kind="config_error")
    folder: Optional[Path] = None
    if Path(model).is_dir():
        folder = Path(model)
    else:
        try:
            from huggingface_hub import snapshot_download
            folder = Path(snapshot_download(model, local_files_only=True, allow_patterns=["*.safetensors"]))
        except Exception:  # noqa: BLE001 - not cached (or no hub library): fall back to the configured default
            folder = None
    if folder is not None:
        params = 0
        for file in folder.glob("*.safetensors"):
            with open(file, "rb") as handle:
                (header_len,) = struct.unpack("<Q", handle.read(8))
                header = json.loads(handle.read(header_len))
            for name, meta in header.items():
                if name == "__metadata__":
                    continue
                count = 1
                for dim in meta["shape"]:
                    count *= dim
                params += count
        if params:
            return params * width / _GB, "safetensors_header"
    return default_gb, "default_estimate"


# --------------------------------------------------------------------------- #
# Managed handle
# --------------------------------------------------------------------------- #

@dataclass(eq=False)
class ManagedModel:
    """Handle to one shared component. ``use()`` is the only way to run it."""

    manager: "ModelManager"
    key: Tuple[Any, ...]
    kind: str                       # "reranker" | "nli" | custom
    component: Any                  # BaseReranker / BaseNLIBackend (or any object with load()/unload())
    remote: bool                    # True: holds no local weights, never counted or unloaded
    estimate_gb: float
    estimate_source: str
    measured_gb: Optional[float] = None
    load_fn: Optional[Callable[[], Any]] = None
    unload_fn: Optional[Callable[[], Any]] = None
    last_used: float = field(default_factory=time.monotonic)
    in_use: int = 0
    loads: int = 0
    unloads: int = 0
    resident: bool = False

    @contextlib.contextmanager
    def use(self) -> Iterator[Any]:
        """Make sure the weights are resident (sweeping idle models and enforcing the budget first), then yield the component."""
        self.manager._acquire(self)
        try:
            yield self.component
        finally:
            self.manager._release(self)

    def info(self) -> Dict[str, Any]:
        return {"kind": self.kind, "key": [str(part) for part in self.key], "resident": self.resident, "remote": self.remote,
                "estimate_gb": round(self.estimate_gb, 3), "estimate_source": self.estimate_source,
                "measured_gb": None if self.measured_gb is None else round(self.measured_gb, 3),
                "loads": self.loads, "unloads": self.unloads, "in_use": self.in_use,
                "idle_seconds": round(time.monotonic() - self.last_used, 3)}


class ModelManager:
    """Shared registry of model components with idle unload and a resident-memory budget."""

    _shared: Optional["ModelManager"] = None
    _shared_lock = threading.Lock()

    def __init__(self, idle_unload_seconds: float = 600.0, max_resident_gb: float = 4.0, min_free_gb: float = 1.0,
                 default_estimate_gb: float = 2.5, wait_for_quiet_machine_gb: Optional[float] = None):
        self._lock = threading.RLock()
        self._models: Dict[Tuple[Any, ...], ManagedModel] = {}
        self._timer: Optional[threading.Thread] = None
        self._timer_stop = threading.Event()
        self.configure(idle_unload_seconds, max_resident_gb, min_free_gb, default_estimate_gb, wait_for_quiet_machine_gb)

    def configure(self, idle_unload_seconds: float, max_resident_gb: float, min_free_gb: float,
                  default_estimate_gb: float = 2.5, wait_for_quiet_machine_gb: Optional[float] = None) -> None:
        if idle_unload_seconds < 0 or max_resident_gb <= 0 or min_free_gb < 0 or default_estimate_gb <= 0:
            raise ModelComponentError("ModelManager limits must be positive (idle_unload_seconds/min_free_gb may be 0)",
                                      kind="config_error")
        self.idle_unload_seconds = float(idle_unload_seconds)
        self.max_resident_gb = float(max_resident_gb)
        self.min_free_gb = float(min_free_gb)
        self.default_estimate_gb = float(default_estimate_gb)
        self.wait_for_quiet_machine_gb = wait_for_quiet_machine_gb

    @classmethod
    def from_config(cls, models_cfg: Any) -> "ModelManager":
        return cls(models_cfg.idle_unload_seconds, models_cfg.max_resident_gb, models_cfg.min_free_gb,
                   models_cfg.default_estimate_gb, models_cfg.wait_for_quiet_machine_gb)

    @classmethod
    def shared(cls, models_cfg: Any = None) -> "ModelManager":
        """Process-wide manager (created on first call); a later config updates its limits, it does not create a second manager."""
        with cls._shared_lock:
            if cls._shared is None:
                cls._shared = cls.from_config(models_cfg) if models_cfg is not None else cls()
            elif models_cfg is not None:
                cls._shared.configure(models_cfg.idle_unload_seconds, models_cfg.max_resident_gb, models_cfg.min_free_gb,
                                      models_cfg.default_estimate_gb, models_cfg.wait_for_quiet_machine_gb)
            return cls._shared

    # ---- handles ------------------------------------------------------- #
    def reranker(self, cfg: Any) -> ManagedModel:
        """Shared handle for a `RerankerConfig`. top_k_in/out are not given to the component: the search tool applies them."""
        from src.retrieval.rerankers import build_reranker
        comp_cfg = cfg.component_config()
        key = ("reranker", comp_cfg["backend"], str(cfg.model or cfg.base_url), cfg.device if cfg.is_local else "server",
               cfg.dtype or "default", cfg.base_url or "", cfg.max_length if (cfg.is_local or cfg.backend == "llamacpp_http") else 0,
               cfg.chunk_chars, cfg.chunk_overlap_chars)
        return self._handle(key, "reranker", cfg.is_local, lambda: build_reranker(comp_cfg), cfg.model, cfg.dtype or "float32",
                            cfg.local_files_only)

    def nli(self, cfg: Any) -> ManagedModel:
        """Shared handle for a `NLIConfig`."""
        from src.verifier.nli_backends import build_nli_backend
        comp_cfg = cfg.component_config()
        backend = comp_cfg["backend"]
        local = backend in ("cross_encoder", "decision_model")
        key = ("nli", backend, str(comp_cfg.get("model") or comp_cfg.get("base_url") or comp_cfg.get("endpoint")),
               comp_cfg.get("device", "auto") if local else "server", str(comp_cfg.get("dtype") or "default"),
               comp_cfg.get("base_url") or comp_cfg.get("endpoint") or "", comp_cfg.get("max_length", 0) if local else 0)
        dtype = comp_cfg.get("dtype") or "float32"   # mDeBERTa is forced to fp32 by the backend (require_fp32)
        return self._handle(key, "nli", local, lambda: build_nli_backend(comp_cfg), comp_cfg.get("model"), dtype,
                            bool(comp_cfg.get("local_files_only", False)))

    def register(self, key: Tuple[Any, ...], kind: str, component: Any, load_fn: Callable[[], Any],
                 unload_fn: Callable[[], Any], estimate_gb: float) -> ManagedModel:
        """Manage an externally built component (e.g. the embedding provider of a hybrid index)."""
        with self._lock:
            handle = self._models.get(key)
            if handle is None:
                handle = ManagedModel(self, key, kind, component, False, float(estimate_gb), "caller_estimate",
                                      load_fn=load_fn, unload_fn=unload_fn)
                self._models[key] = handle
            return handle

    def _handle(self, key: Tuple[Any, ...], kind: str, local: bool, build: Callable[[], Any], model: Optional[str],
                dtype: str, local_files_only: bool) -> ManagedModel:
        with self._lock:
            handle = self._models.get(key)
            if handle is not None:
                return handle
            component = build()
            if component is None:
                raise ModelComponentError(f"{kind}: configuration builds no component (backend 'none'?)", kind="config_error")
            if local:
                gb, source = estimate_weights_gb(model or "", dtype, self.default_estimate_gb, local_files_only)
            else:
                gb, source = 0.0, "remote"
            handle = ManagedModel(self, key, kind, component, not local, gb, source)
            self._models[key] = handle
            return handle

    # ---- accounting ---------------------------------------------------- #
    def _cost(self, handle: ManagedModel) -> float:
        return max(handle.estimate_gb, handle.measured_gb or 0.0)

    def resident_gb(self) -> float:
        with self._lock:
            return sum(self._cost(h) for h in self._models.values() if h.resident and not h.remote)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {"max_resident_gb": self.max_resident_gb, "min_free_gb": self.min_free_gb,
                    "idle_unload_seconds": self.idle_unload_seconds, "resident_estimate_gb": round(self.resident_gb(), 3),
                    "models": [h.info() for h in self._models.values()]}

    # ---- lifecycle ----------------------------------------------------- #
    def _unload(self, handle: ManagedModel) -> None:
        if handle.unload_fn is not None:
            handle.unload_fn()
        else:
            handle.component.unload()
        handle.resident = False
        handle.unloads += 1

    def sweep(self) -> List[str]:
        """Unload every idle model unused for `idle_unload_seconds`. Never touches a model in use. Returns the unloaded keys."""
        done: List[str] = []
        now = time.monotonic()
        with self._lock:
            for handle in self._models.values():
                if handle.resident and not handle.remote and handle.in_use == 0 \
                        and now - handle.last_used >= self.idle_unload_seconds:
                    self._unload(handle)
                    done.append("/".join(str(p) for p in handle.key[:3]))
        return done

    def unload(self, handle: ManagedModel) -> bool:
        """Unload one model now if it is resident and not in use. Returns whether it was unloaded."""
        with self._lock:
            if handle.resident and not handle.remote and handle.in_use == 0:
                self._unload(handle)
                return True
            return False

    def unload_all(self) -> None:
        """Unload every resident model that is not in use (handles stay valid and reload on the next use)."""
        with self._lock:
            for handle in self._models.values():
                if handle.resident and not handle.remote and handle.in_use == 0:
                    self._unload(handle)

    def start_idle_timer(self, interval_seconds: float = 30.0) -> None:
        """Background thread that only calls `sweep()`. It never runs inference and never loads a model."""
        with self._lock:
            if self._timer is not None and self._timer.is_alive():
                return
            self._timer_stop.clear()

            def loop() -> None:
                while not self._timer_stop.wait(interval_seconds):
                    self.sweep()

            self._timer = threading.Thread(target=loop, name="model-manager-idle-sweep", daemon=True)
            self._timer.start()

    def stop_idle_timer(self) -> None:
        self._timer_stop.set()
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.join(timeout=5)

    # ---- acquire / release --------------------------------------------- #
    def _acquire(self, handle: ManagedModel) -> None:
        with self._lock:
            self.sweep()
            handle.in_use += 1
            handle.last_used = time.monotonic()
            if handle.remote or handle.resident:
                return
            try:
                self._make_room(handle)
                self._load(handle)
            except BaseException:
                handle.in_use -= 1
                raise

    def _release(self, handle: ManagedModel) -> None:
        with self._lock:
            handle.in_use -= 1
            handle.last_used = time.monotonic()

    def _make_room(self, handle: ManagedModel) -> None:
        cost = self._cost(handle)
        if cost > self.max_resident_gb:
            raise ModelBudgetError(
                f"{handle.kind} {handle.key[2]!r} needs about {cost:.2f} GB ({handle.estimate_source}) but "
                f"models.max_resident_gb is {self.max_resident_gb:.2f}; raise the budget or choose a smaller model")
        while self.resident_gb() + cost > self.max_resident_gb:
            idle = [h for h in self._models.values() if h.resident and not h.remote and h.in_use == 0 and h is not handle]
            if not idle:
                raise ModelBudgetError(
                    f"loading {handle.kind} {handle.key[2]!r} (about {cost:.2f} GB) would exceed models.max_resident_gb="
                    f"{self.max_resident_gb:.2f} (resident {self.resident_gb():.2f} GB, all of it in use)")
            self._unload(min(idle, key=lambda h: h.last_used))
        if self.wait_for_quiet_machine_gb:
            from src.indexing.resources import wait_for_quiet_machine
            wait_for_quiet_machine(self.wait_for_quiet_machine_gb)
        available = available_memory_gb()
        if available < self.min_free_gb:
            raise ModelBudgetError(
                f"only {available:.2f} GB of memory is available, below models.min_free_gb={self.min_free_gb:.2f}; "
                f"not loading {handle.kind} {handle.key[2]!r}")

    def _load(self, handle: ManagedModel) -> None:
        before = _process_footprint_gb()
        if handle.load_fn is not None:
            handle.load_fn()
        else:
            handle.component.load()
        handle.measured_gb = max(_process_footprint_gb() - before, 0.0)
        handle.resident = True
        handle.loads += 1
