"""Real-model tests for src/retrieval/rerankers.py and src/verifier/nli_backends.py.

No mocks, stubs, patched functions, canned outputs or stand-in components: every
model test runs the real cached Hugging Face weights on this machine (MPS when
available, else CPU).  If weights are missing a test FAILS with the download
command; nothing is skipped.

Memory discipline (16 GB Mac): one model at a time, batch size 1, class-scoped
fixtures that unload the model (del + gc + accelerator cache flush) before the
next class loads, and a guard that waits for another heavy python model process
(>2 GB RSS) to finish instead of running concurrently.

Required weights (download once):
    hf download AITeamVN/Vietnamese_Reranker
    hf download Qwen/Qwen3-Reranker-0.6B
    hf download MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
    hf download OmniJev/OneJev1.6-0.8B

The ``qev_http`` tests talk to the REAL official Qev servers on GPU server 82 through the
existing SSH tunnels (127.0.0.1:18001 = OmniJev/OneJev1.6-0.8B, 127.0.0.1:18004 =
OmniJev/OneJev1.6-4B).  They check /health first and FAIL (never skip) with a message naming
the port when the tunnel is down.  They never start, stop or reconfigure a server or a tunnel,
and send only a handful of sequential requests.

Paths NOT covered (no real server available, and these tests never start one):
    * llama.cpp /v1/rerank success path (needs a llama-server started with
      --reranking and a reranker GGUF); only its refusal/failure behaviour is tested.
    * LLM-prompt NLI success path (needs a non-thinking OpenAI-compatible chat
      server); only config/failure behaviour is tested.
    * qev_http "malformed response" / "missing option" branches: a real Qev server never
      produces them and a fake one is not allowed, so they are untested.
"""
import gc
import json
import math
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from src.model_runtime import (
    ModelComponentError,
    QevHttpClient,
    flush_accelerator_cache,
    release_system_one_runners,
)
from src.retrieval.rerankers import (
    CrossEncoderReranker,
    DecisionModelReranker,
    LlamaCppReranker,
    QevHttpReranker,
    Qwen3Reranker,
    build_reranker,
)
from src.verifier.nli_backends import (
    LABELS,
    CrossEncoderNLI,
    DecisionModelNLI,
    LLMPromptNLI,
    QevHttpNLI,
    build_nli_backend,
)

CORPUS_PATH = Path(__file__).resolve().parents[1] / "data" / "corpus" / "labor_code_2019_official.json"
AITEAM = "AITeamVN/Vietnamese_Reranker"
QWEN3 = "Qwen/Qwen3-Reranker-0.6B"
MDEBERTA = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
ONEJEV = "OmniJev/OneJev1.6-0.8B"

HEAVY_RSS_KB = 2 * 1024 * 1024
WAIT_FOR_NEIGHBOUR_SECONDS = 1800


# --------------------------------------------------------------------------- #
# helpers / fixtures
# --------------------------------------------------------------------------- #

def _require_cached(repo: str) -> None:
    """Fail (never skip) unless config.json and the safetensors weights are in the local HF cache."""
    from huggingface_hub import try_to_load_from_cache
    missing = [f for f in ("config.json", "model.safetensors")
               if not isinstance(try_to_load_from_cache(repo, f), str)]
    if missing:
        pytest.fail(f"{repo}: {missing} not in the local Hugging Face cache. "
                    f"Download with: hf download {repo}", pytrace=False)


def _heavy_python_neighbours():
    out = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True, text=True, check=True).stdout
    found = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or int(parts[0]) == os.getpid():
            continue
        if int(parts[1]) > HEAVY_RSS_KB and "python" in parts[2].lower():
            found.append((int(parts[0]), int(parts[1]), parts[2][:120]))
    return found


def _wait_for_quiet_machine():
    deadline = time.monotonic() + WAIT_FOR_NEIGHBOUR_SECONDS
    while True:
        neighbours = _heavy_python_neighbours()
        if not neighbours:
            return
        if time.monotonic() > deadline:
            pytest.fail(f"another heavy python process kept running for {WAIT_FOR_NEIGHBOUR_SECONDS}s: "
                        f"{neighbours}; refusing to load a model concurrently", pytrace=False)
        time.sleep(10)


