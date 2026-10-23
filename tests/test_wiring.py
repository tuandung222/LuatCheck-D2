"""Wiring of the model components into the application (config, search tool, ModelManager, verification, agent loop).

Real implementations only (AGENTS.md): real corpora, the real AITeamVN reranker and mDeBERTa NLI weights from the local
Hugging Face cache, the real llama-server (Bonsai) on 127.0.0.1:8081 for the end-to-end run. No mocks, stubs,
monkeypatching or injected stand-ins. Temporary directories only. A missing model/server FAILS (naming what is missing).
At most one heavy model is resident at a time; every test that loads one unloads it in a fixture teardown.

These tests make no claim about answer correctness: they check that the components are wired, selected by config,
recorded in the ledger and that failures surface as errors.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
import yaml

from src.agent.loop import LuatCheckAgent
from src.config.app_config import AppConfig, NLIConfig, RerankerConfig, load_config
from src.model_manager import ModelBudgetError, ModelManager, available_memory_gb, estimate_weights_gb
from src.model_runtime import ModelComponentError
from src.retrieval.hybrid_domain import HybridDomainRetriever
from src.tools.domain_tools import DomainKnowledgeRegistry

ROOT = Path(__file__).resolve().parents[1]
CORPUS = "data/corpus/labor_code_2019_official.json"
RERANKER_ID = "AITeamVN/Vietnamese_Reranker"
NLI_ID = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
LLAMA_URL = "http://127.0.0.1:8081"
HEAVY_RSS_KB = 2 * 1024 * 1024
PROBATION_QUERY = "thời gian thử việc tối đa là bao lâu"

# sha256 of json.dumps(result, ensure_ascii=False, sort_keys=True) of the search tool for the frozen D2 configuration,
# computed on the working tree before the wiring change (first-stage order, snippets, field layout).
D2_TOOL_DIGESTS = [
    (PROBATION_QUERY, 3, "68b6224ff98a5d84dee451c25f6da4d20d6a4b39a025419e04fce8204acc2355",
     ["Dieu_27", "Dieu_155", "Dieu_26"]),
    ("người lao động đơn phương chấm dứt hợp đồng lao động phải báo trước bao nhiêu ngày", 5,
     "f7888c10752da50a766aff88152cd07f7972c9b7343f1b846188c7f3ef133e61",
     ["Dieu_38", "Dieu_40", "Dieu_35", "Dieu_39", "Dieu_36"]),
    ("tiền lương làm thêm giờ vào ngày nghỉ lễ", 3,
     "5f031046bb42155f3c08c0e0ccde20f75fc565dd1e67583fe056510396256724", ["Dieu_98", "Dieu_95", "Dieu_111"]),
]


# --------------------------------------------------------------------------- #
# helpers / fixtures
# --------------------------------------------------------------------------- #

def _require_cached(repo: str) -> None:
    from huggingface_hub import try_to_load_from_cache
    missing = [f for f in ("config.json", "model.safetensors") if not isinstance(try_to_load_from_cache(repo, f), str)]
    if missing:
        pytest.fail(f"{repo}: {missing} not in the local Hugging Face cache. Download with: hf download {repo}",
                    pytrace=False)


def _wait_for_quiet_machine(limit_s: float = 900.0) -> None:
    """Wait while another python process holds more than 2 GB (never load a model next to a heavy neighbour)."""
    deadline = time.monotonic() + limit_s
    while True:
        out = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True, text=True, check=True).stdout
        heavy = [(int(p[0]), int(p[1])) for p in (line.split(None, 2) for line in out.splitlines())
                 if len(p) == 3 and int(p[0]) != os.getpid() and int(p[1]) > HEAVY_RSS_KB and "python" in p[2].lower()]
        if not heavy:
            return
        if time.monotonic() > deadline:
            pytest.fail(f"another heavy python process kept running for {limit_s}s: {heavy}", pytrace=False)
        time.sleep(10)


def _reranker_cfg(**over) -> RerankerConfig:
    base = dict(enabled=True, backend="cross_encoder", model=RERANKER_ID, top_k_in=10, top_k_out=3, dtype="float16",
                local_files_only=True)
    base.update(over)
    return RerankerConfig(**base)


def _nli_cfg(**over) -> NLIConfig:
    base = dict(enabled=True, backend="cross_encoder", model=NLI_ID, threshold=0.9, local_files_only=True)
    base.update(over)
    return NLIConfig(**base)


def _digest(result) -> str:
    return hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _ids(result):
    return [a["article_id"] for a in result["articles"]]


def _isolated(cfg: AppConfig, tmp_path: Path) -> AppConfig:
    """Same config with temporary sqlite/audit/outbox files (the agent would otherwise write under data/)."""
    cfg = cfg.model_copy(deep=True)
    cfg.memory.sqlite_path = str(tmp_path / "memory.db")
    cfg.security.audit_log_path = str(tmp_path / "audit.jsonl")
    cfg.security.outbox_path = str(tmp_path / "outbox.jsonl")
    return cfg


@pytest.fixture(scope="module")
def plain_registry():
    return DomainKnowledgeRegistry(corpus_path=CORPUS, retrieval_mode="tfidf", rrf_k=60)


@pytest.fixture(scope="module")
def reranker_manager():
    """One manager and one resident reranker for the module's rerank tests; unloaded afterwards."""
    _require_cached(RERANKER_ID)
    _wait_for_quiet_machine()
    manager = ModelManager(idle_unload_seconds=600, max_resident_gb=4.0, min_free_gb=0.5)
    yield manager
    manager.unload_all()


