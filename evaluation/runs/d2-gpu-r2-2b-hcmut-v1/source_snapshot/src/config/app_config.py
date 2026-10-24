"""
Centralized configuration for LuatCheck: Pydantic models loaded from YAML.

Every optional component has an explicit `enabled` switch (or, for verification, a `mode`) and a `backend` choice,
and is validated here, so a wrong value fails at load time with the key named. `src/pipeline` turns a validated
`AppConfig` into running components. The annotated list of every key is `config/README.md` /
`config/reference.yaml`.

Section models ignore unknown keys (older run configs and benchmark overrides rely on that);
`find_unknown_keys` / `load_config` report them as warnings instead.
"""
import os
import warnings
import yaml
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domains import DEFAULT_PROFILE_ID
from src.verifier.modes import VALID_MODES


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
    thought_max_chars: Optional[int] = Field(
        default=None, ge=20,
        description="r2 (F7): upper bound on the length of the `thought` string of an action. null (default) = unbounded, as in the frozen v3 runs. "
                    "Set, it is added as maxLength to the action JSON schema (see src/agent/llm_client.py)")


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
    # Long candidates (cross_encoder and llamacpp_http): a text longer than chunk_chars is split into overlapping windows, every
    # window is scored and the document score is the max (MaxP); null disables chunking (the pair is then cut at max_length tokens).
    # Defaults equal the class defaults in src/retrieval/rerankers.py (a test pins them).
    chunk_chars: Optional[int] = Field(default=1500, ge=200, description="Window size in characters for long candidates; null = no chunking")
    chunk_overlap_chars: int = Field(default=200, ge=0, description="Overlap between consecutive windows (must be < chunk_chars / 2)")

    @model_validator(mode="after")
    def _check(self) -> "RerankerConfig":
        if self.top_k_out > self.top_k_in:
            raise ValueError("retrieval.reranker.top_k_out must not exceed top_k_in")
        if self.chunk_chars is not None and self.chunk_overlap_chars >= self.chunk_chars // 2:
            raise ValueError("retrieval.reranker.chunk_overlap_chars must be smaller than chunk_chars / 2")
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
            if self.backend == "cross_encoder":
                cfg.update(chunk_chars=self.chunk_chars, chunk_overlap_chars=self.chunk_overlap_chars)
            return cfg
        if self.backend == "qev_http":
            return {"backend": "qev_http", "base_url": self.base_url, "model": self.model or "",
                    "timeout_seconds": self.timeout_seconds, "allow_remote": self.allow_remote}
        cfg = {"backend": "llama_cpp", "endpoint": self.base_url, "timeout_seconds": self.timeout_seconds,
               "max_length": self.max_length, "chunk_chars": self.chunk_chars, "chunk_overlap_chars": self.chunk_overlap_chars}
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
    bm25_top_k: int = Field(default=5, ge=1, description="Accepted for compatibility; not read (each retriever fetches 2 x the requested top_k)")
    dense_top_k: int = Field(default=5, ge=1, description="Accepted for compatibility; not read")
    rrf_k: int = Field(default=60, ge=1, description="Reciprocal Rank Fusion smoothing constant")
    final_top_k: int = Field(default=5, ge=1)
    default_top_k: int = Field(default=3, ge=1, description="r2 (F2): top_k used when the model omits it (still capped by final_top_k). 3 = the frozen v3 behaviour")
    first_search_anchor: Literal["none", "question_plus_query"] = Field(
        default="none",
        description="r2 (F1): 'none' = the first search uses the model's query (v3). 'question_plus_query' = the first search of a run uses the user's "
                    "question followed by the words of the model's query that the question does not already contain")
    corpus_path: str = Field(default="data/corpus/labor_code_2019_official.json")
    dense_model_type: Literal["tfidf", "bm25", "bge-m3", "phobert", "all-minilm", "nomic-embed-text"] = Field(
        default="tfidf",
        description="Second retriever fused with BM25 in mode bm25_tfidf: tfidf (statistical, default), bm25 (BM25 alone), "
                    "or the name of an embedding model served at model.endpoint (neural; fails if unavailable)")
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
    """`mode` switches verification: off | l1 (lexical grounding) | l1_l2 (plus native-model entailment, needs
    `l2_use_slm: true`); aliases are listed in `src/verifier/modes.py`. `nli` is an independent optional step."""
    mode: str = Field(default="l1", description="Verification mode: 'off', 'l1', 'l1_l2' (or an alias, see src/verifier/modes.py)")
    similarity_threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="Accepted for compatibility; not read by any verifier")
    l1_version: Literal["v1", "v2"] = Field(default="v1", description="L1 implementation (default v1 so every existing config keeps its meaning): 'v1' (original, whole-record bag of words; reproduces the frozen runs) or 'v2' (fair quote matching, claim-local quantities, sentence-level support, actionable feedback)")
    l1_overlap_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="L1 v1 only: minimum token overlap with the whole cited text")
    l1_support_threshold: float = Field(default=0.50, ge=0.0, le=1.0, description="L1 v2 only: minimum fraction of an answer sentence's content tokens found in its best single source window")
    l1_sentence_support: Literal["block", "warn"] = Field(
        default="block",
        description="L1 v2 only. 'block' (default) = an answer sentence below l1_support_threshold rejects the answer. 'warn' = recorded as a warning in the "
                    "ledger and the result, the answer is not rejected; quote and quantity failures still block. v1 ignores this key")
    repair_feedback_style: Literal["v1", "verifier_report"] = Field(
        default="v1",
        description="r2 (F6): how a rejection reaches the model. 'v1' = the profile's repair_prompt as a user message (frozen v3 behaviour). "
                    "'verifier_report' = a labelled [VERIFIER_REPORT] observation that offers fixing the flagged item and refuses only if the sources lack the answer")
    l2_entailment_threshold: float = Field(default=0.30, ge=0.0, le=1.0, description="Minimum L2 semantic entailment threshold")
    l2_use_slm: bool = Field(default=False, description="Enable native-model L2 entailment; no heuristic substitute")
    nli: NLIConfig = Field(default_factory=NLIConfig)

    @model_validator(mode="after")
    def _check_mode(self) -> "VerifierConfig":
        if self.mode not in VALID_MODES:
            raise ValueError(f"verifier.mode {self.mode!r} is not valid; expected one of {sorted(VALID_MODES)}")
        return self