def _free(component):
    component.unload()
    release_system_one_runners()
    gc.collect()
    flush_accelerator_cache()


@pytest.fixture(scope="module")
def corpus_by_id():
    docs = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return {d["article_id"]: d for d in docs}


QUERY = "Thời gian thử việc tối đa là bao nhiêu ngày?"
# Dieu_25 = "Thời gian thử việc"; the others are other real articles (one related by topic).
CANDIDATE_IDS = ["Dieu_113", "Dieu_1", "Dieu_25", "Dieu_35", "Dieu_26", "Dieu_24"]


@pytest.fixture()
def candidates(corpus_by_id):
    return [corpus_by_id[i] for i in CANDIDATE_IDS]


def _assert_probation_ranking(reranker, candidates):
    before = json.dumps(candidates, sort_keys=True)
    ranked = reranker.rerank(QUERY, candidates)
    assert json.dumps(candidates, sort_keys=True) == before, "rerank must not mutate its input"
    ids = [d["article_id"] for d, _ in ranked]
    scores = [s for _, s in ranked]
    assert sorted(ids) == sorted(CANDIDATE_IDS)
    assert scores == sorted(scores, reverse=True)
    assert ids[0] == "Dieu_25", f"probation-duration article should rank first, got order {ids} scores {scores}"
    assert ids.index("Dieu_25") < ids.index("Dieu_1") and ids.index("Dieu_25") < ids.index("Dieu_113")
    run = reranker.last_run
    assert run["n_scored"] == len(candidates) and run["wall_ms"] > 0 and run["ms_per_pair"] > 0
    assert reranker.device in ("mps", "cpu")
    top2 = reranker.rerank(QUERY, candidates, top_k=2)
    assert [d["article_id"] for d, _ in top2] == ids[:2]
    return ids


# --------------------------------------------------------------------------- #
# Pure configuration / failure behaviour (real code paths, no models)
# --------------------------------------------------------------------------- #