@pytest.fixture(scope="module")
def reranked_registry(reranker_manager):
    handle = reranker_manager.reranker(_reranker_cfg())
    return DomainKnowledgeRegistry(corpus_path=CORPUS, retrieval_mode="tfidf", rrf_k=60, reranker=handle,
                                   rerank_top_k_in=10, rerank_top_k_out=3)


# --------------------------------------------------------------------------- #
# config parsing and defaults
# --------------------------------------------------------------------------- #

class TestConfig:
    def test_defaults_keep_current_behaviour(self):
        cfg = AppConfig()
        r = cfg.retrieval.reranker
        assert (r.enabled, r.backend, r.model, r.top_k_in, r.top_k_out, r.device, r.max_length, r.dtype, r.base_url,
                r.allow_remote) == (False, "cross_encoder", None, 20, 5, "auto", 1024, None, None, False)
        n = cfg.verifier.nli
        assert (n.enabled, n.threshold, n.action) == (False, 0.9, "flag")
        assert cfg.retrieval.mode == "bm25_tfidf" and cfg.retrieval.index.path is None
        assert (cfg.models.idle_unload_seconds, cfg.models.max_resident_gb) == (600, 4.0)
        assert cfg.domain.profile == "labour_vi_2019"

    def test_yaml_round_trip_and_contract_keys(self, tmp_path):
        path = tmp_path / "c.yaml"
        path.write_text(yaml.safe_dump({
            "retrieval": {"mode": "bm25_tfidf", "reranker": {
                "enabled": True, "backend": "qwen3", "model": "x/y", "top_k_in": 8, "top_k_out": 4, "device": "cpu",
                "max_length": 512, "dtype": "bfloat16", "base_url": None, "allow_remote": False}},
            "verifier": {"nli": {"enabled": True, "backend": "cross_encoder", "model": NLI_ID, "threshold": 0.8,
                                 "action": "repair", "max_length": 256}},
            "models": {"idle_unload_seconds": 5, "max_resident_gb": 3.5}}))
        cfg = load_config(str(path))
        assert cfg.retrieval.reranker.backend == "qwen3" and cfg.retrieval.reranker.max_length == 512
        assert cfg.verifier.nli.action == "repair" and cfg.verifier.nli.component_config()["max_length"] == 256
        assert cfg.models.max_resident_gb == 3.5

    @pytest.mark.parametrize("bad", [
        {"enabled": True},                                                    # model missing
        {"enabled": True, "model": "m", "top_k_in": 3, "top_k_out": 4},       # out > in
        {"enabled": True, "backend": "bm25", "model": "m"},                   # unknown backend
        {"enabled": True, "model": "m", "surprise": 1},                       # unknown key
        {"enabled": True, "backend": "qev_http", "model": "m"},               # base_url missing
        {"enabled": True, "backend": "llamacpp_http", "base_url": "http://127.0.0.1:8082", "allow_remote": True},
    ])
    def test_bad_reranker_config_is_rejected(self, bad):
        with pytest.raises(ValueError):
            RerankerConfig(**bad)

    def test_bad_nli_and_retrieval_mode_are_rejected(self):
        with pytest.raises(ValueError):
            NLIConfig(enabled=True)                       # model missing
        with pytest.raises(ValueError):
            NLIConfig(action="delete")
        with pytest.raises(ValueError):
            AppConfig(retrieval={"mode": "faiss"})        # unsupported value: clear validation error
        with pytest.raises(ValueError, match="requires retrieval.index.path"):
            AppConfig(retrieval={"mode": "hybrid_index"})
        with pytest.raises(ValueError):
            AppConfig(models={"max_resident_gb": 0})

    def test_http_backends_map_to_component_config_and_build_without_network(self):
        manager = ModelManager()
        qev = manager.reranker(RerankerConfig(enabled=True, backend="qev_http", base_url="http://127.0.0.1:18001",
                                              model="OmniJev/OneJev1.6-0.8B"))
        llama = manager.reranker(RerankerConfig(enabled=True, backend="llamacpp_http", base_url="http://127.0.0.1:8082"))
        assert (qev.component.backend, llama.component.backend) == ("qev_http", "llama_cpp")
        assert qev.remote and llama.remote and not qev.resident         # nothing local is loaded or budgeted
        with pytest.raises(ModelComponentError) as err:                 # loopback rule of the component is kept
            manager.reranker(RerankerConfig(enabled=True, backend="qev_http", base_url="http://example.com:1",
                                            model="m"))
        assert err.value.kind == "config_error"

    def test_app_profiles(self):
        lite = load_config(str(ROOT / "config/profiles/lite.yaml"))
        assert lite.model_dump() == load_config(str(ROOT / "config/config.yaml")).model_dump()
        assert not lite.retrieval.reranker.enabled and not lite.verifier.nli.enabled
        full = load_config(str(ROOT / "config/profiles/local-full.yaml"))
        assert full.retrieval.reranker.enabled and full.retrieval.reranker.model == RERANKER_ID
        assert full.verifier.nli.enabled and full.verifier.nli.model == NLI_ID and full.verifier.nli.action == "flag"
        remote = load_config(str(ROOT / "config/profiles/remote.yaml"))
        assert remote.retrieval.reranker.model == RERANKER_ID
        assert (remote.verifier.nli.backend, remote.verifier.nli.base_url, remote.verifier.nli.model) == (
            "qev_http", "http://127.0.0.1:18004", "OmniJev/OneJev1.6-4B")
        for profile in (lite, full, remote):                 # everything else is the lite default
            assert profile.model.name == lite.model.name and profile.domain.profile == "labour_vi_2019"
            assert profile.retrieval.corpus_path == lite.retrieval.corpus_path and profile.retrieval.mode == "bm25_tfidf"


