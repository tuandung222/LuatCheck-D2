"""Comprehensive retrieval benchmark comparing LuatCheck's current lexical retrieval (BM25 + TF-IDF RRF, FTS5)
against google/embeddinggemma-2 (128-d MRL) across Vector-only (NumPy, FAISS Flat/HNSW, Qdrant) and Hybrid (FTS5 + Vector RRF).

Evaluates on:
  1. bll2019_v1 (220 articles, Bộ luật Lao động 2019)
  2. labour_vi_v1 (458 articles, D2 multi-doc Vietnamese labour law)
  3. hcmut_v1 (143 sections, D2 HCMUT academic regulations)
  4. zalo_legal (GreenNode/zalo-ai-legal-text-retrieval-vn, 818 test queries on Hard-Negative 1.5K pool + 61.4K full lexical reference)
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from src.config.app_config import AppConfig
from src.domains import load_profile
from src.indexing.builder import load_index
from src.indexing.embeddings import EmbeddingProvider
from src.indexing.keyword import SqliteFts5Index
from src.pipeline.builder import build_retriever
from src.retrieval.hybrid_domain import HybridDomainRetriever, IndexedRetriever
from src.tools.domain_tools import DomainKnowledgeRegistry


# --------------------------------------------------------------------------- #
# Standard IR Metrics (Recall@k, MRR@k, NDCG@k, MAP@k)
# --------------------------------------------------------------------------- #

def compute_ir_metrics(
    rankings: List[List[str]],
    gold_sets: List[Set[str]],
    ks: Sequence[int] = (1, 5, 10, 20),
) -> Dict[str, float]:
    n = len(gold_sets)
    if n == 0:
        return {}
    metrics: Dict[str, float] = {}
    for k in ks:
        recalls = []
        for ranked, gold in zip(rankings, gold_sets):
            if not gold:
                continue
            top_k = ranked[:k]
            hits = sum(1 for doc_id in gold if doc_id in top_k)
            recalls.append(hits / len(gold))
        metrics[f"Recall@{k}"] = round(float(np.mean(recalls)) * 100.0, 2)

    mrr10, ndcg10, map10 = [], [], []
    for ranked, gold in zip(rankings, gold_sets):
        if not gold:
            continue
        top10 = ranked[:10]
        rr = 0.0
        for rank_idx, doc_id in enumerate(top10, start=1):
            if doc_id in gold:
                rr = 1.0 / rank_idx
                break
        mrr10.append(rr)

        dcg = 0.0
        for rank_idx, doc_id in enumerate(top10, start=1):
            if doc_id in gold:
                dcg += 1.0 / math.log2(rank_idx + 1)
        ideal_hits = min(len(gold), 10)
        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
        ndcg10.append(dcg / idcg if idcg > 0 else 0.0)

        hits_so_far = 0
        prec_sum = 0.0
        for rank_idx, doc_id in enumerate(top10, start=1):
            if doc_id in gold:
                hits_so_far += 1
                prec_sum += hits_so_far / rank_idx
        map10.append(prec_sum / min(len(gold), 10))

    metrics["MRR@10"] = round(float(np.mean(mrr10)) * 100.0, 2)
    metrics["NDCG@10"] = round(float(np.mean(ndcg10)) * 100.0, 2)
    metrics["MAP@10"] = round(float(np.mean(map10)) * 100.0, 2)
    return metrics


def load_luatcheck_tasks(tasks_path: Path, normalize_id: Callable[[str], str]) -> Tuple[List[str], List[Set[str]]]:
    raw = json.loads(tasks_path.read_text(encoding="utf-8"))
    queries: List[str] = []
    gold_sets: List[Set[str]] = []
    for row in raw:
        gt = row.get("ground_truth_article_ids") or []
        if row.get("expected_behavior") == "refuse" or not gt:
            continue
        queries.append(str(row["question"]).strip())
        gold_sets.append({normalize_id(str(x)) for x in gt if str(x).strip()})
    return queries, gold_sets


def load_zalo_queries(queries_path: Path, max_queries: int | None = None) -> Tuple[List[str], List[Set[str]]]:
    raw = json.loads(queries_path.read_text(encoding="utf-8"))
    if max_queries is not None:
        raw = raw[:max_queries]
    queries = [str(r["query"]).strip() for r in raw]
    gold_sets = [{str(x).strip() for x in r["relevant_doc_ids"]} for r in raw]
    return queries, gold_sets


def evaluate_faiss_subprocess(index_dir: Path, store_name: str, query_vecs_npy: Path, depth: int = 50, top_k: int = 20) -> Tuple[List[List[str]], float]:
    """Query FAISS store in an isolated subprocess (since torch and faiss cannot share libomp in one process on macOS)."""
    code = f"""