class TestConfigAndFailures:
    def test_factory_none_only_when_disabled(self):
        assert build_reranker(None) is None and build_reranker({"backend": "none"}) is None
        assert build_nli_backend({}) is None and build_nli_backend({"backend": "none"}) is None

    def test_factory_rejects_unknown_backend_and_keys(self):
        with pytest.raises(ModelComponentError) as e:
            build_reranker({"backend": "magic", "model": "x"})
        assert e.value.kind == "config_error"
        with pytest.raises(ModelComponentError):
            build_reranker({"backend": "cross_encoder", "model": "x", "top_k": 3})   # typo key
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "cross_encoder", "model": "x", "treshold": 0.5})

    def test_factory_builds_each_backend_lazily(self):
        assert isinstance(build_reranker({"backend": "cross_encoder", "model": "x/y"}), CrossEncoderReranker)
        assert isinstance(build_reranker({"backend": "qwen3", "model": "x/y"}), Qwen3Reranker)
        assert isinstance(build_reranker({"backend": "decision_model", "model": "x/y"}), DecisionModelReranker)
        assert isinstance(build_reranker({"backend": "llama_cpp", "endpoint": "http://127.0.0.1:1"}),
                          LlamaCppReranker)
        assert isinstance(build_nli_backend({"backend": "cross_encoder", "model": "x/y"}), CrossEncoderNLI)
        assert isinstance(build_nli_backend({"backend": "decision_model", "model": "x/y"}), DecisionModelNLI)
        assert isinstance(build_nli_backend({"backend": "llm", "endpoint": "http://localhost:1/v1", "model": "m"}),
                          LLMPromptNLI)
        qev = {"base_url": "http://127.0.0.1:18001", "model": "OmniJev/OneJev1.6-0.8B"}
        assert isinstance(build_reranker({"backend": "qev_http", **qev}), QevHttpReranker)
        assert isinstance(build_nli_backend({"backend": "qev_http", **qev}), QevHttpNLI)

    def test_defaults_are_ram_conservative(self):
        ce = build_reranker({"backend": "cross_encoder", "model": "x/y"})
        q3 = build_reranker({"backend": "qwen3", "model": "x/y"})
        dm = build_reranker({"backend": "decision_model", "model": "x/y"})
        assert (ce.max_length, ce.batch_size) == (1024, 1) and (q3.max_length, q3.batch_size) == (1024, 1)
        assert dm.runner.max_prompt_tokens == 1024
        assert build_nli_backend({"backend": "cross_encoder", "model": "x/y"}).batch_size == 1

    def test_remote_endpoints_are_refused(self):
        with pytest.raises(ModelComponentError) as e:
            build_reranker({"backend": "llama_cpp", "endpoint": "http://203.0.113.5:8080"})
        assert e.value.kind == "config_error"
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "llm", "endpoint": "https://api.example.com/v1", "model": "m"})

    def test_llama_cpp_connection_failure_raises(self):
        with socket.socket() as s:                       # a loopback port nobody listens on
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        rr = build_reranker({"backend": "llama_cpp", "endpoint": f"http://127.0.0.1:{port}", "timeout_seconds": 5})
        with pytest.raises(ModelComponentError) as e:
            rr.rerank("q", ["a", "b"])
        assert e.value.kind == "backend_error"

    def test_llm_nli_connection_failure_raises(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        nli = build_nli_backend({"backend": "llm", "endpoint": f"http://127.0.0.1:{port}/v1", "model": "m",
                                 "timeout_seconds": 5})
        with pytest.raises(ModelComponentError) as e:
            nli.classify("premise", "hypothesis")
        assert e.value.kind == "backend_error"

    def test_missing_weights_raise_and_error_is_remembered(self):
        rr = build_reranker({"backend": "cross_encoder", "model": "luatcheck-test/does-not-exist-xyz",
                             "local_files_only": True})
        with pytest.raises(ModelComponentError) as first:
            rr.rerank("q", ["a"])
        assert first.value.kind == "load_error" and "hf download" in str(first.value)
        assert rr.load_error is first.value
        with pytest.raises(ModelComponentError) as second:       # no silent retry, no substitute score
            rr.rerank("q", ["a"])
        assert second.value is first.value

    def test_nli_config_validation(self):
        with pytest.raises(ModelComponentError):                  # mDeBERTa is fp32-only
            build_nli_backend({"backend": "cross_encoder", "model": "x/y", "dtype": "float16"})
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "cross_encoder", "model": "x/y",
                               "label_map": {"0": "entailment", "1": "entailment", "2": "neutral"}})
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "cross_encoder", "model": "x/y", "threshold": 1.5})
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "cross_encoder", "model": "x/y", "aggregate": "vibes"})

    def test_empty_inputs_rejected(self):
        rr = build_reranker({"backend": "cross_encoder", "model": "x/y"})
        assert rr.rerank("q", []) == []
        with pytest.raises(ModelComponentError):
            rr.rerank("   ", ["a"])


# --------------------------------------------------------------------------- #
# Cross-encoder reranker (AITeamVN Vietnamese_Reranker)
# --------------------------------------------------------------------------- #

class TestCrossEncoderReranker:
    @pytest.fixture(scope="class")
    @classmethod
    def reranker(cls):
        _require_cached(AITEAM)
        _wait_for_quiet_machine()
        rr = build_reranker({"backend": "cross_encoder", "model": AITEAM, "local_files_only": True})
        yield rr
        _free(rr)

    def test_probation_article_ranks_first(self, reranker, candidates):
        _assert_probation_ranking(reranker, candidates)
        assert reranker.load_seconds is not None and reranker.dtype_name == "float32"
        assert reranker.last_run["n_truncated"] == 0

    def test_top_k_in_limits_scoring(self, reranker, candidates):
        reranker.top_k_in = 3
        try:
            ranked = reranker.rerank(QUERY, candidates)
        finally:
            reranker.top_k_in = None
        assert len(ranked) == 3 and reranker.last_run["n_dropped_unscored"] == 3
        assert {d["article_id"] for d, _ in ranked} == set(CANDIDATE_IDS[:3])


# --------------------------------------------------------------------------- #
# Qwen3-Reranker (yes/no scoring)
# --------------------------------------------------------------------------- #

