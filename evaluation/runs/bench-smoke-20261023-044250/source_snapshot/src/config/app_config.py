"""
Centralized Configuration Module for LuatCheck.

Centralizes system configuration using Pydantic Models, loaded from YAML
and environment variables. Allows data scientists to easily customize
model parameters, retriever, verifier, and episodic memory settings.
"""
import os
import yaml
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domains import DEFAULT_PROFILE_ID


class ModelConfig(BaseModel):
    provider: Literal["ollama", "mlx", "gateway", "llamacpp", "llama.cpp", "openai", "prism", "prism_llamacpp", "prism-llamacpp", "prismml"] = "ollama"
    endpoint: str = Field(default="http://localhost:11434", description="LLM server endpoint URL")
    name: str = Field(default="qwen2.5:3b", description="Model identifier to serve")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    seed: Optional[int] = None
    max_output_tokens: int = Field(default=512, ge=32)
    context_tokens: int = Field(default=4096, ge=1024)
    top_p: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=0)
    min_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    presence_penalty: Optional[float] = Field(default=None)
    constrained_json: bool = Field(default=True, description="Action-schema constrained decoding (mlx; llamacpp when enabled)")
    enable_thinking: Optional[bool] = Field(default=None, description="Chat-template thinking switch (llamacpp)")
    api_key_env: Optional[str] = Field(default=None, description="Environment variable holding the gateway credential")
    reasoning_effort: Optional[str] = Field(default=None, description="Gateway reasoning effort, when supported")


class BudgetsConfig(BaseModel):
    max_tool_calls: int = Field(default=5, ge=1, description="Maximum tool execution budget per session")
    max_repairs: int = Field(default=2, ge=0, description="Maximum self-repair attempts upon verification failure")
    max_steps: int = Field(default=10, ge=1, description="Maximum total FSM transitions to prevent infinite loops")
    wall_seconds: float = Field(default=180, gt=0)


_LOCAL_RERANKERS = ("cross_encoder", "qwen3")
_HTTP_RERANKERS = ("qev_http", "llamacpp_http")


class RerankerConfig(BaseModel):
    """Optional second-stage reranker (`retrieval.reranker`). Disabled by default: first-stage order is returned as before.

    When enabled, the search tool takes `top_k_in` first-stage candidates, scores them against the search query
    with the configured model and returns the best min(requested top_k, `top_k_out`) in reranked order.
    A reranker failure is an execution error; it never falls back to first-stage order.
    """
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    backend: Literal["cross_encoder", "qwen3", "qev_http", "llamacpp_http"] = "cross_encoder"
    model: Optional[str] = Field(default=None, description="HF repo id / local path (local backends), served model name (HTTP)")
    top_k_in: int = Field(default=20, ge=1, description="First-stage candidates passed to the reranker")
    top_k_out: int = Field(default=5, ge=1, description="Maximum results returned after reranking")
    device: str = "auto"
    max_length: int = Field(default=1024, ge=16, description="Tokens per (query, document) pair; longer pairs are truncated and counted")
    dtype: Optional[str] = None
    base_url: Optional[str] = Field(default=None, description="HTTP backends only (loopback unless allow_remote)")
    allow_remote: bool = False
    # Optional extras beyond the shared contract.
    local_files_only: bool = Field(default=False, description="Never touch the network when loading local weights")
    batch_size: int = Field(default=1, ge=1)
    timeout_seconds: float = Field(default=60.0, gt=0.0)

    @model_validator(mode="after")
    def _check(self) -> "RerankerConfig":
        if self.top_k_out > self.top_k_in:
            raise ValueError("retrieval.reranker.top_k_out must not exceed top_k_in")
        if self.enabled:
            if self.backend != "llamacpp_http" and not self.model:
                raise ValueError(f"retrieval.reranker.model is required when enabled (backend {self.backend})")
            if self.backend in _HTTP_RERANKERS and not self.base_url:
                raise ValueError(f"retrieval.reranker.base_url is required for backend {self.backend}")
            if self.backend == "llamacpp_http" and self.allow_remote:
                raise ValueError("retrieval.reranker: llamacpp_http is loopback-only; allow_remote is not supported")
        return self

    @property
    def is_local(self) -> bool:
        return self.backend in _LOCAL_RERANKERS

    def component_config(self) -> Dict[str, Any]:
        """Config for `src.retrieval.rerankers.build_reranker` (top_k_in/out are applied by the search tool)."""
        if self.backend in _LOCAL_RERANKERS:
            cfg: Dict[str, Any] = {"backend": self.backend, "model": self.model, "device": self.device,
                                   "local_files_only": self.local_files_only, "max_length": self.max_length,
                                   "batch_size": self.batch_size}
            if self.dtype:
                cfg["dtype"] = self.dtype
            return cfg
        if self.backend == "qev_http":
            return {"backend": "qev_http", "base_url": self.base_url, "model": self.model or "",
                    "timeout_seconds": self.timeout_seconds, "allow_remote": self.allow_remote}
        cfg = {"backend": "llama_cpp", "endpoint": self.base_url, "timeout_seconds": self.timeout_seconds}
        if self.model:
            cfg["model"] = self.model
        return cfg