import json, time
import numpy as np
from pathlib import Path
from src.indexing.manifest import read_manifest
from src.indexing.vector_stores import open_store

index_dir = Path({str(index_dir)!r})
store_name = {store_name!r}
qvecs = np.load({str(query_vecs_npy)!r})
manifest = read_manifest(index_dir)
entry = next(e for e in manifest["vector_stores"] if e["name"] == store_name)
path = index_dir / entry["path"]
store = open_store(entry["backend"], str(path), entry["collection"], manifest["embedding"]["dimension"], entry["metric"], mode="open", **entry.get("params", {{}}))
t0 = time.perf_counter()
all_doc_ids = []
for qv in qvecs:
    hits = store.search(qv, k={depth})
    seen = []
    for h in hits:
        did = h.metadata.get("doc_id") or h.id.split("#", 1)[0]
        if did not in seen:
            seen.append(did)
            if len(seen) >= {top_k}:
                break
    all_doc_ids.append(seen)
elapsed_ms = (time.perf_counter() - t0) * 1000.0 / max(1, len(qvecs))
store.close()
print(json.dumps({{"rankings": all_doc_ids, "search_ms_per_query": round(elapsed_ms, 3)}}))
"""
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return payload["rankings"], float(payload["search_ms_per_query"])


def _vector_doc_ranking(store: Any, qvec: np.ndarray, depth: int) -> List[str]:
    hits = store.search(qvec, k=depth)
    seen: List[str] = []
    seen_set: Set[str] = set()
    for h in hits:
        did = h.metadata.get("doc_id") or h.id.split("#", 1)[0]
        if did not in seen_set:
            seen_set.add(did)
            seen.append(did)
    return seen


def _rrf_fuse(kw_ids: List[str], vec_ids: List[str], rrf_k: int = 60, top_k: int = 20) -> List[str]:
    scores: Dict[str, float] = {}
    for rank, did in enumerate(kw_ids, start=1):
        scores[did] = scores.get(did, 0.0) + 1.0 / (rrf_k + rank)
    for rank, did in enumerate(vec_ids, start=1):
        scores[did] = scores.get(did, 0.0) + 1.0 / (rrf_k + rank)
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
    return [did for did, _ in ordered]


def evaluate_suite(
    name: str,
    corpus_path: str,
    profile_name: str,
    queries: List[str],
    gold_sets: List[Set[str]],
    gemma_index_dir: Path,
    shared_provider: Optional[EmbeddingProvider] = None,
    extra_indexes: Dict[str, Path] | None = None,
    top_k: int = 20,
) -> Tuple[Dict[str, Any], EmbeddingProvider]:
    profile = load_profile(profile_name) if profile_name else None
    norm = profile.normalize_id if profile else (lambda x: str(x).strip())

    results: Dict[str, Any] = {
        "benchmark": name,
        "queries_evaluated": len(queries),
        "methods": {},
    }

    # 1. Current LuatCheck First-Stage: BM25 + TF-IDF 1-3gram RRF
    t_build0 = time.perf_counter()
    bm25_tfidf = HybridDomainRetriever(corpus_path=corpus_path, id_normalizer=norm, retrieval_mode="tfidf")
    bm25_tfidf_build_s = time.perf_counter() - t_build0

    t0 = time.perf_counter()
    rankings_bm25_tfidf = [
        [norm(r["doc_id"]) for r in bm25_tfidf.search(q, top_k=top_k)]
        for q in queries
    ]
    ms_bm25_tfidf = (time.perf_counter() - t0) * 1000.0 / len(queries)
    results["methods"]["1_LuatCheck_BM25_TFIDF_RRF (current)"] = {
        **compute_ir_metrics(rankings_bm25_tfidf, gold_sets),
        "latency_ms_per_query": round(ms_bm25_tfidf, 2),
        "build_seconds": round(bm25_tfidf_build_s, 2),
    }

    # 2. LuatCheck BM25-only
    bm25_only = HybridDomainRetriever(corpus_path=corpus_path, id_normalizer=norm, retrieval_mode="bm25")
    t0 = time.perf_counter()
    rankings_bm25 = [
        [norm(r["doc_id"]) for r in bm25_only.search(q, top_k=top_k)]
        for q in queries
    ]
    ms_bm25 = (time.perf_counter() - t0) * 1000.0 / len(queries)
    results["methods"]["2_LuatCheck_BM25_only"] = {
        **compute_ir_metrics(rankings_bm25, gold_sets),
        "latency_ms_per_query": round(ms_bm25, 2),
    }

    # 3. Evaluate google/embeddinggemma-2 (128-d) index (Keyword FTS5, Vector NumPy/Qdrant/FAISS, Hybrid FTS5+Vector RRF)
    loaded = load_index(gemma_index_dir, provider=shared_provider, stores=["numpy", "qdrant"])
    shared_provider = loaded.provider
    manifest = loaded.manifest
    depth = max(int(manifest["search"]["candidates"]), top_k)
    rrf_k = int(manifest["search"]["rrf_k"])

    try:
        # 3a. SQLite FTS5 Keyword-only
        t0 = time.perf_counter()
        kw_full_rankings = [
            [h.id for h in loaded.keyword.search(q, k=depth)]
            for q in queries
        ]
        ms_fts5 = (time.perf_counter() - t0) * 1000.0 / len(queries)
        rankings_fts5 = [[norm(d) for d in r[:top_k]] for r in kw_full_rankings]
        results["methods"]["3_SQLite_FTS5_Keyword"] = {
            **compute_ir_metrics(rankings_fts5, gold_sets),
            "latency_ms_per_query": round(ms_fts5, 2),
        }

        # Embed queries using SentenceTransformerProvider
        t_emb0 = time.perf_counter()
        q_vecs = loaded.provider.embed_queries(queries)
        emb_ms_per_query = (time.perf_counter() - t_emb0) * 1000.0 / len(queries)

        # Measure single-query unbatched latency on a sample of up to 20 queries
        sample_qs = queries[:min(20, len(queries))]
        searcher_np = loaded.searcher("numpy")
        t_sq0 = time.perf_counter()
        for sq in sample_qs:
            searcher_np.search(sq, top_k=top_k, mode="hybrid")
        single_query_hybrid_ms = (time.perf_counter() - t_sq0) * 1000.0 / len(sample_qs)

        # Save query vectors temporarily for isolated FAISS subprocess evaluation
        tmp_qvecs = gemma_index_dir / "_eval_qvecs.npy"
        np.save(tmp_qvecs, q_vecs)

        # 3b. Vector-only (NumPy exact 128-d)
        np_store = loaded.store("numpy")
        t0 = time.perf_counter()
        vec_np_full = [_vector_doc_ranking(np_store, qv, depth) for qv in q_vecs]
        np_search_ms = (time.perf_counter() - t0) * 1000.0 / len(queries)
        rankings_vec_np = [[norm(d) for d in r[:top_k]] for r in vec_np_full]
        results["methods"]["4_EmbeddingGemma2_128d_Vector_NumPy"] = {
            **compute_ir_metrics(rankings_vec_np, gold_sets),
            "search_only_ms_per_query": round(np_search_ms, 3),
            "latency_ms_per_query": round(emb_ms_per_query + np_search_ms, 2),
            "dimension": 128,
        }

        # 3c. Hybrid (SQLite FTS5 + EmbeddingGemma2 128-d Vector RRF)
        t0 = time.perf_counter()
        rankings_hybrid = [
            [norm(d) for d in _rrf_fuse(kw_r, vec_r, rrf_k=rrf_k, top_k=top_k)]
            for kw_r, vec_r in zip(kw_full_rankings, vec_np_full)
        ]
        rrf_ms = (time.perf_counter() - t0) * 1000.0 / len(queries)
        results["methods"]["5_EmbeddingGemma2_128d_Hybrid_RRF (FTS5+Vector)"] = {
            **compute_ir_metrics(rankings_hybrid, gold_sets),
            "latency_ms_per_query": round(emb_ms_per_query + ms_fts5 + np_search_ms + rrf_ms, 2),
            "single_query_unbatched_ms": round(single_query_hybrid_ms, 2),
            "dimension": 128,
        }

        # 3d. Qdrant Vector-only (128-d)
        qd_store = loaded.store("qdrant")
        t0 = time.perf_counter()
        vec_qd_full = [_vector_doc_ranking(qd_store, qv, depth) for qv in q_vecs]
        qd_search_ms = (time.perf_counter() - t0) * 1000.0 / len(queries)
        rankings_qd = [[norm(d) for d in r[:top_k]] for r in vec_qd_full]
        results["methods"]["6_EmbeddingGemma2_128d_Vector_Qdrant"] = {
            **compute_ir_metrics(rankings_qd, gold_sets),
            "search_only_ms_per_query": round(qd_search_ms, 3),
            "latency_ms_per_query": round(emb_ms_per_query + qd_search_ms, 2),
            "dimension": 128,
        }
    finally:
        loaded.close()

    # 3e. FAISS Flat & FAISS HNSW (via isolated subprocess using precomputed query embeddings)
    tmp_qvecs = gemma_index_dir / "_eval_qvecs.npy"
    try:
        rankings_faiss_flat, faiss_flat_search_ms = evaluate_faiss_subprocess(gemma_index_dir, "faiss", tmp_qvecs, depth=depth, top_k=top_k)
        rankings_faiss_flat_norm = [[norm(d) for d in r] for r in rankings_faiss_flat]
        results["methods"]["7_EmbeddingGemma2_128d_Vector_FAISS_Flat"] = {
            **compute_ir_metrics(rankings_faiss_flat_norm, gold_sets),
            "search_only_ms_per_query": round(faiss_flat_search_ms, 3),
            "latency_ms_per_query": round(emb_ms_per_query + faiss_flat_search_ms, 2),
            "dimension": 128,
        }

        rankings_faiss_hnsw, faiss_hnsw_search_ms = evaluate_faiss_subprocess(gemma_index_dir, "faiss_hnsw", tmp_qvecs, depth=depth, top_k=top_k)
        rankings_faiss_hnsw_norm = [[norm(d) for d in r] for r in rankings_faiss_hnsw]
        results["methods"]["8_EmbeddingGemma2_128d_Vector_FAISS_HNSW"] = {
            **compute_ir_metrics(rankings_faiss_hnsw_norm, gold_sets),
            "search_only_ms_per_query": round(faiss_hnsw_search_ms, 3),
            "latency_ms_per_query": round(emb_ms_per_query + faiss_hnsw_search_ms, 2),
            "dimension": 128,
        }
    finally:
        if tmp_qvecs.exists():
            tmp_qvecs.unlink()

    # 4. Optional comparison against existing indexes (e.g. EmbeddingGemma2 768-d or Vietnamese_Embedding 1024-d)
    if extra_indexes:
        for label, idx_path in extra_indexes.items():
            if idx_path.exists():
                loaded_extra = load_index(idx_path, stores=["numpy", "qdrant"] if (idx_path / "vector" / "qdrant").exists() else ["numpy"])
                try:
                    dim = loaded_extra.manifest["embedding"]["dimension"]
                    t_e0 = time.perf_counter()
                    q_vecs_ex = loaded_extra.provider.embed_queries(queries)
                    emb_ex_ms = (time.perf_counter() - t_e0) * 1000.0 / len(queries)

                    np_ex = loaded_extra.store("numpy")
                    t0 = time.perf_counter()
                    vec_ex_full = [_vector_doc_ranking(np_ex, qv, depth) for qv in q_vecs_ex]
                    np_ex_ms = (time.perf_counter() - t0) * 1000.0 / len(queries)
                    r_vec = [[norm(d) for d in r[:top_k]] for r in vec_ex_full]
                    results["methods"][f"{label}_Vector_NumPy_{dim}d"] = {
                        **compute_ir_metrics(r_vec, gold_sets),
                        "search_only_ms_per_query": round(np_ex_ms, 3),
                        "latency_ms_per_query": round(emb_ex_ms + np_ex_ms, 2),
                        "dimension": dim,
                    }

                    t0 = time.perf_counter()
                    r_hyb = [
                        [norm(d) for d in _rrf_fuse(kw_r, vec_r, rrf_k=rrf_k, top_k=top_k)]
                        for kw_r, vec_r in zip(kw_full_rankings, vec_ex_full)
                    ]
                    rrf_ex_ms = (time.perf_counter() - t0) * 1000.0 / len(queries)
                    results["methods"][f"{label}_Hybrid_RRF_{dim}d (FTS5+Vector)"] = {
                        **compute_ir_metrics(r_hyb, gold_sets),
                        "latency_ms_per_query": round(emb_ex_ms + ms_fts5 + np_ex_ms + rrf_ex_ms, 2),
                        "dimension": dim,
                    }

                    tmp_q_ex = idx_path / "_eval_qvecs.npy"
                    np.save(tmp_q_ex, q_vecs_ex)
                    try:
                        store_names = {e["name"] for e in loaded_extra.manifest["vector_stores"]}
                        if "faiss" in store_names:
                            r_ff, ff_ms = evaluate_faiss_subprocess(idx_path, "faiss", tmp_q_ex, depth=depth, top_k=top_k)
                            results["methods"][f"{label}_Vector_FAISS_Flat_{dim}d"] = {
                                **compute_ir_metrics([[norm(d) for d in r] for r in r_ff], gold_sets),
                                "search_only_ms_per_query": round(ff_ms, 3),
                                "latency_ms_per_query": round(emb_ex_ms + ff_ms, 2),
                                "dimension": dim,
                            }
                        if "faiss_hnsw" in store_names:
                            r_fh, fh_ms = evaluate_faiss_subprocess(idx_path, "faiss_hnsw", tmp_q_ex, depth=depth, top_k=top_k)
                            results["methods"][f"{label}_Vector_FAISS_HNSW_{dim}d"] = {
                                **compute_ir_metrics([[norm(d) for d in r] for r in r_fh], gold_sets),
                                "search_only_ms_per_query": round(fh_ms, 3),
                                "latency_ms_per_query": round(emb_ex_ms + fh_ms, 2),
                                "dimension": dim,
                            }
                    finally:
                        if tmp_q_ex.exists():
                            tmp_q_ex.unlink()
                finally:
                    loaded_extra.provider.close()
                    loaded_extra.close()

    results["index_summary"] = {
        "index_dir": str(gemma_index_dir),
        "records": manifest["records"],
        "chunks": manifest["chunks"],
        "build_seconds": manifest["build_seconds"],
        "texts_per_second": manifest["embedding"]["texts_per_second"],
        "stores": {
            e["name"]: {
                "backend": e["backend"],
                "size_kb": round((e.get("size_bytes") or 0) / 1024.0, 1),
                "write_seconds": e["build_seconds_write"],
            }
            for e in manifest["vector_stores"]
        },
    }
    return results, shared_provider


def verify_pipeline_and_ui_wiring(shared_provider: Optional[EmbeddingProvider] = None) -> Dict[str, Any]:
    """Verify end-to-end integration with LuatCheck's pipeline builder, DomainKnowledgeRegistry, and Web Demo runtime."""
    cfg = AppConfig()
    cfg.retrieval.mode = "hybrid_index"
    cfg.retrieval.index.path = "data/index/labor_code_2019_gemma2_128d"
    cfg.retrieval.index.store = "numpy"
    cfg.retrieval.index.search_mode = "hybrid"

    profile = load_profile(cfg.domain.profile, variant=cfg.domain.profile_variant)
    retriever = build_retriever(cfg.retrieval, corpus_path=cfg.retrieval.corpus_path, endpoint=None, manager=None, profile=profile)
    assert isinstance(retriever, IndexedRetriever), f"Expected IndexedRetriever, got {type(retriever)}"

    registry = DomainKnowledgeRegistry(corpus_path=cfg.retrieval.corpus_path, outbox_path=cfg.security.outbox_path, retriever=retriever, profile=profile)
    search_res = registry.search_law("thời gian thử việc tối đa trình độ cao đẳng trở lên", top_k=5)
    read_res = registry.get_article("Dieu_25")
    doc_direct = retriever.get_document_by_id("Điều 25")  # test alias resolution on IndexedRetriever
    retriever.close()

    top_articles = [a["article_id"] for a in search_res.get("articles", [])]
    return {
        "retriever_class": type(retriever).__name__,
        "search_law_top_articles": top_articles,
        "read_law_resolved": "60 ngày" in read_res.get("full_content", ""),
        "alias_resolution_Dieu_25": doc_direct is not None and doc_direct.get("article_id") == "Dieu_25",
    }


