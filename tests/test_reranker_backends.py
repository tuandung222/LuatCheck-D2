"""Real tests for the reranker backends used by D2: LlamaCppReranker (GGUF on llama-server), CrossEncoderReranker and
the shared chunking / truncation policy in src/retrieval/rerankers.py.

No mocks, stubs, patched functions, fake servers or canned responses.  Tests that need the reranking server
(`scripts/reranker/serve_mac.sh`, 127.0.0.1:8082) FAIL with a clear message when it is down (never skip), like
`needs_server` in tests/test_benchmark_runner.py.  The torch reference uses the cached Hugging Face weights of
AITeamVN/Vietnamese_Reranker (revision f536976) and is unloaded after each use (16 GB Mac: one heavy model at a time).
Run only this file:  .venv/bin/python -m pytest -q tests/test_reranker_backends.py
"""
import gc
import inspect
import json
import socket
from pathlib import Path

import pytest
import requests

from src.model_runtime import ModelComponentError, doc_text, flush_accelerator_cache
from src.retrieval.rerankers import (
    CrossEncoderReranker,
    LlamaCppReranker,
    build_reranker,
    split_chunks,
)

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "http://127.0.0.1:8082"
HF_MODEL = "AITeamVN/Vietnamese_Reranker"
SERVER_DOWN = ("reranking llama-server not reachable on 127.0.0.1:8082: start it with "
               "`scripts/reranker/serve_mac.sh` (tests never start it; build the GGUF with "
               "scripts/reranker/build_gguf.sh)")
HCMUT = json.loads((ROOT / "data/corpus/hcmut_academic_v1.json").read_text(encoding="utf-8"))
LONG_RECORD = next(r for r in HCMUT if r["doc_id"] == "HCMUT_CTDT1862_Dieu_1")   # 19.6k chars
# HCMUT-034: gold evidence starts at character 4698 of this record (reference_evidence in tasks.json).


