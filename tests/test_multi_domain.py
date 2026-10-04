"""
Unit and integration tests for Multi-Domain Knowledge Architecture.
Validates UniversalDocument, HybridDomainRetriever, DomainKnowledgeRegistry,
and Agent execution on non-legal domain corpora (Enterprise IT SOPs).
"""
import pytest
from src.contracts.universal_document import UniversalDocument, UniversalCitation
from src.retrieval.hybrid_domain import HybridDomainRetriever
from src.tools.domain_tools import DomainKnowledgeRegistry
from src.agent.loop import LuatCheckAgent
from src.verifier.pipeline import VerificationPipeline, VerificationMode


def test_universal_document_attributes():
    doc = UniversalDocument(
        doc_id="SOP_SEC_01",
        collection_id="enterprise_sop",
        source_name="Quy trình An toàn Thông tin",
        section_title="SOP 01: Ứng phó sự cố",
        content="Nội dung quy trình xử lý sự cố."
    )
    assert doc.article_id == "SOP_SEC_01"
    assert doc.law_name == "Quy trình An toàn Thông tin"
    assert doc.title == "SOP 01: Ứng phó sự cố"

    # From legacy dict conversion
    legacy_data = {
        "article_id": "Dieu_10",
        "law_name": "Bộ luật Dân sự",
        "title": "Điều 10",
        "content": "Nội dung điều 10"
    }
    converted = UniversalDocument.from_dict(legacy_data)
    assert converted.doc_id == "Dieu_10"
    assert converted.source_name == "Bộ luật Dân sự"


def test_hybrid_domain_retriever_tech_sop():
    retriever = HybridDomainRetriever(corpus_path="data/corpus/tech_sop.json")
    assert len(retriever.corpus) == 3

    # Search incident response
    results = retriever.search("quy trình ứng phó sự cố an ninh mạng", top_k=2)
    assert len(results) >= 1
    assert results[0]["doc_id"] == "SOP_SEC_01"
    assert "SOP 01" in results[0]["title"]

    # Search backup disaster recovery
    backup_res = retriever.search("sao lưu và phục hồi thảm họa cơ sở dữ liệu", top_k=2)
    assert len(backup_res) >= 1
    assert backup_res[0]["doc_id"] == "SOP_BACKUP_03"

    # Fetch document by id
    doc = retriever.get_document_by_id("SOP_DEPLOY_02")
    assert doc is not None
    assert "Zero-Downtime" in doc["title"]


def test_domain_knowledge_registry():
    registry = DomainKnowledgeRegistry(corpus_path="data/corpus/tech_sop.json")

    # Search knowledge
    search_res = registry.search_knowledge("triển khai blue-green", top_k=2)
    assert search_res["status"] == "success"
    assert len(search_res["documents"]) >= 1
    assert search_res["documents"][0]["doc_id"] == "SOP_DEPLOY_02"

    # Get document
    doc_res = registry.get_document("SOP_SEC_01")
    assert doc_res["status"] == "success"
    assert doc_res["doc_id"] == "SOP_SEC_01"
    assert "15 phút" in doc_res["full_content"]


def test_agent_multi_domain_execution():
    """Agent seamlessly executes queries and verification against an IT SOP corpus."""
    retriever = HybridDomainRetriever(corpus_path="data/corpus/tech_sop.json")
    tool_registry = DomainKnowledgeRegistry(retriever=retriever)

    agent = LuatCheckAgent(
        retriever=retriever,
        verification_mode=VerificationMode.LEXICAL_GROUNDING
    )
    assert agent.tool_registry.retriever is retriever

    # Query IT SOP knowledge
    query = "Khi xảy ra sự cố an ninh mạng thì phải làm gì trong 15 phút?"
    ledger = agent.run(query)

    assert ledger.is_terminal is True
    assert ledger.terminal_status == "answered"
    assert ledger.final_output is not None
    assert ledger.final_output.get("verified") is True