def main() -> None:
    all_results: Dict[str, Any] = {
        "pipeline_and_ui_verification": verify_pipeline_and_ui_wiring(),
        "benchmarks": {},
    }

    shared_provider: Optional[EmbeddingProvider] = None
    try:
        # 1. BLL2019 (220 articles)
        p_bll = load_profile("labour_vi_2019")
        q_bll, g_bll = load_luatcheck_tasks(Path("evaluation/benchmarks/bll2019_v1/tasks.json"), p_bll.normalize_id)
        res_bll, shared_provider = evaluate_suite(
            name="bll2019_v1 (Bộ luật Lao động 2019 - 220 điều)",
            corpus_path="data/corpus/labor_code_2019_official.json",
            profile_name="labour_vi_2019",
            queries=q_bll,
            gold_sets=g_bll,
            gemma_index_dir=Path("data/index/labor_code_2019_gemma2_128d"),
            shared_provider=shared_provider,
            extra_indexes={
                "9_EmbeddingGemma2_768d": Path("data/index/labor_code_2019_gemma2_768d"),
                "10_Vietnamese_Embedding_1024d": Path("data/index/labor_code_2019"),
            },
        )
        all_results["benchmarks"]["bll2019_v1"] = res_bll

        # 2. Labour VI v1 (458 articles)
        p_lvn = load_profile("labour_vi_multi")
        q_lvn, g_lvn = load_luatcheck_tasks(Path("evaluation/benchmarks/labour_vi_v1/tasks.json"), p_lvn.normalize_id)
        res_lvn, shared_provider = evaluate_suite(
            name="labour_vi_v1 (Đa văn bản Pháp luật Lao động - 458 điều)",
            corpus_path="data/corpus/labour_vi_v1.json",
            profile_name="labour_vi_multi",
            queries=q_lvn,
            gold_sets=g_lvn,
            gemma_index_dir=Path("data/index/labour_vi_v1_gemma2_128d"),
            shared_provider=shared_provider,
            extra_indexes={"9_EmbeddingGemma2_768d": Path("data/index/labour_vi_v1_gemma2_768d")},
        )
        all_results["benchmarks"]["labour_vi_v1"] = res_lvn

        # 3. HCMUT Academic v1 (143 sections)
        p_hcmut = load_profile("hcmut_academic")
        q_hcmut, g_hcmut = load_luatcheck_tasks(Path("evaluation/benchmarks/hcmut_v1/tasks.json"), p_hcmut.normalize_id)
        res_hcmut, shared_provider = evaluate_suite(
            name="hcmut_v1 (Quy chế Học vụ ĐHBK HCMUT - 143 mục)",
            corpus_path="data/corpus/hcmut_academic_v1.json",
            profile_name="hcmut_academic",
            queries=q_hcmut,
            gold_sets=g_hcmut,
            gemma_index_dir=Path("data/index/hcmut_academic_v1_gemma2_128d"),
            shared_provider=shared_provider,
            extra_indexes={"9_EmbeddingGemma2_768d": Path("data/index/hcmut_academic_v1_gemma2_768d")},
        )
        all_results["benchmarks"]["hcmut_v1"] = res_hcmut

        # 4. GreenNode Zalo AI Legal Text Retrieval (818 test queries on 1,000 Hard-Negative Pool + 61,425 Full FTS5)
        q_zalo, g_zalo = load_zalo_queries(Path("data/benchmarks/zalo_legal/test_queries.json"))
        zalo_res, shared_provider = evaluate_suite(
            name="zalo_legal_hard1k (GreenNode Zalo AI Legal - 1,000 Hard-Negative Pool, 818 queries)",
            corpus_path="data/benchmarks/zalo_legal/corpus_eval_hard2k.json",
            profile_name="",
            queries=q_zalo,
            gold_sets=g_zalo,
            gemma_index_dir=Path("data/index/zalo_legal_gemma2_128d"),
            shared_provider=shared_provider,
            extra_indexes={"9_EmbeddingGemma2_768d": Path("data/index/zalo_legal_gemma2_768d")},
        )

        # Also evaluate SQLite FTS5 on the full 61,425-article Zalo corpus
        fts_61k_path = Path("data/benchmarks/zalo_legal/fts5_full_61k.sqlite")
        if fts_61k_path.exists():
            fts_61k = SqliteFts5Index(path=str(fts_61k_path), mode="open")
            try:
                t0 = time.perf_counter()
                r_fts61k = [[h.id for h in fts_61k.search(q, k=20)] for q in q_zalo]
                ms_fts61k = (time.perf_counter() - t0) * 1000.0 / len(q_zalo)
                zalo_res["methods"]["0_SQLite_FTS5_Full_61425_Corpus (reference)"] = {
                    **compute_ir_metrics(r_fts61k, g_zalo),
                    "latency_ms_per_query": round(ms_fts61k, 2),
                    "corpus_size": 61425,
                }
            finally:
                fts_61k.close()

        all_results["benchmarks"]["zalo_legal"] = zalo_res
    finally:
        if shared_provider is not None:
            shared_provider.close()

    out_path = Path("data/benchmarks/zalo_legal/retrieval_comparison_results.json")
    out_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
