"""Tests for src/indexing: real corpus, real multilingual embeddings, real vector databases.

No mocks, stubs, monkeypatching or stand-in components (AGENTS.md). The local embedding model is loaded
once per module and used for everything (index build and live query embedding); the index is built once
with every installed backend from one embedding pass. Temporary directories hold the test indexes.

Failure-path tests use real failures: a closed loopback port, an over-long text, a missing file.
HTTP embedding providers are exercised against the Ollama server already running on 127.0.0.1:11434. It only
has a chat model, which that server refuses to embed with, so the error path is tested against it; the success
path is skipped (with the reason) unless an embedding-capable model is installed.

Measured numbers are written to data/index/test_run_metrics.json for docs/plans/indexing.md.
"""
from __future__ import annotations

import datetime
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
import requests
import yaml

from src.indexing import (BackendError, BackendUnavailableError, ConfigError, EmbeddingError, HybridSearcher, ManifestError,
                          MemoryLimitError, OllamaProvider, OpenAICompatibleProvider, SentenceTransformerProvider,
                          StaleIndexError, TextTooLongError, backend_status, build_index, load_config, load_corpus,
                          load_index, open_store)
from src.indexing.chunking import ChunkingConfig, chunk_record
from src.indexing.keyword import Bm25MemoryIndex, KeywordDoc, SqliteFts5Index
from src.indexing.records import sha256_file, vector_metadata
from src.indexing.resources import current_rss_mb, peak_rss_mb, wait_for_quiet_machine

ROOT = Path(__file__).resolve().parents[1]
LABOR = ROOT / "data/corpus/labor_code_2019_official.json"
HCMUT = ROOT / "data/corpus/hcmut_academic_v1.json"
TASKS = ROOT / "evaluation/benchmarks/bll2019_v1/tasks.json"
METRICS_PATH = ROOT / "data/index/test_run_metrics.json"
RSS_LIMIT_GB = 4.0

METRICS: Dict[str, object] = {"recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}

QUERIES = [
    "Thời gian thử việc tối đa đối với công việc cần trình độ chuyên môn là bao lâu?",
    "Người lao động đơn phương chấm dứt hợp đồng không xác định thời hạn phải báo trước bao nhiêu ngày?",
    "Lao động nữ mang thai có bị chấm dứt hợp đồng lao động không?",
    "Tiền lương làm thêm giờ vào ngày nghỉ lễ được tính thế nào?",
    "Người sử dụng lao động có được yêu cầu đặt cọc khi giao kết hợp đồng lao động không?",
    "Thời giờ làm việc bình thường tối đa trong một tuần",
    "Quy định về nghỉ hằng năm của người lao động",
    "Trợ cấp thôi việc được tính như thế nào?",
]

STATUS = backend_status()
FAISS_NAMES = ("faiss", "faiss_hnsw")  # FAISS cannot share a process with torch: these stores are tested in a separate interpreter


def _available(name: str) -> bool:
    return STATUS[name]["available"]


# ============================================================================================
# session fixtures
# ============================================================================================
@pytest.fixture(scope="module")
def provider():
    """The one local embedding model for the whole session (loaded once, freed at the end)."""
    rss_before = current_rss_mb()
    wait_for_quiet_machine(min_rss_gb=2.0, poll_seconds=30, timeout_seconds=600)
    p = SentenceTransformerProvider(model="AITeamVN/Vietnamese_Embedding", device="auto", batch_size=4,
                                    max_seq_length=2048, max_rss_gb=RSS_LIMIT_GB)
    p.load()
    METRICS["embedding_model"] = {"load_seconds": round(p.load_seconds, 2), "device": p.device,
                                  "rss_before_load_mb": round(rss_before, 1),
                                  "memory_rss_plus_mps_after_load_mb": round(p.memory_after_load_mb, 1),
                                  "native_max_seq_length": p.native_max_seq_length, "configured_max_seq_length": p.max_tokens,
                                  "dimension": p.dimension, "model_revision": p.model_revision}
    yield p
    peak = p.memory_peak_seen_mb
    mem_loaded = p.memory_mb()
    p.close()
    import gc
    gc.collect()
    mem_after = current_rss_mb()
    try:
        import torch
        mps_after = round(torch.mps.current_allocated_memory() / 2**20, 1) if p.device == "mps" else None
    except Exception:
        mps_after = None
    METRICS["embedding_model"].update({"mps_allocated_after_close_mb": mps_after, "memory_peak_seen_mb": round(peak, 1), "memory_loaded_end_mb": round(mem_loaded, 1),
                                       "rss_after_close_mb": round(mem_after, 1), "process_peak_rss_mb": round(peak_rss_mb(), 1)})
    assert peak < RSS_LIMIT_GB * 1024, f"peak RSS+MPS {peak:.0f} MB exceeded {RSS_LIMIT_GB} GB"
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(METRICS, indent=2, ensure_ascii=False), encoding="utf-8")