def server_up() -> bool:
    try:
        return requests.get(f"{ENDPOINT}/v1/models", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def needs_server(test):
    """Real-inference tests fail (never skip) when the reranking server is down."""
    def wrapper(*args, **kwargs):
        assert server_up(), SERVER_DOWN
        return test(*args, **kwargs)
    wrapper.__name__, wrapper.__doc__ = test.__name__, test.__doc__
    wrapper.__signature__ = inspect.signature(test)
    return wrapper


def served_alias() -> str:
    return requests.get(f"{ENDPOINT}/v1/models", timeout=5).json()["data"][0]["id"]


def long_query() -> str:
    tasks = json.loads((ROOT / "evaluation/benchmarks/hcmut_v1/tasks.json").read_text(encoding="utf-8"))
    return next(t["question"] for t in tasks if t["task_id"] == "HCMUT-034")


@pytest.fixture()
def torch_reference():
    ref = CrossEncoderReranker(HF_MODEL, device="cpu", dtype="float32", local_files_only=True, max_length=1024,
                               chunk_chars=None)
    yield ref
    ref.unload()
    gc.collect()
    flush_accelerator_cache()


# --------------------------------------------------------------------------- #
# chunking policy (pure function, real text from the benchmark corpus)
# --------------------------------------------------------------------------- #

class TestChunking:
    def test_short_text_is_one_unchanged_chunk(self):
        assert split_chunks("Điều 1. Ngắn", 1500) == ["Điều 1. Ngắn"]

    def test_long_record_is_fully_covered_with_title_prefix(self):
        text = doc_text(LONG_RECORD)
        chunks = split_chunks(text, 1500, 200)
        assert len(chunks) > 10 and chunks[0] == text[: len(chunks[0])]
        title = text.split("\n", 1)[0]
        assert all(c.startswith(title) for c in chunks[1:])          # every later window names its section
        assert all(len(c) <= 1500 for c in chunks)
        for offset in range(0, len(text) - 80, 97):                  # every 80-char probe lies inside some chunk
            assert any(text[offset: offset + 80] in c for c in chunks), offset
        assert chunks == split_chunks(text, 1500, 200)               # deterministic

    def test_gold_evidence_of_hcmut_034_lands_in_a_later_chunk(self):
        text = doc_text(LONG_RECORD)
        tasks = json.loads((ROOT / "evaluation/benchmarks/hcmut_v1/tasks.json").read_text(encoding="utf-8"))
        ev = next(t for t in tasks if t["task_id"] == "HCMUT-034")["reference_evidence"][0]
        at = LONG_RECORD["content"].find(ev["exact_quote"])
        assert at > 3000, "benchmark evidence is expected beyond the first 3000 characters"
        chunks = split_chunks(text, 1500, 200)
        assert not any(ev["exact_quote"] in c for c in chunks[:2])
        assert any(ev["exact_quote"] in c for c in chunks)

    @pytest.mark.parametrize("bad", [{"chunk_chars": 100}, {"chunk_chars": 1500, "chunk_overlap_chars": 900},
                                     {"chunk_chars": True}, {"chunk_chars": 1500, "chunk_overlap_chars": -1}])
    def test_bad_chunk_config_is_rejected(self, bad):
        with pytest.raises(ModelComponentError) as err:
            build_reranker({"backend": "llama_cpp", "endpoint": ENDPOINT, **bad})
        assert err.value.kind == "config_error"

    def test_policy_defaults_are_identical_across_backends(self):
        mac = build_reranker({"backend": "llama_cpp", "endpoint": ENDPOINT})
        gpu = build_reranker({"backend": "cross_encoder", "model": "x/y"})
        assert (mac.chunk_chars, mac.chunk_overlap_chars, mac.max_length) == (1500, 200, 1024)
        assert (gpu.chunk_chars, gpu.chunk_overlap_chars, gpu.max_length) == (1500, 200, 1024)


# --------------------------------------------------------------------------- #
# loud failures (no server needed; real closed port / real missing weights)
# --------------------------------------------------------------------------- #

class TestFailsLoudly:
    def test_unreachable_server_is_an_execution_error_with_start_hint(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        rr = build_reranker({"backend": "llama_cpp", "endpoint": f"http://127.0.0.1:{port}", "timeout_seconds": 5})
        with pytest.raises(ModelComponentError) as err:
            rr.rerank("câu hỏi", ["đoạn a", "đoạn b"])
        assert err.value.kind == "backend_error" and "serve_mac.sh" in str(err.value)

    def test_remote_endpoint_is_refused(self):
        with pytest.raises(ModelComponentError) as err:
            build_reranker({"backend": "llama_cpp", "endpoint": "http://203.0.113.9:8082"})
        assert err.value.kind == "config_error"

    def test_unknown_key_is_rejected(self):
        with pytest.raises(ModelComponentError):
            build_reranker({"backend": "llama_cpp", "endpoint": ENDPOINT, "chunks": 3})

    def test_cuda_request_without_cuda_raises_instead_of_falling_back(self):
        import torch
        rr = CrossEncoderReranker(HF_MODEL, device="cuda", dtype="float16", local_files_only=True)
        if torch.cuda.is_available():     # on the GPU server the same config must really run on CUDA
            scores = rr.score("thời gian thử việc", ["Thời gian thử việc không quá 60 ngày", "Nghỉ phép năm"])
            assert rr.device.startswith("cuda") and scores[0] > scores[1]
            rr.unload()
        else:
            with pytest.raises(ModelComponentError) as err:
                rr.score("thời gian thử việc", ["a"])
            assert err.value.kind in ("missing_runtime", "load_error") and rr.load_error is not None


# --------------------------------------------------------------------------- #
# llama.cpp GGUF reranker on the real server
# --------------------------------------------------------------------------- #

class TestLlamaCppServer:
    @needs_server
    def test_ranks_relevant_passage_first_and_scores_are_finite(self):
        rr = LlamaCppReranker(ENDPOINT, model=served_alias())
        docs = ["Nghỉ hằng năm của người lao động được tính theo số tháng làm việc.",
                "Thời gian thử việc do hai bên thỏa thuận nhưng không quá 60 ngày đối với công việc có chức danh "
                "nghề nghiệp cần trình độ chuyên môn kỹ thuật từ cao đẳng trở lên.",
                "Người sử dụng lao động phải trả lương đúng hạn."]
        ranked = rr.rerank("Thời gian thử việc tối đa là bao lâu?", docs)
        assert ranked[0][0] == docs[1] and ranked[0][1] > ranked[1][1]
        assert rr.last_run["backend"] == "llama_cpp" and rr.last_run["n_scored"] == 3

    @needs_server
    def test_wrong_model_name_is_a_config_error(self):
        rr = LlamaCppReranker(ENDPOINT, model="not-the-served-model")
        with pytest.raises(ModelComponentError) as err:
            rr.score("q", ["d"])
        assert err.value.kind == "config_error"

    @needs_server
    def test_server_prompt_template_matches_the_hf_pair_encoding(self):
        """Regression for the GGUF converter gap (missing <s> and second </s>): token counts must equal HF's."""
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(HF_MODEL, local_files_only=True)
        rr = LlamaCppReranker(ENDPOINT, model=served_alias(), chunk_chars=None)
        for query, text in [("Thời gian thử việc tối đa là bao lâu?", "Thời gian thử việc không quá 60 ngày"),
                            ("Nghỉ phép năm", "Người lao động được nghỉ hằng năm 12 ngày làm việc.")]:
            rr.score(query, [text])
            assert rr.last_run["server_prompt_tokens"] == len(tok(query, text)["input_ids"])

    @needs_server
    def test_pair_longer_than_max_length_is_cut_client_side_to_the_cap(self):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(HF_MODEL, local_files_only=True)
        query = long_query()
        text = doc_text(LONG_RECORD)
        rr = LlamaCppReranker(ENDPOINT, model=served_alias(), max_length=512, chunk_chars=None)
        rr.score(query, [text])
        expected = len(tok(query, text, truncation="longest_first", max_length=512)["input_ids"])
        assert rr.last_run["n_truncated"] == 1 and expected == 512
        assert abs(rr.last_run["server_prompt_tokens"] - expected) <= 2    # detokenize/retokenize round trip

    @needs_server
    def test_best_chunk_finds_evidence_beyond_the_truncated_prefix(self):
        query, text = long_query(), doc_text(LONG_RECORD)
        prefix_only = LlamaCppReranker(ENDPOINT, model=served_alias(), chunk_chars=None)
        chunked = LlamaCppReranker(ENDPOINT, model=served_alias())
        base = prefix_only.score(query, [text])[0]
        best = chunked.score(query, [text])[0]
        assert chunked.last_run["n_chunks"] > 10 and chunked.last_run["best_chunk"][0] > 0
        assert best > base, "max over chunks must see the evidence that prefix truncation misses"

    @needs_server
    def test_gguf_scores_match_torch_fp32_on_real_benchmark_pairs(self, torch_reference):
        tasks = json.loads((ROOT / "evaluation/benchmarks/hcmut_v1/tasks.json").read_text(encoding="utf-8"))
        by_id = {r["doc_id"]: r for r in HCMUT}
        pairs = []
        for task in tasks[:3]:
            gold = by_id[task["ground_truth_article_ids"][0]]
            other = HCMUT[(sum(map(ord, task["task_id"])) + 7) % len(HCMUT)]   # deterministic unrelated record
            pairs.append((task["question"], [doc_text(gold), doc_text(other)]))
        gguf = LlamaCppReranker(ENDPOINT, model=served_alias(), chunk_chars=None)
        for query, texts in pairs:
            got = gguf.score(query, texts)
            want = torch_reference.score(query, texts)
            assert max(abs(a - b) for a, b in zip(got, want)) < 0.5, (got, want)
            assert (got[0] > got[1]) == (want[0] > want[1])


# --------------------------------------------------------------------------- #
# concurrency: one cached instance is shared by the benchmark's worker threads
# --------------------------------------------------------------------------- #
def test_shared_cross_encoder_is_thread_safe(torch_reference):
    """Concurrent reranks on one real instance neither collide in the tokenizer ("Already borrowed") nor
    mix up per-call telemetry when the caller reads `last_run` under the instance lock (as domain_tools does)."""
    from concurrent.futures import ThreadPoolExecutor

    tasks = json.loads((ROOT / "evaluation/benchmarks/hcmut_v1/tasks.json").read_text(encoding="utf-8"))
    queries = [t["question"] for t in tasks[:8]]
    candidates = [r for r in HCMUT if len(doc_text(r)) < 1200][:4]

    def call(query):
        with torch_reference.lock:
            ranked = torch_reference.rerank(query, candidates, top_k=len(candidates))
            run = dict(torch_reference.last_run)
        return [doc for doc, _ in ranked], run

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(call, queries))
    for ranked_docs, run in results:
        assert [r["doc_id"] for r in run["ranking"]] == [d["doc_id"] for d in ranked_docs]
        assert run["n_scored"] == len(candidates)