class TestQwen3Reranker:
    @pytest.fixture(scope="class")
    @classmethod
    def reranker(cls):
        _require_cached(QWEN3)
        _wait_for_quiet_machine()
        rr = build_reranker({"backend": "qwen3", "model": QWEN3, "local_files_only": True})
        yield rr
        _free(rr)

    def test_probation_article_ranks_first_and_scores_are_probabilities(self, reranker, candidates):
        _assert_probation_ranking(reranker, candidates)
        scores = reranker.score(QUERY, candidates)
        assert all(0.0 <= s <= 1.0 for s in scores)


# --------------------------------------------------------------------------- #
# Decision model (OneJev / System One): reranker and NLI share one loaded runner
# --------------------------------------------------------------------------- #

class TestDecisionModel:
    @pytest.fixture(scope="class")
    @classmethod
    def components(cls):
        _require_cached(ONEJEV)
        _wait_for_quiet_machine()
        cfg = {"model": ONEJEV, "local_files_only": True}
        rr = build_reranker({"backend": "decision_model", **cfg})
        nli = build_nli_backend({"backend": "decision_model", **cfg})
        yield rr, nli
        _free(rr)

    def test_rerank_probation(self, components, candidates):
        rr, _ = components
        _assert_probation_ranking(rr, candidates)
        assert all(0.0 <= s <= 1.0 for s in rr.score(QUERY, candidates[:2]))
        assert rr.runner.last_details["prompt_version"] == "qev-labels-v2"

    def test_nli_entailed_and_contradicted(self, components, corpus_by_id):
        _, nli = components
        premise = corpus_by_id["Dieu_26"]["content"]
        entailed = "Tiền lương thử việc ít nhất phải bằng 85% mức lương của công việc đó."
        wrong_number = "Tiền lương thử việc ít nhất phải bằng 95% mức lương của công việc đó."
        opposite = "Tiền lương thử việc có thể thấp hơn 85% mức lương của công việc đó."
        unrelated = "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm 12 ngày làm việc."
        assert nli.verify(premise, entailed).label == "entailment"
        assert nli.verify(premise, wrong_number).label == "contradiction"
        assert nli.verify(premise, opposite).label == "contradiction"
        assert nli.verify(premise, unrelated).label == "neutral"
        probs = nli.classify(premise, entailed)
        assert set(probs) == set(LABELS) and math.isclose(sum(probs.values()), 1.0, abs_tol=1e-3)
        assert nli.last_details["probability_source"] == "softmax_over_option_letter_logits"
        assert nli.device in ("mps", "cpu")

    def test_long_prompt_is_refused_not_truncated(self, components, corpus_by_id):
        rr, _ = components
        long_doc = " ".join(corpus_by_id[i]["content"] for i in ("Dieu_113", "Dieu_35", "Dieu_25")) * 3
        with pytest.raises(ModelComponentError) as e:
            rr.rerank(QUERY, [long_doc])
        assert e.value.kind == "input_too_long"


# --------------------------------------------------------------------------- #
# Cross-encoder NLI (mDeBERTa) incl. >512-token window aggregation
# --------------------------------------------------------------------------- #