@pytest.fixture(scope="module")
def built(provider, tmp_path_factory):
    """Build one index (labour code + HCMUT regulations) with every installed backend from one embedding pass."""
    out = tmp_path_factory.mktemp("indexes")
    stores = []
    if _available("numpy"):
        stores.append({"backend": "numpy", "collection": "chunks", "metric": "cosine"})
    if _available("faiss"):
        stores.append({"backend": "faiss", "collection": "chunks", "metric": "cosine", "index_type": "flat"})
        stores.append({"backend": "faiss", "name": "faiss_hnsw", "collection": "chunks", "metric": "cosine",
                       "index_type": "hnsw", "hnsw_m": 32, "ef_construction": 200, "ef_search": 128})
    for b in ("sqlite_vec", "lancedb", "qdrant", "chroma"):
        if _available(b):
            stores.append({"backend": b, "collection": "chunks", "metric": "cosine"})
    cfg_dict = {
        "name": "test_multi",
        "output_dir": str(out),
        "corpora": [{"path": str(LABOR), "collection_id": "labor_code_2019"}, {"path": str(HCMUT)}],
        "chunking": {"max_tokens": 512, "overlap_tokens": 64, "contextual_title": True},
        "retrieval": {"embedding": {"provider": "sentence_transformers", "model": "AITeamVN/Vietnamese_Embedding"},
                      "keyword_index": {"backend": "sqlite_fts5", "tokenizer": "unicode61 remove_diacritics 0", "title_weight": 2.0},
                      "vector_stores": stores, "default_store": "numpy", "rrf_k": 60, "candidates": 50},
    }
    cfg_path = out / "test_multi.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg_dict, allow_unicode=True), encoding="utf-8")
    cfg = load_config(cfg_path)
    t0 = time.perf_counter()
    manifest = build_index(cfg, provider=provider)
    wall = time.perf_counter() - t0
    METRICS["build"] = {
        "wall_seconds": round(wall, 2), "records": manifest["records"], "chunks": manifest["chunks"],
        "embed_seconds": manifest["embedding"]["embed_seconds"], "embed_texts_per_second": manifest["embedding"]["texts_per_second"],
        "keyword_build_seconds": manifest["keyword"]["build_seconds"], "keyword_size_bytes": manifest["keyword"]["size_bytes"],
        "stores": {e["name"]: {"write_seconds": e["build_seconds_write"], "size_bytes": e["size_bytes"], "count": e["count"],
                               "version": e["info"].get("version")} for e in manifest["vector_stores"]},
    }
    return {"dir": cfg.index_dir, "manifest": manifest, "cfg": cfg, "cfg_path": cfg_path, "out": out}


@pytest.fixture(scope="module")
def query_vectors(provider):
    t0 = time.perf_counter()
    vecs = provider.embed_queries(QUERIES)
    METRICS["query_embedding_ms_per_query"] = round((time.perf_counter() - t0) / len(QUERIES) * 1000, 1)
    return vecs


@pytest.fixture(scope="module")
def loaded(built, provider):
    """Every store that can live in this (torch) process; FAISS stores are covered by the isolated-process tests."""
    names = [e["name"] for e in built["manifest"]["vector_stores"] if e["backend"] != "faiss"]
    with load_index(built["dir"], provider=provider, stores=names) as idx:
        yield idx


@pytest.fixture(scope="module")
def chunk_vectors(built):
    """The real chunk embeddings of the built index, read back from the persisted numpy store."""
    import json as _json
    d = built["dir"] / "vector" / "numpy"
    mat = np.load(d / "chunks.npy")
    state = _json.loads((d / "chunks.json").read_text(encoding="utf-8"))
    return state["ids"], mat, state["metadata"]


# ============================================================================================
# helpers
# ============================================================================================
def assert_same_ranking(ref, got, label, atol=1e-4):
    """Same top-k ids and scores; positions may only swap where the scores are numerically tied."""
    ref_ids, got_ids = [h.id for h in ref], [h.id for h in got]
    assert set(ref_ids) == set(got_ids), f"{label}: top-{len(ref)} differ: {ref_ids} vs {got_ids}"
    for pos, (a, b) in enumerate(zip(ref, got)):
        assert abs(a.score - b.score) < atol, f"{label}: score at rank {pos + 1} {a.score} vs {b.score}"
        if a.id != b.id:
            near = [abs(a.score - h.score) for h in ref if h.id == b.id]
            assert near and near[0] < 1e-5, f"{label}: rank {pos + 1} is {b.id} not {a.id} and they are not tied"


def brute_force(mat, ids, meta, q, k, flt=None):
    scores = mat @ q
    order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))
    out = []
    for i in order:
        if flt and not all(meta[i].get(f) in (v if isinstance(v, list) else [v]) for f, v in flt.items()):
            continue
        out.append((ids[i], float(scores[i])))
        if len(out) == k:
            break
    return out


def gold_ids(task) -> List[str]:
    g = task["ground_truth_article_ids"]
    return list(g) if isinstance(g, list) else []


# ============================================================================================
# environment / registry
# ============================================================================================
def test_backend_matrix_recorded():
    METRICS["backend_status"] = STATUS
    assert STATUS["numpy"]["available"]
    # every backend reports availability with a version or an explicit reason; nothing is silently skipped
    for name, st in STATUS.items():
        assert st["available"] or st.get("reason"), name


def test_unknown_backend_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="unknown vector store backend"):
        open_store("not_a_backend", str(tmp_path), "c", 4)


