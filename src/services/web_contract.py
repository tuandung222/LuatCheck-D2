"""Validated API snapshots and compatibility normalization for persisted runs."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


VerificationMode = Literal["off", "lexical_grounding", "semantic_entailment"]
RetrievalMode = Literal["hybrid_wrrf", "bm25_tfidf", "fts5_keyword", "vector_768d", "hybrid_rrf_equal"]
TerminalStatus = Literal["answered", "clarified", "refused", "error"]
JobStatus = Literal["queued", "running", "finished"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CitationSnapshot(ContractModel):
    article_id: str
    law_name: Optional[str] = None
    exact_quote: Optional[str] = None
    title: Optional[str] = None
    source_url: Optional[str] = None
    source_pages: Optional[List[int]] = None
    source_sha256: Optional[str] = None
    scope: Optional[str] = None
    available: bool = False


class FinalOutputSnapshot(ContractModel):
    action: Optional[str] = None
    content: Optional[str] = None
    question: Optional[str] = None
    reason: Optional[str] = None
    error_kind: Optional[str] = None
    verified: Optional[bool] = None
    from_cache: Optional[bool] = None
    pre_model_policy_refusal: Optional[bool] = None
    citations: List[CitationSnapshot] = Field(default_factory=list)


class BudgetCounter(ContractModel):
    used: int
    limit: int


class RunBudgets(ContractModel):
    tool_calls: BudgetCounter
    repairs: BudgetCounter
    steps: BudgetCounter


class UsageSnapshot(ContractModel):
    model_call_count: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model_wall_ms: Optional[float] = None


class GroundingSentence(ContractModel):
    sentence: str
    overlap_ratio: Optional[float] = None
    is_supported: Optional[bool] = None
    best_article_id: Optional[str] = None


class GroundingSnapshot(ContractModel):
    label: str
    grounded_ratio: Optional[float] = None
    sentences: List[GroundingSentence] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    invalid_citations: List[str] = Field(default_factory=list)


class ProfileRef(ContractModel):
    id: str
    display_name: Optional[str] = None


RefusalKind = Literal["guardrail", "verification_failed", "model"]


class RunSnapshot(ContractModel):
    terminal_status: TerminalStatus
    refusal_kind: Optional[RefusalKind] = None
    profile: Optional[ProfileRef] = None
    final_output: FinalOutputSnapshot = Field(default_factory=FinalOutputSnapshot)
    verification_mode: Optional[VerificationMode] = None
    retrieval_mode: Optional[RetrievalMode] = None
    budgets: Optional[RunBudgets] = None
    retrieved_article_ids: List[str] = Field(default_factory=list)
    grounding: Optional[GroundingSnapshot] = None
    usage: Optional[UsageSnapshot] = None
    elapsed_ms: Optional[float] = None


class RunSummaryResponse(ContractModel):
    run_id: str
    query: str
    verification_mode: VerificationMode
    retrieval_mode: Optional[RetrievalMode] = None
    job_status: JobStatus
    terminal_status: Optional[TerminalStatus] = None
    profile_id: Optional[str] = None
    created_at: float
    updated_at: float
    snapshot: Optional[RunSnapshot] = None


class RunResponse(RunSummaryResponse):
    pasted_document: Optional[str] = None


class RunListResponse(ContractModel):
    items: List[RunSummaryResponse]
    total: int
    limit: int
    offset: int


class ProposalResponse(ContractModel):
    proposal_id: str
    recipient: str
    content: str
    payload_hash: str
    status: Literal["pending_confirmation", "completed"]
    delivery: str
    result: Optional[Dict[str, Any]] = None
    event_id: Optional[int] = None
    event_created_at: Optional[float] = None


class ConfirmResponse(ContractModel):
    proposal_id: str
    status: Literal["completed"]
    replayed: bool
    result: Dict[str, Any]
    event_id: Optional[int] = None
    event_created_at: Optional[float] = None
    display_message: Optional[str] = None


def _valid_mode(value: Any) -> Optional[VerificationMode]:
    if value in {"off", "lexical_grounding", "semantic_entailment"}:
        return value
    return None


def _valid_retrieval_mode(value: Any) -> Optional[RetrievalMode]:
    if value in {"hybrid_wrrf", "bm25_tfidf", "fts5_keyword", "vector_768d", "hybrid_rrf_equal"}:
        return value
    return None


def _valid_terminal(value: Any) -> Optional[TerminalStatus]:
    if value in {"answered", "clarified", "refused", "error"}:
        return value
    return None


def normalize_snapshot(
    value: Any,
    *,
    persisted_mode: Any,
    persisted_terminal: Any,
) -> Optional[Dict[str, Any]]:
    """Normalize old snapshots without inventing measurements or answer content."""
    if value is None:
        return None
    raw = value if isinstance(value, dict) else {}
    snapshot_status = _valid_terminal(raw.get("terminal_status"))
    row_status = _valid_terminal(persisted_terminal)
    status_mismatch = bool(snapshot_status and row_status and snapshot_status != row_status)
    status = row_status or snapshot_status
    final_output = raw.get("final_output") if isinstance(raw.get("final_output"), dict) else {}
    if status_mismatch:
        status = "error"
        final_output = {
            **final_output,
            "action": "error",
            "reason": "Bản ghi run cũ không thống nhất giữa trạng thái và snapshot.",
            "error_kind": "inconsistent_persisted_snapshot",
        }
    if status is None:
        status = "error"
        final_output = {
            **final_output,
            "action": final_output.get("action") or "error",
            "reason": final_output.get("reason") or "Bản ghi run cũ thiếu trạng thái cuối hợp lệ.",
            "error_kind": final_output.get("error_kind") or "invalid_persisted_snapshot",
        }
    elif status == "error" and not final_output.get("reason"):
        final_output = {
            **final_output,
            "action": final_output.get("action") or "error",
            "reason": "Run kết thúc lỗi; bản ghi cũ không lưu reason chi tiết.",
        }

    citations = final_output.get("citations")
    if not isinstance(citations, list):
        citations = []
    final_output = {
        **final_output,
        "citations": [
            citation
            for citation in citations
            if isinstance(citation, dict) and isinstance(citation.get("article_id"), str) and citation["article_id"].strip()
        ],
    }

    retrieved_ids = raw.get("retrieved_article_ids")
    if not isinstance(retrieved_ids, list):
        retrieved_ids = []
    retrieved_ids = [item for item in retrieved_ids if isinstance(item, str)]

    budgets = raw.get("budgets")
    if not isinstance(budgets, dict):
        budgets = None
    else:
        try:
            budgets = RunBudgets.model_validate(budgets).model_dump(mode="json")
        except Exception:
            budgets = None

    grounding = raw.get("grounding")
    if not isinstance(grounding, dict):
        grounding = None
    else:
        try:
            grounding = GroundingSnapshot.model_validate(grounding).model_dump(mode="json")
        except Exception:
            grounding = None

    usage = raw.get("usage")
    if not isinstance(usage, dict):
        usage = None
    else:
        usage = {
            key: item if isinstance(item, (int, float)) and math.isfinite(float(item)) else None
            for key, item in usage.items()
            if key in {"model_call_count", "input_tokens", "output_tokens", "model_wall_ms"}
        }

    profile_ref = raw.get("profile")
    if not (isinstance(profile_ref, dict) and isinstance(profile_ref.get("id"), str)):
        profile_ref = None
    else:
        profile_ref = {"id": profile_ref["id"], "display_name": profile_ref.get("display_name") if isinstance(profile_ref.get("display_name"), str) else None}

    elapsed_ms = raw.get("elapsed_ms")
    if not isinstance(elapsed_ms, (int, float)) or not math.isfinite(float(elapsed_ms)) or elapsed_ms < 0:
        elapsed_ms = None

    normalized = {
        "terminal_status": status,
        "final_output": final_output,
        "verification_mode": _valid_mode(raw.get("verification_mode")) or _valid_mode(persisted_mode),
        "retrieval_mode": _valid_retrieval_mode(raw.get("retrieval_mode")),
        "refusal_kind": raw.get("refusal_kind") if raw.get("refusal_kind") in {"guardrail", "verification_failed", "model"} else None,
        "profile": profile_ref,
        "budgets": budgets,
        "retrieved_article_ids": retrieved_ids,
        "grounding": grounding,
        "usage": usage,
        "elapsed_ms": elapsed_ms,
    }
    return RunSnapshot.model_validate(normalized).model_dump(mode="json")


def make_error_snapshot(
    verification_mode: Any,
    error_kind: str,
    reason: str,
    elapsed_ms: Optional[float],
    retrieval_mode: Any = None,
) -> Dict[str, Any]:
    return RunSnapshot.model_validate({
        "terminal_status": "error",
        "final_output": {
            "action": "error",
            "reason": reason,
            "error_kind": error_kind,
            "citations": [],
            "verified": False,
        },
        "verification_mode": _valid_mode(verification_mode),
        "retrieval_mode": _valid_retrieval_mode(retrieval_mode),
        "budgets": None,
        "retrieved_article_ids": [],
        "grounding": None,
        "usage": {
            "model_call_count": None,
            "input_tokens": None,
            "output_tokens": None,
            "model_wall_ms": None,
        },
        "elapsed_ms": elapsed_ms,
    }).model_dump(mode="json")


def make_restart_snapshot(verification_mode: Any) -> Dict[str, Any]:
    return make_error_snapshot(
        verification_mode,
        "api_restart",
        "API khởi động lại khi tác vụ chưa hoàn tất.",
        None,
    )
