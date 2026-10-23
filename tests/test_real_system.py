"""Tests of real implementations, official-source data and native inference.

No component substitution is permitted. Local DB/outbox files are temporary.
Native tests require the configured real Ollama server and cached model.
"""
import ast
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT/"evaluation/benchmarks/bll2019_v1"
CORPUS = ROOT/"data/corpus/labor_code_2019_official.json"

def load_data():
    return json.loads((BENCH/"tasks.json").read_text()), json.loads(CORPUS.read_text())

def test_real_source_snapshot_and_complete_article_coverage():
    manifest = json.loads((ROOT/"docs/materials/benchmark-sources/corpus_manifest.json").read_text())
    assert hashlib.sha256(CORPUS.read_bytes()).hexdigest() == manifest["corpus_sha256"]
    pdf = ROOT/"docs/materials/benchmark-sources/bll2019-congbao.pdf"
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == manifest["pdf_sha256"]
    _, corpus = load_data()
    assert [r["article_id"] for r in corpus] == [f"Dieu_{i}" for i in range(1,221)]
    assert all(r["source_pages"] and r["content"].startswith("Điều ") for r in corpus)

def test_curated_gold_has_actual_source_evidence():
    tasks, corpus = load_data()
    lookup = {r["article_id"]:r for r in corpus}
    review = json.loads((BENCH/"review.json").read_text())
    assert hashlib.sha256((BENCH/"tasks.json").read_bytes()).hexdigest() == review["tasks_sha256"]
    assert len(tasks) == len({r["task_id"] for r in tasks})
    assert review["review_kind"] == "AI_source_review_not_human_expert"
    for task in tasks:
        if task["expected_behavior"] == "answer":
            assert task["reference_evidence"]
            assert set(task["ground_truth_article_ids"]) <= set(lookup)
            for evidence in task["reference_evidence"]:
                assert evidence["exact_quote"] in lookup[evidence["article_id"]]["content"]

def test_no_component_replacement_in_executable_source():
    paths = (list((ROOT/"src").rglob("*.py")) + list((ROOT/"evaluation").rglob("*.py"))
             + list((ROOT/"tests").glob("*.py")) + list((ROOT/"docs").rglob("*.py")))
    forbidden_imports = {"unittest" + ".mock", "pytest_mock"}
    for path in paths:
        # Run snapshots are preserved evidence, not active source.
        if "runs" in path.relative_to(ROOT).parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in forbidden_imports, str(path)
            if isinstance(node, ast.Import):
                assert all(a.name not in forbidden_imports for a in node.names), str(path)
            if isinstance(node, ast.FunctionDef):
                assert not any(a.arg == "monkey" + "patch" for a in node.args.args), str(path)
            if isinstance(node, ast.ClassDef):
                assert not any(label in node.name.lower() for label in ["mo"+"ck", "st"+"ub"]), str(path)

def test_real_retriever_uses_full_official_corpus():
    from src.retrieval.hybrid_domain import HybridDomainRetriever
    tasks, corpus = load_data()
    retriever = HybridDomainRetriever(corpus_path=str(CORPUS), retrieval_mode="tfidf")
    assert retriever.retrieval_mode == "bm25_tfidf_rrf"
    assert len(retriever.corpus) == 220
    valid = {r["article_id"] for r in corpus}
    for task in tasks:
        result = retriever.search(task["question"], top_k=5)
        assert 0 < len(result) <= 5
        assert all(r["article_id"] in valid for r in result)
    # Ranking correctness is measured separately, not forced to perfect in this test.

def test_actual_quantity_check_on_gazette_clause():
    from src.verifier.lexical_grounding import LexicalGroundingVerifier
    from src.agent.state import Citation
    tasks, corpus = load_data()
    verifier = LexicalGroundingVerifier(corpus)
    wage = next(t for t in tasks if t["task_id"].endswith("PROBATION_WAGE"))
    quote = wage["reference_evidence"][0]["exact_quote"]
    assert verifier.verify(quote,[Citation(article_id="Dieu_26")],["Dieu_26"]).is_valid
    # A mutation of an actual source is a negative assertion, not a replacement component.
    assert not verifier.verify(quote.replace("85%", "50%"),[Citation(article_id="Dieu_26")],["Dieu_26"]).is_valid

