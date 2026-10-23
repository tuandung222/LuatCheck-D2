"""Human-readable summary of which components a config switches on. Builds and loads nothing."""
from typing import List, Tuple

from src.config.app_config import AppConfig
from src.verifier.modes import LEXICAL_GROUNDING, OFF, SEMANTIC_ENTAILMENT, canonical_mode

Row = Tuple[str, str, str]   # (component, state, detail)


def describe_pipeline(config: AppConfig) -> List[Row]:
    model, retrieval, verifier = config.model, config.retrieval, config.verifier
    rerank, nli, memory = retrieval.reranker, verifier.nli, config.memory
    mode = canonical_mode(verifier.mode)

    if retrieval.mode == "hybrid_index":
        retriever = f"index {retrieval.index.path} (store {retrieval.index.store or 'manifest default'}, {retrieval.index.search_mode})"
    else:
        retriever = f"BM25 + {retrieval.dense_model_type}, RRF k={retrieval.rrf_k}, corpus {retrieval.corpus_path}"
    l2_detail = "native-model entailment" if verifier.l2_use_slm else "mode asks for L2 but verifier.l2_use_slm is false: L2 will raise"
    return [
        ("domain", "on", config.domain.profile),
        ("controller LLM", "on", f"{model.provider}: {model.name} @ {model.endpoint}"),
        ("guardrails", "on" if config.security.guardrails.enabled else "off", "input pattern check before the model"),
        ("retriever", "on", f"{retrieval.mode}: {retriever}"),
        ("reranker", "on" if rerank.enabled else "off",
         f"{rerank.backend}: {rerank.model or rerank.base_url} (top_k_in {rerank.top_k_in} -> top_k_out {rerank.top_k_out})" if rerank.enabled else ""),
        ("verifier L1", "on" if mode in (LEXICAL_GROUNDING, SEMANTIC_ENTAILMENT) else "off", f"verifier.mode = {verifier.mode}"),
        ("verifier L2", "on" if mode == SEMANTIC_ENTAILMENT else "off", l2_detail if mode == SEMANTIC_ENTAILMENT else ""),
        ("verifier NLI", "on" if nli.enabled and mode != OFF else "off",
         f"{nli.backend}: {nli.model} (action {nli.action}, threshold {nli.threshold})" if nli.enabled else ""),
        ("memory", "on" if memory.enabled else "off",
         f"{memory.backend}: {memory.sqlite_path}; reuse_answers={memory.reuse_answers}" if memory.enabled else ""),
    ]


def format_pipeline(config: AppConfig) -> str:
    rows = describe_pipeline(config)
    width = max(len(name) for name, _, _ in rows)
    return "\n".join(f"{name:<{width}}  {state:<3}  {detail}".rstrip() for name, state, detail in rows)