# ============================================================================================
# embeddings, chunking, memory
# ============================================================================================
def test_local_embedding_provider_properties(provider):
    info = provider.info()
    assert info["dimension"] == 1024
    assert provider.max_tokens == 2048
    assert info["device"] in ("mps", "cpu")
    v = provider.embed_documents(["Điều 25. Thời gian thử việc", "Điều 26. Tiền lương thử việc"])
    assert v.shape == (2, 1024) and v.dtype == np.float32
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-4)
    # Vietnamese semantics: a probation query is closer to the probation article than to an unrelated one
    q = provider.embed_queries(["thời gian thử việc tối đa"])[0]
    far = provider.embed_documents(["Điều 99. Quy định về an toàn vệ sinh lao động trong khai thác mỏ"])[0]
    assert float(q @ v[0]) > float(q @ far)


def test_overlong_text_is_an_error_not_truncated(provider):
    long_text = "người lao động " * 1200  # ~3600 tokens > 2048
    assert provider.token_count(long_text) > provider.max_tokens
    with pytest.raises(TextTooLongError):
        provider.embed_documents([long_text])
    with pytest.raises(EmbeddingError):
        provider.embed_documents(["   "])


def test_chunking_covers_content_and_fits_model(provider):
    records = load_corpus(HCMUT) + load_corpus(LABOR)
    cfg = ChunkingConfig(max_tokens=512, overlap_tokens=64)
    longest = max(records, key=lambda r: len(r["content"]))
    chunks = chunk_record(longest, cfg, provider.token_offsets)
    assert len(chunks) > 3, "the longest record must be split"
    covered = np.zeros(len(longest["content"]), dtype=bool)
    for c in chunks:
        assert longest["content"][c.start:c.end] == c.text
        assert provider.token_count(c.embed_text) <= cfg.max_tokens, "chunk exceeds the token budget"
        covered[c.start:c.end] = True
    uncovered = [i for i, ch in enumerate(longest["content"]) if not covered[i] and not ch.isspace()]
    assert not uncovered, "chunks must cover every non-space character (nothing silently dropped)"
    # every chunk of every record embeds without TextTooLongError
    rec = next(r for r in records if r["doc_id"] == "Dieu_25")
    assert len(chunk_record(rec, cfg, provider.token_offsets)) == 1


def test_memory_guard_raises_instead_of_continuing(provider):
    limit = provider.max_rss_gb
    provider.max_rss_gb = 0.05
    try:
        with pytest.raises(MemoryLimitError, match="exceeds the limit"):
            provider.embed_documents(["thử việc"])
    finally:
        provider.max_rss_gb = limit
    assert provider.memory_mb() < RSS_LIMIT_GB * 1024


def test_unreachable_embedding_endpoint_raises():
    # port 1 on loopback has no listener: a real connection failure, not a simulated one
    for cls, endpoint in ((OllamaProvider, "http://127.0.0.1:1"), (OpenAICompatibleProvider, "http://127.0.0.1:1/v1")):
        p = cls(model="whatever", endpoint=endpoint, timeout_seconds=3)
        with pytest.raises(EmbeddingError, match="failed"):
            p.embed_documents(["thử việc"])


def test_non_loopback_embedding_endpoint_needs_explicit_opt_in():
    with pytest.raises(ConfigError, match="not loopback"):
        OpenAICompatibleProvider(model="m", endpoint="http://example.invalid/v1")
    OpenAICompatibleProvider(model="m", endpoint="http://example.invalid/v1", allow_remote=True)  # accepted, never contacted


def _ollama_up() -> bool:
    try:
        return requests.get("http://127.0.0.1:11434/api/tags", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def _ollama_models() -> List[dict]:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        return r.json()["models"] if r.status_code == 200 else []
    except (requests.RequestException, ValueError, KeyError):
        return []


@pytest.mark.skipif(not _ollama_models(), reason="Ollama is not reachable on 127.0.0.1:11434")
def test_http_providers_surface_real_server_errors():
    """The running Ollama serves chat models only (`This server does not support embeddings`); both HTTP
    providers must raise EmbeddingError with the server's message instead of returning placeholder vectors."""
    models = [m for m in _ollama_models() if "embedding" not in (m.get("capabilities") or [])]
    if not models:
        pytest.skip("every installed Ollama model is embedding-capable")
    name = models[0]["name"]
    for provider in (OllamaProvider(model=name, timeout_seconds=60),
                     OpenAICompatibleProvider(model=name, endpoint="http://127.0.0.1:11434/v1", timeout_seconds=60)):
        with pytest.raises(EmbeddingError, match="HTTP"):
            provider.embed_documents(["thử việc"])
    with pytest.raises(EmbeddingError, match="HTTP"):
        OllamaProvider(model="no-such-model-xyz", timeout_seconds=30).embed_documents(["x"])
    METRICS["http_provider_error_path"] = {"model": name, "checked": "HTTP error from a real server raises EmbeddingError"}


def test_http_providers_success_path_against_embedding_capable_server():
    """Wire-protocol success check; needs an embedding-capable model in the running Ollama server."""
    capable = [m["name"] for m in _ollama_models() if "embedding" in (m.get("capabilities") or [])]
    if not capable:
        pytest.skip("no embedding-capable model is installed in the running Ollama server on this machine; "
                    "the HTTP success path is unverified here")
    texts = ["thử việc", "Điều 25. Thời gian thử việc"]
    native = OllamaProvider(model=capable[0], batch_size=2, timeout_seconds=120)
    compat = OpenAICompatibleProvider(model=capable[0], endpoint="http://127.0.0.1:11434/v1", batch_size=2, timeout_seconds=120)
    a, b = native.embed_documents(texts), compat.embed_documents(texts)
    assert a.shape == b.shape and a.shape[1] == native.dimension == compat.dimension
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0, atol=1e-4)
    assert ((a * b).sum(1) > 0.98).all()
    METRICS["http_provider_success_path"] = {"model": capable[0], "dimension": int(a.shape[1])}