class TestCrossEncoderNLI:
    @pytest.fixture(scope="class")
    @classmethod
    def nli(cls):
        _require_cached(MDEBERTA)
        _wait_for_quiet_machine()
        n = build_nli_backend({"backend": "cross_encoder", "model": MDEBERTA, "local_files_only": True,
                               "threshold": 0.7})
        yield n
        _free(n)

    ENTAILED = "Tiền lương thử việc ít nhất phải bằng 85% mức lương của công việc đó."
    WRONG_NUMBER = "Tiền lương thử việc ít nhất phải bằng 95% mức lương của công việc đó."

    def test_entailed_paraphrase_vs_changed_number(self, nli, corpus_by_id):
        premise = corpus_by_id["Dieu_26"]["content"]
        v = nli.verify(premise, self.ENTAILED)
        assert v.label == "entailment" and v.entailed and v.probabilities["entailment"] > 0.9
        c = nli.verify(premise, self.WRONG_NUMBER)
        assert c.label == "contradiction" and not c.entailed and c.probabilities["contradiction"] > 0.9
        n = nli.verify(premise, "Người lao động được nghỉ hằng năm 12 ngày làm việc.")
        assert n.label == "neutral" and not n.entailed
        assert nli.dtype_name == "float32" and nli.device in ("mps", "cpu")
        assert nli.label_map == {0: "entailment", 1: "neutral", 2: "contradiction"}
        assert nli.last_details["n_windows"] == 1 and nli.last_details["aggregate"] == "single_window"

    def test_threshold_gates_entailment(self, nli, corpus_by_id):
        premise = corpus_by_id["Dieu_26"]["content"]
        nli.threshold = 0.9999999
        try:
            assert not nli.verify(premise, self.ENTAILED).entailed
        finally:
            nli.threshold = 0.7

    @pytest.fixture(scope="class")
    @classmethod
    def long_premise(cls, corpus_by_id):
        # Real articles concatenated; the salary clause (Dieu_26) sits in the final windows.
        order = ["Dieu_113", "Dieu_35", "Dieu_24", "Dieu_25", "Dieu_26", "Dieu_1"]
        return "\n\n".join(corpus_by_id[i]["content"] for i in order)

    def test_windowing_follows_documented_rule(self, nli, long_premise):
        probs = nli.classify(long_premise, self.ENTAILED)
        d = nli.last_details
        assert d["premise_tokens"] > 512 and d["n_windows"] >= 2
        room, overlap = d["window_room_tokens"], d["window_overlap"]
        assert overlap == 64 and room == 512 - d["hypothesis_tokens"] - 3
        expected = 1 + math.ceil((d["premise_tokens"] - room) / (room - overlap))
        assert d["n_windows"] == expected, "windows must advance by room - overlap premise tokens"
        assert len(d["window_probabilities"]) == d["n_windows"]
        # max_evidence: the selected window maximises 1 - P(neutral) (earliest on ties)
        w = d["window_probabilities"]
        best = max(range(len(w)), key=lambda i: (1.0 - w[i]["neutral"], -i))
        assert d["selected_window"] == best and d["aggregate"] == "max_evidence"
        assert probs == {k: w[best][k] for k in LABELS}
        assert probs["entailment"] > 0.7

    def test_windowed_contradiction_detected(self, nli, long_premise):
        probs = nli.classify(long_premise, self.WRONG_NUMBER)
        assert max(probs, key=probs.get) == "contradiction" and probs["contradiction"] > 0.7

    def test_mean_and_max_entailment_rules(self, nli, long_premise):
        saved = nli.aggregate
        try:
            nli.aggregate = "mean"
            probs = nli.classify(long_premise, self.ENTAILED)
            w = nli.last_details["window_probabilities"]
            for k in LABELS:
                assert math.isclose(probs[k], sum(x[k] for x in w) / len(w), abs_tol=1e-9)
            assert nli.last_details["selected_window"] is None
            nli.aggregate = "max_entailment"
            probs = nli.classify(long_premise, self.ENTAILED)
            w = nli.last_details["window_probabilities"]
            assert nli.last_details["selected_window"] == max(range(len(w)), key=lambda i: (w[i]["entailment"], -i))
        finally:
            nli.aggregate = saved

    def test_oversized_inputs_raise_instead_of_truncating(self, nli, long_premise):
        saved = nli.max_windows
        nli.max_windows = 2
        try:
            with pytest.raises(ModelComponentError) as e:
                nli.classify(long_premise, self.ENTAILED)
            assert e.value.kind == "input_too_long"
        finally:
            nli.max_windows = saved
        with pytest.raises(ModelComponentError) as e:
            nli.classify("Một tiền đề ngắn.", "từ " * 600)
        assert e.value.kind == "input_too_long"


# --------------------------------------------------------------------------- #
# Official Qev HTTP servers (OneJev 1.6, remote GPU through SSH tunnels)
# --------------------------------------------------------------------------- #

QEV_SERVERS = {18001: "OmniJev/OneJev1.6-0.8B", 18004: "OmniJev/OneJev1.6-4B"}


def _qev_config(port: int) -> dict:
    return {"base_url": f"http://127.0.0.1:{port}", "model": QEV_SERVERS[port], "timeout_seconds": 120}


