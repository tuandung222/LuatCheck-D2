"""
Centralized Configuration Module for LuatCheck
Tập trung hóa cấu hình hệ thống bằng Pydantic Models, nạp từ YAML và Environment Variables.
Cho phép Data Scientist dễ dàng tùy chỉnh tham số mô hình, retriever, verifier và bộ nhớ.
"""
import os
import yaml
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str = Field(default="ollama", description="Nhà cung cấp LLM: 'ollama', 'mock', 'vllm'")
    endpoint: str = Field(default="http://localhost:11434", description="URL endpoint của LLM server")
    name: str = Field(default="qwen2.5:3b", description="Tên mô hình phục vụ")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=30.0, gt=0.0)


class BudgetsConfig(BaseModel):
    max_tool_calls: int = Field(default=5, ge=1, description="Số lượt gọi công cụ tối đa cho mỗi phiên")
    max_repairs: int = Field(default=2, ge=0, description="Số lần thử tự sửa chữa tối đa khi vi phạm kiểm chứng")
    max_steps: int = Field(default=10, ge=1, description="Tổng số bước FSM tối đa để chống lặp vô hạn")


class RetrievalConfig(BaseModel):
    bm25_top_k: int = Field(default=5, ge=1)
    dense_top_k: int = Field(default=5, ge=1)
    rrf_k: int = Field(default=60, ge=1, description="Hằng số RRF làm mịn xếp hạng")
    final_top_k: int = Field(default=5, ge=1)
    corpus_path: str = Field(default="data/corpus/labor_code_2019.json")
    dense_model_type: str = Field(default="tfidf", description="Kiểu dense model: 'tfidf', 'bge-m3', 'phobert'")


class VerifierConfig(BaseModel):
    mode: str = Field(default="l1", description="Chế độ xác thực: 'off', 'l1', 'l1_l2'")
    similarity_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    l1_overlap_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Ngưỡng token overlap tối thiểu L1")
    l2_entailment_threshold: float = Field(default=0.30, ge=0.0, le=1.0, description="Ngưỡng kéo theo ngữ nghĩa tối thiểu L2")
    l2_use_slm: bool = Field(default=False, description="Bật chế độ dùng SLM cho L2 thay vì heuristic fallback")


class MemoryConfig(BaseModel):
    sqlite_path: str = Field(default="data/db/luatcheck_memory.db")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    index_version: str = Field(default="v2026.1")


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
        """Alias cho verifier để thân thiện với cấu hình người dùng."""
        return self.verifier


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Nạp cấu hình từ file YAML. Nếu file không tồn tại, trả về AppConfig với giá trị mặc định.
    Cho phép override qua biến môi trường LUATCHECK_CONFIG_PATH.
    """
    target_path = config_path or os.getenv("LUATCHECK_CONFIG_PATH", "config/config.yaml")
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f) or {}
            return AppConfig(**raw_data)
        except Exception:
            return AppConfig()
    return AppConfig()
