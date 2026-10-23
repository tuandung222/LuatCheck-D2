"""
Base Protocol Interfaces for LuatCheck Architecture.

Defines decoupled Strategy Protocols (Abstract Protocols) for the components the controller
(`src/agent/loop.py`) talks to: retriever, LLM client, verifiers, tool registry and verification pipeline.
`src/pipeline/builder.py` builds the default implementations from the app config; any object that satisfies
a protocol can be injected instead.
"""
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional, Tuple


@runtime_checkable
class BaseRetriever(Protocol):
    """Standard protocol interface for document retrieval engines (first stage)."""
    corpus: List[Dict[str, Any]]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search document sections relevant to the query."""
        ...

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Fetch verbatim text by canonical document identifier."""
        ...


@runtime_checkable
class BaseLLMClient(Protocol):
    """Standard protocol interface for language model inference backends."""

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[Any] = None) -> Dict[str, Any]:
        """Generate the next ReAct action for the agent (as a validated JSON dict)."""
        ...


@runtime_checkable
class BaseVerifier(Protocol):
    """Standard protocol interface for evidence verification modules."""

    def verify(self, answer_text: str, citations: List[Any], retrieved_article_ids: List[str]) -> Any:
        """Check the generated answer against the retrieved evidence (a lexical proxy, not a correctness proof)."""
        ...


@runtime_checkable
class BaseToolRegistry(Protocol):
    """What the controller needs from the tool registry: the search and read tools over a retriever."""
    retriever: BaseRetriever

    def search_with_metadata(self, query: str, top_k: int = 5) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """(model-visible result, audit metadata for the ledger only)."""
        ...

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Verbatim text of one document section, or an error result for an unknown ID."""
        ...


@runtime_checkable
class BaseVerificationPipeline(Protocol):
    """Runs the configured verification stages (off | L1 | L1 + L2, optional NLI step) on one answer."""
    mode: str

    def verify(self, answer_text: str, citations: List[Any], retrieved_article_ids: List[str]) -> Any:
        """Result with `is_valid`, `repair_feedback`, `mode` and optional `nli_result`."""
        ...


# Self-documenting domain-agnostic protocol aliases
BaseGroundingVerifier = BaseVerifier


@runtime_checkable
class BaseNLIVerifier(Protocol):
    """Standard protocol interface for semantic natural language inference (NLI) entailment."""

    def verify_all_claims(self, answer_text: str, retrieved_article_ids: List[str]) -> Dict[str, Any]:
        """Verify semantic entailment across all constituent claim statements."""
        ...



@runtime_checkable
class BaseDenseRetriever(Protocol):
    """Standard protocol interface for dense neural embedding retrieval engines."""

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search articles by dense vector cosine similarity, returning list of (article_id, score)."""
        ...