class IndexConfig(BaseModel):
    """`retrieval.index`: a built `src/indexing` index used when `retrieval.mode` is `hybrid_index`."""
    model_config = ConfigDict(extra="forbid")

    path: Optional[str] = Field(default=None, description="Index name under data/index or a path to the index directory")
    store: Optional[str] = Field(default=None, description="Vector store name inside the index; default = the manifest's default store")
    search_mode: Literal["hybrid", "keyword", "vector"] = "hybrid"
    verify_corpus: bool = Field(default=True, description="Refuse an index whose corpus hash no longer matches")


class RetrievalConfig(BaseModel):
    bm25_top_k: int = Field(default=5, ge=1)
    dense_top_k: int = Field(default=5, ge=1)
    rrf_k: int = Field(default=60, ge=1, description="Reciprocal Rank Fusion smoothing constant")
    final_top_k: int = Field(default=5, ge=1)
    corpus_path: str = Field(default="data/corpus/labor_code_2019_official.json")
    dense_model_type: Literal["tfidf", "bm25", "bge-m3", "phobert", "all-minilm", "nomic-embed-text"] = "tfidf"
    mode: Literal["bm25_tfidf", "hybrid_index"] = Field(
        default="bm25_tfidf",
        description="bm25_tfidf: in-memory BM25 + TF-IDF/RRF over corpus_path (default). hybrid_index: src/indexing HybridSearcher over `index`")
    index: IndexConfig = Field(default_factory=IndexConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)

    @model_validator(mode="after")
    def _check_mode(self) -> "RetrievalConfig":
        if self.mode == "hybrid_index" and not self.index.path:
            raise ValueError("retrieval.mode 'hybrid_index' requires retrieval.index.path")
        return self


class NLIConfig(BaseModel):
    """Optional NLI check after L1 (`verifier.nli`). Disabled by default.

    Premise = the full content of one cited record (never a concatenation), hypothesis = one answer sentence.
    `flag` records the results in the ledger; `repair` also triggers the repair loop when P(contradiction) >= threshold.
    Any other key (model, device, base_url, max_length, ...) is passed to `build_nli_backend`, which rejects unknown ones.
    """
    model_config = ConfigDict(extra="allow")

    enabled: bool = False
    backend: Literal["cross_encoder", "llm", "decision_model", "qev_http"] = "cross_encoder"
    model: Optional[str] = None
    threshold: float = Field(default=0.9, ge=0.0, le=1.0, description="P(contradiction) at which `repair` fires")
    action: Literal["flag", "repair"] = "flag"

    @model_validator(mode="after")
    def _check(self) -> "NLIConfig":
        if self.enabled and not self.model:
            raise ValueError("verifier.nli.model is required when enabled")
        return self

    def component_config(self) -> Dict[str, Any]:
        cfg = {k: v for k, v in self.model_dump().items() if k not in ("enabled", "action") and v is not None}
        return cfg


