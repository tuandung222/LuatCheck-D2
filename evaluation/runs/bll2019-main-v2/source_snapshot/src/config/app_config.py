"""
Centralized Configuration Module for LuatCheck.

Centralizes system configuration using Pydantic Models, loaded from YAML
and environment variables. Allows data scientists to easily customize
model parameters, retriever, verifier, and episodic memory settings.
"""
import os
import yaml
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: Literal["ollama", "llamacpp", "llama.cpp", "openai", "prism", "prism_llamacpp", "prism-llamacpp", "prismml"] = "ollama"
    endpoint: str = Field(default="http://localhost:11434", description="LLM server endpoint URL")
    name: str = Field(default="qwen2.5:3b", description="Model identifier to serve")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    seed: Optional[int] = None
    max_output_tokens: int = Field(default=512, ge=32)
    context_tokens: int = Field(default=4096, ge=1024)


class BudgetsConfig(BaseModel):
    max_tool_calls: int = Field(default=5, ge=1, description="Maximum tool execution budget per session")
    max_repairs: int = Field(default=2, ge=0, description="Maximum self-repair attempts upon verification failure")
    max_steps: int = Field(default=10, ge=1, description="Maximum total FSM transitions to prevent infinite loops")
    wall_seconds: float = Field(default=180, gt=0)


class RetrievalConfig(BaseModel):
    bm25_top_k: int = Field(default=5, ge=1)
    dense_top_k: int = Field(default=5, ge=1)
    rrf_k: int = Field(default=60, ge=1, description="Reciprocal Rank Fusion smoothing constant")
    final_top_k: int = Field(default=5, ge=1)
    corpus_path: str = Field(default="data/corpus/labor_code_2019_official.json")
    dense_model_type: Literal["tfidf", "bm25", "bge-m3", "phobert", "all-minilm", "nomic-embed-text"] = "tfidf"


class VerifierConfig(BaseModel):
    mode: str = Field(default="l1", description="Verification mode: 'off', 'l1', 'l1_l2'")
    similarity_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    l1_overlap_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Minimum L1 token overlap threshold")
    l2_entailment_threshold: float = Field(default=0.30, ge=0.0, le=1.0, description="Minimum L2 semantic entailment threshold")
    l2_use_slm: bool = Field(default=False, description="Enable SLM-based L2 entailment instead of heuristic fallback")


class MemoryConfig(BaseModel):
    enabled: bool = True
    sqlite_path: str = Field(default="data/db/local_slm_memory.db")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    index_version: str = Field(default="native-v2026.10.22")


class SecurityConfig(BaseModel):
    audit_log_path: str = Field(default="data/audit_log.jsonl")
    outbox_path: str = Field(default="data/outbox/sent_summaries.jsonl")
    egress_requires_confirmation: bool = Field(default=True)


class AppConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    budgets: BudgetsConfig = Field(default_factory=BudgetsConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    verifier: VerifierConfig = Field(default_factory=VerifierConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

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