# --------------------------------------------------------------------------- #
# frozen D2 configuration: unchanged behaviour
# --------------------------------------------------------------------------- #

class TestFrozenD2:
    def test_components_disabled_and_nothing_built(self, tmp_path):
        raw = yaml.safe_load((ROOT / "config/d2_native.yaml").read_text())
        assert "reranker" not in raw["retrieval"] and "nli" not in raw["verifier"] and "models" not in raw
        cfg = load_config(str(ROOT / "config/d2_native.yaml"))
        assert not cfg.retrieval.reranker.enabled and not cfg.verifier.nli.enabled and cfg.retrieval.mode == "bm25_tfidf"
        agent = LuatCheckAgent(config=_isolated(cfg, tmp_path))
        assert agent.model_manager is None and agent.reranker_handle is None
        assert agent.verification_pipeline.nli_step is None
        assert agent.tool_registry.reranker is None

    @pytest.mark.parametrize("query,top_k,digest,ids", D2_TOOL_DIGESTS)
    def test_tool_output_identical_to_before_the_wiring(self, tmp_path, query, top_k, digest, ids):
        agent = LuatCheckAgent(config=_isolated(load_config(str(ROOT / "config/d2_native.yaml")), tmp_path))
        result = agent._search(query, top_k)
        assert _ids(result) == ids and _digest(result) == digest
        result2, metadata = agent._search_with_metadata(query, top_k)
        assert result2 == result and metadata is None


# --------------------------------------------------------------------------- #
# search tool with a real reranker
# --------------------------------------------------------------------------- #

class TestRerankedSearch:
    def test_reranked_results_and_ledger_metadata(self, reranked_registry, plain_registry):
        result, meta = reranked_registry.search_with_metadata(PROBATION_QUERY, top_k=5)
        first_stage = _ids(plain_registry.search_knowledge(PROBATION_QUERY, top_k=10))
        rerank = meta["rerank"]
        assert rerank["first_stage_ids"] == first_stage                          # candidates = first-stage top_k_in
        assert rerank["top_k_in"] == 10 and rerank["top_k_out"] == 3 and rerank["n_candidates"] == 10
        assert len(_ids(result)) == 3 and set(_ids(result)) <= set(first_stage)
        assert _ids(result) == rerank["reranked_ids"]
        assert _ids(result)[0] == "Dieu_25"                                      # the probation article, ranked by the model
        ranking = rerank["ranking"]
        scores = [r["score"] for r in ranking]
        assert len(ranking) == 10 == rerank["n_scored"]                           # every candidate scored and recorded
        assert scores == sorted(scores, reverse=True)
        assert [r["doc_id"] for r in ranking[:3]] == _ids(result)
        assert rerank["backend"] == "cross_encoder" and rerank["model"] == RERANKER_ID
        assert rerank["device"] in ("mps", "cpu") and rerank["wall_ms"] > 0 and rerank["ms_per_pair"] > 0
        assert rerank["first_stage_ms"] >= 0 and "not answer correctness" in rerank["score_note"]
        json.dumps(meta)                                                          # ledger-serialisable
        # scores and timing are for the ledger only: the model-visible result carries none of them
        visible = json.dumps(result, ensure_ascii=False)
        assert "score" not in visible and "ms_per_pair" not in visible and "wall_ms" not in visible
        # the first stage of the plain tool differs in order, and snippets are computed exactly as without a reranker
        assert _ids(plain_registry.search_knowledge(PROBATION_QUERY, top_k=3)) != _ids(result)
        plain_by_id = {a["article_id"]: a for a in plain_registry.search_knowledge(PROBATION_QUERY, top_k=10)["articles"]}
        for article in result["articles"]:
            assert article == plain_by_id[article["article_id"]]

    def test_requested_top_k_caps_the_output(self, reranked_registry):
        result, meta = reranked_registry.search_with_metadata(PROBATION_QUERY, top_k=2)
        assert len(result["articles"]) == 2 and meta["rerank"]["requested_top_k"] == 2
        assert len(meta["rerank"]["ranking"]) == 10       # still all 10 scored

    def test_search_knowledge_returns_only_the_model_visible_result(self, reranked_registry):
        result = reranked_registry.search_knowledge(PROBATION_QUERY, top_k=3)
        assert _ids(result)[0] == "Dieu_25" and set(result) == {"status", "law_name", "count", "articles"}

    def test_missing_weights_raise_and_nothing_is_returned(self):
        manager = ModelManager(min_free_gb=0.0)
        handle = manager.reranker(RerankerConfig(enabled=True, model="no-such-owner/no-such-reranker",
                                                 local_files_only=True, top_k_in=5, top_k_out=2))
        registry = DomainKnowledgeRegistry(corpus_path=CORPUS, retrieval_mode="tfidf", reranker=handle,
                                           rerank_top_k_in=5, rerank_top_k_out=2)
        for _ in range(2):                                            # the failure is remembered, not retried silently
            with pytest.raises(ModelComponentError) as err:
                registry.search_with_metadata(PROBATION_QUERY, 3)
            assert err.value.kind == "load_error" and "no-such-reranker" in str(err.value)
        assert not handle.resident

    def test_dead_http_reranker_raises(self):
        manager = ModelManager()
        handle = manager.reranker(RerankerConfig(enabled=True, backend="qev_http", base_url="http://127.0.0.1:9",
                                                 model="OmniJev/OneJev1.6-0.8B", timeout_seconds=3))
        registry = DomainKnowledgeRegistry(corpus_path=CORPUS, retrieval_mode="tfidf", reranker=handle,
                                           rerank_top_k_in=5, rerank_top_k_out=2)
        with pytest.raises(ModelComponentError) as err:
            registry.search_with_metadata(PROBATION_QUERY, 3)
        assert err.value.kind in ("backend_error", "config_error")

    def test_mixed_sources_name_each_article(self):
        """Two real corpora in one knowledge base: every article carries its own law_name instead of one shared name."""
        labour = json.loads((ROOT / CORPUS).read_text(encoding="utf-8"))[:60]
        hcmut = json.loads((ROOT / "data/corpus/hcmut_academic_v1.json").read_text(encoding="utf-8"))[:60]
        registry = DomainKnowledgeRegistry(retriever=HybridDomainRetriever(corpus=labour + hcmut))
        result = registry.search_knowledge("thời gian", top_k=5)
        names = {a.get("law_name") for a in result["articles"]}
        assert len(names) > 1 and None not in names and "law_name" not in result
        single = registry.search_knowledge("hợp đồng", top_k=5)
        assert "law_name" in single and all("law_name" not in a for a in single["articles"])


