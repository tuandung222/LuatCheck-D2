"""Same-origin local HTTP API. Every answer comes from the configured LuatCheck core."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import queue
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agent.loop import LuatCheckAgent
from src.config.app_config import AppConfig, load_config
from src.services.web_contract import (
    ConfirmResponse,
    ProposalResponse,
    RunListResponse,
    RunResponse,
    RunSummaryResponse,
    make_error_snapshot,
    normalize_snapshot,
)
from src.services.web_store import WebStore
from src.api.runtime import (
    ProfileRuntime,
    RETRIEVAL_MODES,
    apply_retrieval_mode,
    config_retrieval_mode,
    default_runtime,
    describe_runtime,
    load_profile_runtimes,
    load_ui_hints,
    make_event_sink,
    reranker_endpoint_status,
)
from src.tools.legal_tools import LegalToolRegistry
from src.verifier.grounding_analyzer import analyze_grounding
from src.verifier.modes import LEXICAL_GROUNDING, OFF, SEMANTIC_ENTAILMENT, canonical_mode


MAX_QUERY_CHARS = int(os.getenv("LUATCHECK_WEB_MAX_QUERY_CHARS", "8000"))
MAX_DOCUMENT_CHARS = int(os.getenv("LUATCHECK_WEB_MAX_DOCUMENT_CHARS", "100000"))
MAX_SUMMARY_CHARS = int(os.getenv("LUATCHECK_WEB_MAX_SUMMARY_CHARS", "40000"))
MAX_QUEUE_SIZE = max(1, int(os.getenv("LUATCHECK_WEB_QUEUE_SIZE", "2")))
API_PREFIX = "/api/v1"
logger = logging.getLogger("luatcheck.web")


class RunRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(min_length=1, max_length=MAX_QUERY_CHARS)
    pasted_document: Optional[str] = Field(default=None, max_length=MAX_DOCUMENT_CHARS)
    verification_mode: str = Field(default="lexical_grounding", max_length=40)
    retrieval_mode: Optional[str] = Field(default=None, max_length=40, description="First-stage retrieval mode; default = profile config")
    profile: Optional[str] = Field(default=None, max_length=80, description="Domain profile id; default = first available")


class ProposalRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    recipient: str = Field(min_length=1, max_length=320)
    content: str = Field(min_length=1, max_length=MAX_SUMMARY_CHARS)


class ConfirmRequest(BaseModel):
    payload_hash: str = Field(min_length=64, max_length=64)


def _store_path() -> str:
    return os.getenv("LUATCHECK_WEB_DB", "data/db/web_ui.sqlite3")


def _retention_days() -> int:
    return max(1, int(os.getenv("LUATCHECK_WEB_RETENTION_DAYS", "30")))


def _loopback_only(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _safe_model_status(config: Optional[AppConfig]) -> Dict[str, Any]:
    if config is None:
        return {"status": "unknown", "reachable": None, "configured_model_present": None}
    endpoint = config.model.endpoint.rstrip("/")
    is_ollama = config.model.provider == "ollama"
    if is_ollama:
        url = endpoint if endpoint.endswith("/api") else f"{endpoint}/api"
        url = f"{url}/tags"
    else:
        url = endpoint if endpoint.endswith("/v1") else f"{endpoint}/v1"
        url = f"{url}/models"
    try:
        response = requests.get(url, timeout=1.5)
        response.raise_for_status()
        data = response.json()
        if is_ollama:
            models = data.get("models", []) if isinstance(data, dict) else []
            names = [str(model.get("name", "")) for model in models if isinstance(model, dict)]
        else:
            models = data.get("data", []) if isinstance(data, dict) else []
            names = [str(model.get("id", "")) for model in models if isinstance(model, dict)]
        present = any(name == config.model.name for name in names)
        return {
            "status": "reachable",
            "reachable": True,
            "configured_model_present": present,
        }
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        return {"status": "unavailable", "reachable": False, "configured_model_present": None}


def _event(app: FastAPI, run_id: str, name: str, data: Dict[str, Any]) -> None:
    app.state.store.append_event(run_id, name, data)


def _article_dto(registry: LegalToolRegistry, article_id: str) -> Optional[Dict[str, Any]]:
    getter = getattr(registry.retriever, "get_document_by_id", None) or getattr(registry.retriever, "get_article_by_id", None)
    doc = getter(article_id) if getter else None
    if not doc:
        return None
    return {
        "article_id": str(doc.get("article_id") or doc.get("doc_id") or article_id),
        "title": str(doc.get("title") or doc.get("section_title") or ""),
        "content": str(doc.get("content") or doc.get("full_content") or ""),
        "law_name": str(doc.get("law_name") or doc.get("source_name") or ""),
        "scope": doc.get("scope"),
        "source_url": doc.get("source_url"),
        "source_pages": doc.get("source_pages"),
        "source_sha256": doc.get("source_sha256"),
        "extraction": doc.get("extraction"),
    }


def _source_matched_quote(model_quote: Any, article: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(model_quote, str) or not model_quote.strip() or not article:
        return None
    quote = " ".join(model_quote.split())
    source = " ".join(str(article.get("content", "")).split())
    return model_quote if quote and quote in source else None


def _ledger_snapshot(ledger: Any, agent: LuatCheckAgent, started_at: float,
                     runtime: Optional[ProfileRuntime] = None, sink_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    output = ledger.final_output or {}
    citations = []
    article_ids = []
    raw_citations = output.get("citations", [])
    if isinstance(raw_citations, list):
        for citation in raw_citations:
            if not isinstance(citation, dict):
                continue
            article_id = str(citation.get("article_id") or "").strip()
            if not article_id:
                continue
            article_ids.append(article_id)
            article = _article_dto(agent.tool_registry, article_id)
            citations.append({
                "article_id": article_id,
                "law_name": citation.get("law_name"),
                "exact_quote": _source_matched_quote(citation.get("exact_quote"), article),
                "title": article.get("title") if article else None,
                "source_url": article.get("source_url") if article else None,
                "source_pages": article.get("source_pages") if article else None,
                "source_sha256": article.get("source_sha256") if article else None,
                "scope": article.get("scope") if article else None,
                "available": article is not None,
            })

    final_output: Dict[str, Any] = {
        "action": output.get("action"),
        "citations": citations,
        "verified": output.get("verified"),
        "from_cache": output.get("from_cache", False),
    }
    for key in ("content", "question", "reason", "error_kind", "pre_model_policy_refusal"):
        if key in output:
            final_output[key] = output[key]

    refusal_kind = None
    if ledger.terminal_status == "refused":
        if output.get("pre_model_policy_refusal"):
            refusal_kind = "guardrail"
        elif sink_state and sink_state.get("last_verification_passed") is False:
            refusal_kind = "verification_failed"
        else:
            refusal_kind = "model"

    grounding = None
    if output.get("action") == "answer" and output.get("content"):
        analysis = analyze_grounding(
            str(output["content"]), raw_citations, agent,
            retrieved_article_ids=list(ledger.retrieved_article_ids),
        )
        grounding = {
            "label": "lexical proxy",
            "grounded_ratio": analysis.get("grounded_ratio"),
            "sentences": analysis.get("sentences_data", []),
            "unsupported_claims": analysis.get("unsupported_claims", []),
            "invalid_citations": analysis.get("invalid_citations", []),
        }

    calls = list(ledger.llm_calls)
    def complete_numeric(field: str) -> Optional[int]:
        values = [call.get(field) for call in calls]
        if not values or any(not isinstance(value, (int, float)) for value in values):
            return None
        return int(sum(values))

    latency_values = [call.get("wall_ms") for call in calls]
    model_latency = round(sum(float(value) for value in latency_values), 3) if latency_values and all(isinstance(v, (int, float)) for v in latency_values) else None
    return {
        "terminal_status": ledger.terminal_status,
        "final_output": final_output,
        "verification_mode": agent.verification_mode,
        "retrieval_mode": config_retrieval_mode(agent.config),
        "refusal_kind": refusal_kind,
        "profile": {"id": runtime.key, "display_name": getattr(runtime.profile, "display_name", None)} if runtime else None,
        "budgets": {
            "tool_calls": {"used": ledger.tool_calls_count, "limit": ledger.max_tool_calls},
            "repairs": {"used": ledger.repairs_count, "limit": ledger.max_repairs},
            "steps": {"used": ledger.step_count, "limit": ledger.max_steps},
        },
        "retrieved_article_ids": list(dict.fromkeys([*ledger.retrieved_article_ids, *article_ids])),
        "grounding": grounding,
        "usage": {
            "model_call_count": len(calls),
            "input_tokens": complete_numeric("input_tokens"),
            "output_tokens": complete_numeric("output_tokens"),
            "model_wall_ms": model_latency,
        },
        "elapsed_ms": round((time.monotonic() - started_at) * 1000, 1),
    }


def _run_worker(app: FastAPI) -> None:
    while not app.state.worker_stop.is_set():
        try:
            job = app.state.jobs.get(timeout=0.4)
        except queue.Empty:
            continue
        if job is None:
            app.state.jobs.task_done()
            continue
        run_id = job["run_id"]
        app.state.active_run_id = run_id
        app.state.store.update_run_status(run_id, "running")
        started_at = time.monotonic()
        try:
            config = AppConfig.model_validate(job["config"])
            runtime = app.state.profiles.get(job.get("profile"))
            if runtime is None or not runtime.available:
                raise RuntimeError(f"Profile {job.get('profile')!r} is not loaded.")
            run_registry = runtime.registry_for_config(config)
            holder: Dict[str, Any] = {}

            def title_of(article_id: str, _registry=run_registry) -> str:
                dto = _article_dto(_registry, article_id)
                return (dto or {}).get("title", "") if dto else ""

            sink = make_event_sink(lambda name, data: _event(app, run_id, name, data), holder, title_of)
            agent = LuatCheckAgent(config=config, tool_registry=run_registry, event_sink=sink)
            holder["agent"] = agent
            ledger = agent.run(job["query"], pasted_doc=job.get("pasted_document"), session_id=run_id)
            if ledger.terminal_status not in {"answered", "clarified", "refused", "error"}:
                ledger.terminal_status = "error"
                ledger.is_terminal = True
                ledger.final_output = {
                    "action": "error", "reason": "Tác vụ kết thúc mà không có trạng thái cuối hợp lệ.",
                    "error_kind": "invalid_terminal_state", "citations": [], "verified": False,
                }
            snapshot = normalize_snapshot(
                _ledger_snapshot(ledger, agent, started_at, runtime, holder.get("state")),
                persisted_mode=job["verification_mode"],
                persisted_terminal=ledger.terminal_status,
            )
            app.state.store.update_run_status(run_id, "finished", ledger.terminal_status, snapshot)
            app.state.store.append_event(run_id, "run_persisted", {"terminal_status": ledger.terminal_status})
        except Exception as exc:
            # Application, retrieval, config, and backend failures remain execution errors.
            error_kind = getattr(exc, "kind", None) or type(exc).__name__
            logger.exception("run %s failed", run_id)
            snapshot = make_error_snapshot(
                job["verification_mode"],
                str(error_kind),
                f"Tác vụ thất bại do lỗi thực thi ({type(exc).__name__}: {str(exc)[:240]}). Xem log của API để biết chi tiết.",
                round((time.monotonic() - started_at) * 1000, 1),
                retrieval_mode=job.get("retrieval_mode"),
            )
            app.state.store.update_run_status(run_id, "finished", "error", snapshot)
            app.state.store.append_event(run_id, "run_failed", {"error_kind": str(error_kind)})
        finally:
            app.state.active_run_id = None
            app.state.jobs.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = WebStore(_store_path(), _retention_days())
    app.state.jobs = queue.Queue(maxsize=MAX_QUEUE_SIZE)
    app.state.enqueue_lock = threading.RLock()
    app.state.registry_lock = threading.RLock()
    app.state.worker_stop = threading.Event()
    app.state.active_run_id = None
    app.state.config = None
    app.state.config_error = None
    app.state.registry = None
    app.state.corpus_available = False
    app.state.hints = load_ui_hints()
    app.state.profiles = {}
    app.state.default_profile = None
    try:
        app.state.profiles = load_profile_runtimes()
        default = default_runtime(app.state.profiles)
        if default is not None:
            app.state.default_profile = default.key
            app.state.config = default.config
            app.state.registry = default.registry
            app.state.corpus_available = default.available
            app.state.config_error = default.error
        if not any(r.available for r in app.state.profiles.values()) and app.state.config_error is None:
            app.state.config_error = "No domain profile could be loaded."
    except Exception as exc:
        app.state.config_error = f"{type(exc).__name__}: {exc}"
    app.state.worker = threading.Thread(target=_run_worker, args=(app,), name="luatcheck-inference-worker", daemon=True)
    app.state.worker.start()
    try:
        yield
    finally:
        app.state.worker_stop.set()
        app.state.worker.join(timeout=0.2)


app = FastAPI(title="LuatCheck Local API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def enforce_request_body_limit(request: Request, call_next):
    if request.method == "POST" and request.url.path.startswith(API_PREFIX):
        raw_size = request.headers.get("content-length")
        if raw_size:
            try:
                size = int(raw_size)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length."})
            limit = (MAX_QUERY_CHARS + MAX_DOCUMENT_CHARS + MAX_SUMMARY_CHARS) * 4 + 8192
            if size > limit:
                return JSONResponse(status_code=413, content={"detail": "Request body exceeds the configured local limit."})
    return await call_next(request)


def _session(request: Request, response: Optional[Response] = None, create: bool = False) -> Dict[str, str]:
    sid = request.cookies.get("luatcheck_session")
    if not sid:
        if not create:
            raise HTTPException(status_code=401, detail="Browser session required.")
        sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    stored = request.app.state.store.get_or_create_session(sid, csrf)
    if response is not None and not request.cookies.get("luatcheck_session"):
        response.set_cookie(
            "luatcheck_session", sid, httponly=True, secure=False, samesite="lax", path="/",
            max_age=_retention_days() * 86400,
        )
    return stored


def _check_origin_and_csrf(request: Request, session: Dict[str, str]) -> None:
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(status_code=403, detail="Origin header is required for this action.")
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=403, detail="Invalid request origin.")
    try:
        loopback = _loopback_only(parsed.hostname)
    except ValueError:
        loopback = False
    if not loopback:
        raise HTTPException(status_code=403, detail="Only loopback browser origins are allowed.")
    allowed = {value.strip().rstrip("/") for value in os.getenv("LUATCHECK_WEB_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if value.strip()}
    request_origin = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    if origin.rstrip("/") not in allowed and origin.rstrip("/") != request_origin:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), session["csrf_token"]):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


def _config_or_503(request: Request) -> AppConfig:
    config = request.app.state.config
    if config is None or request.app.state.config_error:
        raise HTTPException(status_code=503, detail="Configured inference or corpus dependencies are unavailable.")
    return config


def _public_run(row: Dict[str, Any], *, include_document: bool = False) -> Dict[str, Any]:
    snapshot = normalize_snapshot(
        row.get("snapshot"),
        persisted_mode=row.get("verification_mode"),
        persisted_terminal=row.get("terminal_status"),
    )
    ret_mode = (snapshot.get("retrieval_mode") if isinstance(snapshot, dict) else None) or config_retrieval_mode(row.get("config"))
    payload = {
        "run_id": row["run_id"],
        "query": row["query_text"],
        "verification_mode": row["verification_mode"],
        "retrieval_mode": ret_mode,
        "job_status": row["job_status"],
        "terminal_status": snapshot["terminal_status"] if snapshot else row.get("terminal_status"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "snapshot": snapshot,
        "profile_id": ((row.get("config") or {}).get("domain") or {}).get("profile") if isinstance(row.get("config"), dict) else None,
    }
    if include_document:
        payload["pasted_document"] = row.get("pasted_document")
    model = RunResponse if include_document else RunSummaryResponse
    return model.model_validate(payload).model_dump(mode="json")


@app.get("/api/v1/session")
def get_session(request: Request, response: Response):
    session = _session(request, response, create=True)
    return {"csrf_token": session["csrf_token"]}


@app.get("/api/v1/health")
def health(request: Request):
    config = request.app.state.config
    return {
        "api": "ok",
        "configuration": "available" if config and not request.app.state.config_error else "error",
        "corpus": "available" if request.app.state.corpus_available else "unavailable",
        "model": _safe_model_status(config),
        "reranker": reranker_endpoint_status(config),
        "active_run": bool(request.app.state.active_run_id),
        "queued_runs": request.app.state.jobs.qsize(),
    }


@app.get("/api/v1/capabilities")
def capabilities(request: Request):
    config: Optional[AppConfig] = request.app.state.config
    runtimes: Dict[str, ProfileRuntime] = request.app.state.profiles
    if config is None and not runtimes:
        return JSONResponse(status_code=200, content={"available": False, "reason": request.app.state.config_error or "Cấu hình inference không đọc được.", "verification_modes": [], "profiles": []})
    default = runtimes.get(request.app.state.default_profile) if request.app.state.default_profile else None
    semantic_available = bool(config and config.verifier.l2_use_slm)
    modes = ["off", "lexical_grounding"]
    if semantic_available:
        modes.append("semantic_entailment")
    profiles = [describe_runtime(runtime, request.app.state.hints) for runtime in runtimes.values()]
    default_info = next((p for p in profiles if p["id"] == request.app.state.default_profile), None)
    configured_mode = canonical_mode(config.verifier.mode) if config else OFF
    default_mode = configured_mode if configured_mode in modes else LEXICAL_GROUNDING
    avail_ret_modes = ((default_info or {}).get("retrieval") or {}).get("available_modes") or list(RETRIEVAL_MODES)
    default_ret_mode = "hybrid_wrrf" if "hybrid_wrrf" in avail_ret_modes else config_retrieval_mode(config)
    any_available = any(p["available"] for p in profiles)
    reason = None if any_available else (request.app.state.config_error or "Không có profile miền nào sẵn sàng.")
    return {
        "available": any_available,
        "reason": reason,
        "model": {"provider": config.model.provider, "name": config.model.name, "endpoint": config.model.endpoint} if config else None,
        "profiles": profiles,
        "default_profile": request.app.state.default_profile,
        "default_verification_mode": default_mode,
        "default_retrieval_mode": default_ret_mode,
        "retrieval_modes": avail_ret_modes,
        "corpus": {
            "available": bool(request.app.state.corpus_available),
            "name": (default_info or {}).get("display_name") or (default_info or {}).get("id") or "",
            "scope": (default_info or {}).get("scope_note") or "",
            "retrieval": config.retrieval.dense_model_type if config else "",
        },
        "verification_modes": modes,
        "semantic_unavailable_reason": None if semantic_available else "Native semantic verifier chưa được bật trong cấu hình.",
        "budgets": {
            "max_tool_calls": config.budgets.max_tool_calls,
            "max_repairs": config.budgets.max_repairs,
            "max_steps": config.budgets.max_steps,
            "wall_seconds": config.budgets.wall_seconds,
        } if config else None,
        "queue": {"waiting_limit": MAX_QUEUE_SIZE, "single_inference_worker": True},
        "web_storage": {
            "retention_days": _retention_days(),
            "database_location": "data/db/web_ui.sqlite3" if not os.getenv("LUATCHECK_WEB_DB") else "custom local path",
        },
    }


@app.post("/api/v1/runs", status_code=202)
def create_run(
    body: RunRequest,
    request: Request,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
):
    session = _session(request)
    _check_origin_and_csrf(request, session)
    _config_or_503(request)
    profile_key = body.profile or request.app.state.default_profile
    runtime = request.app.state.profiles.get(profile_key) if profile_key else None
    if runtime is None:
        raise HTTPException(status_code=422, detail="Unknown domain profile.")
    if not runtime.available:
        raise HTTPException(status_code=503, detail=f"Domain profile is unavailable: {runtime.error}")
    base_config = runtime.config
    requested_mode = body.verification_mode
    if requested_mode not in {"off", "lexical_grounding", "semantic_entailment"}:
        raise HTTPException(status_code=422, detail="Unsupported verification mode.")
    if requested_mode == "semantic_entailment" and not base_config.verifier.l2_use_slm:
        raise HTTPException(status_code=422, detail="Native semantic verification is not enabled in the configured backend.")
    config = base_config.model_copy(deep=True)
    config.verifier.mode = requested_mode
    requested_retrieval = body.retrieval_mode or config_retrieval_mode(base_config)
    if requested_retrieval not in RETRIEVAL_MODES:
        raise HTTPException(status_code=422, detail="Unsupported retrieval mode.")
    apply_retrieval_mode(config, requested_retrieval)
    canonical = {"query": body.query, "pasted_document": body.pasted_document, "verification_mode": requested_mode,
                 "retrieval_mode": requested_retrieval, "profile": runtime.key}
    request_sha = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    with request.app.state.enqueue_lock:
        previous = request.app.state.store.find_run_by_key(session["session_id"], idempotency_key)
        if previous:
            if previous["request_sha256"] != request_sha:
                raise HTTPException(status_code=409, detail="Idempotency key already belongs to a different request.")
            return JSONResponse(status_code=202, content={"run_id": previous["run_id"], "job_status": previous["job_status"], "replayed": True})
        if request.app.state.jobs.full():
            raise HTTPException(status_code=429, detail="Hàng đợi đang đầy; hãy thử gửi lại sau.", headers={"Retry-After": "2"})
        run_id = str(uuid.uuid4())
        try:
            request.app.state.store.create_run(
                run_id, session["session_id"], idempotency_key, request_sha, body.query,
                body.pasted_document, requested_mode, config.model_dump(mode="json"),
            )
            request.app.state.store.append_event(run_id, "run_queued", {})
            job = {
                "run_id": run_id,
                "query": body.query,
                "pasted_document": body.pasted_document,
                "verification_mode": requested_mode,
                "retrieval_mode": requested_retrieval,
                "profile": runtime.key,
                "config": config.model_dump(mode="json"),
            }
            request.app.state.jobs.put_nowait(job)
        except queue.Full:
            request.app.state.store.delete_run(run_id, session["session_id"])
            raise HTTPException(status_code=429, detail="Hàng đợi đang đầy; hãy thử gửi lại sau.", headers={"Retry-After": "2"})
        except Exception:
            request.app.state.store.delete_run(run_id, session["session_id"])
            raise
    response.headers["Location"] = f"/api/v1/runs/{run_id}"
    return {"run_id": run_id, "job_status": "queued", "replayed": False}


@app.get("/api/v1/runs", response_model=RunListResponse)
def list_runs(request: Request, limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    session = _session(request)
    rows = request.app.state.store.list_runs(session["session_id"], limit, offset)
    return {"items": [_public_run(row) for row in rows], "total": request.app.state.store.count_runs(session["session_id"]), "limit": limit, "offset": offset}


@app.get("/api/v1/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, request: Request):
    session = _session(request)
    row = request.app.state.store.get_run(session["session_id"], run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run không tồn tại trong browser session hiện tại.")
    return _public_run(row, include_document=True)


@app.get("/api/v1/runs/{run_id}/events")
async def run_events(run_id: str, request: Request, after: int = Query(default=0, ge=0), last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID")):
    session = _session(request)
    row = request.app.state.store.get_run(session["session_id"], run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run không tồn tại trong browser session hiện tại.")
    cursor = after
    if last_event_id:
        try:
            cursor = max(cursor, int(last_event_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Last-Event-ID must be numeric.")

    async def stream():
        current = cursor
        while True:
            if await request.is_disconnected():
                break
            events = request.app.state.store.list_events(run_id, current)
            for event in events:
                current = event["id"]
                payload = json.dumps({**event["data"], "created_at": event["created_at"]}, ensure_ascii=False, separators=(",", ":"))
                yield f"id: {event['id']}\nevent: {event['event']}\ndata: {payload}\n\n"
            latest = request.app.state.store.get_run(session["session_id"], run_id)
            if latest and latest["job_status"] == "finished" and not events:
                break
            if latest and latest["job_status"] == "finished" and events and any(e["event"] in {"run_persisted", "run_failed", "run_interrupted"} for e in events):
                break
            if not events:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/runs/{run_id}/articles/{article_id}")
def get_article(run_id: str, article_id: str, request: Request):
    session = _session(request)
    row = request.app.state.store.get_run(session["session_id"], run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run không tồn tại trong browser session hiện tại.")
    run_profile = ((row.get("config") or {}).get("domain") or {}).get("profile") if isinstance(row.get("config"), dict) else None
    runtime = request.app.state.profiles.get(run_profile) or request.app.state.profiles.get(request.app.state.default_profile)
    if runtime is None or runtime.registry is None:
        raise HTTPException(status_code=503, detail="Corpus retrieval is not available.")
    snapshot = row.get("snapshot") or {}
    if article_id not in set(snapshot.get("retrieved_article_ids", [])):
        raise HTTPException(status_code=404, detail="Mục này không thuộc các mục được truy xuất trong run.")
    article = _article_dto(runtime.registry, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Mục không có trong corpus của phiên bản này.")
    return article


@app.post("/api/v1/runs/{run_id}/summary-proposals", response_model=ProposalResponse)
def create_summary_proposal(run_id: str, body: ProposalRequest, request: Request):
    session = _session(request)
    _check_origin_and_csrf(request, session)
    row = request.app.state.store.get_run(session["session_id"], run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run không tồn tại trong browser session hiện tại.")
    if row["job_status"] != "finished" or row["terminal_status"] != "answered":
        raise HTTPException(status_code=409, detail="Chỉ có thể chuẩn bị tóm tắt từ run đã trả lời xong.")
    if request.app.state.registry is None:
        raise HTTPException(status_code=503, detail="Local outbox is unavailable.")
    idem = hashlib.sha256(json.dumps(
        ["web-summary", run_id, session["session_id"], body.recipient, body.content],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    candidate_id = f"prop_{uuid.uuid4().hex}"
    with request.app.state.registry_lock:
        candidate = request.app.state.registry.create_summary_proposal(
            body.recipient, body.content, idem, proposal_id=candidate_id,
        )
        persisted, _created, event_record = request.app.state.store.create_or_get_proposal({
            **candidate,
            "run_id": run_id,
            "session_id": session["session_id"],
            "idempotency_key": idem,
        })
        if persisted["proposal_id"] != candidate_id:
            request.app.state.registry.discard_unapproved_proposal(candidate_id)
    is_completed = persisted["status"] == "completed"
    if is_completed and not isinstance(persisted.get("result"), dict):
        raise HTTPException(status_code=503, detail="Proposal đã hoàn tất nhưng không có receipt bền vững; cần kiểm tra outbox local.")
    return {
        "proposal_id": persisted["proposal_id"],
        "recipient": persisted["recipient"],
        "content": persisted["content"],
        "payload_hash": persisted["payload_hash"],
        "status": "completed" if is_completed else "pending_confirmation",
        "delivery": "Local outbox only; not sent.",
        "result": persisted["result"] if is_completed else None,
        "event_id": event_record["id"] if event_record else None,
        "event_created_at": event_record["created_at"] if event_record else None,
    }


@app.post("/api/v1/summary-proposals/{proposal_id}/confirm", response_model=ConfirmResponse)
def confirm_summary_proposal(proposal_id: str, body: ConfirmRequest, request: Request):
    session = _session(request)
    _check_origin_and_csrf(request, session)
    proposal = request.app.state.store.get_proposal(session["session_id"], proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal không tồn tại trong browser session hiện tại.")
    if proposal["status"] == "completed":
        receipt = proposal.get("result")
        if not isinstance(receipt, dict) or receipt.get("status") not in {"queued_locally", "duplicate_suppressed"}:
            raise HTTPException(status_code=503, detail="Proposal đã hoàn tất nhưng receipt outbox không hợp lệ; cần kiểm tra storage local.")
        return {"proposal_id": proposal_id, "status": "completed", "replayed": True, "result": receipt}
    if proposal["status"] != "pending":
        raise HTTPException(status_code=409, detail="Proposal đã hết hiệu lực hoặc không còn chờ xác nhận.")
    if not secrets.compare_digest(body.payload_hash, proposal["payload_hash"]):
        raise HTTPException(status_code=409, detail="Payload thay đổi; cần tạo proposal mới để duyệt lại.")
    registry = request.app.state.registry
    if registry is None:
        raise HTTPException(status_code=503, detail="Local outbox is unavailable.")
    with request.app.state.registry_lock:
        token = registry.approve_proposal(proposal_id)
        if not token:
            raise HTTPException(status_code=409, detail="Proposal đã mất hiệu lực sau khi API khởi động lại.")
        result = registry.dispatch_external_action(
            proposal["recipient"], proposal["content"], proposal["idempotency_key"],
            user_confirmed=True, proposal_id=proposal_id, approval_token=token,
        )
    if result.get("status") not in {"queued_locally", "duplicate_suppressed"}:
        raise HTTPException(status_code=503, detail="Không thể xác nhận ghi bền vững vào outbox; proposal vẫn chờ để thử lại.")
    request.app.state.store.update_proposal(proposal_id, "completed", result)
    event_record = request.app.state.store.append_event(proposal["run_id"], "summary_proposal_completed", {"status": result.get("status")})
    return {
        "proposal_id": proposal_id,
        "status": "completed",
        "replayed": False,
        "result": result,
        "event_id": event_record["id"],
        "event_created_at": event_record["created_at"],
        "display_message": (
            "Đã lưu hàng đợi cục bộ; chưa gửi email/webhook."
            if result.get("status") == "queued_locally"
            else "Bản tóm tắt này đã có trong hàng đợi cục bộ; chưa gửi email/webhook."
        ),
    }


@app.get("/", include_in_schema=False)
def root(request: Request):
    index = Path("frontend/dist/index.html")
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-store"})
    return {"service": "LuatCheck Local API", "frontend": "Run `npm --prefix frontend run dev` during development."}


@app.get("/{asset_path:path}", include_in_schema=False)
def frontend_asset(asset_path: str):
    target = (Path("frontend/dist") / asset_path).resolve()
    root_path = Path("frontend/dist").resolve()
    if target.is_file() and root_path in target.parents:
        return FileResponse(target)
    index = Path("frontend/dist/index.html")
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-store"})
    raise HTTPException(status_code=404, detail="Frontend build not found.")


def main() -> None:
    import uvicorn

    host = os.getenv("LUATCHECK_WEB_HOST", "127.0.0.1")
    if not _loopback_only(host):
        raise SystemExit("LuatCheck web UI is local-only; LUATCHECK_WEB_HOST must be a loopback address.")
    port = int(os.getenv("LUATCHECK_WEB_PORT", "8000"))
    uvicorn.run("src.api.app:app", host=host, port=port, reload=False, access_log=False)


if __name__ == "__main__":
    main()