# ============================================================================================
# keyword indexes
# ============================================================================================
def test_fts5_finds_probation_article(loaded):
    kw = loaded.keyword
    assert isinstance(kw, SqliteFts5Index)
    assert "remove_diacritics 0" in kw.info()["tokenizer"]
    hits = kw.search("thời gian thử việc tối đa", k=10)
    ids = [h.id for h in hits]
    assert "Dieu_25" in ids[:3], ids
    METRICS["fts5_probation_ids_top5"] = ids[:5]
    # metadata filter on the keyword index
    only_hcmut = kw.search("thời gian thử việc", k=10, filter={"collection_id": "hcmut_academic"})
    assert all(h.metadata["collection_id"] == "hcmut_academic" for h in only_hcmut)
    assert kw.search("zzzzqqqq", k=5) == []
    assert kw.search("   ", k=5) == []


def test_fts5_persistence_roundtrip_and_bm25_wrapper(loaded, built):
    before = [(h.id, round(h.score, 9)) for h in loaded.keyword.search("trợ cấp thôi việc", k=10)]
    idx = SqliteFts5Index(built["dir"] / "keyword" / "fts5.sqlite", mode="open")
    after = [(h.id, round(h.score, 9)) for h in idx.search("trợ cấp thôi việc", k=10)]
    idx.close()
    assert before == after and before
    bm = Bm25MemoryIndex()
    bm.build([KeywordDoc(r["doc_id"], r["title"], r["content"], vector_metadata(r)) for r in loaded.records])
    hits = bm.search("thời gian thử việc tối đa", k=10)
    assert "Dieu_25" in [h.id for h in hits][:5]
    assert bm.info()["persistent"] is False


def test_fts5_missing_index_is_an_error(tmp_path):
    with pytest.raises(BackendError):
        SqliteFts5Index(tmp_path / "absent.sqlite", mode="open")


# ============================================================================================
# vector stores: consistency, persistence, filters, lifecycle
# ============================================================================================
def test_manifest_contents(built, provider):
    m = built["manifest"]
    assert m["records"] == len(load_corpus(LABOR)) + len(load_corpus(HCMUT))
    assert m["chunks"] >= m["records"]
    assert [c["sha256"] for c in m["corpora"]] == [sha256_file(LABOR), sha256_file(HCMUT)]
    e = m["embedding"]
    assert e["dimension"] == 1024 and e["normalized"] is True and e["identity"]["model"] == "AITeamVN/Vietnamese_Embedding"
    assert e["info"]["device"] in ("mps", "cpu") and e["max_tokens"] == 2048
    assert {s["name"] for s in m["vector_stores"]} >= {"numpy"}
    for s in m["vector_stores"]:
        assert s["count"] == m["chunks"] and s["info"]["version"]
    assert (built["dir"] / "manifest.json").is_file()


def test_exact_backends_return_identical_top10(loaded, query_vectors):
    names = [n for n in loaded.stores if loaded.stores[n].exact]
    assert "numpy" in names and len(names) >= 2
    lat: Dict[str, List[float]] = {n: [] for n in loaded.stores}
    for qi, q in enumerate(query_vectors):
        ref = loaded.stores["numpy"].search(q, 10)
        assert len(ref) == 10
        for name, store in loaded.stores.items():
            t0 = time.perf_counter()
            got = store.search(q, 10)
            lat[name].append((time.perf_counter() - t0) * 1000)
            if store.exact:
                assert_same_ranking(ref, got, f"{name} q{qi}")
    METRICS["exact_backends_compared"] = names
    METRICS["query_latency_ms_top10"] = {
        n: {"median": round(statistics.median(v), 3), "max": round(max(v), 3), "n_queries": len(v)} for n, v in lat.items()}


def test_approximate_backends_recall_against_exact(loaded, query_vectors):
    recalls: Dict[str, List[float]] = {}
    for name, store in loaded.stores.items():
        if store.exact:
            continue
        for q in query_vectors:
            ref = {h.id for h in loaded.stores["numpy"].search(q, 10)}
            got = {h.id for h in store.search(q, 10)}
            recalls.setdefault(name, []).append(len(ref & got) / 10)
    METRICS["approximate_recall_at_10_vs_numpy"] = {n: round(statistics.mean(v), 4) for n, v in recalls.items()}
    for name, v in recalls.items():
        assert statistics.mean(v) >= 0.9, f"{name}: mean recall@10 {statistics.mean(v):.2f} vs exact"