# --------------------------------------------------------------------------- #
# ModelManager with the real models
# --------------------------------------------------------------------------- #

class TestModelManager:
    def test_estimate_is_the_cached_weight_size(self):
        gb16, source = estimate_weights_gb(RERANKER_ID, "float16", 9.0)
        gb32, _ = estimate_weights_gb(RERANKER_ID, "float32", 9.0)
        assert source == "safetensors_header" and 0.9 < gb16 < 1.3 and abs(gb32 - 2 * gb16) < 1e-6
        assert estimate_weights_gb("no-such-owner/no-such-model", "float32", 2.5) == (2.5, "default_estimate")
        assert available_memory_gb() > 0

    def test_one_shared_lazy_handle_per_component(self):
        manager = ModelManager()
        a, b = manager.reranker(_reranker_cfg()), manager.reranker(_reranker_cfg(top_k_in=12, top_k_out=2))
        assert a is b and a.component is b.component                   # top_k does not select a different model
        assert manager.reranker(_reranker_cfg(device="cpu")) is not a   # device is part of the identity
        assert manager.reranker(_reranker_cfg(dtype="float32")) is not a
        assert not a.resident and a.loads == 0 and not a.component.loaded     # lazy: nothing loaded by building a handle
        assert a.component.top_k_in is None and a.component.top_k_out is None  # limits are applied by the search tool
        assert ModelManager.shared() is ModelManager.shared(AppConfig().models)

    def test_reuse_idle_unload_and_reload(self):
        _require_cached(RERANKER_ID)
        _wait_for_quiet_machine()
        manager = ModelManager(idle_unload_seconds=1.0, max_resident_gb=4.0, min_free_gb=0.5)
        handle = manager.reranker(_reranker_cfg())
        docs = ["Thời gian thử việc do hai bên thỏa thuận, không quá 60 ngày.", "Tiền lương được trả bằng tiền mặt."]
        try:
            with handle.use() as rr:
                first = rr.score(PROBATION_QUERY, docs)
            assert handle.resident and handle.loads == 1 and rr.loaded and handle.measured_gb > 0
            with handle.use() as rr:                                   # reuse: no second load
                again = rr.score(PROBATION_QUERY, docs)
            assert handle.loads == 1 and again == first
            with handle.use():                                         # a model in use is never unloaded
                time.sleep(1.2)
                assert manager.sweep() == [] and handle.resident
            time.sleep(1.2)
            assert manager.sweep() and not handle.resident and not rr.loaded and handle.unloads == 1  # idle -> unloaded
            with handle.use() as rr:                                   # next access reloads, same weights, same scores
                reloaded = rr.score(PROBATION_QUERY, docs)
            assert handle.loads == 2 and handle.resident
            assert reloaded == pytest.approx(first, abs=0.05)
            time.sleep(1.2)
            with handle.use():                                         # the access check itself sweeps (unload + reload)
                pass
            assert handle.unloads == 2 and handle.loads == 3
        finally:
            manager.unload_all()

    def test_background_timer_unloads_but_never_loads(self):
        _require_cached(RERANKER_ID)
        _wait_for_quiet_machine()
        manager = ModelManager(idle_unload_seconds=0.5, min_free_gb=0.5)
        handle = manager.reranker(_reranker_cfg())
        try:
            manager.start_idle_timer(0.2)
            time.sleep(1.0)
            assert handle.loads == 0 and not handle.resident          # the timer does not load anything
            with handle.use() as rr:
                rr.score(PROBATION_QUERY, ["Thời gian thử việc tối đa là 60 ngày."])
            deadline = time.monotonic() + 10
            while handle.resident and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not handle.resident and handle.unloads == 1 and handle.loads == 1
        finally:
            manager.stop_idle_timer()
            manager.unload_all()

    def test_budget_unloads_least_recently_used_before_loading(self):
        _require_cached(RERANKER_ID)
        _require_cached(NLI_ID)
        _wait_for_quiet_machine()
        manager = ModelManager(idle_unload_seconds=600, max_resident_gb=4.0, min_free_gb=0.5)
        reranker, nli = manager.reranker(_reranker_cfg()), manager.nli(_nli_cfg())
        try:
            with reranker.use() as rr:
                rr.score(PROBATION_QUERY, ["Thời gian thử việc tối đa là 60 ngày."])
            assert reranker.resident and reranker.measured_gb > 0
            # A budget that holds either model alone but not both: the second load must evict the first.
            cost_r = max(reranker.estimate_gb, reranker.measured_gb)
            manager.configure(600, max(cost_r, nli.estimate_gb) + 0.1, 0.5)
            with nli.use() as model:
                model.classify("Thời gian thử việc tối đa là 60 ngày.", "Thời gian thử việc không quá 60 ngày.")
            assert nli.resident and not reranker.resident and reranker.unloads == 1 and not reranker.component.loaded
            with reranker.use() as rr:                                 # and back: one heavy model resident at a time
                rr.score(PROBATION_QUERY, ["Thời gian thử việc tối đa là 60 ngày."])
            assert reranker.resident and not nli.resident and nli.unloads == 1 and reranker.loads == 2
            assert sum(h["resident"] for h in manager.status()["models"]) == 1
        finally:
            manager.unload_all()

    def test_model_larger_than_budget_is_refused_before_loading(self):
        manager = ModelManager(max_resident_gb=0.5, min_free_gb=0.0)
        handle = manager.reranker(_reranker_cfg())
        with pytest.raises(ModelBudgetError) as err:
            with handle.use():
                pass
        assert err.value.kind == "memory_budget" and "max_resident_gb" in str(err.value)
        assert handle.loads == 0 and not handle.component.loaded and handle.in_use == 0

    def test_free_memory_floor_is_enforced_before_loading(self):
        manager = ModelManager(max_resident_gb=4.0, min_free_gb=100000.0)
        handle = manager.reranker(_reranker_cfg())
        with pytest.raises(ModelBudgetError) as err:
            with handle.use():
                pass
        assert err.value.kind == "memory_budget" and "min_free_gb" in str(err.value)
        assert handle.loads == 0 and not handle.component.loaded

    def test_load_failure_is_an_error_not_a_resident_model(self):
        manager = ModelManager(min_free_gb=0.0)
        handle = manager.reranker(RerankerConfig(enabled=True, model="no-such-owner/no-such-reranker", local_files_only=True))
        with pytest.raises(ModelComponentError) as err:
            with handle.use():
                pass
        assert err.value.kind == "load_error" and not handle.resident and handle.in_use == 0 and handle.loads == 0


