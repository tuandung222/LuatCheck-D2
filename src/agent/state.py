"""
State schemas and data models for LuatCheck Agent
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    SEARCH_LAW = "search_law"
    GET_ARTICLE = "get_article"
    ANSWER = "answer"
    CLARIFY = "clarify"
    REFUSE = "refuse"


class Citation(BaseModel):
    article_id: str = Field(description="Legal article identifier, e.g., 'Dieu_35' or 'Điều 35'")
    law_name: str = Field(default="Bộ luật Lao động 2019", description="Statute title")
    exact_quote: Optional[str] = Field(default=None, description="Direct statutory text quotation supporting the statement")


class AgentAction(BaseModel):
    thought: str = Field(description="Step-by-step agent reasoning before deciding an action")
    action: ActionType = Field(description="Chosen action: search_law, get_article, answer, clarify, refuse")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the chosen action or tool")


class L1VerificationResult(BaseModel):
    is_valid: bool = Field(description="True if all claims and citations pass L1 verification checks")
    unsupported_claims: List[str] = Field(default_factory=list, description="Claim sentences lacking statutory evidence")
    invalid_citations: List[str] = Field(default_factory=list, description="Non-existent or un-retrieved article identifiers")
    repair_feedback: Optional[str] = Field(default=None, description="Self-repair guidance fed back to the agent upon violation")


class CaseLedger(BaseModel):
    """
    Short-term working memory ledger tracking state, budgets, and provenance of an advisory session.
    """
    session_id: str
    original_query: str
    untrusted_documents: List[str] = Field(default_factory=list)
    extracted_facts: List[str] = Field(default_factory=list)
    queries_issued: List[str] = Field(default_factory=list)
    retrieved_article_ids: List[str] = Field(default_factory=list)
    retrieved_articles_cache: Dict[str, str] = Field(default_factory=dict)
    
    # Budgets
    tool_calls_count: int = 0
    max_tool_calls: int = 5
    repairs_count: int = 0
    max_repairs: int = 2
    step_count: int = 0
    max_steps: int = 10
    
    # State tracking
    is_terminal: bool = False
    terminal_status: Optional[Literal["answered", "clarified", "refused"]] = None
    final_output: Optional[Dict[str, Any]] = None
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)

    def can_call_tool(self) -> bool:
        return self.tool_calls_count < self.max_tool_calls

    def can_repair(self) -> bool:
        return self.repairs_count < self.max_repairs

    def can_step(self) -> bool:
        return self.step_count < self.max_steps

    def record_step(self):
        self.step_count += 1

    def record_tool_call(self, tool_name: str, args: Dict[str, Any], result_summary: str):
        self.tool_calls_count += 1
        self.audit_events.append({
            "event": "tool_call",
            "count": self.tool_calls_count,
            "tool": tool_name,
            "args": args,
            "result_summary": result_summary
        })

    def record_repair(self, feedback: str):
        self.repairs_count += 1
        self.audit_events.append({
            "event": "repair",
            "count": self.repairs_count,
            "feedback": feedback
        })