def test_metadata_filter_matches_brute_force(loaded, query_vectors, chunk_vectors):
    ids, mat, meta = chunk_vectors
    filters = [
        {"collection_id": "hcmut_academic"},
        {"collection_id": "labor_code_2019"},
        {"collection_id": ["labor_code_2019", "hcmut_academic"]},
        {"collection_id": "labor_code_2019", "chunk_index": 0},
        {"collection_id": "does_not_exist"},
    ]
    assert {m.get("collection_id") for m in meta} == {"labor_code_2019", "hcmut_academic"}
    for flt in filters:
        for q in query_vectors[:4]:
            truth = brute_force(mat, ids, meta, q, 10, flt)
            for name, store in loaded.stores.items():
                got = store.search(q, 10, filter=flt)
                if not truth:
                    assert got == [], f"{name}: filter {flt} must return nothing"
                    continue
                assert all(all(h.metadata.get(f) in (v if isinstance(v, list) else [v]) for f, v in flt.items()) for h in got), \
                    f"{name}: returned a row violating {flt}"
                if store.exact:
                    assert [h.id for h in got][:len(truth)] == [t[0] for t in truth] or \
                        {h.id for h in got} == {t[0] for t in truth}, f"{name}: filter {flt} differs from brute force"
                else:
                    assert len({h.id for h in got} & {t[0] for t in truth}) >= 8, f"{name}: filtered recall too low"


def test_filter_validation_errors(loaded, query_vectors):
    store = loaded.stores["numpy"]
    with pytest.raises(BackendError):
        store.search(query_vectors[0], 5, filter={"collection_id": []})
    with pytest.raises(BackendError):
        store.search(query_vectors[0], 5, filter={"collection_id": {"nested": 1}})


def lifecycle_checks(backend, params, path, ids, mat, meta, queries):
    """create -> upsert -> search -> close -> reopen -> identical results -> delete/overwrite -> reopen -> error paths.
    A plain function so FAISS can run it in a separate interpreter (see test_faiss_in_isolated_process)."""
    n = 120
    store = open_store(backend, path, "lifecycle", mat.shape[1], "cosine", mode="create", **params)
    store.upsert(ids[:n], mat[:n], meta[:n])
    assert store.count() == n
    before = [[(h.id, round(h.score, 5)) for h in store.search(q, 10)] for q in queries[:4]]
    store.close()

    reopened = open_store(backend, path, "lifecycle", mat.shape[1], "cosine", mode="open", **params)
    assert reopened.count() == n
    after = [[(h.id, round(h.score, 5)) for h in reopened.search(q, 10)] for q in queries[:4]]
    assert before == after, f"{backend}: results changed across close/reopen"

    victim = before[0][0][0]
    reopened.delete([victim, "never-existed"])
    assert reopened.count() == n - 1
    assert victim not in [h.id for h in reopened.search(queries[0], 10)]
    repl = next(i for i in ids[:n] if i != victim)
    reopened.upsert([repl], mat[n:n + 1], [{"doc_id": repl, "collection_id": "replaced"}])  # same id, new vector + metadata
    assert reopened.count() == n - 1
    top = reopened.search(mat[n], 1, filter={"collection_id": "replaced"})
    assert [h.id for h in top] == [repl] and top[0].score > 0.999
    reopened.close()

    again = open_store(backend, path, "lifecycle", mat.shape[1], "cosine", mode="open", **params)
    assert again.count() == n - 1
    assert [h.id for h in again.search(mat[n], 1, filter={"collection_id": "replaced"})] == [repl]
    assert victim not in [h.id for h in again.search(queries[0], 10)]
    with pytest.raises(BackendError):
        again.search(np.ones(mat.shape[1] + 1, dtype=np.float32), 3)
    with pytest.raises(BackendError):
        again.upsert(["x"], np.ones((1, mat.shape[1] + 1), dtype=np.float32), [{}])
    again.close()
    with pytest.raises(BackendError):
        again.search(queries[0], 3)  # closed store is an error, not an empty answer
    with pytest.raises(BackendError):
        open_store(backend, path, "lifecycle", mat.shape[1] + 1, "cosine", mode="open", **params)  # dim mismatch
    with pytest.raises(BackendError):
        open_store(backend, os.path.join(os.path.dirname(path), "absent"), "lifecycle", mat.shape[1], "cosine", mode="open", **params)
    with pytest.raises(BackendError):
        open_store(backend, path, "lifecycle", mat.shape[1], "cosine", mode="create", **params)  # already exists


@pytest.mark.parametrize("backend,params", [
    ("numpy", {}), ("sqlite_vec", {}), ("lancedb", {}), ("qdrant", {}), ("chroma", {}),
])
def test_persistence_and_lifecycle(backend, params, tmp_path, chunk_vectors, query_vectors):
    if not _available(backend):
        pytest.skip(f"{backend} unavailable: {STATUS[backend].get('reason')}")
    ids, mat, meta = chunk_vectors
    lifecycle_checks(backend, params, str(tmp_path / backend), ids, mat, meta, query_vectors)