# --------------------------------------------------------------------------- #
# NLI step in the verification pipeline (real mDeBERTa)
# --------------------------------------------------------------------------- #

SUPPORTED = "Thời gian thử việc đối với công việc của người quản lý doanh nghiệp tối đa là 180 ngày."
# Reverses the article's "chỉ được thử việc một lần": shares its vocabulary (passes the lexical L1 check) but the model
# scores it as contradicting Dieu_25. (This says nothing about NLI accuracy in general: on a probe the same model also
# "entailed" a wrong duration for another job category.)
CONTRADICTED = "Người lao động có thể thử việc nhiều lần đối với một công việc."


@pytest.fixture(scope="module")
def nli_world():
    """Real corpus, lexical verifier and one resident NLI model for the module; unloaded afterwards."""
    _require_cached(NLI_ID)
    _wait_for_quiet_machine()
    from src.domains import load_profile
    from src.verifier.lexical_grounding import LexicalGroundingVerifier
    retriever = HybridDomainRetriever(corpus_path=CORPUS)
    profile = load_profile("labour_vi_2019")
    manager = ModelManager(min_free_gb=0.5)
    yield {"manager": manager, "retriever": retriever, "profile": profile,
           "lexical": LexicalGroundingVerifier(retriever.corpus, profile=profile)}
    manager.unload_all()


def _pipeline(world, action="flag", threshold=0.9, mode="l1", nli_cfg=None):
    from src.agent.state import Citation
    from src.verifier.pipeline import NLIStep, VerificationPipeline
    handle = world["manager"].nli(nli_cfg or _nli_cfg(threshold=threshold, action=action))
    step = NLIStep(handle, world["retriever"].get_document_by_id, threshold=threshold, action=action)
    pipeline = VerificationPipeline(lexical_verifier=world["lexical"], mode=mode, nli_step=step,
                                    corpus=world["retriever"].corpus, ollama_url=LLAMA_URL,
                                    model_name="unused", l2_use_slm=False)   # the SLM L2 stage is off in these modes
    return pipeline, Citation


