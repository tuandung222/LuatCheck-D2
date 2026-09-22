"""
Base Protocol Interfaces for LuatCheck Architecture.

Defines decoupled Strategy Protocols (Abstract Protocols) allowing Data Scientists
to easily swap in custom components (Custom Retriever, Custom LLM Backend, Custom Verifier).
"""
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional, Tuple


@runtime_checkable
class BaseRetriever(Protocol):
    """Standard protocol interface for legal document retrieval engines."""
    corpus: List[Dict[str, Any]]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search legal provisions relevant to the query."""
        ...

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Fetch verbatim article text by canonical article identifier."""
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
        """Verify factual correctness and statutory evidence grounding of the generated answer."""
        ...