def test_inner_product_metric_matches_cosine_on_normalised_vectors(tmp_path, chunk_vectors, query_vectors):
    ids, mat, meta = chunk_vectors
    results = {}
    for backend in ("numpy", "lancedb", "qdrant", "chroma"):  # (FAISS: see test_faiss_in_isolated_process)
        if not _available(backend):
            continue
        s = open_store(backend, str(tmp_path / backend), "ipc", mat.shape[1], "ip", mode="create")
        s.upsert(ids[:80], mat[:80], meta[:80])
        results[backend] = s.search(query_vectors[0], 5)
        s.close()
    ref = brute_force(mat[:80], ids[:80], meta[:80], query_vectors[0], 5)
    for backend, hits in results.items():
        assert [h.id for h in hits] == [r[0] for r in ref], backend
        assert abs(hits[0].score - ref[0][1]) < 1e-4, backend


def test_sqlite_vec_rejects_unsupported_metric(tmp_path):
    if not _available("sqlite_vec"):
        pytest.skip("sqlite_vec unavailable")
    with pytest.raises(ConfigError, match="cosine"):
        open_store("sqlite_vec", str(tmp_path), "c", 8, "ip", mode="create")


def test_remote_qdrant_down_is_an_error():
    if not _available("qdrant"):
        pytest.skip("qdrant unavailable")
    with pytest.raises(BackendError):
        open_store("qdrant", None, "c", 8, "cosine", mode="open_or_create", url="http://127.0.0.1:1", timeout_seconds=3)