def _require_qev(port: int) -> None:
    """Fail (never skip) with a message naming the port unless /health answers ok for the right model."""
    import requests
    url = f"http://127.0.0.1:{port}/health"
    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as exc:
        pytest.fail(f"Qev server for {QEV_SERVERS[port]} is not reachable on 127.0.0.1:{port} ({url}): "
                    f"{type(exc).__name__}: {exc}. The SSH tunnel to GPU server 82 for port {port} is probably "
                    "down; this test must not be skipped or faked.", pytrace=False)
    if resp.status_code != 200 or resp.json().get("status") != "ok":
        pytest.fail(f"Qev /health on 127.0.0.1:{port} returned HTTP {resp.status_code}: {resp.text[:200]!r}",
                    pytrace=False)


class TestQevHttpConfig:
    """Configuration behaviour of the qev_http backends (no network)."""

    def test_non_loopback_refused_unless_allow_remote(self):
        cfg = {"base_url": "http://203.0.113.5:8000", "model": "OmniJev/OneJev1.6-0.8B"}
        for builder, backend in ((build_reranker, "qev_http"), (build_nli_backend, "qev_http")):
            with pytest.raises(ModelComponentError) as e:
                builder({"backend": backend, **cfg})
            assert e.value.kind == "config_error" and "allow_remote" in str(e.value)
        rr = build_reranker({"backend": "qev_http", **cfg, "allow_remote": True})      # construction only
        assert rr.client.allow_remote is True and rr.info()["allow_remote"] is True
        assert isinstance(build_nli_backend({"backend": "qev_http", **cfg, "allow_remote": True}), QevHttpNLI)
        for loopback in ("http://localhost:18001", "http://127.0.0.1:18001/", "http://[::1]:18001"):
            QevHttpClient(loopback, "m")

    def test_base_url_and_model_are_mandatory_and_typed(self):
        for cfg in ({"model": "m"}, {"base_url": "http://127.0.0.1:1"}, {"base_url": "", "model": "m"},
                    {"base_url": "ftp://127.0.0.1:1", "model": "m"},
                    {"base_url": "http://127.0.0.1:1", "model": "m", "allow_remote": "yes"},
                    {"base_url": "http://127.0.0.1:1", "model": "m", "timeout_seconds": 0}):
            with pytest.raises(ModelComponentError) as e:
                build_reranker({"backend": "qev_http", **cfg})
            assert e.value.kind == "config_error"

    def test_unknown_keys_and_bad_options_rejected(self):
        base = {"base_url": "http://127.0.0.1:1", "model": "m"}
        with pytest.raises(ModelComponentError):
            build_reranker({"backend": "qev_http", **base, "endpoint": "http://127.0.0.1:1"})
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "qev_http", **base, "treshold": 0.5})
        with pytest.raises(ModelComponentError):
            build_nli_backend({"backend": "qev_http", **base, "options": {"entailment": "a", "neutral": "b"}})

    def test_connection_failure_raises(self):
        with socket.socket() as s:                       # a loopback port nobody listens on
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        cfg = {"base_url": f"http://127.0.0.1:{port}", "model": "m", "timeout_seconds": 5}
        with pytest.raises(ModelComponentError) as e:
            build_reranker({"backend": "qev_http", **cfg}).rerank("q", ["a", "b"])
        assert e.value.kind == "backend_error"
        with pytest.raises(ModelComponentError) as e:
            build_nli_backend({"backend": "qev_http", **cfg}).classify("premise", "hypothesis")
        assert e.value.kind == "backend_error"


@pytest.fixture(scope="class", params=sorted(QEV_SERVERS), ids=[QEV_SERVERS[p].rsplit("-", 1)[1] for p in sorted(QEV_SERVERS)])
def qev_port(request):
    _require_qev(request.param)
    return request.param


