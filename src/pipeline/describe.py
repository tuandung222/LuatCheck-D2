"""Human-readable summary of which components a config switches on. Builds and loads nothing."""
from typing import List, Tuple

from src.config.app_config import AppConfig
from src.domains import profile_file_stem
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
        ("domain", "on", profile_file_stem(config.domain.profile, config.domain.profile_variant)
         + (f" (variant {config.domain.profile_variant})" if config.domain.profile_variant else "")),
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
    ] + describe_revision_switches(config)


def describe_revision_switches(config: AppConfig) -> List[Row]:
    """The r2 revision switches (docs/reviews/v3_failure_analysis_2026-10-24.md, F1-F8): `off` = the frozen v3 behaviour."""
    retrieval, verifier, agent, tools, model, domain = (config.retrieval, config.verifier, config.agent, config.tools,
                                                       config.model, config.domain)
    anchored = retrieval.first_search_anchor != "none"
    rows: List[Row] = [
        ("F1 first-search anchor", "on" if anchored else "off",
         "first search = user question + model query" if anchored else "first search = model query"),
        ("F2 default top_k", "on" if retrieval.default_top_k != 3 else "off",
         f"{retrieval.default_top_k} when the model omits it (cap final_top_k {retrieval.final_top_k})"),
        ("F3 search hints", "on" if tools.search_hints else "off",
         "truncation count, read advice, tool_calls_remaining" if tools.search_hints else ""),
        ("F4/F6 profile variant", "on" if domain.profile_variant else "off", domain.profile_variant),
        ("F5 search-first gate", "on" if agent.require_search_before_answer else "off",
         "answer/clarify before a search becomes an observation" if agent.require_search_before_answer else ""),
        ("F6 repair feedback", "on" if verifier.repair_feedback_style != "v1" else "off", verifier.repair_feedback_style),
        ("F7 thought cap", "on" if model.thought_max_chars is not None else "off",
         f"maxLength {model.thought_max_chars}" if model.thought_max_chars is not None else "unbounded"),
        ("F8 free duplicate notices", "on" if agent.free_duplicate_notices else "off", ""),
        ("L1 sentence support", "on" if verifier.l1_sentence_support != "block" else "off",
         f"{verifier.l1_sentence_support}" + (" (ignored: verifier.l1_version is v1)" if verifier.l1_version == "v1" else "")),
    ]
    return rows


def format_pipeline(config: AppConfig) -> str:
    rows = describe_pipeline(config)
    width = max(len(name) for name, _, _ in rows)
    return "\n".join(f"{name:<{width}}  {state:<3}  {detail}".rstrip() for name, state, detail in rows)
