"""
Base Protocol Interfaces for LuatCheck Architecture
Cung cấp các giao diện mở (Protocols / Abstract Base Classes) cho phép Data Scientist
dễ dàng cắm các thành phần tùy biến (Custom Retriever, Custom LLM Backend, Custom Verifier).
"""
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional, Tuple


@runtime_checkable
class BaseRetriever(Protocol):
    """Giao diện chuẩn cho thành phần truy xuất pháp luật (Retriever Engine)."""
    corpus: List[Dict[str, Any]]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Tìm kiếm điều luật liên quan đến query."""
        ...

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết văn bản điều luật theo mã định danh."""
        ...


@runtime_checkable
class BaseLLMClient(Protocol):
    """Giao diện chuẩn cho thành phần sinh suy luận (LLM Engine)."""

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[Any] = None) -> Dict[str, Any]:
        """Sinh hành động tiếp theo cho ReAct agent (dưới dạng JSON dict hợp lệ)."""
        ...


@runtime_checkable
class BaseVerifier(Protocol):
    """Giao diện chuẩn cho thành phần kiểm chứng căn cứ (Evidence Verifier)."""

    def verify(self, answer_text: str, citations: List[Any], retrieved_article_ids: List[str]) -> Any:
        """Kiểm chứng tính đúng đắn và căn cứ pháp lý của câu trả lời."""
        ...
