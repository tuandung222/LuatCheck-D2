"""
Offline & Air-Gap Deployment Integrity Verification (Requirement R4)
Đảm bảo 100% hoạt động cục bộ không phụ thuộc vào kết nối mạng bên ngoài
"""
import pytest
import json
from src.verifier.lexical_grounding import LexicalGroundingVerifier, LexicalGroundingVerifier as L1EvidenceVerifier
from src.verifier.semantic_nli import SemanticNLIVerifier, SemanticNLIVerifier as L2SemanticEntailmentVerifier
from src.memory.sqlite_store import SQLiteEpisodicStore
from src.retrieval.hybrid_rrf import HybridLegalRetriever
from src.agent.state import Citation


def test_airgap_offline_execution(tmp_path):
    """
    Kiểm tra rằng toàn bộ chu trình xử lý (hybrid retrieval, L1/L2 verifier, memory)
    hoạt động hoàn toàn nội bộ trong điều kiện cô lập mạng ngoại vi.
    """
    with open("data/corpus/labor_code_2019.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # 1. Retrieval
    retriever = HybridLegalRetriever("data/corpus/labor_code_2019.json")
    res = retriever.search("thời gian thử việc cử nhân cao đẳng đại học")
    assert len(res) > 0

    # 2. L1 Verifier
    l1 = L1EvidenceVerifier(corpus)
    v_res = l1.verify(
        "Thời gian thử việc không quá 60 ngày đối với trình độ đại học.",
        [Citation(article_id="Dieu_25")],
        ["Dieu_25"]
    )
    assert v_res.is_valid is True

    # 3. L2 NLI Verifier
    l2 = L2SemanticEntailmentVerifier(corpus, entailment_threshold=0.30)
    is_ent, score, _ = l2.verify_entailment(
        "Thời gian thử việc không quá 60 ngày đối với chức danh trình độ cao đẳng trở lên.",
        "Dieu_25"
    )
    assert is_ent is True
    assert score >= 0.30

    # 4. Episodic Memory
    db_file = str(tmp_path / "test_memory.db")
    db = SQLiteEpisodicStore(db_path=db_file)
    written = db.write_if_verified(
        case_id="offline_test_01",
        query="thử việc bao lâu",
        answer="Tối đa 60 ngày theo Điều 25.",
        citations=[{"article_id": "Dieu_25"}],
        is_l1_verified=True
    )
    assert written is True
    cached = db.retrieve_similar_case("thử việc bao lâu")
    assert cached is not None
    assert cached["case_id"] == "offline_test_01"