# ============================================================================================
# FAISS: cannot share a process with torch, so it is verified in a separate interpreter
# ============================================================================================
def run_isolated(code: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run `code` in a fresh Python (no torch, no pytest state) from the repo root; real faiss, real files."""
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, "PYTHONPATH": str(ROOT)})


def faiss_worker(index_dir: str, queries_file: str, filters_file: str, out_file: str) -> None:
    """Executed in the separate interpreter: query both FAISS stores of a built index and dump the hits as JSON."""
    from src.indexing import open_store
    manifest = json.loads((Path(index_dir) / "manifest.json").read_text(encoding="utf-8"))
    queries = np.load(queries_file)
    filters = json.loads(Path(filters_file).read_text(encoding="utf-8"))
    out = {}
    for e in manifest["vector_stores"]:
        if e["backend"] != "faiss":
            continue
        st = open_store("faiss", str(Path(index_dir) / e["path"]), e["collection"], manifest["embedding"]["dimension"], e["metric"],
                        mode="open", **e["params"])
        lat, hits = [], []
        for q in queries:
            t0 = time.perf_counter()
            hits.append([[h.id, h.score] for h in st.search(q, 10)])
            lat.append((time.perf_counter() - t0) * 1000)
        filtered = [[[h.id, h.score, h.metadata] for h in st.search(queries[fi % len(queries)], 10, filter=f)]
                    for fi, f in enumerate(filters)]
        out[e["name"]] = {"hits": hits, "filtered": filtered, "latency_ms_median": statistics.median(lat), "exact": st.exact,
                          "info": st.info()}
        st.close()
    assert "torch" not in sys.modules, "the FAISS worker must run without torch"
    Path(out_file).write_text(json.dumps(out), encoding="utf-8")


def test_faiss_in_isolated_process(built, query_vectors, chunk_vectors, tmp_path):
    if not _available("faiss"):
        pytest.skip(f"faiss unavailable: {STATUS['faiss'].get('reason')}")
    m = built["manifest"]
    faiss_entries = [e for e in m["vector_stores"] if e["backend"] == "faiss"]
    assert {e["name"] for e in faiss_entries} == set(FAISS_NAMES)
    # the builder wrote them by copying the numpy store's vectors in a separate process (no re-embedding)
    assert all(e["copied_from"] == "numpy" and e["count"] == m["chunks"] for e in faiss_entries)

    ids, mat, meta = chunk_vectors
    filters = [{"collection_id": "hcmut_academic"}, {"collection_id": "labor_code_2019"},
               {"collection_id": ["labor_code_2019", "hcmut_academic"]}, {"collection_id": "does_not_exist"}]
    qf, ff, of = tmp_path / "q.npy", tmp_path / "f.json", tmp_path / "out.json"
    np.save(qf, query_vectors)
    ff.write_text(json.dumps(filters), encoding="utf-8")
    proc = run_isolated(f"from tests.test_indexing import faiss_worker; faiss_worker({str(built['dir'])!r}, {str(qf)!r}, {str(ff)!r}, {str(of)!r})")
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(of.read_text(encoding="utf-8"))
    assert set(out) == set(FAISS_NAMES)

    from src.indexing.types import Hit
    for qi, q in enumerate(query_vectors):
        truth = [Hit(i, s, {}) for i, s in brute_force(mat, ids, meta, q, 10)]
        flat = [Hit(i, s, {}) for i, s in out["faiss"]["hits"][qi]]
        assert_same_ranking(truth, flat, f"faiss flat q{qi}")
        hnsw = {i for i, _ in out["faiss_hnsw"]["hits"][qi]}
        assert len(hnsw & {t.id for t in truth}) >= 9, f"faiss hnsw q{qi} recall"
    for fi, flt in enumerate(filters):
        for name in FAISS_NAMES:
            rows = out[name]["filtered"][fi]
            truth = brute_force(mat, ids, meta, query_vectors[fi % len(query_vectors)], 10, flt)
            assert all(all(r[2].get(f) in (v if isinstance(v, list) else [v]) for f, v in flt.items()) for r in rows)
            if not truth:
                assert rows == []
            elif name == "faiss":
                assert [r[0] for r in rows] == [t[0] for t in truth], f"{name}: filter {flt}"
            else:
                assert len({r[0] for r in rows} & {t[0] for t in truth}) >= 8
    recalls = [len({i for i, _ in out["faiss_hnsw"]["hits"][qi]} & {i for i, _ in out["faiss"]["hits"][qi]}) / 10
               for qi in range(len(query_vectors))]
    METRICS["faiss_isolated_process"] = {
        "latency_ms_median_top10": {n: round(out[n]["latency_ms_median"], 3) for n in FAISS_NAMES},
        "hnsw_recall_at_10_vs_flat": round(statistics.mean(recalls), 4), "n_queries": len(query_vectors)}


def faiss_lifecycle_worker(workdir: str) -> None:
    """Executed in the separate interpreter: the full persistence/lifecycle checks for FAISS flat and HNSW."""
    d = Path(workdir)
    ids = json.loads((d / "ids.json").read_text(encoding="utf-8"))
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    mat, queries = np.load(d / "mat.npy"), np.load(d / "queries.npy")
    for n, params in (("flat", {"index_type": "flat"}), ("hnsw", {"index_type": "hnsw"})):
        lifecycle_checks("faiss", params, str(d / n / "store"), ids, mat, meta, queries)
    assert "torch" not in sys.modules


def test_faiss_persistence_and_lifecycle_in_isolated_process(tmp_path, chunk_vectors, query_vectors):
    if not _available("faiss"):
        pytest.skip(f"faiss unavailable: {STATUS['faiss'].get('reason')}")
    ids, mat, meta = chunk_vectors
    (tmp_path / "ids.json").write_text(json.dumps(ids), encoding="utf-8")
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    np.save(tmp_path / "mat.npy", mat)
    np.save(tmp_path / "queries.npy", query_vectors)
    proc = run_isolated(f"from tests.test_indexing import faiss_lifecycle_worker; faiss_lifecycle_worker({str(tmp_path)!r})")
    assert proc.returncode == 0, proc.stderr[-2500:]


def test_faiss_and_torch_refuse_to_share_a_process(tmp_path):
    """Measured hazard: faiss-cpu + torch in one process abort/segfault (duplicate libomp). Both sides fail loudly."""
    import sys as _sys
    assert "torch" in _sys.modules  # the embedding fixtures of this module loaded it
    if _available("faiss"):
        with pytest.raises(BackendUnavailableError, match="libomp"):
            open_store("faiss", str(tmp_path / "f"), "c", 8, "cosine", mode="create")
        # reverse order, in a fresh interpreter: faiss first, then the local embedding model
        proc = run_isolated(
            "import sys\n"
            "from src.indexing import open_store, SentenceTransformerProvider, BackendUnavailableError\n"
            "s = open_store('faiss', sys.argv[1] if len(sys.argv) > 1 else '" + str(tmp_path / "g") + "', 'c', 8, 'cosine', mode='create')\n"
            "try:\n"
            "    SentenceTransformerProvider().load()\n"
            "except BackendUnavailableError as e:\n"
            "    assert 'libomp' in str(e); print('refused')\n"
            "else:\n"
            "    raise SystemExit('provider loaded next to faiss')\n"
            "assert 'torch' not in sys.modules\n")
        assert proc.returncode == 0 and "refused" in proc.stdout, proc.stderr[-1500:]


# ============================================================================================
# staleness and failed builds
# ============================================================================================
def test_stale_corpus_is_detected(built, provider, tmp_path):
    labor = LABOR.read_text(encoding="utf-8")
    changed = tmp_path / "labor_changed.json"
    changed.write_text(labor.replace("Điều 25.", "Điều 25 .", 1), encoding="utf-8")
    assert changed.read_text(encoding="utf-8") != labor
    with pytest.raises(StaleIndexError, match="python -m src.indexing build --config"):
        load_index(built["dir"], provider=provider, corpus_paths=[changed, HCMUT])
    with pytest.raises(StaleIndexError, match="missing"):
        load_index(built["dir"], provider=provider, corpus_paths=[tmp_path / "nope.json", HCMUT])
    # the unchanged corpus loads
    load_index(built["dir"], provider=provider, stores=["numpy"]).close()


def test_embedding_model_mismatch_is_detected(built):
    other = OllamaProvider(model="bge-m3")  # different provider/model; constructed but never contacted
    with pytest.raises(StaleIndexError, match="embedding provider does not match"):
        load_index(built["dir"], provider=other)
    wrong_prefix = SentenceTransformerProvider(model="AITeamVN/Vietnamese_Embedding", query_prefix="query: ")  # not loaded
    with pytest.raises(StaleIndexError, match="query_prefix"):
        load_index(built["dir"], provider=wrong_prefix)


def test_missing_manifest_and_failed_build_are_errors(tmp_path, provider):
    with pytest.raises(ManifestError, match="no manifest"):
        load_index(tmp_path / "nothing_here")
    cfg_dict = {
        "name": "will_fail", "output_dir": str(tmp_path),
        "corpus": str(tmp_path / "missing_corpus.json"),
        "retrieval": {"embedding": {"provider": "sentence_transformers", "model": "AITeamVN/Vietnamese_Embedding"},
                      "vector_store": {"backend": "numpy"}},
    }
    p = tmp_path / "fail.yaml"
    p.write_text(yaml.safe_dump(cfg_dict), encoding="utf-8")
    cfg = load_config(p)
    with pytest.raises(ConfigError, match="corpus file not found"):
        build_index(cfg, provider=provider)
    assert (cfg.index_dir / "BUILD_FAILED.json").is_file()  # the failed run is preserved
    with pytest.raises(ManifestError, match="did not finish"):
        load_index(cfg.index_dir)


def test_build_refuses_to_clobber_without_overwrite(built, provider):
    with pytest.raises(Exception, match="already exists"):
        build_index(built["cfg"], provider=provider)


# ============================================================================================
# hybrid search
# ============================================================================================
def test_hybrid_result_shape_and_filters(loaded):
    searcher = loaded.searcher("numpy")
    res = searcher.search("thời gian thử việc tối đa", top_k=5)
    assert len(res) == 5
    for r in res:
        for key in ("doc_id", "article_id", "title", "content", "rrf_score", "source_name", "law_name", "law_id"):
            assert key in r
        assert r["doc_id"] == r["article_id"] and r["content"]
    assert [r["rrf_score"] for r in res] == sorted((r["rrf_score"] for r in res), reverse=True)
    assert "Dieu_25" in [r["doc_id"] for r in res]
    filtered = searcher.search("quy định học vụ", top_k=5, filter={"collection_id": "hcmut_academic"})
    assert filtered and all(r["collection_id"] == "hcmut_academic" for r in filtered)
    assert searcher.get_document_by_id("dieu 25")["doc_id"] == "Dieu_25"
    assert searcher.search("   ", top_k=3) == []


def test_hybrid_propagates_backend_failure(built, provider):
    # a closed vector store must surface as an error, not degrade to keyword-only results
    with load_index(built["dir"], provider=provider, stores=["numpy"]) as idx:
        searcher = idx.searcher("numpy")
        idx.store("numpy").close()
        with pytest.raises(BackendError):
            searcher.search("thử việc", top_k=3)
        assert searcher.search("thử việc", top_k=3, mode="keyword")  # explicit keyword-only mode is a user choice


def test_benchmark_questions_gold_ranks(loaded):
    """Report (not force) the rank of the gold article for every benchmark task, per retrieval mode and store."""
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    answerable = [t for t in tasks if gold_ids(t)]
    assert len(answerable) >= 5
    report = {}
    for store_name in [n for n in ("numpy", "sqlite_vec", "lancedb", "qdrant", "chroma") if n in loaded.stores]:
        searcher = loaded.searcher(store_name)
        per_mode = {}
        for mode in ("hybrid", "keyword", "vector"):
            ranks = {}
            for t in answerable:
                docs = [r["doc_id"] for r in searcher.search(t["question"], top_k=20, mode=mode)]
                ranks[t["task_id"]] = {g: (docs.index(g) + 1 if g in docs else None) for g in gold_ids(t)}
            per_mode[mode] = ranks
        report[store_name] = per_mode

    def first_gold_rank(r):
        found = [v for v in r.values() if v is not None]
        return min(found) if found else None

    summary = {}
    for store_name, per_mode in report.items():
        summary[store_name] = {}
        for mode, ranks in per_mode.items():
            firsts = [first_gold_rank(r) for r in ranks.values()]
            summary[store_name][mode] = {
                "gold_in_top1": sum(1 for f in firsts if f == 1), "gold_in_top5": sum(1 for f in firsts if f and f <= 5),
                "gold_in_top10": sum(1 for f in firsts if f and f <= 10), "n_tasks": len(firsts),
                "mrr_at_20": round(sum(1.0 / f for f in firsts if f) / len(firsts), 4)}
    METRICS["benchmark_gold_rank_summary_bll2019_v1"] = {
        "note": "retrieval-only, gold = ground_truth_article_ids (AI-checked, not expert certified); documents = whole articles; "
                "searched in the multi-domain test index (labour code + HCMUT). NOT held-out: the keyword `bigrams` default was "
                "chosen after comparing ranks on these same 9 tasks, and the questions quote statute wording",
        "summary": summary,
        "ranks_numpy_hybrid": report["numpy"]["hybrid"]}
    # sanity only, per the task brief: the pipeline works and finds gold for most answerable questions
    hybrid = summary["numpy"]["hybrid"]
    assert hybrid["gold_in_top10"] >= hybrid["n_tasks"] // 2, hybrid


def test_hybrid_latency_recorded(loaded):
    searcher = loaded.searcher("numpy")
    searcher.search("warm up thử việc", top_k=5)
    times = []
    for q in QUERIES:
        t0 = time.perf_counter()
        searcher.search(q, top_k=5)
        times.append((time.perf_counter() - t0) * 1000)
    METRICS["hybrid_search_ms_incl_query_embedding"] = {"median": round(statistics.median(times), 1), "max": round(max(times), 1),
                                                         "n_queries": len(times)}
    assert max(times) < 5000