class VerifierConfig(BaseModel):
    mode: str = Field(default="l1", description="Verification mode: 'off', 'l1', 'l1_l2'")
    similarity_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    l1_overlap_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum L1 token overlap threshold")
    l2_entailment_threshold: float = Field(default=0.30, ge=0.0, le=1.0, description="Minimum L2 semantic entailment threshold")
    l2_use_slm: bool = Field(default=False, description="Enable native-model L2 entailment; no heuristic substitute")
    nli: NLIConfig = Field(default_factory=NLIConfig)


class MemoryConfig(BaseModel):
    enabled: bool = True
    reuse_answers: bool = Field(default=True, description="Serve a stored answer to a similar later question")
    sqlite_path: str = Field(default="data/db/local_slm_memory.db")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    index_version: str = Field(default="native-v2026.10.22")


class SecurityConfig(BaseModel):
    audit_log_path: str = Field(default="data/audit_log.jsonl")
    outbox_path: str = Field(default="data/outbox/sent_summaries.jsonl")
    egress_requires_confirmation: bool = Field(default=True)


class DomainConfig(BaseModel):
    profile: str = Field(default=DEFAULT_PROFILE_ID,
                         description="Domain profile id (config/domains/<id>.yaml) or path to a profile YAML: prompts, tool names, ID rules, guardrails, L1 units")


class ModelsConfig(BaseModel):
    """Resident-model policy of `src.model_manager.ModelManager` (reranker / NLI / embedding models loaded in this process)."""
    model_config = ConfigDict(extra="forbid")

    idle_unload_seconds: float = Field(default=600.0, ge=0.0, description="Unload a model unused for this long (checked on the next access, or by the idle timer)")
    max_resident_gb: float = Field(default=4.0, gt=0.0, description="Estimated resident budget; least-recently-used models are unloaded before a new load that would exceed it")
    min_free_gb: float = Field(default=1.0, ge=0.0, description="Refuse to load when available system memory is below this floor")
    default_estimate_gb: float = Field(default=2.5, gt=0.0, description="Estimate used when a model's weights cannot be sized from the local cache")
    wait_for_quiet_machine_gb: Optional[float] = Field(default=None, gt=0.0, description="Before a load, wait while another python process holds more than this")


class AppConfig(BaseModel):
    domain: DomainConfig = Field(default_factory=DomainConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    budgets: BudgetsConfig = Field(default_factory=BudgetsConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)

    @property
    def verification(self) -> VerifierConfig:
        """Alias for verifier to support alternative configuration naming."""
        return self.verifier


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from a YAML file. If the file does not exist,
    returns an AppConfig instance with default values.
    Can be overridden via the LOCAL_SLM_CONFIG_PATH or LUATCHECK_CONFIG_PATH environment variable,
    with dynamic environment variable overrides for MODEL_NAME, MODEL_ENDPOINT, MODEL_PROVIDER.
    """
    target_path = (
        config_path
        or os.getenv("LOCAL_SLM_CONFIG_PATH")
        or os.getenv("LUATCHECK_CONFIG_PATH", "config/config.yaml")
    )
    raw_data = {}
    if os.path.exists(target_path):
        with open(target_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
    elif config_path or os.getenv("LOCAL_SLM_CONFIG_PATH") or os.getenv("LUATCHECK_CONFIG_PATH"):
        raise FileNotFoundError(f"Explicit configuration not found: {target_path}")

    cfg = AppConfig(**raw_data)

    # Dynamic environment variable overrides
    if os.getenv("MODEL_ENDPOINT"):
        cfg.model.endpoint = os.getenv("MODEL_ENDPOINT")
    elif os.getenv("OLLAMA_ENDPOINT"):
        cfg.model.endpoint = os.getenv("OLLAMA_ENDPOINT")
    if os.getenv("MODEL_NAME"):
        cfg.model.name = os.getenv("MODEL_NAME")
    if os.getenv("MODEL_PROVIDER"):
        cfg.model.provider = os.getenv("MODEL_PROVIDER")

    return AppConfig.model_validate(cfg.model_dump())
