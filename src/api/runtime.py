"""Per-profile runtime for the local web API: configuration, tool registry, corpus facts and UI-safe run events.

A profile runtime is one (config, corpus, tool registry) triple. The API can serve several of them in one process
(`LUATCHECK_WEB_CONFIGS=a.yaml,b.yaml`); they share the controller and reranker servers named in their configs.
Nothing here produces an answer: it only describes what is loaded and enriches the operational events of a real run.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from src.config.app_config import AppConfig, load_config
from src.domains import load_profile
from src.model_manager import ModelManager
from src.pipeline.builder import build_retriever, needs_model_manager
from src.tools.legal_tools import LegalToolRegistry

HINTS_PATH = Path(__file__).with_name("ui_hints.json")


@dataclass
class ProfileRuntime:
    """One loaded domain profile. `error` is set (and `registry` is None) when it could not be loaded."""
    key: str
    config_path: Optional[str]
    config: Optional[AppConfig] = None
    profile: Any = None
    registry: Optional[LegalToolRegistry] = None
    error: Optional[str] = None
    corpus_records: Optional[int] = None
    corpus_documents: Optional[int] = None

    @property
    def available(self) -> bool:
        return self.registry is not None and self.error is None


def load_ui_hints() -> Dict[str, Any]:
    """Per-domain presentation data (short name, scope note, example questions). Domain specifics stay in data."""
    try:
        data = json.loads(HINTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _corpus_counts(path: str) -> Dict[str, Optional[int]]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"records": None, "documents": None}
    if not isinstance(data, list):
        return {"records": None, "documents": None}
    sources = {str(r.get("source_name") or r.get("law_name") or "") for r in data if isinstance(r, dict)}
    return {"records": len(data), "documents": len(sources - {""})}


def _build_runtime(index: int, path: Optional[str]) -> ProfileRuntime:
    key = f"config_{index}"
    try:
        config = load_config(path)
        key = config.domain.profile
        runtime = ProfileRuntime(key=key, config_path=path, config=config)
        if not os.path.isfile(config.retrieval.corpus_path):
            runtime.error = f"Corpus file is unavailable: {config.retrieval.corpus_path}"
            return runtime
        profile = load_profile(config.domain.profile, config.domain.profile_variant)   # r2 configs load <id>_r2
        manager = ModelManager.shared(config.models) if needs_model_manager(config) else None
        runtime.profile = profile
        runtime.registry = LegalToolRegistry(
            corpus_path=config.retrieval.corpus_path,
            outbox_path=config.security.outbox_path,
            retriever=build_retriever(config.retrieval, corpus_path=config.retrieval.corpus_path,
                                      endpoint=config.model.endpoint, manager=manager, profile=profile),
            profile=profile,
        )
        counts = _corpus_counts(config.retrieval.corpus_path)
        runtime.corpus_records, runtime.corpus_documents = counts["records"], counts["documents"]
        return runtime
    except Exception as exc:  # a broken profile must not hide the working ones
        return ProfileRuntime(key=key, config_path=path, error=f"{type(exc).__name__}: {exc}")


def load_profile_runtimes() -> Dict[str, ProfileRuntime]:
    """Profiles to serve: `LUATCHECK_WEB_CONFIGS` (comma-separated paths), else the single default config."""
    raw = [p.strip() for p in os.getenv("LUATCHECK_WEB_CONFIGS", "").split(",") if p.strip()]
    runtimes: Dict[str, ProfileRuntime] = {}
    for index, path in enumerate(raw or [None]):
        runtime = _build_runtime(index, path)
        if runtime.key in runtimes:
            runtime = ProfileRuntime(key=f"{runtime.key}#{index}", config_path=path,
                                     error=f"Duplicate domain profile id in LUATCHECK_WEB_CONFIGS: {runtime.key}")
        runtimes[runtime.key] = runtime
    return runtimes


def default_runtime(runtimes: Dict[str, ProfileRuntime]) -> Optional[ProfileRuntime]:
    for runtime in runtimes.values():
        if runtime.available:
            return runtime
    return next(iter(runtimes.values()), None)


# --------------------------------------------------------------------------- descriptions for /capabilities

def reranker_endpoint_status(config: Optional[AppConfig]) -> Dict[str, Any]:
    """Reachability of the configured reranker server (never loads or runs a model)."""
    if config is None:
        return {"enabled": None, "reachable": None}
    cfg = config.retrieval.reranker
    status: Dict[str, Any] = {"enabled": bool(cfg.enabled), "backend": cfg.backend, "model": cfg.model,
                              "reachable": None}
    if cfg.enabled and cfg.backend in {"llamacpp_http", "qev_http"} and cfg.base_url:
        try:
            response = requests.get(cfg.base_url.rstrip("/") + "/health", timeout=1.5)
            status["reachable"] = bool(response.ok)
        except requests.RequestException:
            status["reachable"] = False
    return status


def describe_runtime(runtime: ProfileRuntime, hints: Dict[str, Any]) -> Dict[str, Any]:
    hint = hints.get(runtime.key) if isinstance(hints.get(runtime.key), dict) else {}
    info: Dict[str, Any] = {
        "id": runtime.key,
        "available": runtime.available,
        "error": runtime.error,
        "short_name": hint.get("short_name"),
        "scope_note": hint.get("scope_note"),
        "suggestions": hint.get("suggestions") if isinstance(hint.get("suggestions"), list) else [],
        "config_file": Path(runtime.config_path).name if runtime.config_path else None,
    }
    if runtime.profile is not None:
        info.update({
            "display_name": runtime.profile.display_name,
            "source_name": runtime.profile.source_name,
            "language": runtime.profile.language,
            "search_tool": runtime.profile.tools.search.name,
            "read_tool": runtime.profile.tools.read.name,
            "id_example": runtime.profile.ids.example,
        })
    if runtime.config is not None:
        cfg = runtime.config
        rr = cfg.retrieval.reranker
        info.update({
            "corpus": {"records": runtime.corpus_records, "documents": runtime.corpus_documents},
            "retrieval": {
                "mode": cfg.retrieval.mode, "first_stage": cfg.retrieval.dense_model_type,
                "reranker": {"enabled": bool(rr.enabled), "backend": rr.backend if rr.enabled else None,
                             "model": rr.model if rr.enabled else None,
                             "top_k_in": rr.top_k_in if rr.enabled else None,
                             "top_k_out": rr.top_k_out if rr.enabled else None},
            },
            "verifier_mode": str(getattr(cfg.verifier.mode, "value", cfg.verifier.mode)),
            "budgets": {"max_tool_calls": cfg.budgets.max_tool_calls, "max_repairs": cfg.budgets.max_repairs,
                        "max_steps": cfg.budgets.max_steps, "wall_seconds": cfg.budgets.wall_seconds},
        })
    return info


# --------------------------------------------------------------------------- run events

def _compact_rerank(metadata: Any) -> Optional[Dict[str, Any]]:
    rerank = metadata.get("rerank") if isinstance(metadata, dict) else None
    if not isinstance(rerank, dict):
        return None
    keys = ("backend", "model", "top_k_in", "top_k_out", "n_candidates", "n_scored", "n_truncated", "first_stage_ms",
            "wall_ms", "ms_per_pair")
    out = {k: rerank.get(k) for k in keys if rerank.get(k) is not None}
    out["first_stage_ids"] = [str(i) for i in (rerank.get("first_stage_ids") or [])][:20]
    out["reranked_ids"] = [str(i) for i in (rerank.get("reranked_ids") or [])][:10]
    return out


def make_event_sink(record: Callable[[str, Dict[str, Any]], None], holder: Dict[str, Any],
                    title_of: Callable[[str], str]) -> Callable[[str, Dict[str, Any]], None]:
    """Event sink for `LuatCheckAgent`: stores each operational event with measured extras read from the ledger.

    Added fields are copies of values the core already recorded (search query, ids, reranker run, the last model
    call's measured wall time and token counts, repair feedback). Prompts and model thoughts are never included.
    `holder["agent"]` is set by the caller once the agent exists; `holder["state"]` is readable afterwards.
    """
    state: Dict[str, Any] = holder.setdefault("state", {})
    state.update({"t0": None, "seen_calls": 0, "last_verification_passed": None})

    def sink(name: str, data: Dict[str, Any]) -> None:
        payload = dict(data)
        now = time.monotonic()
        if name == "run_started" or state["t0"] is None:
            state["t0"] = now
        payload["t_ms"] = round((now - state["t0"]) * 1000.0, 1)
        if name == "model_call_started":
            state["last_verification_passed"] = None
        if name == "verification_completed":
            state["last_verification_passed"] = bool(data.get("passed"))
        agent = holder.get("agent")
        ledger = getattr(agent, "ledger", None)
        if ledger is not None:
            try:
                _enrich(name, payload, ledger, state, title_of)
            except Exception:
                pass  # observability must never change a run
        record(name, payload)

    return sink


def _last_event(ledger: Any, kind: str) -> Optional[Dict[str, Any]]:
    for event in reversed(ledger.audit_events):
        if event.get("event") == kind:
            return event
    return None


def _enrich(name: str, payload: Dict[str, Any], ledger: Any, state: Dict[str, Any],
            title_of: Callable[[str], str]) -> None:
    calls = ledger.llm_calls
    if name in {"tool_completed", "verification_completed", "run_finished"} and len(calls) > state["seen_calls"]:
        call = calls[-1]
        response = call.get("response") if isinstance(call.get("response"), dict) else {}
        payload["model"] = {
            "wall_ms": call.get("wall_ms"), "input_tokens": call.get("input_tokens"),
            "output_tokens": call.get("output_tokens"), "outcome": call.get("outcome"),
            "error_kind": call.get("error_kind"), "action": response.get("action"),
        }
        state["seen_calls"] = len(calls)
    if name == "tool_completed":
        record = _last_event(ledger, "tool_call") or {}
        args = record.get("args") if isinstance(record.get("args"), dict) else {}
        if args.get("query") is not None:
            payload["query"] = str(args.get("query"))[:400]
        if args.get("article_id") is not None:
            payload["requested_id"] = str(args.get("article_id"))[:200]
        ids = [str(i) for i in payload.get("article_ids", [])][:10]
        payload["results"] = [{"id": i, "title": title_of(i)} for i in ids]
        rerank = _compact_rerank(record.get("metadata"))
        if rerank is not None:
            payload["rerank"] = rerank
    elif name == "repair_started":
        record = _last_event(ledger, "repair") or {}
        if record.get("feedback"):
            payload["feedback"] = str(record["feedback"])[:800]
    elif name == "run_finished" and ledger.audit_events:
        failed = ledger.audit_events[-1]
        if failed.get("event") == "tool_call" and isinstance(failed.get("error"), dict):
            args = failed.get("args") if isinstance(failed.get("args"), dict) else {}
            payload["failed_tool"] = {"tool": failed.get("tool"), "query": str(args.get("query", ""))[:400],
                                      "error_kind": failed["error"].get("kind")}