class MemoryConfig(BaseModel):
    """Episodic memory of verified answers (`src/memory`). `enabled: false` creates no store at all."""
    enabled: bool = True
    backend: Literal["sqlite"] = "sqlite"
    reuse_answers: bool = Field(default=True, description="Serve a stored answer to a similar later question")
    sqlite_path: str = Field(default="data/db/local_slm_memory.db")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    index_version: str = Field(default="native-v2026.10.22")


class GuardrailsConfig(BaseModel):
    """Pre-model input check (`SecurityGuardrails.check_input_safety`: shared injection patterns plus the domain
    profile's patterns). Input delimiting of untrusted text (`wrap_untrusted_input`) is part of the prompt and is
    always applied."""
    enabled: bool = True


class SecurityConfig(BaseModel):
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    audit_log_path: str = Field(default="data/audit_log.jsonl")
    outbox_path: str = Field(default="data/outbox/sent_summaries.jsonl")
    egress_requires_confirmation: bool = Field(default=True, description="Accepted for compatibility; no component reads it (the UI always asks)")


class DomainConfig(BaseModel):
    profile: str = Field(default=DEFAULT_PROFILE_ID,
                         description="Domain profile id (config/domains/<id>.yaml) or path to a profile YAML: prompts, tool names, ID rules, guardrails, L1 units")
    profile_variant: Literal["", "r2"] = Field(
        default="",
        description="r2 (F4, F6): '' = load `profile` as written. 'r2' = load the revised profile `<profile>_r2` (config/domains/<profile>_r2.yaml): "
                    "refuse also when the retrieved text lacks the answer, clarify only for missing facts about the user's situation, query-writing guidance. "
                    "Needs a profile id, not a path")


class ToolsConfig(BaseModel):
    """Wording of the tool observations the model reads."""
    search_hints: bool = Field(
        default=False,
        description="r2 (F3): false = search observations as in v3. true = each search observation also states how many hits are truncated, "
                    "advises reading before concluding, and shows `tool_calls_remaining`")


class AgentConfig(BaseModel):
    """Controller policy of one run (`src/agent/loop.py`)."""
    require_search_before_answer: bool = Field(
        default=False,
        description="r2 (F5): true = an answer or clarify before the first search becomes an observation telling the model to search first "
                    "(a step, not a tool call); refuse stays allowed. Inactive when the client cannot search (closed-book / oracle baselines)")
    free_duplicate_notices: bool = Field(
        default=False,
        description="r2 (F8): true = duplicate_query / already_read notices do not consume a tool call (they still use a step)")


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
    agent: AgentConfig = Field(default_factory=AgentConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
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


def find_unknown_keys(raw: Dict[str, Any], model: type = AppConfig, prefix: str = "") -> List[str]:
    """Dotted paths of keys in a raw config dict that no config model declares (typos, removed keys).

    Sections that accept arbitrary keys (`verifier.nli`, whose extras go to the NLI backend) are not descended into.
    """
    unknown: List[str] = []
    for key, value in (raw or {}).items():
        field = model.model_fields.get(key)
        if field is None:
            unknown.append(f"{prefix}{key}")
        elif isinstance(value, dict) and isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
            if field.annotation.model_config.get("extra") != "allow":
                unknown.extend(find_unknown_keys(value, field.annotation, f"{prefix}{key}."))
    return unknown


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

    for key in find_unknown_keys(raw_data):
        warnings.warn(f"{target_path}: unknown config key '{key}' is ignored", UserWarning, stacklevel=2)
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
