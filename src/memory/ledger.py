"""
Short-term memory: Case Ledger
Quản lý ngữ cảnh và ngân sách của phiên tư vấn
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
