"""
Short-term memory: Case Ledger
Quản lý ngữ cảnh, ngân sách và dòng sự kiện của phiên tư vấn
"""
from typing import List, Dict, Any, Optional
from src.agent.state import CaseLedger


class CaseLedgerManager:
    @staticmethod
    def create_session(session_id: str, query: str, untrusted_docs: Optional[List[str]] = None) -> CaseLedger:
        return CaseLedger(
            session_id=session_id,
            original_query=query,
            untrusted_documents=untrusted_docs or [],
            extracted_facts=[],
            queries_issued=[],
            retrieved_article_ids=[],
            retrieved_articles_cache={},
            tool_calls_count=0,
            repairs_count=0,
            is_terminal=False,
            terminal_status=None,
            final_output=None,
            audit_events=[]
        )

    @staticmethod
    def add_retrieved_article(ledger: CaseLedger, article_id: str, content: str):
        if article_id not in ledger.retrieved_article_ids:
            ledger.retrieved_article_ids.append(article_id)
        ledger.retrieved_articles_cache[article_id] = content

    @staticmethod
    def add_query(ledger: CaseLedger, query: str):
        """Ghi nhận truy vấn tìm kiếm pháp luật được phát ra trong phiên"""
        ledger.queries_issued.append(query)

    @staticmethod
    def add_fact(ledger: CaseLedger, fact: str):
        """Trích xuất và lưu trữ dữ kiện pháp lý từ câu hỏi của người dùng"""
        if fact not in ledger.extracted_facts:
            ledger.extracted_facts.append(fact)

    @staticmethod
    def record_cache_hit(
        ledger: CaseLedger,
        case_id: str,
        article_ids: List[str],
        articles_cache: Optional[Dict[str, str]] = None
    ):
        """Khôi phục và nạp căn cứ pháp lý từ episodic store vào ledger hiện tại"""
        for aid in article_ids:
            if aid not in ledger.retrieved_article_ids:
                ledger.retrieved_article_ids.append(aid)
        if articles_cache:
            ledger.retrieved_articles_cache.update(articles_cache)
        ledger.audit_events.append({
            "event": "cache_hit",
            "case_id": case_id,
            "article_ids": article_ids
        })
