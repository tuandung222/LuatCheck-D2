"""
Unified Multi-Stage Evidence Verification Pipeline.

Orchestrates multi-stage evidence verification into a decoupled pipeline:
1. Lexical Grounding Verification (L1): validates citation existence, provenance, token overlap and exact quantities.
2. Optional NLI step (`verifier.nli`): per (sentence, cited record) NLI probabilities, flag or repair.
3. Semantic Entailment Verification (L2): native-model cross-examination, only in the L2 modes.
"""
import time
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional

from src.agent.state import Citation, GroundingVerificationResult
from src.domains import load_profile
from src.domains.profile import MessagesSpec
from src.verifier.lexical_grounding import LexicalGroundingVerifier, split_sentences
from src.verifier.modes import LEXICAL_GROUNDING, OFF, VALID_MODES, VerificationMode, canonical_mode
from src.verifier.semantic_nli import SemanticNLIVerifier
from src.model_runtime import ModelComponentError, doc_text

__all__ = ["VerificationMode", "PipelineVerificationResult", "NLIStep", "VerificationPipeline"]


def _failed_claim_lines(sentences: List[str]) -> str:
    return "\n".join(f'- "{s}"' for s in sentences[:2])


@dataclass
class PipelineVerificationResult:
    is_valid: bool
    repair_feedback: Optional[str] = None
    mode: str = "lexical_grounding"
    grounding_result: Optional[GroundingVerificationResult] = None
    semantic_result: Optional[Dict[str, Any]] = None
    nli_result: Optional[Dict[str, Any]] = None

    @property
    def l1_result(self) -> Optional[GroundingVerificationResult]:
        return self.grounding_result

    @property
    def l2_result(self) -> Optional[Dict[str, Any]]:
        return self.semantic_result


class NLIStep:
    """Optional NLI check after L1 (`verifier.nli`).

    For every answer sentence (hypothesis) and every cited record (premise = the full text of that one record,
    never a concatenation of several records) the NLI backend returns P(entailment / neutral / contradiction).
    ``action="flag"`` only records the results; ``action="repair"`` also fails the verification (which triggers the
    existing repair loop) when any pair has P(contradiction) >= ``threshold``. Probabilities are model outputs,
    not evidence of answer correctness. A backend failure raises ``ModelComponentError``: it is never turned into
    a pass, a flag or a repair request.
    """

    _DETAIL_KEYS = ("backend", "wall_ms", "device", "n_windows", "selected_window", "remote_inference", "input_tokens")

    def __init__(self, handle: Any, lookup: Callable[[str], Optional[Dict[str, Any]]], threshold: float = 0.9,
                 action: str = "flag", messages: Optional[MessagesSpec] = None):
        if action not in ("flag", "repair"):
            raise ModelComponentError(f"NLI action must be 'flag' or 'repair', got {action!r}", kind="config_error")
        if not 0.0 <= threshold <= 1.0:
            raise ModelComponentError(f"NLI threshold must be in [0, 1], got {threshold!r}", kind="config_error")
        self.handle, self.lookup, self.threshold, self.action = handle, lookup, float(threshold), action
        self.messages = messages or load_profile().messages

    def sentences(self, answer_text: str) -> List[str]:
        """Same sentence split as the L1 verifier."""
        return split_sentences(answer_text)

    def run(self, answer_text: str, citations: List[Citation]) -> Dict[str, Any]:
        premises: Dict[str, str] = {}
        for citation in citations:
            if citation.article_id in premises:
                continue
            record = self.lookup(citation.article_id)
            if not record:
                raise ModelComponentError(f"NLI: cited record {citation.article_id!r} not found", kind="config_error")
            premises[citation.article_id] = doc_text(record, ("title", "content", "full_content"))
        sentences = self.sentences(answer_text)
        pairs: List[Dict[str, Any]] = []
        started = time.perf_counter()
        with self.handle.use() as nli:
            for sentence in sentences:
                for article_id, premise in premises.items():
                    verdict = nli.verify(premise, sentence)
                    pairs.append({
                        "sentence": sentence, "premise_id": article_id, "premise_chars": len(premise),
                        "label": verdict.label, "probabilities": dict(verdict.probabilities),
                        "contradiction": verdict.probabilities["contradiction"],
                        "contradicted": verdict.probabilities["contradiction"] >= self.threshold,
                        "details": {k: verdict.details[k] for k in self._DETAIL_KEYS if k in verdict.details}})
            component = nli.info()
        contradicted = [p for p in pairs if p["contradicted"]]
        return {"action": self.action, "threshold": self.threshold, "component": component,
                "n_sentences": len(sentences), "n_premises": len(premises), "n_pairs": len(pairs),
                "wall_ms": (time.perf_counter() - started) * 1000.0, "pairs": pairs,
                "n_contradicted": len(contradicted),
                "triggers_repair": self.action == "repair" and bool(contradicted),
                "note": "NLI model probabilities; not evidence of answer correctness"}

    def repair_feedback(self, result: Dict[str, Any]) -> str:
        bad = [p for p in result["pairs"] if p["contradicted"]]
        pairs = "\n".join(self.messages.nli_pair_line.format(
            sentence=p["sentence"], premise_id=p["premise_id"], probability=p["contradiction"]) for p in bad[:2])
        return self.messages.nli_repair_feedback.format(count=len(bad), threshold=self.threshold, pairs=pairs)