class TestNLIStep:
    def test_flag_records_every_sentence_against_the_full_cited_record(self, nli_world):
        pipeline, Citation = _pipeline(nli_world, action="flag")
        answer = f"{SUPPORTED} {CONTRADICTED}"
        result = pipeline.verify(answer, [Citation(article_id="Dieu_25")], ["Dieu_25"])
        nli = result.nli_result
        record = nli_world["retriever"].get_document_by_id("Dieu_25")["content"]
        assert result.is_valid and result.grounding_result.is_valid        # "flag" never changes the verdict
        assert nli["action"] == "flag" and nli["n_sentences"] == 2 and nli["n_pairs"] == 2 and nli["n_premises"] == 1
        assert all(p["premise_id"] == "Dieu_25" and p["premise_chars"] == len(record) for p in nli["pairs"])
        for pair in nli["pairs"]:
            assert abs(sum(pair["probabilities"].values()) - 1.0) < 1e-3 and pair["label"] in pair["probabilities"]
        by_sentence = {p["sentence"]: p for p in nli["pairs"]}
        assert by_sentence[SUPPORTED]["label"] == "entailment" and not by_sentence[SUPPORTED]["contradicted"]
        assert by_sentence[CONTRADICTED]["contradicted"] and nli["n_contradicted"] == 1
        assert nli["triggers_repair"] is False and "not evidence of answer correctness" in nli["note"]
        json.dumps(nli)

    def test_repair_fails_verification_only_when_contradiction_reaches_threshold(self, nli_world):
        pipeline, Citation = _pipeline(nli_world, action="repair")
        bad = pipeline.verify(f"{SUPPORTED} {CONTRADICTED}", [Citation(article_id="Dieu_25")], ["Dieu_25"])
        assert not bad.is_valid and bad.nli_result["triggers_repair"] and "NLI" in bad.repair_feedback
        assert CONTRADICTED[:30] in bad.repair_feedback and bad.grounding_result.is_valid
        good = pipeline.verify(SUPPORTED, [Citation(article_id="Dieu_25")], ["Dieu_25"])
        assert good.is_valid and good.repair_feedback is None and good.nli_result["n_contradicted"] == 0
        strict, _ = _pipeline(nli_world, action="repair", threshold=1.0)   # P(contradiction) >= 1.0 is not reached
        assert strict.verify(f"{SUPPORTED} {CONTRADICTED}", [Citation(article_id="Dieu_25")], ["Dieu_25"]).is_valid

    def test_each_cited_record_is_its_own_premise(self, nli_world):
        pipeline, Citation = _pipeline(nli_world, action="flag")
        retriever = nli_world["retriever"]
        cited = [Citation(article_id="Dieu_25"), Citation(article_id="Dieu_24")]
        result = pipeline.verify(SUPPORTED, cited, ["Dieu_25", "Dieu_24"])
        pairs = result.nli_result["pairs"]
        assert result.nli_result["n_premises"] == 2 and len(pairs) == 2
        assert {p["premise_id"]: p["premise_chars"] for p in pairs} == {
            aid: len(retriever.get_document_by_id(aid)["content"]) for aid in ("Dieu_25", "Dieu_24")}   # never concatenated

    def test_not_run_when_verification_is_off_or_l1_fails(self, nli_world):
        pipeline, Citation = _pipeline(nli_world)
        pipeline.set_mode("off")
        assert pipeline.verify(CONTRADICTED, [Citation(article_id="Dieu_25")], ["Dieu_25"]).nli_result is None
        pipeline.set_mode("l1")
        uncited = pipeline.verify(SUPPORTED, [Citation(article_id="Dieu_25")], [])   # never retrieved: L1 provenance fails
        assert not uncited.is_valid and uncited.nli_result is None

    def test_backend_failure_raises_instead_of_passing(self, nli_world):
        pipeline, Citation = _pipeline(nli_world, nli_cfg=NLIConfig(
            enabled=True, backend="qev_http", model="OmniJev/OneJev1.6-4B", base_url="http://127.0.0.1:9", timeout_seconds=3))
        with pytest.raises(ModelComponentError):
            pipeline.verify(SUPPORTED, [Citation(article_id="Dieu_25")], ["Dieu_25"])


class TestAgentConstruction:
    """Config selects the components; building the agent loads no model (lazy)."""

    def test_enabled_components_are_wired_lazily_and_shared(self, tmp_path):
        from src.verifier.pipeline import NLIStep
        cfg = _isolated(load_config(str(ROOT / "config/profiles/local-full.yaml")), tmp_path)
        manager = ModelManager(min_free_gb=0.5)
        first, second = LuatCheckAgent(config=cfg, model_manager=manager), LuatCheckAgent(config=cfg, model_manager=manager)
        assert first.reranker_handle is second.reranker_handle                     # one shared reranker for both agents
        step = first.verification_pipeline.nli_step
        assert isinstance(step, NLIStep) and step.handle is second.verification_pipeline.nli_step.handle
        assert (step.threshold, step.action) == (0.9, "flag")
        assert first.tool_registry.rerank_top_k_in == 20 and first.tool_registry.rerank_top_k_out == 5
        assert not first.reranker_handle.resident and not step.handle.resident     # nothing loaded yet
        assert first.reranker_handle.estimate_gb < manager.max_resident_gb

    def test_default_manager_is_the_process_wide_one(self, tmp_path):
        cfg = _isolated(load_config(str(ROOT / "config/profiles/local-full.yaml")), tmp_path)
        agent = LuatCheckAgent(config=cfg)
        assert agent.model_manager is ModelManager.shared()

    def test_injected_registry_is_configured_with_the_reranker_not_left_without_it(self, tmp_path):
        registry = DomainKnowledgeRegistry(corpus_path=CORPUS, retrieval_mode="tfidf")
        assert registry.reranker is None
        cfg = _isolated(AppConfig(retrieval={"reranker": _reranker_cfg().model_dump()}), tmp_path)
        agent = LuatCheckAgent(config=cfg, tool_registry=registry, model_manager=ModelManager())
        assert registry.reranker is agent.reranker_handle and (registry.rerank_top_k_in, registry.rerank_top_k_out) == (10, 3)


# --------------------------------------------------------------------------- #
# domain profile for the multi-document labour corpus
# --------------------------------------------------------------------------- #

