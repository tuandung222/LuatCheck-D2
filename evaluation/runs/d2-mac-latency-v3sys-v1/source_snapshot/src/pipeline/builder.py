"""Builds the controller's components from an `AppConfig`.

This module is the one place that maps a config key to an implementation:

| config key                                | component                                             |
|-------------------------------------------|-------------------------------------------------------|
| `model.provider`                          | controller LLM client (`src/agent/llm_client.py`)      |
| `retrieval.mode`, `retrieval.dense_model_type` | first-stage retriever (BM25 + TF-IDF/RRF, BM25 only, neural, or a built index) |
| `retrieval.reranker.enabled/backend`      | second-stage reranker through the `ModelManager`       |
| `verifier.mode`, `verifier.l2_use_slm`    | L1 lexical grounding / L2 entailment                   |
| `verifier.nli.enabled/backend`            | optional NLI step after L1                             |
| `memory.enabled/reuse_answers/backend`    | episodic answer memory                                 |
| `security.guardrails.enabled`             | input guardrails (read by the controller)              |
| `domain.profile`, `domain.profile_variant` | prompts, tool names, ID rules, messages (`<id>` or the revised `<id>_r2`) |

Nothing is built unless its section asks for it; an unavailable backend raises when it is used and never turns into a
substitute result. Callers that already own a component pass it in `Overrides`, which takes precedence over the config.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.agent.llm_client import (
    GatewayLLMClient, LlamaCppLLMClient, MlxVlmLLMClient, NativeLLMClient, OllamaLLMClient)
from src.config.app_config import AppConfig, ModelConfig, RerankerConfig, RetrievalConfig
from src.domains import DomainProfile, load_profile
from src.interfaces.base import BaseLLMClient, BaseRetriever, BaseToolRegistry, BaseVerificationPipeline, BaseVerifier
from src.memory.answer_memory import AnswerMemory
from src.memory.sqlite_store import SQLiteEpisodicStore
from src.model_manager import ModelManager
from src.security.audit_logger import AuditLogger
from src.tools.domain_tools import DomainKnowledgeRegistry
from src.verifier.lexical_grounding_v2 import make_lexical_verifier
from src.verifier.modes import resolve_mode
from src.verifier.pipeline import NLIStep, VerificationPipeline
from src.verifier.semantic_nli import SemanticNLIVerifier

LLAMACPP_PROVIDERS = frozenset({"llamacpp", "llama.cpp", "openai", "prism", "prism_llamacpp", "prism-llamacpp", "prismml"})


@dataclass
class Overrides:
    """Values the caller supplies instead of reading them from the config. `None` means "use the config"."""
    # per-agent settings
    model_name: Optional[str] = None
    endpoint: Optional[str] = None            # controller endpoint; also the neural embedding endpoint
    corpus_path: Optional[str] = None
    outbox_path: Optional[str] = None
    verification_mode: Optional[str] = None
    enable_verification: Optional[bool] = None   # legacy switch: False forces mode off, True turns off into L1
    l2_use_slm: Optional[bool] = None
    # ready-made components
    profile: Optional[DomainProfile] = None
    model_manager: Optional[ModelManager] = None
    retriever: Optional[BaseRetriever] = None
    tool_registry: Optional[BaseToolRegistry] = None
    llm_client: Optional[BaseLLMClient] = None
    lexical_verifier: Optional[BaseVerifier] = None
    semantic_verifier: Optional[Any] = None
    verification_pipeline: Optional[BaseVerificationPipeline] = None
    sqlite_store: Optional[SQLiteEpisodicStore] = None
    audit_logger: Optional[AuditLogger] = None


@dataclass
class AgentComponents:
    """Everything `LuatCheckAgent` needs, already built. Construct with `build_components`."""
    config: AppConfig
    profile: DomainProfile
    model_name: str
    endpoint: str
    corpus_path: str
    outbox_path: str
    l2_use_slm: bool
    verification_mode: str
    model_manager: Optional[ModelManager]
    tool_registry: BaseToolRegistry
    reranker_handle: Any
    lexical_verifier: BaseVerifier
    semantic_verifier: Any
    verification_pipeline: BaseVerificationPipeline
    answer_memory: AnswerMemory
    sqlite_store: Optional[SQLiteEpisodicStore]
    audit_logger: AuditLogger
    llm_client: BaseLLMClient


# --------------------------------------------------------------------------- #
# controller LLM client
# --------------------------------------------------------------------------- #

def _sampling(model: ModelConfig) -> Dict[str, Any]:
    pairs = (("top_p", model.top_p), ("top_k", model.top_k), ("min_p", model.min_p),
             ("presence_penalty", model.presence_penalty))
    return {key: value for key, value in pairs if value is not None}


def build_llm_client(config: AppConfig, profile: DomainProfile, *, endpoint: Optional[str] = None,
                     model_name: Optional[str] = None) -> NativeLLMClient:
    """Native client for `model.provider`: ollama | mlx | llamacpp (and its aliases) | gateway."""
    model = config.model
    endpoint = endpoint or model.endpoint
    options = dict(model_name=model_name or model.name, temperature=model.temperature,
                   timeout_seconds=model.timeout_seconds, seed=model.seed, max_output_tokens=model.max_output_tokens,
                   context_tokens=model.context_tokens, profile=profile, thought_max_chars=model.thought_max_chars)
    provider = model.provider
    if provider == "gateway":
        if not model.api_key_env:
            raise ValueError("Gateway provider requires model.api_key_env.")
        return GatewayLLMClient(endpoint=endpoint, api_key_env=model.api_key_env,
                                reasoning_effort=model.reasoning_effort, **options)
    if provider == "mlx":
        return MlxVlmLLMClient(endpoint=endpoint, sampling=_sampling(model),
                               constrained_json=model.constrained_json, **options)
    if provider in LLAMACPP_PROVIDERS:
        return LlamaCppLLMClient(endpoint=endpoint, sampling=_sampling(model),
                                 constrained_json=model.constrained_json,
                                 enable_thinking=model.enable_thinking, **options)
    if provider == "ollama":
        return OllamaLLMClient(endpoint=endpoint, **options)
    raise ValueError(f"Unsupported model.provider {provider!r}; native inference is required.")


# --------------------------------------------------------------------------- #
# retrieval and tools
# --------------------------------------------------------------------------- #

def needs_model_manager(config: AppConfig) -> bool:
    """True when a component that holds a model in this process is enabled."""
    return bool(config.retrieval.reranker.enabled or config.verifier.nli.enabled
                or config.retrieval.mode == "hybrid_index")


def build_retriever(retrieval: RetrievalConfig, *, corpus_path: str, endpoint: Optional[str],
                    manager: Optional[ModelManager], profile: Optional[DomainProfile] = None) -> BaseRetriever:
    """First-stage retriever for `retrieval.mode`.

    * `bm25_tfidf`:  in-memory BM25 fused by RRF with the retriever named by `dense_model_type`
                     (tfidf, bm25 = BM25 alone, or an embedding model served at `endpoint`).
    * `hybrid_index`: a built, persisted `src/indexing` index (`retrieval.index`).
    """
    if retrieval.mode == "hybrid_index":
        from src.retrieval.hybrid_domain import IndexedRetriever
        return IndexedRetriever(retrieval.index, manager=manager)
    from src.retrieval.hybrid_domain import HybridDomainRetriever
    kwargs: Dict[str, Any] = dict(corpus_path=corpus_path, dense_endpoint=endpoint,
                                  retrieval_mode=retrieval.dense_model_type, rrf_k=retrieval.rrf_k,
                                  id_normalizer=profile.normalize_id if profile is not None else None)
    if retrieval.dense_model_type not in ("tfidf", "bm25"):
        kwargs["dense_model_name"] = retrieval.dense_model_type
    return HybridDomainRetriever(**kwargs)


def attach_reranker(registry: Any, reranker: RerankerConfig, manager: Optional[ModelManager]) -> Any:
    """Turn on second-stage reranking in the search tool when `retrieval.reranker.enabled`; returns the model handle."""
    if not reranker.enabled:
        return None
    if not hasattr(registry, "configure_reranker"):
        raise ValueError("retrieval.reranker is enabled but the injected tool_registry cannot rerank "
                         "(it has no configure_reranker)")
    handle = manager.reranker(reranker)
    registry.configure_reranker(handle, reranker.top_k_in, reranker.top_k_out)
    return handle


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #

def build_verification_pipeline(config: AppConfig, profile: DomainProfile, registry: Any, manager: Optional[ModelManager],
                                *, mode: str, endpoint: str, model_name: str, l2_use_slm: bool,
                                lexical: Optional[BaseVerifier] = None, semantic: Optional[Any] = None):
    """(L1 verifier, L2 verifier, pipeline) for `verifier.*`. The NLI step is added only when `verifier.nli.enabled`."""
    verifier_cfg, nli_cfg = config.verifier, config.verifier.nli
    corpus = getattr(registry.retriever, "corpus", [])
    lexical = lexical or make_lexical_verifier(corpus, verifier_cfg.l1_version, profile=profile,
                                               overlap_threshold=verifier_cfg.l1_overlap_threshold,
                                               support_threshold=verifier_cfg.l1_support_threshold,
                                               sentence_support=verifier_cfg.l1_sentence_support)
    semantic = semantic or SemanticNLIVerifier(corpus, entailment_threshold=verifier_cfg.l2_entailment_threshold,
                                               ollama_url=endpoint, model_name=model_name, use_slm=l2_use_slm,
                                               profile=profile)
    nli_step = None
    if nli_cfg.enabled:
        lookup = getattr(registry.retriever, "get_document_by_id", None) or registry.retriever.get_article_by_id
        nli_step = NLIStep(manager.nli(nli_cfg), lookup, threshold=nli_cfg.threshold, action=nli_cfg.action,
                           messages=profile.messages)
    pipeline = VerificationPipeline(lexical_verifier=lexical, semantic_verifier=semantic, mode=mode,
                                    nli_step=nli_step, messages=profile.messages)
    return lexical, semantic, pipeline


# --------------------------------------------------------------------------- #
# the whole set
# --------------------------------------------------------------------------- #

def build_components(config: AppConfig, overrides: Optional[Overrides] = None) -> AgentComponents:
    """Read `config` and build every component it enables; `overrides` replace config values or whole components."""
    o = overrides or Overrides()
    profile = o.profile or load_profile(config.domain.profile, config.domain.profile_variant)
    model_name = o.model_name or config.model.name
    endpoint = o.endpoint or config.model.endpoint
    corpus_path = o.corpus_path or config.retrieval.corpus_path
    outbox_path = o.outbox_path or config.security.outbox_path
    l2_use_slm = o.l2_use_slm if o.l2_use_slm is not None else config.verifier.l2_use_slm
    mode = resolve_mode(config.verifier.mode, o.verification_mode, o.enable_verification)

    manager = o.model_manager
    if manager is None and needs_model_manager(config):
        manager = ModelManager.shared(config.models)

    registry = o.tool_registry
    if registry is None:
        retriever = o.retriever or build_retriever(config.retrieval, corpus_path=corpus_path, endpoint=endpoint,
                                                   manager=manager, profile=profile)
        registry = DomainKnowledgeRegistry(corpus_path=corpus_path, outbox_path=outbox_path, retriever=retriever,
                                           profile=profile)
    reranker_handle = attach_reranker(registry, config.retrieval.reranker, manager)

    if o.verification_pipeline is not None:
        pipeline = o.verification_pipeline
        lexical = getattr(pipeline, "lexical_verifier", pipeline.verifier)
        semantic = getattr(pipeline, "semantic_verifier", pipeline.l2_verifier)
    else:
        lexical, semantic, pipeline = build_verification_pipeline(
            config, profile, registry, manager, mode=mode, endpoint=endpoint, model_name=model_name,
            l2_use_slm=l2_use_slm, lexical=o.lexical_verifier, semantic=o.semantic_verifier)

    memory_cfg = config.memory
    store = o.sqlite_store or (SQLiteEpisodicStore(db_path=memory_cfg.sqlite_path, index_version=memory_cfg.index_version)
                               if memory_cfg.enabled else None)
    audit_logger = o.audit_logger or AuditLogger(log_path=config.security.audit_log_path)
    memory = AnswerMemory(store, audit_logger, profile, enabled=memory_cfg.enabled,
                          reuse_answers=memory_cfg.reuse_answers, similarity_threshold=memory_cfg.similarity_threshold)

    llm_client = o.llm_client or build_llm_client(config, profile, endpoint=endpoint, model_name=model_name)
    return AgentComponents(
        config=config, profile=profile, model_name=model_name, endpoint=endpoint, corpus_path=corpus_path,
        outbox_path=outbox_path, l2_use_slm=l2_use_slm, verification_mode=mode, model_manager=manager,
        tool_registry=registry, reranker_handle=reranker_handle, lexical_verifier=lexical, semantic_verifier=semantic,
        verification_pipeline=pipeline, answer_memory=memory, sqlite_store=store, audit_logger=audit_logger,
        llm_client=llm_client)
