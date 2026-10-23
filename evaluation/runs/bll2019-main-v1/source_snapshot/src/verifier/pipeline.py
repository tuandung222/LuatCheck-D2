"""
Unified Multi-Stage Evidence Verification Pipeline.

Orchestrates multi-stage evidence verification into a decoupled pipeline:
1. Lexical Grounding Verification: Validates citation existence, provenance, and token overlap.
2. Semantic Entailment Verification: Validates logical entailment via NLI or local SLM cross-examination.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional

from src.agent.state import Citation, GroundingVerificationResult
from src.verifier.lexical_grounding import LexicalGroundingVerifier
from src.verifier.semantic_nli import SemanticNLIVerifier


class VerificationMode(str, Enum):
    OFF = "off"
    LEXICAL_GROUNDING = "lexical_grounding"
    SEMANTIC_ENTAILMENT = "semantic_entailment"
    FULL = "full"


@dataclass
class PipelineVerificationResult:
    is_valid: bool
    repair_feedback: Optional[str] = None
    mode: str = "lexical_grounding"
    grounding_result: Optional[GroundingVerificationResult] = None
    semantic_result: Optional[Dict[str, Any]] = None

    @property
    def l1_result(self) -> Optional[GroundingVerificationResult]:
        return self.grounding_result

    @property
    def l2_result(self) -> Optional[Dict[str, Any]]:
        return self.semantic_result


class VerificationPipeline:
    """
    Decoupled verification pipeline orchestrating Lexical Grounding and Semantic NLI verifiers.
    """

    VALID_MODES = {
        "off",
        "lexical_grounding",
        "lexical",
        "grounding",
        "l1",
        "l1_only",
        "l1_on",
        "semantic_entailment",
        "semantic",
        "full",
        "l1_l2",
        "l1_l2_on"
    }

    def __init__(
        self,
        lexical_verifier: Optional[LexicalGroundingVerifier] = None,
        semantic_verifier: Optional[SemanticNLIVerifier] = None,
        verifier: Optional[LexicalGroundingVerifier] = None,
        l2_verifier: Optional[SemanticNLIVerifier] = None,
        mode: str = "lexical_grounding",
        corpus: Optional[List[Dict[str, Any]]] = None,
        l2_entailment_threshold: float = 0.5,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        l2_use_slm: bool = False
    ):
        corpus_data = corpus or []
        self.lexical_verifier = lexical_verifier or verifier or LexicalGroundingVerifier(corpus_data)
        self.semantic_verifier = semantic_verifier or l2_verifier or SemanticNLIVerifier(
            corpus_data,
            entailment_threshold=l2_entailment_threshold,
            ollama_url=ollama_url,
            model_name=model_name,
            use_slm=l2_use_slm
        )
        self.verifier = self.lexical_verifier
        self.l2_verifier = self.semantic_verifier

        self.mode = mode

    def _normalize_mode(self, mode: Any) -> str:
        raw_val = mode.value if hasattr(mode, "value") else str(mode)
        m = str(raw_val).strip().lower()
        if m in ["off"]:
            return "off"
        if m in ["lexical_grounding", "lexical", "grounding", "l1", "l1_only", "l1_on"]:
            return "lexical_grounding"
        if m in ["semantic_entailment", "semantic", "full", "l1_l2", "l1_l2_on"]:
            return "semantic_entailment"
        return m

    def set_mode(self, mode: str):
        normalized = self._normalize_mode(mode)
        if mode not in self.VALID_MODES and normalized not in self.VALID_MODES:
            raise ValueError(f"Invalid verification mode: {mode}. Must be one of {sorted(list(self.VALID_MODES))}")
        self.mode = mode

    def verify(
        self,
        answer_text: str,
        citations: List[Citation],
        retrieved_article_ids: List[str]
    ) -> PipelineVerificationResult:
        """
        Executes verification according to the active mode contract.
        """
        norm_mode = self._normalize_mode(self.mode)

        if norm_mode == "off":
            return PipelineVerificationResult(is_valid=True, repair_feedback=None, mode=self.mode)

        # 1. Execute Stage 1: Lexical Grounding Verification
        grounding_res = self.lexical_verifier.verify(
            answer_text=answer_text,
            citations=citations,
            retrieved_article_ids=retrieved_article_ids
        )

        if not grounding_res.is_valid:
            return PipelineVerificationResult(
                is_valid=False,
                repair_feedback=grounding_res.repair_feedback,
                mode=self.mode,
                grounding_result=grounding_res
            )

        # If lexical grounding only, return success
        if norm_mode == "lexical_grounding":
            return PipelineVerificationResult(
                is_valid=True,
                repair_feedback=None,
                mode=self.mode,
                grounding_result=grounding_res
            )

        # 2. Execute Stage 2: Semantic NLI Entailment Verification
        if norm_mode == "semantic_entailment":
            cit_ids = [c.article_id for c in citations]
            semantic_res = self.semantic_verifier.verify_all_claims(answer_text, cit_ids)

            if not semantic_res.get("is_entailed", False):
                failed_claims = semantic_res.get("failed_claims", [])
                failed_sentences = [f["sentence"] for f in failed_claims]
                repair_fb = (
                    f"CẢNH BÁO XÁC THỰC NGỮ NGHĨA (Semantic Entailment): Phát hiện {len(failed_sentences)} câu khẳng định "
                    f"chưa đạt căn cứ kéo theo ngữ nghĩa (entailment score < {self.semantic_verifier.entailment_threshold}):\n"
                    + "\n".join(f"- \"{s}\"" for s in failed_sentences[:2])
                )
                return PipelineVerificationResult(
                    is_valid=False,
                    repair_feedback=repair_fb,
                    mode=self.mode,
                    grounding_result=grounding_res,
                    semantic_result=semantic_res
                )

            return PipelineVerificationResult(
                is_valid=True,
                repair_feedback=None,
                mode=self.mode,
                grounding_result=grounding_res,
                semantic_result=semantic_res
            )

        return PipelineVerificationResult(is_valid=True, repair_feedback=None, mode=self.mode)