class VerificationPipeline:
    """
    Decoupled verification pipeline orchestrating Lexical Grounding and Semantic NLI verifiers.

    `mode` (see `src.verifier.modes`): ``off`` accepts every answer; the L1 modes run the lexical grounding verifier;
    the L2 modes add the semantic entailment verifier. An optional `nli_step` runs after L1 in every non-off mode.
    """

    VALID_MODES = VALID_MODES

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
        l2_use_slm: bool = False,
        nli_step: Optional[NLIStep] = None,
        messages: Optional[MessagesSpec] = None
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
        self.messages = messages or self.lexical_verifier.profile.messages

        self._check_mode(mode)
        self.mode = mode
        self.nli_step = nli_step

    def _check_mode(self, mode: Any) -> None:
        if mode not in self.VALID_MODES and canonical_mode(mode) not in self.VALID_MODES:
            raise ValueError(f"Invalid verification mode: {mode}. Must be one of {sorted(self.VALID_MODES)}")

    def _normalize_mode(self, mode: Any) -> str:
        return canonical_mode(mode)

    def set_mode(self, mode: str):
        self._check_mode(mode)
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
        norm_mode = canonical_mode(self.mode)
        if norm_mode == OFF:
            return PipelineVerificationResult(is_valid=True, repair_feedback=None, mode=self.mode)

        # Stage 1: lexical grounding (L1)
        grounding_res = self.lexical_verifier.verify(
            answer_text=answer_text,
            citations=citations,
            retrieved_article_ids=retrieved_article_ids
        )
        if not grounding_res.is_valid:
            return PipelineVerificationResult(is_valid=False, repair_feedback=grounding_res.repair_feedback,
                                              mode=self.mode, grounding_result=grounding_res)

        # Optional NLI step after L1 (verifier.nli): records every pair; fails verification only in "repair" action.
        nli_res = self.nli_step.run(answer_text, citations) if self.nli_step is not None else None
        if nli_res is not None and nli_res["triggers_repair"]:
            return PipelineVerificationResult(is_valid=False, repair_feedback=self.nli_step.repair_feedback(nli_res),
                                              mode=self.mode, grounding_result=grounding_res, nli_result=nli_res)

        if norm_mode == LEXICAL_GROUNDING:
            return PipelineVerificationResult(is_valid=True, repair_feedback=None, mode=self.mode,
                                              grounding_result=grounding_res, nli_result=nli_res)

        # Stage 2: semantic entailment (L2), norm_mode == SEMANTIC_ENTAILMENT
        semantic_res = self.semantic_verifier.verify_all_claims(answer_text, [c.article_id for c in citations])
        if not semantic_res.get("is_entailed", False):
            failed = [f["sentence"] for f in semantic_res.get("failed_claims", [])]
            feedback = self.messages.l2_repair_feedback.format(
                count=len(failed), threshold=self.semantic_verifier.entailment_threshold,
                claims=_failed_claim_lines(failed))
            return PipelineVerificationResult(is_valid=False, repair_feedback=feedback, mode=self.mode,
                                              grounding_result=grounding_res, semantic_result=semantic_res,
                                              nli_result=nli_res)
        return PipelineVerificationResult(is_valid=True, repair_feedback=None, mode=self.mode,
                                          grounding_result=grounding_res, semantic_result=semantic_res,
                                          nli_result=nli_res)