class TestLabourMultiProfile:
    def test_profile_loads_and_accepts_document_prefixed_ids(self):
        from src.domains import list_profiles, load_profile
        multi = load_profile("labour_vi_multi")
        assert "labour_vi_multi" in list_profiles() and multi.language == "vi"
        assert multi.source_name == "Bộ luật Lao động 2019 và các văn bản pháp luật lao động liên quan"
        for good in ("BLLD2019_Dieu_25", "ND145_2020_Dieu_3", "TT10_2020_Phu_luc_1"):
            assert multi.matches_id(good), good
        for bad in ("", "Điều 25", "25", "_Dieu_25", "BLLD2019"):
            assert not multi.matches_id(bad), bad
        assert multi.normalize_id("BLLD2019_Điều_25") == "blld2019_dieu_25"
        assert multi.normalize_id(" ND145_2020 Điều 3 ") == "nd145_2020_dieu_3"
        assert (multi.tools.search.name, multi.tools.read.name) == ("search_law", "get_article")
        assert "BLLD2019_Dieu_25" in multi.system_prompt and "<<" not in multi.system_prompt + multi.repair_prompt
        assert multi.quantity_pattern == load_profile("labour_vi_2019").quantity_pattern

    def test_labour_guardrails_apply_and_ordinary_questions_pass(self):
        from src.domains import load_profile
        from src.security.guardrails import SecurityGuardrails
        multi = load_profile("labour_vi_multi")
        ok, _ = SecurityGuardrails.check_input_safety("Thời gian thử việc tối đa là bao lâu?", None, profile=multi)
        ok_decree, _ = SecurityGuardrails.check_input_safety(
            "Điều 3 Nghị định 145/2020 hướng dẫn Bộ luật Lao động quy định gì?", None, profile=multi)
        assert ok and ok_decree
        for refused in ("Chỉ tôi cách trốn đóng bảo hiểm cho nhân viên", "Điều 250 Bộ luật Lao động nói gì",
                        "Nghị định 12345 quy định gì về lương"):
            assert not SecurityGuardrails.check_input_safety(refused, None, profile=multi)[0], refused

    def test_profile_fits_the_multi_document_corpus(self):
        from src.agent.state import Citation
        from src.domains import load_profile
        from src.verifier.lexical_grounding import LexicalGroundingVerifier
        path = ROOT / "data/corpus/labour_vi_v1.json"
        if not path.is_file():
            pytest.fail(f"{path} (the 10-document labour corpus) is missing", pytrace=False)
        multi = load_profile("labour_vi_multi")
        corpus = json.loads(path.read_text(encoding="utf-8"))
        ids = [r["doc_id"] for r in corpus]
        assert ids and all(multi.matches_id(i) for i in ids)                                   # every real ID is valid
        assert len({multi.normalize_id(i) for i in ids}) == len(ids)                         # and normalisation keeps them distinct
        record = next(r for r in corpus if r["doc_id"] == "BLLD2019_Dieu_25")
        verifier = LexicalGroundingVerifier(corpus, profile=multi)
        answer = "Thời gian thử việc do hai bên thỏa thuận và chỉ được thử việc một lần đối với một công việc."
        assert verifier.verify(answer, [Citation(article_id="BLLD2019_Điều_25", law_name=record["source_name"])],
                               ["BLLD2019_Dieu_25"]).is_valid
        registry = DomainKnowledgeRegistry(retriever=HybridDomainRetriever(corpus=corpus))
        result = registry.search_knowledge("bảo hiểm tai nạn lao động tự nguyện", top_k=5)
        assert result["status"] == "success" and all(multi.matches_id(a["article_id"]) for a in result["articles"])

    def test_existing_profiles_are_untouched(self):
        from src.domains import load_profile
        assert load_profile("labour_vi_2019").ids.pattern == r"^Dieu_[0-9]+$"
        assert load_profile("hcmut_academic").ids.pattern == r"^HCMUT_[A-Z0-9]+_[A-Za-z0-9_]+$"


# --------------------------------------------------------------------------- #
# retrieval.mode: hybrid_index
# --------------------------------------------------------------------------- #

class TestHybridIndexMode:
    def test_faiss_store_is_rejected_with_a_clear_error_before_anything_is_opened(self, tmp_path):
        agent_cfg = _isolated(AppConfig(retrieval={"mode": "hybrid_index",
                                                   "index": {"path": "labor_code_2019_vi", "store": "faiss"}}), tmp_path)
        with pytest.raises(Exception, match="FAISS.*cannot.*share a process with torch|cannot be used inside the application"):
            LuatCheckAgent(config=agent_cfg)

    def test_missing_index_or_store_is_an_error(self, tmp_path):
        with pytest.raises(Exception):
            LuatCheckAgent(config=_isolated(AppConfig(retrieval={"mode": "hybrid_index", "index": {"path": "no_such_index"}}), tmp_path))
        with pytest.raises(Exception, match="no vector store"):
            LuatCheckAgent(config=_isolated(AppConfig(retrieval={"mode": "hybrid_index", "index": {
                "path": "labor_code_2019_vi", "store": "no_such_store"}}), tmp_path))

    def test_search_through_the_real_index_and_managed_embedding_model(self, tmp_path):
        """Run in a fresh interpreter: the embedding provider limits process RSS + MPS memory to 4 GB, which a long test
        session that already held other models would exceed through no fault of the code under test."""
        _require_cached("AITeamVN/Vietnamese_Embedding")
        _wait_for_quiet_machine()
        script = r"""
import json, sys
from src.agent.loop import LuatCheckAgent
from src.config.app_config import AppConfig
from src.model_manager import ModelManager
tmp, query = sys.argv[1], sys.argv[2]
cfg = AppConfig(retrieval={"mode": "hybrid_index", "index": {"path": "labor_code_2019_vi", "store": "numpy"}},
                models={"min_free_gb": 0.5})
cfg.memory.sqlite_path, cfg.security.audit_log_path, cfg.security.outbox_path = (
    tmp + "/m.db", tmp + "/a.jsonl", tmp + "/o.jsonl")
agent = LuatCheckAgent(config=cfg, model_manager=ModelManager.from_config(cfg.models))
retriever = agent.tool_registry.retriever
out = {"lazy": not retriever.handle.resident}
result, meta = agent._search_with_metadata(query, 5)
out.update(ids=[a["article_id"] for a in result["articles"]], meta=meta, resident=retriever.handle.resident,
           loads=retriever.handle.loads, doc=retriever.get_document_by_id("Dieu_25")["doc_id"], n=len(retriever.corpus))
retriever.close()
out["resident_after_close"] = retriever.handle.resident
print("RESULT" + json.dumps(out))
"""
        proc = subprocess.run([sys.executable, "-c", script, str(tmp_path), PROBATION_QUERY], cwd=ROOT, capture_output=True,
                              text=True, env={**os.environ, "PYTHONPATH": str(ROOT)})
        assert proc.returncode == 0, proc.stderr[-1500:]
        out = json.loads(proc.stdout.rsplit("RESULT", 1)[1])
        assert out["lazy"] and "Dieu_25" in out["ids"] and out["meta"] is None            # lazy until the first query
        assert out["resident"] and out["loads"] == 1 and out["doc"] == "Dieu_25" and out["n"] == 220
        assert out["resident_after_close"] is False