class TestQevHttpServers:
    """Real requests to the official Qev servers (0.8B on 18001, 4B on 18004)."""

    def test_health_identity_and_wrong_model_name(self, qev_port):
        client = QevHttpClient(**_qev_config(qev_port))
        health = client.health()
        assert health["status"] == "ok" and health["model"] == QEV_SERVERS[qev_port]
        assert health["prompt_version"] == "qev-labels-v2"
        other = next(m for p, m in QEV_SERVERS.items() if p != qev_port)
        wrong = QevHttpClient(**{**_qev_config(qev_port), "model": other})     # the server answers any alias
        with pytest.raises(ModelComponentError) as e:
            wrong.decide_yes_no({"a": "b"}, "The state is a dictionary")
        assert e.value.kind == "config_error" and str(qev_port) in str(e.value)

    def test_rerank_probation(self, qev_port, candidates):
        rr = build_reranker({"backend": "qev_http", **_qev_config(qev_port)})
        before = json.dumps(candidates, sort_keys=True)
        ranked = rr.rerank(QUERY, candidates)
        assert json.dumps(candidates, sort_keys=True) == before, "rerank must not mutate its input"
        ids = [d["article_id"] for d, _ in ranked]
        scores = [s for _, s in ranked]
        assert sorted(ids) == sorted(CANDIDATE_IDS) and scores == sorted(scores, reverse=True)
        assert all(0.0 <= s <= 1.0 for s in scores)
        assert ids[0] == "Dieu_25", f"probation-duration article should rank first, got {ids} {scores}"
        run = rr.last_run
        assert run["backend"] == "qev_http" and run["n_scored"] == len(candidates)
        assert run["wall_ms"] > 0 and run["remote_inference"] is True and run["device"] == "server"
        assert [d["article_id"] for d, _ in rr.rerank(QUERY, candidates, top_k=2)] == ids[:2]
        assert rr.client.last_details["prompt_version"] == "qev-labels-v2"
        assert rr.client.last_details["input_tokens"] > 0

    def test_nli_entailed_contradicted_neutral(self, qev_port, corpus_by_id):
        nli = build_nli_backend({"backend": "qev_http", **_qev_config(qev_port)})
        premise = corpus_by_id["Dieu_26"]["content"]
        entailed = "Tiền lương thử việc ít nhất phải bằng 85% mức lương của công việc đó."
        wrong_number = "Tiền lương thử việc ít nhất phải bằng 95% mức lương của công việc đó."
        opposite = "Tiền lương thử việc có thể thấp hơn 85% mức lương của công việc đó."
        unrelated = "Người lao động làm việc đủ 12 tháng được nghỉ hằng năm 12 ngày làm việc."
        assert nli.verify(premise, entailed).label == "entailment"
        assert nli.verify(premise, wrong_number).label == "contradiction"
        assert nli.verify(premise, opposite).label == "contradiction"
        assert nli.verify(premise, unrelated).label == "neutral"
        probs = nli.classify(premise, entailed)
        assert tuple(probs) == LABELS and math.isclose(sum(probs.values()), 1.0, abs_tol=1e-3)
        d = nli.last_details
        assert d["device"] == "server" and d["probability_source"] == "qev_server_option_probabilities"
        assert d["server"]["remote_inference"] is True and d["server"]["server_model"] == QEV_SERVERS[qev_port]
        assert nli.verify(premise, entailed).entailed and not nli.verify(premise, unrelated).entailed

    def test_http_error_and_timeout_raise(self, qev_port):
        client = QevHttpClient(**_qev_config(qev_port))
        with pytest.raises(ModelComponentError) as e:      # the real server rejects an unknown question type (HTTP 422)
            client.system_one({"a": "b"}, {"q": {"type": "bogus", "instructions": "x"}})
        assert e.value.kind == "backend_error" and "HTTP 422" in str(e.value)
        impatient = QevHttpClient(**{**_qev_config(qev_port), "timeout_seconds": 0.001})
        with pytest.raises(ModelComponentError) as e:
            impatient.decide_yes_no({"a": "b"}, "The state is a dictionary")
        assert e.value.kind == "backend_error"

    def test_choice_needs_two_options(self, qev_port):
        client = QevHttpClient(**_qev_config(qev_port))
        with pytest.raises(ModelComponentError) as e:
            client.decide_choice({"a": "b"}, "Pick", {"only": "one"})
        assert e.value.kind == "config_error"