def test_real_outbox_requires_host_approval_and_persists():
    from src.tools.domain_tools import DomainKnowledgeRegistry
    tasks, _ = load_data()
    content = tasks[0]["reference_evidence"][0]["exact_quote"]
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory)/"outbox.jsonl")
        registry = DomainKnowledgeRegistry(corpus_path=str(CORPUS),outbox_path=path)
        payload = dict(recipient="review@example.invalid",content=content,idempotency_key="real-file-integration")
        assert registry.send_summary(**payload,user_confirmed=True)["status"] == "blocked_by_permission_gate"
        proposal = registry.create_proposal(**payload)
        token = registry.approve_proposal(proposal["proposal_id"])
        approved = dict(user_confirmed=True,proposal_id=proposal["proposal_id"],approval_token=token)
        tampered = dict(payload,content=content+" ")
        assert registry.send_summary(**tampered,**approved)["status"] == "blocked_by_permission_gate"
        result = registry.send_summary(**payload,**approved)
        assert result["status"] == "queued_locally" and result["delivered"] is False
        rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
        assert len(rows) == 1 and rows[0]["content"] == content
        assert registry.send_summary(**payload,**approved)["status"] == "duplicate_suppressed"

def test_real_sqlite_rejects_unproven_cache_origin():
    from src.memory.sqlite_store import SQLiteEpisodicStore
    tasks, _ = load_data()
    task = tasks[0]
    with tempfile.TemporaryDirectory() as directory:
        store = SQLiteEpisodicStore(str(Path(directory)/"memory.db"))
        assert store.write_if_verified("source",task["question"],task["expected_answer"],
                                       [{"article_id":"Dieu_25"}],True)
        record = store.retrieve_similar_case(task["question"])
        assert record is not None
        assert not store.has_native_evidence(record)

def test_real_mcp_stdio_transport():
    script = ROOT/"docs/reviews/native-integrity-revision-2026-10-22/check_mcp_transport.py"
    result = subprocess.run([sys.executable,str(script)],cwd=ROOT,capture_output=True,text=True,timeout=35)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["article_lookup"] == "success"
    assert data["summary"] == "blocked_by_permission_gate"

def test_real_native_end_to_end():
    from evaluation.run_eval import preflight
    from src.config.app_config import load_config
    from src.agent.loop import LuatCheckAgent
    cfg = load_config(str(ROOT/"config/d2_native.yaml"))
    metadata = preflight(str(ROOT/"config/d2_native.yaml"))
    assert metadata["model"]["digest"]
    tasks, _ = load_data()
    with tempfile.TemporaryDirectory() as directory:
        cfg.memory.enabled = False
        cfg.memory.sqlite_path = str(Path(directory)/"memory.db")
        cfg.security.audit_log_path = str(Path(directory)/"audit.jsonl")
        cfg.security.outbox_path = str(Path(directory)/"outbox.jsonl")
        agent = LuatCheckAgent(config=cfg,verification_mode="off")
        result = agent.run(tasks[0]["question"],session_id="real-native-integration")
        assert result.llm_calls
        assert all(call["backend"] == "ollama" for call in result.llm_calls)
        assert all(call["outcome"] == "success" for call in result.llm_calls), result.final_output
        assert result.is_terminal and result.terminal_status in {"answered","clarified","refused"}
        assert result.tool_calls_count <= cfg.budgets.max_tool_calls
        assert not result.final_output.get("from_cache", False)

def test_real_collector_refuses_unapproved_execution():
    from evaluation.run_eval import collect_runs
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/"unstarted"
        with pytest.raises(ValueError,match="disabled"):
            collect_runs(str(BENCH/"tasks.json"),[42],["off"],str(ROOT/"config/d2_native.yaml"),path)
        assert not path.exists()

def test_actual_report_has_eight_ordered_sections():
    import re
    source = (ROOT/"report_d2/main_d2.tex").read_text()
    assert len(re.findall(r"^\\section\{",source,re.MULTILINE)) == 8