# --------------------------------------------------------------------------- #
# end to end: the real agent loop on the running llama-server (Bonsai)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def llama_server():
    try:
        health = requests.get(f"{LLAMA_URL}/health", timeout=5)
    except requests.RequestException as exc:
        pytest.fail(f"llama-server (Bonsai) is not reachable on {LLAMA_URL}: {exc}", pytrace=False)
    assert health.status_code == 200, f"llama-server on {LLAMA_URL} answered {health.status_code}"


E2E_QUESTIONS = [
    "Thời gian thử việc tối đa là bao lâu?",
    "Người lao động đơn phương chấm dứt hợp đồng lao động không xác định thời hạn phải báo trước bao nhiêu ngày?",
    "Người sử dụng lao động có được yêu cầu người lao động làm thêm giờ vào ngày nghỉ lễ không?",
]


class TestAgentEndToEnd:
    def _config(self, tmp_path, **retrieval):
        cfg = load_config(str(ROOT / "config/config.yaml"))                     # Bonsai via llama.cpp, profile labour_vi_2019
        assert cfg.model.endpoint.startswith(LLAMA_URL) and cfg.domain.profile == "labour_vi_2019"
        cfg = _isolated(cfg, tmp_path)
        cfg.memory.enabled = False
        cfg.budgets.wall_seconds = 180
        cfg.retrieval.reranker = _reranker_cfg(**retrieval)
        return cfg

    @staticmethod
    def _run_until_search(agent):
        """Real runs of the real model. A 2B model sometimes clarifies/refuses without searching, so up to three
        different questions are tried; the assertions concern only the runs in which the model did call search."""
        ledgers = []
        for n, question in enumerate(E2E_QUESTIONS):
            ledger = agent.run(question, session_id=f"wiring_e2e_{n}")
            ledgers.append(ledger)
            searches = [e for e in ledger.audit_events if e["event"] == "tool_call" and e["tool"] == "search_law"]
            if searches:
                return ledger, searches
        pytest.fail("the model never called search_law in %d runs: %s" % (
            len(ledgers), [(l.terminal_status, l.original_query[:30]) for l in ledgers]), pytrace=False)

    def test_run_with_reranker_records_rerank_metadata_in_the_ledger(self, tmp_path, llama_server, reranker_manager):
        agent = LuatCheckAgent(config=self._config(tmp_path), model_manager=reranker_manager)
        assert agent.reranker_handle is not None and agent.tool_registry.reranker is agent.reranker_handle
        ledger, searches = self._run_until_search(agent)
        assert ledger.terminal_status != "error", ledger.final_output
        rerank = searches[0]["metadata"]["rerank"]
        assert rerank["backend"] == "cross_encoder" and rerank["model"] == RERANKER_ID
        assert rerank["n_candidates"] == len(rerank["first_stage_ids"]) <= 10 and rerank["wall_ms"] > 0
        assert rerank["n_scored"] == len(rerank["ranking"]) == rerank["n_candidates"]
        assert 1 <= len(rerank["reranked_ids"]) <= 3 and set(rerank["reranked_ids"]) <= set(rerank["first_stage_ids"])
        assert set(rerank["reranked_ids"]) <= set(ledger.retrieved_article_ids)      # what the model was shown
        json.dumps(ledger.model_dump())                                             # the whole ledger stays serialisable
        handle = agent.reranker_handle
        assert handle.loads >= 1 and handle.resident

    def test_reranker_failure_ends_the_run_as_an_error_recorded_in_the_ledger(self, tmp_path, llama_server):
        cfg = self._config(tmp_path, model="no-such-owner/no-such-reranker")
        agent = LuatCheckAgent(config=cfg, model_manager=ModelManager(min_free_gb=0.0))
        ledger, searches = self._run_until_search(agent)
        assert ledger.terminal_status == "error" and ledger.final_output["action"] == "error"
        assert ledger.final_output["error_kind"] == "load_error" and ledger.final_output["verified"] is False
        assert searches[-1]["error"]["kind"] == "load_error"
        assert "metadata" not in searches[-1] and ledger.retrieved_article_ids == []   # nothing from the first stage leaks through
